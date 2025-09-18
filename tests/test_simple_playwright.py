#!/usr/bin/env python3
"""
シンプルなPlaywrightテスト - UIの基本動作を確認
"""

import asyncio
from playwright.async_api import async_playwright
import tempfile
import json
import os


async def test_basic_ui_load():
    """UIページが読み込めることを確認"""
    print("=" * 60)
    print("基本的なUI読み込みテスト")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # UIを開く
            print("\n1. UIページにアクセス...")
            await page.goto("http://localhost:18081/ui", timeout=10000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            print("✅ ページが正常に読み込まれました")

            # タイトルを確認
            title = await page.title()
            print(f"ページタイトル: {title}")

            # h1タグの内容を確認
            h1_element = page.locator("h1")
            if await h1_element.count() > 0:
                h1_text = await h1_element.text_content()
                print(f"ヘッダーテキスト: {h1_text}")

            # タブボタンの存在を確認（別のセレクタで試す）
            print("\n2. タブ要素の確認...")

            # タブボタンをクラス名で探す
            tab_buttons = page.locator(".tab-button")
            tab_count = await tab_buttons.count()
            print(f"タブボタンの数: {tab_count}")

            if tab_count > 0:
                for i in range(tab_count):
                    tab_text = await tab_buttons.nth(i).text_content()
                    print(f"  タブ {i + 1}: {tab_text}")
            else:
                print("❗ タブボタンが見つかりません")

            # フォーム要素の確認
            print("\n3. フォーム要素の確認...")
            forms = page.locator("form")
            form_count = await forms.count()
            print(f"フォームの数: {form_count}")

            # ファイル入力の確認
            file_inputs = page.locator("input[type='file']")
            file_input_count = await file_inputs.count()
            print(f"ファイル入力フィールドの数: {file_input_count}")

            print("\n✅ 基本的な要素確認が完了しました")

        except Exception as e:
            print(f"\n❌ エラー発生: {e}")
            # スクリーンショットを撮る
            await page.screenshot(path="ui_error.png")
            print("エラー時のスクリーンショットを ui_error.png に保存しました")

            # ページのHTMLを出力（デバッグ用）
            content = await page.content()
            with open("ui_debug.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("ページのHTMLを ui_debug.html に保存しました")

        finally:
            await browser.close()


async def test_single_file_upload():
    """単一ファイルアップロードの簡単なテスト"""
    print("\n" + "=" * 60)
    print("単一ファイルアップロードテスト")
    print("=" * 60)

    # テストファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        test_data = [
            {"inference1": "テスト1", "inference2": "テスト1"}
        ]
        for item in test_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        test_file = f.name

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # UIを開く
            print("\n1. UIページにアクセス...")
            await page.goto("http://localhost:18081/ui", timeout=10000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            print("✅ ページが読み込まれました")

            # 単一ファイルモードの確認（デフォルト）
            print("\n2. 単一ファイルモードの確認...")

            # uploadFormが存在するか確認
            upload_form = page.locator("#uploadForm")
            if await upload_form.count() > 0:
                print("✅ アップロードフォームが見つかりました")

                # ファイル入力フィールドを探す
                file_input = page.locator("#file")
                if await file_input.count() > 0:
                    print("✅ ファイル入力フィールドが見つかりました")

                    # ファイルを設定
                    print(f"\n3. ファイルを選択: {test_file}")
                    await file_input.set_input_files(test_file)

                    # 送信ボタンを探す
                    submit_button = page.locator("#submitButton")
                    if await submit_button.count() > 0:
                        print("✅ 送信ボタンが見つかりました")

                        # ボタンのテキストを確認
                        button_text = await submit_button.text_content()
                        print(f"ボタンテキスト: {button_text}")

                        # フォームを送信
                        print("\n4. フォームを送信...")
                        await submit_button.click()

                        # 結果を待つ（少し待機）
                        await page.wait_for_timeout(3000)

                        # 結果表示の確認
                        result_container = page.locator("#resultContainer")
                        if await result_container.count() > 0:
                            # 結果が表示されているか確認（activeクラス）
                            is_active = await result_container.evaluate("el => el.classList.contains('active')")
                            if is_active:
                                print("✅ 結果が表示されました")

                                # 結果内容を取得
                                result_content = page.locator("#resultContent")
                                if await result_content.count() > 0:
                                    text = await result_content.text_content()
                                    if text:
                                        print(f"結果の一部: {text[:100]}...")
                            else:
                                print("❗ 結果コンテナはあるが、表示されていません")
                    else:
                        print("❗ 送信ボタンが見つかりません")
                else:
                    print("❗ ファイル入力フィールドが見つかりません")
            else:
                print("❗ アップロードフォームが見つかりません")

            print("\n✅ テスト完了")

        except Exception as e:
            print(f"\n❌ エラー発生: {e}")
            await page.screenshot(path="upload_error.png")
            print("エラー時のスクリーンショットを upload_error.png に保存しました")

        finally:
            await browser.close()
            os.unlink(test_file)


async def main():
    """メインテスト実行"""
    print("\n" + "🎭" * 30)
    print("PlaywrightによるUIテスト開始")
    print("🎭" * 30 + "\n")

    # 基本的なUI読み込みテスト
    await test_basic_ui_load()

    # ファイルアップロードテスト
    await test_single_file_upload()

    print("\n" + "=" * 60)
    print("すべてのテストが完了しました")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())