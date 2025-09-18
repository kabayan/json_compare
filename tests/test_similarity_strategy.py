"""類似度計算戦略パターンのテスト"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# これから実装するモジュールをインポート
from src.similarity_strategy import (
    SimilarityStrategy,
    EmbeddingSimilarityStrategy,
    LLMSimilarityStrategy,
    SimilarityCalculator,
    StrategyResult,
    StrategyError
)


class TestSimilarityStrategy:
    """類似度計算戦略のテストクラス"""

    def test_strategy_result_creation(self):
        """StrategyResult作成のテスト"""
        result = StrategyResult(
            score=0.85,
            method="llm",
            processing_time=1.5,
            metadata={"model": "qwen3-14b-awq", "confidence": 0.9}
        )

        assert result.score == 0.85
        assert result.method == "llm"
        assert result.processing_time == 1.5
        assert result.metadata["model"] == "qwen3-14b-awq"
        assert result.metadata["confidence"] == 0.9

    def test_strategy_result_to_dict(self):
        """StrategyResult辞書変換のテスト"""
        result = StrategyResult(
            score=0.75,
            method="embedding",
            processing_time=0.5,
            metadata={"field_match_ratio": 0.8}
        )

        result_dict = result.to_dict()

        assert result_dict["score"] == 0.75
        assert result_dict["method"] == "embedding"
        assert result_dict["processing_time"] == 0.5
        assert result_dict["metadata"]["field_match_ratio"] == 0.8


class TestEmbeddingSimilarityStrategy:
    """埋め込みベース類似度戦略のテストクラス"""

    @pytest.fixture
    def embedding_strategy(self):
        """EmbeddingSimilarityStrategyインスタンスを返すフィクスチャ"""
        return EmbeddingSimilarityStrategy()

    @pytest.mark.asyncio
    async def test_calculate_similarity(self, embedding_strategy):
        """埋め込みベース類似度計算のテスト"""
        json1 = '{"name": "田中", "age": 30}'
        json2 = '{"name": "田中太郎", "age": 31}'

        with patch('src.similarity.calculate_json_similarity') as mock_calc:
            mock_calc.return_value = (0.85, {"field_match_ratio": 0.5, "value_similarity": 0.7})

            result = await embedding_strategy.calculate_similarity(json1, json2)

            assert isinstance(result, StrategyResult)
            assert result.score == 0.85
            assert result.method == "embedding"
            assert result.processing_time > 0
            assert result.metadata["field_match_ratio"] == 0.5
            assert result.metadata["value_similarity"] == 0.7

    @pytest.mark.asyncio
    async def test_calculate_similarity_error(self, embedding_strategy):
        """埋め込み計算エラー時のテスト"""
        json1 = 'invalid json'
        json2 = '{"name": "test"}'

        with patch('src.similarity.calculate_json_similarity') as mock_calc:
            mock_calc.side_effect = Exception("Calculation error")

            with pytest.raises(StrategyError, match="埋め込みベース計算に失敗"):
                await embedding_strategy.calculate_similarity(json1, json2)


class TestLLMSimilarityStrategy:
    """LLMベース類似度戦略のテストクラス"""

    @pytest.fixture
    def mock_llm_similarity(self):
        """モックLLMSimilarityを返すフィクスチャ"""
        mock_llm = AsyncMock()
        return mock_llm

    @pytest.fixture
    def llm_strategy(self, mock_llm_similarity):
        """LLMSimilarityStrategyインスタンスを返すフィクスチャ"""
        return LLMSimilarityStrategy(llm_similarity=mock_llm_similarity)

    @pytest.mark.asyncio
    async def test_calculate_similarity(self, llm_strategy, mock_llm_similarity):
        """LLMベース類似度計算のテスト"""
        json1 = '{"task": "データ処理"}'
        json2 = '{"task": "データの処理"}'

        # モックのLLMレスポンス
        from src.llm_similarity import SimilarityResult as LLMResult
        mock_result = LLMResult(
            score=0.9,
            category="非常に類似",
            reason="タスクの内容が非常に近い",
            method="llm",
            model_used="qwen3-14b-awq",
            processing_time=1.2,
            confidence=0.95,
            tokens_used=45
        )
        mock_llm_similarity.calculate_similarity.return_value = mock_result

        result = await llm_strategy.calculate_similarity(json1, json2)

        assert isinstance(result, StrategyResult)
        assert result.score == 0.9
        assert result.method == "llm"
        assert result.processing_time == 1.2
        assert result.metadata["category"] == "非常に類似"
        assert result.metadata["model_used"] == "qwen3-14b-awq"
        assert result.metadata["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_calculate_similarity_error(self, llm_strategy, mock_llm_similarity):
        """LLM計算エラー時のテスト"""
        json1 = '{"test": "data"}'
        json2 = '{"test": "other"}'

        mock_llm_similarity.calculate_similarity.side_effect = Exception("LLM API error")

        with pytest.raises(StrategyError, match="LLMベース計算に失敗"):
            await llm_strategy.calculate_similarity(json1, json2)


class TestSimilarityCalculator:
    """類似度計算機（戦略コンテキスト）のテストクラス"""

    @pytest.fixture
    def mock_embedding_strategy(self):
        """モック埋め込み戦略を返すフィクスチャ"""
        strategy = AsyncMock()
        return strategy

    @pytest.fixture
    def mock_llm_strategy(self):
        """モックLLM戦略を返すフィクスチャ"""
        strategy = AsyncMock()
        return strategy

    @pytest.fixture
    def similarity_calculator(self, mock_embedding_strategy, mock_llm_strategy):
        """SimilarityCalculatorインスタンスを返すフィクスチャ"""
        return SimilarityCalculator(
            embedding_strategy=mock_embedding_strategy,
            llm_strategy=mock_llm_strategy
        )

    @pytest.mark.asyncio
    async def test_calculate_with_embedding_strategy(self, similarity_calculator, mock_embedding_strategy):
        """埋め込み戦略での計算テスト"""
        mock_result = StrategyResult(score=0.75, method="embedding", processing_time=0.5)
        mock_embedding_strategy.calculate_similarity.return_value = mock_result

        result = await similarity_calculator.calculate_similarity(
            '{"a": 1}', '{"a": 2}', method="embedding"
        )

        assert result.score == 0.75
        assert result.method == "embedding"
        mock_embedding_strategy.calculate_similarity.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_with_llm_strategy(self, similarity_calculator, mock_llm_strategy):
        """LLM戦略での計算テスト"""
        mock_result = StrategyResult(score=0.9, method="llm", processing_time=2.0)
        mock_llm_strategy.calculate_similarity.return_value = mock_result

        result = await similarity_calculator.calculate_similarity(
            '{"task": "処理"}', '{"task": "実行"}', method="llm"
        )

        assert result.score == 0.9
        assert result.method == "llm"
        mock_llm_strategy.calculate_similarity.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_with_auto_fallback(self, similarity_calculator, mock_embedding_strategy, mock_llm_strategy):
        """自動フォールバック機能のテスト"""
        # LLM戦略が失敗
        mock_llm_strategy.calculate_similarity.side_effect = StrategyError("LLM failed")

        # 埋め込み戦略が成功
        mock_result = StrategyResult(score=0.6, method="embedding_fallback", processing_time=0.3)
        mock_embedding_strategy.calculate_similarity.return_value = mock_result

        result = await similarity_calculator.calculate_similarity(
            '{"data": "test"}', '{"data": "example"}',
            method="llm",
            fallback_enabled=True
        )

        assert result.score == 0.6
        assert result.method == "embedding_fallback"
        mock_llm_strategy.calculate_similarity.assert_called_once()
        mock_embedding_strategy.calculate_similarity.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_with_auto_strategy_selection(self, similarity_calculator, mock_embedding_strategy):
        """自動戦略選択のテスト"""
        # 短いJSONは埋め込み戦略を使用
        mock_result = StrategyResult(score=0.8, method="embedding", processing_time=0.2)
        mock_embedding_strategy.calculate_similarity.return_value = mock_result

        result = await similarity_calculator.calculate_similarity(
            '{"id": 1}', '{"id": 2}', method="auto"
        )

        assert result.method == "embedding"
        mock_embedding_strategy.calculate_similarity.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_batch_similarity(self, similarity_calculator, mock_embedding_strategy):
        """バッチ類似度計算のテスト"""
        json_pairs = [
            ('{"a": 1}', '{"a": 2}'),
            ('{"b": 3}', '{"b": 4}'),
            ('{"c": 5}', '{"c": 6}')
        ]

        mock_results = [
            StrategyResult(score=0.7, method="embedding", processing_time=0.1),
            StrategyResult(score=0.8, method="embedding", processing_time=0.1),
            StrategyResult(score=0.6, method="embedding", processing_time=0.1)
        ]
        mock_embedding_strategy.calculate_similarity.side_effect = mock_results

        results = await similarity_calculator.calculate_batch_similarity(
            json_pairs, method="embedding"
        )

        assert len(results) == 3
        assert all(r.method == "embedding" for r in results)
        assert [r.score for r in results] == [0.7, 0.8, 0.6]

    def test_get_statistics(self, similarity_calculator):
        """統計情報取得のテスト"""
        # 統計データを設定
        similarity_calculator._stats = {
            "total_calculations": 100,
            "embedding_used": 60,
            "llm_used": 35,
            "fallback_used": 5,
            "failed_calculations": 0,
            "total_processing_time": 150.0
        }

        stats = similarity_calculator.get_statistics()

        assert stats["total_calculations"] == 100
        assert stats["embedding_used"] == 60
        assert stats["llm_used"] == 35
        assert stats["fallback_used"] == 5
        assert stats["success_rate"] == 1.0  # 全て成功
        assert stats["average_processing_time"] == 1.5

    @pytest.mark.asyncio
    async def test_strategy_switching_during_runtime(self, similarity_calculator, mock_embedding_strategy, mock_llm_strategy):
        """実行時戦略切り替えのテスト"""
        # 最初は埋め込み戦略
        mock_embedding_result = StrategyResult(score=0.7, method="embedding", processing_time=0.3)
        mock_embedding_strategy.calculate_similarity.return_value = mock_embedding_result

        result1 = await similarity_calculator.calculate_similarity(
            '{"test": 1}', '{"test": 2}', method="embedding"
        )

        # 戦略をLLMに切り替え
        mock_llm_result = StrategyResult(score=0.9, method="llm", processing_time=1.5)
        mock_llm_strategy.calculate_similarity.return_value = mock_llm_result

        result2 = await similarity_calculator.calculate_similarity(
            '{"task": "処理"}', '{"task": "実行"}', method="llm"
        )

        assert result1.method == "embedding"
        assert result2.method == "llm"

    def test_invalid_strategy_method(self, similarity_calculator):
        """無効な戦略メソッドのテスト"""
        with pytest.raises(StrategyError, match="サポートされていない計算方法"):
            similarity_calculator._validate_method("invalid_method")

    @pytest.mark.asyncio
    async def test_context_manager_support(self, mock_embedding_strategy, mock_llm_strategy):
        """コンテキストマネージャーサポートのテスト"""
        async with SimilarityCalculator(mock_embedding_strategy, mock_llm_strategy) as calculator:
            mock_result = StrategyResult(score=0.8, method="embedding", processing_time=0.4)
            mock_embedding_strategy.calculate_similarity.return_value = mock_result

            result = await calculator.calculate_similarity(
                '{"data": "test"}', '{"data": "example"}', method="embedding"
            )

            assert result.score == 0.8