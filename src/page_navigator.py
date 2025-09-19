"""ページナビゲーション基本機能

WebUI初期アクセス、ページ読み込み完了確認、エラーページ検出、ページ構造検証の実装
Requirements: 2.1, 2.2, 2.3, 2.4 - ナビゲーション基本機能、ページ検証、エラー検出
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from src.mcp_wrapper import MCPTestExecutor, MCPWrapperError


class NavigationError(Exception):
    """ナビゲーション専用エラークラス

    Attributes:
        original_error: 元の例外オブジェクト（存在する場合）
    """

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class PageLoadTimeoutError(Exception):
    """ページ読み込みタイムアウト専用エラークラス"""

    def __init__(self, message: str, timeout: float) -> None:
        super().__init__(message)
        self.timeout = timeout


@dataclass
class ErrorPattern:
    """エラーパターン定義"""
    error_type: str
    title_keywords: List[str]
    element_keywords: List[str]
    default_message: str


@dataclass
class PageValidationResult:
    """ページ検証結果"""
    valid: bool
    found_elements: int
    missing_elements: List[Dict[str, Any]]
    total_expected: int
    total_actual: int


@dataclass
class ErrorDetectionResult:
    """エラー検出結果"""
    has_error: bool
    error_type: Optional[str]
    error_message: Optional[str]


class PageNavigator:
    """ページナビゲーション基本機能クラス

    WebUIへのナビゲーション、ページ読み込み確認、エラー検出、構造検証を提供します。

    Attributes:
        DEFAULT_BASE_URL: デフォルトのベースURL
        DEFAULT_TIMEOUT: デフォルトタイムアウト時間（秒）
        POLL_INTERVAL: ページ読み込みポーリング間隔（秒）
        base_url: ベースURL
        default_timeout: デフォルトタイムアウト時間
        _executor: MCPテスト実行コントローラー
        _logger: ロガーインスタンス
    """

    # クラス定数
    DEFAULT_BASE_URL: str = "http://localhost:18081"
    DEFAULT_TIMEOUT: float = 30.0
    POLL_INTERVAL: float = 0.5

    # エラーパターン定義
    ERROR_PATTERNS: List[ErrorPattern] = [
        ErrorPattern(
            error_type="404",
            title_keywords=["404", "not found"],
            element_keywords=["404", "not found"],
            default_message="Page not found"
        ),
        ErrorPattern(
            error_type="500",
            title_keywords=["500", "internal server error", "server error"],
            element_keywords=["500", "server error", "internal"],
            default_message="Internal server error"
        )
    ]

    def __init__(self, base_url: Optional[str] = None, default_timeout: Optional[float] = None) -> None:
        """初期化

        Args:
            base_url: ベースURL（デフォルト: http://localhost:18081）
            default_timeout: デフォルトタイムアウト時間（デフォルト: 30秒）
        """
        self.base_url: str = base_url or self.DEFAULT_BASE_URL
        self.default_timeout: float = default_timeout or self.DEFAULT_TIMEOUT
        self._executor: Optional[MCPTestExecutor] = None
        self._logger: logging.Logger = logging.getLogger(__name__)

    async def _ensure_executor(self) -> MCPTestExecutor:
        """MCPテスト実行コントローラーを確保する（内部メソッド）

        Returns:
            MCPTestExecutor インスタンス

        Raises:
            NavigationError: 初期化に失敗した場合
        """
        if self._executor is None:
            try:
                self._executor = MCPTestExecutor()
                await self._executor.initialize()
                self._logger.info("MCPTestExecutor initialized for navigation")
            except Exception as e:
                raise NavigationError(f"Failed to initialize MCPTestExecutor: {str(e)}", e)

        return self._executor

    async def navigate_to_webui(self, url: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """WebUIへのナビゲーションを実行する

        Args:
            url: ナビゲーション先URL
            timeout: タイムアウト時間（デフォルトは self.default_timeout）

        Returns:
            ナビゲーション結果辞書

        Raises:
            NavigationError: ナビゲーションに失敗した場合
        """
        executor = await self._ensure_executor()
        timeout_val = timeout or self.default_timeout

        try:
            self._logger.info(f"Navigating to WebUI: {url}")

            # MCPラッパーを使用してナビゲーション実行
            result = await executor._mcp_wrapper.navigate(url)

            self._logger.info(f"Navigation completed: {result}")
            return result

        except Exception as e:
            raise NavigationError(f"Failed to navigate to WebUI {url}: {str(e)}", e)

    async def wait_for_page_load(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """ページ読み込み完了を待機する

        Args:
            timeout: タイムアウト時間（デフォルトは self.default_timeout）

        Returns:
            ページ読み込み結果辞書

        Raises:
            PageLoadTimeoutError: タイムアウトした場合
            NavigationError: その他のエラー
        """
        executor = await self._ensure_executor()
        timeout_val = timeout or self.default_timeout

        start_time = time.time()
        self._logger.info(f"Waiting for page load completion (timeout: {timeout_val}s)")

        try:
            while time.time() - start_time < timeout_val:
                snapshot_result = await executor._mcp_wrapper.take_snapshot()

                if snapshot_result.get('success'):
                    snapshot = snapshot_result.get('snapshot', {})
                    ready_state = snapshot.get('ready_state', '')
                    title = snapshot.get('title', '')

                    # ページが完全に読み込まれた場合
                    if ready_state == 'complete' and title:
                        self._logger.info(f"Page load completed: {title}")
                        return {
                            'loaded': True,
                            'title': title,
                            'ready_state': ready_state,
                            'load_time': time.time() - start_time
                        }

                # ポーリング間隔で待機
                await asyncio.sleep(self.POLL_INTERVAL)

            # タイムアウト
            raise PageLoadTimeoutError(f"Page load timeout after {timeout_val} seconds", timeout_val)

        except PageLoadTimeoutError:
            raise
        except Exception as e:
            raise NavigationError(f"Error while waiting for page load: {str(e)}", e)

    async def detect_error_page(self) -> ErrorDetectionResult:
        """エラーページを検出する

        Returns:
            エラー検出結果

        Raises:
            NavigationError: スナップショット取得に失敗した場合
        """
        executor = await self._ensure_executor()

        try:
            self._logger.info("Detecting error page")

            snapshot_result = await executor._mcp_wrapper.take_snapshot()

            if not snapshot_result.get('success'):
                raise NavigationError("Failed to take snapshot for error detection")

            snapshot = snapshot_result.get('snapshot', {})
            title = snapshot.get('title', '').lower()
            elements = snapshot.get('elements', [])

            # エラーパターンの検出
            error_result_dict = self._analyze_error_patterns(title, elements)

            # ErrorDetectionResultに変換
            error_result = ErrorDetectionResult(
                has_error=error_result_dict['has_error'],
                error_type=error_result_dict['error_type'],
                error_message=error_result_dict['error_message']
            )

            self._logger.info(f"Error detection completed: {error_result}")
            return error_result

        except Exception as e:
            raise NavigationError(f"Error during error page detection: {str(e)}", e)

    def _analyze_error_patterns(self, title: str, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """エラーパターンを分析する（内部メソッド）

        Args:
            title: ページタイトル
            elements: ページ要素のリスト

        Returns:
            エラー分析結果辞書
        """
        # 要素内容からエラーを検出（優先的にチェック）
        best_404_message = None
        best_500_message = None

        for element in elements:
            text = element.get('text', '').lower()
            element_text = element.get('text', '')

            # 404エラーの検出（より詳細なメッセージを優先）
            if '404' in text or 'not found' in text:
                if best_404_message is None or len(element_text) > len(best_404_message):
                    best_404_message = element_text

            # 500エラーの検出（より詳細なメッセージを優先）
            elif '500' in text or 'server error' in text:
                if best_500_message is None or len(element_text) > len(best_500_message):
                    best_500_message = element_text

        # 最も詳細な404エラーメッセージが見つかった場合
        if best_404_message:
            return {
                'has_error': True,
                'error_type': '404',
                'error_message': best_404_message
            }

        # 最も詳細な500エラーメッセージが見つかった場合
        if best_500_message:
            return {
                'has_error': True,
                'error_type': '500',
                'error_message': best_500_message
            }

        # タイトルからエラーを検出
        if '404' in title or 'not found' in title:
            # より詳細なメッセージを要素から検索
            detailed_message = self._extract_error_message(elements, 'not found', 'page', 'error')
            return {
                'has_error': True,
                'error_type': '404',
                'error_message': detailed_message or 'Page not found'
            }

        if '500' in title or 'internal server error' in title or 'server error' in title:
            # より詳細なメッセージを要素から検索
            detailed_message = self._extract_error_message(elements, 'server error', 'internal', 'error')
            return {
                'has_error': True,
                'error_type': '500',
                'error_message': detailed_message or 'Internal server error'
            }

        # エラーなし
        return {
            'has_error': False,
            'error_type': None,
            'error_message': None
        }

    def _extract_error_message(self, elements: List[Dict[str, Any]], *keywords: str) -> Optional[str]:
        """エラーメッセージを抽出する（内部メソッド）

        Args:
            elements: ページ要素のリスト
            *keywords: 検索キーワード

        Returns:
            エラーメッセージ（見つからない場合はNone）
        """
        for element in elements:
            text = element.get('text', '').lower()
            for keyword in keywords:
                if keyword in text:
                    return element.get('text', f'Error containing: {keyword}')

        # 見つからない場合はNone
        return None

    async def validate_page_structure(self, expected_elements: List[Dict[str, Any]]) -> PageValidationResult:
        """ページ構造を検証する

        Args:
            expected_elements: 期待される要素のリスト

        Returns:
            構造検証結果

        Raises:
            NavigationError: スナップショット取得に失敗した場合
        """
        executor = await self._ensure_executor()

        try:
            self._logger.info(f"Validating page structure with {len(expected_elements)} expected elements")

            snapshot_result = await executor._mcp_wrapper.take_snapshot()

            if not snapshot_result.get('success'):
                raise NavigationError("Failed to take snapshot for structure validation")

            snapshot = snapshot_result.get('snapshot', {})
            actual_elements = snapshot.get('elements', [])

            # 構造検証の実行
            validation_result_dict = self._validate_element_structure(expected_elements, actual_elements)

            # PageValidationResultに変換
            validation_result = PageValidationResult(
                valid=validation_result_dict['valid'],
                found_elements=validation_result_dict['found_elements'],
                missing_elements=validation_result_dict['missing_elements'],
                total_expected=validation_result_dict['total_expected'],
                total_actual=validation_result_dict['total_actual']
            )

            self._logger.info(f"Structure validation completed: {validation_result}")
            return validation_result

        except Exception as e:
            raise NavigationError(f"Error during page structure validation: {str(e)}", e)

    def _validate_element_structure(self, expected: List[Dict[str, Any]], actual: List[Dict[str, Any]]) -> Dict[str, Any]:
        """要素構造を検証する（内部メソッド）

        Args:
            expected: 期待される要素のリスト
            actual: 実際の要素のリスト

        Returns:
            検証結果辞書
        """
        found_elements = 0
        missing_elements = []

        for expected_element in expected:
            if self._find_matching_element(expected_element, actual):
                found_elements += 1
            else:
                missing_elements.append(expected_element)

        is_valid = len(missing_elements) == 0

        return {
            'valid': is_valid,
            'found_elements': found_elements,
            'missing_elements': missing_elements,
            'total_expected': len(expected),
            'total_actual': len(actual)
        }

    def _find_matching_element(self, expected: Dict[str, Any], actual_elements: List[Dict[str, Any]]) -> bool:
        """一致する要素を検索する（内部メソッド）

        Args:
            expected: 期待される要素
            actual_elements: 実際の要素のリスト

        Returns:
            一致する要素が見つかった場合True
        """
        for actual_element in actual_elements:
            if self._elements_match(expected, actual_element):
                return True
        return False

    def _elements_match(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> bool:
        """要素が一致するかチェックする（内部メソッド）

        Args:
            expected: 期待される要素
            actual: 実際の要素

        Returns:
            要素が一致する場合True
        """
        for key, value in expected.items():
            if key not in actual:
                return False
            if actual[key] != value:
                return False
        return True

    async def cleanup(self) -> None:
        """リソースをクリーンアップする"""
        if self._executor:
            await self._executor.cleanup()
            self._executor = None
            self._logger.info("PageNavigator cleanup completed")