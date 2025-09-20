"""API Response Validation Engine for Dual File Comparison

Task 13.4の実装：
- APIレスポンス構造とメタデータの包括的検証エンジンを構築
- validateScoreResponse/validateFileResponseメソッドの実装
- 必須フィールド（score、total_lines、_metadata）の存在確認機能を追加
- データ型正確性とメタデータ一貫性（calculation_method、source_files、column_compared）の検証
- ValidationResultインターフェースで詳細なエラー・警告情報を提供

Requirements: 10.6, 10.9 - 2ファイル比較検証システム

Modules:
- APIResponseValidationEngine: メインのAPIレスポンス検証エンジンクラス
- ExpectedMetadata: 期待されるメタデータ情報のデータクラス
- ValidationResult: 検証結果のデータクラス（dual_file_test_management_frameworkから再エクスポート）

Design Patterns:
- Strategy Pattern: 異なるレスポンス形式（score/file）の検証戦略
- Template Method Pattern: 共通の検証フローと特化した検証ロジック
- Builder Pattern: 複雑なValidationResultの構築
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Literal, Union
from datetime import datetime

# 既存のValidationResult関連をインポート
from .dual_file_test_management_framework import ValidationResult, ValidationError, ValidationWarning


@dataclass
class ExpectedMetadata:
    """期待されるメタデータ情報

    Attributes:
        calculation_method: 計算手法（embedding または llm）
        source_files: ソースファイル情報
        column_compared: 比較対象カラム名
        additional_fields: 追加の期待フィールド
    """
    calculation_method: Literal["embedding", "llm"]
    source_files: Dict[str, str]
    column_compared: str
    additional_fields: Dict[str, Any] = field(default_factory=dict)


class APIResponseValidationEngineError(Exception):
    """API Response Validation Engine専用エラークラス"""
    pass


class APIResponseValidationEngine:
    """API Response Validation Engine

    APIレスポンスの構造とメタデータの包括的検証を行う。
    スコア形式とファイル形式の両方に対応し、計算手法の一貫性を確認する。
    """

    def __init__(self):
        """APIレスポンス検証エンジンの初期化"""
        self._logger = logging.getLogger(__name__)

    def validateScoreResponse(
        self,
        response: Any,
        expectedMethod: Literal["embedding", "llm"]
    ) -> ValidationResult:
        """スコア形式レスポンスの検証

        Args:
            response: 検証対象のAPIレスポンス
            expectedMethod: 期待される計算手法

        Returns:
            ValidationResult: 検証結果
        """
        try:
            self._logger.info(f"Validating score response with expected method: {expectedMethod}")

            errors = []
            warnings = []
            details = {}

            # レスポンスがdictかどうかを確認
            if not isinstance(response, dict):
                errors.append(ValidationError(
                    message="Response must be a dictionary",
                    code="INVALID_RESPONSE_TYPE",
                    details={"actual_type": type(response).__name__}
                ))
                return ValidationResult(
                    isValid=False,
                    errors=errors,
                    warnings=warnings,
                    details=details
                )

            # 必須フィールドの存在確認
            required_fields = ["score", "total_lines", "_metadata"]
            for field in required_fields:
                if field not in response:
                    errors.append(ValidationError(
                        message=f"Required field '{field}' is missing",
                        code="MISSING_REQUIRED_FIELD",
                        details={"field": field}
                    ))

            # データ型の検証
            if "score" in response:
                if not isinstance(response["score"], (int, float)):
                    errors.append(ValidationError(
                        message="Field 'score' must be a number",
                        code="INVALID_FIELD_TYPE",
                        details={"field": "score", "expected": "number", "actual": type(response["score"]).__name__}
                    ))

            if "total_lines" in response:
                if not isinstance(response["total_lines"], int):
                    errors.append(ValidationError(
                        message="Field 'total_lines' must be an integer",
                        code="INVALID_FIELD_TYPE",
                        details={"field": "total_lines", "expected": "integer", "actual": type(response["total_lines"]).__name__}
                    ))

            # メタデータの検証
            if "_metadata" in response:
                metadata_result = self._validateMetadata(response["_metadata"], expectedMethod)
                errors.extend(metadata_result.errors)
                warnings.extend(metadata_result.warnings)
                details.update(metadata_result.details)

            # LLMレスポンス特有のフィールドチェック
            if expectedMethod == "llm" and "_metadata" in response:
                metadata = response["_metadata"]
                if "model_name" not in metadata:
                    warnings.append(ValidationWarning(
                        message="LLM response should include 'model_name' in metadata",
                        code="MISSING_OPTIONAL_FIELD",
                        details={"field": "model_name"}
                    ))
                if "llm_response_time" not in metadata:
                    warnings.append(ValidationWarning(
                        message="LLM response should include 'llm_response_time' in metadata",
                        code="MISSING_OPTIONAL_FIELD",
                        details={"field": "llm_response_time"}
                    ))

            is_valid = len(errors) == 0

            details.update({
                "response_type": "score",
                "expected_method": expectedMethod,
                "validation_timestamp": datetime.now().isoformat(),
                "required_fields_present": all(field in response for field in required_fields)
            })

            return ValidationResult(
                isValid=is_valid,
                errors=errors,
                warnings=warnings,
                details=details
            )

        except Exception as e:
            self._logger.error(f"Score response validation failed: {e}")
            return ValidationResult(
                isValid=False,
                errors=[ValidationError(
                    message=f"Validation error: {str(e)}",
                    code="VALIDATION_ERROR",
                    details={"exception": str(e)}
                )],
                warnings=[],
                details={}
            )

    def validateFileResponse(
        self,
        response: Any,
        expectedMethod: Literal["embedding", "llm"]
    ) -> ValidationResult:
        """ファイル形式レスポンスの検証

        Args:
            response: 検証対象のAPIレスポンス
            expectedMethod: 期待される計算手法

        Returns:
            ValidationResult: 検証結果
        """
        try:
            self._logger.info(f"Validating file response with expected method: {expectedMethod}")

            errors = []
            warnings = []
            details = {}

            # レスポンスがdictかどうかを確認
            if not isinstance(response, dict):
                errors.append(ValidationError(
                    message="Response must be a dictionary",
                    code="INVALID_RESPONSE_TYPE",
                    details={"actual_type": type(response).__name__}
                ))
                return ValidationResult(
                    isValid=False,
                    errors=errors,
                    warnings=warnings,
                    details=details
                )

            # 必須フィールドの存在確認
            required_fields = ["detailed_results", "total_lines", "_metadata"]
            for field in required_fields:
                if field not in response:
                    errors.append(ValidationError(
                        message=f"Required field '{field}' is missing",
                        code="MISSING_REQUIRED_FIELD",
                        details={"field": field}
                    ))

            # detailed_resultsの検証
            if "detailed_results" in response:
                if not isinstance(response["detailed_results"], list):
                    errors.append(ValidationError(
                        message="Field 'detailed_results' must be an array",
                        code="INVALID_FIELD_TYPE",
                        details={"field": "detailed_results", "expected": "array", "actual": type(response["detailed_results"]).__name__}
                    ))

            # データ型の検証
            if "total_lines" in response:
                if not isinstance(response["total_lines"], int):
                    errors.append(ValidationError(
                        message="Field 'total_lines' must be an integer",
                        code="INVALID_FIELD_TYPE",
                        details={"field": "total_lines", "expected": "integer", "actual": type(response["total_lines"]).__name__}
                    ))

            # メタデータの検証
            if "_metadata" in response:
                metadata_result = self._validateMetadata(response["_metadata"], expectedMethod)
                errors.extend(metadata_result.errors)
                warnings.extend(metadata_result.warnings)
                details.update(metadata_result.details)

            # LLMレスポンス特有のフィールドチェック
            if expectedMethod == "llm" and "_metadata" in response:
                metadata = response["_metadata"]
                if "model_name" not in metadata:
                    warnings.append(ValidationWarning(
                        message="LLM response should include 'model_name' in metadata",
                        code="MISSING_OPTIONAL_FIELD",
                        details={"field": "model_name"}
                    ))
                if "llm_response_time" not in metadata:
                    warnings.append(ValidationWarning(
                        message="LLM response should include 'llm_response_time' in metadata",
                        code="MISSING_OPTIONAL_FIELD",
                        details={"field": "llm_response_time"}
                    ))

            is_valid = len(errors) == 0

            details.update({
                "response_type": "file",
                "expected_method": expectedMethod,
                "validation_timestamp": datetime.now().isoformat(),
                "required_fields_present": all(field in response for field in required_fields)
            })

            return ValidationResult(
                isValid=is_valid,
                errors=errors,
                warnings=warnings,
                details=details
            )

        except Exception as e:
            self._logger.error(f"File response validation failed: {e}")
            return ValidationResult(
                isValid=False,
                errors=[ValidationError(
                    message=f"Validation error: {str(e)}",
                    code="VALIDATION_ERROR",
                    details={"exception": str(e)}
                )],
                warnings=[],
                details={}
            )

    def validateMetadataConsistency(
        self,
        response: Any,
        expectedMetadata: ExpectedMetadata
    ) -> ValidationResult:
        """メタデータ一貫性の検証

        Args:
            response: 検証対象のAPIレスポンス
            expectedMetadata: 期待されるメタデータ

        Returns:
            ValidationResult: 検証結果
        """
        try:
            self._logger.info("Validating metadata consistency")

            errors = []
            warnings = []
            details = {}

            if not isinstance(response, dict) or "_metadata" not in response:
                errors.append(ValidationError(
                    message="Response must contain '_metadata' field",
                    code="MISSING_METADATA",
                    details={}
                ))
                return ValidationResult(
                    isValid=False,
                    errors=errors,
                    warnings=warnings,
                    details=details
                )

            metadata = response["_metadata"]

            # calculation_methodの一貫性チェック
            if "calculation_method" in metadata:
                if metadata["calculation_method"] != expectedMetadata.calculation_method:
                    errors.append(ValidationError(
                        message=f"Calculation method mismatch: expected '{expectedMetadata.calculation_method}', got '{metadata['calculation_method']}'",
                        code="CALCULATION_METHOD_MISMATCH",
                        details={
                            "expected": expectedMetadata.calculation_method,
                            "actual": metadata["calculation_method"]
                        }
                    ))

            # source_filesの一貫性チェック
            if "source_files" in metadata:
                actual_files = metadata["source_files"]
                expected_files = expectedMetadata.source_files

                for key, expected_value in expected_files.items():
                    if key not in actual_files:
                        errors.append(ValidationError(
                            message=f"Missing source file key: {key}",
                            code="MISSING_SOURCE_FILE",
                            details={"missing_key": key}
                        ))
                    elif actual_files[key] != expected_value:
                        errors.append(ValidationError(
                            message=f"Source file mismatch for {key}: expected '{expected_value}', got '{actual_files[key]}'",
                            code="SOURCE_FILE_MISMATCH",
                            details={
                                "key": key,
                                "expected": expected_value,
                                "actual": actual_files[key]
                            }
                        ))

            # column_comparedの一貫性チェック
            if "column_compared" in metadata:
                if metadata["column_compared"] != expectedMetadata.column_compared:
                    errors.append(ValidationError(
                        message=f"Column compared mismatch: expected '{expectedMetadata.column_compared}', got '{metadata['column_compared']}'",
                        code="COLUMN_COMPARED_MISMATCH",
                        details={
                            "expected": expectedMetadata.column_compared,
                            "actual": metadata["column_compared"]
                        }
                    ))

            # 追加フィールドの検証
            for field, expected_value in expectedMetadata.additional_fields.items():
                if field in metadata:
                    if metadata[field] != expected_value:
                        warnings.append(ValidationWarning(
                            message=f"Additional field mismatch for {field}: expected '{expected_value}', got '{metadata[field]}'",
                            code="ADDITIONAL_FIELD_MISMATCH",
                            details={
                                "field": field,
                                "expected": expected_value,
                                "actual": metadata[field]
                            }
                        ))

            is_valid = len(errors) == 0

            details.update({
                "metadata_consistency_check": True,
                "expected_calculation_method": expectedMetadata.calculation_method,
                "validation_timestamp": datetime.now().isoformat()
            })

            return ValidationResult(
                isValid=is_valid,
                errors=errors,
                warnings=warnings,
                details=details
            )

        except Exception as e:
            self._logger.error(f"Metadata consistency validation failed: {e}")
            return ValidationResult(
                isValid=False,
                errors=[ValidationError(
                    message=f"Validation error: {str(e)}",
                    code="VALIDATION_ERROR",
                    details={"exception": str(e)}
                )],
                warnings=[],
                details={}
            )

    def _validateMetadata(
        self,
        metadata: Any,
        expectedMethod: Literal["embedding", "llm"]
    ) -> ValidationResult:
        """メタデータの詳細検証（内部メソッド）

        Args:
            metadata: 検証対象のメタデータ
            expectedMethod: 期待される計算手法

        Returns:
            ValidationResult: 検証結果
        """
        errors = []
        warnings = []
        details = {}

        if not isinstance(metadata, dict):
            errors.append(ValidationError(
                message="Metadata must be a dictionary",
                code="INVALID_METADATA_TYPE",
                details={"actual_type": type(metadata).__name__}
            ))
            return ValidationResult(
                isValid=False,
                errors=errors,
                warnings=warnings,
                details=details
            )

        # calculation_methodの確認
        if "calculation_method" not in metadata:
            errors.append(ValidationError(
                message="Metadata must contain 'calculation_method'",
                code="MISSING_CALCULATION_METHOD",
                details={}
            ))
        elif metadata["calculation_method"] != expectedMethod:
            errors.append(ValidationError(
                message=f"Calculation method mismatch: expected '{expectedMethod}', got '{metadata['calculation_method']}'",
                code="CALCULATION_METHOD_MISMATCH",
                details={
                    "expected": expectedMethod,
                    "actual": metadata["calculation_method"]
                }
            ))

        return ValidationResult(
            isValid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            details=details
        )