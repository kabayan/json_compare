#!/usr/bin/env python3
"""Improved CSV download tests with better wait conditions"""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest
from playwright.async_api import async_playwright, expect


async def wait_for_result(page, timeout=70000):
    """Helper function to wait for processing result"""
    # Wait for loading to disappear
    loading = page.locator("#loading")

    try:
        # Check if loading appears
        await loading.wait_for(state="visible", timeout=3000)
        print("Loading state detected")

        # Wait for loading to disappear
        await loading.wait_for(state="hidden", timeout=timeout)
        print("Loading completed")
    except:
        print("Loading state not detected or already completed")

    # Wait for result container to be active
    await page.wait_for_function(
        """
        () => {
            const container = document.getElementById('resultContainer');
            if (!container) return false;
            const isActive = container.classList.contains('active');
            const hasContent = container.querySelector('#resultContent')?.textContent?.length > 0;
            return isActive || hasContent;
        }
        """,
        timeout=timeout
    )

    return True


@pytest.mark.asyncio
async def test_csv_download_functionality():
    """Test CSV download functionality with improved wait conditions"""

    # Create test JSONL file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        test_data = [
            {"inference1": "テスト文章1", "inference2": "テスト文書1"},
            {"inference1": "機械学習は便利", "inference2": "機械学習は有用"},
            {"inference1": "自然言語処理", "inference2": "NLP処理"}
        ]
        for item in test_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        temp_file = f.name

    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-dev-shm-usage']
            )
            context = await browser.new_context()
            page = await context.new_page()

            # Add console logging for debugging
            page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
            page.on("pageerror", lambda exc: print(f"Browser error: {exc}"))

            # Navigate to UI
            await page.goto("http://localhost:18081/ui")

            # Verify page loaded
            assert "JSON Compare" in await page.title()

            # Upload file
            file_input = page.locator('input[type="file"]')
            await file_input.set_input_files(temp_file)

            # Wait for file selection to register
            await page.wait_for_timeout(500)

            # Submit form
            submit_button = page.locator('#submitButton')
            await submit_button.click()

            # Wait for processing to complete
            await wait_for_result(page)

            # Check if download buttons are visible
            download_buttons = page.locator('#downloadButtons')

            # Wait for buttons container to be visible
            try:
                await download_buttons.wait_for(state="visible", timeout=5000)
                print("Download buttons are visible")
            except:
                # If buttons not visible, check if result has error
                result_container = page.locator('#resultContainer')
                is_error = await result_container.evaluate("el => el.classList.contains('error')")

                if is_error:
                    error_text = await page.locator('#resultContent').inner_text()
                    print(f"Processing error: {error_text}")
                    pytest.fail(f"Processing failed with error: {error_text}")
                else:
                    # Try to get result content for debugging
                    result_text = await page.locator('#resultContent').inner_text()
                    print(f"Result content: {result_text[:200]}...")
                    pytest.fail("Download buttons did not appear after processing")

            # Verify both buttons exist
            json_button = page.locator('#downloadJsonButton')
            csv_button = page.locator('#downloadCsvButton')

            await expect(json_button).to_be_visible()
            await expect(csv_button).to_be_visible()

            # Check button text
            json_text = await json_button.inner_text()
            csv_text = await csv_button.inner_text()

            assert 'JSON' in json_text, "JSON button text not found"
            assert 'CSV' in csv_text, "CSV button text not found"

            print("✅ CSV download buttons test passed")

            await browser.close()

    finally:
        # Cleanup
        Path(temp_file).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_csv_download_with_download():
    """Test actual CSV download functionality"""

    # Create test JSONL file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        test_data = [
            {"inference1": "サンプルテキスト1", "inference2": "サンプル文書1"},
            {"inference1": "サンプルテキスト2", "inference2": "サンプル文書2"}
        ]
        for item in test_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        temp_file = f.name

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            # Create context with download handling
            with tempfile.TemporaryDirectory() as download_dir:
                context = await browser.new_context(
                    accept_downloads=True
                )
                page = await context.new_page()

                # Navigate and upload
                await page.goto("http://localhost:18081/ui")
                await page.locator('input[type="file"]').set_input_files(temp_file)
                await page.wait_for_timeout(500)

                # Select score mode
                await page.locator('input[value="score"]').check()

                # Submit
                await page.locator('#submitButton').click()

                # Wait for result
                await wait_for_result(page)

                # Wait for download buttons
                await page.locator('#downloadButtons').wait_for(state="visible", timeout=5000)

                # Click CSV download button
                csv_button = page.locator('#downloadCsvButton')

                # Handle download
                async with page.expect_download() as download_info:
                    await csv_button.click()
                download = await download_info.value

                # Verify download
                assert download.suggested_filename.endswith('.csv'), "Downloaded file should be CSV"
                assert 'result_' in download.suggested_filename, "Filename should contain 'result_'"

                # Save and check content
                download_path = Path(download_dir) / download.suggested_filename
                await download.save_as(download_path)

                # Read CSV content
                csv_content = download_path.read_text(encoding='utf-8-sig')  # Remove BOM if present

                # Verify CSV content
                assert len(csv_content) > 0, "CSV file should not be empty"
                assert '項目' in csv_content or 'スコア' in csv_content, "CSV should contain Japanese headers"

                print("✅ CSV download with actual file test passed")

                await browser.close()

    finally:
        # Cleanup
        Path(temp_file).unlink(missing_ok=True)


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_csv_download_functionality())