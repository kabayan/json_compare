"""vLLM APIクライアント

httpxを使用してvLLM APIと通信するクライアントモジュール。
エラーハンドリング、リトライ、タイムアウト処理を含む。
"""

import httpx
import asyncio
import os
import time
import logging
import uuid
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from functools import wraps
import json
from tqdm import tqdm

logger = logging.getLogger(__name__)

# メトリクス収集のための遅延インポート
try:
    from .llm_metrics import LLMMetricsCollector
except ImportError:
    LLMMetricsCollector = None


class LLMClientError(Exception):
    """LLMクライアント関連のエラー"""
    pass


@dataclass
class LLMConfig:
    """LLMクライアントの設定"""
    api_url: str = "http://192.168.1.18:8000/v1/chat/completions"
    model: str = "qwen3-14b-awq"
    temperature: float = 0.2
    max_tokens: int = 64
    timeout: float = 30.0
    auth_token: str = "EMPTY"
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_factor: float = 2.0

    def __post_init__(self):
        """設定値のバリデーション"""
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError("temperature は 0.0 から 1.0 の間である必要があります")
        if self.max_tokens < 1:
            raise ValueError("max_tokens は 1 以上である必要があります")
        if self.timeout < 1:
            raise ValueError("timeout は 1 秒以上である必要があります")

    @classmethod
    def from_environment(cls) -> 'LLMConfig':
        """環境変数から設定を読み込む"""
        return cls(
            api_url=os.getenv('VLLM_API_URL', cls.api_url),
            model=os.getenv('VLLM_MODEL', cls.model),
            temperature=float(os.getenv('VLLM_TEMPERATURE', str(cls.temperature))),
            max_tokens=int(os.getenv('VLLM_MAX_TOKENS', str(cls.max_tokens))),
            timeout=float(os.getenv('VLLM_TIMEOUT', str(cls.timeout))),
            auth_token=os.getenv('VLLM_AUTH_TOKEN', cls.auth_token)
        )

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "chat_template_kwargs": {
                "enable_thinking": False
            }
        }


@dataclass
class ChatMessage:
    """チャットメッセージ"""
    role: str  # "system", "user", "assistant"
    content: str

    def to_dict(self) -> Dict[str, str]:
        """辞書形式に変換"""
        return {
            "role": self.role,
            "content": self.content
        }


@dataclass
class LLMResponse:
    """LLMレスポンス"""
    id: str = ""
    content: str = ""
    model: str = ""
    finish_reason: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    created: int = 0

    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> 'LLMResponse':
        """APIレスポンスからインスタンスを作成"""
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = response.get("usage", {})

        return cls(
            id=response.get("id", ""),
            content=message.get("content", ""),
            model=response.get("model", ""),
            finish_reason=choice.get("finish_reason", ""),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            created=response.get("created", 0)
        )


class LLMClient:
    """vLLM APIクライアント"""

    def __init__(self, config: Optional[LLMConfig] = None, metrics_collector: Optional[Any] = None):
        """
        LLMクライアントを初期化

        Args:
            config: クライアント設定
            metrics_collector: メトリクス収集インスタンス
        """
        self.config = config or LLMConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self.metrics_collector = metrics_collector

        # Task 2.2: 連続失敗時のフォールバック管理
        self.consecutive_failures = 0
        self.should_fallback_to_embedding = False

    async def __aenter__(self):
        """非同期コンテキストマネージャーの開始"""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了"""
        await self.close()

    async def _ensure_client(self):
        """HTTPクライアントの初期化を確実に行う"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout)
            )

    async def close(self):
        """クライアントをクリーンアップ"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_headers(self) -> Dict[str, str]:
        """リクエストヘッダーを生成"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.auth_token}"
        }

    def _check_consecutive_failures(self) -> None:
        """
        連続失敗回数をチェックしてフォールバック推奨フラグを設定（Requirement 6.3）
        """
        if self.consecutive_failures >= 3:
            self.should_fallback_to_embedding = True
            logger.warning(
                f"LLM API呼び出しが{self.consecutive_failures}回連続で失敗しました。"
                "埋め込みベースモードへのフォールバックを推奨します。"
            )

    async def _retry_with_backoff(self, func, *args, **kwargs):
        """指数バックオフ付きリトライ"""
        last_exception = None
        delay = self.config.retry_delay

        for attempt in range(self.config.max_retries):
            try:
                return await func(*args, **kwargs)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    logger.warning(f"リトライ {attempt + 1}/{self.config.max_retries}: {e}")
                    await asyncio.sleep(delay)
                    delay *= self.config.backoff_factor
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    retry_after = e.response.headers.get("Retry-After", delay)
                    logger.warning(f"レート制限エラー。{retry_after}秒後にリトライ")
                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(float(retry_after))
                        continue
                raise

        raise last_exception

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        """
        チャット補完APIを呼び出す

        Args:
            messages: チャットメッセージのリスト
            stream: ストリーミングモード（未実装）
            **kwargs: 追加のパラメータ

        Returns:
            LLMレスポンス

        Raises:
            LLMClientError: API呼び出しに失敗した場合
            NotImplementedError: ストリーミングモードが指定された場合
        """
        if stream:
            raise NotImplementedError("ストリーミングモードは未実装です")

        await self._ensure_client()

        # メトリクス記録用のリクエストID生成
        request_id = str(uuid.uuid4())

        # メトリクス記録開始
        if self.metrics_collector:
            self.metrics_collector.start_api_call(request_id=request_id, model_name=self.config.model)

        # リクエストボディを構築
        request_data = self.config.to_dict()
        request_data["messages"] = [msg.to_dict() for msg in messages]
        request_data.update(kwargs)

        try:
            # Task 2.2: 5秒以上の応答時間でプログレスバー表示（Requirement 6.2）
            start_time = time.time()

            # プログレスバー付きAPI呼び出しを作成
            async def api_call_with_progress():
                response_task = self._retry_with_backoff(
                    self._client.post,
                    self.config.api_url,
                    json=request_data,
                    headers=self._get_headers()
                )

                # 5秒待機してから応答をチェック
                try:
                    return await asyncio.wait_for(response_task, timeout=5.0)
                except asyncio.TimeoutError:
                    # 5秒を超えた場合はログを出力
                    logger.info("LLM処理中... (5秒以上かかっています)")

                    # 新しいタスクを作成（再利用問題を回避）
                    new_response_task = self._retry_with_backoff(
                        self._client.post,
                        self.config.api_url,
                        json=request_data,
                        headers=self._get_headers()
                    )
                    try:
                        response = await new_response_task
                        logger.info("LLM処理完了")
                        return response
                    except Exception as e:
                        logger.error(f"LLM処理エラー: {e}")
                        raise

            response = await api_call_with_progress()

            # ステータスコードチェック
            if response.status_code != 200:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "Unknown error")

                # メトリクス記録（エラー）
                if self.metrics_collector:
                    self.metrics_collector.end_api_call(
                        request_id=request_id,
                        success=False,
                        response_tokens=0,
                        error=f"APIエラー ({response.status_code}): {error_message}"
                    )

                if response.status_code == 429:
                    raise LLMClientError(f"レート制限エラー: {error_message}")
                else:
                    raise LLMClientError(f"APIエラー ({response.status_code}): {error_message}")

            # レスポンスをパース
            response_data = response.json()
            llm_response = LLMResponse.from_api_response(response_data)

            # メトリクス記録（成功）
            if self.metrics_collector:
                self.metrics_collector.end_api_call(
                    request_id=request_id,
                    success=True,
                    response_tokens=llm_response.total_tokens,
                    error=None
                )

            # 成功時は連続失敗カウンターをリセット
            self.consecutive_failures = 0
            return llm_response

        except httpx.ConnectError as e:
            # Task 2.2: 連続失敗カウンターの更新
            self.consecutive_failures += 1
            self._check_consecutive_failures()

            # メトリクス記録（接続エラー）
            if self.metrics_collector:
                self.metrics_collector.end_api_call(
                    request_id=request_id,
                    success=False,
                    response_tokens=0,
                    error=f"接続エラー: {e}"
                )
            # Task 2.2: フォールバック情報を含むエラーメッセージ（Requirement 1.4）
            fallback_msg = "埋め込みベースの計算にフォールバックを検討してください。"
            raise LLMClientError(f"vLLM APIへの接続に失敗しました: {e}。{fallback_msg}")
        except httpx.TimeoutException as e:
            # Task 2.2: 連続失敗カウンターの更新
            self.consecutive_failures += 1
            self._check_consecutive_failures()

            # メトリクス記録（タイムアウトエラー）
            if self.metrics_collector:
                self.metrics_collector.end_api_call(
                    request_id=request_id,
                    success=False,
                    response_tokens=0,
                    error=f"タイムアウト: {e}"
                )
            # Task 2.2: フォールバック情報を含むエラーメッセージ（Requirement 1.4）
            fallback_msg = "埋め込みベースの計算にフォールバックを検討してください。"
            raise LLMClientError(f"APIリクエストがタイムアウトしました: {e}。{fallback_msg}")
        except json.JSONDecodeError as e:
            # Task 2.2: 連続失敗カウンターの更新
            self.consecutive_failures += 1
            self._check_consecutive_failures()

            # メトリクス記録（JSON解析エラー）
            if self.metrics_collector:
                self.metrics_collector.end_api_call(
                    request_id=request_id,
                    success=False,
                    response_tokens=0,
                    error=f"JSON解析エラー: {e}"
                )
            raise LLMClientError(f"APIレスポンスの解析に失敗しました: {e}")
        except Exception as e:
            # Task 2.2: 連続失敗カウンターの更新
            self.consecutive_failures += 1
            self._check_consecutive_failures()

            # メトリクス記録（その他のエラー）
            if self.metrics_collector:
                self.metrics_collector.end_api_call(
                    request_id=request_id,
                    success=False,
                    response_tokens=0,
                    error=f"予期しないエラー: {e}"
                )
            if isinstance(e, LLMClientError):
                raise
            raise LLMClientError(f"予期しないエラーが発生しました: {e}")

    async def health_check(self) -> bool:
        """
        APIの健全性をチェック

        Returns:
            APIが利用可能な場合はTrue
        """
        try:
            await self._ensure_client()

            # ヘルスチェックエンドポイントを呼び出し
            # vLLMには専用のヘルスチェックエンドポイントがない場合があるので
            # モデル一覧エンドポイントを使用
            health_url = self.config.api_url.replace("/chat/completions", "/models")

            response = await self._client.get(
                health_url,
                headers=self._get_headers(),
                timeout=5.0  # ヘルスチェックは短めのタイムアウト
            )

            return response.status_code == 200

        except Exception as e:
            logger.warning(f"ヘルスチェックに失敗: {e}")
            return False

    async def list_models(self) -> List[str]:
        """
        利用可能なモデルのリストを取得

        Returns:
            モデル名のリスト
        """
        await self._ensure_client()

        try:
            models_url = self.config.api_url.replace("/chat/completions", "/models")
            response = await self._client.get(
                models_url,
                headers=self._get_headers()
            )

            if response.status_code != 200:
                raise LLMClientError(f"モデル一覧の取得に失敗: {response.status_code}")

            data = response.json()
            models = data.get("data", [])
            return [model.get("id") for model in models if "id" in model]

        except Exception as e:
            logger.error(f"モデル一覧の取得に失敗: {e}")
            return []


async def create_client(config: Optional[LLMConfig] = None) -> LLMClient:
    """
    LLMクライアントを作成（ヘルパー関数）

    Args:
        config: クライアント設定

    Returns:
        初期化されたLLMクライアント
    """
    client = LLMClient(config)
    await client._ensure_client()
    return client