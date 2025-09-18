"""LLMベース類似度計算エンジンのテスト"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

# これから実装するモジュールをインポート
from src.llm_similarity import (
    LLMSimilarity,
    LLMSimilarityError,
    SimilarityResult,
    LLMConfig
)
from src.llm_client import ChatMessage, LLMResponse
from src.prompt_template import PromptTemplate


class TestLLMSimilarity:
    """LLMベース類似度計算のテストクラス"""

    @pytest.fixture
    def mock_llm_client(self):
        """モックLLMクライアントを返すフィクスチャ"""
        client = AsyncMock()
        return client

    @pytest.fixture
    def mock_prompt_template(self):
        """モックプロンプトテンプレートを返すフィクスチャ"""
        template = MagicMock()
        template.load_template.return_value = {
            "prompts": {
                "system": "あなたは類似度判定の専門家です。",
                "user": "テキスト1: {text1}\nテキスト2: {text2}\n\n類似度を評価してください。"
            },
            "parameters": {
                "temperature": 0.2,
                "max_tokens": 64
            }
        }
        template.render.return_value = "テキスト1: サンプル1\nテキスト2: サンプル2\n\n類似度を評価してください。"
        return template

    @pytest.fixture
    def similarity_engine(self, mock_llm_client, mock_prompt_template):
        """LLMSimilarityインスタンスを返すフィクスチャ"""
        return LLMSimilarity(
            llm_client=mock_llm_client,
            prompt_template=mock_prompt_template
        )

    @pytest.mark.asyncio
    async def test_calculate_similarity_success(self, similarity_engine, mock_llm_client):
        """類似度計算の成功テスト"""
        # モックレスポンス
        mock_response = LLMResponse(
            content="スコア: 0.85\nカテゴリ: 非常に類似\n理由: 両テキストは同じ概念を扱っています。",
            model="qwen3-14b-awq",
            total_tokens=45
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # テスト実行
        result = await similarity_engine.calculate_similarity(
            "これはテストテキスト1です",
            "これはテストテキスト2です"
        )

        # アサーション
        assert isinstance(result, SimilarityResult)
        assert result.score == 0.85
        assert result.category == "非常に類似"
        assert result.reason == "両テキストは同じ概念を扱っています。"
        assert result.method == "llm"
        assert result.model_used == "qwen3-14b-awq"
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_batch_processing(self, similarity_engine, mock_llm_client):
        """バッチ処理のテスト"""
        # モックレスポンスを設定
        mock_response = LLMResponse(
            content="スコア: 0.75\nカテゴリ: 類似\n理由: 共通点があります。",
            model="qwen3-14b-awq"
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # テストデータ
        text_pairs = [
            ("テキスト1-1", "テキスト1-2"),
            ("テキスト2-1", "テキスト2-2"),
            ("テキスト3-1", "テキスト3-2")
        ]

        # バッチ処理実行
        results = await similarity_engine.calculate_batch_similarity(text_pairs)

        # アサーション
        assert len(results) == 3
        for result in results:
            assert isinstance(result, SimilarityResult)
            assert result.score == 0.75
            assert result.category == "類似"

        # LLMクライアントが3回呼び出されたことを確認
        assert mock_llm_client.chat_completion.call_count == 3

    @pytest.mark.asyncio
    async def test_model_parameter_override(self, similarity_engine, mock_llm_client):
        """モデルパラメータのオーバーライドテスト"""
        mock_response = LLMResponse(content="スコア: 0.9\nカテゴリ: 非常に類似")
        mock_llm_client.chat_completion.return_value = mock_response

        # カスタムパラメータで実行
        custom_config = {
            "model": "custom-model",
            "temperature": 0.5,
            "max_tokens": 128
        }

        await similarity_engine.calculate_similarity(
            "テキスト1", "テキスト2",
            model_config=custom_config
        )

        # LLMクライアントが正しいパラメータで呼び出されたことを確認
        call_args = mock_llm_client.chat_completion.call_args
        assert "model" in call_args.kwargs
        assert call_args.kwargs["model"] == "custom-model"
        assert call_args.kwargs["temperature"] == 0.5
        assert call_args.kwargs["max_tokens"] == 128

    @pytest.mark.asyncio
    async def test_prompt_template_customization(self, similarity_engine, mock_prompt_template):
        """プロンプトテンプレートのカスタマイズテスト"""
        # カスタムテンプレートファイルを使用
        custom_template_path = "prompts/custom_template.yaml"

        await similarity_engine.set_prompt_template(custom_template_path)

        # プロンプトテンプレートが正しいファイルを読み込んだことを確認
        mock_prompt_template.load_template.assert_called_with(custom_template_path)

    @pytest.mark.asyncio
    async def test_error_handling_llm_failure(self, similarity_engine, mock_llm_client):
        """LLMエラー時のハンドリングテスト"""
        # LLMクライアントでエラーが発生
        mock_llm_client.chat_completion.side_effect = Exception("API Error")

        # エラーが適切に処理されることを確認
        with pytest.raises(LLMSimilarityError, match="LLM推論に失敗"):
            await similarity_engine.calculate_similarity("テキスト1", "テキスト2")

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, similarity_engine, mock_llm_client):
        """不正な形式のレスポンス処理テスト"""
        # 不正な形式のレスポンス
        mock_response = LLMResponse(
            content="これは不正な形式のレスポンスです。スコアがありません。"
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # エラーが発生することを確認
        with pytest.raises(LLMSimilarityError, match="レスポンス解析に失敗"):
            await similarity_engine.calculate_similarity("テキスト1", "テキスト2")

    @pytest.mark.asyncio
    async def test_sequential_processing_rate_limiting(self, similarity_engine, mock_llm_client):
        """シーケンシャル処理によるレート制限対応テスト"""
        mock_response = LLMResponse(content="スコア: 0.8\nカテゴリ: 非常に類似")
        mock_llm_client.chat_completion.return_value = mock_response

        # 複数のタスクを順次処理
        text_pairs = [("t1", "t2"), ("t3", "t4")]

        start_time = asyncio.get_event_loop().time()
        results = await similarity_engine.calculate_batch_similarity(
            text_pairs,
            sequential=True,
            delay_between_requests=0.1
        )
        end_time = asyncio.get_event_loop().time()

        # 順次処理により十分な時間がかかったことを確認
        assert end_time - start_time >= 0.1
        assert len(results) == 2

    def test_validate_texts(self, similarity_engine):
        """テキスト入力のバリデーションテスト"""
        # 空のテキスト
        with pytest.raises(LLMSimilarityError, match="テキスト1が空"):
            similarity_engine._validate_texts("", "テキスト2")

        with pytest.raises(LLMSimilarityError, match="テキスト2が空"):
            similarity_engine._validate_texts("テキスト1", "")

        # 長すぎるテキスト（10000文字制限と仮定）
        long_text = "a" * 10001
        with pytest.raises(LLMSimilarityError, match="テキスト1が長すぎます"):
            similarity_engine._validate_texts(long_text, "テキスト2")

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_llm_client, mock_prompt_template):
        """コンテキストマネージャーのテスト"""
        async with LLMSimilarity(mock_llm_client, mock_prompt_template) as engine:
            mock_response = LLMResponse(content="スコア: 0.9\nカテゴリ: 非常に類似")
            mock_llm_client.chat_completion.return_value = mock_response

            result = await engine.calculate_similarity("テキスト1", "テキスト2")
            assert result.score == 0.9

    @pytest.mark.asyncio
    async def test_fallback_to_embedding_mode(self, similarity_engine, mock_llm_client):
        """埋め込みモードへのフォールバック機能テスト"""
        # 3回連続でエラーが発生
        mock_llm_client.chat_completion.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            Exception("Error 3")
        ]

        # フォールバック機能が有効な場合
        similarity_engine.enable_fallback = True
        similarity_engine.embedding_calculator = MagicMock()
        similarity_engine.embedding_calculator.calculate_similarity.return_value = 0.75

        result = await similarity_engine.calculate_similarity("テキスト1", "テキスト2")

        # 埋め込みモードで計算されたことを確認
        assert result.method == "embedding_fallback"
        assert result.score == 0.75

    def test_get_statistics(self, similarity_engine):
        """統計情報取得のテスト"""
        # 統計データを設定
        similarity_engine._stats = {
            "total_requests": 10,
            "successful_requests": 8,
            "failed_requests": 2,
            "total_processing_time": 15.0,
            "model_usage": {"qwen3-14b-awq": 8, "other-model": 2}
        }

        stats = similarity_engine.get_statistics()

        assert stats["total_requests"] == 10
        assert stats["success_rate"] == 0.8
        assert stats["average_processing_time"] == 1.5
        assert "qwen3-14b-awq" in stats["model_usage"]