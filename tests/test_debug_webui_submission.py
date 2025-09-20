"""WebUI送信デバッグテスト"""

import asyncio
import tempfile
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def debug_webui_submission():
    """WebUI送信の詳細デバッグ"""

    # テスト用ファイル準備
    test_data_1 = [
        {"text": "Hello world", "inference": "greeting"},
        {"text": "Good morning", "inference": "greeting"}
    ]

    test_data_2 = [
        {"text": "Hello world", "inference": "greeting"},
        {"text": "Good morning", "inference": "salutation"}
    ]

    temp_dir = Path(tempfile.gettempdir()) / "debug_test"
    temp_dir.mkdir(exist_ok=True)

    file1_path = temp_dir / "test1.jsonl"
    file2_path = temp_dir / "test2.jsonl"

    with open(file1_path, 'w', encoding='utf-8') as f:
        for item in test_data_1:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    with open(file2_path, 'w', encoding='utf-8') as f:
        for item in test_data_2:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # エラーやログを捕捉
        console_logs = []
        network_requests = []
        network_responses = []

        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text,
            "location": msg.location
        }))

        page.on("request", lambda request: network_requests.append({
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers)
        }))

        page.on("response", lambda response: network_responses.append({
            "url": response.url,
            "status": response.status,
            "status_text": response.status_text
        }))

        try:
            print("=== WebUI送信詳細デバッグ ===")

            # WebUIページに移動
            await page.goto("http://localhost:18081/ui")
            await page.wait_for_load_state('networkidle')
            print("✅ ページ読み込み完了")

            # 2ファイル比較モードに切り替え
            dual_mode_button = page.locator('button:has-text("📑 2ファイル比較")')
            await dual_mode_button.click()
            await page.wait_for_timeout(500)
            print("✅ 2ファイル比較モードに切り替え")

            # dualFormが表示されているか確認
            dual_form_visible = await page.locator('#dualForm').is_visible()
            print(f"dualForm表示状態: {dual_form_visible}")

            # ファイルアップロード
            file1_input = page.locator('#file1')
            file2_input = page.locator('#file2')

            await file1_input.set_input_files(str(file1_path))
            await file2_input.set_input_files(str(file2_path))
            print("✅ ファイルアップロード完了")

            # フォーム状態確認
            form_data = await page.evaluate("""
                () => {
                    const form = document.getElementById('dualForm');
                    const file1 = document.getElementById('file1');
                    const file2 = document.getElementById('file2');
                    const submitBtn = form.querySelector('button[type="submit"]');

                    return {
                        form_exists: !!form,
                        file1_has_files: file1.files.length > 0,
                        file2_has_files: file2.files.length > 0,
                        submit_btn_enabled: !submitBtn.disabled,
                        submit_btn_visible: window.getComputedStyle(submitBtn).display !== 'none'
                    };
                }
            """)
            print(f"フォーム状態: {form_data}")

            # 送信ボタンクリック
            submit_button = page.locator('#dualForm button[type="submit"]')
            print("送信ボタンをクリック...")
            await submit_button.click()

            # 少し待機してリクエストを確認
            await page.wait_for_timeout(5000)

            print(f"\n=== コンソールログ ({len(console_logs)}件) ===")
            for log in console_logs[-5:]:  # 最新5件
                print(f"{log['type']}: {log['text']}")

            print(f"\n=== ネットワークリクエスト ({len(network_requests)}件) ===")
            for req in network_requests[-10:]:  # 最新10件
                print(f"{req['method']} {req['url']}")

            print(f"\n=== ネットワークレスポンス ({len(network_responses)}件) ===")
            for res in network_responses[-10:]:  # 最新10件
                print(f"{res['status']} {res['url']}")

            # 進捗表示要素の確認
            progress_elements = await page.evaluate("""
                () => {
                    const progress = document.getElementById('progress-container');
                    const progressBar = document.getElementById('progress-bar');
                    const resultContainer = document.getElementById('resultContainer');

                    return {
                        progress_container_exists: !!progress,
                        progress_container_visible: progress ? window.getComputedStyle(progress).display !== 'none' : false,
                        progress_bar_exists: !!progressBar,
                        result_container_exists: !!resultContainer,
                        result_container_visible: resultContainer ? window.getComputedStyle(resultContainer).display !== 'none' : false
                    };
                }
            """)
            print(f"\n=== 進捗表示要素状態 ===")
            for key, value in progress_elements.items():
                print(f"{key}: {value}")

            # 現在のページのURLと状態
            current_url = page.url
            print(f"\n現在のURL: {current_url}")

        except Exception as e:
            print(f"エラー: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_webui_submission())