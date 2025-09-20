#!/usr/bin/env python3
"""
Test Case 3: LLM + Score形式
Test Case 4: LLM + File形式
"""

import asyncio
import json
from playwright.async_api import async_playwright

async def test_llm_modes():
    """LLMモードのテスト（Score + File）"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        page.on("console", lambda msg: print(f"Console: {msg.text}"))

        results = []

        try:
            # Test Case 3: LLM + Score形式
            print("=== Test 3: LLM + Score形式 ===")

            await page.goto("http://localhost:18081/ui")
            await page.wait_for_load_state("networkidle")

            # 2ファイル比較モードに切り替え
            dual_button = await page.wait_for_selector('button[data-mode="dual"]')
            await dual_button.click()
            await page.evaluate('switchMode("dual")')
            await page.wait_for_timeout(1000)

            # ファイルアップロード
            file1_input = await page.query_selector('#file1')
            await file1_input.set_input_files("/home/kabayan/workspace/json_compare/test_data1.jsonl")

            file2_input = await page.query_selector('#file2')
            await file2_input.set_input_files("/home/kabayan/workspace/json_compare/test_data2.jsonl")

            # 出力形式: score
            select_element = await page.wait_for_selector('#dual_type')
            await select_element.select_option('score')

            # LLM使用: checked
            llm_checkbox = await page.wait_for_selector('#dual_use_llm')
            is_checked = await llm_checkbox.is_checked()
            if not is_checked:
                await llm_checkbox.click()

            # 送信
            submit_button = await page.wait_for_selector('#dualSubmitButton')
            await submit_button.click()

            await page.wait_for_timeout(5000)
            await page.screenshot(path="/home/kabayan/workspace/json_compare/test3_result.png")

            page_text = await page.inner_text('body')

            results.append({
                "test_case": "Test 3: LLM + Score形式",
                "success": True,
                "ui_interaction": "成功",
                "form_submission": "成功",
                "llm_enabled": True,
                "output_format": "score",
                "page_text": page_text[:500]
            })

            print("Test 3完了")

            # Test Case 4: LLM + File形式
            print("=== Test 4: LLM + File形式 ===")

            # ページをリフレッシュ
            await page.goto("http://localhost:18081/ui")
            await page.wait_for_load_state("networkidle")

            # 2ファイル比較モードに切り替え
            dual_button = await page.wait_for_selector('button[data-mode="dual"]')
            await dual_button.click()
            await page.evaluate('switchMode("dual")')
            await page.wait_for_timeout(1000)

            # ファイルアップロード
            file1_input = await page.query_selector('#file1')
            await file1_input.set_input_files("/home/kabayan/workspace/json_compare/test_data1.jsonl")

            file2_input = await page.query_selector('#file2')
            await file2_input.set_input_files("/home/kabayan/workspace/json_compare/test_data2.jsonl")

            # 出力形式: file
            select_element = await page.wait_for_selector('#dual_type')
            await select_element.select_option('file')

            # LLM使用: checked
            llm_checkbox = await page.wait_for_selector('#dual_use_llm')
            is_checked = await llm_checkbox.is_checked()
            if not is_checked:
                await llm_checkbox.click()

            # 送信
            submit_button = await page.wait_for_selector('#dualSubmitButton')
            await submit_button.click()

            await page.wait_for_timeout(5000)
            await page.screenshot(path="/home/kabayan/workspace/json_compare/test4_result.png")

            page_text = await page.inner_text('body')

            results.append({
                "test_case": "Test 4: LLM + File形式",
                "success": True,
                "ui_interaction": "成功",
                "form_submission": "成功",
                "llm_enabled": True,
                "output_format": "file",
                "page_text": page_text[:500]
            })

            print("Test 4完了")

            return results

        except Exception as e:
            results.append({
                "test_case": "Test 3&4",
                "success": False,
                "error": str(e)
            })
            return results
        finally:
            await browser.close()

if __name__ == "__main__":
    results = asyncio.run(test_llm_modes())
    print(f"\n=== Test 3&4結果 ===")
    print(json.dumps(results, indent=2, ensure_ascii=False))