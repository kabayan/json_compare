#!/usr/bin/env python3
"""
WebUIの構造を調査
"""

import asyncio
from playwright.async_api import async_playwright

async def inspect_dual_compare_page():
    """2ファイル比較ページの構造を調査"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # WebUIにアクセス
            print("WebUIにアクセス中...")
            await page.goto("http://localhost:18081/ui")
            await page.wait_for_load_state("networkidle")

            # 2ファイル比較ボタンをクリック
            print("2ファイル比較ボタンをクリック中...")
            dual_button = await page.wait_for_selector('button:has-text("📑 2ファイル比較")')
            await dual_button.click()
            await page.wait_for_load_state("networkidle")

            # ページの構造を調査
            print("ページの構造を調査中...")

            # すべてのファイル入力要素を取得
            file_inputs = await page.query_selector_all('input[type="file"]')
            print(f"ファイル入力要素数: {len(file_inputs)}")

            for i, input_element in enumerate(file_inputs):
                # 要素の属性を取得
                id_attr = await input_element.get_attribute('id')
                name_attr = await input_element.get_attribute('name')
                class_attr = await input_element.get_attribute('class')
                accept_attr = await input_element.get_attribute('accept')

                print(f"Input {i+1}: id='{id_attr}', name='{name_attr}', class='{class_attr}', accept='{accept_attr}'")

            # dual_typeセレクトボックスを確認
            dual_type = await page.query_selector('#dual_type')
            if dual_type:
                print("dual_typeセレクトボックスが見つかりました")
            else:
                print("dual_typeセレクトボックスが見つかりません")

            # dual_use_llmチェックボックスを確認
            dual_use_llm = await page.query_selector('#dual_use_llm')
            if dual_use_llm:
                print("dual_use_llmチェックボックスが見つかりました")
            else:
                print("dual_use_llmチェックボックスが見つかりません")

            # フォーム全体のHTML構造を取得
            form = await page.query_selector('form')
            if form:
                form_html = await form.inner_html()
                print("フォームHTML構造:")
                print(form_html[:1000] + "..." if len(form_html) > 1000 else form_html)

        except Exception as e:
            print(f"調査エラー: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_dual_compare_page())