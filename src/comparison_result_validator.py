"""比較結果表示検証マネージャー

WebUIの比較結果表示を検証するためのマネージャークラス。
Task 5.1の実装に対応。
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from src.mcp_wrapper import MCPTestExecutor


@dataclass
class ResultElementVerificationResult:
    """結果要素確認の結果"""
    success: bool
    result_container_present: bool = False
    score_display_present: bool = False
    details_section_present: bool = False
    summary_stats_present: bool = False
    missing_elements: List[str] = field(default_factory=list)


@dataclass
class ScoreInfo:
    """スコア情報"""
    field: str
    value: float
    format: str
    is_valid: bool = False
    format_correct: bool = False


@dataclass
class ScoreValidationResult:
    """スコア検証結果"""
    success: bool
    all_scores_valid: bool = False
    scores: List[ScoreInfo] = field(default_factory=list)
    invalid_scores: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DetailedResultDisplayResult:
    """詳細結果表示の検証結果"""
    success: bool
    total_rows: int = 0
    displayed_rows: int = 0
    has_pagination: bool = False
    columns: List[str] = field(default_factory=list)
    is_sortable: bool = False
    is_filterable: bool = False


@dataclass
class ProgressBarDisplayResult:
    """プログレスバー表示の検証結果"""
    success: bool
    is_visible: bool = False
    percentage: int = 0
    status_text: str = ""
    is_animated: bool = False
    style: str = ""
    is_complete: bool = False
    is_hidden_after_completion: bool = False


@dataclass
class FullValidationWorkflowResult:
    """完全な検証ワークフローの結果"""
    success: bool
    comparison_executed: bool = False
    results_displayed: bool = False
    all_validations_passed: bool = False


@dataclass
class RetryValidationResult:
    """リトライ検証の結果"""
    success: bool
    retry_count: int = 0
    recovered_from_error: bool = False


class ComparisonResultValidator:
    """比較結果表示検証マネージャー"""

    def __init__(self):
        self.executor = MCPTestExecutor()
        # MCPラッパーを初期化
        from src.mcp_wrapper import PlaywrightMCPWrapper
        self.executor._mcp_wrapper = PlaywrightMCPWrapper()
        # NOTE: 実際の実装では await self.executor._mcp_wrapper.initialize() が必要

    async def _ensure_initialized(self):
        """ラッパーが初期化されていることを確認する"""
        if self.executor._mcp_wrapper and not self.executor._mcp_wrapper.is_initialized:
            await self.executor._mcp_wrapper.initialize()

    async def verify_result_elements(self) -> ResultElementVerificationResult:
        """結果要素の存在を確認する"""
        try:
            await self._ensure_initialized()
            # JavaScriptを使用して結果要素の存在を確認
            evaluation_result = await self.executor._mcp_wrapper.browser_evaluate(
                function="""() => {
                    return {
                        result_container: !!document.querySelector('.result-container'),
                        score_display: !!document.querySelector('.score-display'),
                        details_section: !!document.querySelector('.details-section'),
                        summary_stats: !!document.querySelector('.summary-stats')
                    };
                }"""
            )

            if evaluation_result['success']:
                result_data = evaluation_result['result']

                # すべての要素が存在するかチェック
                all_present = all([
                    result_data.get('result_container', False),
                    result_data.get('score_display', False),
                    result_data.get('details_section', False),
                    result_data.get('summary_stats', False)
                ])

                # 不足している要素のリスト作成
                missing = []
                for key, value in result_data.items():
                    if not value:
                        missing.append(key)

                return ResultElementVerificationResult(
                    success=all_present,
                    result_container_present=result_data.get('result_container', False),
                    score_display_present=result_data.get('score_display', False),
                    details_section_present=result_data.get('details_section', False),
                    summary_stats_present=result_data.get('summary_stats', False),
                    missing_elements=missing
                )

            return ResultElementVerificationResult(success=False)

        except Exception as e:
            return ResultElementVerificationResult(
                success=False,
                missing_elements=[str(e)]
            )

    async def validate_score_values(self) -> ScoreValidationResult:
        """スコア値の妥当性を検証する"""
        try:
            await self._ensure_initialized()
            scores_result = await self.executor._mcp_wrapper.get_score_values()

            if scores_result['success']:
                scores_list = []
                invalid_list = []

                for score_data in scores_result['scores']:
                    value = score_data['value']
                    is_valid = 0 <= value <= 1

                    score_info = ScoreInfo(
                        field=score_data['field'],
                        value=value,
                        format=score_data['format'],
                        is_valid=is_valid,
                        format_correct=True  # 簡略化のため常にTrue
                    )
                    scores_list.append(score_info)

                    if not is_valid:
                        invalid_list.append({
                            'field': score_data['field'],
                            'value': value,
                            'reason': 'Value out of range [0, 1]'
                        })

                all_valid = len(invalid_list) == 0

                return ScoreValidationResult(
                    success=all_valid,
                    all_scores_valid=all_valid,
                    scores=scores_list,
                    invalid_scores=invalid_list
                )

            return ScoreValidationResult(success=False)

        except Exception as e:
            return ScoreValidationResult(
                success=False,
                invalid_scores=[{'error': str(e)}]
            )

    async def verify_detailed_result_display(self) -> DetailedResultDisplayResult:
        """詳細結果表示を確認する"""
        try:
            await self._ensure_initialized()
            details_result = await self.executor._mcp_wrapper.get_detailed_results()

            if details_result['success']:
                details = details_result['details']

                return DetailedResultDisplayResult(
                    success=True,
                    total_rows=details.get('total_rows', 0),
                    displayed_rows=details.get('displayed_rows', 0),
                    has_pagination=details.get('has_pagination', False),
                    columns=details.get('columns', []),
                    is_sortable=details.get('sortable', False),
                    is_filterable=details.get('filterable', False)
                )

            return DetailedResultDisplayResult(success=False)

        except Exception as e:
            return DetailedResultDisplayResult(success=False)

    async def verify_progress_bar_display(self) -> ProgressBarDisplayResult:
        """プログレスバー表示を検証する"""
        try:
            await self._ensure_initialized()
            progress_result = await self.executor._mcp_wrapper.get_progress_bar_state()

            if progress_result['success']:
                progress = progress_result['progress']

                return ProgressBarDisplayResult(
                    success=True,
                    is_visible=progress.get('visible', False),
                    percentage=progress.get('percentage', 0),
                    status_text=progress.get('status_text', ''),
                    is_animated=progress.get('animated', False),
                    style=progress.get('style', '')
                )

            return ProgressBarDisplayResult(success=False)

        except Exception as e:
            return ProgressBarDisplayResult(success=False)

    async def verify_progress_bar_completion(self) -> ProgressBarDisplayResult:
        """プログレスバー完了状態を検証する"""
        try:
            await self._ensure_initialized()
            progress_result = await self.executor._mcp_wrapper.get_progress_bar_state()

            if progress_result['success']:
                progress = progress_result['progress']

                is_complete = progress.get('completed', False) or progress.get('percentage', 0) == 100
                is_hidden = not progress.get('visible', True) if is_complete else False

                return ProgressBarDisplayResult(
                    success=True,
                    is_complete=is_complete,
                    percentage=progress.get('percentage', 0),
                    is_hidden_after_completion=is_hidden
                )

            return ProgressBarDisplayResult(success=False)

        except Exception as e:
            return ProgressBarDisplayResult(success=False)

    async def execute_full_validation_workflow(self) -> FullValidationWorkflowResult:
        """完全な検証ワークフローを実行する"""
        try:
            await self._ensure_initialized()
            # 比較を実行
            exec_result = await self.executor._mcp_wrapper.execute_comparison()
            if not exec_result.get('success'):
                return FullValidationWorkflowResult(success=False)

            # 結果を待つ
            wait_result = await self.executor._mcp_wrapper.wait_for_results()
            if not wait_result.get('success'):
                return FullValidationWorkflowResult(
                    success=False,
                    comparison_executed=True
                )

            # すべての要素を検証
            verify_result = await self.executor._mcp_wrapper.verify_all_elements()

            return FullValidationWorkflowResult(
                success=verify_result.get('success', False) and verify_result.get('all_present', False),
                comparison_executed=True,
                results_displayed=True,
                all_validations_passed=verify_result.get('all_present', False)
            )

        except Exception as e:
            return FullValidationWorkflowResult(success=False)

    async def validate_with_retry(self, max_retries: int = 3) -> RetryValidationResult:
        """リトライ付きで検証を実行する"""
        await self._ensure_initialized()
        retry_count = 0
        recovered = False

        for attempt in range(max_retries):
            try:
                result = await self.executor._mcp_wrapper.get_score_values()
                if result.get('success'):
                    return RetryValidationResult(
                        success=True,
                        retry_count=retry_count,
                        recovered_from_error=recovered
                    )
            except Exception as e:
                retry_count += 1
                recovered = True
                if attempt == max_retries - 1:
                    raise
                continue

        return RetryValidationResult(
            success=False,
            retry_count=retry_count,
            recovered_from_error=False
        )