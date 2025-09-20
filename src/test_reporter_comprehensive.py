"""Test Reporter Comprehensive for Dual File Comparison

Task 13.5の実装：
- 4つの組み合わせテスト結果の集約とレポート生成システムを構築
- ComprehensiveTestReport（実行サマリー、組み合わせ結果、パフォーマンス指標）の実装
- エラー分析（ErrorAnalysis）と推奨事項（recommendations）の自動生成機能
- markdown/json/html形式での結果エクスポート機能を実装
- テストレポートの自動保存とファイル管理機能を追加

Requirements: 10.10, 10.12 - 2ファイル比較検証システム

Modules:
- TestReporterComprehensive: メインのテストレポート生成クラス
- ComprehensiveTestReport: 包括的テストレポートのデータクラス
- ErrorAnalysis: エラー分析のデータクラス

Design Patterns:
- Builder Pattern: 複雑なレポート構造の構築
- Strategy Pattern: 異なるエクスポート形式（markdown/json/html）
- Template Method Pattern: 共通のレポート生成フローと特化した出力処理

Key Features:
- 4-combination test result aggregation with comprehensive analysis
- Performance metrics calculation with timing and success rate
- Multi-format export (markdown, json, html) with template-based generation
- Automatic report saving with timestamp-based file management
- Error analysis with categorization and recommendation generation
- Report history tracking and cleanup functionality
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
import tempfile

# テストケース結果の型定義（互換性のため）
from typing import Any, Protocol

class TestCaseResult(Protocol):
    """テストケース結果のプロトコル"""
    isSuccess: bool
    testCaseId: str
    executionTime: float
    errors: List[str]
    warnings: List[str]
    details: Dict[str, Any]


@dataclass
class ComprehensiveTestReport:
    """包括的テストレポート

    Attributes:
        execution_summary: 実行サマリー（合計、成功、失敗、実行時間）
        combination_results: 組み合わせ別結果
        performance_metrics: パフォーマンス指標
        error_analysis: エラー分析（オプション）
        timestamp: レポート生成時刻
    """
    execution_summary: Dict[str, Any]
    combination_results: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    error_analysis: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ErrorAnalysis:
    """エラー分析

    Attributes:
        error_summary: エラーサマリー（総数、カテゴリ、最頻発エラー）
        detailed_errors: 詳細エラー情報
        recommendations: 推奨事項
    """
    error_summary: Dict[str, Any]
    detailed_errors: List[Dict[str, Any]]
    recommendations: List[str]


class TestReporterComprehensiveError(Exception):
    """Test Reporter Comprehensive専用エラークラス"""
    pass


class TestReporterComprehensive:
    """Test Reporter Comprehensive

    4つの組み合わせテスト結果の集約とレポート生成システム。
    包括的なエラー分析と推奨事項の自動生成を行う。
    """

    def __init__(self):
        """テストレポーター包括の初期化"""
        self._logger = logging.getLogger(__name__)
        self._auto_save_directory = None

    def aggregateTestResults(
        self,
        test_results: List[TestCaseResult]
    ) -> ComprehensiveTestReport:
        """テスト結果の集約

        Args:
            test_results: 4つの組み合わせテストの実行結果

        Returns:
            ComprehensiveTestReport: 包括的テストレポート
        """
        try:
            self._logger.info(f"Aggregating {len(test_results)} test results")

            # 実行サマリーの計算
            total_combinations = len(test_results)
            passed_combinations = sum(1 for result in test_results if result.isSuccess)
            failed_combinations = total_combinations - passed_combinations
            total_execution_time = sum(result.executionTime for result in test_results)

            execution_summary = {
                "total_combinations": total_combinations,
                "passed_combinations": passed_combinations,
                "failed_combinations": failed_combinations,
                "execution_time": round(total_execution_time, 2),
                "timestamp": datetime.now().isoformat(),
                "success_rate": round(passed_combinations / total_combinations, 3) if total_combinations > 0 else 0.0
            }

            # 組み合わせ別結果の構築
            combination_results = []
            for result in test_results:
                combination_result = {
                    "combination_id": result.testCaseId,
                    "method": result.details.get("method", "unknown"),
                    "output_format": result.details.get("format", "unknown"),
                    "status": "passed" if result.isSuccess else "failed",
                    "execution_time": round(result.executionTime, 2),
                    "error_count": len(result.errors),
                    "warning_count": len(result.warnings),
                    "endpoint": result.details.get("endpoint", "unknown")
                }
                combination_results.append(combination_result)

            # パフォーマンス指標の計算
            performance_metrics = self.calculatePerformanceMetrics(test_results)

            return ComprehensiveTestReport(
                execution_summary=execution_summary,
                combination_results=combination_results,
                performance_metrics=performance_metrics
            )

        except Exception as e:
            self._logger.error(f"Failed to aggregate test results: {e}")
            raise TestReporterComprehensiveError(f"Failed to aggregate test results: {e}") from e

    def generateErrorAnalysis(
        self,
        test_results: List[TestCaseResult]
    ) -> ErrorAnalysis:
        """エラー分析の生成

        Args:
            test_results: テスト実行結果

        Returns:
            ErrorAnalysis: エラー分析
        """
        try:
            self._logger.info("Generating error analysis")

            # 全エラーの収集
            all_errors = []
            error_categories = set()

            for result in test_results:
                for error in result.errors:
                    error_categories.add(self._categorizeError(error))
                    all_errors.append({
                        "error_type": self._categorizeError(error),
                        "message": error,
                        "combination": result.testCaseId,
                        "timestamp": datetime.now().isoformat()
                    })

            # エラーサマリーの構築
            total_errors = len(all_errors)
            most_common_error = self._findMostCommonError(all_errors) if all_errors else None

            error_summary = {
                "total_errors": total_errors,
                "error_categories": list(error_categories),
                "most_common_error": most_common_error
            }

            # 推奨事項の生成
            recommendations = self._generateRecommendations(test_results, all_errors)

            return ErrorAnalysis(
                error_summary=error_summary,
                detailed_errors=all_errors,
                recommendations=recommendations
            )

        except Exception as e:
            self._logger.error(f"Failed to generate error analysis: {e}")
            raise TestReporterComprehensiveError(f"Failed to generate error analysis: {e}") from e

    def calculatePerformanceMetrics(
        self,
        test_results: List[TestCaseResult]
    ) -> Dict[str, Any]:
        """パフォーマンス指標の計算

        Args:
            test_results: テスト実行結果

        Returns:
            Dict[str, Any]: パフォーマンス指標
        """
        if not test_results:
            return {
                "average_response_time": 0.0,
                "total_execution_time": 0.0,
                "total_requests": 0,
                "success_rate": 0.0
            }

        # レスポンス時間の計算
        response_times = []
        for result in test_results:
            response_time = result.details.get("response_time")
            if response_time is not None:
                response_times.append(response_time)

        average_response_time = sum(response_times) / len(response_times) if response_times else 0.0

        # 合計実行時間
        total_execution_time = sum(result.executionTime for result in test_results)

        # 成功率
        successful_count = sum(1 for result in test_results if result.isSuccess)
        success_rate = successful_count / len(test_results)

        return {
            "average_response_time": round(average_response_time, 2),
            "total_execution_time": round(total_execution_time, 2),
            "total_requests": len(test_results),
            "success_rate": round(success_rate, 3)
        }

    def exportToMarkdown(
        self,
        report: ComprehensiveTestReport,
        output_path: str
    ) -> bool:
        """Markdown形式でのエクスポート

        Args:
            report: 包括的テストレポート
            output_path: 出力ファイルパス

        Returns:
            bool: エクスポート成功の場合True
        """
        try:
            self._logger.info(f"Exporting report to markdown: {output_path}")

            markdown_content = self._generateMarkdownContent(report)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            self._logger.info(f"Markdown export completed: {output_path}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to export to markdown: {e}")
            return False

    def exportToJSON(
        self,
        report: ComprehensiveTestReport,
        output_path: str
    ) -> bool:
        """JSON形式でのエクスポート

        Args:
            report: 包括的テストレポート
            output_path: 出力ファイルパス

        Returns:
            bool: エクスポート成功の場合True
        """
        try:
            self._logger.info(f"Exporting report to JSON: {output_path}")

            # dataclassをdictに変換
            report_dict = {
                "execution_summary": report.execution_summary,
                "combination_results": report.combination_results,
                "performance_metrics": report.performance_metrics,
                "error_analysis": report.error_analysis,
                "timestamp": report.timestamp
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False)

            self._logger.info(f"JSON export completed: {output_path}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to export to JSON: {e}")
            return False

    def exportToHTML(
        self,
        report: ComprehensiveTestReport,
        output_path: str
    ) -> bool:
        """HTML形式でのエクスポート

        Args:
            report: 包括的テストレポート
            output_path: 出力ファイルパス

        Returns:
            bool: エクスポート成功の場合True
        """
        try:
            self._logger.info(f"Exporting report to HTML: {output_path}")

            html_content = self._generateHTMLContent(report)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self._logger.info(f"HTML export completed: {output_path}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to export to HTML: {e}")
            return False

    def setAutoSaveDirectory(self, directory: str) -> None:
        """自動保存ディレクトリの設定

        Args:
            directory: 保存先ディレクトリパス
        """
        self._auto_save_directory = directory
        self._logger.info(f"Auto save directory set to: {directory}")

    def autoSaveReport(self, report: ComprehensiveTestReport) -> bool:
        """レポートの自動保存

        Args:
            report: 包括的テストレポート

        Returns:
            bool: 保存成功の場合True
        """
        if not self._auto_save_directory:
            self._logger.warning("Auto save directory not set")
            return False

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.json"
            output_path = Path(self._auto_save_directory) / filename

            return self.exportToJSON(report, str(output_path))

        except Exception as e:
            self._logger.error(f"Failed to auto save report: {e}")
            return False

    def listSavedReports(self) -> List[str]:
        """保存されたレポートの一覧

        Returns:
            List[str]: レポートファイルパスのリスト
        """
        if not self._auto_save_directory:
            return []

        try:
            directory = Path(self._auto_save_directory)
            if not directory.exists():
                return []

            report_files = list(directory.glob("test_report_*.json"))
            return [str(f) for f in sorted(report_files)]

        except Exception as e:
            self._logger.error(f"Failed to list saved reports: {e}")
            return []

    def cleanupOldReports(self, keep_count: int = 10) -> int:
        """古いレポートのクリーンアップ

        Args:
            keep_count: 保持するレポート数

        Returns:
            int: 削除されたレポート数
        """
        if not self._auto_save_directory:
            return 0

        try:
            saved_reports = self.listSavedReports()
            if len(saved_reports) <= keep_count:
                return 0

            # 古いレポートを削除
            reports_to_delete = saved_reports[:-keep_count]
            deleted_count = 0

            for report_path in reports_to_delete:
                try:
                    Path(report_path).unlink()
                    deleted_count += 1
                except Exception as e:
                    self._logger.warning(f"Failed to delete report {report_path}: {e}")

            self._logger.info(f"Cleaned up {deleted_count} old reports")
            return deleted_count

        except Exception as e:
            self._logger.error(f"Failed to cleanup old reports: {e}")
            return 0

    def getReportHistory(self) -> List[Dict[str, Any]]:
        """レポート履歴の取得

        Returns:
            List[Dict[str, Any]]: レポート履歴情報
        """
        saved_reports = self.listSavedReports()
        history = []

        for report_path in saved_reports:
            try:
                path_obj = Path(report_path)
                stat = path_obj.stat()

                history.append({
                    "path": report_path,
                    "filename": path_obj.name,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

            except Exception as e:
                self._logger.warning(f"Failed to get info for report {report_path}: {e}")

        return history

    # プライベートメソッド

    def _categorizeError(self, error_message: str) -> str:
        """エラーメッセージのカテゴリ化"""
        error_lower = error_message.lower()

        if "endpoint" in error_lower:
            return "endpoint_mismatch"
        elif "validation" in error_lower:
            return "validation_failure"
        elif "timeout" in error_lower:
            return "timeout_error"
        elif "connection" in error_lower:
            return "connection_error"
        else:
            return "other_error"

    def _findMostCommonError(self, errors: List[Dict[str, Any]]) -> Optional[str]:
        """最頻発エラーの特定"""
        if not errors:
            return None

        error_counts = {}
        for error in errors:
            error_type = error["error_type"]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return max(error_counts, key=error_counts.get)

    def _generateRecommendations(
        self,
        test_results: List[TestCaseResult],
        errors: List[Dict[str, Any]]
    ) -> List[str]:
        """推奨事項の生成"""
        recommendations = []

        # エラータイプ別の推奨事項
        error_types = set(error["error_type"] for error in errors)

        if "endpoint_mismatch" in error_types:
            recommendations.append("Check endpoint configuration for dual file comparison")
            recommendations.append("Verify API routing is correctly implemented")

        if "validation_failure" in error_types:
            recommendations.append("Review API response validation rules")
            recommendations.append("Check metadata consistency requirements")

        if "timeout_error" in error_types:
            recommendations.append("Consider increasing timeout values for LLM operations")
            recommendations.append("Optimize API response times")

        # 失敗した組み合わせ別の推奨事項
        failed_combinations = [r for r in test_results if not r.isSuccess]
        if failed_combinations:
            for combo in failed_combinations:
                method = combo.details.get("method", "unknown")
                format_type = combo.details.get("format", "unknown")
                recommendations.append(f"Investigate {method} + {format_type} combination failures")

        return recommendations

    def _generateMarkdownContent(self, report: ComprehensiveTestReport) -> str:
        """Markdownコンテンツの生成"""
        content = f"""# Test Execution Report

Generated: {report.timestamp}

## Execution Summary

- **Total Combinations**: {report.execution_summary['total_combinations']}
- **Passed**: {report.execution_summary['passed_combinations']}
- **Failed**: {report.execution_summary['failed_combinations']}
- **Success Rate**: {report.execution_summary.get('success_rate', 0.0):.1%}
- **Total Execution Time**: {report.execution_summary.get('execution_time', 0.0)}s

## Performance Metrics

- **Average Response Time**: {report.performance_metrics.get('average_response_time', 0.0)}ms
- **Total Requests**: {report.performance_metrics.get('total_requests', 0)}
- **Success Rate**: {report.performance_metrics.get('success_rate', 0.0):.1%}

## Combination Results

| Combination ID | Method | Format | Status | Execution Time | Errors | Warnings |
|---------------|--------|--------|--------|---------------|--------|----------|
"""

        for result in report.combination_results:
            content += f"| {result['combination_id']} | {result['method']} | {result['output_format']} | {result['status']} | {result['execution_time']}s | {result['error_count']} | {result['warning_count']} |\n"

        if report.error_analysis:
            content += f"""
## Error Analysis

- **Total Errors**: {report.error_analysis.get('error_summary', {}).get('total_errors', 0)}
- **Error Categories**: {', '.join(report.error_analysis.get('error_summary', {}).get('error_categories', []))}

### Recommendations

"""
            for rec in report.error_analysis.get('recommendations', []):
                content += f"- {rec}\n"

        return content

    def _generateHTMLContent(self, report: ComprehensiveTestReport) -> str:
        """HTMLコンテンツの生成"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Execution Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
    </style>
</head>
<body>
    <h1>Test Execution Report</h1>
    <p>Generated: {report.timestamp}</p>

    <div class="summary">
        <h2>Execution Summary</h2>
        <ul>
            <li>Total Combinations: {report.execution_summary['total_combinations']}</li>
            <li>Passed: {report.execution_summary['passed_combinations']}</li>
            <li>Failed: {report.execution_summary['failed_combinations']}</li>
            <li>Success Rate: {report.execution_summary.get('success_rate', 0.0):.1%}</li>
            <li>Total Execution Time: {report.execution_summary.get('execution_time', 0.0)}s</li>
        </ul>
    </div>

    <h2>Combination Results</h2>
    <table>
        <tr>
            <th>Combination ID</th>
            <th>Method</th>
            <th>Format</th>
            <th>Status</th>
            <th>Execution Time</th>
            <th>Errors</th>
            <th>Warnings</th>
        </tr>
        {''.join(f'<tr><td>{r["combination_id"]}</td><td>{r["method"]}</td><td>{r["output_format"]}</td><td class="{r["status"]}">{r["status"]}</td><td>{r["execution_time"]}s</td><td>{r["error_count"]}</td><td>{r["warning_count"]}</td></tr>' for r in report.combination_results)}
    </table>
</body>
</html>"""