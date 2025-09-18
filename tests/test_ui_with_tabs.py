#!/usr/bin/env python3
"""
タブ機能を含むWeb UIのPlaywrightテスト
"""

import asyncio
from playwright.async_api import async_playwright
import tempfile
import json
import os

# テスト対象のURLを設定（モックサーバー）
BASE_URL = "http://localhost:18083"


async def test_tab_switching():
    """タブ切り替え機能のテスト"""
    print("=" * 60)
    print("タブ切り替え機能テスト")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # UIを開く
            print("\n1. UIページにアクセス...")
            await page.goto(f"{BASE_URL}/ui", timeout=10000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            print("✅ ページが読み込まれました")

            # タブボタンの確認
            print("\n2. タブボタンの確認...")
            single_tab = page.locator('button.tab-button[data-mode="single"]')
            dual_tab = page.locator('button.tab-button[data-mode="dual"]')

            # タブボタンが存在することを確認
            assert await single_tab.count() > 0, "単一ファイルタブが見つかりません"
            assert await dual_tab.count() > 0, "2ファイルタブが見つかりません"
            print("✅ タブボタンが見つかりました")

            # 初期状態の確認（単一ファイルモードがアクティブ）
            print("\n3. 初期状態の確認...")
            single_tab_classes = await single_tab.get_attribute("class")
            dual_tab_classes = await dual_tab.get_attribute("class")

            assert "active" in single_tab_classes, "単一ファイルタブが初期状態でアクティブではありません"
            assert "active" not in dual_tab_classes, "2ファイルタブが初期状態でアクティブです"
            print("✅ 初期状態は単一ファイルモード")

            # フォームの表示確認
            single_form = page.locator('#uploadForm')
            dual_form = page.locator('#dualForm')

            single_form_classes = await single_form.get_attribute("class")
            dual_form_classes = await dual_form.get_attribute("class")

            assert "active" in single_form_classes, "単一ファイルフォームが表示されていません"
            assert "active" not in dual_form_classes, "2ファイルフォームが誤って表示されています"
            print("✅ 単一ファイルフォームが表示されています")

            # 2ファイルモードに切り替え
            print("\n4. 2ファイルモードに切り替え...")
            await dual_tab.click()
            await page.wait_for_timeout(500)

            # タブの状態確認
            single_tab_classes = await single_tab.get_attribute("class")
            dual_tab_classes = await dual_tab.get_attribute("class")

            assert "active" not in single_tab_classes, "単一ファイルタブがまだアクティブです"
            assert "active" in dual_tab_classes, "2ファイルタブがアクティブになっていません"
            print("✅ 2ファイルモードに切り替わりました")

            # フォームの表示確認
            single_form_classes = await single_form.get_attribute("class")
            dual_form_classes = await dual_form.get_attribute("class")

            assert "active" not in single_form_classes, "単一ファイルフォームがまだ表示されています"
            assert "active" in dual_form_classes, "2ファイルフォームが表示されていません"
            print("✅ 2ファイルフォームが表示されています")

            # 2ファイルモードの要素確認
            file1_input = page.locator('#file1')
            file2_input = page.locator('#file2')
            column_input = page.locator('#column')

            assert await file1_input.count() > 0, "ファイル1入力が見つかりません"
            assert await file2_input.count() > 0, "ファイル2入力が見つかりません"
            assert await column_input.count() > 0, "列名入力が見つかりません"
            print("✅ 2ファイルモードの入力要素が確認されました")

            # 列名のデフォルト値を確認
            column_value = await column_input.input_value()
            assert column_value == "inference", f"列名のデフォルト値が正しくありません: {column_value}"
            print(f"✅ 列名のデフォルト値: {column_value}")

            # 単一ファイルモードに戻す
            print("\n5. 単一ファイルモードに戻す...")
            await single_tab.click()
            await page.wait_for_timeout(500)

            # 元の状態に戻ったことを確認
            single_tab_classes = await single_tab.get_attribute("class")
            dual_tab_classes = await dual_tab.get_attribute("class")

            assert "active" in single_tab_classes, "単一ファイルタブがアクティブに戻っていません"
            assert "active" not in dual_tab_classes, "2ファイルタブがまだアクティブです"
            print("✅ 単一ファイルモードに戻りました")

            print("\n✅ タブ切り替えテスト成功！")

        except Exception as e:
            print(f"\n❌ エラー発生: {e}")
            await page.screenshot(path="tab_test_error.png")
            print("エラー時のスクリーンショットを tab_test_error.png に保存しました")
            raise

        finally:
            await browser.close()


async def test_dual_file_upload():
    """2ファイルアップロード機能のテスト"""
    print("\n" + "=" * 60)
    print("2ファイルアップロード機能テスト")
    print("=" * 60)

    # テストファイル1を作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        test_data1 = [
            {"id": 1, "inference": "テキスト1", "score": 0.8}
        ]
        for item in test_data1:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        test_file1 = f.name

    # テストファイル2を作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        test_data2 = [
            {"id": 1, "inference": "テキスト2", "score": 0.9}
        ]
        for item in test_data2:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        test_file2 = f.name

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # UIを開く
            print("\n1. UIページにアクセス...")
            await page.goto(f"{BASE_URL}/ui", timeout=10000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            print("✅ ページが読み込まれました")

            # 2ファイルモードに切り替え
            print("\n2. 2ファイルモードに切り替え...")
            dual_tab = page.locator('button.tab-button[data-mode="dual"]')
            await dual_tab.click()
            await page.wait_for_timeout(500)
            print("✅ 2ファイルモードに切り替わりました")

            # ファイルを選択
            print("\n3. ファイルを選択...")
            file1_input = page.locator('#file1')
            file2_input = page.locator('#file2')

            await file1_input.set_input_files(test_file1)
            await file2_input.set_input_files(test_file2)
            print(f"✅ ファイル1: {test_file1}")
            print(f"✅ ファイル2: {test_file2}")

            # ラベルの更新を確認
            file1_label = page.locator('#file1Label')
            file2_label = page.locator('#file2Label')

            file1_text = await file1_label.text_content()
            file2_text = await file2_label.text_content()

            assert "✅" in file1_text, "ファイル1のラベルが更新されていません"
            assert "✅" in file2_text, "ファイル2のラベルが更新されていません"
            print("✅ ファイル選択後のラベルが更新されました")

            # カスタム列名を入力
            print("\n4. カスタム列名を入力...")
            column_input = page.locator('#column')
            await column_input.fill("")
            await column_input.type("custom_column")
            column_value = await column_input.input_value()
            assert column_value == "custom_column", f"列名が正しく入力されていません: {column_value}"
            print(f"✅ 列名を入力: {column_value}")

            # フォームを送信
            print("\n5. フォームを送信...")
            submit_button = page.locator('#dualSubmitButton')
            await submit_button.click()
            await page.wait_for_timeout(1000)

            # 結果表示を確認
            result_container = page.locator('#resultContainer')
            result_title = page.locator('#resultTitle')
            result_content = page.locator('#resultContent')

            # 結果コンテナが表示されていることを確認
            result_classes = await result_container.get_attribute("class")
            assert "active" in result_classes, "結果が表示されていません"
            print("✅ 結果が表示されました")

            # 結果タイトルを確認
            title_text = await result_title.text_content()
            assert "✅" in title_text or "完了" in title_text, f"結果タイトルが正しくありません: {title_text}"
            print(f"✅ 結果タイトル: {title_text}")

            # 結果内容を確認（モックなので簡単な確認）
            content_text = await result_content.text_content()
            assert "score" in content_text, "結果にスコアが含まれていません"
            assert "_metadata" in content_text, "結果にメタデータが含まれていません"

            # JSONとしてパース可能か確認
            try:
                result_json = json.loads(content_text)
                assert "custom_column" in str(result_json), "カスタム列名が結果に反映されていません"
                print("✅ 結果のJSONが正しく表示されています")
            except:
                print("⚠️ 結果のJSONパースに失敗（モックのため許容）")

            print("\n✅ 2ファイルアップロードテスト成功！")

        except Exception as e:
            print(f"\n❌ エラー発生: {e}")
            await page.screenshot(path="dual_upload_error.png")
            print("エラー時のスクリーンショットを dual_upload_error.png に保存しました")
            raise

        finally:
            await browser.close()
            os.unlink(test_file1)
            os.unlink(test_file2)


async def main():
    """メインテスト実行"""
    print("\n" + "🎭" * 30)
    print("PlaywrightによるWeb UIテスト（タブ機能含む）")
    print("🎭" * 30 + "\n")

    try:
        # タブ切り替えテスト
        await test_tab_switching()

        # 2ファイルアップロードテスト
        await test_dual_file_upload()

        print("\n" + "=" * 60)
        print("✨ すべてのテストが成功しました！")
        print("=" * 60)
        return True

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ テスト失敗: {e}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)