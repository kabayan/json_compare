"""vLLM APIクライアントのテスト"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import os

# これから実装するモジュールをインポート
from src.llm_client import (
    LLMClient,
    LLMClientError,
    LLMResponse,
    ChatMessage,
    LLMConfig
)


class TestLLMClient:
    """LLMクライアントのテストクラス"""

    @pytest.fixture
    def default_config(self):
        """デフォルト設定を返すフィクスチャ"""
        return LLMConfig(
            api_url="http://192.168.1.18:8000/v1/chat/completions",
            model="qwen3-14b-awq",
            temperature=0.2,
            max_tokens=64,
            timeout=30.0
        )

    @pytest.fixture
    def client(self, default_config):
        """LLMクライアントのインスタンスを返すフィクスチャ"""
        return LLMClient(default_config)

    @pytest.mark.asyncio
    async def test_chat_completion_success(self, client):
        """正常な chat completion のテスト"""
        # モックレスポンス
        mock_response = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "qwen3-14b-awq",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "スコア: 0.85\\nカテゴリ: 非常に類似\\n理由: 両テキストは同じトピックです。"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 9,
                "completion_tokens": 12,
                "total_tokens": 21
            }
        }

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_response
            )

            messages = [
                ChatMessage(role="system", content="あなたは評価者です"),
                ChatMessage(role="user", content="テキストを比較してください")
            ]

            response = await client.chat_completion(messages)

            assert response.id == "chatcmpl-123"
            assert response.content == "スコア: 0.85\\nカテゴリ: 非常に類似\\n理由: 両テキストは同じトピックです。"
            assert response.model == "qwen3-14b-awq"
            assert response.total_tokens == 21

    @pytest.mark.asyncio
    async def test_connection_error(self, client):
        """接続エラーのテスト"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.ConnectError("接続できません")

            messages = [
                ChatMessage(role="user", content="テスト")
            ]

            with pytest.raises(LLMClientError, match="vLLM APIへの接続に失敗"):
                await client.chat_completion(messages)

    @pytest.mark.asyncio
    async def test_timeout_error(self, client):
        """タイムアウトエラーのテスト"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.TimeoutException("タイムアウト")

            messages = [
                ChatMessage(role="user", content="テスト")
            ]

            with pytest.raises(LLMClientError, match="APIリクエストがタイムアウト"):
                await client.chat_completion(messages)

    @pytest.mark.asyncio
    async def test_api_error_response(self, client):
        """APIエラーレスポンスのテスト"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=400,
                json=lambda: {"error": {"message": "Invalid request"}}
            )

            messages = [
                ChatMessage(role="user", content="テスト")
            ]

            with pytest.raises(LLMClientError, match="APIエラー"):
                await client.chat_completion(messages)

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """ヘルスチェックのテスト"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = AsyncMock(
                status_code=200,
                json=lambda: {"status": "healthy"}
            )

            is_healthy = await client.health_check()
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """ヘルスチェック失敗のテスト"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("接続エラー")

            is_healthy = await client.health_check()
            assert is_healthy is False

    def test_environment_variable_config(self):
        """環境変数による設定のテスト"""
        with patch.dict(os.environ, {'VLLM_API_URL': 'http://localhost:8000/v1/chat/completions'}):
            config = LLMConfig.from_environment()
            assert config.api_url == 'http://localhost:8000/v1/chat/completions'

    def test_config_validation(self):
        """設定バリデーションのテスト"""
        # 不正な温度パラメータ
        with pytest.raises(ValueError, match="temperature"):
            LLMConfig(
                api_url="http://test.com",
                temperature=1.5  # 範囲外
            )

        # 不正な最大トークン数
        with pytest.raises(ValueError, match="max_tokens"):
            LLMConfig(
                api_url="http://test.com",
                max_tokens=-1  # 負の値
            )

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, client):
        """リトライメカニズムのテスト"""
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("一時的なエラー")
            return AsyncMock(
                status_code=200,
                json=lambda: {
                    "choices": [{
                        "message": {"content": "成功"}
                    }]
                }
            )

        with patch('httpx.AsyncClient.post', new=mock_post):
            client.config.max_retries = 3

            messages = [ChatMessage(role="user", content="テスト")]
            response = await client.chat_completion(messages)

            assert call_count == 3
            assert response.content == "成功"

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, client):
        """レート制限エラーのハンドリングテスト"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=429,
                headers={"Retry-After": "2"},
                json=lambda: {"error": {"message": "Rate limit exceeded"}}
            )

            messages = [ChatMessage(role="user", content="テスト")]

            with pytest.raises(LLMClientError, match="レート制限"):
                await client.chat_completion(messages)

    def test_message_serialization(self):
        """メッセージのシリアライゼーションテスト"""
        message = ChatMessage(role="user", content="こんにちは")
        serialized = message.to_dict()

        assert serialized["role"] == "user"
        assert serialized["content"] == "こんにちは"

    @pytest.mark.asyncio
    async def test_custom_headers(self):
        """カスタムヘッダーのテスト"""
        config = LLMConfig(
            api_url="http://test.com",
            auth_token="test-token"
        )
        client = LLMClient(config)

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: {
                    "choices": [{
                        "message": {"content": "テスト"}
                    }]
                }
            )

            messages = [ChatMessage(role="user", content="テスト")]
            await client.chat_completion(messages)

            # Authorizationヘッダーが正しく設定されているか確認
            call_args = mock_post.call_args
            assert "headers" in call_args.kwargs
            assert call_args.kwargs["headers"]["Authorization"] == "Bearer test-token"

    @pytest.mark.asyncio
    async def test_streaming_not_supported(self, client):
        """ストリーミングがサポートされていないことのテスト"""
        messages = [ChatMessage(role="user", content="テスト")]

        with pytest.raises(NotImplementedError, match="ストリーミング"):
            await client.chat_completion(messages, stream=True)

    @pytest.mark.asyncio
    async def test_api_response_time_metrics_logging(self, client):
        """API応答時間のメトリクスログ記録テスト（Requirement 6.1）"""
        # モックレスポンス
        mock_response = {
            "id": "chatcmpl-metrics-test",
            "choices": [{
                "message": {"content": "テスト応答"},
                "finish_reason": "stop"
            }],
            "usage": {"total_tokens": 10}
        }

        with patch('httpx.AsyncClient.post') as mock_post, \
             patch('src.llm_client.LLMMetricsCollector') as mock_metrics_class:

            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_response
            )

            # モックメトリクスコレクター
            mock_metrics = AsyncMock()
            mock_metrics_class.return_value = mock_metrics

            # クライアントにメトリクスコレクターを注入
            client.metrics_collector = mock_metrics

            messages = [ChatMessage(role="user", content="メトリクステスト")]
            response = await client.chat_completion(messages)

            # メトリクス記録が呼び出されたかを確認
            mock_metrics.start_api_call.assert_called_once()
            mock_metrics.end_api_call.assert_called_once()

            # start_api_callの引数確認
            start_call_args = mock_metrics.start_api_call.call_args[1]
            assert start_call_args["model_name"] == "qwen3-14b-awq"

            # end_api_callの引数確認
            end_call_args = mock_metrics.end_api_call.call_args[1]
            assert end_call_args["success"] is True
            assert end_call_args["response_tokens"] == 10

    # Task 2.2 特化テスト: APIレスポンス処理とエラー管理
    @pytest.mark.asyncio
    async def test_slow_response_progress_display(self, client):
        """5秒以上の応答時間でプログレスバー表示（Requirement 6.2）"""
        mock_response = {
            "choices": [{"message": {"content": "遅いレスポンス"}}],
            "usage": {"total_tokens": 5}
        }

        async def slow_response(*args, **kwargs):
            # 6秒の遅延をシミュレート
            await asyncio.sleep(6)
            return AsyncMock(status_code=200, json=lambda: mock_response)

        with patch('httpx.AsyncClient.post', new=slow_response), \
             patch('src.llm_client.tqdm') as mock_tqdm:

            # tqdmモックを設定
            mock_progress = MagicMock()
            mock_tqdm.return_value.__aenter__.return_value = mock_progress

            messages = [ChatMessage(role="user", content="遅いテスト")]
            response = await client.chat_completion(messages)

            # プログレスバーが作成されたことを確認
            mock_tqdm.assert_called_once()
            call_args = mock_tqdm.call_args[1]
            assert "LLM処理中" in call_args["desc"]

    @pytest.mark.asyncio
    async def test_connection_failure_fallback_available(self, client):
        """接続失敗時のフォールバックオプション提供（Requirement 1.4）"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.ConnectError("接続失敗")

            messages = [ChatMessage(role="user", content="フォールバックテスト")]

            # フォールバック情報を含むエラーが発生することを確認
            with pytest.raises(LLMClientError) as exc_info:
                await client.chat_completion(messages)

            error_message = str(exc_info.value)
            assert "フォールバック" in error_message or "fallback" in error_message.lower()

    @pytest.mark.asyncio
    async def test_consecutive_failures_trigger_fallback(self, client):
        """3回連続失敗でフォールバック推奨（Requirement 6.3）"""
        # クライアントに失敗カウンターを追加
        client.consecutive_failures = 0

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.ConnectError("連続失敗")

            messages = [ChatMessage(role="user", content="連続失敗テスト")]

            # 3回連続で失敗させる
            for i in range(3):
                with pytest.raises(LLMClientError):
                    await client.chat_completion(messages)

            # 3回目の失敗後にフォールバック推奨フラグが設定されることを確認
            assert hasattr(client, 'should_fallback_to_embedding')
            assert client.should_fallback_to_embedding is True

    @pytest.mark.asyncio
    async def test_enhanced_rate_limit_backoff(self, client):
        """レート制限エラーの指数バックオフリトライ（Requirement 6.4）"""
        call_count = 0
        backoff_delays = []

        async def rate_limited_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # 最初の2回はレート制限エラー
                error_response = MagicMock()
                error_response.status_code = 429
                error_response.headers = {"Retry-After": "2"}
                error_response.json.return_value = {"error": {"message": "Rate limited"}}
                # HTTPStatusErrorを発生させる
                raise httpx.HTTPStatusError(
                    "Rate limited",
                    request=MagicMock(),
                    response=error_response
                )
            else:
                # 3回目は成功
                success_response = MagicMock()
                success_response.status_code = 200
                success_response.json.return_value = {"choices": [{"message": {"content": "成功"}}]}
                return success_response

        # asyncio.sleepをモックして遅延時間を記録
        original_sleep = asyncio.sleep
        async def mock_sleep(delay):
            backoff_delays.append(delay)
            # 実際には待機しない（テスト高速化）
            pass

        with patch('httpx.AsyncClient.post', new=rate_limited_response), \
             patch('asyncio.sleep', new=mock_sleep):

            client.config.max_retries = 3
            client.config.retry_delay = 1.0
            client.config.backoff_factor = 2.0

            messages = [ChatMessage(role="user", content="レート制限テスト")]
            response = await client.chat_completion(messages)

            # リトライが発生し、指数バックオフが適用されたことを確認
            assert call_count == 3
            assert len(backoff_delays) >= 2  # 少なくとも2回のバックオフ
            # Retry-Afterヘッダーの値（2秒）が使用されることを確認
            assert 2.0 in backoff_delays