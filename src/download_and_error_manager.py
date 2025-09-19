"""ダウンロード機能とエラー表示管理マネージャー

WebUIのダウンロード機能とエラー表示を管理するマネージャークラス。
Task 5.2の実装に対応。
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from src.mcp_wrapper import MCPTestExecutor, PlaywrightMCPWrapper


@dataclass
class CSVDownloadResult:
    """CSVダウンロード結果"""
    success: bool
    download_started: bool = False
    download_id: str = ""
    filename: str = ""


@dataclass
class DownloadCompletionResult:
    """ダウンロード完了結果"""
    success: bool
    is_completed: bool = False
    download_path: str = ""
    file_size: int = 0


@dataclass
class CSVContentValidationResult:
    """CSV内容検証結果"""
    success: bool
    has_header: bool = False
    column_count: int = 0
    row_count: int = 0
    headers: List[str] = field(default_factory=list)
    is_valid_csv: bool = False


@dataclass
class LargeDownloadMonitorResult:
    """大量ダウンロード監視結果"""
    success: bool
    progress_updates: List[Dict[str, Any]] = field(default_factory=list)
    final_percentage: int = 0
    total_bytes: int = 0
    download_speed: Optional[float] = None
    duration: float = 0.0


@dataclass
class ErrorDisplayResult:
    """エラー表示結果"""
    success: bool
    error_displayed: bool = False
    error_message: str = ""
    error_type: str = ""
    is_visible: bool = False


@dataclass
class ErrorTrackingResult:
    """エラー追跡結果"""
    success: bool
    error_id: str = ""
    has_timestamp: bool = False
    severity: str = ""
    has_user_friendly_message: bool = False
    has_technical_details: bool = False


@dataclass
class ErrorRecoveryOptionsResult:
    """エラーリカバリオプション結果"""
    success: bool
    recovery_options: List[Dict[str, Any]] = field(default_factory=list)
    has_retry_option: bool = False
    has_upload_new_option: bool = False
    has_cancel_option: bool = False


@dataclass
class ErrorRecoveryExecutionResult:
    """エラーリカバリ実行結果"""
    success: bool
    recovery_attempted: bool = False
    recovery_successful: bool = False
    error_cleared: bool = False
    processing_resumed: bool = False


@dataclass
class DownloadWithErrorHandlingResult:
    """エラーハンドリング付きダウンロード結果"""
    success: bool
    download_failed: bool = False
    error_displayed: bool = False
    error_id: str = ""


@dataclass
class DownloadFormatOptionsResult:
    """ダウンロード形式オプション結果"""
    success: bool
    available_formats: List[Dict[str, Any]] = field(default_factory=list)
    csv_available: bool = False
    json_available: bool = False
    excel_available: bool = False


class DownloadAndErrorManager:
    """ダウンロードとエラー表示管理マネージャー"""

    def __init__(self):
        self.executor = MCPTestExecutor()
        # MCPラッパーを初期化
        self.executor._mcp_wrapper = PlaywrightMCPWrapper()

    async def _ensure_initialized(self):
        """ラッパーが初期化されていることを確認する"""
        if self.executor._mcp_wrapper and not self.executor._mcp_wrapper.is_initialized:
            await self.executor._mcp_wrapper.initialize()

    async def initiate_csv_download(self) -> CSVDownloadResult:
        """CSVダウンロードを開始する"""
        try:
            await self._ensure_initialized()

            # ダウンロードリンクをクリック
            click_result = await self.executor._mcp_wrapper.click_element(
                element="csv-download-link",
                ref="csv-download-link"
            )

            if not click_result.get('success'):
                return CSVDownloadResult(success=False)

            # ダウンロード開始を待つ
            download_result = await self.executor._mcp_wrapper.wait_for_download()

            if download_result.get('success'):
                return CSVDownloadResult(
                    success=True,
                    download_started=True,
                    download_id=download_result.get('download_id', ''),
                    filename=download_result.get('filename', '')
                )

            return CSVDownloadResult(success=False)

        except Exception as e:
            return CSVDownloadResult(success=False)

    async def verify_download_completion(self, download_id: str) -> DownloadCompletionResult:
        """ダウンロード完了を確認する"""
        try:
            await self._ensure_initialized()

            status_result = await self.executor._mcp_wrapper.check_download_status(download_id)

            if status_result.get('success') and status_result.get('status') == 'completed':
                return DownloadCompletionResult(
                    success=True,
                    is_completed=True,
                    download_path=status_result.get('download_path', ''),
                    file_size=status_result.get('file_size', 0)
                )

            return DownloadCompletionResult(success=False)

        except Exception as e:
            return DownloadCompletionResult(success=False)

    async def validate_csv_content(self, file_path: str) -> CSVContentValidationResult:
        """CSVファイル内容を検証する"""
        try:
            await self._ensure_initialized()

            content_result = await self.executor._mcp_wrapper.read_download_file(file_path)

            if content_result.get('success'):
                content = content_result.get('content', '')
                lines = content.strip().split('\n')

                if lines:
                    headers = lines[0].split(',')
                    return CSVContentValidationResult(
                        success=True,
                        has_header=True,
                        column_count=content_result.get('columns', len(headers)),
                        row_count=content_result.get('rows', len(lines)),
                        headers=headers,
                        is_valid_csv=True
                    )

            return CSVContentValidationResult(success=False)

        except Exception as e:
            return CSVContentValidationResult(success=False)

    async def monitor_large_download(self, download_id: str) -> LargeDownloadMonitorResult:
        """大量データのダウンロードを監視する"""
        try:
            await self._ensure_initialized()

            monitor_result = await self.executor._mcp_wrapper.monitor_download_progress(download_id)

            if monitor_result.get('success'):
                progress_updates = monitor_result.get('progress_updates', [])
                total_bytes = monitor_result.get('total_bytes', 0)
                duration = monitor_result.get('duration', 0)

                download_speed = None
                if duration > 0:
                    download_speed = total_bytes / duration

                return LargeDownloadMonitorResult(
                    success=True,
                    progress_updates=progress_updates,
                    final_percentage=100 if progress_updates else 0,
                    total_bytes=total_bytes,
                    download_speed=download_speed,
                    duration=duration
                )

            return LargeDownloadMonitorResult(success=False)

        except Exception as e:
            return LargeDownloadMonitorResult(success=False)

    async def verify_error_display(self) -> ErrorDisplayResult:
        """エラー表示を検証する"""
        try:
            await self._ensure_initialized()

            error_result = await self.executor._mcp_wrapper.get_error_elements()

            if error_result.get('success') and error_result.get('error_present'):
                return ErrorDisplayResult(
                    success=True,
                    error_displayed=True,
                    error_message=error_result.get('error_message', ''),
                    error_type=error_result.get('error_type', ''),
                    is_visible=error_result.get('error_container_visible', False)
                )

            return ErrorDisplayResult(success=False)

        except Exception as e:
            return ErrorDisplayResult(success=False)

    async def verify_error_id_tracking(self) -> ErrorTrackingResult:
        """エラーID追跡を検証する"""
        try:
            await self._ensure_initialized()

            details_result = await self.executor._mcp_wrapper.get_error_details()

            if details_result.get('success'):
                return ErrorTrackingResult(
                    success=True,
                    error_id=details_result.get('error_id', ''),
                    has_timestamp=bool(details_result.get('timestamp')),
                    severity=details_result.get('severity', ''),
                    has_user_friendly_message=bool(details_result.get('user_message')),
                    has_technical_details=bool(details_result.get('technical_details'))
                )

            return ErrorTrackingResult(success=False)

        except Exception as e:
            return ErrorTrackingResult(success=False)

    async def verify_error_recovery_options(self) -> ErrorRecoveryOptionsResult:
        """エラーリカバリオプションを検証する"""
        try:
            await self._ensure_initialized()

            options_result = await self.executor._mcp_wrapper.get_recovery_options()

            if options_result.get('success'):
                recovery_options = options_result.get('recovery_options', [])

                has_retry = any(opt.get('action') == 'retry' for opt in recovery_options)
                has_upload = any(opt.get('action') == 'upload_new' for opt in recovery_options)
                has_cancel = any(opt.get('action') == 'cancel' for opt in recovery_options)

                return ErrorRecoveryOptionsResult(
                    success=True,
                    recovery_options=recovery_options,
                    has_retry_option=has_retry,
                    has_upload_new_option=has_upload,
                    has_cancel_option=has_cancel
                )

            return ErrorRecoveryOptionsResult(success=False)

        except Exception as e:
            return ErrorRecoveryOptionsResult(success=False)

    async def execute_error_recovery(self, action: str) -> ErrorRecoveryExecutionResult:
        """エラーリカバリを実行する"""
        try:
            await self._ensure_initialized()

            # リカバリボタンをクリック
            button_map = {
                'retry': 'retry-button',
                'upload_new': 'upload-new-button',
                'cancel': 'cancel-button'
            }

            button_ref = button_map.get(action, 'retry-button')
            click_result = await self.executor._mcp_wrapper.click_element(
                element=button_ref,
                ref=button_ref
            )

            if not click_result.get('success'):
                return ErrorRecoveryExecutionResult(success=False)

            # リカバリの完了を待つ
            recovery_result = await self.executor._mcp_wrapper.wait_for_recovery()

            if recovery_result.get('success') and recovery_result.get('recovery_status') == 'success':
                return ErrorRecoveryExecutionResult(
                    success=True,
                    recovery_attempted=True,
                    recovery_successful=True,
                    error_cleared=recovery_result.get('error_cleared', False),
                    processing_resumed=recovery_result.get('processing_resumed', False)
                )

            return ErrorRecoveryExecutionResult(
                success=False,
                recovery_attempted=True,
                recovery_successful=False
            )

        except Exception as e:
            return ErrorRecoveryExecutionResult(success=False)

    async def download_with_error_handling(self) -> DownloadWithErrorHandlingResult:
        """エラーハンドリング付きでダウンロードを実行する"""
        try:
            await self._ensure_initialized()

            # ダウンロードを試行
            try:
                click_result = await self.executor._mcp_wrapper.click_element(
                    element="csv-download-link",
                    ref="csv-download-link"
                )
            except Exception as download_error:
                # エラーが発生した場合、エラー表示を確認
                error_result = await self.executor._mcp_wrapper.get_error_elements()

                if error_result.get('success') and error_result.get('error_present'):
                    return DownloadWithErrorHandlingResult(
                        success=False,
                        download_failed=True,
                        error_displayed=True,
                        error_id=error_result.get('error_id', '')
                    )

                raise

            return DownloadWithErrorHandlingResult(success=True)

        except Exception as e:
            return DownloadWithErrorHandlingResult(
                success=False,
                download_failed=True
            )

    async def verify_download_format_options(self) -> DownloadFormatOptionsResult:
        """ダウンロード形式オプションを検証する"""
        try:
            await self._ensure_initialized()

            options_result = await self.executor._mcp_wrapper.get_download_options()

            if options_result.get('success'):
                formats = options_result.get('formats', [])

                csv_available = any(fmt.get('format') == 'csv' and fmt.get('enabled', False) for fmt in formats)
                json_available = any(fmt.get('format') == 'json' and fmt.get('enabled', False) for fmt in formats)
                excel_available = any(fmt.get('format') == 'excel' and fmt.get('enabled', False) for fmt in formats)

                return DownloadFormatOptionsResult(
                    success=True,
                    available_formats=formats,
                    csv_available=csv_available,
                    json_available=json_available,
                    excel_available=excel_available
                )

            return DownloadFormatOptionsResult(success=False)

        except Exception as e:
            return DownloadFormatOptionsResult(success=False)