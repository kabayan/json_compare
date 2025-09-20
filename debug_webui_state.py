#!/usr/bin/env python3
"""
WebUIのデバッグ - 状態確認
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_webui_state():
    """WebUIの状態をデバッグ"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print("=== WebUI状態デバッグ ===")

            # WebUIにアクセス
            print("1. WebUIにアクセス中...")
            await page.goto("http://localhost:18081/ui")
            await page.wait_for_load_state("networkidle")

            # 初期状態のスクリーンショット
            await page.screenshot(path="/home/kabayan/workspace/json_compare/debug_initial.png")

            # 2ファイル比較ボタンをクリック
            print("2. 2ファイル比較ボタンをクリック中...")
            dual_button = await page.wait_for_selector('button[data-mode="dual"]')
            await dual_button.click()

            # クリック後のスクリーンショット
            await page.screenshot(path="/home/kabayan/workspace/json_compare/debug_after_click.png")

            # 明示的にdualモードに切り替え
            print("3. 明示的にdualモードに切り替え...")
            await page.evaluate('switchMode("dual")')
            await page.wait_for_timeout(1000)

            # 切り替え後のスクリーンショット
            await page.screenshot(path="/home/kabayan/workspace/json_compare/debug_after_switch.png")

            # フォームの状態を確認
            print("4. フォームの状態を確認中...")

            # dual formがactiveクラスを持っているか確認
            dual_form = await page.query_selector('.mode-form[data-mode="dual"]')
            if dual_form:
                classes = await dual_form.get_attribute('class')
                print(f"Dual form classes: {classes}")
            else:
                print("Dual form not found")

            # buttonの状態も確認
            dual_button_after = await page.query_selector('button[data-mode="dual"]')
            if dual_button_after:
                button_classes = await dual_button_after.get_attribute('class')
                print(f"Dual button classes: {button_classes}")

            # file1要素の状態を詳しく確認
            file1 = await page.query_selector('#file1')
            if file1:
                print("file1要素が見つかりました")

                # 表示状態確認
                is_visible = await file1.is_visible()
                print(f"file1 is_visible: {is_visible}")

                # CSS確認
                styles = await page.evaluate('''(element) => {
                    const computedStyles = window.getComputedStyle(element);
                    return {
                        display: computedStyles.display,
                        visibility: computedStyles.visibility,
                        opacity: computedStyles.opacity
                    };
                }''', file1)
                print(f"file1 styles: {styles}")

                # 親要素の状態確認
                parent = await page.evaluate('(element) => element.parentElement', file1)
                if parent:
                    parent_styles = await page.evaluate('''(element) => {
                        const computedStyles = window.getComputedStyle(element);
                        return {
                            display: computedStyles.display,
                            visibility: computedStyles.visibility,
                            opacity: computedStyles.opacity
                        };
                    }''', parent)
                    print(f"file1 parent styles: {parent_styles}")

            else:
                print("file1要素が見つかりません")

            # currentModeの確認
            current_mode = await page.evaluate('window.currentMode')
            print(f"Current mode: {current_mode}")

        except Exception as e:
            print(f"デバッグエラー: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_webui_state())