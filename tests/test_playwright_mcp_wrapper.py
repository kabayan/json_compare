"""Task 1.1: Playwright MCP軽量ラッパーテスト

TDD実装：既存MCPツールへの軽量ラッパークラス作成
Requirements: 1.1, 1.2, 1.3 - MCP環境構築、エラーハンドリング、リソース管理
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional


class TestPlaywrightMCPWrapper:
    """Playwright MCP軽量ラッパーのテスト"""

    def test_mcp_wrapper_initialization(self):
        """MCPラッパークラスが正しく初期化されること"""
        from src.mcp_wrapper import PlaywrightMCPWrapper

        wrapper = PlaywrightMCPWrapper()
        assert wrapper is not None
        assert hasattr(wrapper, 'initialize')
        assert hasattr(wrapper, 'cleanup')
        assert hasattr(wrapper, 'navigate')
        assert hasattr(wrapper, 'take_snapshot')
        assert hasattr(wrapper, 'click_element')

    @pytest.mark.asyncio
    async def test_mcp_wrapper_initialize(self):
        """MCPラッパーが正しく初期化されること"""
        from src.mcp_wrapper import PlaywrightMCPWrapper

        wrapper = PlaywrightMCPWrapper()

        # 初期化前は未初期化状態
        assert not wrapper.is_initialized

        # 初期化実行
        await wrapper.initialize()

        # 初期化後は初期化済み状態
        assert wrapper.is_initialized

    @pytest.mark.asyncio
    async def test_mcp_wrapper_navigate_success(self):
        """ページナビゲーションが成功すること"""
        from src.mcp_wrapper import PlaywrightMCPWrapper

        wrapper = PlaywrightMCPWrapper()
        await wrapper.initialize()

        # MCPツール呼び出しをモック
        with patch('src.mcp_wrapper.mcp__playwright__browser_navigate') as mock_navigate:
            mock_navigate.return_value = {'success': True, 'url': 'http://localhost:18081/ui'}

            result = await wrapper.navigate('http://localhost:18081/ui')

            assert result['success'] is True
            assert result['url'] == 'http://localhost:18081/ui'
            mock_navigate.assert_called_once_with(url='http://localhost:18081/ui')

    @pytest.mark.asyncio
    async def test_mcp_wrapper_navigate_with_retry(self):
        """ナビゲーション失敗時にリトライが実行されること"""
        from src.mcp_wrapper import PlaywrightMCPWrapper

        wrapper = PlaywrightMCPWrapper()
        await wrapper.initialize()

        # 1回目失敗、2回目成功のシナリオ
        with patch('src.mcp_wrapper.mcp__playwright__browser_navigate') as mock_navigate:
            mock_navigate.side_effect = [
                {'success': False, 'error': 'Network timeout'},
                {'success': True, 'url': 'http://localhost:18081/ui'}
            ]

            result = await wrapper.navigate('http://localhost:18081/ui', max_retries=2)

            assert result['success'] is True
            assert mock_navigate.call_count == 2

    @pytest.mark.asyncio
    async def test_mcp_wrapper_error_handling(self):
        """エラーハンドリングが正しく動作すること"""
        from src.mcp_wrapper import PlaywrightMCPWrapper
        from src.mcp_wrapper import MCPWrapperError

        wrapper = PlaywrightMCPWrapper()
        await wrapper.initialize()

        # MCP呼び出しでエラーが発生
        with patch('src.mcp_wrapper.mcp__playwright__browser_navigate') as mock_navigate:
            mock_navigate.side_effect = Exception("MCP connection failed")

            with pytest.raises(MCPWrapperError) as exc_info:
                await wrapper.navigate('http://localhost:18081/ui', max_retries=1)

            assert "MCP connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mcp_wrapper_take_snapshot(self):
        """スナップショット機能が正しく動作すること"""
        from src.mcp_wrapper import PlaywrightMCPWrapper

        wrapper = PlaywrightMCPWrapper()
        await wrapper.initialize()

        with patch('src.mcp_wrapper.mcp__playwright__browser_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {
                'success': True,
                'snapshot': {'title': 'JSON Compare WebUI', 'elements': []}
            }

            result = await wrapper.take_snapshot()

            assert result['success'] is True
            assert 'snapshot' in result
            mock_snapshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_wrapper_click_element(self):
        """要素クリック機能が正しく動作すること"""
        from src.mcp_wrapper import PlaywrightMCPWrapper

        wrapper = PlaywrightMCPWrapper()
        await wrapper.initialize()

        with patch('src.mcp_wrapper.mcp__playwright__browser_click') as mock_click:
            mock_click.return_value = {'success': True}

            result = await wrapper.click_element("Submit button", "btn-submit")

            assert result['success'] is True
            mock_click.assert_called_once_with(
                element="Submit button",
                ref="btn-submit"
            )

    @pytest.mark.asyncio
    async def test_mcp_wrapper_context_management(self):
        """テストコンテキスト管理が正しく動作すること"""
        from src.mcp_wrapper import PlaywrightMCPWrapper

        wrapper = PlaywrightMCPWrapper()
        await wrapper.initialize()

        # コンテキスト変数の設定
        wrapper.set_context_variable('test_session_id', 'session_123')
        wrapper.set_context_variable('base_url', 'http://localhost:18081')

        # コンテキスト変数の取得
        assert wrapper.get_context_variable('test_session_id') == 'session_123'
        assert wrapper.get_context_variable('base_url') == 'http://localhost:18081'
        assert wrapper.get_context_variable('nonexistent') is None

        # コンテキスト全体の取得
        context = wrapper.get_context()
        assert context['test_session_id'] == 'session_123'
        assert context['base_url'] == 'http://localhost:18081'

    @pytest.mark.asyncio
    async def test_mcp_wrapper_cleanup(self):
        """クリーンアップが正しく実行されること"""
        from src.mcp_wrapper import PlaywrightMCPWrapper

        wrapper = PlaywrightMCPWrapper()
        await wrapper.initialize()

        # コンテキスト変数を設定
        wrapper.set_context_variable('test_data', 'cleanup_test')

        # クリーンアップ実行
        await wrapper.cleanup()

        # 初期化状態がリセットされること
        assert not wrapper.is_initialized

        # コンテキストがクリアされること
        assert len(wrapper.get_context()) == 0


class TestMCPWrapperIntegration:
    """MCP ラッパーの統合テスト"""

    @pytest.mark.asyncio
    async def test_full_navigation_flow(self):
        """完全なナビゲーションフローのテスト"""
        from src.mcp_wrapper import PlaywrightMCPWrapper

        wrapper = PlaywrightMCPWrapper()

        try:
            # 1. 初期化
            await wrapper.initialize()
            assert wrapper.is_initialized

            # 2. ナビゲーション（モック）
            with patch('src.mcp_wrapper.mcp__playwright__browser_navigate') as mock_nav:
                mock_nav.return_value = {'success': True, 'url': 'http://localhost:18081/ui'}

                nav_result = await wrapper.navigate('http://localhost:18081/ui')
                assert nav_result['success'] is True

            # 3. スナップショット取得（モック）
            with patch('src.mcp_wrapper.mcp__playwright__browser_snapshot') as mock_snap:
                mock_snap.return_value = {'success': True, 'snapshot': {'title': 'WebUI'}}

                snap_result = await wrapper.take_snapshot()
                assert snap_result['success'] is True

        finally:
            # 4. クリーンアップ
            await wrapper.cleanup()
            assert not wrapper.is_initialized


class TestMCPTestExecutor:
    """Task 1.2: テスト実行コントローラーのテスト"""

    def test_test_executor_initialization(self):
        """テスト実行コントローラーが正しく初期化されること"""
        from src.mcp_wrapper import MCPTestExecutor

        executor = MCPTestExecutor()
        assert executor is not None
        assert hasattr(executor, 'initialize')
        assert hasattr(executor, 'execute_test')
        assert hasattr(executor, 'cleanup')
        assert hasattr(executor, 'get_session_state')

    @pytest.mark.asyncio
    async def test_test_executor_session_management(self):
        """テストセッション状態管理が正しく動作すること"""
        from src.mcp_wrapper import MCPTestExecutor

        executor = MCPTestExecutor()
        await executor.initialize()

        # セッションIDが生成されること
        session_id = executor.get_session_id()
        assert session_id is not None
        assert len(session_id) > 0

        # セッション状態の管理
        executor.set_session_variable('test_start_time', '2025-09-18T20:00:00Z')
        executor.set_session_variable('test_user', 'automation_user')

        assert executor.get_session_variable('test_start_time') == '2025-09-18T20:00:00Z'
        assert executor.get_session_variable('test_user') == 'automation_user'

        # セッション状態の一括取得
        session_state = executor.get_session_state()
        assert session_state['test_start_time'] == '2025-09-18T20:00:00Z'
        assert session_state['test_user'] == 'automation_user'

        await executor.cleanup()

    @pytest.mark.asyncio
    async def test_test_executor_browser_context_management(self):
        """ブラウザコンテキスト管理が正しく動作すること"""
        from src.mcp_wrapper import MCPTestExecutor

        executor = MCPTestExecutor()
        await executor.initialize()

        # ブラウザコンテキストの作成
        context_id = await executor.create_browser_context()
        assert context_id is not None

        # アクティブコンテキストの設定
        await executor.set_active_context(context_id)
        assert executor.get_active_context_id() == context_id

        # コンテキストのクリーンアップ
        await executor.cleanup_browser_context(context_id)

        await executor.cleanup()

    @pytest.mark.asyncio
    async def test_test_executor_execute_test(self):
        """テストケース実行が正しく動作すること"""
        from src.mcp_wrapper import MCPTestExecutor, TestCase, TestStep

        executor = MCPTestExecutor()
        await executor.initialize()

        # テストケースの作成
        test_case = TestCase(
            id="test_001",
            name="Basic navigation test",
            steps=[
                TestStep(action="navigate", params={"url": "http://localhost:18081/ui"}),
                TestStep(action="snapshot", params={}),
            ],
            timeout=30
        )

        # MCP Wrapperをモック
        with patch.object(executor, '_mcp_wrapper') as mock_wrapper:
            mock_wrapper.navigate = AsyncMock(return_value={'success': True})
            mock_wrapper.take_snapshot = AsyncMock(return_value={'success': True, 'snapshot': {}})

            # テスト実行
            result = await executor.execute_test(test_case)

            assert result.test_id == "test_001"
            assert result.status == "passed"
            assert result.duration > 0
            assert len(result.step_results) == 2

        await executor.cleanup()

    @pytest.mark.asyncio
    async def test_test_executor_execute_test_failure(self):
        """テストケース実行失敗時の処理が正しく動作すること"""
        from src.mcp_wrapper import MCPTestExecutor, TestCase, TestStep

        executor = MCPTestExecutor()
        await executor.initialize()

        # 失敗するテストケースの作成
        test_case = TestCase(
            id="test_002",
            name="Failing navigation test",
            steps=[
                TestStep(action="navigate", params={"url": "http://invalid-url"}),
            ],
            timeout=30
        )

        # MCP Wrapperをモック（失敗）
        with patch.object(executor, '_mcp_wrapper') as mock_wrapper:
            mock_wrapper.navigate = AsyncMock(side_effect=Exception("Navigation failed"))

            # テスト実行
            result = await executor.execute_test(test_case)

            assert result.test_id == "test_002"
            assert result.status == "failed"
            assert len(result.errors) > 0
            assert "Navigation failed" in str(result.errors[0])

        await executor.cleanup()

    @pytest.mark.asyncio
    async def test_test_executor_resource_cleanup(self):
        """リソースクリーンアップが正しく実行されること"""
        from src.mcp_wrapper import MCPTestExecutor

        executor = MCPTestExecutor()
        await executor.initialize()

        # 複数のブラウザコンテキストを作成
        context1 = await executor.create_browser_context()
        context2 = await executor.create_browser_context()

        # セッション変数を設定
        executor.set_session_variable('temp_data', 'cleanup_test')

        # クリーンアップ実行
        await executor.cleanup()

        # 全てのリソースがクリーンアップされること
        assert len(executor.get_active_contexts()) == 0
        assert len(executor.get_session_state()) == 0

    @pytest.mark.asyncio
    async def test_test_executor_timeout_handling(self):
        """タイムアウト処理が正しく動作すること"""
        from src.mcp_wrapper import MCPTestExecutor, TestCase, TestStep

        executor = MCPTestExecutor()
        await executor.initialize()

        # タイムアウトするテストケース
        test_case = TestCase(
            id="test_003",
            name="Timeout test",
            steps=[
                TestStep(action="navigate", params={"url": "http://localhost:18081/ui"}),
            ],
            timeout=0.1  # 0.1秒でタイムアウト
        )

        # MCP Wrapperをモック（遅延）
        with patch.object(executor, '_mcp_wrapper') as mock_wrapper:
            async def slow_navigate(*args, **kwargs):
                await asyncio.sleep(1)  # 1秒待機
                return {'success': True}

            mock_wrapper.navigate = AsyncMock(side_effect=slow_navigate)

            # テスト実行
            result = await executor.execute_test(test_case)

            assert result.test_id == "test_003"
            assert result.status == "failed"
            assert any("timed out" in str(error).lower() for error in result.errors)

        await executor.cleanup()