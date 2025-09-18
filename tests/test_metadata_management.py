"""Task 4.2: メタデータ管理と結果フォーマット拡張のテスト

TDD実装：LLM固有メタデータとパフォーマンス指標の追加
Requirements: 5.5, 6.1
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from src.enhanced_result_format import (
    EnhancedResult,
    ResultFormatter,
    LLMMetadata,
    PerformanceMetrics,
    create_enhanced_result_from_strategy
)
from src.similarity_strategy import StrategyResult


class TestLLMMetadata:
    """Requirement 5.5: LLM固有メタデータのテスト"""

    def test_llm_metadata_creation(self):
        """LLM メタデータクラスの作成テスト"""
        metadata = LLMMetadata(
            model_name="qwen3-14b-awq",
            prompt_file="custom_prompt.yaml",
            temperature=0.3,
            max_tokens=128,
            tokens_used=95,
            prompt_tokens=45,
            completion_tokens=50
        )

        assert metadata.model_name == "qwen3-14b-awq"
        assert metadata.prompt_file == "custom_prompt.yaml"
        assert metadata.temperature == 0.3
        assert metadata.max_tokens == 128
        assert metadata.tokens_used == 95
        assert metadata.prompt_tokens == 45
        assert metadata.completion_tokens == 50

    def test_llm_metadata_to_dict(self):
        """LLM メタデータの辞書変換テスト"""
        metadata = LLMMetadata(
            model_name="test-model",
            temperature=0.2,
            max_tokens=64
        )

        result_dict = metadata.to_dict()

        assert result_dict["model_name"] == "test-model"
        assert result_dict["temperature"] == 0.2
        assert result_dict["max_tokens"] == 64
        assert "timestamp" in result_dict
        assert "llm_version" in result_dict

    def test_llm_metadata_with_prompt_details(self):
        """プロンプト詳細情報付きのLLMメタデータテスト"""
        metadata = LLMMetadata(
            model_name="qwen3-14b-awq",
            prompt_file="similarity.yaml",
            prompt_version="1.2",
            system_prompt_hash="abc123",
            user_prompt_template="{text1} vs {text2}"
        )

        result_dict = metadata.to_dict()

        assert result_dict["prompt_file"] == "similarity.yaml"
        assert result_dict["prompt_version"] == "1.2"
        assert result_dict["system_prompt_hash"] == "abc123"
        assert result_dict["user_prompt_template"] == "{text1} vs {text2}"


class TestPerformanceMetrics:
    """Requirement 6.1: パフォーマンスメトリクスのテスト"""

    def test_performance_metrics_creation(self):
        """パフォーマンス指標クラスの作成テスト"""
        metrics = PerformanceMetrics(
            api_call_time=2.5,
            total_processing_time=3.1,
            queue_wait_time=0.3,
            token_generation_rate=25.5
        )

        assert metrics.api_call_time == 2.5
        assert metrics.total_processing_time == 3.1
        assert metrics.queue_wait_time == 0.3
        assert metrics.token_generation_rate == 25.5

    def test_performance_metrics_with_retries(self):
        """リトライ情報付きパフォーマンス指標のテスト"""
        metrics = PerformanceMetrics(
            api_call_time=5.2,
            total_processing_time=8.7,
            retry_count=2,
            retry_total_time=3.5,
            fallback_used=True
        )

        assert metrics.retry_count == 2
        assert metrics.retry_total_time == 3.5
        assert metrics.fallback_used is True

    def test_performance_metrics_calculation(self):
        """パフォーマンス指標の計算機能テスト"""
        metrics = PerformanceMetrics(
            api_call_time=3.0,
            total_processing_time=4.0,
            token_generation_rate=20.0
        )

        # 効率指標の計算
        assert metrics.calculate_efficiency_ratio() == pytest.approx(0.75, rel=1e-2)

        # スループット計算
        throughput = metrics.calculate_throughput(tokens_generated=60)
        assert throughput == pytest.approx(20.0, rel=1e-2)

    def test_performance_metrics_to_dict(self):
        """パフォーマンス指標の辞書変換テスト"""
        metrics = PerformanceMetrics(
            api_call_time=1.5,
            total_processing_time=2.0,
            memory_usage_mb=256.5
        )

        result_dict = metrics.to_dict()

        assert result_dict["api_call_time"] == 1.5
        assert result_dict["total_processing_time"] == 2.0
        assert result_dict["memory_usage_mb"] == 256.5
        assert "timestamp" in result_dict


class TestEnhancedResultWithMetadata:
    """拡張結果とメタデータ統合のテスト"""

    def test_enhanced_result_includes_method_info(self):
        """Requirement 5.5: 結果に判定方式情報が含まれることのテスト"""
        result = EnhancedResult(
            score=0.8,
            method="llm",
            processing_time=2.5,
            input_data={"json1": "test1", "json2": "test2"}
        )

        assert result.method == "llm"
        assert result.score == 0.8
        assert "method" in result.to_dict()
        assert result.to_dict()["method"] == "llm"

    def test_enhanced_result_with_llm_metadata(self):
        """LLMメタデータ付き拡張結果のテスト"""
        llm_metadata = LLMMetadata(
            model_name="qwen3-14b-awq",
            temperature=0.3,
            tokens_used=85
        )

        result = EnhancedResult(
            score=0.9,
            method="llm",
            processing_time=3.2,
            input_data={"text1": "sample1", "text2": "sample2"},
            llm_metadata=llm_metadata
        )

        result_dict = result.to_dict()
        assert "llm_metadata" in result_dict
        assert result_dict["llm_metadata"]["model_name"] == "qwen3-14b-awq"
        assert result_dict["llm_metadata"]["tokens_used"] == 85

    def test_enhanced_result_with_performance_metrics(self):
        """パフォーマンス指標付き拡張結果のテスト"""
        perf_metrics = PerformanceMetrics(
            api_call_time=1.8,
            total_processing_time=2.1,
            token_generation_rate=30.5
        )

        result = EnhancedResult(
            score=0.7,
            method="llm",
            processing_time=2.1,
            input_data={"input": "test"},
            performance_metrics=perf_metrics
        )

        result_dict = result.to_dict()
        assert "performance_metrics" in result_dict
        assert result_dict["performance_metrics"]["api_call_time"] == 1.8
        assert result_dict["performance_metrics"]["token_generation_rate"] == 30.5

    def test_enhanced_result_embedding_fallback_metadata(self):
        """埋め込みフォールバック時のメタデータテスト"""
        result = EnhancedResult(
            score=0.6,
            method="embedding_fallback",
            processing_time=1.2,
            input_data={"text": "fallback_test"},
            fallback_reason="LLM API timeout",
            original_method="llm"
        )

        result_dict = result.to_dict()
        assert result_dict["method"] == "embedding_fallback"
        assert result_dict["fallback_reason"] == "LLM API timeout"
        assert result_dict["original_method"] == "llm"


class TestResultFormatterExtensions:
    """結果フォーマッター拡張のテスト"""

    def test_format_score_output_with_method_info(self):
        """Requirement 5.5: scoreフォーマットに判定方式情報が含まれることのテスト"""
        formatter = ResultFormatter()

        enhanced_result = EnhancedResult(
            score=0.8,
            method="llm",
            processing_time=2.3,
            input_data={"file": "test.jsonl"}
        )

        formatted_output = formatter.format_score_output(enhanced_result)

        assert "method_used" in formatted_output
        assert formatted_output["method_used"] == "llm"
        assert "processing_time" in formatted_output
        assert formatted_output["processing_time"] == 2.3

    def test_format_file_output_with_metadata(self):
        """fileフォーマットにメタデータが含まれることのテスト"""
        formatter = ResultFormatter()

        llm_metadata = LLMMetadata(
            model_name="test-model",
            tokens_used=100
        )

        enhanced_result = EnhancedResult(
            score=0.9,
            method="llm",
            processing_time=1.5,
            input_data={"line": 1, "content": "test"},
            llm_metadata=llm_metadata
        )

        formatted_output = formatter.format_file_output(enhanced_result)

        assert "metadata" in formatted_output
        assert "method" in formatted_output["metadata"]
        assert "llm_info" in formatted_output["metadata"]
        assert formatted_output["metadata"]["llm_info"]["model_name"] == "test-model"

    def test_format_output_with_performance_summary(self):
        """パフォーマンス要約付き出力フォーマットのテスト"""
        formatter = ResultFormatter()

        perf_metrics = PerformanceMetrics(
            api_call_time=2.0,
            total_processing_time=2.5,
            retry_count=1
        )

        enhanced_result = EnhancedResult(
            score=0.75,
            method="llm",
            processing_time=2.5,
            input_data={"test": "data"},
            performance_metrics=perf_metrics
        )

        formatted_output = formatter.format_detailed_output(enhanced_result)

        assert "performance_summary" in formatted_output
        perf_summary = formatted_output["performance_summary"]
        assert perf_summary["api_call_time"] == 2.0
        assert perf_summary["retry_count"] == 1
        assert perf_summary["efficiency_ratio"] == pytest.approx(0.8, rel=1e-1)


class TestBackwardCompatibility:
    """既存フォーマットとの互換性テスト"""

    def test_legacy_format_compatibility(self):
        """レガシー形式との互換性テスト"""
        formatter = ResultFormatter()

        # 従来の結果形式をシミュレート
        legacy_result = {
            "score": 0.7,
            "details": {"similarity_type": "cosine"}
        }

        # 拡張結果
        enhanced_result = EnhancedResult(
            score=0.7,
            method="embedding",
            processing_time=1.0,
            input_data={"legacy": True}
        )

        # レガシー出力形式で変換
        legacy_output = formatter.format_legacy_compatible(enhanced_result)

        assert legacy_output["score"] == 0.7
        assert "details" in legacy_output
        # メタデータは詳細セクションに含まれる
        assert "method" in legacy_output["details"]

    def test_enhanced_format_extensions(self):
        """拡張フォーマットの追加情報テスト"""
        formatter = ResultFormatter()

        enhanced_result = EnhancedResult(
            score=0.85,
            method="llm",
            processing_time=3.0,
            input_data={"enhanced": True}
        )

        enhanced_output = formatter.format_enhanced_output(enhanced_result)

        # 拡張フォーマット固有の情報
        assert "execution_info" in enhanced_output
        assert "timestamp" in enhanced_output["execution_info"]
        assert "method_used" in enhanced_output["execution_info"]
        assert "processing_duration" in enhanced_output["execution_info"]


class TestCreateEnhancedResultFromStrategy:
    """StrategyResultからの拡張結果作成のテスト"""

    def test_create_from_embedding_strategy_result(self):
        """埋め込み戦略結果からの拡張結果作成テスト"""
        strategy_result = StrategyResult(
            score=0.8,
            method="embedding",
            processing_time=1.5,
            metadata={"model": "ruri-v3-310m"}
        )

        enhanced_result = create_enhanced_result_from_strategy(
            strategy_result,
            input_data={"json1": "test1", "json2": "test2"}
        )

        assert enhanced_result.score == 0.8
        assert enhanced_result.method == "embedding"
        assert enhanced_result.processing_time == 1.5
        assert enhanced_result.llm_metadata is None  # 埋め込みモードではLLMメタデータなし

    def test_create_from_llm_strategy_result(self):
        """LLM戦略結果からの拡張結果作成テスト"""
        strategy_result = StrategyResult(
            score=0.9,
            method="llm",
            processing_time=3.2,
            metadata={
                "model_used": "qwen3-14b-awq",
                "tokens_used": 95,
                "confidence": 0.85,
                "category": "非常に類似"
            }
        )

        enhanced_result = create_enhanced_result_from_strategy(
            strategy_result,
            input_data={"text1": "sample1", "text2": "sample2"},
            llm_config={
                "model": "qwen3-14b-awq",
                "temperature": 0.3,
                "prompt_file": "custom.yaml"
            }
        )

        assert enhanced_result.score == 0.9
        assert enhanced_result.method == "llm"
        assert enhanced_result.llm_metadata is not None
        assert enhanced_result.llm_metadata.model_name == "qwen3-14b-awq"
        assert enhanced_result.llm_metadata.tokens_used == 95

    def test_create_with_performance_tracking(self):
        """パフォーマンス追跡付きの拡張結果作成テスト"""
        strategy_result = StrategyResult(
            score=0.75,
            method="llm",
            processing_time=4.1,
            metadata={"api_call_duration": 3.8}
        )

        enhanced_result = create_enhanced_result_from_strategy(
            strategy_result,
            input_data={"input": "test"},
            performance_data={
                "api_call_time": 3.8,
                "queue_wait_time": 0.3,
                "token_generation_rate": 22.5
            }
        )

        assert enhanced_result.performance_metrics is not None
        assert enhanced_result.performance_metrics.api_call_time == 3.8
        assert enhanced_result.performance_metrics.queue_wait_time == 0.3
        assert enhanced_result.performance_metrics.token_generation_rate == 22.5