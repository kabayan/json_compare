"""LLMモード設定とモデル選択テストケース

Task 6.1の要件に対応：
- LLM モード切り替え機能のテスト実装
- モデル選択オプション表示確認の実装
- プロンプトテンプレートアップロード機能テストの作成
- YAML ファイル処理検証の実装
Requirements: 6.1, 6.2 - LLMモード設定、モデル選択、プロンプトテンプレート
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import yaml


def create_manager_with_mock():
    """モックされたラッパー付きのマネージャを作成するヘルパー関数"""
    from src.llm_configuration_manager import LLMConfigurationManager

    mock_wrapper = AsyncMock()
    mock_wrapper.is_initialized = False
    mock_wrapper.initialize = AsyncMock(return_value=None)

    manager = LLMConfigurationManager()
    manager.executor._mcp_wrapper = mock_wrapper

    return manager, mock_wrapper


class TestLLMModeConfiguration:
    """LLMモード設定テストクラス"""

    @pytest.mark.asyncio
    async def test_llm_mode_toggle_activation(self):
        """LLMモード切り替えが正しく動作すること"""
        manager, mock_wrapper = create_manager_with_mock()

        # LLMモード切り替えボタンのクリックをモック
        mock_wrapper.click_element = AsyncMock(return_value={
            'success': True,
            'element': 'llm-mode-toggle',
            'clicked': True
        })

        # モード状態の取得をモック
        mock_wrapper.get_llm_mode_state = AsyncMock(return_value={
            'success': True,
            'llm_enabled': True,
            'mode_label': 'LLMモード: 有効',
            'ui_updated': True
        })

        # LLMモードを切り替え
        result = await manager.toggle_llm_mode()

        assert result.success is True
        assert result.llm_enabled is True
        assert result.mode_label == 'LLMモード: 有効'
        assert result.ui_state_updated is True

    @pytest.mark.asyncio
    async def test_llm_mode_ui_elements_visibility(self):
        """LLMモード有効時にUI要素が表示されること"""
        manager, mock_wrapper = create_manager_with_mock()

        # LLMモード関連UI要素の表示状態をモック
        mock_wrapper.get_llm_ui_elements = AsyncMock(return_value={
            'success': True,
            'model_selector_visible': True,
            'prompt_upload_visible': True,
            'metrics_panel_visible': True,
            'api_settings_visible': True
        })

        # UI要素の表示状態を確認
        result = await manager.verify_llm_ui_visibility()

        assert result.success is True
        assert result.model_selector_visible is True
        assert result.prompt_upload_visible is True
        assert result.metrics_panel_visible is True
        assert result.api_settings_visible is True

    @pytest.mark.asyncio
    async def test_model_selection_dropdown_options(self):
        """モデル選択ドロップダウンのオプションが正しく表示されること"""
        manager, mock_wrapper = create_manager_with_mock()

        # モデルオプションの取得をモック
        mock_wrapper.get_model_options = AsyncMock(return_value={
            'success': True,
            'available_models': [
                {'value': 'qwen3-14b-awq', 'label': 'Qwen3 14B AWQ', 'enabled': True},
                {'value': 'llama3-8b', 'label': 'Llama3 8B', 'enabled': True},
                {'value': 'mixtral-8x7b', 'label': 'Mixtral 8x7B', 'enabled': False}
            ],
            'selected_model': 'qwen3-14b-awq'
        })

        # モデルオプションを取得
        result = await manager.get_available_models()

        assert result.success is True
        assert len(result.models) == 3
        assert result.models[0]['value'] == 'qwen3-14b-awq'
        assert result.selected_model == 'qwen3-14b-awq'
        assert result.has_enabled_models is True

    @pytest.mark.asyncio
    async def test_model_selection_change(self):
        """モデル選択の変更が正しく処理されること"""
        manager, mock_wrapper = create_manager_with_mock()

        # モデル選択をモック
        mock_wrapper.select_option = AsyncMock(return_value={
            'success': True,
            'element': 'model-selector',
            'selected_value': 'llama3-8b'
        })

        # 選択確認をモック
        mock_wrapper.verify_model_selection = AsyncMock(return_value={
            'success': True,
            'current_model': 'llama3-8b',
            'api_updated': True
        })

        # モデルを変更
        result = await manager.select_model('llama3-8b')

        assert result.success is True
        assert result.selected_model == 'llama3-8b'
        assert result.selection_confirmed is True
        assert result.api_configuration_updated is True


class TestPromptTemplateUpload:
    """プロンプトテンプレートアップロードテストクラス"""

    @pytest.mark.asyncio
    async def test_prompt_template_file_upload(self):
        """プロンプトテンプレートファイルのアップロードが成功すること"""
        manager, mock_wrapper = create_manager_with_mock()

        # ファイルアップロードをモック
        mock_wrapper.upload_file = AsyncMock(return_value={
            'success': True,
            'file_path': '/tmp/uploads/custom_prompt.yaml',
            'filename': 'custom_prompt.yaml',
            'upload_id': 'upload_789'
        })

        # YAMLファイル検証をモック
        mock_wrapper.validate_yaml_file = AsyncMock(return_value={
            'success': True,
            'valid_yaml': True,
            'has_required_fields': True
        })

        # プロンプトテンプレートをアップロード
        result = await manager.upload_prompt_template('/path/to/prompt.yaml')

        assert result.success is True
        assert result.file_uploaded is True
        assert result.yaml_valid is True
        assert result.template_loaded is True

    @pytest.mark.asyncio
    async def test_yaml_file_validation(self):
        """YAMLファイルの内容が正しく検証されること"""
        manager, mock_wrapper = create_manager_with_mock()

        yaml_content = """
        system_prompt: "You are a helpful assistant"
        user_prompt_template: "Compare: {text1} and {text2}"
        temperature: 0.7
        max_tokens: 512
        """

        # YAMLファイル内容の取得をモック
        mock_wrapper.get_uploaded_content = AsyncMock(return_value={
            'success': True,
            'content': yaml_content,
            'file_type': 'yaml'
        })

        # YAML検証を実行
        result = await manager.validate_yaml_content('/tmp/uploads/custom_prompt.yaml')

        assert result.success is True
        assert result.has_system_prompt is True
        assert result.has_user_prompt_template is True
        assert result.temperature == 0.7
        assert result.max_tokens == 512
        assert result.is_valid_template is True

    @pytest.mark.asyncio
    async def test_invalid_yaml_handling(self):
        """無効なYAMLファイルのエラーハンドリング"""
        manager, mock_wrapper = create_manager_with_mock()

        # 無効なYAMLファイルのアップロードをモック
        mock_wrapper.upload_file = AsyncMock(return_value={
            'success': True,
            'file_path': '/tmp/uploads/invalid.yaml',
            'filename': 'invalid.yaml'
        })

        # YAML検証エラーをモック
        mock_wrapper.validate_yaml_file = AsyncMock(return_value={
            'success': False,
            'valid_yaml': False,
            'error': 'Invalid YAML syntax',
            'error_line': 5
        })

        # エラー表示をモック
        mock_wrapper.show_error_message = AsyncMock(return_value={
            'success': True,
            'error_displayed': True
        })

        # 無効なYAMLをアップロード
        result = await manager.upload_prompt_template('/path/to/invalid.yaml')

        assert result.success is False
        assert result.yaml_valid is False
        assert result.error_message == 'Invalid YAML syntax'
        assert result.error_displayed is True

    @pytest.mark.asyncio
    async def test_prompt_template_preview(self):
        """プロンプトテンプレートのプレビュー表示"""
        manager, mock_wrapper = create_manager_with_mock()

        # プレビュー表示をモック
        mock_wrapper.show_template_preview = AsyncMock(return_value={
            'success': True,
            'preview_visible': True,
            'template_content': {
                'system': 'You are a helpful assistant',
                'user': 'Compare: {text1} and {text2}',
                'variables': ['text1', 'text2']
            }
        })

        # テンプレートプレビューを表示
        result = await manager.preview_prompt_template()

        assert result.success is True
        assert result.preview_displayed is True
        assert 'system' in result.template_sections
        assert 'user' in result.template_sections
        assert len(result.template_variables) == 2


class TestLLMProcessingErrors:
    """LLM処理エラーテストクラス"""

    @pytest.mark.asyncio
    async def test_vllm_api_connection_error(self):
        """vLLM API接続エラーの処理"""
        manager, mock_wrapper = create_manager_with_mock()

        # API接続エラーをモック
        mock_wrapper.test_api_connection = AsyncMock(return_value={
            'success': False,
            'error': 'Connection refused',
            'error_code': 'CONN_REFUSED'
        })

        # エラー表示をモック
        mock_wrapper.display_connection_error = AsyncMock(return_value={
            'success': True,
            'error_shown': True,
            'fallback_option_shown': True
        })

        # API接続をテスト
        result = await manager.test_vllm_connection()

        assert result.success is False
        assert result.connection_failed is True
        assert result.error_code == 'CONN_REFUSED'
        assert result.error_displayed is True
        assert result.fallback_available is True

    @pytest.mark.asyncio
    async def test_timeout_and_cancellation(self):
        """タイムアウトとキャンセル機能のテスト"""
        manager, mock_wrapper = create_manager_with_mock()

        # 長時間処理をモック
        mock_wrapper.start_llm_processing = AsyncMock(return_value={
            'success': True,
            'process_id': 'proc_123',
            'cancel_button_visible': True
        })

        # キャンセル操作をモック
        mock_wrapper.cancel_processing = AsyncMock(return_value={
            'success': True,
            'process_cancelled': True,
            'cleanup_completed': True
        })

        # 処理を開始してキャンセル
        start_result = await manager.start_llm_processing()
        assert start_result.cancel_available is True

        cancel_result = await manager.cancel_llm_processing('proc_123')
        assert cancel_result.success is True
        assert cancel_result.cancelled_successfully is True

    @pytest.mark.asyncio
    async def test_metrics_display(self):
        """メトリクス表示の確認テスト"""
        manager, mock_wrapper = create_manager_with_mock()

        # メトリクス取得をモック
        mock_wrapper.get_llm_metrics = AsyncMock(return_value={
            'success': True,
            'metrics': {
                'token_count': 1024,
                'processing_time': 2.5,
                'tokens_per_second': 409.6,
                'model_name': 'qwen3-14b-awq'
            },
            'display_updated': True
        })

        # メトリクスを取得
        result = await manager.get_processing_metrics()

        assert result.success is True
        assert result.token_count == 1024
        assert result.processing_time == 2.5
        assert result.tokens_per_second == 409.6
        assert result.metrics_displayed is True

    @pytest.mark.asyncio
    async def test_fallback_behavior(self):
        """フォールバック動作の検証"""
        manager, mock_wrapper = create_manager_with_mock()

        # LLMモード失敗をモック
        mock_wrapper.process_with_llm = AsyncMock(side_effect=Exception("LLM service unavailable"))

        # フォールバック実行をモック
        mock_wrapper.process_with_embedding = AsyncMock(return_value={
            'success': True,
            'fallback_used': True,
            'method': 'embedding',
            'result': {'score': 0.85}
        })

        # フォールバック通知をモック
        mock_wrapper.show_fallback_notice = AsyncMock(return_value={
            'success': True,
            'notice_displayed': True
        })

        # フォールバック動作を実行
        result = await manager.process_with_fallback()

        assert result.success is True
        assert result.fallback_executed is True
        assert result.fallback_method == 'embedding'
        assert result.user_notified is True