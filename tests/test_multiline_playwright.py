#!/usr/bin/env python3
"""
Playwright test for multi-line JSONL files (testing auto-format feature)
"""

import asyncio
from playwright.async_api import async_playwright
import os
from pathlib import Path
import json

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


async def test_multiline_dual_upload():
    """Test dual file upload with multi-line JSONL files"""
    print("=" * 60)
    print("マルチラインJSONLファイルでの2ファイル比較テスト")
    print("（自動フォーマット機能のテスト）")
    print("=" * 60)

    # マルチライン形式のテストファイル
    file1_path = PROJECT_ROOT / "datas" / "test_multiline.jsonl"
    file2_path = PROJECT_ROOT / "datas" / "test_multiline2.jsonl"

    # ファイルが存在することを確認
    if not file1_path.exists():
        print(f"❌ ファイル1が見つかりません: {file1_path}")
        return False
    if not file2_path.exists():
        print(f"❌ ファイル2が見つかりません: {file2_path}")
        return False

    # ファイルの行数を確認（マルチライン形式の確認）
    with open(file1_path, 'r') as f:
        lines1 = len(f.readlines())
    with open(file2_path, 'r') as f:
        lines2 = len(f.readlines())

    print(f"\n📁 テストファイル情報:")
    print(f"  ファイル1: {file1_path.name} ({lines1}行)")
    print(f"  ファイル2: {file2_path.name} ({lines2}行)")
    print(f"  ※ 各ファイルは3つのJSONオブジェクトを含む（マルチライン形式）")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # UIを開く
            print("\n1. UIページにアクセス...")
            await page.goto("http://localhost:18081/ui", timeout=10000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            print("✅ ページが読み込まれました")

            # 2ファイルモードに切り替え
            print("\n2. 2ファイルモードに切り替え...")
            dual_tab = page.locator('button[data-mode="dual"]')
            await dual_tab.click()
            await page.wait_for_timeout(500)
            print("✅ 2ファイルモードがアクティブになりました")

            # ファイル1を選択
            print(f"\n3. ファイル1を選択: {file1_path.name}")
            file1_input = page.locator('#file1')
            await file1_input.set_input_files(str(file1_path))

            # ファイル1が選択されたことを確認
            file1_label = page.locator('#file1Label')
            label1_text = await file1_label.text_content()
            print(f"   ラベル: {label1_text}")

            # ファイル2を選択
            print(f"\n4. ファイル2を選択: {file2_path.name}")
            file2_input = page.locator('#file2')
            await file2_input.set_input_files(str(file2_path))

            # ファイル2が選択されたことを確認
            file2_label = page.locator('#file2Label')
            label2_text = await file2_label.text_content()
            print(f"   ラベル: {label2_text}")

            # 列名を確認（デフォルトは inference）
            print("\n5. 比較列名の確認...")
            column_input = page.locator('#column')
            column_value = await column_input.input_value()
            print(f"   列名: {column_value}")

            # フォームを送信
            print("\n6. フォームを送信...")
            submit_button = page.locator('#dualSubmitButton')
            await submit_button.click()

            # 処理中表示を待つ
            print("   処理中...")
            loading = page.locator('#loading')
            try:
                await page.wait_for_selector('#loading.active', timeout=5000)
            except:
                pass  # ロード表示がすぐに消える場合もある

            # 結果表示を待つ（最大30秒）
            print("   結果を待っています（最大30秒）...")
            result_container = page.locator('#resultContainer')
            await page.wait_for_selector('#resultContainer.active', timeout=30000)

            # 結果タイトルを確認
            result_title = page.locator('#resultTitle')
            title_text = await result_title.text_content()
            print(f"\n7. 結果タイトル: {title_text}")

            # 結果内容を取得
            result_content = page.locator('#resultContent')
            content_text = await result_content.text_content()

            # JSONをパース
            try:
                result_json = json.loads(content_text)
                print("\n8. 比較結果:")
                print(f"   - スコア: {result_json.get('score', 'N/A')}")
                print(f"   - 意味: {result_json.get('meaning', 'N/A')}")
                print(f"   - 総行数: {result_json.get('total_lines', 'N/A')}")

                if '_metadata' in result_json:
                    metadata = result_json['_metadata']
                    print(f"\n9. メタデータ:")
                    print(f"   - 比較列: {metadata.get('column_compared', 'N/A')}")
                    print(f"   - 比較行数: {metadata.get('rows_compared', 'N/A')}")
                    print(f"   - GPU使用: {metadata.get('gpu_used', 'N/A')}")
                    print(f"   - 処理時間: {metadata.get('processing_time', 'N/A')}")

                    if 'data_repairs' in metadata:
                        repairs = metadata['data_repairs']
                        print(f"\n10. 🔧 データ自動修復:")
                        print(f"   - ファイル1: {repairs.get('file1', 0)}行修復")
                        print(f"   - ファイル2: {repairs.get('file2', 0)}行修復")

                        if repairs.get('file1', 0) > 0 or repairs.get('file2', 0) > 0:
                            print(f"\n✨ 自動フォーマット機能が正常に動作しました！")
                            print(f"   マルチライン形式のJSONLファイルが自動的に修正されました")

                print("\n✅ 2ファイル比較が正常に完了しました！")
                return True
            except json.JSONDecodeError as e:
                print(f"❌ 結果のパースに失敗: {e}")
                print(f"結果の一部: {content_text[:500]}")
                return False

        except Exception as e:
            print(f"\n❌ エラー発生: {e}")
            # スクリーンショットを撮る
            await page.screenshot(path="multiline_upload_error.png")
            print("エラー時のスクリーンショットを multiline_upload_error.png に保存しました")
            return False

        finally:
            await browser.close()


async def main():
    """メインテスト実行"""
    print("\n" + "🎭" * 30)
    print("マルチライン形式JSONLファイルの自動修正テスト")
    print("🎭" * 30 + "\n")

    success = await test_multiline_dual_upload()

    print("\n" + "=" * 60)
    if success:
        print("✨ テストが成功しました！")
        print("マルチライン形式のJSONLファイルが自動的に処理されました")
    else:
        print("❌ テストが失敗しました")
    print("=" * 60)

    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)