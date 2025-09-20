"""シンプルな単一ファイルテスト"""

import asyncio
import tempfile
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def test_simple_single_file():
    """単一ファイル比較のシンプルテスト"""

    # テスト用ファイル準備
    test_data = [
        {"text": "Hello world", "inference": "greeting"},
        {"text": "Good morning", "inference": "greeting"}
    ]

    temp_dir = Path(tempfile.gettempdir()) / "simple_test"
    temp_dir.mkdir(exist_ok=True)

    file_path = temp_dir / "test.jsonl"

    with open(file_path, 'w', encoding='utf-8') as f:
        for item in test_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # エラーやログを捕捉
        console_logs = []
        network_responses = []

        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text
        }))

        page.on("response", lambda response: network_responses.append({
            "url": response.url,
            "status": response.status
        }))

        try:
            print("=== 単一ファイル比較テスト ===")

            # WebUIページに移動
            await page.goto("http://localhost:18081/ui")
            await page.wait_for_load_state('networkidle')
            print("✅ ページ読み込み完了")

            # デフォルトで単一ファイルフォームが表示されているはず
            upload_form_visible = await page.locator('#uploadForm').is_visible()
            print(f"uploadForm表示状態: {upload_form_visible}")

            # ファイルアップロード
            file_input = page.locator('#file')
            await file_input.set_input_files(str(file_path))
            print("✅ ファイルアップロード完了")

            # 送信ボタンクリック
            submit_button = page.locator('#uploadForm button[type="submit"]')
            print("送信ボタンをクリック...")
            await submit_button.click()

            # 少し待機
            await page.wait_for_timeout(10000)

            print(f"\n=== コンソールログ ({len(console_logs)}件) ===")
            for log in console_logs[-5:]:
                print(f"{log['type']}: {log['text']}")

            print(f"\n=== ネットワークレスポンス (最新5件) ===")
            for res in network_responses[-5:]:
                print(f"{res['status']} {res['url']}")

            # タスクIDを探す
            task_id = None
            for log in console_logs:
                if "Started polling for task:" in log['text']:
                    task_id = log['text'].split(": ")[-1]
                    break

            if task_id:
                print(f"\nタスクID: {task_id}")
                # タスクの状況を直接確認
                import subprocess
                result = subprocess.run(
                    ["curl", "-s", f"http://localhost:18081/api/progress/{task_id}"],
                    capture_output=True, text=True
                )
                print(f"タスク状況: {result.stdout}")
            else:
                print("タスクIDが見つかりませんでした")

        except Exception as e:
            print(f"エラー: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_simple_single_file())