"""Task 2.2: ビューポート管理とレスポンシブテストの作成

TDD実装：画面サイズ変更、モバイル・タブレット・デスクトップ表示検証、レスポンシブレイアウト確認、ブレークポイント動作検証
Requirements: 2.5, 8.1, 8.2 - ビューポート管理、レスポンシブ機能、デバイス対応
"""

import pytest
import asyncio
from typing import Dict, Any, List, Tuple
from unittest.mock import patch, MagicMock, AsyncMock


class TestViewportManagerBasics:
    """ビューポート管理基本テストクラス"""

    def test_viewport_manager_initialization(self):
        """ViewportManagerが正しく初期化されること"""
        from src.viewport_manager import ViewportManager

        manager = ViewportManager()
        assert manager is not None
        assert hasattr(manager, 'resize_viewport')
        assert hasattr(manager, 'verify_responsive_layout')
        assert hasattr(manager, 'test_device_breakpoints')
        assert hasattr(manager, 'get_current_viewport_info')

    @pytest.mark.asyncio
    async def test_resize_viewport_desktop(self):
        """デスクトップサイズへのビューポート変更が成功すること"""
        from src.viewport_manager import ViewportManager

        manager = ViewportManager()

        with patch('src.viewport_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.resize_browser.return_value = {
                'success': True,
                'width': 1920,
                'height': 1080,
                'device_type': 'desktop'
            }

            result = await manager.resize_viewport(1920, 1080)

            assert result['success'] is True
            assert result['width'] == 1920
            assert result['height'] == 1080
            assert result['device_type'] == 'desktop'

    @pytest.mark.asyncio
    async def test_resize_viewport_mobile(self):
        """モバイルサイズへのビューポート変更が成功すること"""
        from src.viewport_manager import ViewportManager

        manager = ViewportManager()

        with patch('src.viewport_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.resize_browser.return_value = {
                'success': True,
                'width': 375,
                'height': 667,
                'device_type': 'mobile'
            }

            result = await manager.resize_viewport(375, 667)

            assert result['success'] is True
            assert result['width'] == 375
            assert result['height'] == 667
            assert result['device_type'] == 'mobile'

    @pytest.mark.asyncio
    async def test_resize_viewport_tablet(self):
        """タブレットサイズへのビューポート変更が成功すること"""
        from src.viewport_manager import ViewportManager

        manager = ViewportManager()

        with patch('src.viewport_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.resize_browser.return_value = {
                'success': True,
                'width': 768,
                'height': 1024,
                'device_type': 'tablet'
            }

            result = await manager.resize_viewport(768, 1024)

            assert result['success'] is True
            assert result['width'] == 768
            assert result['height'] == 1024
            assert result['device_type'] == 'tablet'

    @pytest.mark.asyncio
    async def test_verify_responsive_layout_desktop(self):
        """デスクトップレイアウトの検証が正しく動作すること"""
        from src.viewport_manager import ViewportManager

        manager = ViewportManager()

        with patch('src.viewport_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'viewport': {'width': 1920, 'height': 1080},
                    'elements': [
                        {'type': 'container', 'id': 'main-container', 'width': 1200, 'display': 'block'},
                        {'type': 'sidebar', 'id': 'sidebar', 'width': 300, 'display': 'block'},
                        {'type': 'navigation', 'id': 'nav-menu', 'display': 'flex'}
                    ]
                }
            }

            expected_layout = {
                'container_min_width': 1000,
                'sidebar_visible': True,
                'navigation_layout': 'horizontal'
            }

            result = await manager.verify_responsive_layout('desktop', expected_layout)

            assert result['layout_valid'] is True
            assert result['device_type'] == 'desktop'
            assert result['viewport_width'] == 1920

    @pytest.mark.asyncio
    async def test_verify_responsive_layout_mobile(self):
        """モバイルレイアウトの検証が正しく動作すること"""
        from src.viewport_manager import ViewportManager

        manager = ViewportManager()

        with patch('src.viewport_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'viewport': {'width': 375, 'height': 667},
                    'elements': [
                        {'type': 'container', 'id': 'main-container', 'width': 375, 'display': 'block'},
                        {'type': 'sidebar', 'id': 'sidebar', 'width': 0, 'display': 'none'},
                        {'type': 'navigation', 'id': 'nav-menu', 'display': 'none'},
                        {'type': 'hamburger', 'id': 'mobile-menu', 'display': 'block'}
                    ]
                }
            }

            expected_layout = {
                'container_min_width': 320,
                'sidebar_visible': False,
                'navigation_layout': 'hamburger'
            }

            result = await manager.verify_responsive_layout('mobile', expected_layout)

            assert result['layout_valid'] is True
            assert result['device_type'] == 'mobile'
            assert result['viewport_width'] == 375

    @pytest.mark.asyncio
    async def test_test_device_breakpoints(self):
        """デバイスブレークポイントのテストが正しく動作すること"""
        from src.viewport_manager import ViewportManager

        manager = ViewportManager()

        with patch('src.viewport_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()

            # 複数のビューポートサイズに対するモックレスポンス
            viewport_responses = [
                # モバイル (375px)
                {
                    'success': True,
                    'snapshot': {
                        'viewport': {'width': 375, 'height': 667},
                        'elements': [
                            {'type': 'container', 'width': 375, 'class': 'mobile-layout'}
                        ]
                    }
                },
                # タブレット (768px)
                {
                    'success': True,
                    'snapshot': {
                        'viewport': {'width': 768, 'height': 1024},
                        'elements': [
                            {'type': 'container', 'width': 768, 'class': 'tablet-layout'}
                        ]
                    }
                },
                # デスクトップ (1920px)
                {
                    'success': True,
                    'snapshot': {
                        'viewport': {'width': 1920, 'height': 1080},
                        'elements': [
                            {'type': 'container', 'width': 1200, 'class': 'desktop-layout'}
                        ]
                    }
                }
            ]

            mock_executor._mcp_wrapper.resize_browser.return_value = {'success': True}
            mock_executor._mcp_wrapper.take_snapshot.side_effect = viewport_responses

            breakpoints = [
                {'name': 'mobile', 'width': 375, 'height': 667},
                {'name': 'tablet', 'width': 768, 'height': 1024},
                {'name': 'desktop', 'width': 1920, 'height': 1080}
            ]

            result = await manager.test_device_breakpoints(breakpoints)

            assert result['all_breakpoints_valid'] is True
            assert len(result['breakpoint_results']) == 3
            assert result['breakpoint_results'][0]['device_type'] == 'mobile'
            assert result['breakpoint_results'][1]['device_type'] == 'tablet'
            assert result['breakpoint_results'][2]['device_type'] == 'desktop'

    @pytest.mark.asyncio
    async def test_get_current_viewport_info(self):
        """現在のビューポート情報取得が正しく動作すること"""
        from src.viewport_manager import ViewportManager

        manager = ViewportManager()

        with patch('src.viewport_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'viewport': {'width': 1920, 'height': 1080},
                    'title': 'JSON Compare WebUI',
                    'url': 'http://localhost:18081/ui'
                }
            }

            result = await manager.get_current_viewport_info()

            assert result['width'] == 1920
            assert result['height'] == 1080
            assert result['device_type'] == 'desktop'
            assert result['title'] == 'JSON Compare WebUI'


class TestViewportManagerEdgeCases:
    """ビューポート管理エッジケーステスト"""

    @pytest.mark.asyncio
    async def test_viewport_resize_failure(self):
        """ビューポートリサイズ失敗時の処理が正しく動作すること"""
        from src.viewport_manager import ViewportManager, ViewportError

        manager = ViewportManager()

        with patch('src.viewport_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.resize_browser.side_effect = Exception("Resize failed")

            with pytest.raises(ViewportError) as exc_info:
                await manager.resize_viewport(1920, 1080)

            assert "Failed to resize viewport" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_viewport_dimensions(self):
        """無効なビューポートサイズでエラーが発生すること"""
        from src.viewport_manager import ViewportManager, ViewportError

        manager = ViewportManager()

        # 負の値
        with pytest.raises(ViewportError) as exc_info:
            await manager.resize_viewport(-100, 800)

        assert "Invalid viewport dimensions" in str(exc_info.value)

        # ゼロ値
        with pytest.raises(ViewportError) as exc_info:
            await manager.resize_viewport(0, 0)

        assert "Invalid viewport dimensions" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_responsive_layout_validation_failure(self):
        """レスポンシブレイアウト検証が失敗した場合の処理が正しく動作すること"""
        from src.viewport_manager import ViewportManager

        manager = ViewportManager()

        with patch('src.viewport_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'viewport': {'width': 375, 'height': 667},
                    'elements': [
                        {'type': 'container', 'id': 'main-container', 'width': 400, 'display': 'block'},  # 横幅超過
                        {'type': 'sidebar', 'id': 'sidebar', 'width': 300, 'display': 'block'},  # モバイルで表示されるべきでない
                    ]
                }
            }

            expected_layout = {
                'container_min_width': 320,
                'sidebar_visible': False,
                'navigation_layout': 'hamburger'
            }

            result = await manager.verify_responsive_layout('mobile', expected_layout)

            assert result['layout_valid'] is False
            assert len(result['layout_issues']) > 0


class TestViewportManagerIntegration:
    """ビューポート管理統合テスト"""

    @pytest.mark.asyncio
    async def test_full_responsive_testing_workflow(self):
        """完全なレスポンシブテストワークフローのテスト"""
        from src.viewport_manager import ViewportManager

        manager = ViewportManager()

        with patch('src.viewport_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()

            # リサイズとスナップショットのモックを設定
            mock_executor._mcp_wrapper.resize_browser.return_value = {'success': True}
            mock_executor._mcp_wrapper.take_snapshot.side_effect = [
                # モバイルレイアウト確認
                {
                    'success': True,
                    'snapshot': {
                        'viewport': {'width': 375, 'height': 667},
                        'elements': [{'type': 'container', 'class': 'mobile-layout'}]
                    }
                },
                # タブレットレイアウト確認
                {
                    'success': True,
                    'snapshot': {
                        'viewport': {'width': 768, 'height': 1024},
                        'elements': [{'type': 'container', 'class': 'tablet-layout'}]
                    }
                },
                # デスクトップレイアウト確認
                {
                    'success': True,
                    'snapshot': {
                        'viewport': {'width': 1920, 'height': 1080},
                        'elements': [{'type': 'container', 'class': 'desktop-layout'}]
                    }
                }
            ]

            try:
                # 1. モバイルテスト
                mobile_resize = await manager.resize_viewport(375, 667)
                assert mobile_resize['success'] is True

                mobile_layout = await manager.verify_responsive_layout('mobile', {
                    'container_min_width': 320,
                    'sidebar_visible': False
                })
                assert mobile_layout['layout_valid'] is True

                # 2. タブレットテスト
                tablet_resize = await manager.resize_viewport(768, 1024)
                assert tablet_resize['success'] is True

                tablet_layout = await manager.verify_responsive_layout('tablet', {
                    'container_min_width': 600,
                    'sidebar_visible': True
                })
                assert tablet_layout['layout_valid'] is True

                # 3. デスクトップテスト
                desktop_resize = await manager.resize_viewport(1920, 1080)
                assert desktop_resize['success'] is True

                desktop_layout = await manager.verify_responsive_layout('desktop', {
                    'container_min_width': 1000,
                    'sidebar_visible': True
                })
                assert desktop_layout['layout_valid'] is True

            except Exception as e:
                pytest.fail(f"Full responsive workflow failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_concurrent_viewport_operations(self):
        """並行ビューポート操作の安全性テスト"""
        from src.viewport_manager import ViewportManager

        manager = ViewportManager()

        with patch('src.viewport_manager.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            mock_executor._mcp_wrapper = AsyncMock()
            mock_executor._mcp_wrapper.take_snapshot.return_value = {
                'success': True,
                'snapshot': {
                    'viewport': {'width': 1920, 'height': 1080},
                    'elements': []
                }
            }

            # 複数の並行操作（リサイズは除く）
            tasks = [
                manager.get_current_viewport_info(),
                manager.get_current_viewport_info(),
                manager.get_current_viewport_info()
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 全ての操作が正常完了することを確認
            for result in results:
                assert not isinstance(result, Exception), f"Concurrent operation failed: {result}"
                assert result['width'] == 1920
                assert result['height'] == 1080

    def test_viewport_manager_configuration(self):
        """ViewportManager設定のテスト"""
        from src.viewport_manager import ViewportManager

        # デフォルト設定
        manager1 = ViewportManager()
        assert manager1 is not None

        # カスタム設定（将来の拡張用）
        manager2 = ViewportManager()
        assert manager2 is not None