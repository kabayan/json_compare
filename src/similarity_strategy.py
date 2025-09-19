"""類似度計算戦略パターンの実装

Strategyパターンを使用して埋め込みベースとLLMベースの類似度計算を
動的に切り替えるモジュール。フォールバック機能と統計収集を含む。
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from . import similarity
from .llm_similarity import LLMSimilarity, SimilarityResult as LLMResult, LLMSimilarityError

logger = logging.getLogger(__name__)


class StrategyError(Exception):
    """戦略パターン関連のエラー"""
    pass


@dataclass
class StrategyResult:
    """戦略パターンによる類似度計算結果"""
    score: float
    method: str
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "score": self.score,
            "method": self.method,
            "processing_time": self.processing_time,
            "metadata": self.metadata
        }


class SimilarityStrategy(ABC):
    """類似度計算戦略の抽象基底クラス"""

    @abstractmethod
    async def calculate_similarity(self, json1: str, json2: str) -> StrategyResult:
        """
        類似度を計算する抽象メソッド

        Args:
            json1: JSON文字列1
            json2: JSON文字列2

        Returns:
            計算結果

        Raises:
            StrategyError: 計算に失敗した場合
        """
        pass


class EmbeddingSimilarityStrategy(SimilarityStrategy):
    """埋め込みベース類似度計算戦略"""

    def __init__(self, use_gpu: bool = False):
        """
        初期化

        Args:
            use_gpu: GPU使用フラグ
        """
        self.use_gpu = use_gpu
        # 埋め込みモデルの設定
        similarity.set_gpu_mode(use_gpu)

    async def calculate_similarity(self, json1: str, json2: str) -> StrategyResult:
        """
        埋め込みベースで類似度を計算

        Args:
            json1: JSON文字列1
            json2: JSON文字列2

        Returns:
            計算結果

        Raises:
            StrategyError: 計算に失敗した場合
        """
        start_time = time.time()

        try:
            # 既存の埋め込みベース計算を実行
            score, details = similarity.calculate_json_similarity(json1, json2)

            processing_time = time.time() - start_time

            return StrategyResult(
                score=score,
                method="embedding",
                processing_time=processing_time,
                metadata=details
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"埋め込みベース類似度計算に失敗: {e}")
            raise StrategyError(f"埋め込みベース計算に失敗しました: {e}")


class LLMSimilarityStrategy(SimilarityStrategy):
    """LLMベース類似度計算戦略"""

    def __init__(self, llm_similarity: Optional[LLMSimilarity] = None):
        """
        初期化

        Args:
            llm_similarity: LLMSimilarityインスタンス
        """
        self.llm_similarity = llm_similarity or LLMSimilarity()

    async def calculate_similarity(self, json1: str, json2: str) -> StrategyResult:
        """
        LLMベースで類似度を計算

        Args:
            json1: JSON文字列1
            json2: JSON文字列2

        Returns:
            計算結果

        Raises:
            StrategyError: 計算に失敗した場合
        """
        try:
            # LLMベース計算を実行
            llm_result = await self.llm_similarity.calculate_similarity(json1, json2)

            # LLMResultをStrategyResultに変換
            return StrategyResult(
                score=llm_result.score,
                method="llm",
                processing_time=llm_result.processing_time,
                metadata={
                    "category": llm_result.category,
                    "reason": llm_result.reason,
                    "model_used": llm_result.model_used,
                    "confidence": llm_result.confidence,
                    "tokens_used": llm_result.tokens_used
                }
            )

        except Exception as e:
            logger.error(f"LLMベース類似度計算に失敗: {e}")
            raise StrategyError(f"LLMベース計算に失敗しました: {e}")


class SimilarityCalculator:
    """類似度計算機（戦略パターンのコンテキスト）"""

    def __init__(
        self,
        embedding_strategy: Optional[EmbeddingSimilarityStrategy] = None,
        llm_strategy: Optional[LLMSimilarityStrategy] = None
    ):
        """
        初期化

        Args:
            embedding_strategy: 埋め込み戦略
            llm_strategy: LLM戦略
        """
        self.embedding_strategy = embedding_strategy or EmbeddingSimilarityStrategy()
        self.llm_strategy = llm_strategy or LLMSimilarityStrategy()

        # 統計情報
        self._stats = {
            "total_calculations": 0,
            "embedding_used": 0,
            "llm_used": 0,
            "fallback_used": 0,
            "failed_calculations": 0,
            "total_processing_time": 0.0
        }

    async def __aenter__(self):
        """非同期コンテキストマネージャーの開始"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了"""
        # リソースクリーンアップ（必要に応じて）
        pass

    def _validate_method(self, method: str):
        """計算方法の妥当性を検証"""
        valid_methods = ["embedding", "llm", "auto"]
        if method not in valid_methods:
            raise StrategyError(f"サポートされていない計算方法: {method}")

    def _should_use_llm_for_auto(self, json1: str, json2: str) -> bool:
        """
        自動選択でLLMを使うべきかどうかを判断

        Args:
            json1: JSON文字列1
            json2: JSON文字列2

        Returns:
            LLMを使うべきならTrue
        """
        # 基本ルール：テキスト量が多い場合やsemanticな比較が必要そうな場合はLLM
        total_length = len(json1) + len(json2)

        # 長いテキストの場合はLLM
        if total_length > 1000:
            return True

        # 特定のキーワードが含まれている場合はLLM（意味的比較が重要）
        semantic_keywords = ["task", "description", "message", "content", "text", "comment"]
        combined_text = (json1 + json2).lower()

        for keyword in semantic_keywords:
            if keyword in combined_text:
                return True

        # デフォルトは埋め込みを使用
        return False

    async def calculate_similarity(
        self,
        json1: str,
        json2: str,
        method: str = "auto",
        fallback_enabled: bool = True,
        **kwargs
    ) -> StrategyResult:
        """
        指定された戦略で類似度を計算

        Args:
            json1: JSON文字列1
            json2: JSON文字列2
            method: 計算方法（"embedding", "llm", "auto"）
            fallback_enabled: フォールバック有効フラグ
            **kwargs: 各戦略に渡す追加パラメータ

        Returns:
            計算結果

        Raises:
            StrategyError: 計算に失敗した場合
        """
        self._validate_method(method)
        self._stats["total_calculations"] += 1

        start_time = time.time()

        try:
            # 方法の決定
            if method == "auto":
                if self._should_use_llm_for_auto(json1, json2):
                    chosen_method = "llm"
                else:
                    chosen_method = "embedding"
            else:
                chosen_method = method

            # 戦略の実行
            try:
                if chosen_method == "llm":
                    result = await self.llm_strategy.calculate_similarity(json1, json2)
                    self._stats["llm_used"] += 1
                else:  # embedding
                    result = await self.embedding_strategy.calculate_similarity(json1, json2)
                    self._stats["embedding_used"] += 1

                processing_time = time.time() - start_time
                self._stats["total_processing_time"] += processing_time

                return result

            except Exception as e:
                # フォールバック処理
                if fallback_enabled and chosen_method == "llm":
                    logger.warning(f"LLM計算に失敗、埋め込みモードにフォールバック: {e}")
                    try:
                        result = await self.embedding_strategy.calculate_similarity(json1, json2)
                        result.method = "embedding_fallback"
                        self._stats["embedding_used"] += 1
                        self._stats["fallback_used"] += 1

                        processing_time = time.time() - start_time
                        self._stats["total_processing_time"] += processing_time

                        return result

                    except Exception as fallback_error:
                        logger.error(f"フォールバックも失敗: {fallback_error}")
                        self._stats["failed_calculations"] += 1
                        raise StrategyError(f"全ての計算方法が失敗しました: {fallback_error}")

                else:
                    self._stats["failed_calculations"] += 1
                    if isinstance(e, (StrategyError, LLMSimilarityError)):
                        raise
                    else:
                        raise StrategyError(f"LLM計算に失敗しました: {e}")

        except Exception as e:
            # 内側のexceptで既にfailed_calculationsが更新されている場合はスキップ
            if not isinstance(e, (StrategyError, LLMSimilarityError)):
                self._stats["failed_calculations"] += 1
            logger.error(f"類似度計算に失敗: {e}")
            if isinstance(e, StrategyError):
                raise
            raise StrategyError(f"類似度計算に失敗しました: {e}")

    async def calculate_batch_similarity(
        self,
        json_pairs: List[Tuple[str, str]],
        method: str = "auto",
        sequential: bool = True,
        fallback_enabled: bool = True,
        **kwargs
    ) -> List[StrategyResult]:
        """
        複数のJSONペアの類似度を一括計算

        Args:
            json_pairs: JSONペアのリスト
            method: 計算方法
            sequential: 順次処理するかどうか
            fallback_enabled: フォールバック有効フラグ
            **kwargs: 各戦略に渡す追加パラメータ

        Returns:
            計算結果のリスト
        """
        results = []

        if sequential:
            # 順次処理
            for i, (json1, json2) in enumerate(json_pairs):
                try:
                    result = await self.calculate_similarity(
                        json1, json2, method=method, fallback_enabled=fallback_enabled, **kwargs
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"ペア {i+1} の処理に失敗: {e}")
                    # エラーが発生してもcontinue
                    error_result = StrategyResult(
                        score=0.0,
                        method="error",
                        metadata={"error": str(e)}
                    )
                    results.append(error_result)

        else:
            # 並列処理
            tasks = [
                self.calculate_similarity(
                    json1, json2, method=method, fallback_enabled=fallback_enabled, **kwargs
                )
                for json1, json2 in json_pairs
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 例外をエラー結果に変換
            for result in batch_results:
                if isinstance(result, Exception):
                    error_result = StrategyResult(
                        score=0.0,
                        method="error",
                        metadata={"error": str(result)}
                    )
                    results.append(error_result)
                else:
                    results.append(result)

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        total = self._stats["total_calculations"]
        successful = total - self._stats["failed_calculations"]

        return {
            "total_calculations": total,
            "successful_calculations": successful,
            "failed_calculations": self._stats["failed_calculations"],
            "success_rate": successful / max(total, 1),
            "embedding_used": self._stats["embedding_used"],
            "llm_used": self._stats["llm_used"],
            "fallback_used": self._stats["fallback_used"],
            "total_processing_time": self._stats["total_processing_time"],
            "average_processing_time": self._stats["total_processing_time"] / max(total, 1)
        }

    def reset_statistics(self):
        """統計情報をリセット"""
        self._stats = {
            "total_calculations": 0,
            "embedding_used": 0,
            "llm_used": 0,
            "fallback_used": 0,
            "failed_calculations": 0,
            "total_processing_time": 0.0
        }


# ファクトリー関数
async def create_similarity_calculator(
    use_gpu: bool = False,
    llm_config: Optional[Dict[str, Any]] = None
) -> SimilarityCalculator:
    """
    SimilarityCalculatorのファクトリー関数

    Args:
        use_gpu: 埋め込み計算でGPU使用するかどうか
        llm_config: LLM設定

    Returns:
        初期化されたSimilarityCalculator
    """
    embedding_strategy = EmbeddingSimilarityStrategy(use_gpu=use_gpu)

    # LLM戦略の初期化
    if llm_config:
        from .llm_client import LLMConfig, LLMClient
        client_config = LLMConfig(**llm_config)
        llm_client = LLMClient(client_config)
        llm_similarity = LLMSimilarity(llm_client=llm_client)
        llm_strategy = LLMSimilarityStrategy(llm_similarity=llm_similarity)
    else:
        llm_strategy = LLMSimilarityStrategy()

    return SimilarityCalculator(
        embedding_strategy=embedding_strategy,
        llm_strategy=llm_strategy
    )


async def create_similarity_calculator_from_args(config) -> SimilarityCalculator:
    """
    CLI設定からSimilarityCalculatorを作成（テスト互換性用）

    Args:
        config: CLI設定オブジェクト

    Returns:
        初期化されたSimilarityCalculator
    """
    use_gpu = getattr(config, 'use_gpu', False)
    llm_config = getattr(config, 'to_llm_config', lambda: None)()

    return await create_similarity_calculator(
        use_gpu=use_gpu,
        llm_config=llm_config
    )