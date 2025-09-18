"""拡張結果フォーマットのテスト"""

import pytest
from unittest.mock import MagicMock
from typing import Dict, Any

# これから実装するモジュールをインポート
from src.enhanced_result_format import (
    EnhancedResult,
    ResultFormatter,
    MetadataCollector,
    CompatibilityLayer
)
from src.similarity_strategy import StrategyResult


class TestEnhancedResult:
    """拡張結果クラスのテスト"""

    def test_enhanced_result_creation_with_embedding(self):
        """埋め込みベース結果の拡張結果作成テスト"""
        strategy_result = StrategyResult(
            score=0.85,
            method="embedding",
            processing_time=0.5,
            metadata={
                "field_match_ratio": 0.8,
                "value_similarity": 0.9
            }
        )

        enhanced_result = EnhancedResult.from_strategy_result(
            strategy_result,
            input_data={"file1": "test1.json", "file2": "test2.json"}
        )

        assert enhanced_result.score == 0.85
        assert enhanced_result.method == "embedding"
        assert enhanced_result.processing_time == 0.5
        assert enhanced_result.input_data["file1"] == "test1.json"
        assert enhanced_result.metadata["field_match_ratio"] == 0.8
        assert enhanced_result.metadata["value_similarity"] == 0.9

    def test_enhanced_result_creation_with_llm(self):
        """LLMベース結果の拡張結果作成テスト"""
        strategy_result = StrategyResult(
            score=0.92,
            method="llm",
            processing_time=2.1,
            metadata={
                "category": "非常に類似",
                "reason": "両テキストの意味が非常に近い",
                "model_used": "qwen3-14b-awq",
                "confidence": 0.95,
                "tokens_used": 45
            }
        )

        enhanced_result = EnhancedResult.from_strategy_result(
            strategy_result,
            input_data={"json1": '{"task": "データ処理"}', "json2": '{"task": "データの処理"}'}
        )

        assert enhanced_result.score == 0.92
        assert enhanced_result.method == "llm"
        assert enhanced_result.processing_time == 2.1
        assert enhanced_result.metadata["category"] == "非常に類似"
        assert enhanced_result.metadata["model_used"] == "qwen3-14b-awq"
        assert enhanced_result.metadata["confidence"] == 0.95

    def test_enhanced_result_to_dict(self):
        """拡張結果の辞書変換テスト"""
        strategy_result = StrategyResult(
            score=0.75,
            method="embedding_fallback",
            processing_time=1.0,
            metadata={"field_match_ratio": 0.6, "value_similarity": 0.8}
        )

        enhanced_result = EnhancedResult.from_strategy_result(
            strategy_result,
            input_data={"file": "test.jsonl"}
        )

        result_dict = enhanced_result.to_dict()

        assert result_dict["score"] == 0.75
        assert result_dict["method"] == "embedding_fallback"
        assert result_dict["processing_time"] == 1.0
        assert result_dict["metadata"]["field_match_ratio"] == 0.6
        assert "input_data" in result_dict


class TestResultFormatter:
    """結果フォーマッターのテスト"""

    @pytest.fixture
    def result_formatter(self):
        """ResultFormatterインスタンスを返すフィクスチャ"""
        return ResultFormatter()

    def test_format_score_output_embedding(self, result_formatter):
        """埋め込みベースのscoreタイプ出力フォーマットテスト"""
        enhanced_result = EnhancedResult(
            score=0.85,
            method="embedding",
            processing_time=0.5,
            input_data={"file1": "test1.json", "file2": "test2.json"},
            metadata={
                "field_match_ratio": 0.8,
                "value_similarity": 0.9
            }
        )

        formatted = result_formatter.format_score_output(enhanced_result)

        # 既存フォーマットとの互換性確認
        assert formatted["file"] == "test1.json vs test2.json"
        assert formatted["score"] == 0.85
        assert formatted["meaning"] == "非常に類似"
        assert formatted["json"]["field_match_ratio"] == 0.8
        assert formatted["json"]["value_similarity"] == 0.9
        assert formatted["json"]["final_score"] == 0.85

        # 新しいメタデータの確認
        assert formatted["metadata"]["calculation_method"] == "embedding"
        assert formatted["metadata"]["processing_time"] == 0.5
        assert "timestamp" in formatted["metadata"]

    def test_format_score_output_llm(self, result_formatter):
        """LLMベースのscoreタイプ出力フォーマットテスト"""
        enhanced_result = EnhancedResult(
            score=0.92,
            method="llm",
            processing_time=2.1,
            input_data={"json1": '{"task": "処理"}', "json2": '{"task": "実行"}'},
            metadata={
                "category": "非常に類似",
                "reason": "タスクの意味が非常に近い",
                "model_used": "qwen3-14b-awq",
                "confidence": 0.95,
                "tokens_used": 45
            }
        )

        formatted = result_formatter.format_score_output(enhanced_result)

        # 既存フォーマットとの互換性
        assert formatted["score"] == 0.92
        assert formatted["meaning"] == "非常に類似"

        # LLM固有メタデータ
        assert formatted["metadata"]["calculation_method"] == "llm"
        assert formatted["metadata"]["llm_details"]["model_used"] == "qwen3-14b-awq"
        assert formatted["metadata"]["llm_details"]["confidence"] == 0.95
        assert formatted["metadata"]["llm_details"]["tokens_used"] == 45
        assert formatted["metadata"]["llm_details"]["category"] == "非常に類似"
        assert formatted["metadata"]["llm_details"]["reason"] == "タスクの意味が非常に近い"

    def test_format_file_output_with_metadata(self, result_formatter):
        """メタデータ付きfileタイプ出力フォーマットテスト"""
        original_data = {
            "id": 1,
            "inference1": '{"task": "データ処理"}',
            "inference2": '{"task": "データの処理"}'
        }

        enhanced_result = EnhancedResult(
            score=0.88,
            method="llm",
            processing_time=1.8,
            input_data={"original_row": original_data},
            metadata={
                "category": "非常に類似",
                "model_used": "qwen3-14b-awq",
                "confidence": 0.92
            }
        )

        formatted = result_formatter.format_file_output(enhanced_result)

        # 元のデータが保持されていることを確認
        assert formatted["id"] == 1
        assert formatted["inference1"] == '{"task": "データ処理"}'
        assert formatted["inference2"] == '{"task": "データの処理"}'

        # 既存の類似度情報
        assert formatted["similarity_score"] == 0.88
        assert "similarity_details" in formatted

        # 新しいメタデータ
        assert formatted["calculation_metadata"]["method"] == "llm"
        assert formatted["calculation_metadata"]["processing_time"] == 1.8
        assert formatted["calculation_metadata"]["llm_details"]["model_used"] == "qwen3-14b-awq"

    def test_format_batch_results(self, result_formatter):
        """バッチ結果フォーマットのテスト"""
        enhanced_results = [
            EnhancedResult(
                score=0.8, method="embedding", processing_time=0.3,
                input_data={"row": 1}, metadata={"field_match_ratio": 0.7}
            ),
            EnhancedResult(
                score=0.9, method="llm", processing_time=1.5,
                input_data={"row": 2}, metadata={"model_used": "qwen3-14b-awq"}
            )
        ]

        formatted = result_formatter.format_batch_results(enhanced_results, output_type="score")

        # 全体統計
        assert formatted["summary"]["total_comparisons"] == 2
        assert formatted["summary"]["average_score"] == 0.85
        assert formatted["summary"]["total_processing_time"] == 1.8

        # 方法別統計
        assert formatted["summary"]["method_breakdown"]["embedding"] == 1
        assert formatted["summary"]["method_breakdown"]["llm"] == 1

        # 詳細結果
        assert len(formatted["detailed_results"]) == 2


class TestMetadataCollector:
    """メタデータ収集器のテスト"""

    @pytest.fixture
    def metadata_collector(self):
        """MetadataCollectorインスタンスを返すフィクスチャ"""
        return MetadataCollector()

    def test_collect_system_metadata(self, metadata_collector):
        """システムメタデータ収集のテスト"""
        metadata = metadata_collector.collect_system_metadata()

        assert "timestamp" in metadata
        assert "version" in metadata
        assert "python_version" in metadata
        assert "platform" in metadata

    def test_collect_performance_metadata(self, metadata_collector):
        """パフォーマンスメタデータ収集のテスト"""
        strategy_result = StrategyResult(
            score=0.8,
            method="llm",
            processing_time=2.5,
            metadata={"tokens_used": 50}
        )

        metadata = metadata_collector.collect_performance_metadata(strategy_result)

        assert metadata["processing_time"] == 2.5
        assert metadata["calculation_method"] == "llm"
        assert "performance_category" in metadata  # fast/medium/slow

    def test_collect_llm_metadata(self, metadata_collector):
        """LLMメタデータ収集のテスト"""
        strategy_result = StrategyResult(
            score=0.9,
            method="llm",
            processing_time=1.5,
            metadata={
                "model_used": "qwen3-14b-awq",
                "confidence": 0.95,
                "tokens_used": 45,
                "category": "非常に類似",
                "reason": "意味が非常に近い"
            }
        )

        llm_metadata = metadata_collector.collect_llm_metadata(strategy_result)

        assert llm_metadata["model_used"] == "qwen3-14b-awq"
        assert llm_metadata["confidence"] == 0.95
        assert llm_metadata["tokens_used"] == 45
        assert llm_metadata["category"] == "非常に類似"
        assert llm_metadata["reason"] == "意味が非常に近い"
        assert "tokens_per_second" in llm_metadata  # 計算された値


class TestCompatibilityLayer:
    """互換性レイヤーのテスト"""

    @pytest.fixture
    def compatibility_layer(self):
        """CompatibilityLayerインスタンスを返すフィクスチャ"""
        return CompatibilityLayer()

    def test_convert_to_legacy_format(self, compatibility_layer):
        """レガシーフォーマット変換のテスト"""
        enhanced_result = EnhancedResult(
            score=0.85,
            method="embedding",
            processing_time=0.5,
            input_data={"file1": "test1.json", "file2": "test2.json"},
            metadata={
                "field_match_ratio": 0.8,
                "value_similarity": 0.9
            }
        )

        legacy_format = compatibility_layer.convert_to_legacy_format(enhanced_result)

        # レガシーフォーマットが正確に再現されることを確認
        assert legacy_format["file"] == "test1.json vs test2.json"
        assert legacy_format["score"] == 0.85
        assert legacy_format["meaning"] == "非常に類似"
        assert legacy_format["json"]["field_match_ratio"] == 0.8
        assert legacy_format["json"]["value_similarity"] == 0.9
        assert legacy_format["json"]["final_score"] == 0.85

        # 新しいメタデータは含まれていないことを確認
        assert "metadata" not in legacy_format
        assert "calculation_method" not in legacy_format

    def test_detect_format_version(self, compatibility_layer):
        """フォーマットバージョン検出のテスト"""
        # レガシーフォーマット
        legacy_data = {
            "file": "test1.json vs test2.json",
            "score": 0.85,
            "meaning": "非常に類似",
            "json": {"field_match_ratio": 0.8}
        }

        # 拡張フォーマット
        enhanced_data = {
            "file": "test1.json vs test2.json",
            "score": 0.85,
            "metadata": {"calculation_method": "llm"}
        }

        assert compatibility_layer.detect_format_version(legacy_data) == "legacy"
        assert compatibility_layer.detect_format_version(enhanced_data) == "enhanced"

    def test_upgrade_legacy_format(self, compatibility_layer):
        """レガシーフォーマットのアップグレードテスト"""
        legacy_data = {
            "file": "test1.json vs test2.json",
            "score": 0.85,
            "meaning": "非常に類似",
            "json": {
                "field_match_ratio": 0.8,
                "value_similarity": 0.9,
                "final_score": 0.85
            }
        }

        enhanced_data = compatibility_layer.upgrade_legacy_format(legacy_data)

        # 元のデータが保持されることを確認
        assert enhanced_data["score"] == 0.85
        assert enhanced_data["meaning"] == "非常に類似"

        # 拡張メタデータが追加されることを確認
        assert enhanced_data["metadata"]["calculation_method"] == "unknown"
        assert enhanced_data["metadata"]["format_version"] == "enhanced"
        assert "timestamp" in enhanced_data["metadata"]

    def test_maintain_backward_compatibility(self, compatibility_layer):
        """後方互換性維持のテスト"""
        # 既存のCLIクライアントが期待するフィールドが全て存在することを確認
        enhanced_result = EnhancedResult(
            score=0.75,
            method="llm",
            processing_time=2.0,
            input_data={"file1": "a.json", "file2": "b.json"},
            metadata={"model_used": "qwen3-14b-awq"}
        )

        backward_compatible = compatibility_layer.ensure_backward_compatibility(enhanced_result)

        # 必須フィールドの存在確認
        required_fields = ["file", "score", "meaning", "json"]
        for field in required_fields:
            assert field in backward_compatible

        # json サブフィールドの確認
        json_fields = ["field_match_ratio", "value_similarity", "final_score"]
        for field in json_fields:
            assert field in backward_compatible["json"]