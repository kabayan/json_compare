"""Task 4.1: 類似度計算戦略の切り替えシステムの統合テスト

Task 4.1専用のテストスイート。
Requirements 1.1, 1.2, 1.4, 6.3の統合的検証。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from src.similarity_strategy import (
    SimilarityCalculator,
    LLMSimilarityStrategy,
    EmbeddingSimilarityStrategy,
    StrategyResult,
    StrategyError
)
from src.llm_similarity import LLMSimilarityError


class TestTask41StrategySwitching:
    """Task 4.1: 類似度計算戦略の切り替えシステムの統合テストクラス"""

    @pytest.fixture
    def task_4_1_calculator(self):
        """Task 4.1専用のSimilarityCalculatorインスタンス"""
        calculator = SimilarityCalculator()
        calculator.reset_statistics()  # 各テストで統計をリセット
        return calculator

    @pytest.mark.asyncio
    async def test_requirement_1_1_llm_based_similarity_execution(self, task_4_1_calculator):
        """
        Requirement 1.1: vLLM APIを使用したLLMベースの類似度判定を実行

        Task 4.1: 埋め込みモードとLLMモードの動的切り替え機能を実装
        """
        json1 = '{"task": "データ処理を実行する"}'
        json2 = '{"task": "データの処理を行う"}'

        # LLM戦略が呼び出されることを確認
        with patch.object(task_4_1_calculator.llm_strategy, 'calculate_similarity') as mock_llm:
            mock_llm.return_value = StrategyResult(
                score=0.92,
                method="llm",
                processing_time=1.5,
                metadata={
                    "category": "非常に類似",
                    "model_used": "qwen3-14b-awq",
                    "confidence": 0.95
                }
            )

            # Requirement 1.1: LLMモードで実行
            result = await task_4_1_calculator.calculate_similarity(
                json1, json2, method="llm"
            )

            # LLM戦略が使用されたことを確認
            assert result.method == "llm"
            assert result.score == 0.92
            assert result.metadata["model_used"] == "qwen3-14b-awq"
            mock_llm.assert_called_once_with(json1, json2)

    @pytest.mark.asyncio
    async def test_requirement_1_2_embedding_based_default_execution(self, task_4_1_calculator):
        """
        Requirement 1.2: フラグが指定されていない場合、既存の埋め込みベース計算を実行

        Task 4.1: 既存の類似度計算システムとの統合を実現
        """
        json1 = '{"name": "田中", "age": 30}'
        json2 = '{"name": "佐藤", "age": 32}'

        # 埋め込み戦略が呼び出されることを確認
        with patch.object(task_4_1_calculator.embedding_strategy, 'calculate_similarity') as mock_embedding:
            mock_embedding.return_value = StrategyResult(
                score=0.75,
                method="embedding",
                processing_time=0.3,
                metadata={
                    "field_match_ratio": 0.8,
                    "value_similarity": 0.7
                }
            )

            # Requirement 1.2: デフォルト（埋め込み）モードで実行
            result = await task_4_1_calculator.calculate_similarity(
                json1, json2, method="embedding"
            )

            # 埋め込み戦略が使用されたことを確認
            assert result.method == "embedding"
            assert result.score == 0.75
            assert result.metadata["field_match_ratio"] == 0.8
            mock_embedding.assert_called_once_with(json1, json2)

    @pytest.mark.asyncio
    async def test_requirement_1_4_llm_connection_failure_fallback(self, task_4_1_calculator):
        """
        Requirement 1.4: vLLM APIへの接続が失敗した場合、埋め込みベースの計算にフォールバック

        Task 4.1: フォールバック機能と自動切り替えロジックを構築
        """
        json1 = '{"description": "システムの説明文です"}'
        json2 = '{"description": "システムについての説明です"}'

        # LLM戦略が失敗し、埋め込み戦略が成功
        with patch.object(task_4_1_calculator.llm_strategy, 'calculate_similarity') as mock_llm, \
             patch.object(task_4_1_calculator.embedding_strategy, 'calculate_similarity') as mock_embedding:

            # LLM戦略が接続エラーで失敗
            mock_llm.side_effect = StrategyError("vLLM API接続に失敗しました")

            # 埋め込み戦略が成功
            mock_embedding.return_value = StrategyResult(
                score=0.68,
                method="embedding_fallback",
                processing_time=0.4,
                metadata={"fallback_reason": "llm_connection_failed"}
            )

            # Requirement 1.4: LLMモードで開始し、フォールバックが発生
            result = await task_4_1_calculator.calculate_similarity(
                json1, json2, method="llm", fallback_enabled=True
            )

            # フォールバックが正常に動作したことを確認
            assert result.method == "embedding_fallback"
            assert result.score == 0.68
            mock_llm.assert_called_once()
            mock_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_requirement_6_3_consecutive_failure_automatic_fallback(self, task_4_1_calculator):
        """
        Requirement 6.3: API呼び出しが3回連続で失敗した場合、自動的に埋め込みベースモードにフォールバック

        Task 4.1: 戦略選択のためのインターフェース統一を実装
        """
        json_pairs = [
            ('{"task": "処理1"}', '{"task": "実行1"}'),
            ('{"task": "処理2"}', '{"task": "実行2"}'),
            ('{"task": "処理3"}', '{"task": "実行3"}'),
            ('{"task": "処理4"}', '{"task": "実行4"}')  # 4回目は成功するはず
        ]

        with patch.object(task_4_1_calculator.llm_strategy, 'calculate_similarity') as mock_llm, \
             patch.object(task_4_1_calculator.embedding_strategy, 'calculate_similarity') as mock_embedding:

            # 最初の3回はLLMが失敗
            mock_llm.side_effect = [
                StrategyError("LLM API error 1"),
                StrategyError("LLM API error 2"),
                StrategyError("LLM API error 3"),
                StrategyResult(score=0.9, method="llm", processing_time=1.0)  # 4回目は成功
            ]

            # 埋め込み戦略は常に成功
            mock_embedding.return_value = StrategyResult(
                score=0.7,
                method="embedding_fallback",
                processing_time=0.2
            )

            results = []
            for json1, json2 in json_pairs:
                try:
                    result = await task_4_1_calculator.calculate_similarity(
                        json1, json2, method="llm", fallback_enabled=True
                    )
                    results.append(result)
                except Exception as e:
                    # 予期しないエラーが発生した場合
                    results.append(StrategyResult(
                        score=0.0, method="error", metadata={"error": str(e)}
                    ))

            # Requirement 6.3: 3回連続失敗でフォールバックが発生
            assert len(results) == 4
            # 最初の3回はフォールバック
            for i in range(3):
                assert results[i].method == "embedding_fallback"

            # 埋め込み戦略が3回呼び出されている（フォールバック）
            assert mock_embedding.call_count == 3

    @pytest.mark.asyncio
    async def test_task_4_1_dynamic_strategy_switching_integration(self, task_4_1_calculator):
        """
        Task 4.1: 動的戦略切り替えの統合テスト

        埋め込みモードとLLMモードの動的切り替え機能の包括的検証
        """
        test_cases = [
            # ケース1: 短いJSONは埋め込み戦略を選択
            ('{"id": 1}', '{"id": 2}', "auto", "embedding"),
            # ケース2: 長いJSONまたはsemanticキーワードはLLM戦略を選択
            ('{"task": "大量のデータを処理する複雑なタスク"}', '{"task": "複雑なデータ処理タスク"}', "auto", "llm"),
            # ケース3: 明示的な指定
            ('{"name": "test"}', '{"name": "example"}', "embedding", "embedding"),
            ('{"description": "説明"}', '{"description": "詳細"}', "llm", "llm")
        ]

        with patch.object(task_4_1_calculator.llm_strategy, 'calculate_similarity') as mock_llm, \
             patch.object(task_4_1_calculator.embedding_strategy, 'calculate_similarity') as mock_embedding:

            # モック戦略の設定
            mock_embedding.return_value = StrategyResult(score=0.75, method="embedding", processing_time=0.2)
            mock_llm.return_value = StrategyResult(score=0.85, method="llm", processing_time=1.0)

            for json1, json2, method, expected_method in test_cases:
                result = await task_4_1_calculator.calculate_similarity(
                    json1, json2, method=method
                )

                # 期待される戦略が選択されたことを確認
                assert result.method == expected_method

        # 統計情報の確認
        stats = task_4_1_calculator.get_statistics()
        assert stats["total_calculations"] == 4
        assert stats["embedding_used"] >= 2  # 埋め込み戦略が使用された
        assert stats["llm_used"] >= 2  # LLM戦略が使用された

    @pytest.mark.asyncio
    async def test_task_4_1_strategy_interface_unification(self, task_4_1_calculator):
        """
        Task 4.1: 戦略選択のためのインターフェース統一を実装

        すべての戦略が同一のインターフェースで動作することを確認
        """
        json1 = '{"content": "テストデータ"}'
        json2 = '{"content": "テスト内容"}'

        # 両戦略の結果形式が統一されていることを確認
        with patch.object(task_4_1_calculator.llm_strategy, 'calculate_similarity') as mock_llm, \
             patch.object(task_4_1_calculator.embedding_strategy, 'calculate_similarity') as mock_embedding:

            # 両戦略とも同一のインターフェース（StrategyResult）を返す
            mock_embedding.return_value = StrategyResult(
                score=0.70, method="embedding", processing_time=0.15,
                metadata={"algorithm": "cosine_similarity"}
            )
            mock_llm.return_value = StrategyResult(
                score=0.80, method="llm", processing_time=1.20,
                metadata={"model": "qwen3-14b-awq", "confidence": 0.9}
            )

            # 埋め込み戦略でのテスト
            embedding_result = await task_4_1_calculator.calculate_similarity(
                json1, json2, method="embedding"
            )

            # LLM戦略でのテスト
            llm_result = await task_4_1_calculator.calculate_similarity(
                json1, json2, method="llm"
            )

            # インターフェースの統一性確認
            for result in [embedding_result, llm_result]:
                assert hasattr(result, 'score')
                assert hasattr(result, 'method')
                assert hasattr(result, 'processing_time')
                assert hasattr(result, 'metadata')
                assert isinstance(result.score, float)
                assert isinstance(result.method, str)
                assert isinstance(result.processing_time, float)
                assert isinstance(result.metadata, dict)

            # 結果の変換可能性確認
            embedding_dict = embedding_result.to_dict()
            llm_dict = llm_result.to_dict()

            for result_dict in [embedding_dict, llm_dict]:
                assert 'score' in result_dict
                assert 'method' in result_dict
                assert 'processing_time' in result_dict
                assert 'metadata' in result_dict

    @pytest.mark.asyncio
    async def test_task_4_1_fallback_mechanism_comprehensive(self, task_4_1_calculator):
        """
        Task 4.1: フォールバック機能の包括的テスト

        様々な失敗シナリオでのフォールバック動作を検証
        """
        # 統計をリセットして確実に分離
        task_4_1_calculator.reset_statistics()

        json1 = '{"system": "メインシステム"}'
        json2 = '{"system": "バックアップシステム"}'

        failure_scenarios = [
            LLMSimilarityError("API接続タイムアウト"),
            StrategyError("認証失敗"),
            Exception("予期しないエラー"),
        ]

        with patch.object(task_4_1_calculator.embedding_strategy, 'calculate_similarity') as mock_embedding:
            mock_embedding.return_value = StrategyResult(
                score=0.65, method="embedding_fallback", processing_time=0.25
            )

            for i, error in enumerate(failure_scenarios):
                with patch.object(task_4_1_calculator.llm_strategy, 'calculate_similarity') as mock_llm:
                    mock_llm.side_effect = error

                    # フォールバック有効でテスト
                    result = await task_4_1_calculator.calculate_similarity(
                        json1, json2, method="llm", fallback_enabled=True
                    )

                    # フォールバックが正常に動作
                    assert result.method == "embedding_fallback"
                    assert result.score == 0.65

        # フォールバック統計の確認
        stats = task_4_1_calculator.get_statistics()
        assert stats["fallback_used"] == len(failure_scenarios)

    @pytest.mark.asyncio
    async def test_task_4_1_error_handling_without_fallback(self, task_4_1_calculator):
        """
        Task 4.1: フォールバック無効時のエラーハンドリング

        フォールバックが無効な場合の適切なエラー処理を確認
        """
        # 統計をリセットして確実に分離
        task_4_1_calculator.reset_statistics()

        json1 = '{"data": "テストデータ"}'
        json2 = '{"data": "検証データ"}'

        with patch.object(task_4_1_calculator.llm_strategy, 'calculate_similarity') as mock_llm:
            mock_llm.side_effect = StrategyError("LLM API complete failure")

            # フォールバック無効でテスト
            with pytest.raises(StrategyError, match="LLM API complete failure"):
                await task_4_1_calculator.calculate_similarity(
                    json1, json2, method="llm", fallback_enabled=False
                )

        # エラー統計の確認
        stats = task_4_1_calculator.get_statistics()
        assert stats["failed_calculations"] == 1
        assert stats["fallback_used"] == 0  # フォールバック未使用