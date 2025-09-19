"""ファイルアップロード管理システム

ファイル選択処理の自動化、アップロード進捗監視、処理完了待機、成功確認ロジックの実装
Requirements: 3.1, 3.3, 3.4 - ファイルアップロード機能、進捗監視、成功確認
"""

import asyncio
import logging
import os
import time
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from src.mcp_wrapper import MCPTestExecutor, MCPWrapperError


class UploadStatus(Enum):
    """アップロード状態を表す列挙型"""
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(Enum):
    """ファイルタイプを表す列挙型"""
    JSONL = "jsonl"
    JSON = "json"


class ErrorType(Enum):
    """エラータイプを表す列挙型"""
    INVALID_FORMAT = "invalid_format"
    SIZE_LIMIT = "size_limit"
    TIMEOUT = "timeout"
    FILE_NOT_FOUND = "file_not_found"
    UPLOAD_FAILED = "upload_failed"


class ComparisonMode(Enum):
    """比較モードを表す列挙型"""
    SINGLE_FILE = "single_file"
    DUAL_FILE = "dual_file"


@dataclass
class UploadProgress:
    """アップロード進捗情報"""
    progress: int
    status: UploadStatus
    bytes_uploaded: int
    total_bytes: Optional[int] = None
    estimated_time_remaining: Optional[float] = None


@dataclass
class UploadResult:
    """アップロード結果"""
    success: bool
    upload_id: str
    filename: str
    status: UploadStatus
    file_size: Optional[int] = None
    upload_time: Optional[float] = None


@dataclass
class CompletionResult:
    """アップロード完了結果"""
    status: UploadStatus
    upload_id: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    completion_time: Optional[float] = None


@dataclass
class SuccessIndicator:
    """成功指標"""
    type: str
    contains: Optional[str] = None
    id: Optional[str] = None
    class_name: Optional[str] = None


@dataclass
class VerificationResult:
    """成功確認結果"""
    success: bool
    upload_id: str
    found_indicators: List[SuccessIndicator]
    missing_indicators: List[SuccessIndicator]
    total_expected: int
    total_found: int


@dataclass
class ErrorIndicator:
    """エラー指標"""
    type: str
    class_name: Optional[str] = None
    id: Optional[str] = None
    contains: Optional[str] = None


@dataclass
class ErrorVerificationResult:
    """エラー確認結果"""
    success: bool
    found_error_indicators: List[ErrorIndicator]
    missing_error_indicators: List[ErrorIndicator]
    error_messages: List[str]
    error_details: List[str]


@dataclass
class DualFileUploadResult:
    """2ファイルアップロード結果"""
    success: bool
    upload_id: str
    comparison_mode: ComparisonMode
    file1: Dict[str, Any]
    file2: Dict[str, Any]
    status: UploadStatus
    total_size: Optional[int] = None
    upload_time: Optional[float] = None


@dataclass
class RecoveryResult:
    """エラーリカバリ結果"""
    success: bool
    recovery_action: str
    result: Dict[str, Any]
    recovery_time: Optional[float] = None


class FileUploadError(Exception):
    """ファイルアップロード専用エラークラス

    Attributes:
        original_error: 元の例外オブジェクト（存在する場合）
    """

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class UploadTimeoutError(Exception):
    """アップロードタイムアウト専用エラークラス"""

    def __init__(self, message: str, timeout: float) -> None:
        super().__init__(message)
        self.timeout = timeout


class FileValidationError(Exception):
    """ファイルバリデーション専用エラークラス"""

    def __init__(self, message: str, file_path: Optional[str] = None) -> None:
        super().__init__(message)
        self.file_path = file_path


class FileUploadManager:
    """ファイルアップロード管理クラス

    ファイル選択処理、アップロード進捗監視、処理完了待機、成功確認を提供します。

    Attributes:
        DEFAULT_TIMEOUT: デフォルトタイムアウト時間（秒）
        PROGRESS_POLL_INTERVAL: 進捗監視ポーリング間隔（秒）
        MAX_FILE_SIZE: 最大ファイルサイズ（バイト）
        ALLOWED_FILE_TYPES: 許可されるファイルタイプ
        _executor: MCPテスト実行コントローラー
        _logger: ロガーインスタンス
        _default_timeout: デフォルトタイムアウト時間
        _progress_interval: 進捗監視間隔
        _max_file_size: 最大ファイルサイズ制限
    """

    # クラス定数
    DEFAULT_TIMEOUT: float = 60.0
    PROGRESS_POLL_INTERVAL: float = 0.5
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_FILE_TYPES: Dict[str, FileType] = {
        '.jsonl': FileType.JSONL,
        '.json': FileType.JSON
    }

    def __init__(
        self,
        default_timeout: Optional[float] = None,
        progress_interval: Optional[float] = None,
        max_file_size: Optional[int] = None
    ) -> None:
        """初期化

        Args:
            default_timeout: デフォルトタイムアウト時間（デフォルト: 60秒）
            progress_interval: 進捗監視間隔（デフォルト: 0.5秒）
            max_file_size: 最大ファイルサイズ（デフォルト: 100MB）
        """
        self._executor: Optional[MCPTestExecutor] = None
        self._logger: logging.Logger = logging.getLogger(__name__)
        self._default_timeout: float = default_timeout or self.DEFAULT_TIMEOUT
        self._progress_interval: float = progress_interval or self.PROGRESS_POLL_INTERVAL
        self._max_file_size: int = max_file_size or self.MAX_FILE_SIZE

    async def _ensure_executor(self) -> MCPTestExecutor:
        """MCPテスト実行コントローラーを確保する（内部メソッド）

        Returns:
            MCPTestExecutor インスタンス

        Raises:
            FileUploadError: 初期化に失敗した場合
        """
        if self._executor is None:
            try:
                self._executor = MCPTestExecutor()
                await self._executor.initialize()
                self._logger.info("MCPTestExecutor initialized for file upload management")
            except Exception as e:
                raise FileUploadError(f"Failed to initialize MCPTestExecutor: {str(e)}", e)

        return self._executor

    def _validate_file(self, file_path: str) -> FileType:
        """ファイルのバリデーションを行う（内部メソッド）

        Args:
            file_path: バリデーション対象のファイルパス

        Returns:
            検証されたファイルタイプ

        Raises:
            FileValidationError: ファイルが無効な場合
        """
        # ファイル存在チェック
        if not os.path.exists(file_path):
            raise FileValidationError(f"File not found: {file_path}", file_path)

        # 拡張子チェック
        _, ext = os.path.splitext(file_path.lower())
        if ext not in self.ALLOWED_FILE_TYPES:
            allowed = ', '.join(self.ALLOWED_FILE_TYPES.keys())
            raise FileValidationError(f"Invalid file format: {ext}. Allowed: {allowed}", file_path)

        # ファイルサイズチェック
        file_size = os.path.getsize(file_path)
        if file_size > self._max_file_size:
            max_mb = self._max_file_size / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            raise FileValidationError(
                f"File too large: {actual_mb:.1f}MB exceeds limit of {max_mb:.1f}MB",
                file_path
            )

        return self.ALLOWED_FILE_TYPES[ext]

    async def select_and_upload_file(self, file_path: str) -> Dict[str, Any]:
        """ファイル選択とアップロードを実行する

        Args:
            file_path: アップロード対象のファイルパス

        Returns:
            アップロード結果辞書

        Raises:
            FileUploadError: アップロードに失敗した場合
            FileValidationError: ファイルが無効な場合
        """
        # ファイルバリデーション
        file_type = self._validate_file(file_path)

        executor = await self._ensure_executor()

        try:
            self._logger.info(f"Starting file upload: {file_path} (type: {file_type.value})")

            # MCPラッパーを使用してファイルアップロード実行
            result = await executor._mcp_wrapper.upload_file(file_path)

            # ファイル情報を追加
            result['file_type'] = file_type.value
            result['file_size'] = os.path.getsize(file_path)

            self._logger.info(f"File upload initiated: {result}")
            return result

        except Exception as e:
            raise FileUploadError(f"Failed to upload file {file_path}: {str(e)}", e)

    async def monitor_upload_progress(self, upload_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """アップロード進捗を監視する

        Args:
            upload_id: アップロードID

        Yields:
            進捗情報辞書

        Raises:
            FileUploadError: 進捗監視に失敗した場合
        """
        executor = await self._ensure_executor()

        try:
            self._logger.info(f"Starting upload progress monitoring: {upload_id}")

            progress_count = 0
            while True:
                try:
                    progress = await executor._mcp_wrapper.get_upload_progress(upload_id)

                    self._logger.debug(f"Upload progress: {progress}")
                    yield progress

                    # 完了チェック
                    if progress.get('progress', 0) >= 100 or progress.get('status') == 'uploaded':
                        break

                    # 進捗監視間隔で待機
                    await asyncio.sleep(self._progress_interval)
                    progress_count += 1

                except StopIteration:
                    break
                except Exception as e:
                    self._logger.warning(f"Progress monitoring error: {str(e)}")
                    break

        except Exception as e:
            raise FileUploadError(f"Error during upload progress monitoring for {upload_id}: {str(e)}", e)

    async def wait_for_upload_completion(self, upload_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """アップロード完了を待機する

        Args:
            upload_id: アップロードID
            timeout: タイムアウト時間（デフォルトは self._default_timeout）

        Returns:
            完了結果辞書

        Raises:
            UploadTimeoutError: タイムアウトした場合
            FileUploadError: その他のエラー
        """
        executor = await self._ensure_executor()
        timeout_val = timeout or self._default_timeout

        start_time = time.time()
        self._logger.info(f"Waiting for upload completion: {upload_id} (timeout: {timeout_val}s)")

        try:
            while time.time() - start_time < timeout_val:
                status_result = await executor._mcp_wrapper.get_upload_status(upload_id)

                if status_result.get('status') == 'completed':
                    self._logger.info(f"Upload completed: {upload_id}")
                    return status_result

                # ポーリング間隔で待機
                await asyncio.sleep(self.PROGRESS_POLL_INTERVAL)

            # タイムアウト
            raise UploadTimeoutError(f"Upload completion timeout after {timeout_val} seconds", timeout_val)

        except UploadTimeoutError:
            raise
        except Exception as e:
            raise FileUploadError(f"Error while waiting for upload completion: {str(e)}", e)

    async def verify_upload_success(self, upload_id: str, expected_indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """アップロード成功を確認する

        Args:
            upload_id: アップロードID
            expected_indicators: 期待される成功指標のリスト

        Returns:
            成功確認結果辞書

        Raises:
            FileUploadError: 確認処理に失敗した場合
        """
        executor = await self._ensure_executor()

        try:
            self._logger.info(f"Verifying upload success: {upload_id}")

            snapshot_result = await executor._mcp_wrapper.take_snapshot()

            if not snapshot_result.get('success'):
                raise FileUploadError("Failed to take snapshot for upload verification")

            snapshot = snapshot_result.get('snapshot', {})
            elements = snapshot.get('elements', [])

            # 成功指標の検証
            verification_result = self._verify_success_indicators(expected_indicators, elements)
            verification_result['upload_id'] = upload_id

            self._logger.info(f"Upload verification completed: {verification_result}")
            return verification_result

        except Exception as e:
            raise FileUploadError(f"Error during upload success verification for {upload_id}: {str(e)}", e)

    def _verify_success_indicators(self, expected_indicators: List[Dict[str, Any]], elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """成功指標を検証する（内部メソッド）

        Args:
            expected_indicators: 期待される指標のリスト
            elements: ページ要素のリスト

        Returns:
            検証結果辞書
        """
        found_indicators = []
        missing_indicators = []

        for indicator in expected_indicators:
            if self._find_indicator_in_elements(indicator, elements):
                found_indicators.append(indicator)
            else:
                missing_indicators.append(indicator)

        success = len(missing_indicators) == 0

        return {
            'success': success,
            'found_indicators': found_indicators,
            'missing_indicators': missing_indicators,
            'total_expected': len(expected_indicators),
            'total_found': len(found_indicators)
        }

    def _find_indicator_in_elements(self, indicator: Dict[str, Any], elements: List[Dict[str, Any]]) -> bool:
        """要素内で指標を検索する（内部メソッド）

        Args:
            indicator: 検索する指標
            elements: 検索対象の要素リスト

        Returns:
            指標が見つかった場合True
        """
        for element in elements:
            if self._element_matches_indicator(element, indicator):
                return True
        return False

    def _element_matches_indicator(self, element: Dict[str, Any], indicator: Dict[str, Any]) -> bool:
        """要素が指標と一致するかチェックする（内部メソッド）

        Args:
            element: チェック対象の要素
            indicator: 一致確認する指標

        Returns:
            一致する場合True
        """
        # タイプマッチング
        if 'type' in indicator and element.get('type') != indicator['type']:
            return False

        # IDマッチング
        if 'id' in indicator and element.get('id') != indicator['id']:
            return False

        # クラスマッチング
        if 'class' in indicator and element.get('class') != indicator['class']:
            return False

        # テキスト内容マッチング
        if 'contains' in indicator:
            element_text = element.get('text', '').lower()
            if indicator['contains'].lower() not in element_text:
                return False

        return True

    def get_supported_file_types(self) -> List[str]:
        """サポートされているファイルタイプを取得する

        Returns:
            サポートされているファイル拡張子のリスト
        """
        return list(self.ALLOWED_FILE_TYPES.keys())

    def get_max_file_size_mb(self) -> float:
        """最大ファイルサイズをMB単位で取得する

        Returns:
            最大ファイルサイズ（MB）
        """
        return self._max_file_size / (1024 * 1024)

    def is_supported_file_type(self, file_path: str) -> bool:
        """ファイルタイプがサポートされているかチェックする

        Args:
            file_path: チェック対象のファイルパス

        Returns:
            サポートされている場合True
        """
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.ALLOWED_FILE_TYPES

    def get_file_type(self, file_path: str) -> Optional[FileType]:
        """ファイルパスからファイルタイプを取得する

        Args:
            file_path: ファイルパス

        Returns:
            ファイルタイプ（サポートされていない場合はNone）
        """
        _, ext = os.path.splitext(file_path.lower())
        return self.ALLOWED_FILE_TYPES.get(ext)

    def format_file_size(self, size_bytes: int) -> str:
        """ファイルサイズを人間が読みやすい形式でフォーマットする

        Args:
            size_bytes: ファイルサイズ（バイト）

        Returns:
            フォーマットされたファイルサイズ文字列
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _validate_dual_files(self, file1_path: str, file2_path: str) -> tuple[FileType, FileType]:
        """2つのファイルをバリデーションする（内部メソッド）

        Args:
            file1_path: 1つ目のファイルパス
            file2_path: 2つ目のファイルパス

        Returns:
            両ファイルのファイルタイプのタプル

        Raises:
            FileValidationError: ファイルが無効な場合
        """
        try:
            file1_type = self._validate_file(file1_path)
        except FileValidationError as e:
            raise FileValidationError(f"First file not found: {file1_path}", file1_path) from e

        try:
            file2_type = self._validate_file(file2_path)
        except FileValidationError as e:
            raise FileValidationError(f"Second file not found: {file2_path}", file2_path) from e

        return file1_type, file2_type

    def _create_error_message(self, error_type: ErrorType, context: str, details: Optional[str] = None) -> str:
        """エラーメッセージを生成する（内部メソッド）

        Args:
            error_type: エラータイプ
            context: エラーコンテキスト
            details: 追加詳細情報

        Returns:
            フォーマットされたエラーメッセージ
        """
        base_messages = {
            ErrorType.INVALID_FORMAT: f"Invalid file format: {context}",
            ErrorType.SIZE_LIMIT: f"File size exceeds limit: {context}",
            ErrorType.TIMEOUT: f"Upload timeout: {context}",
            ErrorType.FILE_NOT_FOUND: f"File not found: {context}",
            ErrorType.UPLOAD_FAILED: f"Upload failed: {context}"
        }

        message = base_messages.get(error_type, f"Unknown error: {context}")
        if details:
            message += f" - {details}"

        return message

    def _calculate_total_file_size(self, file_paths: List[str]) -> int:
        """複数ファイルの合計サイズを計算する（内部メソッド）

        Args:
            file_paths: ファイルパスのリスト

        Returns:
            合計ファイルサイズ（バイト）
        """
        return sum(os.path.getsize(path) for path in file_paths if os.path.exists(path))

    async def get_upload_summary(self, upload_id: str) -> Dict[str, Any]:
        """アップロードの詳細サマリーを取得する

        Args:
            upload_id: アップロードID

        Returns:
            アップロードサマリー辞書

        Raises:
            FileUploadError: サマリー取得に失敗した場合
        """
        try:
            executor = await self._ensure_executor()

            # 状態と進捗を取得
            status_result = await executor._mcp_wrapper.get_upload_status(upload_id)
            progress_result = await executor._mcp_wrapper.get_upload_progress(upload_id)

            return {
                'upload_id': upload_id,
                'status': status_result.get('status'),
                'progress': progress_result.get('progress', 0),
                'bytes_uploaded': progress_result.get('bytes_uploaded', 0),
                'formatted_size': self.format_file_size(progress_result.get('bytes_uploaded', 0)),
                'result': status_result.get('result'),
                'last_updated': time.time()
            }

        except Exception as e:
            raise FileUploadError(f"Failed to get upload summary for {upload_id}: {str(e)}", e)

    async def cleanup(self) -> None:
        """リソースをクリーンアップする"""
        if self._executor:
            await self._executor.cleanup()
            self._executor = None
            self._logger.info("FileUploadManager cleanup completed")

    # Task 3.2: 複数ファイルおよびエラー処理メソッド

    async def upload_two_files_for_comparison(self, file1_path: str, file2_path: str) -> Dict[str, Any]:
        """2ファイル比較モードのアップロードを実行する

        Args:
            file1_path: 1つ目のファイルパス
            file2_path: 2つ目のファイルパス

        Returns:
            アップロード結果辞書

        Raises:
            FileUploadError: アップロードに失敗した場合
            FileValidationError: ファイルが無効な場合
        """
        # 両方のファイルをバリデーション
        file1_type, file2_type = self._validate_dual_files(file1_path, file2_path)

        executor = await self._ensure_executor()

        try:
            self._logger.info(f"Starting two-file upload: {file1_path}, {file2_path}")

            # MCPラッパーを使用して2ファイルアップロード実行
            result = await executor._mcp_wrapper.upload_two_files(file1_path, file2_path)

            # ファイル情報を追加
            file1_size = os.path.getsize(file1_path)
            file2_size = os.path.getsize(file2_path)

            result['file1']['file_type'] = file1_type.value
            result['file1']['size'] = file1_size
            result['file2']['file_type'] = file2_type.value
            result['file2']['size'] = file2_size
            result['total_size'] = file1_size + file2_size
            result['total_size_formatted'] = self.format_file_size(file1_size + file2_size)

            self._logger.info(f"Two-file upload initiated: {result}")
            return result

        except Exception as e:
            error_msg = self._create_error_message(
                ErrorType.UPLOAD_FAILED,
                f"{file1_path}, {file2_path}",
                str(e)
            )
            raise FileUploadError(error_msg, e)

    async def validate_file_format(self, file_path: str) -> FileType:
        """ファイル形式のバリデーションを行う

        Args:
            file_path: バリデーション対象のファイルパス

        Returns:
            検証されたファイルタイプ

        Raises:
            FileValidationError: ファイル形式が無効な場合
        """
        # 拡張子チェック
        _, ext = os.path.splitext(file_path.lower())
        if ext not in self.ALLOWED_FILE_TYPES:
            allowed = ', '.join(self.ALLOWED_FILE_TYPES.keys())
            raise FileValidationError(
                f"Invalid file format: {ext}. Allowed: {allowed}",
                file_path
            )

        return self.ALLOWED_FILE_TYPES[ext]

    async def validate_file_size(self, file_path: str, max_size: int) -> None:
        """ファイルサイズのバリデーションを行う

        Args:
            file_path: バリデーション対象のファイルパス
            max_size: 最大許可サイズ（バイト）

        Raises:
            FileValidationError: ファイルサイズが制限を超える場合
        """
        file_size = os.path.getsize(file_path)
        if file_size > max_size:
            raise FileValidationError(
                f"File size exceeds limit: {file_size} bytes > {max_size} bytes",
                file_path
            )

    async def verify_error_message_display(self, expected_error_indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """エラーメッセージ表示を確認する

        Args:
            expected_error_indicators: 期待されるエラー指標のリスト

        Returns:
            エラーメッセージ確認結果辞書

        Raises:
            FileUploadError: 確認処理に失敗した場合
        """
        executor = await self._ensure_executor()

        try:
            self._logger.info("Verifying error message display")

            snapshot_result = await executor._mcp_wrapper.take_snapshot()

            if not snapshot_result.get('success'):
                raise FileUploadError("Failed to take snapshot for error verification")

            snapshot = snapshot_result.get('snapshot', {})
            elements = snapshot.get('elements', [])

            # エラー指標の検証
            verification_result = self._verify_error_indicators(expected_error_indicators, elements)

            self._logger.info(f"Error verification completed: {verification_result}")
            return verification_result

        except Exception as e:
            raise FileUploadError(f"Error during error message verification: {str(e)}", e)

    def _verify_error_indicators(self, expected_indicators: List[Dict[str, Any]], elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """エラー指標を検証する（内部メソッド）

        Args:
            expected_indicators: 期待される指標のリスト
            elements: ページ要素のリスト

        Returns:
            検証結果辞書
        """
        found_error_indicators = []
        missing_error_indicators = []
        error_messages = []
        error_details = []

        for indicator in expected_indicators:
            matching_element = self._find_error_indicator_in_elements(indicator, elements)
            if matching_element:
                found_error_indicators.append(indicator)
                if 'text' in matching_element:
                    if indicator.get('class') == 'error-message':
                        error_messages.append(matching_element['text'])
                    elif indicator.get('id') == 'error-details':
                        error_details.append(matching_element['text'])
            else:
                missing_error_indicators.append(indicator)

        success = len(missing_error_indicators) == 0

        return {
            'success': success,
            'found_error_indicators': found_error_indicators,
            'missing_error_indicators': missing_error_indicators,
            'error_messages': error_messages,
            'error_details': error_details
        }

    def _find_error_indicator_in_elements(self, indicator: Dict[str, Any], elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """要素内でエラー指標を検索する（内部メソッド）

        Args:
            indicator: 検索する指標
            elements: 検索対象の要素リスト

        Returns:
            見つかった要素（なければNone）
        """
        for element in elements:
            if self._element_matches_indicator(element, indicator):
                return element
        return None

    async def handle_upload_error(self, error_type: str, context: str) -> None:
        """アップロードエラーを処理する

        Args:
            error_type: エラーの種類
            context: エラーコンテキスト

        Raises:
            FileValidationError: ファイル関連エラー
            UploadTimeoutError: タイムアウトエラー
            FileUploadError: その他のエラー
        """
        # 文字列をErrorType列挙型に変換
        try:
            error_enum = ErrorType(error_type)
        except ValueError:
            error_enum = ErrorType.UPLOAD_FAILED

        # エラーメッセージを生成
        error_message = self._create_error_message(error_enum, context)

        # エラータイプに応じて適切な例外を発生
        if error_enum in [ErrorType.INVALID_FORMAT, ErrorType.SIZE_LIMIT, ErrorType.FILE_NOT_FOUND]:
            raise FileValidationError(error_message, context)
        elif error_enum == ErrorType.TIMEOUT:
            raise UploadTimeoutError(error_message, 60.0)
        else:
            raise FileUploadError(error_message)

    async def perform_error_recovery(self, retry_button: Dict[str, Any]) -> Dict[str, Any]:
        """エラーリカバリ操作を実行する

        Args:
            retry_button: リトライボタンの指標

        Returns:
            リカバリ結果辞書

        Raises:
            FileUploadError: リカバリに失敗した場合
        """
        executor = await self._ensure_executor()

        try:
            self._logger.info("Performing error recovery")

            # リトライボタンをクリック
            result = await executor._mcp_wrapper.click_element(
                element=retry_button.get('type', 'button'),
                ref=retry_button.get('class', 'retry-button')
            )

            self._logger.info("Error recovery completed")
            return result

        except Exception as e:
            raise FileUploadError(f"Error recovery failed: {str(e)}", e)

    async def verify_recovery_success(self, success_indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """リカバリ後の成功を確認する

        Args:
            success_indicators: 期待される成功指標のリスト

        Returns:
            成功確認結果辞書

        Raises:
            FileUploadError: 確認処理に失敗した場合
        """
        executor = await self._ensure_executor()

        try:
            self._logger.info("Verifying recovery success")

            snapshot_result = await executor._mcp_wrapper.take_snapshot()

            if not snapshot_result.get('success'):
                raise FileUploadError("Failed to take snapshot for recovery verification")

            snapshot = snapshot_result.get('snapshot', {})
            elements = snapshot.get('elements', [])

            # 成功指標の検証
            verification_result = self._verify_success_indicators(success_indicators, elements)

            self._logger.info(f"Recovery verification completed: {verification_result}")
            return verification_result

        except Exception as e:
            raise FileUploadError(f"Error during recovery verification: {str(e)}", e)