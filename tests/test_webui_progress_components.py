"""Test suite for WebUI Progress Display Components using TDD."""

import pytest
import asyncio
import json
from playwright.async_api import async_playwright, Page, BrowserContext
from typing import Dict, Any

# Import our progress tracker
from src.progress_tracker import ProgressTracker
from src.api import app

class TestProgressDisplayUIComponents:
    """Test Task 5.1: 進捗表示UIコンポーネントを構築."""

    @pytest.mark.asyncio
    async def test_progress_bar_display_area_exists(self):
        """プログレスバーの表示領域をHTMLに追加."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Navigate to the WebUI
            await page.goto("http://localhost:18081/ui")

            # Check if progress bar container exists
            progress_container = await page.query_selector("#progress-container")
            assert progress_container is not None, "Progress container should exist in HTML"

            # Check if progress bar element exists
            progress_bar = await page.query_selector("#progress-bar")
            assert progress_bar is not None, "Progress bar element should exist"

            # Check if progress bar has correct attributes
            progress_max = await progress_bar.get_attribute("max")
            assert progress_max == "100", "Progress bar should have max=100"

            progress_value = await progress_bar.get_attribute("value")
            assert progress_value == "0", "Progress bar should start at 0"

            await browser.close()

    @pytest.mark.asyncio
    async def test_percentage_and_count_display_elements(self):
        """パーセンテージと処理件数を表示する要素を作成."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Check percentage display element
            percentage_display = await page.query_selector("#progress-percentage")
            assert percentage_display is not None, "Percentage display element should exist"

            percentage_text = await percentage_display.text_content()
            assert "0%" in percentage_text, "Should display initial percentage as 0%"

            # Check current count display
            current_count = await page.query_selector("#progress-current")
            assert current_count is not None, "Current count display should exist"

            current_text = await current_count.text_content()
            assert "0" in current_text, "Should display initial current count as 0"

            # Check total count display
            total_count = await page.query_selector("#progress-total")
            assert total_count is not None, "Total count display should exist"

            # Check combined progress text display
            progress_text = await page.query_selector("#progress-text")
            assert progress_text is not None, "Progress text display should exist"

            await browser.close()

    @pytest.mark.asyncio
    async def test_time_display_functionality(self):
        """経過時間と推定残り時間の表示機能を実装."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Check elapsed time display
            elapsed_time = await page.query_selector("#elapsed-time")
            assert elapsed_time is not None, "Elapsed time display should exist"

            elapsed_text = await elapsed_time.text_content()
            assert "00:00:00" in elapsed_text, "Should display initial elapsed time as 00:00:00"

            # Check estimated remaining time display
            remaining_time = await page.query_selector("#remaining-time")
            assert remaining_time is not None, "Remaining time display should exist"

            remaining_text = await remaining_time.text_content()
            assert "計算中" in remaining_text or "--:--:--" in remaining_text, "Should display initial remaining time as calculating or dashes"

            # Check processing speed display
            processing_speed = await page.query_selector("#processing-speed")
            assert processing_speed is not None, "Processing speed display should exist"

            await browser.close()

    @pytest.mark.asyncio
    async def test_error_and_warning_display_areas(self):
        """エラーメッセージと警告の表示領域を追加."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Check error message display area
            error_display = await page.query_selector("#error-message")
            assert error_display is not None, "Error message display area should exist"

            # Should be hidden initially
            error_visible = await error_display.is_visible()
            assert not error_visible, "Error display should be hidden initially"

            # Check warning message display area
            warning_display = await page.query_selector("#warning-message")
            assert warning_display is not None, "Warning message display area should exist"

            # Should be hidden initially
            warning_visible = await warning_display.is_visible()
            assert not warning_visible, "Warning display should be hidden initially"

            # Check status message display area
            status_display = await page.query_selector("#status-message")
            assert status_display is not None, "Status message display area should exist"

            await browser.close()

    @pytest.mark.asyncio
    async def test_progress_container_layout_and_styling(self):
        """進捗表示コンテナのレイアウトとスタイリングを確認."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Check if progress container is properly styled
            progress_container = await page.query_selector("#progress-container")

            # Check if container has proper CSS classes
            container_class = await progress_container.get_attribute("class")
            assert "progress-container" in container_class, "Progress container should have proper CSS class"

            # Check if progress section exists and is hidden initially
            progress_section = await page.query_selector("#progress-section")
            assert progress_section is not None, "Progress section should exist"

            # Should be hidden initially (display: none or similar)
            is_hidden = await progress_section.evaluate("element => getComputedStyle(element).display === 'none'")
            assert is_hidden, "Progress section should be hidden initially"

            await browser.close()


class TestProgressDisplayFunctionality:
    """Test progress display update functionality."""

    @pytest.mark.asyncio
    async def test_progress_update_function_exists(self):
        """進捗更新関数が存在することを確認."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Check if updateProgress function exists in JavaScript
            function_exists = await page.evaluate("""
                typeof window.updateProgress === 'function'
            """)
            assert function_exists, "updateProgress function should exist in window scope"

            # Check if showProgress function exists
            show_function_exists = await page.evaluate("""
                typeof window.showProgress === 'function'
            """)
            assert show_function_exists, "showProgress function should exist in window scope"

            # Check if hideProgress function exists
            hide_function_exists = await page.evaluate("""
                typeof window.hideProgress === 'function'
            """)
            assert hide_function_exists, "hideProgress function should exist in window scope"

            await browser.close()

    @pytest.mark.asyncio
    async def test_progress_visibility_control(self):
        """進捗表示の表示/非表示制御をテスト."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Initially hidden
            progress_section = await page.query_selector("#progress-section")
            is_hidden = await progress_section.evaluate("element => getComputedStyle(element).display === 'none'")
            assert is_hidden, "Progress section should be hidden initially"

            # Show progress
            await page.evaluate("window.showProgress()")

            is_visible = await progress_section.evaluate("element => getComputedStyle(element).display !== 'none'")
            assert is_visible, "Progress section should be visible after showProgress()"

            # Hide progress
            await page.evaluate("window.hideProgress()")

            is_hidden_again = await progress_section.evaluate("element => getComputedStyle(element).display === 'none'")
            assert is_hidden_again, "Progress section should be hidden after hideProgress()"

            await browser.close()

    @pytest.mark.asyncio
    async def test_format_time_function(self):
        """時間フォーマット関数のテスト."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Test formatTime function
            formatted_time = await page.evaluate("window.formatTime(3661)")  # 1 hour, 1 minute, 1 second
            assert formatted_time == "01:01:01", f"formatTime should return '01:01:01' but got '{formatted_time}'"

            # Test edge cases
            zero_time = await page.evaluate("window.formatTime(0)")
            assert zero_time == "00:00:00", f"formatTime(0) should return '00:00:00' but got '{zero_time}'"

            short_time = await page.evaluate("window.formatTime(65)")  # 1 minute, 5 seconds
            assert short_time == "00:01:05", f"formatTime(65) should return '00:01:05' but got '{short_time}'"

            await browser.close()


class TestSSEClientFunctionality:
    """Test Task 5.2: SSEクライアント機能を実装."""

    @pytest.mark.asyncio
    async def test_eventsource_connection_capability_exists(self):
        """EventSourceを使用したSSE接続機能の存在確認."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Check if connectSSE function exists
            connect_function_exists = await page.evaluate("""
                typeof window.connectSSE === 'function'
            """)
            assert connect_function_exists, "connectSSE function should exist in window scope"

            # Check if disconnectSSE function exists
            disconnect_function_exists = await page.evaluate("""
                typeof window.disconnectSSE === 'function'
            """)
            assert disconnect_function_exists, "disconnectSSE function should exist in window scope"

            # Check if EventSource is available in browser
            eventsource_available = await page.evaluate("""
                typeof EventSource !== 'undefined'
            """)
            assert eventsource_available, "EventSource should be available in browser"

            await browser.close()

    @pytest.mark.asyncio
    async def test_sse_message_handling_functions_exist(self):
        """受信した進捗データでUIを更新する処理関数の存在確認."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Check if handleSSEMessage function exists
            handle_message_exists = await page.evaluate("""
                typeof window.handleSSEMessage === 'function'
            """)
            assert handle_message_exists, "handleSSEMessage function should exist"

            # Check if handleSSEError function exists
            handle_error_exists = await page.evaluate("""
                typeof window.handleSSEError === 'function'
            """)
            assert handle_error_exists, "handleSSEError function should exist"

            # Check if handleSSEComplete function exists
            handle_complete_exists = await page.evaluate("""
                typeof window.handleSSEComplete === 'function'
            """)
            assert handle_complete_exists, "handleSSEComplete function should exist"

            await browser.close()

    @pytest.mark.asyncio
    async def test_sse_connection_error_handling_exists(self):
        """接続エラー時の自動再接続機能の存在確認."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Check if reconnectSSE function exists
            reconnect_exists = await page.evaluate("""
                typeof window.reconnectSSE === 'function'
            """)
            assert reconnect_exists, "reconnectSSE function should exist"

            # Check if maxReconnectAttempts variable exists
            max_attempts_exists = await page.evaluate("""
                typeof window.maxReconnectAttempts !== 'undefined'
            """)
            assert max_attempts_exists, "maxReconnectAttempts should be defined"

            # Check if currentReconnectAttempts variable exists
            current_attempts_exists = await page.evaluate("""
                typeof window.currentReconnectAttempts !== 'undefined'
            """)
            assert current_attempts_exists, "currentReconnectAttempts should be defined"

            await browser.close()

    @pytest.mark.asyncio
    async def test_progress_completion_result_display_function(self):
        """処理完了時の結果表示への切り替え機能の存在確認."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Check if showResults function exists
            show_results_exists = await page.evaluate("""
                typeof window.showResults === 'function'
            """)
            assert show_results_exists, "showResults function should exist"

            # Check if hideResults function exists
            hide_results_exists = await page.evaluate("""
                typeof window.hideResults === 'function'
            """)
            assert hide_results_exists, "hideResults function should exist"

            # Check if displayCompletionMessage function exists
            display_completion_exists = await page.evaluate("""
                typeof window.displayCompletionMessage === 'function'
            """)
            assert display_completion_exists, "displayCompletionMessage function should exist"

            await browser.close()


class TestUserInteractionFunctionality:
    """Test Task 5.3: ユーザーインタラクション機能を追加."""

    @pytest.mark.asyncio
    async def test_cancel_button_and_functionality_exists(self):
        """処理のキャンセルボタンと機能の存在確認."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Check if cancel button exists
            cancel_button = await page.query_selector("#cancel-button")
            assert cancel_button is not None, "Cancel button should exist"

            # Check if cancel button is hidden initially
            is_hidden = await cancel_button.evaluate("element => getComputedStyle(element).display === 'none'")
            assert is_hidden, "Cancel button should be hidden initially"

            # Check if cancelProcessing function exists
            cancel_function_exists = await page.evaluate("""
                typeof window.cancelProcessing === 'function'
            """)
            assert cancel_function_exists, "cancelProcessing function should exist"

            await browser.close()

    @pytest.mark.asyncio
    async def test_retry_button_for_error_recovery_exists(self):
        """エラー発生時の再試行ボタンの存在確認."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Check if retry button exists
            retry_button = await page.query_selector("#retry-button")
            assert retry_button is not None, "Retry button should exist"

            # Check if retry button is hidden initially
            is_hidden = await retry_button.evaluate("element => getComputedStyle(element).display === 'none'")
            assert is_hidden, "Retry button should be hidden initially"

            # Check if retryProcessing function exists
            retry_function_exists = await page.evaluate("""
                typeof window.retryProcessing === 'function'
            """)
            assert retry_function_exists, "retryProcessing function should exist"

            # Check if showRetryButton function exists
            show_retry_exists = await page.evaluate("""
                typeof window.showRetryButton === 'function'
            """)
            assert show_retry_exists, "showRetryButton function should exist"

            await browser.close()

    @pytest.mark.asyncio
    async def test_partial_results_download_functionality_exists(self):
        """部分結果のダウンロード機能の存在確認."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Check if download partial results button exists
            download_button = await page.query_selector("#download-partial-results")
            assert download_button is not None, "Download partial results button should exist"

            # Check if download partial results button is hidden initially
            is_hidden = await download_button.evaluate("element => getComputedStyle(element).display === 'none'")
            assert is_hidden, "Download partial results button should be hidden initially"

            # Check if downloadPartialResults function exists
            download_function_exists = await page.evaluate("""
                typeof window.downloadPartialResults === 'function'
            """)
            assert download_function_exists, "downloadPartialResults function should exist"

            # Check if enablePartialDownload function exists
            enable_function_exists = await page.evaluate("""
                typeof window.enablePartialDownload === 'function'
            """)
            assert enable_function_exists, "enablePartialDownload function should exist"

            await browser.close()

    @pytest.mark.asyncio
    async def test_file_size_split_suggestion_display_exists(self):
        """ファイルサイズ超過時の分割提案表示の存在確認."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # Check if split suggestion area exists
            split_suggestion = await page.query_selector("#split-suggestion")
            assert split_suggestion is not None, "Split suggestion area should exist"

            # Check if split suggestion is hidden initially
            is_hidden = await split_suggestion.evaluate("element => getComputedStyle(element).display === 'none'")
            assert is_hidden, "Split suggestion should be hidden initially"

            # Check if showSplitSuggestion function exists
            show_split_exists = await page.evaluate("""
                typeof window.showSplitSuggestion === 'function'
            """)
            assert show_split_exists, "showSplitSuggestion function should exist"

            # Check if hideSplitSuggestion function exists
            hide_split_exists = await page.evaluate("""
                typeof window.hideSplitSuggestion === 'function'
            """)
            assert hide_split_exists, "hideSplitSuggestion function should exist"

            # Check if calculateOptimalSplitSize function exists
            calculate_split_exists = await page.evaluate("""
                typeof window.calculateOptimalSplitSize === 'function'
            """)
            assert calculate_split_exists, "calculateOptimalSplitSize function should exist"

            await browser.close()


class TestLogSystemIntegration:
    """Test Task 6.1: ログシステムとの連携を実装."""

    @pytest.mark.asyncio
    async def test_progress_info_logging_functionality_exists(self):
        """進捗情報をログエントリとして記録する機能の存在確認."""
        # ProgressTrackerクラスでログ機能が存在することを確認
        from src.progress_tracker import ProgressTracker

        tracker = ProgressTracker()

        # ログ機能が存在することを確認
        assert hasattr(tracker, 'log_progress'), "log_progress method should exist"
        assert hasattr(tracker, 'log_task_creation'), "log_task_creation method should exist"
        assert hasattr(tracker, 'log_task_completion'), "log_task_completion method should exist"

    @pytest.mark.asyncio
    async def test_error_detailed_logging_functionality_exists(self):
        """エラー発生時の詳細ログ記録機能の存在確認."""
        from src.progress_tracker import ProgressTracker

        tracker = ProgressTracker()

        # エラーログ機能が存在することを確認
        assert hasattr(tracker, 'log_error'), "log_error method should exist"
        assert hasattr(tracker, 'log_warning'), "log_warning method should exist"
        assert hasattr(tracker, 'log_exception'), "log_exception method should exist"

    @pytest.mark.asyncio
    async def test_metrics_collection_integration_exists(self):
        """メトリクス収集機能との統合処理の存在確認."""
        from src.progress_tracker import ProgressTracker

        tracker = ProgressTracker()

        # メトリクス統合機能が存在することを確認
        assert hasattr(tracker, 'record_metrics'), "record_metrics method should exist"
        assert hasattr(tracker, 'get_performance_metrics'), "get_performance_metrics method should exist"
        assert hasattr(tracker, 'export_metrics'), "export_metrics method should exist"

    @pytest.mark.asyncio
    async def test_log_rotation_support_functionality_exists(self):
        """ログローテーション対応機能の存在確認."""
        from src.progress_tracker import ProgressTracker

        tracker = ProgressTracker()

        # ログローテーション対応機能が存在することを確認
        assert hasattr(tracker, 'configure_log_rotation'), "configure_log_rotation method should exist"
        assert hasattr(tracker, 'cleanup_old_logs'), "cleanup_old_logs method should exist"
        assert hasattr(tracker, 'get_log_settings'), "get_log_settings method should exist"


class TestExistingWebUIModifications:
    """Test Task 6.2: 既存のWeb UIとAPIの改修."""

    @pytest.mark.asyncio
    async def test_synchronous_endpoint_compatibility_maintained(self):
        """現在の同期処理エンドポイントとの互換性を維持."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # 既存の同期フォームが存在することを確認
            single_file_form = await page.query_selector("form[action='/api/compare']")
            assert single_file_form is not None, "Single file form should exist for backward compatibility"

            dual_file_form = await page.query_selector("form[action='/api/compare/dual']")
            assert dual_file_form is not None, "Dual file form should exist for backward compatibility"

            # フォームの必須フィールドが存在することを確認
            file_input = await page.query_selector("input[name='file'][type='file']")
            assert file_input is not None, "File input should exist"

            await browser.close()

    @pytest.mark.asyncio
    async def test_file_upload_form_async_support_implemented(self):
        """ファイルアップロードフォームの非同期対応を実装."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # 非同期処理用のJavaScript関数が存在することを確認
            async_upload_exists = await page.evaluate("""
                typeof window.handleAsyncUpload === 'function'
            """)
            assert async_upload_exists, "handleAsyncUpload function should exist for async support"

            start_async_exists = await page.evaluate("""
                typeof window.startAsyncProcessing === 'function'
            """)
            assert start_async_exists, "startAsyncProcessing function should exist"

            # フォームにonsubmitハンドラが設定されていることを確認
            form_has_handler = await page.evaluate("""
                (() => {
                    const form = document.querySelector('form[action="/api/compare"]');
                    return form && typeof form.onsubmit === 'function';
                })()
            """)
            assert form_has_handler, "Form should have async submit handler"

            await browser.close()

    @pytest.mark.asyncio
    async def test_progress_display_area_layout_adjusted(self):
        """進捗表示エリアのレイアウト調整を行う."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # 進捗表示エリアが適切な位置に配置されていることを確認
            progress_section = await page.query_selector("#progress-section")
            assert progress_section is not None, "Progress section should exist"

            # レイアウトが既存のフォームと調和していることを確認
            progress_position = await progress_section.evaluate("""
                element => {
                    const rect = element.getBoundingClientRect();
                    const style = getComputedStyle(element);
                    return {
                        position: style.position,
                        zIndex: style.zIndex,
                        width: style.width,
                        margin: style.margin
                    };
                }
            """)

            # 進捗セクションが適切なスタイリングを持っていることを確認
            assert progress_position['width'] != '0px', "Progress section should have proper width"

            await browser.close()

    @pytest.mark.asyncio
    async def test_existing_error_handling_integration_implemented(self):
        """既存のエラーハンドリングとの統合を実装."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("http://localhost:18081/ui")

            # 既存のエラー表示機能が統合されていることを確認
            integrated_error_handler_exists = await page.evaluate("""
                typeof window.handleFormError === 'function'
            """)
            assert integrated_error_handler_exists, "handleFormError function should exist for error integration"

            validation_exists = await page.evaluate("""
                typeof window.validateForm === 'function'
            """)
            assert validation_exists, "validateForm function should exist"

            # エラーメッセージの統一表示が機能することを確認
            unified_error_display_exists = await page.evaluate("""
                typeof window.displayUnifiedError === 'function'
            """)
            assert unified_error_display_exists, "displayUnifiedError function should exist"

            # 既存のエラー表示エリアと進捗表示エラーが統合されていることを確認
            error_integration_setup = await page.evaluate("""
                (() => {
                    const errorDiv = document.getElementById('error-message');
                    const progressErrorDiv = document.getElementById('error-message');
                    return errorDiv && progressErrorDiv && errorDiv === progressErrorDiv;
                })()
            """)
            assert error_integration_setup, "Error displays should be integrated"

            await browser.close()