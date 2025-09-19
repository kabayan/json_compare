"""タブ管理とナビゲーション履歴テストケース

Task 8.2の要件に対応：
- 新規タブ作成と切り替えテストの実装
- タブ間のデータ共有検証の実装
- ブラウザバック機能テストの作成
- セッションストレージ動作確認の実装
Requirements: 8.5, 10.1, 10.2, 10.3, 10.4, 10.5
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json


def create_manager_with_mock():
    """モックされたラッパー付きのマネージャを作成するヘルパー関数"""
    from src.tab_navigation_manager import TabNavigationManager
    
    mock_wrapper = AsyncMock()
    mock_wrapper.is_initialized = False
    mock_wrapper.initialize = AsyncMock(return_value=None)
    
    manager = TabNavigationManager()
    manager.executor._mcp_wrapper = mock_wrapper
    
    return manager, mock_wrapper


class TestTabManagement:
    """タブ管理テストクラス"""
    
    @pytest.mark.asyncio
    async def test_create_new_tab(self):
        """新しいタブの作成が正しく動作すること"""
        manager, mock_wrapper = create_manager_with_mock()
        
        # タブ作成をモック
        mock_wrapper.create_new_tab = AsyncMock(return_value={
            'success': True,
            'tab_created': True,
            'tab_id': 'tab-2',
            'tab_index': 1,
            'total_tabs': 2
        })
        
        # タブ一覧をモック
        mock_wrapper.list_tabs = AsyncMock(return_value={
            'success': True,
            'tabs': [
                {'id': 'tab-1', 'index': 0, 'active': False, 'url': 'http://localhost:18081/ui'},
                {'id': 'tab-2', 'index': 1, 'active': True, 'url': 'about:blank'}
            ]
        })
        
        # 新しいタブを作成
        result = await manager.create_new_tab()
        
        assert result.success is True
        assert result.tab_created is True
        assert result.tab_id == 'tab-2'
        assert result.total_tabs == 2
    
    @pytest.mark.asyncio
    async def test_switch_between_tabs(self):
        """タブ間の切り替えが正しく動作すること"""
        manager, mock_wrapper = create_manager_with_mock()
        
        # タブ切り替えをモック
        mock_wrapper.switch_to_tab = AsyncMock(return_value={
            'success': True,
            'switched': True,
            'current_tab': 'tab-2',
            'previous_tab': 'tab-1'
        })
        
        # アクティブタブ確認をモック
        mock_wrapper.get_active_tab = AsyncMock(return_value={
            'success': True,
            'active_tab': 'tab-2',
            'tab_url': 'http://localhost:18081/ui/compare'
        })
        
        # タブを切り替え
        result = await manager.switch_tab(1)
        
        assert result.success is True
        assert result.tab_switched is True
        assert result.current_tab_id == 'tab-2'
        assert result.previous_tab_id == 'tab-1'
    
    @pytest.mark.asyncio
    async def test_close_tab(self):
        """タブを閉じる操作が正しく動作すること"""
        manager, mock_wrapper = create_manager_with_mock()
        
        # タブクローズをモック
        mock_wrapper.close_tab = AsyncMock(return_value={
            'success': True,
            'tab_closed': True,
            'closed_tab_id': 'tab-2',
            'remaining_tabs': 1
        })
        
        # リソース解放確認をモック
        mock_wrapper.verify_tab_resources_freed = AsyncMock(return_value={
            'success': True,
            'resources_freed': True,
            'memory_released': True
        })
        
        # タブを閉じる
        result = await manager.close_tab('tab-2')
        
        assert result.success is True
        assert result.tab_closed is True
        assert result.resources_freed is True
    
    @pytest.mark.asyncio
    async def test_tab_data_sharing(self):
        """タブ間でデータが共有されること"""
        manager, mock_wrapper = create_manager_with_mock()
        
        # タブでデータ設定をモック
        mock_wrapper.set_tab_data = AsyncMock(return_value={
            'success': True,
            'data_set': True,
            'key': 'shared_config',
            'value': {'theme': 'dark', 'lang': 'ja'}
        })
        
        # 別タブからデータ取得をモック
        mock_wrapper.get_tab_data = AsyncMock(return_value={
            'success': True,
            'data_found': True,
            'key': 'shared_config',
            'value': {'theme': 'dark', 'lang': 'ja'}
        })
        
        # データを設定して取得
        set_result = await manager.set_shared_data('shared_config', {'theme': 'dark', 'lang': 'ja'})
        get_result = await manager.get_shared_data('shared_config')
        
        assert set_result.success is True
        assert get_result.success is True
        assert get_result.data['theme'] == 'dark'
    
    @pytest.mark.asyncio
    async def test_external_link_opens_new_tab(self):
        """外部リンクが新しいタブで開くこと"""
        manager, mock_wrapper = create_manager_with_mock()
        
        # リンククリックをモック
        mock_wrapper.click_external_link = AsyncMock(return_value={
            'success': True,
            'link_clicked': True,
            'new_tab_opened': True,
            'new_tab_id': 'tab-3',
            'target_url': 'https://example.com'
        })
        
        # 新しいタブの内容確認をモック
        mock_wrapper.verify_tab_content = AsyncMock(return_value={
            'success': True,
            'content_loaded': True,
            'url_matches': True
        })
        
        # 外部リンクをクリック
        result = await manager.click_external_link('https://example.com')
        
        assert result.success is True
        assert result.new_tab_opened is True
        assert result.target_url == 'https://example.com'


class TestNavigationHistory:
    """ナビゲーション履歴テストクラス"""
    
    @pytest.mark.asyncio
    async def test_browser_back_navigation(self):
        """ブラウザバックが正しく動作すること"""
        manager, mock_wrapper = create_manager_with_mock()
        
        # ナビゲーション履歴をモック
        mock_wrapper.get_navigation_history = AsyncMock(return_value={
            'success': True,
            'history': [
                {'url': 'http://localhost:18081/ui', 'title': 'Home'},
                {'url': 'http://localhost:18081/ui/compare', 'title': 'Compare'},
                {'url': 'http://localhost:18081/ui/results', 'title': 'Results'}
            ],
            'current_index': 2
        })
        
        # バックナビゲーションをモック
        mock_wrapper.navigate_back = AsyncMock(return_value={
            'success': True,
            'navigated': True,
            'current_url': 'http://localhost:18081/ui/compare',
            'previous_url': 'http://localhost:18081/ui/results'
        })
        
        # ブラウザバックを実行
        result = await manager.navigate_back()
        
        assert result.success is True
        assert result.navigated is True
        assert result.current_url == 'http://localhost:18081/ui/compare'
    
    @pytest.mark.asyncio
    async def test_browser_forward_navigation(self):
        """ブラウザフォワードが正しく動作すること"""
        manager, mock_wrapper = create_manager_with_mock()
        
        # フォワードナビゲーションをモック
        mock_wrapper.navigate_forward = AsyncMock(return_value={
            'success': True,
            'navigated': True,
            'current_url': 'http://localhost:18081/ui/results',
            'previous_url': 'http://localhost:18081/ui/compare'
        })
        
        # フォワードを実行
        result = await manager.navigate_forward()
        
        assert result.success is True
        assert result.navigated is True
        assert result.current_url == 'http://localhost:18081/ui/results'
    
    @pytest.mark.asyncio
    async def test_history_preservation_across_tabs(self):
        """各タブで履歴が保持されること"""
        manager, mock_wrapper = create_manager_with_mock()
        
        # タブ1の履歴をモック
        mock_wrapper.get_tab_history = AsyncMock(side_effect=[
            {
                'success': True,
                'tab_id': 'tab-1',
                'history': [
                    {'url': 'http://localhost:18081/ui', 'title': 'Home'},
                    {'url': 'http://localhost:18081/ui/compare', 'title': 'Compare'}
                ],
                'current_index': 1
            },
            {
                'success': True,
                'tab_id': 'tab-2',
                'history': [
                    {'url': 'http://localhost:18081/ui/llm', 'title': 'LLM'}
                ],
                'current_index': 0
            }
        ])
        
        # 各タブの履歴を確認
        tab1_history = await manager.get_tab_history('tab-1')
        tab2_history = await manager.get_tab_history('tab-2')
        
        assert tab1_history.success is True
        assert len(tab1_history.history) == 2
        assert tab2_history.success is True
        assert len(tab2_history.history) == 1


class TestStorageManagement:
    """ストレージ管理テストクラス"""
    
    @pytest.mark.asyncio
    async def test_session_storage_operations(self):
        """セッションストレージの操作が正しく動作すること"""
        manager, mock_wrapper = create_manager_with_mock()
        
        # セッションストレージへの保存をモック
        mock_wrapper.set_session_storage = AsyncMock(return_value={
            'success': True,
            'key': 'temp_data',
            'value': {'session_id': 'abc123', 'timestamp': 1642000000},
            'stored': True
        })
        
        # セッションストレージからの取得をモック
        mock_wrapper.get_session_storage = AsyncMock(return_value={
            'success': True,
            'key': 'temp_data',
            'value': {'session_id': 'abc123', 'timestamp': 1642000000},
            'found': True
        })
        
        # セッションストレージのクリアをモック
        mock_wrapper.clear_session_storage = AsyncMock(return_value={
            'success': True,
            'cleared': True
        })
        
        # セッションストレージ操作を実行
        set_result = await manager.set_session_storage('temp_data', {'session_id': 'abc123', 'timestamp': 1642000000})
        get_result = await manager.get_session_storage('temp_data')
        clear_result = await manager.clear_session_storage()
        
        assert set_result.success is True
        assert get_result.success is True
        assert get_result.value['session_id'] == 'abc123'
        assert clear_result.success is True
    
    @pytest.mark.asyncio
    async def test_local_storage_persistence(self):
        """ローカルストレージがタブを跨いで保持されること"""
        manager, mock_wrapper = create_manager_with_mock()
        
        # ローカルストレージへの保存をモック
        mock_wrapper.set_local_storage = AsyncMock(return_value={
            'success': True,
            'key': 'user_preferences',
            'value': {'theme': 'dark', 'language': 'ja', 'llm_mode': True},
            'stored': True
        })
        
        # 別タブからローカルストレージ取得をモック
        mock_wrapper.get_local_storage_from_new_tab = AsyncMock(return_value={
            'success': True,
            'key': 'user_preferences',
            'value': {'theme': 'dark', 'language': 'ja', 'llm_mode': True},
            'persisted': True
        })
        
        # ローカルストレージの永続性を確認
        set_result = await manager.set_local_storage('user_preferences', {'theme': 'dark', 'language': 'ja', 'llm_mode': True})
        get_result = await manager.get_local_storage_from_new_tab('user_preferences')
        
        assert set_result.success is True
        assert get_result.success is True
        assert get_result.persisted is True
        assert get_result.value['llm_mode'] is True
    
    @pytest.mark.asyncio
    async def test_storage_quota_limits(self):
        """ストレージの容量制限が正しく処理されること"""
        manager, mock_wrapper = create_manager_with_mock()
        
        # ストレージ容量確認をモック
        mock_wrapper.check_storage_quota = AsyncMock(return_value={
            'success': True,
            'used_bytes': 4500000,  # 4.5MB
            'quota_bytes': 5242880,  # 5MB
            'percentage_used': 85.8
        })
        
        # 大きなデータ保存試行をモック
        mock_wrapper.store_large_data = AsyncMock(return_value={
            'success': False,
            'error': 'QuotaExceededError',
            'message': 'Storage quota would be exceeded'
        })
        
        # ストレージ容量を確認
        quota_result = await manager.check_storage_quota()
        store_result = await manager.store_large_data('huge_data', {'data': 'x' * 1000000})
        
        assert quota_result.success is True
        assert quota_result.percentage_used > 80
        assert store_result.success is False
        assert store_result.error == 'QuotaExceededError'
    
    @pytest.mark.asyncio
    async def test_tab_close_clears_session_storage(self):
        """タブを閉じるとセッションストレージがクリアされること"""
        manager, mock_wrapper = create_manager_with_mock()
        
        # タブクローズとストレージクリアをモック
        mock_wrapper.close_tab_and_verify_storage = AsyncMock(return_value={
            'success': True,
            'tab_closed': True,
            'session_storage_cleared': True,
            'local_storage_preserved': True
        })
        
        # タブを閉じてストレージ状態を確認
        result = await manager.close_tab_and_verify_storage('tab-1')
        
        assert result.success is True
        assert result.session_storage_cleared is True
        assert result.local_storage_preserved is True
