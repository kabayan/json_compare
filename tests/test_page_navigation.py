"""Task 2.1: ページナビゲーション基本テストの作成

TDD実装：WebUI初期アクセス、ページ読み込み完了確認、エラーページ検出、ページ構造検証
Requirements: 2.1, 2.2, 2.3, 2.4 - ナビゲーション基本機能、ページ検証、エラー検出
"""

import pytest
import asyncio
import time
from typing import Dict, Any, Optional, List
from unittest.mock import patch, MagicMock, AsyncMock


class TestPageNavigationBasics:
    """ページナビゲーション基本テストクラス"""

    def test_page_navigator_initialization(self):
        """PageNavigatorが正しく初期化されること"""
        from src.page_navigator import PageNavigator

        navigator = PageNavigator()
        assert navigator is not None
        assert hasattr(navigator, 'navigate_to_webui')
        assert hasattr(navigator, 'wait_for_page_load')
        assert hasattr(navigator, 'detect_error_page')
        assert hasattr(navigator, 'validate_page_structure')

    @pytest.mark.asyncio
    async def test_navigate_to_webui_success(self):
        """WebUIへの初期アクセスが成功すること"""
        from src.page_navigator import PageNavigator

        navigator = PageNavigator()

        # MCPTestExecutorをモック
        with patch('src.page_navigator.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            # MCPラッパーのnavigateメソッドをモック
            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.navigate.return_value = {
                'success': True,
                'url': 'http://localhost:18081/ui',
                'status': 200
            }

            result = await navigator.navigate_to_webui('http://localhost:18081/ui')

            assert result['success'] is True
            assert result['url'] == 'http://localhost:18081/ui'
            assert result['status'] == 200

    @pytest.mark.asyncio
    async def test_navigate_to_webui_failure(self):
        """WebUIアクセス失敗時の処理が正しく動作すること"""
        from src.page_navigator import PageNavigator, NavigationError

        navigator = PageNavigator()

        with patch('src.page_navigator.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            # ナビゲーション失敗をシミュレート
            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.navigate.side_effect = Exception("Connection failed")

            with pytest.raises(NavigationError) as exc_info:
                await navigator.navigate_to_webui('http://localhost:18081/ui')

            assert "Failed to navigate to WebUI" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_wait_for_page_load_complete(self):
        """ページ読み込み完了確認が正しく動作すること"""
        from src.page_navigator import PageNavigator

        navigator = PageNavigator()

        with patch('src.page_navigator.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            # ページスナップショットをモック
            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'title': 'JSON Compare WebUI',
                    'ready_state': 'complete',
                    'elements': [
                        {'type': 'heading', 'text': 'JSON Compare'},
                        {'type': 'form', 'id': 'upload-form'}
                    ]
                }
            }

            result = await navigator.wait_for_page_load(timeout=10)

            assert result['loaded'] is True
            assert result['title'] == 'JSON Compare WebUI'
            assert result['ready_state'] == 'complete'

    @pytest.mark.asyncio
    async def test_wait_for_page_load_timeout(self):
        """ページ読み込みタイムアウト処理が正しく動作すること"""
        from src.page_navigator import PageNavigator, PageLoadTimeoutError

        navigator = PageNavigator()

        with patch('src.page_navigator.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            # 読み込み未完了状態をシミュレート
            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'title': '',
                    'ready_state': 'loading',
                    'elements': []
                }
            }

            with pytest.raises(PageLoadTimeoutError) as exc_info:
                await navigator.wait_for_page_load(timeout=0.1)

            assert "Page load timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_detect_error_page_no_error(self):
        """正常ページでエラー検出が行われないこと"""
        from src.page_navigator import PageNavigator

        navigator = PageNavigator()

        with patch('src.page_navigator.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'title': 'JSON Compare WebUI',
                    'elements': [
                        {'type': 'heading', 'text': 'JSON Compare'},
                        {'type': 'form', 'id': 'upload-form'}
                    ]
                }
            }

            result = await navigator.detect_error_page()

            assert result.has_error is False
            assert result.error_type is None
            assert result.error_message is None

    @pytest.mark.asyncio
    async def test_detect_error_page_404_error(self):
        """404エラーページが正しく検出されること"""
        from src.page_navigator import PageNavigator

        navigator = PageNavigator()

        with patch('src.page_navigator.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'title': '404 Not Found',
                    'elements': [
                        {'type': 'heading', 'text': '404'},
                        {'type': 'text', 'text': 'Page not found'}
                    ]
                }
            }

            result = await navigator.detect_error_page()

            assert result.has_error is True
            assert result.error_type == '404'
            assert 'not found' in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_detect_error_page_500_error(self):
        """500エラーページが正しく検出されること"""
        from src.page_navigator import PageNavigator

        navigator = PageNavigator()

        with patch('src.page_navigator.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'title': 'Internal Server Error',
                    'elements': [
                        {'type': 'heading', 'text': '500'},
                        {'type': 'text', 'text': 'Internal server error occurred'}
                    ]
                }
            }

            result = await navigator.detect_error_page()

            assert result.has_error is True
            assert result.error_type == '500'
            assert 'server error' in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_validate_page_structure_success(self):
        """ページ構造検証が成功すること"""
        from src.page_navigator import PageNavigator

        navigator = PageNavigator()

        with patch('src.page_navigator.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'title': 'JSON Compare WebUI',
                    'elements': [
                        {'type': 'heading', 'text': 'JSON Compare', 'level': 1},
                        {'type': 'form', 'id': 'upload-form'},
                        {'type': 'button', 'text': 'Upload File', 'id': 'upload-btn'},
                        {'type': 'input', 'input_type': 'file', 'id': 'file-input'}
                    ]
                }
            }

            expected_elements = [
                {'type': 'heading', 'level': 1},
                {'type': 'form', 'id': 'upload-form'},
                {'type': 'button', 'id': 'upload-btn'},
                {'type': 'input', 'input_type': 'file'}
            ]

            result = await navigator.validate_page_structure(expected_elements)

            assert result.valid is True
            assert result.missing_elements == []
            assert result.found_elements == 4

    @pytest.mark.asyncio
    async def test_validate_page_structure_missing_elements(self):
        """必要な要素が不足している場合の検証が正しく動作すること"""
        from src.page_navigator import PageNavigator

        navigator = PageNavigator()

        with patch('src.page_navigator.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'title': 'JSON Compare WebUI',
                    'elements': [
                        {'type': 'heading', 'text': 'JSON Compare', 'level': 1},
                        # フォームとボタンが不足
                    ]
                }
            }

            expected_elements = [
                {'type': 'heading', 'level': 1},
                {'type': 'form', 'id': 'upload-form'},
                {'type': 'button', 'id': 'upload-btn'},
                {'type': 'input', 'input_type': 'file'}
            ]

            result = await navigator.validate_page_structure(expected_elements)

            assert result.valid is False
            assert len(result.missing_elements) == 3  # form, button, input が不足
            assert result.found_elements == 1


class TestPageNavigationIntegration:
    """ページナビゲーション統合テスト"""

    @pytest.mark.asyncio
    async def test_full_navigation_workflow(self):
        """完全なナビゲーションワークフローのテスト"""
        from src.page_navigator import PageNavigator

        navigator = PageNavigator()

        with patch('src.page_navigator.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()

            # 1. ナビゲーション成功
            mock_executor._mcp_wrapper.navigate.return_value = {
                'success': True,
                'url': 'http://localhost:18081/ui',
                'status': 200
            }

            # 2. ページ読み込み完了
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'title': 'JSON Compare WebUI',
                    'ready_state': 'complete',
                    'elements': [
                        {'type': 'heading', 'text': 'JSON Compare', 'level': 1},
                        {'type': 'form', 'id': 'upload-form'},
                        {'type': 'button', 'text': 'Upload File', 'id': 'upload-btn'}
                    ]
                }
            }

            try:
                # フルワークフロー実行
                nav_result = await navigator.navigate_to_webui('http://localhost:18081/ui')
                assert nav_result['success'] is True

                load_result = await navigator.wait_for_page_load(timeout=10)
                assert load_result['loaded'] is True

                error_result = await navigator.detect_error_page()
                assert error_result.has_error is False

                structure_result = await navigator.validate_page_structure([
                    {'type': 'heading', 'level': 1},
                    {'type': 'form', 'id': 'upload-form'}
                ])
                assert structure_result.valid is True

            except Exception as e:
                pytest.fail(f"Full workflow failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """エラー発生時のリカバリワークフローのテスト"""
        from src.page_navigator import PageNavigator, NavigationError

        navigator = PageNavigator()

        with patch('src.page_navigator.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()

            # 初回ナビゲーション失敗
            mock_executor._mcp_wrapper.navigate.side_effect = [
                Exception("Connection timeout"),
                {'success': True, 'url': 'http://localhost:18081/ui', 'status': 200}
            ]

            # リトライ機能のテスト
            try:
                # 初回失敗
                with pytest.raises(NavigationError):
                    await navigator.navigate_to_webui('http://localhost:18081/ui')

                # 2回目成功
                result = await navigator.navigate_to_webui('http://localhost:18081/ui')
                assert result['success'] is True

            except Exception as e:
                pytest.fail(f"Error recovery workflow failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_concurrent_navigation_operations(self):
        """並行ナビゲーション操作の安全性テスト"""
        from src.page_navigator import PageNavigator

        navigator = PageNavigator()

        with patch('src.page_navigator.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'title': 'JSON Compare WebUI',
                    'ready_state': 'complete',
                    'elements': []
                }
            }

            # 複数の並行操作
            tasks = [
                navigator.wait_for_page_load(timeout=5),
                navigator.detect_error_page(),
                navigator.validate_page_structure([])
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 全ての操作が正常完了することを確認
            for result in results:
                assert not isinstance(result, Exception), f"Concurrent operation failed: {result}"

    def test_page_navigator_configuration(self):
        """PageNavigator設定のテスト"""
        from src.page_navigator import PageNavigator

        # デフォルト設定
        navigator1 = PageNavigator()
        assert navigator1.base_url == 'http://localhost:18081'
        assert navigator1.default_timeout == 30

        # カスタム設定
        navigator2 = PageNavigator(
            base_url='http://localhost:8080',
            default_timeout=60
        )
        assert navigator2.base_url == 'http://localhost:8080'
        assert navigator2.default_timeout == 60