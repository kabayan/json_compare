#!/usr/bin/env python3
"""Improved Playwright tests for Web UI with better wait conditions"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, Page, expect


class TestWebUIImproved:
    """Improved Web UI tests with robust wait conditions"""

    @pytest_asyncio.fixture(scope="session")
    async def api_server(self):
        """API server URL for testing"""
        return "http://localhost:18081"

    @pytest_asyncio.fixture
    async def browser(self):
        """Create browser instance"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-dev-shm-usage']  # Prevent shared memory issues
            )
            yield browser
            await browser.close()

    @pytest_asyncio.fixture
    async def page(self, browser, api_server):
        """Create browser page"""
        context = await browser.new_context()
        page = await context.new_page()

        # Set up console logging for debugging
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"Browser error: {exc}"))

        await page.goto(f"{api_server}/ui")
        yield page
        await context.close()

    @pytest_asyncio.fixture
    def sample_jsonl_file(self):
        """Create a sample JSONL file for testing"""
        content = [
            {"inference1": "これはテスト文章です", "inference2": "これは試験文書です"},
            {"inference1": "機械学習は便利です", "inference2": "機械学習は有用です"},
            {"inference1": "自然言語処理の技術", "inference2": "NLP技術"}
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            for item in content:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            temp_path = f.name

        yield temp_path

        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

    async def wait_for_processing(self, page: Page, timeout: int = 70000):
        """Wait for file processing to complete"""
        # Wait for loading to appear
        loading = page.locator("#loading")

        try:
            # Wait for loading to have the active class (processing started)
            await loading.wait_for(state="visible", timeout=5000)
            print("Loading indicator appeared")
        except:
            print("Loading indicator did not appear, checking result directly")

        # Wait for result container to become active (success or error)
        result_container = page.locator("#resultContainer")

        # Wait for either success or error state
        await page.wait_for_function(
            """
            () => {
                const container = document.getElementById('resultContainer');
                return container && container.classList.contains('active');
            }
            """,
            timeout=timeout
        )

        # Check if it's an error
        is_error = await result_container.evaluate("el => el.classList.contains('error')")

        if is_error:
            error_text = await page.locator("#resultContent").inner_text()
            print(f"Processing resulted in error: {error_text}")
        else:
            print("Processing completed successfully")

        return not is_error

    @pytest.mark.asyncio
    async def test_ui_page_loads(self, page: Page):
        """Test that UI page loads correctly"""
        # Check page title
        assert await page.title() == "JSON Compare - ファイルアップロード"

        # Check main elements exist
        assert await page.locator("h1").count() == 1
        assert await page.locator("#uploadForm").count() == 1
        assert await page.locator("#submitButton").count() == 1

    @pytest.mark.asyncio
    async def test_file_upload_and_processing(self, page: Page, sample_jsonl_file):
        """Test file upload and processing with improved wait conditions"""
        # Select file
        file_input = page.locator("#file")
        await file_input.set_input_files(sample_jsonl_file)

        # Wait a moment for file selection to register
        await page.wait_for_timeout(500)

        # Submit form
        submit_button = page.locator("#submitButton")
        await submit_button.click()

        # Wait for processing to complete
        success = await self.wait_for_processing(page)

        assert success, "File processing failed"

        # Verify result is displayed
        result_content = page.locator("#resultContent")
        content_text = await result_content.inner_text()

        # Check that result contains expected data
        assert len(content_text) > 0
        assert ("similarity" in content_text.lower() or
                "score" in content_text.lower() or
                "類似" in content_text)

    @pytest.mark.asyncio
    async def test_csv_download_button(self, page: Page, sample_jsonl_file):
        """Test CSV download button appears after processing"""
        # Upload and process file
        await page.locator("#file").set_input_files(sample_jsonl_file)
        await page.wait_for_timeout(500)
        await page.locator("#submitButton").click()

        # Wait for processing
        success = await self.wait_for_processing(page)

        if success:
            # Check download buttons appear
            download_buttons = page.locator("#downloadButtons")
            await expect(download_buttons).to_be_visible(timeout=5000)

            # Check both JSON and CSV buttons exist
            json_button = page.locator("#downloadJsonButton")
            csv_button = page.locator("#downloadCsvButton")

            await expect(json_button).to_be_visible()
            await expect(csv_button).to_be_visible()

            # Check button text
            json_text = await json_button.inner_text()
            csv_text = await csv_button.inner_text()

            assert "JSON" in json_text
            assert "CSV" in csv_text

    @pytest.mark.asyncio
    async def test_gpu_checkbox(self, page: Page):
        """Test GPU checkbox functionality"""
        gpu_checkbox = page.locator("#gpu")

        # Initially unchecked
        assert not await gpu_checkbox.is_checked()

        # Check it
        await gpu_checkbox.check()
        assert await gpu_checkbox.is_checked()

        # Uncheck it
        await gpu_checkbox.uncheck()
        assert not await gpu_checkbox.is_checked()

    @pytest.mark.asyncio
    async def test_error_handling_empty_file(self, page: Page):
        """Test error handling for empty file"""
        # Create empty file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            temp_file = f.name

        try:
            # Upload empty file
            await page.locator("#file").set_input_files(temp_file)
            await page.wait_for_timeout(500)
            await page.locator("#submitButton").click()

            # Wait for processing (should show error)
            success = await self.wait_for_processing(page, timeout=30000)

            # Should fail
            assert not success, "Empty file should result in error"

            # Check error message is displayed
            result_container = page.locator("#resultContainer")
            has_error_class = await result_container.evaluate("el => el.classList.contains('error')")
            assert has_error_class

        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.remove(temp_file)

    @pytest.mark.asyncio
    async def test_form_type_selection(self, page: Page):
        """Test form type dropdown selection"""
        type_select = page.locator('select#type')

        # Default should be score
        selected_value = await type_select.input_value()
        assert selected_value == "score"

        # Select file type
        await type_select.select_option("file")
        selected_value = await type_select.input_value()
        assert selected_value == "file"

        # Select score type again
        await type_select.select_option("score")
        selected_value = await type_select.input_value()
        assert selected_value == "score"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])