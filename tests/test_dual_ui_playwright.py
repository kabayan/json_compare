"""
PlaywrightによるWeb UI（2ファイル比較機能）のE2Eテスト
"""

import os
import json
import tempfile
import asyncio
import subprocess
import time
from pathlib import Path
import pytest
from playwright.async_api import async_playwright


class TestDualFileUIWithPlaywright:
    """2ファイル比較UIのE2Eテスト"""

    @classmethod
    def setup_class(cls):
        """APIサーバーを起動"""
        cls.server_process = subprocess.Popen(
            ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "18081"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(3)  # サーバーの起動を待つ

    @classmethod
    def teardown_class(cls):
        """APIサーバーを停止"""
        if hasattr(cls, 'server_process'):
            cls.server_process.terminate()
            cls.server_process.wait()

    @pytest.mark.asyncio
    async def test_tab_switching(self):
        """タブ切り替え機能のテスト"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # UIを開く
                await page.goto("http://localhost:18081/ui")
                await page.wait_for_load_state("networkidle")

                # 初期状態の確認（単一ファイルモードがアクティブ）
                single_tab = page.locator('[data-mode="single"]')
                dual_tab = page.locator('[data-mode="dual"]')

                assert await single_tab.evaluate("el => el.classList.contains('active')") == True
                assert await dual_tab.evaluate("el => el.classList.contains('active')") == False

                # 単一ファイルフォームが表示されている
                single_form = page.locator('#uploadForm')
                dual_form = page.locator('#dualForm')

                assert await single_form.evaluate("el => el.classList.contains('active')") == True
                assert await dual_form.evaluate("el => el.classList.contains('active')") == False

                # 2ファイルモードに切り替え
                await dual_tab.click()
                await page.wait_for_timeout(500)

                # タブの状態確認
                assert await single_tab.evaluate("el => el.classList.contains('active')") == False
                assert await dual_tab.evaluate("el => el.classList.contains('active')") == True

                # フォームの表示確認
                assert await single_form.evaluate("el => el.classList.contains('active')") == False
                assert await dual_form.evaluate("el => el.classList.contains('active')") == True

                # 単一ファイルモードに戻す
                await single_tab.click()
                await page.wait_for_timeout(500)

                # 元の状態に戻ったことを確認
                assert await single_tab.evaluate("el => el.classList.contains('active')") == True
                assert await dual_tab.evaluate("el => el.classList.contains('active')") == False

                print("✅ タブ切り替えテスト成功")

            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_single_file_upload(self):
        """単一ファイルアップロードのテスト"""
        # テストファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            test_data = [
                {"inference1": "テキスト1", "inference2": "テキスト1"},
                {"inference1": "テキスト2", "inference2": "テキスト2の修正版"}
            ]
            for item in test_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            test_file = f.name

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # UIを開く
                await page.goto("http://localhost:18081/ui")
                await page.wait_for_load_state("networkidle")

                # ファイルを選択
                file_input = page.locator('#file')
                await file_input.set_input_files(test_file)

                # ファイルが選択されたことを確認
                file_label = page.locator('#fileLabel')
                label_text = await file_label.text_content()
                assert "✅" in label_text
                assert ".jsonl" in label_text

                # フォームを送信
                submit_button = page.locator('#submitButton')
                await submit_button.click()

                # 処理中表示を待つ
                loading = page.locator('#loading')
                await page.wait_for_selector('#loading.active', timeout=5000)

                # 結果表示を待つ
                result_container = page.locator('#resultContainer')
                await page.wait_for_selector('#resultContainer.active', timeout=30000)

                # 結果タイトルを確認
                result_title = page.locator('#resultTitle')
                title_text = await result_title.text_content()
                assert "✅" in title_text or "完了" in title_text

                # 結果内容が表示されていることを確認
                result_content = page.locator('#resultContent')
                content_text = await result_content.text_content()
                assert "score" in content_text or "total_lines" in content_text

                print("✅ 単一ファイルアップロードテスト成功")

            finally:
                await browser.close()
                os.unlink(test_file)

    @pytest.mark.asyncio
    async def test_dual_file_upload(self):
        """2ファイルアップロードのテスト"""
        # テストファイル1を作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            test_data1 = [
                {"id": 1, "inference": "最初のテキスト", "score": 0.8},
                {"id": 2, "inference": "二番目のテキスト", "score": 0.9}
            ]
            for item in test_data1:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            test_file1 = f.name

        # テストファイル2を作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            test_data2 = [
                {"id": 1, "inference": "最初のテキスト", "score": 0.85},
                {"id": 2, "inference": "二番目のテキスト修正版", "score": 0.88}
            ]
            for item in test_data2:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            test_file2 = f.name

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # UIを開く
                await page.goto("http://localhost:18081/ui")
                await page.wait_for_load_state("networkidle")

                # 2ファイルモードに切り替え
                dual_tab = page.locator('[data-mode="dual"]')
                await dual_tab.click()
                await page.wait_for_timeout(500)

                # ファイル1を選択
                file1_input = page.locator('#file1')
                await file1_input.set_input_files(test_file1)

                # ファイル2を選択
                file2_input = page.locator('#file2')
                await file2_input.set_input_files(test_file2)

                # ファイルが選択されたことを確認
                file1_label = page.locator('#file1Label')
                file2_label = page.locator('#file2Label')

                label1_text = await file1_label.text_content()
                label2_text = await file2_label.text_content()

                assert "✅" in label1_text
                assert "✅" in label2_text

                # 列名の確認（デフォルトはinference）
                column_input = page.locator('#column')
                column_value = await column_input.input_value()
                assert column_value == "inference"

                # フォームを送信
                submit_button = page.locator('#dualSubmitButton')
                await submit_button.click()

                # 処理中表示を待つ
                loading = page.locator('#loading')
                await page.wait_for_selector('#loading.active', timeout=5000)

                # 結果表示を待つ（最大60秒）
                result_container = page.locator('#resultContainer')
                await page.wait_for_selector('#resultContainer.active', timeout=60000)

                # 結果タイトルを確認
                result_title = page.locator('#resultTitle')
                title_text = await result_title.text_content()
                assert "✅" in title_text or "2ファイル" in title_text or "完了" in title_text

                # 結果内容が表示されていることを確認
                result_content = page.locator('#resultContent')
                content_text = await result_content.text_content()

                # メタデータの確認
                assert "_metadata" in content_text
                assert "column_compared" in content_text or "source_files" in content_text

                print("✅ 2ファイルアップロードテスト成功")

            finally:
                await browser.close()
                os.unlink(test_file1)
                os.unlink(test_file2)

    @pytest.mark.asyncio
    async def test_custom_column_name(self):
        """カスタム列名指定のテスト"""
        # テストファイル1を作成（カスタム列名）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            test_data1 = [
                {"id": 1, "custom_text": "カスタム列のテキスト1"},
                {"id": 2, "custom_text": "カスタム列のテキスト2"}
            ]
            for item in test_data1:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            test_file1 = f.name

        # テストファイル2を作成（カスタム列名）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            test_data2 = [
                {"id": 1, "custom_text": "カスタム列のテキスト1"},
                {"id": 2, "custom_text": "異なるカスタム列のテキスト"}
            ]
            for item in test_data2:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            test_file2 = f.name

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # UIを開く
                await page.goto("http://localhost:18081/ui")
                await page.wait_for_load_state("networkidle")

                # 2ファイルモードに切り替え
                dual_tab = page.locator('[data-mode="dual"]')
                await dual_tab.click()
                await page.wait_for_timeout(500)

                # ファイルを選択
                file1_input = page.locator('#file1')
                await file1_input.set_input_files(test_file1)

                file2_input = page.locator('#file2')
                await file2_input.set_input_files(test_file2)

                # カスタム列名を入力
                column_input = page.locator('#column')
                await column_input.fill("custom_text")

                # フォームを送信
                submit_button = page.locator('#dualSubmitButton')
                await submit_button.click()

                # 処理中表示を待つ
                loading = page.locator('#loading')
                await page.wait_for_selector('#loading.active', timeout=5000)

                # 結果表示を待つ
                result_container = page.locator('#resultContainer')
                await page.wait_for_selector('#resultContainer.active', timeout=60000)

                # 結果内容を確認
                result_content = page.locator('#resultContent')
                content_text = await result_content.text_content()

                # カスタム列名がメタデータに含まれていることを確認
                assert "custom_text" in content_text

                print("✅ カスタム列名指定テスト成功")

            finally:
                await browser.close()
                os.unlink(test_file1)
                os.unlink(test_file2)

    @pytest.mark.asyncio
    async def test_download_buttons(self):
        """ダウンロードボタンの表示テスト"""
        # テストファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            test_data = [
                {"inference1": "テキスト", "inference2": "テキスト"}
            ]
            for item in test_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            test_file = f.name

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # UIを開く
                await page.goto("http://localhost:18081/ui")
                await page.wait_for_load_state("networkidle")

                # ファイルをアップロード
                file_input = page.locator('#file')
                await file_input.set_input_files(test_file)

                # フォームを送信
                submit_button = page.locator('#submitButton')
                await submit_button.click()

                # 結果表示を待つ
                await page.wait_for_selector('#resultContainer.active', timeout=30000)

                # ダウンロードボタンが表示されることを確認
                download_buttons = page.locator('#downloadButtons')
                await page.wait_for_selector('#downloadButtons', state='visible', timeout=5000)

                # JSONダウンロードボタンの確認
                json_button = page.locator('#downloadJsonButton')
                assert await json_button.is_visible()
                json_text = await json_button.text_content()
                assert "JSON" in json_text

                # CSVダウンロードボタンの確認
                csv_button = page.locator('#downloadCsvButton')
                assert await csv_button.is_visible()
                csv_text = await csv_button.text_content()
                assert "CSV" in csv_text

                print("✅ ダウンロードボタン表示テスト成功")

            finally:
                await browser.close()
                os.unlink(test_file)


def run_tests():
    """テストを実行"""
    import subprocess

    # Playwrightのブラウザをインストール（必要な場合）
    print("Playwrightブラウザのセットアップ...")
    subprocess.run(["playwright", "install", "chromium"], check=True)

    # テストを実行
    print("\n" + "=" * 60)
    print("PlaywrightによるWeb UIテストを開始")
    print("=" * 60 + "\n")

    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    run_tests()