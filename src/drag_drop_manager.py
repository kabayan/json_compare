"""ドラッグアンドドロップ操作管理マネージャー

WebUIのドラッグ&ドロップ操作を管理するマネージャークラス。
Task 8.1の実装に対応。
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from src.mcp_wrapper import MCPTestExecutor, PlaywrightMCPWrapper
from pathlib import Path


@dataclass
class DragDropResult:
    """ドラッグアンドドロップ操作結果"""
    success: bool
    drag_completed: bool = False
    drop_zone_updated: bool = False
    dropped_item_id: str = ""


@dataclass
class DropZoneValidationResult:
    """ドロップゾーン検証結果"""
    success: bool
    total_zones: int = 0
    active_zones: int = 0
    zone_configurations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class FileDragDropResult:
    """ファイルドラッグアンドドロップ結果"""
    success: bool
    files_dropped: int = 0
    all_files_accepted: bool = False
    dropped_files: List[str] = field(default_factory=list)


@dataclass
class HoverEffectResult:
    """ホバーエフェクト結果"""
    success: bool
    hover_active: bool = False
    has_visual_feedback: bool = False
    hover_styles: Dict[str, str] = field(default_factory=dict)


@dataclass
class DragCancelResult:
    """ドラッグキャンセル結果"""
    success: bool
    drag_cancelled: bool = False
    original_state_restored: bool = False


@dataclass
class MultiItemDragResult:
    """複数アイテムドラッグ結果"""
    success: bool
    items_dragged: int = 0
    all_items_dropped: bool = False


@dataclass
class DragBoundaryResult:
    """ドラッグ境界制約結果"""
    success: bool
    constrained_to_bounds: bool = False
    boundary_respected: bool = False


@dataclass
class DragFeedbackResult:
    """ドラッグフィードバック結果"""
    success: bool
    ghost_image_visible: bool = False
    drop_indicators_shown: bool = False
    cursor_feedback: bool = False


class DragDropManager:
    """ドラッグアンドドロップ操作管理マネージャー"""
    
    def __init__(self):
        self.executor = MCPTestExecutor()
        # MCPラッパーを初期化
        self.executor._mcp_wrapper = PlaywrightMCPWrapper()
    
    async def _ensure_initialized(self):
        """ラッパーが初期化されていることを確認する"""
        if self.executor._mcp_wrapper and not self.executor._mcp_wrapper.is_initialized:
            await self.executor._mcp_wrapper.initialize()
    
    async def drag_element_to_zone(self, item_id: str, zone_id: str) -> DragDropResult:
        """要素をドロップゾーンにドラッグする"""
        try:
            await self._ensure_initialized()
            
            # ドラッグ操作を実行
            drag_result = await self.executor._mcp_wrapper.drag_element(
                startElement=f"draggable-item",
                startRef=item_id,
                endElement="drop-zone",
                endRef=zone_id
            )
            
            if not drag_result.get('success'):
                return DragDropResult(success=False)
            
            # ドロップゾーンの状態を確認
            zone_state = await self.executor._mcp_wrapper.verify_drop_zone_state(
                zone_id=zone_id
            )
            
            if zone_state.get('success') and zone_state.get('has_item'):
                return DragDropResult(
                    success=True,
                    drag_completed=True,
                    drop_zone_updated=True,
                    dropped_item_id=zone_state.get('item_id', item_id)
                )
            
            return DragDropResult(success=False)
            
        except Exception as e:
            return DragDropResult(success=False)
    
    async def validate_drop_zones(self) -> DropZoneValidationResult:
        """ドロップゾーンを検証する"""
        try:
            await self._ensure_initialized()
            
            # ドロップゾーン要素を取得
            zones_result = await self.executor._mcp_wrapper.get_drop_zone_elements()
            
            if not zones_result.get('success'):
                return DropZoneValidationResult(success=False)
            
            drop_zones = zones_result.get('drop_zones', [])
            active_count = sum(1 for zone in drop_zones if zone.get('active'))
            
            # 利用可能性を確認
            availability = await self.executor._mcp_wrapper.check_drop_zone_availability()
            
            return DropZoneValidationResult(
                success=True,
                total_zones=len(drop_zones),
                active_zones=active_count,
                zone_configurations=drop_zones
            )
            
        except Exception as e:
            return DropZoneValidationResult(success=False)
    
    async def drag_and_drop_files(self, files: List[Path], zone_id: str) -> FileDragDropResult:
        """ファイルをドラッグアンドドロップする"""
        try:
            await self._ensure_initialized()
            
            # ファイルドラッグシミュレーションを開始
            sim_result = await self.executor._mcp_wrapper.trigger_file_drag_simulation()
            
            if not sim_result.get('success'):
                return FileDragDropResult(success=False)
            
            # ファイルドロップをシミュレート
            file_paths = [str(f) for f in files]
            drop_result = await self.executor._mcp_wrapper.simulate_file_drop(
                files=file_paths,
                zone_id=zone_id
            )
            
            if drop_result.get('success') and drop_result.get('files_accepted'):
                # アップロード状態を確認
                upload_state = await self.executor._mcp_wrapper.verify_file_upload_state()
                
                return FileDragDropResult(
                    success=True,
                    files_dropped=len(files),
                    all_files_accepted=True,
                    dropped_files=drop_result.get('files_dropped', [])
                )
            
            return FileDragDropResult(success=False)
            
        except Exception as e:
            return FileDragDropResult(success=False)
    
    async def verify_hover_effect(self, zone_id: str) -> HoverEffectResult:
        """ホバーエフェクトを検証する"""
        try:
            await self._ensure_initialized()
            
            # 要素にホバー
            hover_result = await self.executor._mcp_wrapper.hover_element(
                element="drop-zone",
                ref=zone_id
            )
            
            if not hover_result.get('success'):
                return HoverEffectResult(success=False)
            
            # ホバースタイルを確認
            styles_result = await self.executor._mcp_wrapper.check_hover_styles(
                element_ref=zone_id
            )
            
            if styles_result.get('success') and styles_result.get('has_hover_class'):
                return HoverEffectResult(
                    success=True,
                    hover_active=True,
                    has_visual_feedback=True,
                    hover_styles=styles_result.get('hover_styles', {})
                )
            
            return HoverEffectResult(success=False)
            
        except Exception as e:
            return HoverEffectResult(success=False)
    
    async def cancel_drag_operation(self, item_id: str) -> DragCancelResult:
        """ドラッグ操作をキャンセルする"""
        try:
            await self._ensure_initialized()
            
            # ドラッグを開始
            start_result = await self.executor._mcp_wrapper.start_drag(
                element_id=item_id
            )
            
            if not start_result.get('success'):
                return DragCancelResult(success=False)
            
            # ESCキーでキャンセル
            key_result = await self.executor._mcp_wrapper.press_key(key="Escape")
            
            # キャンセル状態を確認
            cancel_result = await self.executor._mcp_wrapper.verify_drag_cancelled(
                element_id=item_id
            )
            
            if cancel_result.get('success') and cancel_result.get('drag_cancelled'):
                return DragCancelResult(
                    success=True,
                    drag_cancelled=True,
                    original_state_restored=cancel_result.get('original_position_restored', False)
                )
            
            return DragCancelResult(success=False)
            
        except Exception as e:
            return DragCancelResult(success=False)
    
    async def drag_multiple_items(self, items: List[str], zone_id: str) -> MultiItemDragResult:
        """複数アイテムをドラッグする"""
        try:
            await self._ensure_initialized()
            
            # 複数アイテムを選択
            select_result = await self.executor._mcp_wrapper.select_multiple_items(
                item_ids=items
            )
            
            if not select_result.get('success'):
                return MultiItemDragResult(success=False)
            
            # 複数ドラッグを実行
            drag_result = await self.executor._mcp_wrapper.drag_multiple_elements(
                items=items,
                zone_id=zone_id
            )
            
            if drag_result.get('success') and drag_result.get('all_dropped'):
                return MultiItemDragResult(
                    success=True,
                    items_dragged=drag_result.get('items_dragged', len(items)),
                    all_items_dropped=True
                )
            
            return MultiItemDragResult(success=False)
            
        except Exception as e:
            return MultiItemDragResult(success=False)
    
    async def test_drag_boundaries(self, item_id: str, target_position: Dict[str, int]) -> DragBoundaryResult:
        """ドラッグ境界制約をテストする"""
        try:
            await self._ensure_initialized()
            
            # 境界外へのドラッグを試行
            drag_result = await self.executor._mcp_wrapper.attempt_drag_outside_bounds(
                element_id=item_id,
                target_position=target_position
            )
            
            if not drag_result.get('success'):
                return DragBoundaryResult(success=False)
            
            # 境界制約を検証
            boundary_result = await self.executor._mcp_wrapper.verify_boundary_constraints(
                element_id=item_id
            )
            
            if boundary_result.get('success') and boundary_result.get('boundary_respected'):
                return DragBoundaryResult(
                    success=True,
                    constrained_to_bounds=drag_result.get('constrained_to_bounds', False),
                    boundary_respected=True
                )
            
            return DragBoundaryResult(success=False)
            
        except Exception as e:
            return DragBoundaryResult(success=False)
    
    async def verify_drag_feedback(self, item_id: str) -> DragFeedbackResult:
        """ドラッグフィードバックを検証する"""
        try:
            await self._ensure_initialized()
            
            # ゴーストイメージを確認
            ghost_result = await self.executor._mcp_wrapper.check_drag_ghost_image(
                element_id=item_id
            )
            
            # ドロップインジケーターを確認
            indicators_result = await self.executor._mcp_wrapper.check_drop_indicators()
            
            if ghost_result.get('success') and indicators_result.get('success'):
                return DragFeedbackResult(
                    success=True,
                    ghost_image_visible=ghost_result.get('ghost_image_visible', False),
                    drop_indicators_shown=indicators_result.get('valid_drop_zones_highlighted', False),
                    cursor_feedback=indicators_result.get('cursor_changed', False)
                )
            
            return DragFeedbackResult(success=False)
            
        except Exception as e:
            return DragFeedbackResult(success=False)
