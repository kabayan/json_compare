"""コンソールとネットワーク監視テストケース

Task 7の要件に対応：
Task 7.1: コンソールメッセージ監視テストの実装
- JavaScript エラー検出処理の実装
- 警告メッセージ収集機能の実装
- コンソールログ記録とレポート生成の実装
- エラー発生時のテスト失敗処理の実装
Requirements: 7.1, 7.2

Task 7.2: ネットワーク通信監視テストの実装
- API リクエスト記録機能の実装
- HTTP ステータスコード検証の実装
- レスポンスタイム測定処理の実装
- 予期しないダイアログ処理テストの作成
Requirements: 7.3, 7.4, 7.5
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime


def create_monitor_with_mock():
    """モックされたラッパー付きのモニターを作成するヘルパー関数"""
    from src.console_network_monitor import ConsoleNetworkMonitor

    mock_wrapper = AsyncMock()
    mock_wrapper.is_initialized = False
    mock_wrapper.initialize = AsyncMock(return_value=None)

    monitor = ConsoleNetworkMonitor()
    monitor.executor._mcp_wrapper = mock_wrapper

    return monitor, mock_wrapper


class TestConsoleMessageMonitoring:
    """コンソールメッセージ監視テストクラス"""

    @pytest.mark.asyncio
    async def test_javascript_error_detection(self):
        """JavaScriptエラーの検出が正しく動作すること"""
        monitor, mock_wrapper = create_monitor_with_mock()

        # コンソールメッセージ取得をモック
        mock_wrapper.get_console_messages = AsyncMock(return_value={
            'success': True,
            'messages': [
                {
                    'type': 'error',
                    'text': 'Uncaught TypeError: Cannot read property of undefined',
                    'timestamp': '2024-01-20T10:00:00Z',
                    'source': 'app.js:123'
                },
                {
                    'type': 'log',
                    'text': 'Application started',
                    'timestamp': '2024-01-20T10:00:01Z'
                }
            ]
        })

        # エラー検出を実行
        result = await monitor.detect_javascript_errors()

        assert result.success is True
        assert result.errors_detected is True
        assert len(result.error_messages) == 1
        assert 'TypeError' in result.error_messages[0]['text']
        assert result.error_messages[0]['source'] == 'app.js:123'

    @pytest.mark.asyncio
    async def test_warning_message_collection(self):
        """警告メッセージの収集が正しく動作すること"""
        monitor, mock_wrapper = create_monitor_with_mock()

        # 警告メッセージを含むコンソール出力をモック
        mock_wrapper.get_console_messages = AsyncMock(return_value={
            'success': True,
            'messages': [
                {
                    'type': 'warning',
                    'text': 'Deprecation warning: Function will be removed in v2.0',
                    'timestamp': '2024-01-20T10:00:00Z'
                },
                {
                    'type': 'warning',
                    'text': 'Performance warning: Large dataset detected',
                    'timestamp': '2024-01-20T10:00:02Z'
                },
                {
                    'type': 'info',
                    'text': 'Info message',
                    'timestamp': '2024-01-20T10:00:03Z'
                }
            ]
        })

        # 警告メッセージを収集
        result = await monitor.collect_warning_messages()

        assert result.success is True
        assert result.warnings_found is True
        assert len(result.warning_messages) == 2
        assert 'Deprecation' in result.warning_messages[0]['text']
        assert result.warning_count == 2

    @pytest.mark.asyncio
    async def test_console_log_recording(self):
        """コンソールログの記録が正しく動作すること"""
        monitor, mock_wrapper = create_monitor_with_mock()

        # ログ記録開始をモック
        mock_wrapper.start_console_recording = AsyncMock(return_value={
            'success': True,
            'recording_id': 'rec_456',
            'recording_started': True
        })

        # ログ取得をモック
        mock_wrapper.get_recorded_logs = AsyncMock(return_value={
            'success': True,
            'logs': [
                {'type': 'log', 'text': 'Process started', 'timestamp': '10:00:00'},
                {'type': 'error', 'text': 'Error occurred', 'timestamp': '10:00:05'},
                {'type': 'warning', 'text': 'Warning message', 'timestamp': '10:00:10'}
            ],
            'total_count': 3
        })

        # ログ記録を開始
        start_result = await monitor.start_console_recording()
        assert start_result.success is True
        assert start_result.recording_active is True

        # ログを取得
        logs_result = await monitor.get_console_logs('rec_456')
        assert logs_result.success is True
        assert logs_result.log_count == 3
        assert logs_result.has_errors is True
        assert logs_result.has_warnings is True

    @pytest.mark.asyncio
    async def test_console_report_generation(self):
        """コンソールレポートの生成が正しく動作すること"""
        monitor, mock_wrapper = create_monitor_with_mock()

        # レポート生成をモック
        mock_wrapper.generate_console_report = AsyncMock(return_value={
            'success': True,
            'report': {
                'summary': {
                    'total_messages': 50,
                    'errors': 5,
                    'warnings': 10,
                    'logs': 35
                },
                'critical_errors': [
                    'Uncaught Error at line 123',
                    'Network request failed'
                ],
                'report_path': '/tmp/reports/console_report.html'
            }
        })

        # レポートを生成
        result = await monitor.generate_console_report()

        assert result.success is True
        assert result.report_generated is True
        assert result.total_messages == 50
        assert result.error_count == 5
        assert result.warning_count == 10
        assert len(result.critical_errors) == 2
        assert result.report_path.endswith('.html')

    @pytest.mark.asyncio
    async def test_error_triggered_test_failure(self):
        """エラー発生時にテストが失敗すること"""
        monitor, mock_wrapper = create_monitor_with_mock()

        # エラーメッセージを含むコンソール出力をモック
        mock_wrapper.get_console_messages = AsyncMock(return_value={
            'success': True,
            'messages': [
                {
                    'type': 'error',
                    'text': 'Critical error: Application crashed',
                    'timestamp': '2024-01-20T10:00:00Z'
                }
            ]
        })

        # エラー時のテスト失敗設定をモック
        mock_wrapper.set_fail_on_error = AsyncMock(return_value={
            'success': True,
            'fail_on_error_enabled': True
        })

        # エラー検証を実行（テスト失敗を期待）
        result = await monitor.verify_no_console_errors()

        assert result.success is False
        assert result.test_failed is True
        assert result.failure_reason == 'Console errors detected'
        assert len(result.detected_errors) == 1


class TestNetworkCommunicationMonitoring:
    """ネットワーク通信監視テストクラス"""

    @pytest.mark.asyncio
    async def test_api_request_recording(self):
        """APIリクエストの記録が正しく動作すること"""
        monitor, mock_wrapper = create_monitor_with_mock()

        # ネットワークリクエスト記録をモック
        mock_wrapper.get_network_requests = AsyncMock(return_value={
            'success': True,
            'requests': [
                {
                    'url': 'http://localhost:18081/api/compare',
                    'method': 'POST',
                    'status': 200,
                    'duration': 1.2,
                    'timestamp': '2024-01-20T10:00:00Z'
                },
                {
                    'url': 'http://localhost:18081/api/download',
                    'method': 'GET',
                    'status': 404,
                    'duration': 0.3,
                    'timestamp': '2024-01-20T10:00:05Z'
                }
            ]
        })

        # APIリクエストを記録
        result = await monitor.record_api_requests()

        assert result.success is True
        assert len(result.requests) == 2
        assert result.requests[0]['method'] == 'POST'
        assert result.requests[0]['status'] == 200
        assert result.requests[1]['status'] == 404
        assert result.has_failed_requests is True

    @pytest.mark.asyncio
    async def test_http_status_code_validation(self):
        """HTTPステータスコードの検証が正しく動作すること"""
        monitor, mock_wrapper = create_monitor_with_mock()

        # ネットワークレスポンスをモック
        mock_wrapper.get_network_responses = AsyncMock(return_value={
            'success': True,
            'responses': [
                {'url': '/api/compare', 'status': 200},
                {'url': '/api/upload', 'status': 201},
                {'url': '/api/delete', 'status': 404},
                {'url': '/api/process', 'status': 500}
            ]
        })

        # ステータスコードを検証
        result = await monitor.validate_http_status_codes()

        assert result.success is True
        assert result.success_count == 2  # 200, 201
        assert result.client_error_count == 1  # 404
        assert result.server_error_count == 1  # 500
        assert result.has_errors is True
        assert len(result.error_responses) == 2

    @pytest.mark.asyncio
    async def test_response_time_measurement(self):
        """レスポンスタイムの測定が正しく動作すること"""
        monitor, mock_wrapper = create_monitor_with_mock()

        # レスポンスタイム測定をモック
        mock_wrapper.measure_response_times = AsyncMock(return_value={
            'success': True,
            'measurements': [
                {'endpoint': '/api/compare', 'time': 0.5},
                {'endpoint': '/api/upload', 'time': 2.3},
                {'endpoint': '/api/process', 'time': 5.1},
                {'endpoint': '/api/status', 'time': 0.1}
            ],
            'average_time': 2.0,
            'max_time': 5.1,
            'min_time': 0.1
        })

        # レスポンスタイムを測定
        result = await monitor.measure_api_response_times()

        assert result.success is True
        assert len(result.measurements) == 4
        assert result.average_response_time == 2.0
        assert result.max_response_time == 5.1
        assert result.min_response_time == 0.1
        assert result.slow_requests_count == 2  # > 2秒のリクエスト

    @pytest.mark.asyncio
    async def test_unexpected_dialog_handling(self):
        """予期しないダイアログの処理が正しく動作すること"""
        monitor, mock_wrapper = create_monitor_with_mock()

        # ダイアログ検出をモック
        mock_wrapper.detect_dialog = AsyncMock(return_value={
            'success': True,
            'dialog_present': True,
            'dialog_type': 'alert',
            'dialog_text': 'Unexpected error occurred'
        })

        # ダイアログ処理をモック
        mock_wrapper.handle_dialog = AsyncMock(return_value={
            'success': True,
            'dialog_handled': True,
            'action': 'dismissed'
        })

        # ダイアログを検出して処理
        detect_result = await monitor.detect_unexpected_dialog()
        assert detect_result.success is True
        assert detect_result.dialog_detected is True
        assert detect_result.dialog_type == 'alert'

        handle_result = await monitor.handle_dialog('dismiss')
        assert handle_result.success is True
        assert handle_result.dialog_handled is True

    @pytest.mark.asyncio
    async def test_network_error_recovery(self):
        """ネットワークエラーからの回復テスト"""
        monitor, mock_wrapper = create_monitor_with_mock()

        # ネットワークエラーをモック
        mock_wrapper.detect_network_errors = AsyncMock(return_value={
            'success': True,
            'errors_detected': True,
            'error_types': ['timeout', 'connection_refused']
        })

        # リトライ機能をモック
        mock_wrapper.retry_failed_requests = AsyncMock(return_value={
            'success': True,
            'retry_count': 3,
            'successful_retries': 2,
            'failed_retries': 1
        })

        # エラー検出とリトライ
        error_result = await monitor.detect_network_errors()
        assert error_result.success is True
        assert error_result.has_errors is True

        retry_result = await monitor.retry_failed_network_requests()
        assert retry_result.success is True
        assert retry_result.retry_success_rate == 2/3


class TestMonitoringIntegration:
    """監視機能統合テストクラス"""

    @pytest.mark.asyncio
    async def test_full_monitoring_workflow(self):
        """完全な監視ワークフローのテスト"""
        monitor, mock_wrapper = create_monitor_with_mock()

        # 監視開始をモック
        mock_wrapper.start_monitoring = AsyncMock(return_value={
            'success': True,
            'console_monitoring': True,
            'network_monitoring': True,
            'session_id': 'mon_789'
        })

        # 監視データ収集をモック
        mock_wrapper.collect_monitoring_data = AsyncMock(return_value={
            'success': True,
            'console_data': {'errors': 2, 'warnings': 5},
            'network_data': {'requests': 20, 'failures': 1}
        })

        # 監視レポート生成をモック
        mock_wrapper.generate_monitoring_report = AsyncMock(return_value={
            'success': True,
            'report_generated': True,
            'report_path': '/tmp/monitoring_report.html'
        })

        # 完全なワークフローを実行
        start_result = await monitor.start_full_monitoring()
        assert start_result.success is True
        assert start_result.monitoring_active is True

        data_result = await monitor.collect_all_data('mon_789')
        assert data_result.success is True
        assert data_result.console_errors == 2
        assert data_result.network_failures == 1

        report_result = await monitor.generate_final_report('mon_789')
        assert report_result.success is True
        assert report_result.report_created is True