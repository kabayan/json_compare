"""API Response Validation Engine テストスイート

Task 13.4の要件に対応：
- APIレスポンス構造とメタデータの包括的検証エンジンを構築
- validateScoreResponse/validateFileResponseメソッドの実装
- 必須フィールド（score、total_lines、_metadata）の存在確認機能を追加
- データ型正確性とメタデータ一貫性（calculation_method、source_files、column_compared）の検証
- ValidationResultインターフェースで詳細なエラー・警告情報を提供

Requirements: 10.6, 10.9 - 2ファイル比較検証システム
"""

import pytest
from unittest.mock import MagicMock
from typing import Dict, Any, List, Optional, Literal


class TestAPIResponseValidationEngine:
    """API Response Validation Engine テストクラス"""

    def test_api_response_validation_engine_initialization(self):
        """API Response Validation Engineが正しく初期化されること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine

        engine = APIResponseValidationEngine()
        assert engine is not None

    def test_expected_metadata_interface_definition(self):
        """ExpectedMetadataインターフェースが正しく定義されていること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import ExpectedMetadata

        metadata = ExpectedMetadata(
            calculation_method="embedding",
            source_files={
                "file1": "test1.jsonl",
                "file2": "test2.jsonl"
            },
            column_compared="inference1"
        )

        assert metadata.calculation_method == "embedding"
        assert metadata.source_files["file1"] == "test1.jsonl"
        assert metadata.source_files["file2"] == "test2.jsonl"
        assert metadata.column_compared == "inference1"

    def test_validation_result_interface_import(self):
        """ValidationResultインターフェースがインポートできること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import ValidationResult

        result = ValidationResult(
            isValid=True,
            errors=[],
            warnings=[],
            details={"field_validation": "passed"}
        )

        assert result.isValid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.details["field_validation"] == "passed"

    def test_validate_score_response_embedding_method(self):
        """埋め込みモードのスコアレスポンス検証が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine

        engine = APIResponseValidationEngine()

        # 正常なスコアレスポンス
        valid_score_response = {
            "score": 0.85,
            "total_lines": 100,
            "_metadata": {
                "calculation_method": "embedding",
                "source_files": {
                    "file1": "test1.jsonl",
                    "file2": "test2.jsonl"
                },
                "column_compared": "inference1",
                "processing_time": 2.5
            }
        }

        result = engine.validateScoreResponse(
            response=valid_score_response,
            expectedMethod="embedding"
        )

        assert result.isValid is True
        assert len(result.errors) == 0

    def test_validate_score_response_llm_method(self):
        """LLMモードのスコアレスポンス検証が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine

        engine = APIResponseValidationEngine()

        # 正常なLLMスコアレスポンス
        valid_llm_response = {
            "score": 0.92,
            "total_lines": 50,
            "_metadata": {
                "calculation_method": "llm",
                "model_name": "qwen3-14b-awq",
                "source_files": {
                    "file1": "test1.jsonl",
                    "file2": "test2.jsonl"
                },
                "column_compared": "inference2",
                "processing_time": 15.2,
                "llm_response_time": 12.8
            }
        }

        result = engine.validateScoreResponse(
            response=valid_llm_response,
            expectedMethod="llm"
        )

        assert result.isValid is True
        assert len(result.errors) == 0

    def test_validate_file_response_embedding_method(self):
        """埋め込みモードのファイルレスポンス検証が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine

        engine = APIResponseValidationEngine()

        # 正常なファイルレスポンス
        valid_file_response = {
            "detailed_results": [
                {"line": 1, "score": 0.85, "text1": "test1", "text2": "test2"},
                {"line": 2, "score": 0.92, "text1": "test3", "text2": "test4"}
            ],
            "total_lines": 2,
            "_metadata": {
                "calculation_method": "embedding",
                "source_files": {
                    "file1": "test1.jsonl",
                    "file2": "test2.jsonl"
                },
                "column_compared": "inference1",
                "processing_time": 3.1
            }
        }

        result = engine.validateFileResponse(
            response=valid_file_response,
            expectedMethod="embedding"
        )

        assert result.isValid is True
        assert len(result.errors) == 0

    def test_validate_file_response_llm_method(self):
        """LLMモードのファイルレスポンス検証が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine

        engine = APIResponseValidationEngine()

        # 正常なLLMファイルレスポンス
        valid_llm_file_response = {
            "detailed_results": [
                {"line": 1, "score": 0.88, "text1": "test1", "text2": "test2", "llm_reasoning": "Similar content"},
                {"line": 2, "score": 0.95, "text1": "test3", "text2": "test4", "llm_reasoning": "Very similar"}
            ],
            "total_lines": 2,
            "_metadata": {
                "calculation_method": "llm",
                "model_name": "qwen3-14b-awq",
                "source_files": {
                    "file1": "test1.jsonl",
                    "file2": "test2.jsonl"
                },
                "column_compared": "inference2",
                "processing_time": 18.5,
                "llm_response_time": 15.3
            }
        }

        result = engine.validateFileResponse(
            response=valid_llm_file_response,
            expectedMethod="llm"
        )

        assert result.isValid is True
        assert len(result.errors) == 0

    def test_validate_metadata_consistency_functionality(self):
        """メタデータ一貫性検証が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine, ExpectedMetadata

        engine = APIResponseValidationEngine()

        response = {
            "score": 0.85,
            "total_lines": 100,
            "_metadata": {
                "calculation_method": "embedding",
                "source_files": {
                    "file1": "test1.jsonl",
                    "file2": "test2.jsonl"
                },
                "column_compared": "inference1"
            }
        }

        expected_metadata = ExpectedMetadata(
            calculation_method="embedding",
            source_files={
                "file1": "test1.jsonl",
                "file2": "test2.jsonl"
            },
            column_compared="inference1"
        )

        result = engine.validateMetadataConsistency(
            response=response,
            expectedMetadata=expected_metadata
        )

        assert result.isValid is True
        assert len(result.errors) == 0

    def test_missing_required_fields_detection(self):
        """必須フィールド不足の検出が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine

        engine = APIResponseValidationEngine()

        # スコアフィールドが不足
        incomplete_response = {
            "total_lines": 100,
            "_metadata": {
                "calculation_method": "embedding"
            }
        }

        result = engine.validateScoreResponse(
            response=incomplete_response,
            expectedMethod="embedding"
        )

        assert result.isValid is False
        assert len(result.errors) > 0
        assert any("score" in error.message.lower() for error in result.errors)

    def test_incorrect_data_types_detection(self):
        """データ型不正の検出が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine

        engine = APIResponseValidationEngine()

        # スコアが文字列（不正なデータ型）
        invalid_type_response = {
            "score": "0.85",  # 数値であるべき
            "total_lines": "100",  # 整数であるべき
            "_metadata": {
                "calculation_method": "embedding"
            }
        }

        result = engine.validateScoreResponse(
            response=invalid_type_response,
            expectedMethod="embedding"
        )

        assert result.isValid is False
        assert len(result.errors) > 0

    def test_metadata_calculation_method_mismatch_detection(self):
        """メタデータ計算手法不一致の検出が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine

        engine = APIResponseValidationEngine()

        # 期待されるメソッドとメタデータが不一致
        mismatched_response = {
            "score": 0.85,
            "total_lines": 100,
            "_metadata": {
                "calculation_method": "llm"  # embeddingが期待されている
            }
        }

        result = engine.validateScoreResponse(
            response=mismatched_response,
            expectedMethod="embedding"
        )

        assert result.isValid is False
        assert len(result.errors) > 0
        assert any("calculation method" in error.message.lower() for error in result.errors)

    def test_detailed_results_array_validation(self):
        """detailed_results配列の検証が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine

        engine = APIResponseValidationEngine()

        # detailed_resultsが配列でない
        invalid_results_response = {
            "detailed_results": "not an array",
            "total_lines": 100,
            "_metadata": {
                "calculation_method": "embedding"
            }
        }

        result = engine.validateFileResponse(
            response=invalid_results_response,
            expectedMethod="embedding"
        )

        assert result.isValid is False
        assert len(result.errors) > 0

    def test_source_files_validation(self):
        """source_files検証が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine, ExpectedMetadata

        engine = APIResponseValidationEngine()

        response = {
            "score": 0.85,
            "total_lines": 100,
            "_metadata": {
                "calculation_method": "embedding",
                "source_files": {
                    "file1": "wrong1.jsonl",  # 期待と異なる
                    "file2": "test2.jsonl"
                },
                "column_compared": "inference1"
            }
        }

        expected_metadata = ExpectedMetadata(
            calculation_method="embedding",
            source_files={
                "file1": "test1.jsonl",
                "file2": "test2.jsonl"
            },
            column_compared="inference1"
        )

        result = engine.validateMetadataConsistency(
            response=response,
            expectedMetadata=expected_metadata
        )

        assert result.isValid is False
        assert len(result.errors) > 0

    def test_column_compared_validation(self):
        """column_compared検証が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine, ExpectedMetadata

        engine = APIResponseValidationEngine()

        response = {
            "score": 0.85,
            "total_lines": 100,
            "_metadata": {
                "calculation_method": "embedding",
                "source_files": {
                    "file1": "test1.jsonl",
                    "file2": "test2.jsonl"
                },
                "column_compared": "inference2"  # inference1が期待されている
            }
        }

        expected_metadata = ExpectedMetadata(
            calculation_method="embedding",
            source_files={
                "file1": "test1.jsonl",
                "file2": "test2.jsonl"
            },
            column_compared="inference1"
        )

        result = engine.validateMetadataConsistency(
            response=response,
            expectedMetadata=expected_metadata
        )

        assert result.isValid is False
        assert len(result.errors) > 0

    def test_warning_generation_for_optional_fields(self):
        """オプションフィールドに対する警告生成が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine

        engine = APIResponseValidationEngine()

        # LLMレスポンスでmodel_nameが不足
        response_without_model = {
            "score": 0.85,
            "total_lines": 100,
            "_metadata": {
                "calculation_method": "llm",
                "source_files": {
                    "file1": "test1.jsonl",
                    "file2": "test2.jsonl"
                },
                "column_compared": "inference1"
                # model_nameとllm_response_timeが不足
            }
        }

        result = engine.validateScoreResponse(
            response=response_without_model,
            expectedMethod="llm"
        )

        # 必須フィールドはあるので有効だが、警告があるべき
        assert result.isValid is True
        assert len(result.warnings) > 0

    def test_comprehensive_validation_with_all_fields(self):
        """全フィールドを含む包括的検証が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.api_response_validation_engine import APIResponseValidationEngine

        engine = APIResponseValidationEngine()

        # 完全なレスポンス
        complete_response = {
            "score": 0.85,
            "total_lines": 100,
            "_metadata": {
                "calculation_method": "llm",
                "model_name": "qwen3-14b-awq",
                "source_files": {
                    "file1": "test1.jsonl",
                    "file2": "test2.jsonl"
                },
                "column_compared": "inference1",
                "processing_time": 15.2,
                "llm_response_time": 12.8,
                "total_comparisons": 100,
                "average_score": 0.82
            }
        }

        result = engine.validateScoreResponse(
            response=complete_response,
            expectedMethod="llm"
        )

        assert result.isValid is True
        assert len(result.errors) == 0
        # 警告もないはず（完全なレスポンス）
        assert len(result.warnings) == 0