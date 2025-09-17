#!/usr/bin/env python3
"""CSV ダウンロード機能のPlaywrightテスト"""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest
from playwright.async_api import async_playwright, expect


@pytest.mark.asyncio
async def test_csv_download_buttons():
    """CSV ダウンロードボタンの表示と動作テスト"""
    # テスト用JSONLファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
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
            # ブラウザ起動
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # UIページにアクセス
            await page.goto("http://localhost:18081/ui")

            # ページタイトルの確認
            assert "JSON Compare" in await page.title()

            # ファイルをアップロード
            file_input = page.locator('input[type="file"]')
            await file_input.set_input_files(temp_file)

            # ファイルが選択されたことを確認（JavaScriptイベントの処理を待つ）
            await page.wait_for_timeout(500)

            # 送信ボタンをクリック
            submit_button = page.locator('#submitButton')
            await submit_button.click()

            # 処理完了を待つ
            result_container = page.locator('#resultContainer')
            await expect(result_container).to_have_class('result-container active', timeout=60000)

            # ダウンロードボタンが表示されることを確認
            download_buttons = page.locator('#downloadButtons')
            await expect(download_buttons).to_be_visible()

            # JSONダウンロードボタンの確認
            json_button = page.locator('#downloadJsonButton')
            await expect(json_button).to_be_visible()
            await expect(json_button).to_contain_text('JSON形式でダウンロード')

            # CSVダウンロードボタンの確認
            csv_button = page.locator('#downloadCsvButton')
            await expect(csv_button).to_be_visible()
            await expect(csv_button).to_contain_text('CSV形式でダウンロード')

            await browser.close()

    finally:
        # テストファイルのクリーンアップ
        Path(temp_file).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_csv_download_score_mode():
    """scoreモードでのCSVダウンロードテスト"""
    # テスト用JSONLファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        test_data = [
            {"inference1": "テスト文章1", "inference2": "テスト文書1"},
            {"inference1": "機械学習は便利", "inference2": "機械学習は有用"},
        ]
        for item in test_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        temp_file = f.name

    try:
        async with async_playwright() as p:
            # ブラウザ起動（ダウンロードを処理できるように設定）
            browser = await p.chromium.launch(headless=True)

            # ダウンロードディレクトリを設定
            with tempfile.TemporaryDirectory() as download_dir:
                context = await browser.new_context(
                    accept_downloads=True
                )
                page = await context.new_page()

                # UIページにアクセス
                await page.goto("http://localhost:18081/ui")

                # scoreモードを選択
                score_radio = page.locator('input[value="score"]')
                await score_radio.check()

                # ファイルをアップロード
                file_input = page.locator('input[type="file"]')
                await file_input.set_input_files(temp_file)

                # 送信ボタンをクリック
                submit_button = page.locator('#submitButton')
                await submit_button.click()

                # 処理完了を待つ
                result_container = page.locator('#resultContainer')
                await expect(result_container).to_have_class('result-container active', timeout=60000)

                # CSVダウンロードボタンをクリック
                csv_button = page.locator('#downloadCsvButton')

                # ダウンロードをトリガー
                async with page.expect_download() as download_info:
                    await csv_button.click()
                download = await download_info.value

                # ダウンロードファイル名の確認
                assert download.suggested_filename.endswith('.csv')
                assert 'result_' in download.suggested_filename

                # ダウンロードファイルの内容を確認
                download_path = Path(download_dir) / download.suggested_filename
                await download.save_as(download_path)

                # CSVファイルの内容を読み込み
                csv_content = download_path.read_text(encoding='utf-8-sig')  # BOM付きUTF-8

                # CSVの内容を確認
                assert '項目,値' in csv_content
                assert '全体類似度' in csv_content
                assert '平均類似度' in csv_content

                await browser.close()

    finally:
        # テストファイルのクリーンアップ
        Path(temp_file).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_csv_download_file_mode():
    """fileモードでのCSVダウンロードテスト"""
    # テスト用JSONLファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
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
            # ブラウザ起動
            browser = await p.chromium.launch(headless=True)

            # ダウンロードディレクトリを設定
            with tempfile.TemporaryDirectory() as download_dir:
                context = await browser.new_context(
                    accept_downloads=True
                )
                page = await context.new_page()

                # UIページにアクセス
                await page.goto("http://localhost:18081/ui")

                # fileモードを選択
                file_radio = page.locator('input[value="file"]')
                await file_radio.check()

                # ファイルをアップロード
                file_input = page.locator('input[type="file"]')
                await file_input.set_input_files(temp_file)

                # 送信ボタンをクリック
                submit_button = page.locator('#submitButton')
                await submit_button.click()

                # 処理完了を待つ
                result_container = page.locator('#resultContainer')
                await expect(result_container).to_have_class('result-container active', timeout=60000)

                # CSVダウンロードボタンをクリック
                csv_button = page.locator('#downloadCsvButton')

                # ダウンロードをトリガー
                async with page.expect_download() as download_info:
                    await csv_button.click()
                download = await download_info.value

                # ダウンロードファイルの内容を確認
                download_path = Path(download_dir) / download.suggested_filename
                await download.save_as(download_path)

                # CSVファイルの内容を読み込み
                csv_content = download_path.read_text(encoding='utf-8-sig')  # BOM付きUTF-8

                # CSVの内容を確認
                assert '行番号,類似度,推論1,推論2' in csv_content
                assert 'テスト文章1' in csv_content
                assert 'テスト文書1' in csv_content
                assert '機械学習は便利' in csv_content
                assert '機械学習は有用' in csv_content

                await browser.close()

    finally:
        # テストファイルのクリーンアップ
        Path(temp_file).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_both_download_buttons_work():
    """JSONとCSVの両方のダウンロードボタンが機能することを確認"""
    # テスト用JSONLファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        test_data = [
            {"inference1": "テスト1", "inference2": "試験1"},
            {"inference1": "テスト2", "inference2": "試験2"},
        ]
        for item in test_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        temp_file = f.name

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            with tempfile.TemporaryDirectory() as download_dir:
                context = await browser.new_context(
                    accept_downloads=True
                )
                page = await context.new_page()

                # UIページにアクセス
                await page.goto("http://localhost:18081/ui")

                # ファイルをアップロード
                file_input = page.locator('input[type="file"]')
                await file_input.set_input_files(temp_file)

                # 送信ボタンをクリック
                await page.locator('#submitButton').click()

                # 処理完了を待つ
                await expect(page.locator('#resultContainer')).to_have_class(
                    'result-container active', timeout=60000
                )

                # JSONダウンロードボタンのテスト
                async with page.expect_download() as download_info:
                    await page.locator('#downloadJsonButton').click()
                json_download = await download_info.value

                assert json_download.suggested_filename.endswith('.json')
                json_path = Path(download_dir) / json_download.suggested_filename
                await json_download.save_as(json_path)

                # JSONファイルの内容を確認
                json_content = json.loads(json_path.read_text())
                assert isinstance(json_content, (dict, list))

                # CSVダウンロードボタンのテスト
                async with page.expect_download() as download_info:
                    await page.locator('#downloadCsvButton').click()
                csv_download = await download_info.value

                assert csv_download.suggested_filename.endswith('.csv')
                csv_path = Path(download_dir) / csv_download.suggested_filename
                await csv_download.save_as(csv_path)

                # CSVファイルが存在し、内容があることを確認
                csv_content = csv_path.read_text(encoding='utf-8-sig')
                assert len(csv_content) > 0

                await browser.close()

    finally:
        Path(temp_file).unlink(missing_ok=True)


if __name__ == "__main__":
    # テスト実行
    asyncio.run(test_csv_download_buttons())