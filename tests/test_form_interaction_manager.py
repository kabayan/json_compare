"""Task 4.1: 基本フォーム要素操作テストの実装

TDD実装：テキスト入力、ドロップダウン、チェックボックス・ラジオボタン、フォーム送信処理
Requirements: 4.1, 4.3, 4.4, 4.5 - フォーム要素操作、インタラクション管理
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock, AsyncMock


class TestFormInteractionManagerBasics:
    """フォームインタラクション管理基本テストクラス"""

    def test_form_interaction_manager_initialization(self):
        """FormInteractionManagerが正しく初期化されること"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult

        manager = FormInteractionManager()
        assert manager is not None
        assert hasattr(manager, 'type_text_input')
        assert hasattr(manager, 'select_dropdown_option')
        assert hasattr(manager, 'toggle_checkbox')
        assert hasattr(manager, 'select_radio_button')
        assert hasattr(manager, 'submit_form')

    @pytest.mark.asyncio
    async def test_type_text_input_success(self):
        """テキスト入力フィールドへの文字入力が成功すること"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.type_text.return_value = {
                'success': True,
                'element': 'text-input-field',
                'text': 'テストテキスト',
                'status': 'completed'
            }

            field_selector = {'element': 'text input field', 'ref': 'input-name'}
            input_text = 'テストテキスト'

            result = await manager.type_text_input(field_selector, input_text)

            assert result.success is True
            assert result.element_type.value == 'text_input'
            assert result.interaction_type.value == 'type'
            assert result.result['element'] == 'text-input-field'
            assert result.result['text'] == 'テストテキスト'
            assert result.result['status'] == 'completed'
            assert result.duration is not None

    @pytest.mark.asyncio
    async def test_type_text_input_with_options(self):
        """テキスト入力オプション（slowly, submit）が正しく動作すること"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.type_text.return_value = {
                'success': True,
                'element': 'email-field',
                'text': 'test@example.com',
                'options': {'slowly': True, 'submit': True}
            }

            field_selector = {'element': 'email input', 'ref': 'email-field'}
            email_text = 'test@example.com'
            options = {'slowly': True, 'submit': True}

            result = await manager.type_text_input(field_selector, email_text, options)

            assert result.success is True
            assert result.element_type.value == 'text_input'
            assert result.interaction_type.value == 'type'
            assert result.result['text'] == 'test@example.com'
            assert 'options' in result.result
            assert result.result['options']['slowly'] is True

    @pytest.mark.asyncio
    async def test_select_dropdown_option_single(self):
        """ドロップダウンで単一オプションの選択が成功すること"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.select_option.return_value = {
                'success': True,
                'element': 'model-selector',
                'selected_values': ['qwen3-14b-awq'],
                'selection_type': 'single'
            }

            dropdown_selector = {'element': 'model dropdown', 'ref': 'model-select'}
            option_values = ['qwen3-14b-awq']

            result = await manager.select_dropdown_option(dropdown_selector, option_values)

            assert result.success is True
            assert result.element_type is not None
            assert result.interaction_type is not None
            assert result.result['element'] == 'model-selector'
            assert result.result['selected_values'] == ['qwen3-14b-awq']
            assert result.result['selection_type'] == 'single'

    @pytest.mark.asyncio
    async def test_select_dropdown_option_multiple(self):
        """ドロップダウンで複数オプションの選択が成功すること"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.select_option.return_value = {
                'success': True,
                'element': 'feature-selector',
                'selected_values': ['llm_mode', 'dual_file', 'gpu_acceleration'],
                'selection_type': 'multiple'
            }

            dropdown_selector = {'element': 'feature selector', 'ref': 'features'}
            option_values = ['llm_mode', 'dual_file', 'gpu_acceleration']

            result = await manager.select_dropdown_option(dropdown_selector, option_values)

            assert result.success is True
            assert len(result.result['selected_values']) == 3
            assert result.result['selection_type'] == 'multiple'

    @pytest.mark.asyncio
    async def test_toggle_checkbox_check(self):
        """チェックボックスのチェック操作が成功すること"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.click_element.return_value = {'success': True}
            mock_executor._mcp_wrapper.get_element_state.return_value = {
                'checked': True,
                'element_type': 'checkbox',
                'value': 'gpu_enabled'
            }

            checkbox_selector = {'element': 'GPU acceleration', 'ref': 'gpu-checkbox'}

            result = await manager.toggle_checkbox(checkbox_selector, True)

            assert result.success is True
            assert result.result['checked'] is True
            assert result.result['element_type'] == 'checkbox'

    @pytest.mark.asyncio
    async def test_toggle_checkbox_uncheck(self):
        """チェックボックスのチェック外し操作が成功すること"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.click_element.return_value = {'success': True}
            mock_executor._mcp_wrapper.get_element_state.return_value = {
                'checked': False,
                'element_type': 'checkbox',
                'value': 'gpu_enabled'
            }

            checkbox_selector = {'element': 'GPU acceleration', 'ref': 'gpu-checkbox'}

            result = await manager.toggle_checkbox(checkbox_selector, False)

            assert result.success is True
            assert result.result['checked'] is False

    @pytest.mark.asyncio
    async def test_select_radio_button(self):
        """ラジオボタンの選択が成功すること"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.click_element.return_value = {'success': True}
            mock_executor._mcp_wrapper.get_element_state.return_value = {
                'selected': True,
                'element_type': 'radio',
                'value': 'dual_file_mode',
                'group': 'comparison_mode'
            }

            radio_selector = {'element': 'dual file mode', 'ref': 'dual-mode-radio'}

            result = await manager.select_radio_button(radio_selector)

            assert result.success is True
            assert result.result['selected'] is True
            assert result.result['element_type'] == 'radio'
            assert result.result['value'] == 'dual_file_mode'

    @pytest.mark.asyncio
    async def test_submit_form_success(self):
        """フォーム送信が成功すること"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.click_element.return_value = {'success': True}
            mock_executor._mcp_wrapper.wait_for_navigation.return_value = {
                'success': True,
                'url': '/results',
                'status_code': 200
            }

            submit_button = {'element': 'submit button', 'ref': 'submit-btn'}

            result = await manager.submit_form(submit_button)

            assert result.success is True
            assert result.result['url'] == '/results'
            assert result.result['status_code'] == 200

    @pytest.mark.asyncio
    async def test_submit_form_with_validation_wait(self):
        """フォーム送信前のバリデーション待機が正しく動作すること"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.wait_for_element.return_value = {'success': True}
            mock_executor._mcp_wrapper.click_element.return_value = {'success': True}
            mock_executor._mcp_wrapper.wait_for_navigation.return_value = {
                'success': True,
                'url': '/processing',
                'status_code': 200
            }

            submit_button = {'element': 'submit button', 'ref': 'submit-btn'}
            wait_for_validation = True

            result = await manager.submit_form(submit_button, wait_for_validation)

            assert result.success is True
            assert result.result['validation_waited'] is True


class TestFormInteractionManagerError:
    """フォームインタラクションエラー処理テストクラス"""

    @pytest.mark.asyncio
    async def test_text_input_element_not_found(self):
        """テキスト入力要素が見つからない場合のエラー処理"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult, FormInteractionError

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.type_text.side_effect = Exception("Element not found")

            field_selector = {'element': 'nonexistent field', 'ref': 'missing-input'}

            result = await manager.type_text_input(field_selector, "test text")

            assert result.success is False
            assert result.error_message is not None
            assert "Text input failed" in result.error_message

    @pytest.mark.asyncio
    async def test_dropdown_option_not_available(self):
        """ドロップダウンで指定オプションが利用できない場合のエラー処理"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult, FormInteractionError

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.select_option.side_effect = Exception("Option not available")

            dropdown_selector = {'element': 'model selector', 'ref': 'model-dropdown'}

            result = await manager.select_dropdown_option(dropdown_selector, ['unavailable-model'])

            assert result.success is False
            assert result.error_message is not None
            assert "Dropdown selection failed" in result.error_message

    @pytest.mark.asyncio
    async def test_form_submit_navigation_timeout(self):
        """フォーム送信後のナビゲーション待機タイムアウト処理"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult, FormSubmissionTimeoutError

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.click_element.return_value = {'success': True}
            mock_executor._mcp_wrapper.wait_for_navigation.side_effect = asyncio.TimeoutError()

            submit_button = {'element': 'submit button', 'ref': 'submit-btn'}

            with pytest.raises(FormSubmissionTimeoutError) as exc_info:
                await manager.submit_form(submit_button, wait_for_validation=False, timeout=5)

            assert "Form submission timeout" in str(exc_info.value)


class TestFormInteractionManagerIntegration:
    """フォームインタラクション統合テストクラス"""

    @pytest.mark.asyncio
    async def test_complete_form_filling_workflow(self):
        """完全なフォーム入力ワークフローのテスト"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()

            # テキスト入力
            mock_executor._mcp_wrapper.type_text.return_value = {'success': True}

            # ドロップダウン選択
            mock_executor._mcp_wrapper.select_option.return_value = {
                'success': True,
                'selected_values': ['qwen3-14b-awq']
            }

            # チェックボックス操作
            mock_executor._mcp_wrapper.click_element.return_value = {'success': True}
            mock_executor._mcp_wrapper.get_element_state.return_value = {'checked': True}

            # フォーム送信
            mock_executor._mcp_wrapper.wait_for_navigation.return_value = {
                'success': True,
                'url': '/results'
            }

            try:
                # 1. テキスト入力
                text_result = await manager.type_text_input(
                    {'element': 'name field', 'ref': 'name-input'},
                    'テストユーザー'
                )
                assert text_result.success is True

                # 2. ドロップダウン選択
                dropdown_result = await manager.select_dropdown_option(
                    {'element': 'model selector', 'ref': 'model-select'},
                    ['qwen3-14b-awq']
                )
                assert dropdown_result.success is True

                # 3. チェックボックス選択
                checkbox_result = await manager.toggle_checkbox(
                    {'element': 'GPU option', 'ref': 'gpu-checkbox'},
                    True
                )
                assert checkbox_result.success is True

                # 4. フォーム送信
                submit_result = await manager.submit_form(
                    {'element': 'submit button', 'ref': 'submit-btn'}
                )
                assert submit_result.success is True

            except Exception as e:
                pytest.fail(f"Complete form workflow failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_form_validation_error_handling(self):
        """フォームバリデーションエラーの処理テスト"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.click_element.return_value = {'success': True}
            mock_executor._mcp_wrapper.wait_for_navigation.return_value = {
                'success': False,
                'validation_errors': [
                    {'field': 'email', 'message': 'Invalid email format'},
                    {'field': 'file', 'message': 'File is required'}
                ]
            }

            submit_button = {'element': 'submit button', 'ref': 'submit-btn'}

            result = await manager.submit_form(submit_button)

            # フォーム送信自体は成功するが、バリデーションエラーが含まれる
            assert result.success is True
            assert result.result['success'] is False  # 内部的なレスポンスのsuccessはFalse
            assert 'validation_errors' in result.result
            assert len(result.result['validation_errors']) == 2

    @pytest.mark.asyncio
    async def test_multiple_form_elements_interaction(self):
        """複数フォーム要素の連続操作テスト"""
        from src.form_interaction_manager import FormInteractionManager, FormInteractionResult

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()

            # 各操作の成功レスポンス
            mock_executor._mcp_wrapper.type_text.return_value = {'success': True}
            mock_executor._mcp_wrapper.select_option.return_value = {'success': True}
            mock_executor._mcp_wrapper.click_element.return_value = {'success': True}
            mock_executor._mcp_wrapper.get_element_state.return_value = {'checked': True, 'selected': True}

            # 複数要素の操作
            form_data = [
                {'type': 'text', 'selector': {'element': 'name', 'ref': 'name-input'}, 'value': 'テスト'},
                {'type': 'dropdown', 'selector': {'element': 'model', 'ref': 'model-select'}, 'value': ['qwen3-14b']},
                {'type': 'checkbox', 'selector': {'element': 'gpu', 'ref': 'gpu-check'}, 'value': True},
                {'type': 'radio', 'selector': {'element': 'mode', 'ref': 'dual-radio'}, 'value': True}
            ]

            results = []
            for form_field in form_data:
                if form_field['type'] == 'text':
                    result = await manager.type_text_input(form_field['selector'], form_field['value'])
                elif form_field['type'] == 'dropdown':
                    result = await manager.select_dropdown_option(form_field['selector'], form_field['value'])
                elif form_field['type'] == 'checkbox':
                    result = await manager.toggle_checkbox(form_field['selector'], form_field['value'])
                elif form_field['type'] == 'radio':
                    result = await manager.select_radio_button(form_field['selector'])

                results.append(result)

            # 全ての操作が成功していることを確認
            for result in results:
                assert result.success is True