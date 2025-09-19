"""フォームインタラクション管理システム

フォーム要素の自動操作、テキスト入力、ドロップダウン選択、チェックボックス・ラジオボタン操作、フォーム送信処理の実装
Requirements: 4.1, 4.3, 4.4, 4.5 - フォーム要素操作、インタラクション管理
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from src.mcp_wrapper import MCPTestExecutor, MCPWrapperError


class FormElementType(Enum):
    """フォーム要素タイプを表す列挙型"""
    TEXT_INPUT = "text_input"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SUBMIT_BUTTON = "submit_button"


class InteractionType(Enum):
    """インタラクションタイプを表す列挙型"""
    TYPE = "type"
    SELECT = "select"
    CLICK = "click"
    TOGGLE = "toggle"
    SUBMIT = "submit"


@dataclass
class FormInteractionResult:
    """フォームインタラクション結果"""
    success: bool
    element_type: FormElementType
    interaction_type: InteractionType
    result: Dict[str, Any]
    duration: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class FormElementSelector:
    """フォーム要素セレクター"""
    element: str
    ref: str
    element_type: FormElementType


@dataclass
class TextInputOptions:
    """テキスト入力オプション"""
    slowly: bool = False
    submit: bool = False
    clear_first: bool = False
    validate_input: bool = True


@dataclass
class FormSubmissionOptions:
    """フォーム送信オプション"""
    wait_for_validation: bool = False
    timeout: Optional[float] = None
    expect_redirect: bool = True
    validate_response: bool = True


@dataclass
class FormInteractionMetrics:
    """フォームインタラクション統計"""
    total_interactions: int = 0
    successful_interactions: int = 0
    failed_interactions: int = 0
    average_response_time: float = 0.0
    total_processing_time: float = 0.0


@dataclass
class BatchFormInputResult:
    """複数フィールド一括入力結果"""
    success: bool
    results: List[FormInteractionResult]
    success_count: int = 0
    error_count: int = 0
    errors: List[FormInteractionResult] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class FormValidationError:
    """フォームバリデーションエラー"""
    field: str
    message: str
    code: str = ""
    error_type: str = ""


@dataclass
class FormValidationResult:
    """フォームバリデーション結果"""
    success: bool
    errors: List[FormValidationError]
    has_required_field_errors: bool = False
    has_format_errors: bool = False


@dataclass
class RequiredFieldValidationResult:
    """必須フィールドバリデーション結果"""
    success: bool
    missing_fields: List[str]
    completed_fields: List[str]


@dataclass
class InputPersistenceResult:
    """入力値永続性確認結果"""
    success: bool
    expected_value: str
    actual_value: str
    values_match: bool


@dataclass
class FormStateResult:
    """フォーム状態保持結果"""
    success: bool
    final_state: Dict[str, Any]
    state_preserved_throughout: bool


@dataclass
class ComprehensiveValidationResult:
    """包括的バリデーション結果"""
    success: bool
    total_fields: int
    valid_fields: int
    invalid_fields: int
    overall_form_valid: bool
    validation_errors: List[FormValidationError]


@dataclass
class ValidationEvent:
    """バリデーションイベント"""
    timestamp: str
    field: str
    event_type: str
    message: str


@dataclass
class ValidationEventsResult:
    """バリデーションイベント結果"""
    success: bool
    events: List[ValidationEvent]


class FormInteractionError(Exception):
    """フォームインタラクション専用エラークラス

    Attributes:
        original_error: 元の例外オブジェクト（存在する場合）
    """

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class FormSubmissionTimeoutError(Exception):
    """フォーム送信タイムアウト専用エラークラス"""

    def __init__(self, message: str, timeout: float) -> None:
        super().__init__(message)
        self.timeout = timeout


class BatchFormInputError(Exception):
    """一括フォーム入力専用エラークラス"""

    def __init__(self, message: str, failed_fields: List[str], successful_count: int) -> None:
        super().__init__(message)
        self.failed_fields = failed_fields
        self.successful_count = successful_count


class FormValidationException(Exception):
    """フォームバリデーション専用例外クラス"""

    def __init__(self, message: str, field_errors: List[str]) -> None:
        super().__init__(message)
        self.field_errors = field_errors


class FormInteractionManager:
    """フォームインタラクション管理クラス

    フォーム要素の自動操作、テキスト入力、ドロップダウン選択、チェックボックス・ラジオボタン操作を提供します。

    Attributes:
        DEFAULT_TIMEOUT: デフォルトタイムアウト時間（秒）
        DEFAULT_SUBMIT_TIMEOUT: デフォルトフォーム送信タイムアウト時間（秒）
        _executor: MCPテスト実行コントローラー
        _logger: ロガーインスタンス
        _default_timeout: デフォルトタイムアウト時間
    """

    # クラス定数
    DEFAULT_TIMEOUT: float = 30.0
    DEFAULT_SUBMIT_TIMEOUT: float = 60.0

    def __init__(self, default_timeout: Optional[float] = None) -> None:
        """初期化

        Args:
            default_timeout: デフォルトタイムアウト時間（デフォルト: 30秒）
        """
        self._executor: Optional[MCPTestExecutor] = None
        self._logger: logging.Logger = logging.getLogger(__name__)
        self._default_timeout: float = default_timeout or self.DEFAULT_TIMEOUT
        self._metrics: FormInteractionMetrics = FormInteractionMetrics()

    async def _ensure_executor(self) -> MCPTestExecutor:
        """MCPテスト実行コントローラーを確保する（内部メソッド）

        Returns:
            MCPTestExecutor インスタンス

        Raises:
            FormInteractionError: 初期化に失敗した場合
        """
        if self._executor is None:
            try:
                self._executor = MCPTestExecutor()
                await self._executor.initialize()
                self._logger.info("MCPTestExecutor initialized for form interaction management")
            except Exception as e:
                raise FormInteractionError(f"Failed to initialize MCPTestExecutor: {str(e)}", e)

        return self._executor

    def _update_metrics(self, success: bool, duration: float) -> None:
        """メトリクスを更新する（内部メソッド）

        Args:
            success: 操作が成功したかどうか
            duration: 処理時間（秒）
        """
        self._metrics.total_interactions += 1
        self._metrics.total_processing_time += duration

        if success:
            self._metrics.successful_interactions += 1
        else:
            self._metrics.failed_interactions += 1

        # 平均応答時間を更新
        self._metrics.average_response_time = (
            self._metrics.total_processing_time / self._metrics.total_interactions
        )

    def _validate_form_field_data(self, field_data: Dict[str, Any]) -> bool:
        """フォームフィールドデータの妥当性を検証する（内部メソッド）

        Args:
            field_data: フィールドデータ辞書

        Returns:
            bool: 妥当性チェック結果
        """
        required_keys = ['type', 'selector', 'value']

        # 必須キーの存在確認
        if not all(key in field_data for key in required_keys):
            return False

        # セレクターの妥当性確認
        selector = field_data.get('selector', {})
        if not isinstance(selector, dict) or not all(key in selector for key in ['element', 'ref']):
            return False

        # タイプの妥当性確認
        valid_types = ['text', 'dropdown', 'checkbox', 'radio']
        if field_data.get('type') not in valid_types:
            return False

        return True

    def _create_error_result(self, element_type: FormElementType, interaction_type: InteractionType,
                           error_message: str, duration: float = 0.0) -> FormInteractionResult:
        """エラー結果を作成する（内部メソッド）

        Args:
            element_type: フォーム要素タイプ
            interaction_type: インタラクションタイプ
            error_message: エラーメッセージ
            duration: 処理時間

        Returns:
            FormInteractionResult: エラー結果オブジェクト
        """
        return FormInteractionResult(
            success=False,
            element_type=element_type,
            interaction_type=interaction_type,
            result={},
            duration=duration,
            error_message=error_message
        )

    async def _execute_field_operation(self, field_data: Dict[str, Any]) -> FormInteractionResult:
        """単一フィールドの操作を実行する（内部メソッド）

        Args:
            field_data: フィールドデータ辞書

        Returns:
            FormInteractionResult: 操作結果
        """
        try:
            field_type = field_data['type']
            selector = field_data['selector']
            value = field_data['value']

            if field_type == 'text':
                return await self.type_text_input(selector, value)
            elif field_type == 'dropdown':
                return await self.select_dropdown_option(selector, value)
            elif field_type == 'checkbox':
                return await self.toggle_checkbox(selector, value)
            elif field_type == 'radio':
                return await self.select_radio_button(selector)
            else:
                return self._create_error_result(
                    FormElementType.TEXT_INPUT,
                    InteractionType.TYPE,
                    f"Unknown field type: {field_type}"
                )

        except Exception as e:
            return self._create_error_result(
                FormElementType.TEXT_INPUT,
                InteractionType.TYPE,
                f"Field operation failed: {str(e)}"
            )

    def _process_validation_errors(self, validation_data: List[Dict[str, Any]]) -> List[FormValidationError]:
        """バリデーションエラーデータを処理する（内部メソッド）

        Args:
            validation_data: バリデーションエラーデータのリスト

        Returns:
            List[FormValidationError]: 処理されたバリデーションエラーのリスト
        """
        errors = []
        for error_data in validation_data:
            error = FormValidationError(
                field=error_data.get('field', ''),
                message=error_data.get('message', ''),
                code=error_data.get('code', ''),
                error_type=error_data.get('error_type', '')
            )
            errors.append(error)
        return errors

    async def type_text_input(self, field_selector: Dict[str, str], text: str, options: Optional[Dict[str, Any]] = None) -> FormInteractionResult:
        """テキスト入力フィールドに文字を入力する

        Args:
            field_selector: フィールドセレクター辞書（element, refを含む）
            text: 入力するテキスト
            options: 入力オプション（slowly, submitなど）

        Returns:
            入力結果辞書

        Raises:
            FormInteractionError: 入力に失敗した場合
        """
        executor = await self._ensure_executor()
        options = options or {}

        start_time = time.time()

        try:
            self._logger.info(f"Typing text to field: {field_selector['element']}")

            element = field_selector['element']
            ref = field_selector['ref']
            slowly = options.get('slowly', False)
            submit = options.get('submit', False)

            result = await executor._mcp_wrapper.type_text(element, ref, text, slowly, submit)
            duration = time.time() - start_time

            # メトリクス更新
            self._update_metrics(True, duration)

            self._logger.info(f"Text input completed: {result}")
            return FormInteractionResult(
                success=True,
                element_type=FormElementType.TEXT_INPUT,
                interaction_type=InteractionType.TYPE,
                result=result,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            self._update_metrics(False, duration)
            error_msg = f"Text input failed for {field_selector}: {str(e)}"
            self._logger.error(error_msg)
            return FormInteractionResult(
                success=False,
                element_type=FormElementType.TEXT_INPUT,
                interaction_type=InteractionType.TYPE,
                result={},
                duration=duration,
                error_message=error_msg
            )

    async def select_dropdown_option(self, dropdown_selector: Dict[str, str], option_values: List[str]) -> FormInteractionResult:
        """ドロップダウンでオプションを選択する

        Args:
            dropdown_selector: ドロップダウンセレクター辞書（element, refを含む）
            option_values: 選択する値のリスト

        Returns:
            選択結果辞書

        Raises:
            FormInteractionError: 選択に失敗した場合
        """
        executor = await self._ensure_executor()

        start_time = time.time()

        try:
            self._logger.info(f"Selecting dropdown option: {dropdown_selector['element']}")

            element = dropdown_selector['element']
            ref = dropdown_selector['ref']

            result = await executor._mcp_wrapper.select_option(element, ref, option_values)
            duration = time.time() - start_time

            # メトリクス更新
            self._update_metrics(True, duration)

            self._logger.info(f"Dropdown selection completed: {result}")
            return FormInteractionResult(
                success=True,
                element_type=FormElementType.DROPDOWN,
                interaction_type=InteractionType.SELECT,
                result=result,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            self._update_metrics(False, duration)
            error_msg = f"Dropdown selection failed for {dropdown_selector}: {str(e)}"
            self._logger.error(error_msg)
            return FormInteractionResult(
                success=False,
                element_type=FormElementType.DROPDOWN,
                interaction_type=InteractionType.SELECT,
                result={},
                duration=duration,
                error_message=error_msg
            )

    async def toggle_checkbox(self, checkbox_selector: Dict[str, str], checked: bool) -> FormInteractionResult:
        """チェックボックスの状態を切り替える

        Args:
            checkbox_selector: チェックボックスセレクター辞書（element, refを含む）
            checked: チェック状態（True=チェック、False=チェック外し）

        Returns:
            切り替え結果辞書

        Raises:
            FormInteractionError: 操作に失敗した場合
        """
        executor = await self._ensure_executor()

        start_time = time.time()

        try:
            self._logger.info(f"Toggling checkbox: {checkbox_selector['element']} -> {checked}")

            element = checkbox_selector['element']
            ref = checkbox_selector['ref']

            # チェックボックスをクリック
            click_result = await executor._mcp_wrapper.click_element(element, ref)
            if not click_result.get('success'):
                raise FormInteractionError(f"Failed to click checkbox: {click_result}")

            # 状態を取得
            state_result = await executor._mcp_wrapper.get_element_state(element, ref)
            duration = time.time() - start_time

            result_dict = {
                'success': True,
                'checked': state_result.get('checked', checked),
                'element_type': state_result.get('element_type', 'checkbox'),
                'value': state_result.get('value')
            }

            # メトリクス更新
            self._update_metrics(True, duration)

            self._logger.info(f"Checkbox toggle completed: {result_dict}")
            return FormInteractionResult(
                success=True,
                element_type=FormElementType.CHECKBOX,
                interaction_type=InteractionType.TOGGLE,
                result=result_dict,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            self._update_metrics(False, duration)
            error_msg = f"Checkbox toggle failed for {checkbox_selector}: {str(e)}"
            self._logger.error(error_msg)
            return FormInteractionResult(
                success=False,
                element_type=FormElementType.CHECKBOX,
                interaction_type=InteractionType.TOGGLE,
                result={},
                duration=duration,
                error_message=error_msg
            )

    async def select_radio_button(self, radio_selector: Dict[str, str]) -> FormInteractionResult:
        """ラジオボタンを選択する

        Args:
            radio_selector: ラジオボタンセレクター辞書（element, refを含む）

        Returns:
            選択結果辞書

        Raises:
            FormInteractionError: 選択に失敗した場合
        """
        executor = await self._ensure_executor()

        start_time = time.time()

        try:
            self._logger.info(f"Selecting radio button: {radio_selector['element']}")

            element = radio_selector['element']
            ref = radio_selector['ref']

            # ラジオボタンをクリック
            click_result = await executor._mcp_wrapper.click_element(element, ref)
            if not click_result.get('success'):
                raise FormInteractionError(f"Failed to click radio button: {click_result}")

            # 状態を取得
            state_result = await executor._mcp_wrapper.get_element_state(element, ref)
            duration = time.time() - start_time

            result_dict = {
                'success': True,
                'selected': state_result.get('selected', True),
                'element_type': state_result.get('element_type', 'radio'),
                'value': state_result.get('value'),
                'group': state_result.get('group')
            }

            # メトリクス更新
            self._update_metrics(True, duration)

            self._logger.info(f"Radio button selection completed: {result_dict}")
            return FormInteractionResult(
                success=True,
                element_type=FormElementType.RADIO,
                interaction_type=InteractionType.CLICK,
                result=result_dict,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            self._update_metrics(False, duration)
            error_msg = f"Radio button selection failed for {radio_selector}: {str(e)}"
            self._logger.error(error_msg)
            return FormInteractionResult(
                success=False,
                element_type=FormElementType.RADIO,
                interaction_type=InteractionType.CLICK,
                result={},
                duration=duration,
                error_message=error_msg
            )

    async def submit_form(self, submit_button_selector: Dict[str, str], wait_for_validation: bool = False, timeout: Optional[float] = None) -> FormInteractionResult:
        """フォームを送信する

        Args:
            submit_button_selector: 送信ボタンセレクター辞書（element, refを含む）
            wait_for_validation: 送信前にバリデーションを待機するか
            timeout: タイムアウト時間（Noneの場合はデフォルト値を使用）

        Returns:
            送信結果辞書

        Raises:
            FormInteractionError: 送信に失敗した場合
            FormSubmissionTimeoutError: タイムアウトした場合
        """
        executor = await self._ensure_executor()
        timeout_val = timeout or self.DEFAULT_SUBMIT_TIMEOUT

        start_time = time.time()

        try:
            self._logger.info(f"Submitting form: {submit_button_selector['element']}")

            element = submit_button_selector['element']
            ref = submit_button_selector['ref']

            # バリデーション待機が必要な場合
            if wait_for_validation:
                wait_result = await executor._mcp_wrapper.wait_for_element(element, ref, 10)
                if not wait_result.get('success'):
                    self._logger.warning("Validation wait failed, but proceeding with submission")

            # 送信ボタンをクリック
            click_result = await executor._mcp_wrapper.click_element(element, ref)
            if not click_result.get('success'):
                raise FormInteractionError(f"Failed to click submit button: {click_result}")

            # ナビゲーション待機
            try:
                nav_result = await asyncio.wait_for(
                    executor._mcp_wrapper.wait_for_navigation(timeout_val),
                    timeout=timeout_val
                )
                duration = time.time() - start_time

                result_dict = {
                    'success': nav_result.get('success', True),
                    'url': nav_result.get('url'),
                    'status_code': nav_result.get('status_code'),
                    'validation_errors': nav_result.get('validation_errors', [])
                }

                if wait_for_validation:
                    result_dict['validation_waited'] = True

                # メトリクス更新
                self._update_metrics(True, duration)

                self._logger.info(f"Form submission completed: {result_dict}")
                return FormInteractionResult(
                    success=True,
                    element_type=FormElementType.SUBMIT_BUTTON,
                    interaction_type=InteractionType.SUBMIT,
                    result=result_dict,
                    duration=duration
                )

            except asyncio.TimeoutError:
                duration = time.time() - start_time
                self._update_metrics(False, duration)
                raise FormSubmissionTimeoutError(f"Form submission timeout after {timeout_val} seconds", timeout_val)

        except FormSubmissionTimeoutError:
            raise
        except Exception as e:
            duration = time.time() - start_time
            self._update_metrics(False, duration)
            error_msg = f"Form submission failed for {submit_button_selector}: {str(e)}"
            self._logger.error(error_msg)
            return FormInteractionResult(
                success=False,
                element_type=FormElementType.SUBMIT_BUTTON,
                interaction_type=InteractionType.SUBMIT,
                result={},
                duration=duration,
                error_message=error_msg
            )

    async def get_form_element_state(self, element_selector: Dict[str, str]) -> Dict[str, Any]:
        """フォーム要素の状態を取得する

        Args:
            element_selector: 要素セレクター辞書（element, refを含む）

        Returns:
            要素状態辞書

        Raises:
            FormInteractionError: 状態取得に失敗した場合
        """
        executor = await self._ensure_executor()

        try:
            element = element_selector['element']
            ref = element_selector['ref']

            result = await executor._mcp_wrapper.get_element_state(element, ref)

            self._logger.debug(f"Element state retrieved: {element} -> {result}")
            return result

        except Exception as e:
            raise FormInteractionError(f"Failed to get element state for {element_selector}: {str(e)}", e)

    async def wait_for_form_element(self, element_selector: Dict[str, str], timeout: Optional[float] = None) -> Dict[str, Any]:
        """フォーム要素の出現を待機する

        Args:
            element_selector: 要素セレクター辞書（element, refを含む）
            timeout: タイムアウト時間（Noneの場合はデフォルト値を使用）

        Returns:
            待機結果辞書

        Raises:
            FormInteractionError: 待機に失敗した場合
        """
        executor = await self._ensure_executor()
        timeout_val = timeout or self._default_timeout

        try:
            element = element_selector['element']
            ref = element_selector['ref']

            result = await executor._mcp_wrapper.wait_for_element(element, ref, timeout_val)

            self._logger.info(f"Element wait completed: {element} -> {result}")
            return result

        except Exception as e:
            raise FormInteractionError(f"Failed to wait for element {element_selector}: {str(e)}", e)

    def get_metrics(self) -> FormInteractionMetrics:
        """現在のメトリクス情報を取得する

        Returns:
            FormInteractionMetrics: メトリクス情報
        """
        return self._metrics

    def reset_metrics(self) -> None:
        """メトリクスをリセットする"""
        self._metrics = FormInteractionMetrics()
        self._logger.info("FormInteractionManager metrics reset")

    def create_form_selector(self, element: str, ref: str, element_type: FormElementType) -> FormElementSelector:
        """フォーム要素セレクターを作成する

        Args:
            element: 人間が理解しやすい要素説明
            ref: 要素の正確なリファレンス
            element_type: フォーム要素タイプ

        Returns:
            FormElementSelector: 構造化されたフォーム要素セレクター
        """
        return FormElementSelector(element=element, ref=ref, element_type=element_type)

    # Task 4.2用の新しいメソッド
    async def batch_form_input(self, form_fields: List[Dict[str, Any]], continue_on_error: bool = False) -> BatchFormInputResult:
        """複数フィールドの一括入力を実行する

        Args:
            form_fields: フォームフィールドのリスト
            continue_on_error: エラー時に処理を続行するか

        Returns:
            BatchFormInputResult: 一括入力結果

        Raises:
            BatchFormInputError: 入力データが不正な場合
        """
        # 入力データの事前検証
        if not form_fields or not isinstance(form_fields, list):
            raise BatchFormInputError("Form fields must be a non-empty list", [], 0)

        # 各フィールドデータの妥当性検証
        invalid_fields = []
        for i, field in enumerate(form_fields):
            if not self._validate_form_field_data(field):
                invalid_fields.append(f"field[{i}]")

        if invalid_fields:
            raise BatchFormInputError(
                f"Invalid field data: {', '.join(invalid_fields)}",
                invalid_fields,
                0
            )

        executor = await self._ensure_executor()
        results = []
        success_count = 0
        error_count = 0
        errors = []

        self._logger.info(f"Starting batch form input for {len(form_fields)} fields")

        for i, field in enumerate(form_fields):
            try:
                self._logger.debug(f"Processing field {i+1}/{len(form_fields)}: {field.get('type', 'unknown')}")

                # ヘルパーメソッドを使用して操作を実行
                result = await self._execute_field_operation(field)

                results.append(result)
                if result.success:
                    success_count += 1
                    self._logger.debug(f"Field {i+1} completed successfully")
                else:
                    error_count += 1
                    errors.append(result)
                    self._logger.warning(f"Field {i+1} failed: {result.error_message}")

                    if not continue_on_error:
                        self._logger.info(f"Stopping batch input at field {i+1} due to error")
                        break

            except Exception as e:
                error_result = self._create_error_result(
                    FormElementType.TEXT_INPUT,
                    InteractionType.TYPE,
                    f"Unexpected error in field {i+1}: {str(e)}"
                )
                results.append(error_result)
                errors.append(error_result)
                error_count += 1
                self._logger.error(f"Unexpected error in field {i+1}: {str(e)}")

                if not continue_on_error:
                    break

        self._logger.info(f"Batch form input completed: {success_count} success, {error_count} errors")

        return BatchFormInputResult(
            success=(error_count == 0),
            results=results,
            success_count=success_count,
            error_count=error_count,
            errors=errors
        )

    async def validate_form_fields(self) -> FormValidationResult:
        """フォームフィールドのバリデーションを実行する

        Returns:
            FormValidationResult: バリデーション結果
        """
        executor = await self._ensure_executor()

        try:
            self._logger.info("Starting form field validation")
            result = await executor._mcp_wrapper.get_validation_errors()

            # ヘルパーメソッドを使用してバリデーションエラーを処理
            validation_errors = self._process_validation_errors(result.get('validation_errors', []))

            # エラーの種類を分析
            has_required_errors = any('required' in error.code.lower() for error in validation_errors)
            has_format_errors = any('format' in error.code.lower() or 'invalid' in error.code.lower() for error in validation_errors)

            validation_result = FormValidationResult(
                success=len(validation_errors) == 0,
                errors=validation_errors,
                has_required_field_errors=has_required_errors,
                has_format_errors=has_format_errors
            )

            self._logger.info(f"Form validation completed: {len(validation_errors)} errors found")
            if validation_errors:
                error_fields = [error.field for error in validation_errors]
                self._logger.debug(f"Validation errors in fields: {error_fields}")

            return validation_result

        except Exception as e:
            self._logger.error(f"Form validation failed: {str(e)}")
            return FormValidationResult(
                success=False,
                errors=[FormValidationError(field="general", message=str(e), code="VALIDATION_ERROR")],
                has_required_field_errors=False,
                has_format_errors=False
            )

    async def validate_required_fields(self, required_fields: List[Dict[str, Any]]) -> RequiredFieldValidationResult:
        """必須フィールドのバリデーションを実行する

        Args:
            required_fields: 必須フィールドのリスト

        Returns:
            RequiredFieldValidationResult: 必須フィールドバリデーション結果
        """
        executor = await self._ensure_executor()

        try:
            result = await executor._mcp_wrapper.check_required_fields()
            missing_fields = result.get('missing_required_fields', [])
            completed_fields = result.get('filled_required_fields', [])

            return RequiredFieldValidationResult(
                success=len(missing_fields) == 0,
                missing_fields=missing_fields,
                completed_fields=completed_fields
            )

        except Exception as e:
            self._logger.error(f"Required field validation failed: {str(e)}")
            return RequiredFieldValidationResult(
                success=False,
                missing_fields=[],
                completed_fields=[]
            )

    async def verify_input_persistence(self, field_selector: Dict[str, str], expected_value: str) -> InputPersistenceResult:
        """入力値の永続性を確認する

        Args:
            field_selector: フィールドセレクター
            expected_value: 期待される値

        Returns:
            InputPersistenceResult: 入力値永続性確認結果
        """
        executor = await self._ensure_executor()

        try:
            element = field_selector['element']
            ref = field_selector['ref']

            result = await executor._mcp_wrapper.get_element_value(element, ref)
            actual_value = result.get('value', '')

            return InputPersistenceResult(
                success=result.get('success', False),
                expected_value=expected_value,
                actual_value=actual_value,
                values_match=(expected_value == actual_value)
            )

        except Exception as e:
            self._logger.error(f"Input persistence verification failed: {str(e)}")
            return InputPersistenceResult(
                success=False,
                expected_value=expected_value,
                actual_value="",
                values_match=False
            )

    async def execute_operations_with_state_tracking(self, operations: List[Dict[str, Any]]) -> FormStateResult:
        """複数操作の実行と状態追跡を行う

        Args:
            operations: 実行する操作のリスト

        Returns:
            FormStateResult: フォーム状態保持結果
        """
        executor = await self._ensure_executor()

        try:
            # 各操作を順次実行
            for operation in operations:
                action = operation['action']
                selector = operation['selector']
                value = operation.get('value')

                if action == 'type_text':
                    await self.type_text_input(selector, value)
                elif action == 'toggle_checkbox':
                    await self.toggle_checkbox(selector, value)
                elif action == 'select_dropdown':
                    await self.select_dropdown_option(selector, [value])

            # 最終的なフォーム状態を取得
            state_result = await executor._mcp_wrapper.get_form_state()
            form_data = state_result.get('form_data', {})

            return FormStateResult(
                success=True,
                final_state=form_data,
                state_preserved_throughout=True
            )

        except Exception as e:
            self._logger.error(f"Operations with state tracking failed: {str(e)}")
            return FormStateResult(
                success=False,
                final_state={},
                state_preserved_throughout=False
            )

    async def comprehensive_form_validation(self) -> ComprehensiveValidationResult:
        """包括的フォームバリデーションを実行する

        Returns:
            ComprehensiveValidationResult: 包括的バリデーション結果
        """
        executor = await self._ensure_executor()

        try:
            result = await executor._mcp_wrapper.validate_form_comprehensive()
            summary = result.get('validation_summary', {})
            field_details = result.get('field_details', [])

            validation_errors = []
            for field in field_details:
                if not field.get('valid', True):
                    error = FormValidationError(
                        field=field.get('field', ''),
                        message=field.get('error', ''),
                        code="VALIDATION_ERROR"
                    )
                    validation_errors.append(error)

            return ComprehensiveValidationResult(
                success=result.get('success', False),
                total_fields=summary.get('total_fields', 0),
                valid_fields=summary.get('valid_fields', 0),
                invalid_fields=summary.get('invalid_fields', 0),
                overall_form_valid=(summary.get('invalid_fields', 0) == 0),
                validation_errors=validation_errors
            )

        except Exception as e:
            self._logger.error(f"Comprehensive form validation failed: {str(e)}")
            return ComprehensiveValidationResult(
                success=False,
                total_fields=0,
                valid_fields=0,
                invalid_fields=0,
                overall_form_valid=False,
                validation_errors=[FormValidationError(field="general", message=str(e), code="VALIDATION_ERROR")]
            )

    async def start_real_time_validation_monitoring(self) -> FormValidationResult:
        """リアルタイムバリデーション監視を開始する

        Returns:
            FormValidationResult: 監視開始結果
        """
        executor = await self._ensure_executor()

        try:
            result = await executor._mcp_wrapper.start_validation_monitoring()
            return FormValidationResult(
                success=result.get('success', False),
                errors=[]
            )

        except Exception as e:
            self._logger.error(f"Start real-time validation monitoring failed: {str(e)}")
            return FormValidationResult(
                success=False,
                errors=[FormValidationError(field="monitoring", message=str(e), code="MONITORING_ERROR")]
            )

    async def get_validation_events(self) -> ValidationEventsResult:
        """バリデーションイベントを取得する

        Returns:
            ValidationEventsResult: バリデーションイベント結果
        """
        executor = await self._ensure_executor()

        try:
            result = await executor._mcp_wrapper.get_validation_events()
            events_data = result.get('events', [])

            events = []
            for event_data in events_data:
                event = ValidationEvent(
                    timestamp=event_data.get('timestamp', ''),
                    field=event_data.get('field', ''),
                    event_type=event_data.get('event_type', ''),
                    message=event_data.get('message', '')
                )
                events.append(event)

            return ValidationEventsResult(
                success=result.get('success', False),
                events=events
            )

        except Exception as e:
            self._logger.error(f"Get validation events failed: {str(e)}")
            return ValidationEventsResult(
                success=False,
                events=[]
            )

    async def cleanup(self) -> None:
        """リソースをクリーンアップする"""
        if self._executor:
            await self._executor.cleanup()
            self._executor = None
            self._logger.info("FormInteractionManager cleanup completed")