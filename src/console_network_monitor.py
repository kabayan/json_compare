"""コンソールとネットワーク監視マネージャー

WebUIのコンソールメッセージとネットワーク通信を監視するマネージャークラス。
Task 7の実装に対応。
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from src.mcp_wrapper import MCPTestExecutor, PlaywrightMCPWrapper
from datetime import datetime


@dataclass
class JavaScriptErrorResult:
    """JavaScriptエラー検出結果"""
    success: bool
    errors_detected: bool = False
    error_messages: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class WarningCollectionResult:
    """警告メッセージ収集結果"""
    success: bool
    warnings_found: bool = False
    warning_messages: List[Dict[str, Any]] = field(default_factory=list)
    warning_count: int = 0


@dataclass
class ConsoleRecordingResult:
    """コンソール記録結果"""
    success: bool
    recording_id: str = ""
    recording_active: bool = False


@dataclass
class ConsoleLogsResult:
    """コンソールログ結果"""
    success: bool
    logs: List[Dict[str, Any]] = field(default_factory=list)
    log_count: int = 0
    has_errors: bool = False
    has_warnings: bool = False


@dataclass
class ConsoleReportResult:
    """コンソールレポート結果"""
    success: bool
    report_generated: bool = False
    total_messages: int = 0
    error_count: int = 0
    warning_count: int = 0
    critical_errors: List[str] = field(default_factory=list)
    report_path: str = ""


@dataclass
class ConsoleErrorVerificationResult:
    """コンソールエラー検証結果"""
    success: bool
    test_failed: bool = False
    failure_reason: str = ""
    detected_errors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class APIRequestRecordResult:
    """APIリクエスト記録結果"""
    success: bool
    requests: List[Dict[str, Any]] = field(default_factory=list)
    has_failed_requests: bool = False


@dataclass
class HTTPStatusValidationResult:
    """HTTPステータス検証結果"""
    success: bool
    success_count: int = 0
    client_error_count: int = 0
    server_error_count: int = 0
    has_errors: bool = False
    error_responses: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ResponseTimeResult:
    """レスポンスタイム測定結果"""
    success: bool
    measurements: List[Dict[str, Any]] = field(default_factory=list)
    average_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = 0.0
    slow_requests_count: int = 0


@dataclass
class DialogDetectionResult:
    """ダイアログ検出結果"""
    success: bool
    dialog_detected: bool = False
    dialog_type: str = ""
    dialog_text: str = ""


@dataclass
class DialogHandleResult:
    """ダイアログ処理結果"""
    success: bool
    dialog_handled: bool = False
    action: str = ""


@dataclass
class NetworkErrorResult:
    """ネットワークエラー結果"""
    success: bool
    has_errors: bool = False
    error_types: List[str] = field(default_factory=list)


@dataclass
class NetworkRetryResult:
    """ネットワークリトライ結果"""
    success: bool
    retry_count: int = 0
    successful_retries: int = 0
    retry_success_rate: float = 0.0


@dataclass
class MonitoringStartResult:
    """監視開始結果"""
    success: bool
    monitoring_active: bool = False
    session_id: str = ""


@dataclass
class MonitoringDataResult:
    """監視データ結果"""
    success: bool
    console_errors: int = 0
    console_warnings: int = 0
    network_requests: int = 0
    network_failures: int = 0


@dataclass
class MonitoringReportResult:
    """監視レポート結果"""
    success: bool
    report_created: bool = False
    report_path: str = ""


class ConsoleNetworkMonitor:
    """コンソールとネットワーク監視マネージャー"""

    def __init__(self):
        self.executor = MCPTestExecutor()
        # MCPラッパーを初期化
        self.executor._mcp_wrapper = PlaywrightMCPWrapper()

    async def _ensure_initialized(self):
        """ラッパーが初期化されていることを確認する"""
        if self.executor._mcp_wrapper and not self.executor._mcp_wrapper.is_initialized:
            await self.executor._mcp_wrapper.initialize()

    async def detect_javascript_errors(self) -> JavaScriptErrorResult:
        """JavaScriptエラーを検出する"""
        try:
            await self._ensure_initialized()

            messages_result = await self.executor._mcp_wrapper.get_console_messages()

            if messages_result.get('success'):
                messages = messages_result.get('messages', [])
                errors = [msg for msg in messages if msg.get('type') == 'error']

                return JavaScriptErrorResult(
                    success=True,
                    errors_detected=len(errors) > 0,
                    error_messages=errors
                )

            return JavaScriptErrorResult(success=False)

        except Exception as e:
            return JavaScriptErrorResult(success=False)

    async def collect_warning_messages(self) -> WarningCollectionResult:
        """警告メッセージを収集する"""
        try:
            await self._ensure_initialized()

            messages_result = await self.executor._mcp_wrapper.get_console_messages()

            if messages_result.get('success'):
                messages = messages_result.get('messages', [])
                warnings = [msg for msg in messages if msg.get('type') == 'warning']

                return WarningCollectionResult(
                    success=True,
                    warnings_found=len(warnings) > 0,
                    warning_messages=warnings,
                    warning_count=len(warnings)
                )

            return WarningCollectionResult(success=False)

        except Exception as e:
            return WarningCollectionResult(success=False)

    async def start_console_recording(self) -> ConsoleRecordingResult:
        """コンソール記録を開始する"""
        try:
            await self._ensure_initialized()

            start_result = await self.executor._mcp_wrapper.start_console_recording()

            if start_result.get('success'):
                return ConsoleRecordingResult(
                    success=True,
                    recording_id=start_result.get('recording_id', ''),
                    recording_active=start_result.get('recording_started', False)
                )

            return ConsoleRecordingResult(success=False)

        except Exception as e:
            return ConsoleRecordingResult(success=False)

    async def get_console_logs(self, recording_id: str) -> ConsoleLogsResult:
        """コンソールログを取得する"""
        try:
            await self._ensure_initialized()

            logs_result = await self.executor._mcp_wrapper.get_recorded_logs()

            if logs_result.get('success'):
                logs = logs_result.get('logs', [])

                has_errors = any(log.get('type') == 'error' for log in logs)
                has_warnings = any(log.get('type') == 'warning' for log in logs)

                return ConsoleLogsResult(
                    success=True,
                    logs=logs,
                    log_count=logs_result.get('total_count', len(logs)),
                    has_errors=has_errors,
                    has_warnings=has_warnings
                )

            return ConsoleLogsResult(success=False)

        except Exception as e:
            return ConsoleLogsResult(success=False)

    async def generate_console_report(self) -> ConsoleReportResult:
        """コンソールレポートを生成する"""
        try:
            await self._ensure_initialized()

            report_result = await self.executor._mcp_wrapper.generate_console_report()

            if report_result.get('success'):
                report = report_result.get('report', {})
                summary = report.get('summary', {})

                return ConsoleReportResult(
                    success=True,
                    report_generated=True,
                    total_messages=summary.get('total_messages', 0),
                    error_count=summary.get('errors', 0),
                    warning_count=summary.get('warnings', 0),
                    critical_errors=report.get('critical_errors', []),
                    report_path=report.get('report_path', '')
                )

            return ConsoleReportResult(success=False)

        except Exception as e:
            return ConsoleReportResult(success=False)

    async def verify_no_console_errors(self) -> ConsoleErrorVerificationResult:
        """コンソールエラーがないことを検証する"""
        try:
            await self._ensure_initialized()

            # fail_on_errorを設定
            await self.executor._mcp_wrapper.set_fail_on_error()

            # コンソールメッセージを取得
            messages_result = await self.executor._mcp_wrapper.get_console_messages()

            if messages_result.get('success'):
                messages = messages_result.get('messages', [])
                errors = [msg for msg in messages if msg.get('type') == 'error']

                if errors:
                    return ConsoleErrorVerificationResult(
                        success=False,
                        test_failed=True,
                        failure_reason='Console errors detected',
                        detected_errors=errors
                    )

                return ConsoleErrorVerificationResult(success=True)

            return ConsoleErrorVerificationResult(success=False)

        except Exception as e:
            return ConsoleErrorVerificationResult(success=False)

    async def record_api_requests(self) -> APIRequestRecordResult:
        """APIリクエストを記録する"""
        try:
            await self._ensure_initialized()

            requests_result = await self.executor._mcp_wrapper.get_network_requests()

            if requests_result.get('success'):
                requests = requests_result.get('requests', [])
                has_failed = any(req.get('status', 200) >= 400 for req in requests)

                return APIRequestRecordResult(
                    success=True,
                    requests=requests,
                    has_failed_requests=has_failed
                )

            return APIRequestRecordResult(success=False)

        except Exception as e:
            return APIRequestRecordResult(success=False)

    async def validate_http_status_codes(self) -> HTTPStatusValidationResult:
        """HTTPステータスコードを検証する"""
        try:
            await self._ensure_initialized()

            responses_result = await self.executor._mcp_wrapper.get_network_responses()

            if responses_result.get('success'):
                responses = responses_result.get('responses', [])

                success_count = sum(1 for r in responses if 200 <= r.get('status', 0) < 300)
                client_error_count = sum(1 for r in responses if 400 <= r.get('status', 0) < 500)
                server_error_count = sum(1 for r in responses if r.get('status', 0) >= 500)
                error_responses = [r for r in responses if r.get('status', 0) >= 400]

                return HTTPStatusValidationResult(
                    success=True,
                    success_count=success_count,
                    client_error_count=client_error_count,
                    server_error_count=server_error_count,
                    has_errors=len(error_responses) > 0,
                    error_responses=error_responses
                )

            return HTTPStatusValidationResult(success=False)

        except Exception as e:
            return HTTPStatusValidationResult(success=False)

    async def measure_api_response_times(self) -> ResponseTimeResult:
        """APIレスポンスタイムを測定する"""
        try:
            await self._ensure_initialized()

            times_result = await self.executor._mcp_wrapper.measure_response_times()

            if times_result.get('success'):
                measurements = times_result.get('measurements', [])
                slow_count = sum(1 for m in measurements if m.get('time', 0) > 2.0)

                return ResponseTimeResult(
                    success=True,
                    measurements=measurements,
                    average_response_time=times_result.get('average_time', 0.0),
                    max_response_time=times_result.get('max_time', 0.0),
                    min_response_time=times_result.get('min_time', 0.0),
                    slow_requests_count=slow_count
                )

            return ResponseTimeResult(success=False)

        except Exception as e:
            return ResponseTimeResult(success=False)

    async def detect_unexpected_dialog(self) -> DialogDetectionResult:
        """予期しないダイアログを検出する"""
        try:
            await self._ensure_initialized()

            dialog_result = await self.executor._mcp_wrapper.detect_dialog()

            if dialog_result.get('success') and dialog_result.get('dialog_present'):
                return DialogDetectionResult(
                    success=True,
                    dialog_detected=True,
                    dialog_type=dialog_result.get('dialog_type', ''),
                    dialog_text=dialog_result.get('dialog_text', '')
                )

            return DialogDetectionResult(success=True, dialog_detected=False)

        except Exception as e:
            return DialogDetectionResult(success=False)

    async def handle_dialog(self, action: str) -> DialogHandleResult:
        """ダイアログを処理する"""
        try:
            await self._ensure_initialized()

            handle_result = await self.executor._mcp_wrapper.handle_dialog()

            if handle_result.get('success'):
                return DialogHandleResult(
                    success=True,
                    dialog_handled=handle_result.get('dialog_handled', False),
                    action=handle_result.get('action', action)
                )

            return DialogHandleResult(success=False)

        except Exception as e:
            return DialogHandleResult(success=False)

    async def detect_network_errors(self) -> NetworkErrorResult:
        """ネットワークエラーを検出する"""
        try:
            await self._ensure_initialized()

            error_result = await self.executor._mcp_wrapper.detect_network_errors()

            if error_result.get('success') and error_result.get('errors_detected'):
                return NetworkErrorResult(
                    success=True,
                    has_errors=True,
                    error_types=error_result.get('error_types', [])
                )

            return NetworkErrorResult(success=True, has_errors=False)

        except Exception as e:
            return NetworkErrorResult(success=False)

    async def retry_failed_network_requests(self) -> NetworkRetryResult:
        """失敗したネットワークリクエストをリトライする"""
        try:
            await self._ensure_initialized()

            retry_result = await self.executor._mcp_wrapper.retry_failed_requests()

            if retry_result.get('success'):
                retry_count = retry_result.get('retry_count', 0)
                successful = retry_result.get('successful_retries', 0)

                success_rate = successful / retry_count if retry_count > 0 else 0

                return NetworkRetryResult(
                    success=True,
                    retry_count=retry_count,
                    successful_retries=successful,
                    retry_success_rate=success_rate
                )

            return NetworkRetryResult(success=False)

        except Exception as e:
            return NetworkRetryResult(success=False)

    async def start_full_monitoring(self) -> MonitoringStartResult:
        """完全な監視を開始する"""
        try:
            await self._ensure_initialized()

            start_result = await self.executor._mcp_wrapper.start_monitoring()

            if start_result.get('success'):
                return MonitoringStartResult(
                    success=True,
                    monitoring_active=True,
                    session_id=start_result.get('session_id', '')
                )

            return MonitoringStartResult(success=False)

        except Exception as e:
            return MonitoringStartResult(success=False)

    async def collect_all_data(self, session_id: str) -> MonitoringDataResult:
        """すべての監視データを収集する"""
        try:
            await self._ensure_initialized()

            data_result = await self.executor._mcp_wrapper.collect_monitoring_data()

            if data_result.get('success'):
                console_data = data_result.get('console_data', {})
                network_data = data_result.get('network_data', {})

                return MonitoringDataResult(
                    success=True,
                    console_errors=console_data.get('errors', 0),
                    console_warnings=console_data.get('warnings', 0),
                    network_requests=network_data.get('requests', 0),
                    network_failures=network_data.get('failures', 0)
                )

            return MonitoringDataResult(success=False)

        except Exception as e:
            return MonitoringDataResult(success=False)

    async def generate_final_report(self, session_id: str) -> MonitoringReportResult:
        """最終レポートを生成する"""
        try:
            await self._ensure_initialized()

            report_result = await self.executor._mcp_wrapper.generate_monitoring_report()

            if report_result.get('success'):
                return MonitoringReportResult(
                    success=True,
                    report_created=report_result.get('report_generated', False),
                    report_path=report_result.get('report_path', '')
                )

            return MonitoringReportResult(success=False)

        except Exception as e:
            return MonitoringReportResult(success=False)