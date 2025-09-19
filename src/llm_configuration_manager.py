"""LLM設定とモデル選択管理マネージャー

WebUIのLLMモード設定とモデル選択を管理するマネージャークラス。
Task 6の実装に対応。
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from src.mcp_wrapper import MCPTestExecutor, PlaywrightMCPWrapper
import yaml


@dataclass
class LLMModeToggleResult:
    """LLMモード切り替え結果"""
    success: bool
    llm_enabled: bool = False
    mode_label: str = ""
    ui_state_updated: bool = False


@dataclass
class LLMUIVisibilityResult:
    """LLM UI要素表示状態結果"""
    success: bool
    model_selector_visible: bool = False
    prompt_upload_visible: bool = False
    metrics_panel_visible: bool = False
    api_settings_visible: bool = False


@dataclass
class ModelOptionsResult:
    """モデルオプション結果"""
    success: bool
    models: List[Dict[str, Any]] = field(default_factory=list)
    selected_model: str = ""
    has_enabled_models: bool = False


@dataclass
class ModelSelectionResult:
    """モデル選択結果"""
    success: bool
    selected_model: str = ""
    selection_confirmed: bool = False
    api_configuration_updated: bool = False


@dataclass
class PromptTemplateUploadResult:
    """プロンプトテンプレートアップロード結果"""
    success: bool
    file_uploaded: bool = False
    yaml_valid: bool = False
    template_loaded: bool = False
    error_message: str = ""
    error_displayed: bool = False


@dataclass
class YAMLValidationResult:
    """YAML検証結果"""
    success: bool
    has_system_prompt: bool = False
    has_user_prompt_template: bool = False
    temperature: float = 0.0
    max_tokens: int = 0
    is_valid_template: bool = False


@dataclass
class PromptPreviewResult:
    """プロンプトプレビュー結果"""
    success: bool
    preview_displayed: bool = False
    template_sections: Dict[str, str] = field(default_factory=dict)
    template_variables: List[str] = field(default_factory=list)


@dataclass
class VLLMConnectionResult:
    """vLLM接続テスト結果"""
    success: bool
    connection_failed: bool = False
    error_code: str = ""
    error_displayed: bool = False
    fallback_available: bool = False


@dataclass
class LLMProcessingResult:
    """LLM処理結果"""
    success: bool
    process_id: str = ""
    cancel_available: bool = False
    cancelled_successfully: bool = False


@dataclass
class ProcessingMetricsResult:
    """処理メトリクス結果"""
    success: bool
    token_count: int = 0
    processing_time: float = 0.0
    tokens_per_second: float = 0.0
    metrics_displayed: bool = False


@dataclass
class FallbackResult:
    """フォールバック結果"""
    success: bool
    fallback_executed: bool = False
    fallback_method: str = ""
    user_notified: bool = False


class LLMConfigurationManager:
    """LLM設定管理マネージャー"""

    def __init__(self):
        self.executor = MCPTestExecutor()
        # MCPラッパーを初期化
        self.executor._mcp_wrapper = PlaywrightMCPWrapper()

    async def _ensure_initialized(self):
        """ラッパーが初期化されていることを確認する"""
        if self.executor._mcp_wrapper and not self.executor._mcp_wrapper.is_initialized:
            await self.executor._mcp_wrapper.initialize()

    async def toggle_llm_mode(self) -> LLMModeToggleResult:
        """LLMモードを切り替える"""
        try:
            await self._ensure_initialized()

            # LLMモード切り替えボタンをクリック
            click_result = await self.executor._mcp_wrapper.click_element(
                element="llm-mode-toggle",
                ref="llm-mode-toggle"
            )

            if not click_result.get('success'):
                return LLMModeToggleResult(success=False)

            # モード状態を取得
            state_result = await self.executor._mcp_wrapper.get_llm_mode_state()

            if state_result.get('success'):
                return LLMModeToggleResult(
                    success=True,
                    llm_enabled=state_result.get('llm_enabled', False),
                    mode_label=state_result.get('mode_label', ''),
                    ui_state_updated=state_result.get('ui_updated', False)
                )

            return LLMModeToggleResult(success=False)

        except Exception as e:
            return LLMModeToggleResult(success=False)

    async def verify_llm_ui_visibility(self) -> LLMUIVisibilityResult:
        """LLM UI要素の表示状態を確認する"""
        try:
            await self._ensure_initialized()

            ui_result = await self.executor._mcp_wrapper.get_llm_ui_elements()

            if ui_result.get('success'):
                return LLMUIVisibilityResult(
                    success=True,
                    model_selector_visible=ui_result.get('model_selector_visible', False),
                    prompt_upload_visible=ui_result.get('prompt_upload_visible', False),
                    metrics_panel_visible=ui_result.get('metrics_panel_visible', False),
                    api_settings_visible=ui_result.get('api_settings_visible', False)
                )

            return LLMUIVisibilityResult(success=False)

        except Exception as e:
            return LLMUIVisibilityResult(success=False)

    async def get_available_models(self) -> ModelOptionsResult:
        """利用可能なモデルを取得する"""
        try:
            await self._ensure_initialized()

            models_result = await self.executor._mcp_wrapper.get_model_options()

            if models_result.get('success'):
                models = models_result.get('available_models', [])
                has_enabled = any(m.get('enabled', False) for m in models)

                return ModelOptionsResult(
                    success=True,
                    models=models,
                    selected_model=models_result.get('selected_model', ''),
                    has_enabled_models=has_enabled
                )

            return ModelOptionsResult(success=False)

        except Exception as e:
            return ModelOptionsResult(success=False)

    async def select_model(self, model_value: str) -> ModelSelectionResult:
        """モデルを選択する"""
        try:
            await self._ensure_initialized()

            # モデルを選択
            select_result = await self.executor._mcp_wrapper.select_option(
                element="model-selector",
                ref="model-selector",
                values=[model_value]
            )

            if not select_result.get('success'):
                return ModelSelectionResult(success=False)

            # 選択を確認
            verify_result = await self.executor._mcp_wrapper.verify_model_selection()

            if verify_result.get('success'):
                return ModelSelectionResult(
                    success=True,
                    selected_model=verify_result.get('current_model', model_value),
                    selection_confirmed=True,
                    api_configuration_updated=verify_result.get('api_updated', False)
                )

            return ModelSelectionResult(success=False)

        except Exception as e:
            return ModelSelectionResult(success=False)

    async def upload_prompt_template(self, file_path: str) -> PromptTemplateUploadResult:
        """プロンプトテンプレートをアップロードする"""
        try:
            await self._ensure_initialized()

            # ファイルをアップロード
            upload_result = await self.executor._mcp_wrapper.upload_file(file_path)

            if not upload_result.get('success'):
                return PromptTemplateUploadResult(success=False)

            # YAMLファイルを検証
            validate_result = await self.executor._mcp_wrapper.validate_yaml_file()

            if validate_result.get('valid_yaml', False):
                return PromptTemplateUploadResult(
                    success=True,
                    file_uploaded=True,
                    yaml_valid=True,
                    template_loaded=validate_result.get('has_required_fields', False)
                )
            else:
                # エラー表示
                await self.executor._mcp_wrapper.show_error_message()
                return PromptTemplateUploadResult(
                    success=False,
                    file_uploaded=True,
                    yaml_valid=False,
                    error_message=validate_result.get('error', 'Invalid YAML syntax'),
                    error_displayed=True
                )

        except Exception as e:
            return PromptTemplateUploadResult(
                success=False,
                error_message=str(e)
            )

    async def validate_yaml_content(self, file_path: str) -> YAMLValidationResult:
        """YAML内容を検証する"""
        try:
            await self._ensure_initialized()

            # アップロードされた内容を取得
            content_result = await self.executor._mcp_wrapper.get_uploaded_content()

            if content_result.get('success'):
                yaml_content = content_result.get('content', '')

                # YAMLをパース
                try:
                    yaml_data = yaml.safe_load(yaml_content)

                    return YAMLValidationResult(
                        success=True,
                        has_system_prompt='system_prompt' in yaml_data,
                        has_user_prompt_template='user_prompt_template' in yaml_data,
                        temperature=yaml_data.get('temperature', 0.0),
                        max_tokens=yaml_data.get('max_tokens', 0),
                        is_valid_template=True
                    )
                except yaml.YAMLError:
                    return YAMLValidationResult(success=False)

            return YAMLValidationResult(success=False)

        except Exception as e:
            return YAMLValidationResult(success=False)

    async def preview_prompt_template(self) -> PromptPreviewResult:
        """プロンプトテンプレートをプレビューする"""
        try:
            await self._ensure_initialized()

            preview_result = await self.executor._mcp_wrapper.show_template_preview()

            if preview_result.get('success'):
                template_content = preview_result.get('template_content', {})

                return PromptPreviewResult(
                    success=True,
                    preview_displayed=preview_result.get('preview_visible', False),
                    template_sections={
                        'system': template_content.get('system', ''),
                        'user': template_content.get('user', '')
                    },
                    template_variables=template_content.get('variables', [])
                )

            return PromptPreviewResult(success=False)

        except Exception as e:
            return PromptPreviewResult(success=False)

    async def test_vllm_connection(self) -> VLLMConnectionResult:
        """vLLM接続をテストする"""
        try:
            await self._ensure_initialized()

            # API接続をテスト
            test_result = await self.executor._mcp_wrapper.test_api_connection()

            if not test_result.get('success'):
                # エラー表示
                await self.executor._mcp_wrapper.display_connection_error()

                return VLLMConnectionResult(
                    success=False,
                    connection_failed=True,
                    error_code=test_result.get('error_code', ''),
                    error_displayed=True,
                    fallback_available=True
                )

            return VLLMConnectionResult(success=True)

        except Exception as e:
            return VLLMConnectionResult(
                success=False,
                connection_failed=True
            )

    async def start_llm_processing(self) -> LLMProcessingResult:
        """LLM処理を開始する"""
        try:
            await self._ensure_initialized()

            start_result = await self.executor._mcp_wrapper.start_llm_processing()

            if start_result.get('success'):
                return LLMProcessingResult(
                    success=True,
                    process_id=start_result.get('process_id', ''),
                    cancel_available=start_result.get('cancel_button_visible', False)
                )

            return LLMProcessingResult(success=False)

        except Exception as e:
            return LLMProcessingResult(success=False)

    async def cancel_llm_processing(self, process_id: str) -> LLMProcessingResult:
        """LLM処理をキャンセルする"""
        try:
            await self._ensure_initialized()

            cancel_result = await self.executor._mcp_wrapper.cancel_processing()

            if cancel_result.get('success'):
                return LLMProcessingResult(
                    success=True,
                    process_id=process_id,
                    cancelled_successfully=cancel_result.get('process_cancelled', False)
                )

            return LLMProcessingResult(success=False)

        except Exception as e:
            return LLMProcessingResult(success=False)

    async def get_processing_metrics(self) -> ProcessingMetricsResult:
        """処理メトリクスを取得する"""
        try:
            await self._ensure_initialized()

            metrics_result = await self.executor._mcp_wrapper.get_llm_metrics()

            if metrics_result.get('success'):
                metrics = metrics_result.get('metrics', {})

                return ProcessingMetricsResult(
                    success=True,
                    token_count=metrics.get('token_count', 0),
                    processing_time=metrics.get('processing_time', 0.0),
                    tokens_per_second=metrics.get('tokens_per_second', 0.0),
                    metrics_displayed=metrics_result.get('display_updated', False)
                )

            return ProcessingMetricsResult(success=False)

        except Exception as e:
            return ProcessingMetricsResult(success=False)

    async def process_with_fallback(self) -> FallbackResult:
        """フォールバック付きで処理する"""
        try:
            await self._ensure_initialized()

            try:
                # LLMモードで処理を試行
                llm_result = await self.executor._mcp_wrapper.process_with_llm()
                if llm_result.get('success'):
                    return FallbackResult(
                        success=True,
                        fallback_executed=False
                    )
            except Exception:
                # フォールバックを実行
                fallback_result = await self.executor._mcp_wrapper.process_with_embedding()

                if fallback_result.get('success'):
                    # フォールバック通知を表示
                    await self.executor._mcp_wrapper.show_fallback_notice()

                    return FallbackResult(
                        success=True,
                        fallback_executed=True,
                        fallback_method=fallback_result.get('method', 'embedding'),
                        user_notified=True
                    )

            return FallbackResult(success=False)

        except Exception as e:
            return FallbackResult(success=False)