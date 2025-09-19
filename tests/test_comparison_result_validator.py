"""比較結果表示検証テストケース

Task 5.1の要件に対応：
- 結果要素の存在確認処理の実装
- スコア数値の妥当性検証ロジックの実装
- 詳細結果表示の確認テスト実装
- プログレスバー表示検証の実装
Requirements: 5.1, 5.2, 5.5 - 比較結果の表示とスコアサマリー、プログレスバー
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def create_validator_with_mock():
    """モックされたラッパー付きのバリデータを作成するヘルパー関数"""
    from src.comparison_result_validator import ComparisonResultValidator

    mock_wrapper = AsyncMock()
    mock_wrapper.is_initialized = False
    mock_wrapper.initialize = AsyncMock(return_value=None)

    validator = ComparisonResultValidator()
    validator.executor._mcp_wrapper = mock_wrapper

    return validator, mock_wrapper


class TestComparisonResultDisplay:
    """比較結果表示検証テストクラス"""

    @pytest.mark.asyncio
    async def test_result_element_presence_verification(self):
        """結果要素の存在確認が正しく動作すること"""
        from src.comparison_result_validator import ComparisonResultValidator

        # MCPTestExecutorをパッチしてからインスタンス作成
        with patch('src.comparison_result_validator.MCPTestExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor

            # MCPラッパーのモック設定
            mock_wrapper = AsyncMock()
            mock_wrapper.is_initialized = False
            mock_wrapper.initialize = AsyncMock(return_value=None)
            mock_wrapper.browser_evaluate = AsyncMock(return_value={
                'success': True,
                'result': {
                    'result_container': True,
                    'score_display': True,
                    'details_section': True,
                    'summary_stats': True
                }
            })
            mock_executor._mcp_wrapper = mock_wrapper

            # パッチ適用後にバリデータを作成
            validator = ComparisonResultValidator()
            validator.executor._mcp_wrapper = mock_wrapper

            # 結果要素の存在確認を実行
            result = await validator.verify_result_elements()

        assert result.success is True
        assert result.result_container_present is True
        assert result.score_display_present is True
        assert result.details_section_present is True
        assert result.summary_stats_present is True

    @pytest.mark.asyncio
    async def test_missing_result_elements_detection(self):
        """必要な結果要素が不足している場合の検出"""
        validator, mock_wrapper = create_validator_with_mock()

        mock_wrapper.browser_evaluate = AsyncMock(return_value={
            'success': True,
            'result': {
                'result_container': True,
                'score_display': False,  # スコア表示が欠落
                'details_section': True,
                'summary_stats': False   # サマリー統計が欧落
            }
        })

        result = await validator.verify_result_elements()

        assert result.success is False
        assert len(result.missing_elements) == 2
        assert 'score_display' in result.missing_elements
        assert 'summary_stats' in result.missing_elements

    @pytest.mark.asyncio
    async def test_score_value_validation(self):
        """スコア数値の妥当性検証が正しく動作すること"""
        validator, mock_wrapper = create_validator_with_mock()

        mock_wrapper.get_score_values = AsyncMock(return_value={
            'success': True,
            'scores': [
                {'field': 'overall_score', 'value': 0.85, 'format': '85%'},
                {'field': 'mean_score', 'value': 0.82, 'format': '0.82'},
                {'field': 'median_score', 'value': 0.88, 'format': '0.88'}
            ]
        })

        # スコア値の妥当性検証を実行
        result = await validator.validate_score_values()

        assert result.success is True
        assert result.all_scores_valid is True
        assert result.scores[0].value == 0.85
        assert result.scores[0].is_valid is True  # 0-1の範囲内
        assert result.scores[0].format_correct is True

    @pytest.mark.asyncio
    async def test_invalid_score_detection(self):
        """無効なスコア値の検出"""
        validator, mock_wrapper = create_validator_with_mock()

        mock_wrapper.get_score_values = AsyncMock(return_value={
            'success': True,
            'scores': [
                {'field': 'overall_score', 'value': 1.5, 'format': '150%'},  # 無効な値
                {'field': 'mean_score', 'value': -0.2, 'format': '-0.2'},   # 無効な値
                {'field': 'median_score', 'value': 0.88, 'format': '0.88'}  # 有効な値
            ]
        })

        result = await validator.validate_score_values()

        assert result.success is False
        assert result.all_scores_valid is False
        assert len(result.invalid_scores) == 2
        assert result.invalid_scores[0]['field'] == 'overall_score'
        assert result.invalid_scores[0]['reason'] == 'Value out of range [0, 1]'

    @pytest.mark.asyncio
    async def test_detailed_result_display_verification(self):
        """詳細結果表示の確認が正しく動作すること"""
        validator, mock_wrapper = create_validator_with_mock()

        mock_wrapper.get_detailed_results = AsyncMock(return_value={
            'success': True,
            'details': {
                'total_rows': 100,
                'displayed_rows': 20,
                'has_pagination': True,
                'columns': ['ID', 'Inference1', 'Inference2', 'Score'],
                'sortable': True,
                'filterable': True
            }
        })

        # 詳細結果表示の確認を実行
        result = await validator.verify_detailed_result_display()

        assert result.success is True
        assert result.total_rows == 100
        assert result.displayed_rows == 20
        assert result.has_pagination is True
        assert len(result.columns) == 4
        assert result.is_sortable is True
        assert result.is_filterable is True

    @pytest.mark.asyncio
    async def test_progress_bar_display_verification(self):
        """プログレスバー表示の検証が正しく動作すること"""
        validator, mock_wrapper = create_validator_with_mock()

        mock_wrapper.get_progress_bar_state = AsyncMock(return_value={
            'success': True,
            'progress': {
                'visible': True,
                'percentage': 75,
                'status_text': '75/100 行を処理中...',
                'animated': True,
                'style': 'striped'
            }
        })

        # プログレスバー表示の検証を実行
        result = await validator.verify_progress_bar_display()

        assert result.success is True
        assert result.is_visible is True
        assert result.percentage == 75
        assert result.status_text == '75/100 行を処理中...'
        assert result.is_animated is True
        assert result.style == 'striped'

    @pytest.mark.asyncio
    async def test_progress_bar_completion_state(self):
        """プログレスバー完了状態の検証"""
        validator, mock_wrapper = create_validator_with_mock()

        # 完了状態のプログレスバー
        mock_wrapper.get_progress_bar_state = AsyncMock(return_value={
            'success': True,
            'progress': {
                'visible': False,  # 完了後は非表示
                'percentage': 100,
                'status_text': '処理完了',
                'animated': False,
                'completed': True
            }
        })

        result = await validator.verify_progress_bar_completion()

        assert result.success is True
        assert result.is_complete is True
        assert result.percentage == 100
        assert result.is_hidden_after_completion is True


class TestComparisonResultIntegration:
    """比較結果表示の統合テストクラス"""

    @pytest.mark.asyncio
    async def test_full_result_display_workflow(self):
        """完全な結果表示ワークフローの検証"""
        validator, mock_wrapper = create_validator_with_mock()

        # ワークフロー全体のモック設定
        mock_wrapper.execute_comparison = AsyncMock(return_value={'success': True})
        mock_wrapper.wait_for_results = AsyncMock(return_value={'success': True})
        mock_wrapper.verify_all_elements = AsyncMock(return_value={
            'success': True,
            'all_present': True
        })

        # 完全なワークフローを実行
        workflow_result = await validator.execute_full_validation_workflow()

        assert workflow_result.success is True
        assert workflow_result.comparison_executed is True
        assert workflow_result.results_displayed is True
        assert workflow_result.all_validations_passed is True

    @pytest.mark.asyncio
    async def test_error_recovery_in_result_display(self):
        """結果表示中のエラーからのリカバリテスト"""
        validator, mock_wrapper = create_validator_with_mock()

        # 最初はエラー、リトライで成功
        mock_wrapper.get_score_values = AsyncMock(side_effect=[
            Exception("Temporary network error"),
            {
                'success': True,
                'scores': [
                    {'field': 'overall_score', 'value': 0.85, 'format': '85%'}
                ]
            }
        ])

        # エラーリカバリを含む検証
        result = await validator.validate_with_retry(max_retries=2)

        assert result.success is True
        assert result.retry_count == 1
        assert result.recovered_from_error is True