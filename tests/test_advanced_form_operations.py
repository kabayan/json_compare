"""複合フォーム操作とバリデーションテストの高度なテストケース

Task 4.2の要件に対応：
- 複数フィールド一括入力機能のテスト実装
- フォームバリデーションエラー検証の実装
- 必須フィールド確認テストの作成
- 入力値の永続性確認テストの実装
Requirements: 4.2, 4.5 - 複合フォーム操作、バリデーション処理
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestAdvancedFormOperations:
    """複合フォーム操作テストクラス"""

    @pytest.mark.asyncio
    async def test_batch_form_field_input_success(self):
        """複数フィールドの一括入力が成功すること"""
        from src.form_interaction_manager import FormInteractionManager

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.type_text.return_value = {'success': True}
            mock_executor._mcp_wrapper.select_option.return_value = {'success': True}
            mock_executor._mcp_wrapper.click_element.return_value = {'success': True}
            mock_executor._mcp_wrapper.get_element_state.return_value = {'checked': True, 'selected': True}

            # 複数フィールドの一括入力データ
            form_fields = [
                {
                    'type': 'text',
                    'selector': {'element': 'name field', 'ref': 'name-input'},
                    'value': 'テストユーザー'
                },
                {
                    'type': 'text',
                    'selector': {'element': 'email field', 'ref': 'email-input'},
                    'value': 'test@example.com'
                },
                {
                    'type': 'dropdown',
                    'selector': {'element': 'model selector', 'ref': 'model-select'},
                    'value': ['qwen3-14b-awq']
                },
                {
                    'type': 'checkbox',
                    'selector': {'element': 'gpu option', 'ref': 'gpu-checkbox'},
                    'value': True
                }
            ]

            # 一括入力機能を使用（まだ実装されていないためテストは失敗する）
            result = await manager.batch_form_input(form_fields)

            assert result.success is True
            assert len(result.results) == 4
            assert all(field_result.success for field_result in result.results)

    @pytest.mark.asyncio
    async def test_batch_form_input_with_validation_errors(self):
        """一括入力でバリデーションエラーが発生した場合の処理"""
        from src.form_interaction_manager import FormInteractionManager

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            # 2番目のフィールドでエラーが発生
            mock_executor._mcp_wrapper.type_text.side_effect = [
                {'success': True},  # 1番目は成功
                Exception("Invalid email format"),  # 2番目でエラー
                {'success': True}  # 3番目は成功
            ]

            form_fields = [
                {
                    'type': 'text',
                    'selector': {'element': 'name field', 'ref': 'name-input'},
                    'value': 'テストユーザー'
                },
                {
                    'type': 'text',
                    'selector': {'element': 'email field', 'ref': 'email-input'},
                    'value': 'invalid-email'  # 不正なメール形式
                },
                {
                    'type': 'text',
                    'selector': {'element': 'phone field', 'ref': 'phone-input'},
                    'value': '090-1234-5678'
                }
            ]

            result = await manager.batch_form_input(form_fields, continue_on_error=True)

            # 部分的成功の結果を検証
            assert result.success is False  # 全体としては失敗
            assert result.success_count == 2
            assert result.error_count == 1
            assert len(result.errors) == 1
            assert "Invalid email format" in result.errors[0].error_message

    @pytest.mark.asyncio
    async def test_form_validation_error_detection(self):
        """フォームバリデーションエラーの検出と詳細取得"""
        from src.form_interaction_manager import FormInteractionManager

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.get_validation_errors.return_value = {
                'success': True,
                'validation_errors': [
                    {
                        'field': 'email',
                        'message': 'メールアドレス形式が正しくありません',
                        'code': 'INVALID_EMAIL_FORMAT'
                    },
                    {
                        'field': 'phone',
                        'message': '電話番号は必須項目です',
                        'code': 'REQUIRED_FIELD_MISSING'
                    }
                ]
            }

            # バリデーションエラー検証機能を使用
            validation_result = await manager.validate_form_fields()

            assert validation_result.success is False  # エラーが検出されたため False
            assert len(validation_result.errors) == 2
            assert validation_result.has_required_field_errors is True
            assert validation_result.has_format_errors is True
            assert validation_result.errors[0].field == 'email'
            assert validation_result.errors[1].field == 'phone'

    @pytest.mark.asyncio
    async def test_required_field_validation(self):
        """必須フィールドの検証機能テスト"""
        from src.form_interaction_manager import FormInteractionManager

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.check_required_fields.return_value = {
                'success': True,
                'missing_required_fields': ['name', 'email'],
                'all_required_fields': ['name', 'email', 'file_upload'],
                'filled_required_fields': ['file_upload']
            }

            # 必須フィールド確認機能を使用
            required_fields = [
                {'element': 'name field', 'ref': 'name-input', 'required': True},
                {'element': 'email field', 'ref': 'email-input', 'required': True},
                {'element': 'file upload', 'ref': 'file-input', 'required': True}
            ]

            validation_result = await manager.validate_required_fields(required_fields)

            assert validation_result.success is False  # 必須フィールドが未入力のため失敗
            assert len(validation_result.missing_fields) == 2
            assert 'name' in validation_result.missing_fields
            assert 'email' in validation_result.missing_fields
            assert len(validation_result.completed_fields) == 1

    @pytest.mark.asyncio
    async def test_input_value_persistence_check(self):
        """入力値の永続性確認テスト"""
        from src.form_interaction_manager import FormInteractionManager

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            # 最初の入力
            mock_executor._mcp_wrapper.type_text.return_value = {'success': True}
            # 値の確認
            mock_executor._mcp_wrapper.get_element_value.return_value = {
                'success': True,
                'value': 'テストデータ',
                'element_type': 'input'
            }

            field_selector = {'element': 'name field', 'ref': 'name-input'}
            test_value = 'テストデータ'

            # 値を入力
            input_result = await manager.type_text_input(field_selector, test_value)
            assert input_result.success is True

            # 入力値の永続性を確認
            persistence_result = await manager.verify_input_persistence(field_selector, test_value)

            assert persistence_result.success is True
            assert persistence_result.expected_value == test_value
            assert persistence_result.actual_value == test_value
            assert persistence_result.values_match is True

    @pytest.mark.asyncio
    async def test_form_state_preservation_across_interactions(self):
        """フォーム操作間での状態保持テスト"""
        from src.form_interaction_manager import FormInteractionManager

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.type_text.return_value = {'success': True}
            mock_executor._mcp_wrapper.click_element.return_value = {'success': True}
            mock_executor._mcp_wrapper.get_form_state.return_value = {
                'success': True,
                'form_data': {
                    'name': 'テストユーザー',
                    'email': 'test@example.com',
                    'gpu_enabled': True
                }
            }

            # 複数の操作を順次実行
            operations = [
                {
                    'action': 'type_text',
                    'selector': {'element': 'name field', 'ref': 'name-input'},
                    'value': 'テストユーザー'
                },
                {
                    'action': 'type_text',
                    'selector': {'element': 'email field', 'ref': 'email-input'},
                    'value': 'test@example.com'
                },
                {
                    'action': 'toggle_checkbox',
                    'selector': {'element': 'gpu option', 'ref': 'gpu-checkbox'},
                    'value': True
                }
            ]

            # フォーム状態保持機能を使用
            result = await manager.execute_operations_with_state_tracking(operations)

            assert result.success is True
            assert result.final_state['name'] == 'テストユーザー'
            assert result.final_state['email'] == 'test@example.com'
            assert result.final_state['gpu_enabled'] is True
            assert result.state_preserved_throughout is True


class TestFormValidationIntegration:
    """フォームバリデーション統合テストクラス"""

    @pytest.mark.asyncio
    async def test_comprehensive_form_validation_workflow(self):
        """包括的なフォームバリデーションワークフロー"""
        from src.form_interaction_manager import FormInteractionManager

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.validate_form_comprehensive.return_value = {
                'success': True,
                'validation_summary': {
                    'total_fields': 5,
                    'valid_fields': 3,
                    'invalid_fields': 2,
                    'required_fields_missing': 1,
                    'format_errors': 1
                },
                'field_details': [
                    {'field': 'name', 'valid': True, 'value': 'テストユーザー'},
                    {'field': 'email', 'valid': False, 'error': 'Invalid format'},
                    {'field': 'phone', 'valid': False, 'error': 'Required field missing'},
                    {'field': 'model', 'valid': True, 'value': 'qwen3-14b-awq'},
                    {'field': 'gpu', 'valid': True, 'value': True}
                ]
            }

            # 包括的バリデーション実行
            validation_result = await manager.comprehensive_form_validation()

            assert validation_result.success is True
            assert validation_result.total_fields == 5
            assert validation_result.valid_fields == 3
            assert validation_result.invalid_fields == 2
            assert validation_result.overall_form_valid is False
            assert len(validation_result.validation_errors) == 2

    @pytest.mark.asyncio
    async def test_real_time_validation_monitoring(self):
        """リアルタイムバリデーション監視テスト"""
        from src.form_interaction_manager import FormInteractionManager

        manager = FormInteractionManager()

        with patch('src.form_interaction_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.start_validation_monitoring.return_value = {'success': True}
            mock_executor._mcp_wrapper.get_validation_events.return_value = {
                'success': True,
                'events': [
                    {
                        'timestamp': '2024-01-20T10:00:00Z',
                        'field': 'email',
                        'event_type': 'validation_error',
                        'message': 'Invalid email format'
                    },
                    {
                        'timestamp': '2024-01-20T10:00:05Z',
                        'field': 'email',
                        'event_type': 'validation_success',
                        'message': 'Email format is valid'
                    }
                ]
            }

            # リアルタイムバリデーション監視開始
            monitoring_result = await manager.start_real_time_validation_monitoring()
            assert monitoring_result.success is True

            # バリデーションイベント取得
            events_result = await manager.get_validation_events()
            assert events_result.success is True
            assert len(events_result.events) == 2
            assert events_result.events[0].event_type == 'validation_error'
            assert events_result.events[1].event_type == 'validation_success'