#!/usr/bin/env python3
"""
Test Case 2: Embedding + File形式
"""

import asyncio
import json
from playwright.async_api import async_playwright

async def test_embedding_file():
    """Embedding + File形式テスト"""
    async with async_playwright() as p:
        print("=== Test 2: Embedding + File形式 ===")

        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # コンソールエラーを監視
        page.on("console", lambda msg: print(f"Console: {msg.text}"))

        try:
            # 1. WebUIにアクセス
            print("1. WebUIにアクセス中...")
            await page.goto("http://localhost:18081/ui")
            await page.wait_for_load_state("networkidle")

            # 2. 「📑 2ファイル比較」ボタンをクリック
            print("2. 2ファイル比較ボタンをクリック中...")
            dual_button = await page.wait_for_selector('button[data-mode="dual"]')
            await dual_button.click()
            await page.evaluate('switchMode("dual")')
            await page.wait_for_timeout(1000)

            # 3. ファイルアップロード
            print("3. ファイルアップロード中...")
            file1_input = await page.query_selector('#file1')
            await file1_input.set_input_files("/home/kabayan/workspace/json_compare/test_data1.jsonl")

            file2_input = await page.query_selector('#file2')
            await file2_input.set_input_files("/home/kabayan/workspace/json_compare/test_data2.jsonl")

            # 4. 出力形式を選択（file）
            print("4. 出力形式をfileに設定中...")
            select_element = await page.wait_for_selector('#dual_type')
            await select_element.select_option('file')

            # 5. LLM使用チェックボックスを設定（Embedding = unchecked）
            print("5. LLM使用をuncheckedに設定中...")
            llm_checkbox = await page.wait_for_selector('#dual_use_llm')
            is_checked = await llm_checkbox.is_checked()
            if is_checked:
                await llm_checkbox.click()

            # 6. 送信ボタンをクリック
            print("6. 送信ボタンをクリック中...")
            submit_button = await page.wait_for_selector('#dualSubmitButton')
            await submit_button.click()

            # 7. 処理状態を確認
            print("7. 処理状態を確認中...")
            await page.wait_for_timeout(5000)

            # スクリーンショット取得
            await page.screenshot(path="/home/kabayan/workspace/json_compare/test2_result.png")

            page_text = await page.inner_text('body')
            print(f"ページテキスト（一部）: {page_text[:500]}...")

            return {
                "success": True,
                "test_type": "Embedding + File形式",
                "ui_interaction": "成功",
                "form_submission": "成功",
                "page_text": page_text[:1000]
            }

        except Exception as e:
            print(f"テストエラー: {e}")
            return {
                "success": False,
                "error": str(e),
                "test_type": "Embedding + File形式"
            }
        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_embedding_file())
    print(f"\n=== Test 2結果 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))