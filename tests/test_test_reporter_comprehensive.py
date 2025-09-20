"""Test Reporter Comprehensive テストスイート

Task 13.5の要件に対応：
- 4つの組み合わせテスト結果の集約とレポート生成システムを構築
- ComprehensiveTestReport（実行サマリー、組み合わせ結果、パフォーマンス指標）の実装
- エラー分析（ErrorAnalysis）と推奨事項（recommendations）の自動生成機能
- markdown/json/html形式での結果エクスポート機能を実装
- テストレポートの自動保存とファイル管理機能を追加

Requirements: 10.10, 10.12
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class MockTestCaseResult:
    """テストケース結果（テスト用）"""
    isSuccess: bool
    testCaseId: str
    executionTime: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class TestTestReporterComprehensive:
    """Test Reporter Comprehensive テストクラス"""

    def test_test_reporter_comprehensive_initialization(self):
        """Test Reporter Comprehensiveが正しく初期化されること"""
        # RED: まだ実装されていないので失敗する
        from src.test_reporter_comprehensive import TestReporterComprehensive

        reporter = TestReporterComprehensive()
        assert reporter is not None

    def test_comprehensive_test_report_interface_definition(self):
        """ComprehensiveTestReportインターフェースが正しく定義されていること"""
        # RED: まだ実装されていないので失敗する
        from src.test_reporter_comprehensive import ComprehensiveTestReport

        report = ComprehensiveTestReport(
            execution_summary={
                "total_combinations": 4,
                "passed_combinations": 3,
                "failed_combinations": 1,
                "execution_time": 125.5
            },
            combination_results=[
                {
                    "combination_id": "embedding_score",
                    "method": "embedding",
                    "output_format": "score",
                    "status": "passed",
                    "execution_time": 30.2
                }
            ],
            performance_metrics={
                "average_response_time": 45.8,
                "total_requests": 4,
                "success_rate": 0.75
            }
        )

        assert report.execution_summary["total_combinations"] == 4
        assert len(report.combination_results) == 1
        assert report.performance_metrics["success_rate"] == 0.75

    def test_error_analysis_interface_definition(self):
        """ErrorAnalysisインターフェースが正しく定義されていること"""
        # RED: まだ実装されていないので失敗する
        from src.test_reporter_comprehensive import ErrorAnalysis

        analysis = ErrorAnalysis(
            error_summary={
                "total_errors": 3,
                "error_categories": ["endpoint_mismatch", "validation_failure"],
                "most_common_error": "endpoint_mismatch"
            },
            detailed_errors=[
                {
                    "error_type": "endpoint_mismatch",
                    "message": "Expected /api/compare/dual, got /api/compare/single",
                    "combination": "embedding_score",
                    "timestamp": "2025-01-20T10:30:00Z"
                }
            ],
            recommendations=[
                "Check endpoint configuration for embedding_score combination",
                "Verify API routing is correctly implemented"
            ]
        )

        assert analysis.error_summary["total_errors"] == 3
        assert len(analysis.detailed_errors) == 1
        assert len(analysis.recommendations) == 2

    def test_aggregate_test_results_functionality(self):
        """テスト結果の集約機能が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.test_reporter_comprehensive import TestReporterComprehensive

        reporter = TestReporterComprehensive()

        # 4つの組み合わせの結果をモック
        test_results = [
            MockTestCaseResult(
                isSuccess=True,
                testCaseId="embedding_score",
                executionTime=30.2,
                errors=[],
                warnings=[],
                details={"method": "embedding", "format": "score"}
            ),
            MockTestCaseResult(
                isSuccess=False,
                testCaseId="embedding_file",
                executionTime=25.8,
                errors=["Endpoint mismatch"],
                warnings=[],
                details={"method": "embedding", "format": "file"}
            )
        ]

        comprehensive_report = reporter.aggregateTestResults(test_results)

        assert comprehensive_report is not None
        assert hasattr(comprehensive_report, 'execution_summary')
        assert hasattr(comprehensive_report, 'combination_results')
        assert hasattr(comprehensive_report, 'performance_metrics')

    def test_generate_error_analysis_functionality(self):
        """エラー分析生成機能が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.test_reporter_comprehensive import TestReporterComprehensive

        reporter = TestReporterComprehensive()

        # エラーを含むテスト結果
        test_results = [
            MockTestCaseResult(
                isSuccess=False,
                testCaseId="llm_score",
                executionTime=45.3,
                errors=["Endpoint validation failed", "Response timeout"],
                warnings=["Missing model_name in metadata"],
                details={"method": "llm", "format": "score"}
            )
        ]

        error_analysis = reporter.generateErrorAnalysis(test_results)

        assert error_analysis is not None
        assert hasattr(error_analysis, 'error_summary')
        assert hasattr(error_analysis, 'detailed_errors')
        assert hasattr(error_analysis, 'recommendations')

    def test_export_markdown_format_functionality(self):
        """Markdown形式でのエクスポート機能が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.test_reporter_comprehensive import TestReporterComprehensive, ComprehensiveTestReport

        reporter = TestReporterComprehensive()

        # テストレポートのモック
        test_report = ComprehensiveTestReport(
            execution_summary={
                "total_combinations": 4,
                "passed_combinations": 3,
                "failed_combinations": 1,
                "execution_time": 125.5,
                "timestamp": "2025-01-20T10:30:00Z"
            },
            combination_results=[],
            performance_metrics={}
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_report.md"

            success = reporter.exportToMarkdown(test_report, str(output_path))

            assert success is True
            assert output_path.exists()

            # ファイル内容の確認
            content = output_path.read_text()
            assert "# Test Execution Report" in content
            assert "**Total Combinations**: 4" in content

    def test_export_json_format_functionality(self):
        """JSON形式でのエクスポート機能が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.test_reporter_comprehensive import TestReporterComprehensive, ComprehensiveTestReport

        reporter = TestReporterComprehensive()

        test_report = ComprehensiveTestReport(
            execution_summary={
                "total_combinations": 4,
                "passed_combinations": 3,
                "failed_combinations": 1
            },
            combination_results=[],
            performance_metrics={}
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_report.json"

            success = reporter.exportToJSON(test_report, str(output_path))

            assert success is True
            assert output_path.exists()

            # JSON内容の確認
            with open(output_path, 'r') as f:
                data = json.load(f)
            assert data["execution_summary"]["total_combinations"] == 4

    def test_export_html_format_functionality(self):
        """HTML形式でのエクスポート機能が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.test_reporter_comprehensive import TestReporterComprehensive, ComprehensiveTestReport

        reporter = TestReporterComprehensive()

        test_report = ComprehensiveTestReport(
            execution_summary={
                "total_combinations": 4,
                "passed_combinations": 3,
                "failed_combinations": 1
            },
            combination_results=[],
            performance_metrics={}
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_report.html"

            success = reporter.exportToHTML(test_report, str(output_path))

            assert success is True
            assert output_path.exists()

            # HTML内容の確認
            content = output_path.read_text()
            assert "<html>" in content
            assert "Test Execution Report" in content

    def test_auto_save_functionality(self):
        """自動保存機能が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.test_reporter_comprehensive import TestReporterComprehensive, ComprehensiveTestReport

        reporter = TestReporterComprehensive()

        test_report = ComprehensiveTestReport(
            execution_summary={
                "total_combinations": 4,
                "passed_combinations": 4,
                "failed_combinations": 0
            },
            combination_results=[],
            performance_metrics={}
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            reporter.setAutoSaveDirectory(temp_dir)

            success = reporter.autoSaveReport(test_report)

            assert success is True

            # 自動保存されたファイルの確認
            saved_files = list(Path(temp_dir).glob("test_report_*.json"))
            assert len(saved_files) > 0

    def test_file_management_functionality(self):
        """ファイル管理機能が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.test_reporter_comprehensive import TestReporterComprehensive

        reporter = TestReporterComprehensive()

        with tempfile.TemporaryDirectory() as temp_dir:
            reporter.setAutoSaveDirectory(temp_dir)

            # ファイル管理メソッドの存在確認
            assert hasattr(reporter, 'listSavedReports')
            assert hasattr(reporter, 'cleanupOldReports')
            assert hasattr(reporter, 'getReportHistory')

    def test_performance_metrics_calculation(self):
        """パフォーマンス指標計算が動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.test_reporter_comprehensive import TestReporterComprehensive

        reporter = TestReporterComprehensive()

        test_results = [
            MockTestCaseResult(
                isSuccess=True,
                testCaseId="embedding_score",
                executionTime=30.2,
                errors=[],
                warnings=[],
                details={"response_time": 25.5}
            ),
            MockTestCaseResult(
                isSuccess=True,
                testCaseId="llm_file",
                executionTime=55.8,
                errors=[],
                warnings=[],
                details={"response_time": 48.3}
            )
        ]

        metrics = reporter.calculatePerformanceMetrics(test_results)

        assert metrics is not None
        assert "average_response_time" in metrics
        assert "total_execution_time" in metrics
        assert "success_rate" in metrics

    def test_comprehensive_integration_test(self):
        """包括的な統合テストが動作すること"""
        # RED: まだ実装されていないので失敗する
        from src.test_reporter_comprehensive import TestReporterComprehensive

        reporter = TestReporterComprehensive()

        # 完全な4つの組み合わせテスト結果
        test_results = [
            MockTestCaseResult(
                isSuccess=True,
                testCaseId="embedding_score",
                executionTime=30.2,
                errors=[],
                warnings=[],
                details={"method": "embedding", "format": "score", "endpoint": "/api/compare/dual"}
            ),
            MockTestCaseResult(
                isSuccess=True,
                testCaseId="embedding_file",
                executionTime=35.1,
                errors=[],
                warnings=[],
                details={"method": "embedding", "format": "file", "endpoint": "/api/compare/dual"}
            ),
            MockTestCaseResult(
                isSuccess=True,
                testCaseId="llm_score",
                executionTime=45.8,
                errors=[],
                warnings=["Missing model_name"],
                details={"method": "llm", "format": "score", "endpoint": "/api/compare/dual/llm"}
            ),
            MockTestCaseResult(
                isSuccess=False,
                testCaseId="llm_file",
                executionTime=25.3,
                errors=["Endpoint validation failed"],
                warnings=[],
                details={"method": "llm", "format": "file", "endpoint": "/api/compare/dual/llm"}
            )
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            reporter.setAutoSaveDirectory(temp_dir)

            # 包括的レポート生成
            comprehensive_report = reporter.aggregateTestResults(test_results)
            error_analysis = reporter.generateErrorAnalysis(test_results)

            # 全形式でエクスポート
            md_path = Path(temp_dir) / "full_report.md"
            json_path = Path(temp_dir) / "full_report.json"
            html_path = Path(temp_dir) / "full_report.html"

            md_success = reporter.exportToMarkdown(comprehensive_report, str(md_path))
            json_success = reporter.exportToJSON(comprehensive_report, str(json_path))
            html_success = reporter.exportToHTML(comprehensive_report, str(html_path))

            assert md_success is True
            assert json_success is True
            assert html_success is True
            assert md_path.exists()
            assert json_path.exists()
            assert html_path.exists()