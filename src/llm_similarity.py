"""LLMベース類似度計算エンジン

vLLM APIを使用してテキストの意味的類似度を計算するモジュール。
プロンプトテンプレート、バッチ処理、エラーハンドリングをサポート。
"""

import asyncio
import re
import time
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path

from .llm_client import LLMClient, LLMConfig, ChatMessage, LLMResponse, LLMClientError
from .prompt_template import PromptTemplate, PromptTemplateError

logger = logging.getLogger(__name__)


class LLMSimilarityError(Exception):
    """LLM類似度計算関連のエラー"""
    pass


@dataclass
class SimilarityResult:
    """類似度計算結果"""
    score: float
    category: str = ""
    reason: str = ""
    method: str = "llm"
    model_used: str = ""
    processing_time: float = 0.0
    confidence: float = 0.0
    raw_response: str = ""
    tokens_used: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "score": self.score,
            "category": self.category,
            "reason": self.reason,
            "method": self.method,
            "model_used": self.model_used,
            "processing_time": self.processing_time,
            "confidence": self.confidence,
            "tokens_used": self.tokens_used
        }


class LLMSimilarity:
    """LLMベース類似度計算エンジン"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_template: Optional[PromptTemplate] = None,
        default_template_path: str = "prompts/default_similarity.yaml"
    ):
        """
        LLMSimilarityインスタンスを初期化

        Args:
            llm_client: LLMクライアント
            prompt_template: プロンプトテンプレート
            default_template_path: デフォルトテンプレートのパス
        """
        self.llm_client = llm_client or LLMClient()
        self.prompt_template = prompt_template or PromptTemplate()
        self.default_template_path = default_template_path
        self.current_template: Optional[Dict[str, Any]] = None

        # フォールバック設定
        self.enable_fallback = False
        self.embedding_calculator = None

        # 統計情報
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_processing_time": 0.0,
            "model_usage": {}
        }

        # テキスト長制限
        self.max_text_length = 10000

    async def __aenter__(self):
        """非同期コンテキストマネージャーの開始"""
        await self._load_default_template()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了"""
        if hasattr(self.llm_client, 'close'):
            await self.llm_client.close()

    async def _load_default_template(self):
        """デフォルトテンプレートの読み込み"""
        try:
            self.current_template = self.prompt_template.load_template(
                self.default_template_path
            )
            logger.info(f"デフォルトテンプレートを読み込みました: {self.default_template_path}")
        except Exception as e:
            logger.warning(f"デフォルトテンプレートの読み込みに失敗: {e}")
            self.current_template = self._get_builtin_template()

    def _get_builtin_template(self) -> Dict[str, Any]:
        """組み込みテンプレートを取得"""
        return {
            "prompts": {
                "system": "あなたは日本語テキストの意味的類似度を評価する専門家です。",
                "user": """以下の2つのテキストの類似度を評価してください。

テキスト1: {text1}
テキスト2: {text2}

以下の形式で回答してください：
スコア: [0.0-1.0の数値]
カテゴリ: [完全一致/非常に類似/類似/やや類似/低い類似度]
理由: [判定の根拠]"""
            },
            "parameters": {
                "temperature": 0.2,
                "max_tokens": 64
            }
        }

    def _validate_texts(self, text1: str, text2: str):
        """テキスト入力のバリデーション"""
        if not text1 or not text1.strip():
            raise LLMSimilarityError("テキスト1が空です")
        if not text2 or not text2.strip():
            raise LLMSimilarityError("テキスト2が空です")

        if len(text1) > self.max_text_length:
            raise LLMSimilarityError(f"テキスト1が長すぎます（{len(text1)} > {self.max_text_length}文字）")
        if len(text2) > self.max_text_length:
            raise LLMSimilarityError(f"テキスト2が長すぎます（{len(text2)} > {self.max_text_length}文字）")

    async def set_prompt_template(self, template_path: str):
        """プロンプトテンプレートを設定"""
        try:
            self.current_template = self.prompt_template.load_template(template_path)
            logger.info(f"プロンプトテンプレートを設定しました: {template_path}")
        except Exception as e:
            raise LLMSimilarityError(f"テンプレートの読み込みに失敗: {e}")

    def _build_messages(self, text1: str, text2: str) -> List[ChatMessage]:
        """チャットメッセージを構築"""
        if not self.current_template:
            self.current_template = self._get_builtin_template()

        prompts = self.current_template.get("prompts", {})

        messages = []

        # システムプロンプト
        if "system" in prompts:
            messages.append(ChatMessage(
                role="system",
                content=prompts["system"]
            ))

        # ユーザープロンプト（変数置換）
        user_prompt = prompts.get("user", "テキスト1: {text1}\nテキスト2: {text2}")
        rendered_prompt = self.prompt_template.render(
            user_prompt,
            {"text1": text1, "text2": text2}
        )

        messages.append(ChatMessage(
            role="user",
            content=rendered_prompt
        ))

        return messages

    def _parse_llm_response(self, response: LLMResponse) -> SimilarityResult:
        """LLMレスポンスを解析してSimilarityResultに変換"""
        content = response.content

        # スコア抽出
        score_match = re.search(r'スコア[：:]\s*([0-9.]+)', content)
        if not score_match:
            raise LLMSimilarityError(f"レスポンス解析に失敗: スコアが見つかりません - {content}")

        try:
            score = float(score_match.group(1))
            if not 0.0 <= score <= 1.0:
                score = max(0.0, min(1.0, score))  # 範囲内にクランプ
        except ValueError:
            raise LLMSimilarityError(f"スコアの解析に失敗: {score_match.group(1)}")

        # カテゴリ抽出
        category_match = re.search(r'カテゴリ[：:]\s*([^\n]+)', content)
        category = category_match.group(1).strip() if category_match else ""

        # 理由抽出
        reason_match = re.search(r'理由[：:]\s*([^\n]+(?:\n[^\n*]+)*)', content)
        reason = reason_match.group(1).strip() if reason_match else ""

        return SimilarityResult(
            score=score,
            category=category,
            reason=reason,
            method="llm",
            model_used=response.model,
            raw_response=content,
            tokens_used=response.total_tokens
        )

    async def calculate_similarity(
        self,
        text1: str,
        text2: str,
        model_config: Optional[Dict[str, Any]] = None
    ) -> SimilarityResult:
        """
        2つのテキストの類似度を計算

        Args:
            text1: 比較対象テキスト1
            text2: 比較対象テキスト2
            model_config: モデル設定のオーバーライド

        Returns:
            類似度計算結果

        Raises:
            LLMSimilarityError: 計算に失敗した場合
        """
        start_time = time.time()

        try:
            # 入力バリデーション
            self._validate_texts(text1, text2)

            # デフォルトテンプレートが未読み込みの場合は読み込み
            if not self.current_template:
                await self._load_default_template()

            # メッセージ構築
            messages = self._build_messages(text1, text2)

            # LLM呼び出し
            kwargs = {}
            if model_config:
                kwargs.update(model_config)
            elif self.current_template.get("parameters"):
                kwargs.update(self.current_template["parameters"])

            response = await self.llm_client.chat_completion(messages, **kwargs)

            # レスポンス解析
            result = self._parse_llm_response(response)
            result.processing_time = time.time() - start_time

            # 統計更新
            self._update_stats(success=True, processing_time=result.processing_time, model=response.model)

            logger.info(f"類似度計算完了: スコア={result.score}, 時間={result.processing_time:.2f}秒")
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            self._update_stats(success=False, processing_time=processing_time)

            # フォールバック機能
            if self.enable_fallback and self.embedding_calculator:
                logger.warning(f"LLM計算に失敗、埋め込みモードにフォールバック: {e}")
                try:
                    embedding_score = self.embedding_calculator.calculate_similarity(text1, text2)
                    return SimilarityResult(
                        score=embedding_score,
                        method="embedding_fallback",
                        processing_time=processing_time
                    )
                except Exception as fallback_error:
                    logger.error(f"フォールバックも失敗: {fallback_error}")

            if isinstance(e, LLMSimilarityError):
                raise
            raise LLMSimilarityError(f"LLM推論に失敗しました: {e}")

    async def calculate_batch_similarity(
        self,
        text_pairs: List[Tuple[str, str]],
        sequential: bool = True,
        delay_between_requests: float = 0.0,
        model_config: Optional[Dict[str, Any]] = None
    ) -> List[SimilarityResult]:
        """
        複数のテキストペアの類似度を一括計算

        Args:
            text_pairs: テキストペアのリスト
            sequential: 順次処理するかどうか（レート制限対応）
            delay_between_requests: リクエスト間の遅延時間（秒）
            model_config: モデル設定

        Returns:
            類似度計算結果のリスト
        """
        results = []

        if sequential:
            # 順次処理
            for i, (text1, text2) in enumerate(text_pairs):
                try:
                    result = await self.calculate_similarity(text1, text2, model_config)
                    results.append(result)

                    # 遅延追加（レート制限対応）
                    if delay_between_requests > 0 and i < len(text_pairs) - 1:
                        await asyncio.sleep(delay_between_requests)

                except Exception as e:
                    logger.error(f"ペア {i+1} の処理に失敗: {e}")
                    # エラーが発生してもcontinue
                    results.append(SimilarityResult(
                        score=0.0,
                        method="error",
                        reason=str(e)
                    ))
        else:
            # 並列処理
            tasks = [
                self.calculate_similarity(text1, text2, model_config)
                for text1, text2 in text_pairs
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 例外をエラー結果に変換
            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    processed_results.append(SimilarityResult(
                        score=0.0,
                        method="error",
                        reason=str(result)
                    ))
                else:
                    processed_results.append(result)
            results = processed_results

        return results

    def _update_stats(self, success: bool, processing_time: float, model: str = ""):
        """統計情報を更新"""
        self._stats["total_requests"] += 1
        self._stats["total_processing_time"] += processing_time

        if success:
            self._stats["successful_requests"] += 1
            if model:
                self._stats["model_usage"][model] = self._stats["model_usage"].get(model, 0) + 1
        else:
            self._stats["failed_requests"] += 1

    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        total_requests = self._stats["total_requests"]

        return {
            "total_requests": total_requests,
            "successful_requests": self._stats["successful_requests"],
            "failed_requests": self._stats["failed_requests"],
            "success_rate": self._stats["successful_requests"] / max(total_requests, 1),
            "average_processing_time": self._stats["total_processing_time"] / max(total_requests, 1),
            "model_usage": self._stats["model_usage"].copy()
        }

    def reset_statistics(self):
        """統計情報をリセット"""
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_processing_time": 0.0,
            "model_usage": {}
        }