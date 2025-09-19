"""ダウンロード機能とエラー表示テストケース

Task 5.2の要件に対応：
- CSV ダウンロード機能の動作確認テスト実装
- ダウンロードファイルの内容検証実装
- エラーメッセージとエラーID表示確認の実装
- エラー状態からのリカバリテストの作成
Requirements: 5.3, 5.4 - CSVダウンロード、エラーメッセージ表示
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def create_manager_with_mock():
    """モックされたラッパー付きのマネージャを作成するヘルパー関数"""
    from src.download_and_error_manager import DownloadAndErrorManager

    mock_wrapper = AsyncMock()
    mock_wrapper.is_initialized = False
    mock_wrapper.initialize = AsyncMock(return_value=None)

    manager = DownloadAndErrorManager()
    manager.executor._mcp_wrapper = mock_wrapper

    return manager, mock_wrapper


class TestCSVDownloadFunctionality:
    """CSVダウンロード機能テストクラス"""

    @pytest.mark.asyncio
    async def test_csv_download_link_click(self):
        """CSVダウンロードリンクのクリックが正しく動作すること"""
        manager, mock_wrapper = create_manager_with_mock()

        # ダウンロードリンクのクリックをモック
        mock_wrapper.click_element = AsyncMock(return_value={
            'success': True,
            'element': 'csv-download-link',
            'clicked': True
        })

        # ダウンロード開始の確認をモック
        mock_wrapper.wait_for_download = AsyncMock(return_value={
            'success': True,
            'download_id': 'dl_12345',
            'filename': 'comparison_results.csv',
            'status': 'started'
        })

        # CSVダウンロードを実行
        result = await manager.initiate_csv_download()

        assert result.success is True
        assert result.download_started is True
        assert result.download_id == 'dl_12345'
        assert result.filename == 'comparison_results.csv'

    @pytest.mark.asyncio
    async def test_csv_download_completion(self):
        """CSVダウンロードの完了が正しく確認できること"""
        manager, mock_wrapper = create_manager_with_mock()

        # ダウンロード完了の確認をモック
        mock_wrapper.check_download_status = AsyncMock(return_value={
            'success': True,
            'status': 'completed',
            'download_path': '/tmp/downloads/comparison_results.csv',
            'file_size': 2048
        })

        # ダウンロード完了を確認
        result = await manager.verify_download_completion('dl_12345')

        assert result.success is True
        assert result.is_completed is True
        assert result.download_path == '/tmp/downloads/comparison_results.csv'
        assert result.file_size == 2048

    @pytest.mark.asyncio
    async def test_csv_file_content_validation(self):
        """CSVファイル内容の妥当性検証"""
        manager, mock_wrapper = create_manager_with_mock()

        # CSVファイル内容の取得をモック
        mock_wrapper.read_download_file = AsyncMock(return_value={
            'success': True,
            'content': 'id,inference1,inference2,score\n1,"text1","text2",0.85\n',
            'rows': 2,
            'columns': 4
        })

        # CSVファイル内容を検証
        result = await manager.validate_csv_content('/tmp/downloads/comparison_results.csv')

        assert result.success is True
        assert result.has_header is True
        assert result.column_count == 4
        assert result.row_count == 2
        assert 'score' in result.headers
        assert result.is_valid_csv is True

    @pytest.mark.asyncio
    async def test_large_csv_download_with_progress(self):
        """大量データのCSVダウンロード時のプログレス表示"""
        manager, mock_wrapper = create_manager_with_mock()

        # プログレス付きダウンロードをモック
        mock_wrapper.monitor_download_progress = AsyncMock(return_value={
            'success': True,
            'progress_updates': [
                {'percentage': 25, 'bytes': 256000},
                {'percentage': 50, 'bytes': 512000},
                {'percentage': 75, 'bytes': 768000},
                {'percentage': 100, 'bytes': 1024000}
            ],
            'total_bytes': 1024000,
            'duration': 3.5
        })

        # プログレス付きダウンロードを監視
        result = await manager.monitor_large_download('dl_67890')

        assert result.success is True
        assert len(result.progress_updates) == 4
        assert result.final_percentage == 100
        assert result.total_bytes == 1024000
        assert result.download_speed is not None


class TestErrorDisplayFunctionality:
    """エラー表示機能テストクラス"""

    @pytest.mark.asyncio
    async def test_error_message_display_verification(self):
        """エラーメッセージの表示が正しく確認できること"""
        manager, mock_wrapper = create_manager_with_mock()

        # エラー要素の取得をモック
        mock_wrapper.get_error_elements = AsyncMock(return_value={
            'success': True,
            'error_present': True,
            'error_message': 'ファイル処理中にエラーが発生しました',
            'error_type': 'FileProcessingError',
            'error_container_visible': True
        })

        # エラーメッセージ表示を検証
        result = await manager.verify_error_display()

        assert result.success is True
        assert result.error_displayed is True
        assert result.error_message == 'ファイル処理中にエラーが発生しました'
        assert result.error_type == 'FileProcessingError'
        assert result.is_visible is True

    @pytest.mark.asyncio
    async def test_error_id_display_and_tracking(self):
        """エラーIDの表示と追跡が正しく動作すること"""
        manager, mock_wrapper = create_manager_with_mock()

        # エラーID表示の取得をモック
        mock_wrapper.get_error_details = AsyncMock(return_value={
            'success': True,
            'error_id': 'ERR-2024-001234',
            'timestamp': '2024-01-20T10:30:00Z',
            'severity': 'ERROR',
            'user_message': 'エラーが発生しました。サポートにお問い合わせください。',
            'technical_details': {
                'stack_trace': 'File "api.py", line 123...',
                'context': {'file_size': 105000000}
            }
        })

        # エラーIDと詳細を検証
        result = await manager.verify_error_id_tracking()

        assert result.success is True
        assert result.error_id == 'ERR-2024-001234'
        assert result.has_timestamp is True
        assert result.severity == 'ERROR'
        assert result.has_user_friendly_message is True
        assert result.has_technical_details is True

    @pytest.mark.asyncio
    async def test_error_recovery_ui_elements(self):
        """エラー状態からのリカバリUI要素の検証"""
        manager, mock_wrapper = create_manager_with_mock()

        # リカバリUI要素の取得をモック
        mock_wrapper.get_recovery_options = AsyncMock(return_value={
            'success': True,
            'recovery_options': [
                {'action': 'retry', 'label': '再試行', 'enabled': True},
                {'action': 'upload_new', 'label': '新しいファイルをアップロード', 'enabled': True},
                {'action': 'cancel', 'label': 'キャンセル', 'enabled': True}
            ],
            'has_retry_button': True,
            'has_cancel_button': True
        })

        # リカバリオプションを検証
        result = await manager.verify_error_recovery_options()

        assert result.success is True
        assert len(result.recovery_options) == 3
        assert result.has_retry_option is True
        assert result.has_upload_new_option is True
        assert result.has_cancel_option is True

    @pytest.mark.asyncio
    async def test_error_recovery_action_execution(self):
        """エラーリカバリアクションの実行テスト"""
        manager, mock_wrapper = create_manager_with_mock()

        # リトライボタンのクリックをモック
        mock_wrapper.click_element = AsyncMock(return_value={
            'success': True,
            'element': 'retry-button',
            'clicked': True
        })

        # リトライ後の状態確認をモック
        mock_wrapper.wait_for_recovery = AsyncMock(return_value={
            'success': True,
            'recovery_status': 'success',
            'error_cleared': True,
            'processing_resumed': True
        })

        # エラーリカバリアクションを実行
        result = await manager.execute_error_recovery('retry')

        assert result.success is True
        assert result.recovery_attempted is True
        assert result.recovery_successful is True
        assert result.error_cleared is True
        assert result.processing_resumed is True


class TestDownloadAndErrorIntegration:
    """ダウンロードとエラー処理の統合テストクラス"""

    @pytest.mark.asyncio
    async def test_download_with_error_handling(self):
        """ダウンロード中のエラーハンドリング統合テスト"""
        manager, mock_wrapper = create_manager_with_mock()

        # ダウンロード開始（エラー発生）をモック
        mock_wrapper.click_element = AsyncMock(side_effect=[
            Exception("Network timeout during download")
        ])

        # エラー表示の確認をモック
        mock_wrapper.get_error_elements = AsyncMock(return_value={
            'success': True,
            'error_present': True,
            'error_message': 'ダウンロード中にタイムアウトが発生しました',
            'error_id': 'ERR-DL-TIMEOUT-001'
        })

        # エラー付きダウンロードを試行
        result = await manager.download_with_error_handling()

        assert result.success is False
        assert result.download_failed is True
        assert result.error_displayed is True
        assert result.error_id == 'ERR-DL-TIMEOUT-001'

    @pytest.mark.asyncio
    async def test_multiple_download_format_options(self):
        """複数のダウンロード形式オプションのテスト"""
        manager, mock_wrapper = create_manager_with_mock()

        # 利用可能なダウンロードオプションの取得をモック
        mock_wrapper.get_download_options = AsyncMock(return_value={
            'success': True,
            'formats': [
                {'format': 'csv', 'label': 'CSV形式', 'enabled': True},
                {'format': 'json', 'label': 'JSON形式', 'enabled': True},
                {'format': 'excel', 'label': 'Excel形式', 'enabled': False}
            ]
        })

        # ダウンロードオプションを検証
        result = await manager.verify_download_format_options()

        assert result.success is True
        assert len(result.available_formats) == 3
        assert result.csv_available is True
        assert result.json_available is True
        assert result.excel_available is False