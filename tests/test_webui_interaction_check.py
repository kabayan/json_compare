"""WebUI相互作用確認テスト"""

import asyncio
from playwright.async_api import async_playwright

async def check_webui_interaction():
    """WebUIの相互作用を詳しく確認"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # WebUIページに移動
            await page.goto("http://localhost:18081/ui")
            await page.wait_for_load_state('networkidle')

            print("=== WebUI初期状態確認 ===")

            # 初期状態での要素の可視性確認
            elements_to_check = [
                "#uploadForm",
                "#dualForm",
                "#uploadForm button[type='submit']",
                "#dualForm button[type='submit']"
            ]

            for selector in elements_to_check:
                element = page.locator(selector)
                count = await element.count()
                if count > 0:
                    is_visible = await element.is_visible()
                    print(f"{selector}: 存在={count}, 表示={is_visible}")
                else:
                    print(f"{selector}: 存在しない")

            # ページのタブやセレクタなどを探す
            print("\n=== タブ・モード切り替え要素確認 ===")

            # 一般的なタブ・モード切り替え要素を確認
            tab_selectors = [
                ".tab", ".tabs", "[role='tab']",
                ".mode-selector", ".toggle",
                "input[type='radio']",
                ".nav", ".navbar", ".navigation",
                "button", "a"
            ]

            for selector in tab_selectors:
                elements = page.locator(selector)
                count = await elements.count()
                if count > 0:
                    print(f"{selector}: {count}個見つかりました")
                    # テキスト内容を確認（最初の3個まで）
                    for i in range(min(count, 3)):
                        try:
                            text = await elements.nth(i).text_content()
                            if text and len(text.strip()) > 0:
                                print(f"  - {i}: '{text.strip()[:50]}'")
                        except:
                            pass

            # JavaScript console.logを確認
            print("\n=== JavaScript実行とイベント確認 ===")

            # ページでJavaScriptを実行してフォーム状態を確認
            js_result = await page.evaluate("""
                () => {
                    return {
                        uploadFormVisible: document.getElementById('uploadForm') ?
                            window.getComputedStyle(document.getElementById('uploadForm')).display !== 'none' : false,
                        dualFormVisible: document.getElementById('dualForm') ?
                            window.getComputedStyle(document.getElementById('dualForm')).display !== 'none' : false,
                        allForms: Array.from(document.querySelectorAll('form')).map(f => ({
                            id: f.id,
                            display: window.getComputedStyle(f).display,
                            className: f.className
                        }))
                    };
                }
            """)

            print(f"JavaScript確認結果: {js_result}")

            # clickableな要素でdualやtwinが含まれるものを探す
            print("\n=== dual/twin関連のクリック可能要素確認 ===")

            dual_elements = await page.evaluate("""
                () => {
                    const clickableElements = document.querySelectorAll('button, a, input, label, [onclick], [data-*]');
                    const dualRelated = [];

                    clickableElements.forEach((el, index) => {
                        const text = el.textContent || el.innerText || '';
                        const attrs = Array.from(el.attributes).map(attr => `${attr.name}="${attr.value}"`).join(' ');

                        if (text.toLowerCase().includes('dual') ||
                            text.toLowerCase().includes('twin') ||
                            text.toLowerCase().includes('2') ||
                            text.toLowerCase().includes('二') ||
                            text.toLowerCase().includes('ふた') ||
                            attrs.toLowerCase().includes('dual')) {
                            dualRelated.push({
                                tag: el.tagName,
                                text: text.trim(),
                                attributes: attrs,
                                index: index
                            });
                        }
                    });

                    return dualRelated;
                }
            """)

            for element in dual_elements:
                print(f"  - {element['tag']}: '{element['text'][:50]}' | {element['attributes'][:100]}")

        except Exception as e:
            print(f"エラー: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(check_webui_interaction())