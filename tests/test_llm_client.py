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