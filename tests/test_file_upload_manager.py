"""Task 3.1: 単一ファイルアップロードテストの実装

TDD実装：ファイル選択処理の自動化、アップロード進捗監視、処理完了待機、成功確認ロジック
Requirements: 3.1, 3.3, 3.4 - ファイルアップロード機能、進捗監視、成功確認
"""

import pytest
import asyncio
import tempfile
import os
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock, AsyncMock


class TestFileUploadManagerBasics:
    """ファイルアップロード管理基本テストクラス"""

    def test_file_upload_manager_initialization(self):
        """FileUploadManagerが正しく初期化されること"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()
        assert manager is not None
        assert hasattr(manager, 'select_and_upload_file')
        assert hasattr(manager, 'monitor_upload_progress')
        assert hasattr(manager, 'wait_for_upload_completion')
        assert hasattr(manager, 'verify_upload_success')

    @pytest.mark.asyncio
    async def test_select_and_upload_file_success(self):
        """ファイル選択とアップロードが成功すること"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()

        # MCPTestExecutorをモック
        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            # ファイルアップロード処理をモック
            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.upload_file.return_value = {
                'success': True,
                'upload_id': 'upload_123',
                'filename': 'test.jsonl',
                'status': 'uploading'
            }

            # ファイル存在チェックとサイズチェックをモック
            with patch('src.file_upload_manager.os.path.exists', return_value=True), \
                 patch('src.file_upload_manager.os.path.getsize', return_value=1024):
                # テストファイルパス
                test_file_path = '/tmp/test_file.jsonl'

                result = await manager.select_and_upload_file(test_file_path)

                assert result['success'] is True
                assert result['upload_id'] == 'upload_123'
                assert result['filename'] == 'test.jsonl'
                assert result['status'] == 'uploading'

    @pytest.mark.asyncio
    async def test_select_and_upload_file_failure(self):
        """ファイルアップロード失敗時の処理が正しく動作すること"""
        from src.file_upload_manager import FileUploadManager, FileUploadError

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            # アップロード失敗をシミュレート
            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.upload_file.side_effect = Exception("Upload failed")

            # ファイル存在チェックとサイズチェックをモック
            with patch('src.file_upload_manager.os.path.exists', return_value=True), \
                 patch('src.file_upload_manager.os.path.getsize', return_value=1024):
                test_file_path = '/tmp/test_file.jsonl'

                with pytest.raises(FileUploadError) as exc_info:
                    await manager.select_and_upload_file(test_file_path)

                assert "Failed to upload file" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_monitor_upload_progress(self):
        """アップロード進捗監視が正しく動作すること"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()

            # 進捗情報の段階的変化をシミュレート
            progress_responses = [
                {'progress': 25, 'status': 'uploading', 'bytes_uploaded': 1024},
                {'progress': 50, 'status': 'uploading', 'bytes_uploaded': 2048},
                {'progress': 75, 'status': 'uploading', 'bytes_uploaded': 3072},
                {'progress': 100, 'status': 'uploaded', 'bytes_uploaded': 4096}
            ]

            mock_executor._mcp_wrapper.get_upload_progress.side_effect = progress_responses

            upload_id = 'upload_123'
            progress_history = []

            async for progress in manager.monitor_upload_progress(upload_id):
                progress_history.append(progress)
                if progress['progress'] >= 100:
                    break

            assert len(progress_history) == 4
            assert progress_history[0]['progress'] == 25
            assert progress_history[-1]['progress'] == 100
            assert progress_history[-1]['status'] == 'uploaded'

    @pytest.mark.asyncio
    async def test_wait_for_upload_completion_success(self):
        """アップロード完了待機が成功すること"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.get_upload_status.return_value = {
                'status': 'completed',
                'upload_id': 'upload_123',
                'result': {
                    'processed': True,
                    'comparison_result': {'overall_score': 0.85}
                }
            }

            upload_id = 'upload_123'
            result = await manager.wait_for_upload_completion(upload_id, timeout=10)

            assert result['status'] == 'completed'
            assert result['upload_id'] == 'upload_123'
            assert result['result']['processed'] is True
            assert 'comparison_result' in result['result']

    @pytest.mark.asyncio
    async def test_wait_for_upload_completion_timeout(self):
        """アップロード完了待機タイムアウト処理が正しく動作すること"""
        from src.file_upload_manager import FileUploadManager, UploadTimeoutError

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            # 処理中状態を維持してタイムアウトをシミュレート
            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.get_upload_status.return_value = {
                'status': 'processing',
                'upload_id': 'upload_123',
                'progress': 50
            }

            upload_id = 'upload_123'

            with pytest.raises(UploadTimeoutError) as exc_info:
                await manager.wait_for_upload_completion(upload_id, timeout=0.1)

            assert "Upload completion timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_upload_success(self):
        """アップロード成功確認が正しく動作すること"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'elements': [
                        {'type': 'text', 'text': 'Upload successful'},
                        {'type': 'result', 'id': 'comparison-result', 'text': 'Overall Score: 0.85'},
                        {'type': 'status', 'class': 'success-indicator', 'visible': True}
                    ]
                }
            }

            upload_id = 'upload_123'
            expected_indicators = [
                {'type': 'text', 'contains': 'successful'},
                {'type': 'result', 'id': 'comparison-result'},
                {'type': 'status', 'class': 'success-indicator'}
            ]

            result = await manager.verify_upload_success(upload_id, expected_indicators)

            assert result['success'] is True
            assert result['upload_id'] == 'upload_123'
            assert len(result['found_indicators']) == 3

    @pytest.mark.asyncio
    async def test_verify_upload_success_failure(self):
        """アップロード成功確認が失敗した場合の処理が正しく動作すること"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'elements': [
                        {'type': 'error', 'text': 'Upload failed'},
                        {'type': 'status', 'class': 'error-indicator', 'visible': True}
                    ]
                }
            }

            upload_id = 'upload_123'
            expected_indicators = [
                {'type': 'text', 'contains': 'successful'},
                {'type': 'result', 'id': 'comparison-result'},
                {'type': 'status', 'class': 'success-indicator'}
            ]

            result = await manager.verify_upload_success(upload_id, expected_indicators)

            assert result['success'] is False
            assert len(result['missing_indicators']) > 0

    @pytest.mark.asyncio
    async def test_file_validation(self):
        """ファイルバリデーションが正しく動作すること"""
        from src.file_upload_manager import FileUploadManager, FileValidationError

        manager = FileUploadManager()

        # 存在しないファイル
        with pytest.raises(FileValidationError) as exc_info:
            await manager.select_and_upload_file('/nonexistent/file.jsonl')

        assert "File not found" in str(exc_info.value)

        # 無効な拡張子（ファイルは存在するがフォーマットが無効）
        with patch('src.file_upload_manager.os.path.exists', return_value=True), \
             patch('src.file_upload_manager.os.path.getsize', return_value=1024):
            with pytest.raises(FileValidationError) as exc_info:
                await manager.select_and_upload_file('/tmp/test.txt')

            assert "Invalid file format" in str(exc_info.value)


class TestFileUploadManagerIntegration:
    """ファイルアップロード管理統合テスト"""

    @pytest.mark.asyncio
    async def test_full_upload_workflow(self):
        """完全なアップロードワークフローのテスト"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()

            # 1. ファイルアップロード開始
            mock_executor._mcp_wrapper.upload_file.return_value = {
                'success': True,
                'upload_id': 'upload_123',
                'filename': 'test.jsonl',
                'status': 'uploading'
            }

            # 2. 進捗監視（段階的に更新）
            progress_responses = [
                {'progress': 50, 'status': 'uploading'},
                {'progress': 100, 'status': 'uploaded'}
            ]
            mock_executor._mcp_wrapper.get_upload_progress.side_effect = progress_responses

            # 3. 完了待機
            mock_executor._mcp_wrapper.get_upload_status.return_value = {
                'status': 'completed',
                'upload_id': 'upload_123',
                'result': {'processed': True, 'comparison_result': {'overall_score': 0.85}}
            }

            # 4. 成功確認
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'elements': [
                        {'type': 'text', 'text': 'Upload successful'},
                        {'type': 'result', 'id': 'comparison-result', 'text': 'Overall Score: 0.85'}
                    ]
                }
            }

            try:
                # フルワークフロー実行
                test_file_path = '/tmp/test.jsonl'

                # ファイル存在チェックとサイズチェックをモック
                with patch('src.file_upload_manager.os.path.exists', return_value=True), \
                     patch('src.file_upload_manager.os.path.getsize', return_value=1024):
                    # 1. アップロード開始
                    upload_result = await manager.select_and_upload_file(test_file_path)
                    assert upload_result['success'] is True
                    upload_id = upload_result['upload_id']

                # 2. 進捗監視
                progress_count = 0
                async for progress in manager.monitor_upload_progress(upload_id):
                    progress_count += 1
                    if progress['progress'] >= 100:
                        break

                assert progress_count > 0

                # 3. 完了待機
                completion_result = await manager.wait_for_upload_completion(upload_id, timeout=10)
                assert completion_result['status'] == 'completed'

                # 4. 成功確認
                success_indicators = [
                    {'type': 'text', 'contains': 'successful'},
                    {'type': 'result', 'id': 'comparison-result'}
                ]
                verification_result = await manager.verify_upload_success(upload_id, success_indicators)
                assert verification_result['success'] is True

            except Exception as e:
                pytest.fail(f"Full upload workflow failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_concurrent_upload_operations(self):
        """並行アップロード操作の安全性テスト"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.get_upload_status.return_value = {
                'status': 'completed',
                'upload_id': 'upload_test',
                'result': {'processed': True}
            }

            # 複数の並行操作
            upload_ids = ['upload_1', 'upload_2', 'upload_3']
            tasks = [
                manager.wait_for_upload_completion(upload_id, timeout=5)
                for upload_id in upload_ids
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 全ての操作が正常完了することを確認
            for result in results:
                assert not isinstance(result, Exception), f"Concurrent operation failed: {result}"
                assert result['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_large_file_upload_simulation(self):
        """大容量ファイルアップロードのシミュレーションテスト"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()

            # 大容量ファイルの段階的アップロード進捗をシミュレート
            large_file_progress = [
                {'progress': 10, 'status': 'uploading', 'bytes_uploaded': 10 * 1024 * 1024},
                {'progress': 25, 'status': 'uploading', 'bytes_uploaded': 25 * 1024 * 1024},
                {'progress': 50, 'status': 'uploading', 'bytes_uploaded': 50 * 1024 * 1024},
                {'progress': 75, 'status': 'uploading', 'bytes_uploaded': 75 * 1024 * 1024},
                {'progress': 90, 'status': 'uploading', 'bytes_uploaded': 90 * 1024 * 1024},
                {'progress': 100, 'status': 'uploaded', 'bytes_uploaded': 100 * 1024 * 1024}
            ]

            mock_executor._mcp_wrapper.get_upload_progress.side_effect = large_file_progress

            upload_id = 'large_upload_123'
            progress_updates = []

            async for progress in manager.monitor_upload_progress(upload_id):
                progress_updates.append(progress)
                if progress['progress'] >= 100:
                    break

            # 全ての進捗更新が記録されていることを確認
            assert len(progress_updates) == 6
            assert progress_updates[0]['progress'] == 10
            assert progress_updates[-1]['progress'] == 100
            assert progress_updates[-1]['bytes_uploaded'] == 100 * 1024 * 1024

    def test_file_upload_manager_configuration(self):
        """FileUploadManager設定のテスト"""
        from src.file_upload_manager import FileUploadManager

        # デフォルト設定
        manager1 = FileUploadManager()
        assert manager1 is not None

        # カスタム設定
        manager2 = FileUploadManager(
            default_timeout=60,
            progress_interval=1.0
        )
        assert manager2 is not None


class TestFileUploadManagerMultipleFiles:
    """Task 3.2: 複数ファイルおよびエラー処理テストの実装

    TDD実装：2ファイル比較モード、無効ファイル形式エラー検証、ファイルサイズ制限エラー、エラーメッセージ表示確認
    Requirements: 3.2, 3.4, 3.5 - 複数ファイル処理、エラーハンドリング、メッセージ表示
    """

    @pytest.mark.asyncio
    async def test_upload_two_files_for_comparison(self):
        """2ファイル比較モードのアップロードテストが正しく動作すること"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.upload_two_files.return_value = {
                'success': True,
                'upload_id': 'dual_upload_123',
                'file1': {'filename': 'file1.jsonl', 'status': 'uploaded'},
                'file2': {'filename': 'file2.jsonl', 'status': 'uploaded'},
                'comparison_mode': 'dual_file',
                'status': 'ready_for_comparison'
            }

            # ファイル存在チェックとサイズチェックをモック
            with patch('src.file_upload_manager.os.path.exists', return_value=True), \
                 patch('src.file_upload_manager.os.path.getsize', return_value=1024):
                file1_path = '/tmp/file1.jsonl'
                file2_path = '/tmp/file2.jsonl'

                result = await manager.upload_two_files_for_comparison(file1_path, file2_path)

                assert result['success'] is True
                assert result['upload_id'] == 'dual_upload_123'
                assert result['comparison_mode'] == 'dual_file'
                assert result['file1']['filename'] == 'file1.jsonl'
                assert result['file2']['filename'] == 'file2.jsonl'
                assert result['status'] == 'ready_for_comparison'

    @pytest.mark.asyncio
    async def test_upload_two_files_validation_failure(self):
        """2ファイル比較モードでファイルバリデーション失敗時の処理が正しく動作すること"""
        from src.file_upload_manager import FileUploadManager, FileValidationError

        manager = FileUploadManager()

        # 1つ目のファイルが存在しない場合
        with pytest.raises(FileValidationError) as exc_info:
            await manager.upload_two_files_for_comparison('/nonexistent1.jsonl', '/nonexistent2.jsonl')

        assert "First file not found" in str(exc_info.value)

        # 2つ目のファイルが存在しない場合
        with patch('src.file_upload_manager.os.path.exists') as mock_exists, \
             patch('src.file_upload_manager.os.path.getsize', return_value=1024):
            mock_exists.side_effect = lambda path: path == '/tmp/file1.jsonl'

            with pytest.raises(FileValidationError) as exc_info:
                await manager.upload_two_files_for_comparison('/tmp/file1.jsonl', '/tmp/file2.jsonl')

            assert "Second file not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_file_format_error_verification(self):
        """無効ファイル形式のエラー検証が正しく動作すること"""
        from src.file_upload_manager import FileUploadManager, FileValidationError

        manager = FileUploadManager()

        # サポートされていない拡張子のテスト
        invalid_formats = [
            '/tmp/test.txt',
            '/tmp/test.pdf',
            '/tmp/test.csv',
            '/tmp/test.xlsx',
            '/tmp/test.doc'
        ]

        for invalid_file in invalid_formats:
            with patch('src.file_upload_manager.os.path.exists', return_value=True), \
                 patch('src.file_upload_manager.os.path.getsize', return_value=1024):
                with pytest.raises(FileValidationError) as exc_info:
                    await manager.validate_file_format(invalid_file)

                assert "Invalid file format" in str(exc_info.value)
                assert invalid_file.split('.')[-1] in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_file_size_limit_error_validation(self):
        """ファイルサイズ制限エラーテストが正しく動作すること"""
        from src.file_upload_manager import FileUploadManager, FileValidationError

        manager = FileUploadManager()

        # 最大サイズを超過するファイル
        oversized_file = '/tmp/oversized.jsonl'
        max_size = 100 * 1024 * 1024  # 100MB
        oversized_size = max_size + 1

        with patch('src.file_upload_manager.os.path.exists', return_value=True), \
             patch('src.file_upload_manager.os.path.getsize', return_value=oversized_size):
            with pytest.raises(FileValidationError) as exc_info:
                await manager.validate_file_size(oversized_file, max_size)

            assert "File size exceeds limit" in str(exc_info.value)
            assert f"{oversized_size} bytes" in str(exc_info.value)
            assert f"{max_size} bytes" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_message_display_verification(self):
        """エラーメッセージ表示確認処理が正しく動作すること"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'elements': [
                        {
                            'type': 'error',
                            'class': 'error-message',
                            'text': 'File size exceeds 100MB limit',
                            'visible': True
                        },
                        {
                            'type': 'error',
                            'id': 'error-details',
                            'text': 'Error ID: ERR_FILE_SIZE_001',
                            'visible': True
                        },
                        {
                            'type': 'button',
                            'class': 'retry-button',
                            'text': 'Try Again',
                            'enabled': True
                        }
                    ]
                }
            }

            expected_error_indicators = [
                {'type': 'error', 'class': 'error-message'},
                {'type': 'error', 'id': 'error-details'},
                {'type': 'button', 'class': 'retry-button'}
            ]

            result = await manager.verify_error_message_display(expected_error_indicators)

            assert result['success'] is True
            assert len(result['found_error_indicators']) == 3
            assert 'File size exceeds 100MB limit' in result['error_messages'][0]
            assert 'ERR_FILE_SIZE_001' in result['error_details'][0]

    @pytest.mark.asyncio
    async def test_error_message_display_missing_indicators(self):
        """エラーメッセージ表示確認で必要な要素が見つからない場合の処理が正しく動作すること"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'elements': [
                        {
                            'type': 'info',
                            'text': 'Some unrelated message',
                            'visible': True
                        }
                    ]
                }
            }

            expected_error_indicators = [
                {'type': 'error', 'class': 'error-message'},
                {'type': 'error', 'id': 'error-details'}
            ]

            result = await manager.verify_error_message_display(expected_error_indicators)

            assert result['success'] is False
            assert len(result['missing_error_indicators']) == 2
            assert len(result['found_error_indicators']) == 0

    @pytest.mark.asyncio
    async def test_multiple_error_types_handling(self):
        """複数のエラータイプの処理が正しく動作すること"""
        from src.file_upload_manager import FileUploadManager, FileValidationError, UploadTimeoutError

        manager = FileUploadManager()

        # ファイル形式エラー
        with patch('src.file_upload_manager.os.path.exists', return_value=True), \
             patch('src.file_upload_manager.os.path.getsize', return_value=1024):
            with pytest.raises(FileValidationError) as exc_info:
                await manager.handle_upload_error('invalid_format', '/tmp/test.txt')

            assert "Invalid file format" in str(exc_info.value)

        # ファイルサイズエラー
        with patch('src.file_upload_manager.os.path.exists', return_value=True), \
             patch('src.file_upload_manager.os.path.getsize', return_value=200 * 1024 * 1024):
            with pytest.raises(FileValidationError) as exc_info:
                await manager.handle_upload_error('size_limit', '/tmp/large.jsonl')

            assert "File size exceeds limit" in str(exc_info.value)

        # タイムアウトエラー
        with pytest.raises(UploadTimeoutError) as exc_info:
            await manager.handle_upload_error('timeout', 'upload_123')

        assert "Upload timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """エラー発生からリカバリまでのワークフローテスト"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()

            # エラー状態のシミュレート
            error_snapshot = {
                'success': True,
                'snapshot': {
                    'elements': [
                        {'type': 'error', 'class': 'error-message', 'text': 'Upload failed'},
                        {'type': 'button', 'class': 'retry-button', 'enabled': True}
                    ]
                }
            }

            # リカバリ後の成功状態
            success_snapshot = {
                'success': True,
                'snapshot': {
                    'elements': [
                        {'type': 'text', 'text': 'Upload successful'},
                        {'type': 'result', 'id': 'comparison-result', 'text': 'Overall Score: 0.85'}
                    ]
                }
            }

            mock_executor._mcp_wrapper.take_snapshot.side_effect = [error_snapshot, success_snapshot]
            mock_executor._mcp_wrapper.click_element.return_value = {'success': True}
            mock_executor._mcp_wrapper.upload_file.return_value = {
                'success': True,
                'upload_id': 'retry_upload_123',
                'status': 'uploading'
            }

            # エラーリカバリワークフロー実行
            error_indicators = [{'type': 'error', 'class': 'error-message'}]
            retry_button = {'type': 'button', 'class': 'retry-button'}

            # 1. エラー状態確認
            error_result = await manager.verify_error_message_display(error_indicators)
            assert error_result['success'] is True

            # 2. リトライボタンクリック（リカバリ操作）
            recovery_result = await manager.perform_error_recovery(retry_button)
            assert recovery_result['success'] is True

            # 3. リカバリ後の成功確認
            success_indicators = [{'type': 'text', 'contains': 'successful'}]
            final_result = await manager.verify_recovery_success(success_indicators)
            assert final_result['success'] is True

    @pytest.mark.asyncio
    async def test_dual_file_upload_with_different_sizes(self):
        """異なるサイズの2ファイルアップロードテスト"""
        from src.file_upload_manager import FileUploadManager

        manager = FileUploadManager()

        with patch('src.file_upload_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.upload_two_files.return_value = {
                'success': True,
                'upload_id': 'dual_upload_456',
                'file1': {'filename': 'small.jsonl', 'size': 1024, 'status': 'uploaded'},
                'file2': {'filename': 'large.jsonl', 'size': 50 * 1024 * 1024, 'status': 'uploaded'},
                'comparison_mode': 'dual_file',
                'status': 'ready_for_comparison'
            }

            # 異なるサイズのファイルをモック
            def mock_getsize(path):
                if 'small' in path:
                    return 1024
                elif 'large' in path:
                    return 50 * 1024 * 1024
                return 1024

            with patch('src.file_upload_manager.os.path.exists', return_value=True), \
                 patch('src.file_upload_manager.os.path.getsize', side_effect=mock_getsize):
                small_file = '/tmp/small.jsonl'
                large_file = '/tmp/large.jsonl'

                result = await manager.upload_two_files_for_comparison(small_file, large_file)

                assert result['success'] is True
                assert result['file1']['size'] == 1024
                assert result['file2']['size'] == 50 * 1024 * 1024