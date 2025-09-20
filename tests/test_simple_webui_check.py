"""シンプルなWebUI構造確認テスト"""

import asyncio
from playwright.async_api import async_playwright

async def check_webui_structure():
    """WebUIの構造を確認"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # WebUIページに移動
            await page.goto("http://localhost:18081/ui")
            await page.wait_for_load_state('networkidle')

            print("=== WebUI構造確認 ===")

            # ページタイトル確認
            title = await page.title()
            print(f"ページタイトル: {title}")

            # 主要な要素を確認
            elements = {
                "form": "form",
                "mode_radio": "input[name='mode']",
                "comparison_radio": "input[name='comparison_type']",
                "output_radio": "input[name='output_type']",
                "file_inputs": "input[type='file']",
                "submit_button": "button[type='submit']"
            }

            for name, selector in elements.items():
                count = await page.locator(selector).count()
                print(f"{name}: {count}個見つかりました")

                if count > 0:
                    # 値やテキストを確認
                    if name == "mode_radio":
                        for i in range(count):
                            value = await page.locator(selector).nth(i).get_attribute('value')
                            print(f"  - mode option {i}: {value}")
                    elif name == "comparison_radio":
                        for i in range(count):
                            value = await page.locator(selector).nth(i).get_attribute('value')
                            print(f"  - comparison_type option {i}: {value}")
                    elif name == "output_radio":
                        for i in range(count):
                            value = await page.locator(selector).nth(i).get_attribute('value')
                            print(f"  - output_type option {i}: {value}")

            # HTMLの詳細を表示
            form1_html = await page.locator('#uploadForm').inner_html()
            form2_html = await page.locator('#dualForm').inner_html()
            print(f"\nuploadForm HTML（最初の500文字）:\n{form1_html[:500]}")
            print(f"\ndualForm HTML（最初の500文字）:\n{form2_html[:500]}")

            # すべてのinput要素を確認
            all_inputs = page.locator('input')
            input_count = await all_inputs.count()
            print(f"\n全input要素数: {input_count}")

            for i in range(min(input_count, 10)):  # 最初の10個まで表示
                input_elem = all_inputs.nth(i)
                input_type = await input_elem.get_attribute('type')
                input_name = await input_elem.get_attribute('name')
                input_value = await input_elem.get_attribute('value')
                input_id = await input_elem.get_attribute('id')
                print(f"  input {i}: type={input_type}, name={input_name}, value={input_value}, id={input_id}")

        except Exception as e:
            print(f"エラー: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(check_webui_structure())