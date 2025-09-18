"""Task 3.1: LLMベース類似度判定コア機能の統合テスト

Task 3.1専用のテストスイート。
Requirements 1.1, 3.1, 3.2, 3.3, 3.4, 6.5の統合的検証。
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from src.llm_similarity import LLMSimilarity, SimilarityResult, LLMSimilarityError
from src.llm_client import LLMClient, LLMConfig, ChatMessage, LLMResponse
from src.prompt_template import PromptTemplate
from src.similarity_strategy import SimilarityCalculator, LLMSimilarityStrategy, EmbeddingSimilarityStrategy


class TestTask31SimilarityEngine:
    """Task 3.1: LLMベース類似度判定コア機能の統合テストクラス"""

    @pytest.fixture
    def mock_llm_client(self):
        """モックLLMクライアントフィクスチャ"""
        client = AsyncMock()
        # Requirement 3.1: デフォルトでqwen3-14b-awqモデルを使用
        client.config = LLMConfig(model="qwen3-14b-awq")
        return client

    @pytest.fixture
    def task_3_1_similarity_engine(self, mock_llm_client):
        """Task 3.1専用のLLMSimilarityエンジン"""
        return LLMSimilarity(llm_client=mock_llm_client)

    @pytest.mark.asyncio
    async def test_requirement_1_1_llm_api_integration(self, task_3_1_similarity_engine, mock_llm_client):
        """
        Requirement 1.1: vLLM APIを使用したLLMベースの類似度判定を実行

        Task 3.1: LLMを使用した類似度判定のメインロジックを実装
        """
        # モックLLMレスポンスを設定
        mock_response = LLMResponse(
            content="スコア: 0.87\nカテゴリ: 非常に類似\n理由: 両テキストは類似した概念を扱っています。",
            model="qwen3-14b-awq",
            total_tokens=42
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # LLMベース類似度判定を実行
        result = await task_3_1_similarity_engine.calculate_similarity(
            "JSONデータの構造を比較する",
            "データ構造の類似性を評価する"
        )

        # Requirement 1.1の検証
        assert isinstance(result, SimilarityResult)
        assert result.method == "llm"
        assert result.score == 0.87
        assert result.model_used == "qwen3-14b-awq"
        assert "類似した概念" in result.reason

        # LLMクライアントが正しく呼び出されたことを確認
        mock_llm_client.chat_completion.assert_called_once()
        call_args = mock_llm_client.chat_completion.call_args[0]
        messages = call_args[0]
        assert len(messages) >= 1
        assert any("JSONデータの構造を比較する" in msg.content for msg in messages)

    @pytest.mark.asyncio
    async def test_requirement_3_1_default_model_usage(self, task_3_1_similarity_engine, mock_llm_client):
        """
        Requirement 3.1: デフォルトでqwen3-14b-awqモデルを使用

        Task 3.1: モデル選択とパラメータ設定機能を実装
        """
        mock_response = LLMResponse(
            content="スコア: 0.75\nカテゴリ: 類似",
            model="qwen3-14b-awq",
            total_tokens=35
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # デフォルトモデルでの計算
        result = await task_3_1_similarity_engine.calculate_similarity(
            "テストテキスト1",
            "テストテキスト2"
        )

        # Requirement 3.1の検証
        assert result.model_used == "qwen3-14b-awq"

        # LLMクライアントの設定確認
        assert mock_llm_client.config.model == "qwen3-14b-awq"

    @pytest.mark.asyncio
    async def test_requirement_3_2_custom_model_selection(self, task_3_1_similarity_engine, mock_llm_client):
        """
        Requirement 3.2: --model オプションで指定されたモデル名を使用

        Task 3.1: モデル選択とパラメータ設定機能を実装
        """
        mock_response = LLMResponse(
            content="スコア: 0.82\nカテゴリ: 非常に類似",
            model="custom-llm-model",
            total_tokens=38
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # カスタムモデル設定で計算
        custom_model_config = {
            "model": "custom-llm-model"
        }

        result = await task_3_1_similarity_engine.calculate_similarity(
            "カスタムモデルテスト1",
            "カスタムモデルテスト2",
            model_config=custom_model_config
        )

        # Requirement 3.2の検証
        assert result.model_used == "custom-llm-model"

        # API呼び出しでカスタムモデルが使用されたことを確認
        call_kwargs = mock_llm_client.chat_completion.call_args[1]
        assert "model" in call_kwargs
        assert call_kwargs["model"] == "custom-llm-model"

    @pytest.mark.asyncio
    async def test_requirement_3_3_temperature_parameter_control(self, task_3_1_similarity_engine, mock_llm_client):
        """
        Requirement 3.3: --temperature オプションで温度パラメータを適用

        Task 3.1: モデル選択とパラメータ設定機能を実装
        """
        mock_response = LLMResponse(
            content="スコア: 0.91\nカテゴリ: 非常に類似",
            model="qwen3-14b-awq"
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # 温度パラメータを設定して計算
        temperature_config = {
            "temperature": 0.7
        }

        await task_3_1_similarity_engine.calculate_similarity(
            "温度パラメータテスト1",
            "温度パラメータテスト2",
            model_config=temperature_config
        )

        # Requirement 3.3の検証
        call_kwargs = mock_llm_client.chat_completion.call_args[1]
        assert "temperature" in call_kwargs
        assert call_kwargs["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_requirement_3_4_max_tokens_parameter_control(self, task_3_1_similarity_engine, mock_llm_client):
        """
        Requirement 3.4: --max-tokens オプションで最大トークン数を設定

        Task 3.1: モデル選択とパラメータ設定機能を実装
        """
        mock_response = LLMResponse(
            content="スコア: 0.83\nカテゴリ: 非常に類似",
            model="qwen3-14b-awq"
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # 最大トークン数を設定して計算
        max_tokens_config = {
            "max_tokens": 128
        }

        await task_3_1_similarity_engine.calculate_similarity(
            "最大トークン数テスト1",
            "最大トークン数テスト2",
            model_config=max_tokens_config
        )

        # Requirement 3.4の検証
        call_kwargs = mock_llm_client.chat_completion.call_args[1]
        assert "max_tokens" in call_kwargs
        assert call_kwargs["max_tokens"] == 128

    @pytest.mark.asyncio
    async def test_requirement_6_5_sequential_processing_for_large_files(self, task_3_1_similarity_engine, mock_llm_client):
        """
        Requirement 6.5: 大量ファイル処理でAPI呼び出しを順次処理

        Task 3.1: 大量ファイル処理での順次実行メカニズムを構築
        """
        # モックレスポンスを設定
        mock_response = LLMResponse(
            content="スコア: 0.75\nカテゴリ: 類似",
            model="qwen3-14b-awq"
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # 大量ファイル（5ペア）のバッチ処理テスト
        text_pairs = [
            (f"大量ファイルテスト1-{i}", f"大量ファイルテスト2-{i}")
            for i in range(5)
        ]

        # 開始時間を記録
        start_time = time.time()

        # 順次処理でバッチ計算を実行
        results = await task_3_1_similarity_engine.calculate_batch_similarity(
            text_pairs,
            sequential=True,  # Requirement 6.5: 順次処理
            delay_between_requests=0.1  # レート制限回避のための遅延
        )

        end_time = time.time()

        # Requirement 6.5の検証
        assert len(results) == 5

        # 順次処理により適切な時間がかかったことを確認
        processing_time = end_time - start_time
        expected_min_time = 0.1 * (len(text_pairs) - 1)  # 遅延時間の合計
        assert processing_time >= expected_min_time

        # LLMクライアントが5回順次呼び出されたことを確認
        assert mock_llm_client.chat_completion.call_count == 5

        # 全ての結果が正常に処理されたことを確認
        for result in results:
            assert isinstance(result, SimilarityResult)
            assert result.score == 0.75
            assert result.method == "llm"

    @pytest.mark.asyncio
    async def test_task_3_1_integrated_text_embedding_in_prompts(self, task_3_1_similarity_engine, mock_llm_client):
        """
        Task 3.1: 比較対象テキストのプロンプトへの埋め込み処理を構築

        統合テスト: テキストがプロンプトに正しく埋め込まれることを検証
        """
        mock_response = LLMResponse(
            content="スコア: 0.89\nカテゴリ: 非常に類似\n理由: 構造が類似している。",
            model="qwen3-14b-awq"
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # 特定のテキストペアで類似度計算
        text1 = "JSON構造: {\"name\": \"太郎\", \"age\": 30}"
        text2 = "JSON構造: {\"name\": \"花子\", \"age\": 25}"

        await task_3_1_similarity_engine.calculate_similarity(text1, text2)

        # プロンプトへの正しいテキスト埋め込みを検証
        call_args = mock_llm_client.chat_completion.call_args[0]
        messages = call_args[0]

        # ユーザーメッセージに両方のテキストが含まれることを確認
        user_message = None
        for msg in messages:
            if msg.role == "user":
                user_message = msg
                break

        assert user_message is not None
        assert text1 in user_message.content
        assert text2 in user_message.content

    @pytest.mark.asyncio
    async def test_task_3_1_comprehensive_parameter_integration(self, task_3_1_similarity_engine, mock_llm_client):
        """
        Task 3.1: 全要件の統合テスト

        Requirements 1.1, 3.1, 3.2, 3.3, 3.4の統合的検証
        """
        mock_response = LLMResponse(
            content="スコア: 0.94\nカテゴリ: 完全一致\n理由: 完全に同じ内容です。",
            model="advanced-model-v2",
            total_tokens=55
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # 全パラメータを設定した統合テスト
        comprehensive_config = {
            "model": "advanced-model-v2",  # Requirement 3.2
            "temperature": 0.3,           # Requirement 3.3
            "max_tokens": 256            # Requirement 3.4
        }

        result = await task_3_1_similarity_engine.calculate_similarity(
            "統合テストデータ1",
            "統合テストデータ1",  # 同じテキストで完全一致を期待
            model_config=comprehensive_config
        )

        # 統合的検証
        # Requirement 1.1: LLMベース判定の実行
        assert result.method == "llm"
        assert result.score == 0.94

        # Requirements 3.2, 3.3, 3.4: パラメータの適用
        call_kwargs = mock_llm_client.chat_completion.call_args[1]
        assert call_kwargs["model"] == "advanced-model-v2"
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["max_tokens"] == 256

        # LLMレスポンスの正しい解析
        assert result.category == "完全一致"
        assert result.reason == "完全に同じ内容です。"
        assert result.model_used == "advanced-model-v2"
        assert result.tokens_used == 55

    @pytest.mark.asyncio
    async def test_task_3_1_error_handling_with_fallback_suggestion(self, task_3_1_similarity_engine, mock_llm_client):
        """
        Task 3.1: エラーハンドリングとフォールバック提案の統合テスト

        LLM計算失敗時の適切なエラー処理を検証
        """
        # LLMクライアントでエラーを発生させる
        mock_llm_client.chat_completion.side_effect = Exception("vLLM API connection failed")

        # エラーが適切に処理されることを確認
        with pytest.raises(LLMSimilarityError, match="LLM推論に失敗"):
            await task_3_1_similarity_engine.calculate_similarity(
                "エラーテスト1",
                "エラーテスト2"
            )

    @pytest.mark.asyncio
    async def test_task_3_1_strategy_integration(self):
        """
        Task 3.1: 戦略パターンとの統合テスト

        SimilarityCalculatorを使用したLLM戦略の統合検証
        """
        # モックLLMクライアントを設定
        mock_llm_client = AsyncMock()
        mock_response = LLMResponse(
            content="スコア: 0.78\nカテゴリ: 類似",
            model="qwen3-14b-awq"
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # LLM戦略を使用したSimilarityCalculator
        llm_similarity = LLMSimilarity(llm_client=mock_llm_client)
        llm_strategy = LLMSimilarityStrategy(llm_similarity=llm_similarity)

        calculator = SimilarityCalculator(
            embedding_strategy=EmbeddingSimilarityStrategy(),
            llm_strategy=llm_strategy
        )

        # LLMモードで類似度計算
        result = await calculator.calculate_similarity(
            '{"test": "data1"}',
            '{"test": "data2"}',
            method="llm"
        )

        # 戦略パターンとの統合検証
        assert result.method == "llm"
        assert result.score == 0.78
        assert isinstance(result.processing_time, float)
        assert result.processing_time > 0