#!/usr/bin/env python3
"""Playwright tests for Web UI"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, Page, expect


class TestWebUI:
    """Web UI tests using Playwright"""

    @pytest_asyncio.fixture(scope="session")
    async def api_server(self):
        """API server URL for testing"""
        base_url = "http://localhost:18081"
        return base_url

    @pytest_asyncio.fixture
    async def browser(self):
        """Create browser instance"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            yield browser
            await browser.close()

    @pytest_asyncio.fixture
    async def page(self, browser, api_server):
        """Create browser page"""
        context = await browser.new_context()
        page = await context.new_page()
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

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for item in content:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            temp_path = f.name

        yield temp_path

        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

    @pytest.mark.asyncio
    async def test_ui_page_loads(self, page: Page):
        """Test that UI page loads correctly"""
        # Check page title
        assert await page.title() == "JSON Compare - ファイルアップロード"

        # Check main heading
        heading = page.locator("h1")
        await expect(heading).to_have_text("🔍 JSON Compare")

        # Check subtitle
        subtitle = page.locator(".subtitle")
        await expect(subtitle).to_have_text("JSONLファイルの類似度を計算します")

        # Check form elements exist
        await expect(page.locator("#file")).to_be_attached()
        await expect(page.locator("#type")).to_be_visible()
        await expect(page.locator("#gpu")).to_be_visible()
        await expect(page.locator("#submitButton")).to_be_visible()

    @pytest.mark.asyncio
    async def test_file_selection_updates_ui(self, page: Page, sample_jsonl_file):
        """Test that file selection updates the UI"""
        # Initial state
        file_label = page.locator("#fileLabel")
        await expect(file_label).to_contain_text("📁 クリックしてファイルを選択")

        # Select file
        file_input = page.locator("#file")
        await file_input.set_input_files(sample_jsonl_file)

        # Check that label updated
        filename = os.path.basename(sample_jsonl_file)
        await expect(file_label).to_contain_text("✅")
        await expect(file_label).to_contain_text(filename)

    @pytest.mark.asyncio
    async def test_form_submission_score_type(self, page: Page, sample_jsonl_file):
        """Test form submission with score type"""
        # Select file
        await page.locator("#file").set_input_files(sample_jsonl_file)

        # Select score type (default)
        await page.select_option("#type", "score")

        # Submit form
        await page.click("#submitButton")

        # Wait for loading to appear and disappear
        loading = page.locator("#loading")
        await expect(loading).to_have_class("loading active")

        # Wait for result
        result_container = page.locator("#resultContainer")
        await expect(result_container).to_have_class("result-container active", timeout=70000)

        # Check success message
        result_title = page.locator("#resultTitle")
        await expect(result_title).to_contain_text("✅ 処理完了")

        # Check download button appears
        download_button = page.locator("#downloadButton")
        await expect(download_button).to_be_visible()

    @pytest.mark.asyncio
    async def test_form_submission_file_type(self, page: Page, sample_jsonl_file):
        """Test form submission with file type"""
        # Select file
        await page.locator("#file").set_input_files(sample_jsonl_file)

        # Select file type
        await page.select_option("#type", "file")

        # Submit form
        await page.click("#submitButton")

        # Wait for result
        result_container = page.locator("#resultContainer")
        await expect(result_container).to_have_class("result-container active", timeout=70000)

        # Check that result contains array
        result_content = page.locator("#resultContent")
        content = await result_content.inner_text()
        assert content.startswith("[")  # File type returns array

    @pytest.mark.asyncio
    async def test_gpu_checkbox(self, page: Page, sample_jsonl_file):
        """Test GPU checkbox functionality"""
        # Select file
        await page.locator("#file").set_input_files(sample_jsonl_file)

        # Check GPU checkbox
        gpu_checkbox = page.locator("#gpu")
        await gpu_checkbox.check()

        # Submit form
        await page.click("#submitButton")

        # Wait for result
        result_container = page.locator("#resultContainer")
        await expect(result_container).to_have_class("result-container active", timeout=70000)

        # Check result contains GPU metadata
        result_content = page.locator("#resultContent")
        content = await result_content.inner_text()
        assert '"gpu_used": true' in content or '"gpu": true' in content

    @pytest.mark.asyncio
    async def test_error_handling_invalid_file(self, page: Page):
        """Test error handling for invalid file type"""
        # Create invalid file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is not a JSONL file")
            temp_path = f.name

        try:
            # Select invalid file
            await page.locator("#file").set_input_files(temp_path)

            # Submit form
            await page.click("#submitButton")

            # Wait for error
            result_container = page.locator("#resultContainer")
            await expect(result_container).to_have_class("result-container error active", timeout=30000)

            # Check error message
            result_title = page.locator("#resultTitle")
            await expect(result_title).to_contain_text("❌ エラー")

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @pytest.mark.asyncio
    async def test_loading_state(self, page: Page, sample_jsonl_file):
        """Test loading state during processing"""
        # Select file
        await page.locator("#file").set_input_files(sample_jsonl_file)

        # Submit form
        submit_button = page.locator("#submitButton")
        await submit_button.click()

        # Check button is disabled during processing
        await expect(submit_button).to_be_disabled()

        # Check loading indicator appears
        loading = page.locator("#loading")
        await expect(loading).to_have_class("loading active")

        # Wait for completion
        await expect(loading).not_to_have_class("loading active", timeout=70000)

        # Check button is re-enabled
        await expect(submit_button).not_to_be_disabled()

    @pytest.mark.asyncio
    async def test_download_functionality(self, page: Page, sample_jsonl_file):
        """Test result download functionality"""
        # Select file and submit
        await page.locator("#file").set_input_files(sample_jsonl_file)
        await page.click("#submitButton")

        # Wait for result
        result_container = page.locator("#resultContainer")
        await expect(result_container).to_have_class("result-container active", timeout=70000)

        # Check download buttons
        download_buttons = page.locator("#downloadButtons")
        await expect(download_buttons).to_be_visible()

        # Check both JSON and CSV buttons exist
        json_button = page.locator("#downloadJsonButton")
        csv_button = page.locator("#downloadCsvButton")
        await expect(json_button).to_be_visible()
        await expect(csv_button).to_be_visible()

        # Check download attributes for JSON button
        href = await json_button.get_attribute("href")
        assert href.startswith("blob:")

        download_name = await json_button.get_attribute("download")
        assert download_name.startswith("result_")
        assert download_name.endswith(".json")

    @pytest.mark.asyncio
    async def test_responsive_design(self, page: Page):
        """Test responsive design for mobile"""
        # Set mobile viewport
        await page.set_viewport_size({"width": 375, "height": 667})

        # Check that elements are still visible
        await expect(page.locator("h1")).to_be_visible()
        await expect(page.locator("#uploadForm")).to_be_visible()
        await expect(page.locator("#submitButton")).to_be_visible()

        # Check container has appropriate padding
        container = page.locator(".container")
        await expect(container).to_be_visible()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])