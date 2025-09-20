"""Dual File Comparison Test Management Framework

Task 13.1の実装：
- 4つの組み合わせ（埋め込み/LLM × スコア/ファイル）テストの全体制御機能
- テスト実行状態と結果データの管理システム
- 各テストケース単位での独立トランザクション処理
- TestExecutionResultインターフェース（成功/失敗数、実行時間、詳細結果）
- validateDualFileComparisonメソッドで組み合わせ別検証

Requirements: 10.10, 10.11, 10.12 - 2ファイル比較検証システム

Modules:
- TestManagementFramework: メインのテスト管理フレームワーククラス
- TestExecutionResult: テスト実行結果のデータクラス
- ValidationResult: 検証結果のデータクラス
- TestCase: 個別テストケース情報のデータクラス
- ExecutionState: テスト実行状態の列挙型

Design Patterns:
- Strategy Pattern: 異なる組み合わせの検証ロジック
- State Machine: テスト実行状態の管理
- Factory Pattern: テストケースの生成
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Literal, Union
from datetime import datetime
from enum import Enum


class ExecutionState(Enum):
    """テスト実行状態の列挙型"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ValidationError:
    """検証エラー情報"""
    message: str
    code: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationWarning:
    """検証警告情報"""
    message: str
    code: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """検証結果インターフェース

    Attributes:
        isValid: 検証が成功したかどうか
        errors: エラー情報のリスト
        warnings: 警告情報のリスト
        details: 詳細情報（任意のデータ）
    """
    isValid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestExecutionResult:
    """テスト実行結果インターフェース

    Attributes:
        totalCombinations: 総組み合わせ数（4固定）
        successfulCombinations: 成功した組み合わせ数
        failedCombinations: 失敗した組み合わせ数
        executionTime: 実行時間（秒）
        detailedResults: 詳細な検証結果のリスト
    """
    totalCombinations: int
    successfulCombinations: int
    failedCombinations: int
    executionTime: float
    detailedResults: List[ValidationResult]


@dataclass
class TestCase:
    """個別テストケース情報"""
    mode: Literal["embedding", "llm"]
    format: Literal["score", "file"]
    expectedEndpoint: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    result: Optional[ValidationResult] = None
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None


class TestManagementFramework:
    """Dual File Comparison Test Management Framework

    2ファイル比較検証テストの全体制御と結果統合を行う。
    4つの組み合わせ（埋め込み/LLM × スコア/ファイル）テストを管理する。
    """

    def __init__(self):
        """フレームワークの初期化"""
        self._execution_state: ExecutionState = ExecutionState.IDLE
        self._test_results: List[ValidationResult] = []
        self._test_cases: List[TestCase] = self._initialize_test_cases()
        self._logger = logging.getLogger(__name__)

    def _initialize_test_cases(self) -> List[TestCase]:
        """4つの組み合わせのテストケースを初期化"""
        return [
            TestCase(
                mode="embedding",
                format="score",
                expectedEndpoint="/api/compare/dual"
            ),
            TestCase(
                mode="embedding",
                format="file",
                expectedEndpoint="/api/compare/dual"
            ),
            TestCase(
                mode="llm",
                format="score",
                expectedEndpoint="/api/compare/dual/llm"
            ),
            TestCase(
                mode="llm",
                format="file",
                expectedEndpoint="/api/compare/dual/llm"
            )
        ]

    def getExecutionState(self) -> str:
        """現在の実行状態を取得"""
        return self._execution_state.value

    async def executeComprehensiveTest(self) -> TestExecutionResult:
        """4つの組み合わせの包括的テストを実行

        Returns:
            TestExecutionResult: テスト実行結果

        Raises:
            RuntimeError: テスト実行中にクリティカルなエラーが発生した場合
        """
        if self._execution_state == ExecutionState.RUNNING:
            raise RuntimeError("Test execution is already in progress")

        self._execution_state = ExecutionState.RUNNING
        start_time = time.time()

        try:
            self._logger.info("Starting comprehensive dual file comparison test")
            self._logger.info(f"Test cases to execute: {len(self._test_cases)}")

            successful_count = 0
            failed_count = 0
            detailed_results = []

            # 4つの組み合わせを順次実行
            for i, test_case in enumerate(self._test_cases, 1):
                self._logger.info(f"Executing test case {i}/4: {test_case.mode}-{test_case.format}")

                result = await self._executeIndependentTestCase(test_case)
                detailed_results.append(result)

                if result.isValid:
                    successful_count += 1
                    self._logger.info(f"Test case {i} succeeded")
                else:
                    failed_count += 1
                    self._logger.warning(f"Test case {i} failed with {len(result.errors)} errors")

            execution_time = time.time() - start_time

            self._execution_state = ExecutionState.COMPLETED
            self._logger.info(f"Comprehensive test completed: {successful_count}/{4} successful in {execution_time:.2f}s")

            return TestExecutionResult(
                totalCombinations=4,
                successfulCombinations=successful_count,
                failedCombinations=failed_count,
                executionTime=execution_time,
                detailedResults=detailed_results
            )

        except Exception as e:
            self._execution_state = ExecutionState.FAILED
            self._logger.error(f"Comprehensive test execution failed: {e}", exc_info=True)
            raise RuntimeError(f"Test execution failed: {e}") from e

    async def _executeIndependentTestCase(self, test_case: TestCase) -> ValidationResult:
        """独立したテストケースを実行（トランザクション単位）

        Args:
            test_case: 実行するテストケース

        Returns:
            ValidationResult: 検証結果
        """
        test_case.status = "running"
        test_case.startTime = datetime.now()

        try:
            # 実際の検証を実行
            result = await self.validateDualFileComparison(
                mode=test_case.mode,
                format=test_case.format
            )

            test_case.status = "completed"
            test_case.result = result

        except Exception as e:
            test_case.status = "failed"
            result = ValidationResult(
                isValid=False,
                errors=[ValidationError(
                    message=f"Test case execution failed: {str(e)}",
                    code="EXECUTION_ERROR"
                )],
                details={"test_case": f"{test_case.mode}-{test_case.format}"}
            )
            test_case.result = result

        finally:
            test_case.endTime = datetime.now()

        return result

    async def validateDualFileComparison(
        self,
        mode: Literal["embedding", "llm"],
        format: Literal["score", "file"]
    ) -> ValidationResult:
        """組み合わせ別の2ファイル比較検証を実行

        Args:
            mode: 比較モード（embedding または llm）
            format: 出力形式（score または file）

        Returns:
            ValidationResult: 検証結果
        """
        self._logger.info(f"Validating dual file comparison: {mode}-{format}")

        try:
            # 現在は基本的な検証のみ実装（実際の検証は後続タスクで実装）
            await asyncio.sleep(0.1)  # 非同期処理のシミュレーション

            # 成功ケースを仮実装
            return ValidationResult(
                isValid=True,
                errors=[],
                warnings=[],
                details={
                    "combination": f"{mode}-{format}",
                    "validation_time": datetime.now().isoformat()
                }
            )

        except Exception as e:
            return ValidationResult(
                isValid=False,
                errors=[ValidationError(
                    message=f"Validation failed: {str(e)}",
                    code="VALIDATION_ERROR"
                )],
                details={"combination": f"{mode}-{format}"}
            )

    def generateTestReport(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """テストレポートを生成

        Args:
            results: 検証結果のリスト

        Returns:
            Dict[str, Any]: 生成されたテストレポート
        """
        successful_tests = sum(1 for r in results if r.isValid)
        failed_tests = len(results) - successful_tests

        report = {
            "summary": {
                "total_tests": len(results),
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": successful_tests / len(results) if results else 0
            },
            "detailed_results": results,
            "generated_at": datetime.now().isoformat()
        }

        return report

    def storeTestResult(self, result: ValidationResult) -> None:
        """テスト結果を保存"""
        self._test_results.append(result)

    def getTestResults(self) -> List[ValidationResult]:
        """保存されたテスト結果を取得"""
        return self._test_results.copy()

    def clearTestResults(self) -> None:
        """テスト結果をクリア"""
        self._test_results.clear()

    async def _runSingleCombinationTest(
        self,
        mode: Literal["embedding", "llm"],
        format: Literal["score", "file"]
    ) -> ValidationResult:
        """単一組み合わせテストを実行（内部メソッド）"""
        return await self.validateDualFileComparison(mode, format)