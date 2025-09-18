"""Task 4.2: 比較方法識別とメタデータ拡張機能の統合テスト

Task 4.2専用のテストスイート。
Requirements 8.1, 8.3, 8.4, 6.1の統合的検証。
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from typing import Dict, Any, Optional

from src.enhanced_result_format import (
    EnhancedResult,
    ResultFormatter,
    MetadataCollector,
    CompatibilityLayer,
    LLMMetadata,
    PerformanceMetrics,
    create_enhanced_result_from_strategy
)
from src.similarity_strategy import StrategyResult


class TestTask42MetadataEnhancement:
    """Task 4.2: 比較方法識別とメタデータ拡張機能の統合テストクラス"""

    @pytest.fixture
    def task_4_2_formatter(self):
        """Task 4.2専用のResultFormatterインスタンス"""
        return ResultFormatter()

    @pytest.fixture
    def task_4_2_compatibility(self):
        """Task 4.2専用のCompatibilityLayerインスタンス"""
        return CompatibilityLayer()

    @pytest.fixture
    def task_4_2_metadata_collector(self):
        """Task 4.2専用のMetadataCollectorインスタンス"""
        return MetadataCollector()

    def test_requirement_8_1_comparison_method_identification(self, task_4_2_formatter):
        """
        Requirement 8.1: 使用した判定方式の明示的識別機能を実装

        Task 4.2: 使用した判定方式の明示的識別機能を実装
        """
        # テストケース: 埋め込みモード
        embedding_result = StrategyResult(
            score=0.75,
            method="embedding",
            processing_time=0.3,
            metadata={
                "field_match_ratio": 0.8,
                "value_similarity": 0.7,
                "algorithm": "cosine_similarity",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
            }
        )

        enhanced_embedding = EnhancedResult.from_strategy_result(
            embedding_result,
            input_data={"file1": "test1.json", "file2": "test2.json"}
        )

        formatted_embedding = task_4_2_formatter.format_score_output(enhanced_embedding)

        # Requirement 8.1: 判定方式の明示的識別
        assert "comparison_method" in formatted_embedding["metadata"]
        assert formatted_embedding["metadata"]["comparison_method"] == "embedding"
        assert formatted_embedding["method_used"] == "embedding"

        # テストケース: LLMモード
        llm_result = StrategyResult(
            score=0.92,
            method="llm",
            processing_time=1.5,
            metadata={
                "category": "非常に類似",
                "reason": "意味的に同じ内容",
                "model_used": "qwen3-14b-awq",
                "confidence": 0.95,
                "tokens_used": 45
            }
        )

        enhanced_llm = EnhancedResult.from_strategy_result(
            llm_result,
            input_data={"json1": '{"task": "処理"}', "json2": '{"task": "実行"}'}
        )

        formatted_llm = task_4_2_formatter.format_score_output(enhanced_llm)

        # Requirement 8.1: 判定方式の明示的識別
        assert "comparison_method" in formatted_llm["metadata"]
        assert formatted_llm["metadata"]["comparison_method"] == "llm"
        assert formatted_llm["method_used"] == "llm"

        # テストケース: フォールバックモード
        fallback_result = StrategyResult(
            score=0.68,
            method="embedding_fallback",
            processing_time=0.4,
            metadata={
                "fallback_reason": "llm_api_timeout",
                "original_method": "llm"
            }
        )

        enhanced_fallback = EnhancedResult.from_strategy_result(
            fallback_result,
            input_data={"file1": "test1.json", "file2": "test2.json"}
        )

        formatted_fallback = task_4_2_formatter.format_score_output(enhanced_fallback)

        # Requirement 8.1: フォールバック時の識別
        assert "comparison_method" in formatted_fallback["metadata"]
        assert formatted_fallback["metadata"]["comparison_method"] == "embedding_fallback"
        assert formatted_fallback["method_used"] == "embedding_fallback"

    def test_requirement_8_3_llm_specific_metadata_enhancement(self, task_4_2_formatter):
        """
        Requirement 8.3: LLM固有メタデータの出力結果への付与を実装

        Task 4.2: LLM固有メタデータの出力結果への付与を実装
        """
        # LLM特有のメタデータを含むStrategyResult
        llm_result = StrategyResult(
            score=0.88,
            method="llm",
            processing_time=2.1,
            metadata={
                "category": "類似",
                "reason": "両方とも同じタスクを表現している",
                "model_used": "qwen3-14b-awq",
                "confidence": 0.91,
                "tokens_used": 52,
                "prompt_tokens": 38,
                "completion_tokens": 14,
                "temperature": 0.2,
                "max_tokens": 64
            }
        )

        # LLM設定情報
        llm_config = {
            "model": "qwen3-14b-awq",
            "prompt_file": "similarity_assessment.yaml",
            "temperature": 0.2,
            "max_tokens": 64,
            "api_endpoint": "http://localhost:8000/v1/chat/completions"
        }

        # パフォーマンスデータ
        performance_data = {
            "api_call_time": 1.8,
            "total_processing_time": 2.1,
            "queue_wait_time": 0.1,
            "token_generation_rate": 25.6
        }

        enhanced_result = create_enhanced_result_from_strategy(
            llm_result,
            input_data={"json1": '{"description": "データ処理"}', "json2": '{"description": "データの処理"}'},
            llm_config=llm_config,
            performance_data=performance_data
        )

        formatted_result = task_4_2_formatter.format_score_output(enhanced_result)

        # Requirement 8.3: LLM固有メタデータの存在確認
        assert "llm_details" in formatted_result["metadata"]
        llm_details = formatted_result["metadata"]["llm_details"]

        # LLMモデル情報
        assert llm_details["model_used"] == "qwen3-14b-awq"
        assert llm_details["confidence"] == 0.91

        # トークン使用量情報
        assert llm_details["tokens_used"] == 52
        assert "tokens_per_second" in llm_details

        # 意味解析結果
        assert llm_details["category"] == "類似"
        assert llm_details["reason"] == "両方とも同じタスクを表現している"

        # LLMメタデータオブジェクトの存在確認
        assert enhanced_result.llm_metadata is not None
        assert enhanced_result.llm_metadata.model_name == "qwen3-14b-awq"
        assert enhanced_result.llm_metadata.prompt_file == "similarity_assessment.yaml"
        assert enhanced_result.llm_metadata.tokens_used == 52

    def test_requirement_8_4_embedding_specific_metadata_enhancement(self, task_4_2_formatter):
        """
        Requirement 8.4: 埋め込み固有メタデータの出力結果への付与を実装

        Task 4.2: 埋め込み固有メタデータの出力結果への付与を実装
        """
        # 埋め込み特有のメタデータを含むStrategyResult
        embedding_result = StrategyResult(
            score=0.73,
            method="embedding",
            processing_time=0.25,
            metadata={
                "field_match_ratio": 0.85,
                "value_similarity": 0.68,
                "algorithm": "cosine_similarity",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_dimensions": 384,
                "preprocessing_steps": ["normalization", "tokenization"],
                "similarity_threshold": 0.5,
                "computation_method": "vector_cosine"
            }
        )

        # パフォーマンスデータ
        performance_data = {
            "api_call_time": 0.0,  # ローカル計算
            "total_processing_time": 0.25,
            "memory_usage_mb": 15.2,
            "cpu_usage_percent": 12.5
        }

        enhanced_result = create_enhanced_result_from_strategy(
            embedding_result,
            input_data={"file1": "data1.json", "file2": "data2.json"},
            llm_config=None,
            performance_data=performance_data
        )

        formatted_result = task_4_2_formatter.format_score_output(enhanced_result)

        # Requirement 8.4: 埋め込み固有メタデータの存在確認
        metadata = formatted_result["metadata"]

        # 埋め込み計算メタデータ
        assert metadata["calculation_method"] == "embedding"

        # JSON構造解析結果
        json_details = formatted_result["json"]
        assert json_details["field_match_ratio"] == 0.85
        assert json_details["value_similarity"] == 0.68
        assert json_details["final_score"] == 0.73

        # 埋め込み特有の詳細情報（メタデータ内）
        assert enhanced_result.metadata["algorithm"] == "cosine_similarity"
        assert enhanced_result.metadata["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert enhanced_result.metadata["embedding_dimensions"] == 384

        # パフォーマンス指標
        assert enhanced_result.performance_metrics is not None
        assert enhanced_result.performance_metrics.memory_usage_mb == 15.2

    def test_requirement_6_1_backward_compatibility_maintenance(self, task_4_2_compatibility):
        """
        Requirement 6.1: 既存の出力フォーマットとの後方互換性を維持

        Task 4.2: 既存の出力フォーマットとの後方互換性を維持
        """
        # 既存フォーマット（レガシー）のデータ
        legacy_data = {
            "file": "test1.json vs test2.json",
            "score": 0.82,
            "meaning": "非常に類似",
            "json": {
                "field_match_ratio": 0.9,
                "value_similarity": 0.75,
                "final_score": 0.82
            }
        }

        # 拡張フォーマットへのアップグレード
        upgraded_data = task_4_2_compatibility.upgrade_legacy_format(legacy_data)

        # Requirement 6.1: 必須フィールドの保持
        assert upgraded_data["file"] == "test1.json vs test2.json"
        assert upgraded_data["score"] == 0.82
        assert upgraded_data["meaning"] == "非常に類似"
        assert upgraded_data["json"]["field_match_ratio"] == 0.9

        # 拡張メタデータの追加確認
        assert "metadata" in upgraded_data
        assert "calculation_method" in upgraded_data["metadata"]
        assert "format_version" in upgraded_data["metadata"]

        # 拡張結果からレガシーフォーマットへの変換
        enhanced_result = EnhancedResult(
            score=0.76,
            method="llm",
            processing_time=1.2,
            input_data={"file1": "data1.json", "file2": "data2.json"},
            metadata={
                "category": "類似",
                "model_used": "qwen3-14b-awq",
                "confidence": 0.88
            }
        )

        legacy_converted = task_4_2_compatibility.convert_to_legacy_format(enhanced_result)

        # Requirement 6.1: レガシーフォーマットとの互換性
        assert "file" in legacy_converted
        assert "score" in legacy_converted
        assert "meaning" in legacy_converted
        assert "json" in legacy_converted
        assert legacy_converted["score"] == 0.76

        # 後方互換性確保フォーマット
        backward_compatible = task_4_2_compatibility.ensure_backward_compatibility(enhanced_result)

        # Requirement 6.1: 必須フィールドの存在
        assert all(key in backward_compatible for key in ["file", "score", "meaning", "json"])
        assert "metadata" in backward_compatible  # 拡張メタデータもオプションで追加
        assert backward_compatible["metadata"]["calculation_method"] == "llm"

    def test_task_4_2_comparison_method_integration(self, task_4_2_formatter):
        """
        Task 4.2: 比較方法識別の包括的統合テスト

        様々なシナリオでの比較方法識別機能の検証
        """
        test_scenarios = [
            # シナリオ1: 純粋な埋め込みモード
            {
                "strategy_result": StrategyResult(
                    score=0.71, method="embedding", processing_time=0.2,
                    metadata={"algorithm": "cosine", "model": "all-MiniLM-L6-v2"}
                ),
                "expected_method": "embedding"
            },
            # シナリオ2: 純粋なLLMモード
            {
                "strategy_result": StrategyResult(
                    score=0.89, method="llm", processing_time=1.8,
                    metadata={"model_used": "qwen3-14b-awq", "category": "類似"}
                ),
                "expected_method": "llm"
            },
            # シナリオ3: LLMからのフォールバック
            {
                "strategy_result": StrategyResult(
                    score=0.65, method="embedding_fallback", processing_time=0.4,
                    metadata={"fallback_reason": "api_timeout", "original_method": "llm"}
                ),
                "expected_method": "embedding_fallback"
            },
            # シナリオ4: 自動選択でLLMが選択
            {
                "strategy_result": StrategyResult(
                    score=0.93, method="llm", processing_time=2.2,
                    metadata={"auto_selected": True, "reason": "semantic_content_detected"}
                ),
                "expected_method": "llm"
            }
        ]

        for i, scenario in enumerate(test_scenarios):
            enhanced_result = EnhancedResult.from_strategy_result(
                scenario["strategy_result"],
                input_data={"test_id": f"scenario_{i+1}"}
            )

            formatted_result = task_4_2_formatter.format_score_output(enhanced_result)

            # 比較方法の正確な識別
            assert formatted_result["method_used"] == scenario["expected_method"]
            assert formatted_result["metadata"]["calculation_method"] == scenario["expected_method"]

    def test_task_4_2_metadata_enrichment_comprehensive(self, task_4_2_formatter):
        """
        Task 4.2: メタデータ拡張の包括的テスト

        LLMと埋め込みの両方でのメタデータ拡張機能の統合検証
        """
        # LLMモードでのメタデータ拡張テスト
        llm_result = StrategyResult(
            score=0.87,
            method="llm",
            processing_time=1.9,
            metadata={
                "category": "非常に類似",
                "reason": "同じ概念を異なる表現で示している",
                "model_used": "qwen3-14b-awq",
                "confidence": 0.92,
                "tokens_used": 48,
                "prompt_tokens": 35,
                "completion_tokens": 13
            }
        )

        llm_config = {
            "model": "qwen3-14b-awq",
            "temperature": 0.1,
            "max_tokens": 100,
            "prompt_file": "enhanced_similarity.yaml"
        }

        enhanced_llm = create_enhanced_result_from_strategy(
            llm_result,
            input_data={"content1": "データ分析", "content2": "情報解析"},
            llm_config=llm_config
        )

        formatted_llm = task_4_2_formatter.format_score_output(enhanced_llm)

        # LLMメタデータの包括的検証
        assert "llm_details" in formatted_llm["metadata"]
        llm_details = formatted_llm["metadata"]["llm_details"]
        assert llm_details["model_used"] == "qwen3-14b-awq"
        assert llm_details["confidence"] == 0.92
        assert llm_details["tokens_used"] == 48
        assert "tokens_per_second" in llm_details

        # 埋め込みモードでのメタデータ拡張テスト
        embedding_result = StrategyResult(
            score=0.74,
            method="embedding",
            processing_time=0.18,
            metadata={
                "field_match_ratio": 0.95,
                "value_similarity": 0.58,
                "algorithm": "cosine_similarity",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
            }
        )

        enhanced_embedding = create_enhanced_result_from_strategy(
            embedding_result,
            input_data={"document1": "doc1.json", "document2": "doc2.json"}
        )

        formatted_embedding = task_4_2_formatter.format_score_output(enhanced_embedding)

        # 埋め込みメタデータの検証
        json_details = formatted_embedding["json"]
        assert json_details["field_match_ratio"] == 0.95
        assert json_details["value_similarity"] == 0.58
        assert json_details["final_score"] == 0.74

    def test_task_4_2_performance_metrics_integration(self):
        """
        Task 4.2: パフォーマンス指標の統合テスト

        Requirement 6.1の一部として、パフォーマンス情報の統合
        """
        # パフォーマンスデータ付きの拡張結果作成
        strategy_result = StrategyResult(
            score=0.81,
            method="llm",
            processing_time=1.5,
            metadata={"model_used": "qwen3-14b-awq", "tokens_used": 42}
        )

        performance_data = {
            "api_call_time": 1.3,
            "total_processing_time": 1.5,
            "queue_wait_time": 0.05,
            "token_generation_rate": 32.3,
            "retry_count": 0,
            "memory_usage_mb": 25.7
        }

        enhanced_result = create_enhanced_result_from_strategy(
            strategy_result,
            input_data={"input": "test_data"},
            performance_data=performance_data
        )

        # パフォーマンス指標の検証
        assert enhanced_result.performance_metrics is not None
        perf = enhanced_result.performance_metrics
        assert perf.api_call_time == 1.3
        assert perf.total_processing_time == 1.5
        assert perf.queue_wait_time == 0.05
        assert perf.token_generation_rate == 32.3
        assert perf.memory_usage_mb == 25.7

        # 効率比率の計算テスト
        efficiency_ratio = perf.calculate_efficiency_ratio()
        expected_ratio = 1.3 / 1.5  # api_call_time / total_processing_time
        assert abs(efficiency_ratio - expected_ratio) < 0.001

        # スループット計算テスト
        throughput = perf.calculate_throughput(42)  # tokens_used
        expected_throughput = 42 / 1.3  # tokens / api_call_time
        assert abs(throughput - expected_throughput) < 0.1

    def test_task_4_2_error_handling_and_fallback_metadata(self, task_4_2_formatter):
        """
        Task 4.2: エラーハンドリングとフォールバック時のメタデータ処理

        フォールバック発生時の適切なメタデータ管理
        """
        # フォールバック発生シナリオ
        fallback_result = StrategyResult(
            score=0.69,
            method="embedding_fallback",
            processing_time=0.35,
            metadata={
                "fallback_reason": "llm_api_connection_timeout",
                "original_method": "llm",
                "retry_count": 3,
                "field_match_ratio": 0.7,
                "value_similarity": 0.68
            }
        )

        performance_data = {
            "api_call_time": 0.0,  # フォールバック時はAPI呼び出しなし
            "total_processing_time": 0.35,
            "retry_count": 3,
            "retry_total_time": 5.2,  # リトライに費やした時間
            "fallback_used": True
        }

        enhanced_result = create_enhanced_result_from_strategy(
            fallback_result,
            input_data={"source": "fallback_test"},
            performance_data=performance_data
        )

        formatted_result = task_4_2_formatter.format_score_output(enhanced_result)

        # フォールバック情報の検証
        assert enhanced_result.fallback_reason == "llm_api_connection_timeout"
        assert enhanced_result.original_method == "llm"
        assert formatted_result["method_used"] == "embedding_fallback"

        # パフォーマンス指標でのフォールバック情報
        assert enhanced_result.performance_metrics.fallback_used == True
        assert enhanced_result.performance_metrics.retry_count == 3
        assert enhanced_result.performance_metrics.retry_total_time == 5.2