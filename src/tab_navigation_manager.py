"""タブ管理とナビゲーション履歴管理マネージャー

WebUIのタブ管理、ナビゲーション履歴、ストレージ管理を行うマネージャークラス。
Task 8.2の実装に対応。
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from src.mcp_wrapper import MCPTestExecutor, PlaywrightMCPWrapper


@dataclass
class TabCreationResult:
    """タブ作成結果"""
    success: bool
    tab_created: bool = False
    tab_id: str = ""
    total_tabs: int = 0


@dataclass
class TabSwitchResult:
    """タブ切り替え結果"""
    success: bool
    tab_switched: bool = False
    current_tab_id: str = ""
    previous_tab_id: str = ""


@dataclass
class TabCloseResult:
    """タブクローズ結果"""
    success: bool
    tab_closed: bool = False
    resources_freed: bool = False


@dataclass
class DataSharingResult:
    """データ共有結果"""
    success: bool
    data_set: bool = False
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExternalLinkResult:
    """外部リンク結果"""
    success: bool
    new_tab_opened: bool = False
    target_url: str = ""


@dataclass
class NavigationResult:
    """ナビゲーション結果"""
    success: bool
    navigated: bool = False
    current_url: str = ""


@dataclass
class TabHistoryResult:
    """タブ履歴結果"""
    success: bool
    history: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class StorageResult:
    """ストレージ結果"""
    success: bool
    value: Any = None
    persisted: bool = False


@dataclass
class StorageQuotaResult:
    """ストレージ容量結果"""
    success: bool
    percentage_used: float = 0.0
    error: str = ""


@dataclass
class TabStorageResult:
    """タブストレージ結果"""
    success: bool
    session_storage_cleared: bool = False
    local_storage_preserved: bool = False


class TabNavigationManager:
    """タブ・ナビゲーション管理マネージャー"""
    
    def __init__(self):
        self.executor = MCPTestExecutor()
        # MCPラッパーを初期化
        self.executor._mcp_wrapper = PlaywrightMCPWrapper()
    
    async def _ensure_initialized(self):
        """ラッパーが初期化されていることを確認する"""
        if self.executor._mcp_wrapper and not self.executor._mcp_wrapper.is_initialized:
            await self.executor._mcp_wrapper.initialize()
    
    async def create_new_tab(self) -> TabCreationResult:
        """新しいタブを作成する"""
        try:
            await self._ensure_initialized()
            
            # 新しいタブを作成
            tab_result = await self.executor._mcp_wrapper.create_new_tab()
            
            if tab_result.get('success') and tab_result.get('tab_created'):
                # タブ一覧を取得
                list_result = await self.executor._mcp_wrapper.list_tabs()
                
                return TabCreationResult(
                    success=True,
                    tab_created=True,
                    tab_id=tab_result.get('tab_id', ''),
                    total_tabs=tab_result.get('total_tabs', 0)
                )
            
            return TabCreationResult(success=False)
            
        except Exception as e:
            return TabCreationResult(success=False)
    
    async def switch_tab(self, tab_index: int) -> TabSwitchResult:
        """タブを切り替える"""
        try:
            await self._ensure_initialized()
            
            # タブを切り替え
            switch_result = await self.executor._mcp_wrapper.switch_to_tab(
                tab_index=tab_index
            )
            
            if switch_result.get('success') and switch_result.get('switched'):
                # アクティブタブを確認
                active_result = await self.executor._mcp_wrapper.get_active_tab()
                
                return TabSwitchResult(
                    success=True,
                    tab_switched=True,
                    current_tab_id=switch_result.get('current_tab', ''),
                    previous_tab_id=switch_result.get('previous_tab', '')
                )
            
            return TabSwitchResult(success=False)
            
        except Exception as e:
            return TabSwitchResult(success=False)
    
    async def close_tab(self, tab_id: str) -> TabCloseResult:
        """タブを閉じる"""
        try:
            await self._ensure_initialized()
            
            # タブを閉じる
            close_result = await self.executor._mcp_wrapper.close_tab(
                tab_id=tab_id
            )
            
            if close_result.get('success') and close_result.get('tab_closed'):
                # リソース解放を確認
                resources_result = await self.executor._mcp_wrapper.verify_tab_resources_freed(
                    tab_id=tab_id
                )
                
                return TabCloseResult(
                    success=True,
                    tab_closed=True,
                    resources_freed=resources_result.get('resources_freed', False)
                )
            
            return TabCloseResult(success=False)
            
        except Exception as e:
            return TabCloseResult(success=False)
    
    async def set_shared_data(self, key: str, value: Any) -> DataSharingResult:
        """タブ間で共有するデータを設定する"""
        try:
            await self._ensure_initialized()
            
            # データを設定
            set_result = await self.executor._mcp_wrapper.set_tab_data(
                key=key,
                value=value
            )
            
            if set_result.get('success') and set_result.get('data_set'):
                return DataSharingResult(
                    success=True,
                    data_set=True,
                    data=value
                )
            
            return DataSharingResult(success=False)
            
        except Exception as e:
            return DataSharingResult(success=False)
    
    async def get_shared_data(self, key: str) -> DataSharingResult:
        """タブ間で共有されたデータを取得する"""
        try:
            await self._ensure_initialized()
            
            # データを取得
            get_result = await self.executor._mcp_wrapper.get_tab_data(
                key=key
            )
            
            if get_result.get('success') and get_result.get('data_found'):
                return DataSharingResult(
                    success=True,
                    data_set=False,
                    data=get_result.get('value', {})
                )
            
            return DataSharingResult(success=False)
            
        except Exception as e:
            return DataSharingResult(success=False)
    
    async def click_external_link(self, url: str) -> ExternalLinkResult:
        """外部リンクをクリックして新しいタブを開く"""
        try:
            await self._ensure_initialized()
            
            # 外部リンクをクリック
            link_result = await self.executor._mcp_wrapper.click_external_link(
                url=url
            )
            
            if link_result.get('success') and link_result.get('new_tab_opened'):
                # 新しいタブの内容を確認
                content_result = await self.executor._mcp_wrapper.verify_tab_content(
                    tab_id=link_result.get('new_tab_id', '')
                )
                
                return ExternalLinkResult(
                    success=True,
                    new_tab_opened=True,
                    target_url=link_result.get('target_url', url)
                )
            
            return ExternalLinkResult(success=False)
            
        except Exception as e:
            return ExternalLinkResult(success=False)
    
    async def navigate_back(self) -> NavigationResult:
        """ブラウザバックを実行する"""
        try:
            await self._ensure_initialized()
            
            # 履歴を取得
            history_result = await self.executor._mcp_wrapper.get_navigation_history()
            
            # バックナビゲーションを実行
            nav_result = await self.executor._mcp_wrapper.navigate_back()
            
            if nav_result.get('success') and nav_result.get('navigated'):
                return NavigationResult(
                    success=True,
                    navigated=True,
                    current_url=nav_result.get('current_url', '')
                )
            
            return NavigationResult(success=False)
            
        except Exception as e:
            return NavigationResult(success=False)
    
    async def navigate_forward(self) -> NavigationResult:
        """ブラウザフォワードを実行する"""
        try:
            await self._ensure_initialized()
            
            # フォワードナビゲーションを実行
            nav_result = await self.executor._mcp_wrapper.navigate_forward()
            
            if nav_result.get('success') and nav_result.get('navigated'):
                return NavigationResult(
                    success=True,
                    navigated=True,
                    current_url=nav_result.get('current_url', '')
                )
            
            return NavigationResult(success=False)
            
        except Exception as e:
            return NavigationResult(success=False)
    
    async def get_tab_history(self, tab_id: str) -> TabHistoryResult:
        """タブの履歴を取得する"""
        try:
            await self._ensure_initialized()
            
            # タブの履歴を取得
            history_result = await self.executor._mcp_wrapper.get_tab_history(
                tab_id=tab_id
            )
            
            if history_result.get('success'):
                return TabHistoryResult(
                    success=True,
                    history=history_result.get('history', [])
                )
            
            return TabHistoryResult(success=False)
            
        except Exception as e:
            return TabHistoryResult(success=False)
    
    async def set_session_storage(self, key: str, value: Any) -> StorageResult:
        """セッションストレージにデータを保存する"""
        try:
            await self._ensure_initialized()
            
            # セッションストレージに保存
            set_result = await self.executor._mcp_wrapper.set_session_storage(
                key=key,
                value=value
            )
            
            if set_result.get('success') and set_result.get('stored'):
                return StorageResult(
                    success=True,
                    value=value,
                    persisted=False
                )
            
            return StorageResult(success=False)
            
        except Exception as e:
            return StorageResult(success=False)
    
    async def get_session_storage(self, key: str) -> StorageResult:
        """セッションストレージからデータを取得する"""
        try:
            await self._ensure_initialized()
            
            # セッションストレージから取得
            get_result = await self.executor._mcp_wrapper.get_session_storage(
                key=key
            )
            
            if get_result.get('success') and get_result.get('found'):
                return StorageResult(
                    success=True,
                    value=get_result.get('value'),
                    persisted=False
                )
            
            return StorageResult(success=False)
            
        except Exception as e:
            return StorageResult(success=False)
    
    async def clear_session_storage(self) -> StorageResult:
        """セッションストレージをクリアする"""
        try:
            await self._ensure_initialized()
            
            # セッションストレージをクリア
            clear_result = await self.executor._mcp_wrapper.clear_session_storage()
            
            if clear_result.get('success') and clear_result.get('cleared'):
                return StorageResult(
                    success=True,
                    value=None,
                    persisted=False
                )
            
            return StorageResult(success=False)
            
        except Exception as e:
            return StorageResult(success=False)
    
    async def set_local_storage(self, key: str, value: Any) -> StorageResult:
        """ローカルストレージにデータを保存する"""
        try:
            await self._ensure_initialized()
            
            # ローカルストレージに保存
            set_result = await self.executor._mcp_wrapper.set_local_storage(
                key=key,
                value=value
            )
            
            if set_result.get('success') and set_result.get('stored'):
                return StorageResult(
                    success=True,
                    value=value,
                    persisted=True
                )
            
            return StorageResult(success=False)
            
        except Exception as e:
            return StorageResult(success=False)
    
    async def get_local_storage_from_new_tab(self, key: str) -> StorageResult:
        """新しいタブからローカルストレージを取得する"""
        try:
            await self._ensure_initialized()
            
            # 新しいタブからローカルストレージを取得
            get_result = await self.executor._mcp_wrapper.get_local_storage_from_new_tab(
                key=key
            )
            
            if get_result.get('success') and get_result.get('persisted'):
                return StorageResult(
                    success=True,
                    value=get_result.get('value'),
                    persisted=True
                )
            
            return StorageResult(success=False)
            
        except Exception as e:
            return StorageResult(success=False)
    
    async def check_storage_quota(self) -> StorageQuotaResult:
        """ストレージ容量を確認する"""
        try:
            await self._ensure_initialized()
            
            # ストレージ容量を確認
            quota_result = await self.executor._mcp_wrapper.check_storage_quota()
            
            if quota_result.get('success'):
                return StorageQuotaResult(
                    success=True,
                    percentage_used=quota_result.get('percentage_used', 0.0)
                )
            
            return StorageQuotaResult(success=False)
            
        except Exception as e:
            return StorageQuotaResult(success=False)
    
    async def store_large_data(self, key: str, value: Any) -> StorageQuotaResult:
        """大きなデータを保存する"""
        try:
            await self._ensure_initialized()
            
            # 大きなデータを保存
            store_result = await self.executor._mcp_wrapper.store_large_data(
                key=key,
                value=value
            )
            
            if store_result.get('success'):
                return StorageQuotaResult(
                    success=True,
                    percentage_used=0.0
                )
            else:
                return StorageQuotaResult(
                    success=False,
                    error=store_result.get('error', '')
                )
            
        except Exception as e:
            return StorageQuotaResult(success=False)
    
    async def close_tab_and_verify_storage(self, tab_id: str) -> TabStorageResult:
        """タブを閉じてストレージ状態を確認する"""
        try:
            await self._ensure_initialized()
            
            # タブを閉じてストレージを確認
            result = await self.executor._mcp_wrapper.close_tab_and_verify_storage(
                tab_id=tab_id
            )
            
            if result.get('success'):
                return TabStorageResult(
                    success=True,
                    session_storage_cleared=result.get('session_storage_cleared', False),
                    local_storage_preserved=result.get('local_storage_preserved', False)
                )
            
            return TabStorageResult(success=False)
            
        except Exception as e:
            return TabStorageResult(success=False)
