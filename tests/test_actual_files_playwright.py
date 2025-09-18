#!/usr/bin/env python3
"""
Playwright test for actual data files from datas/ directory
"""

import asyncio
from playwright.async_api import async_playwright
import os
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


async def test_actual_dual_file_upload():
    """Test dual file upload with actual data files"""
    print("=" * 60)
    print("実際のデータファイルでの2ファイル比較テスト")
    print("=" * 60)

    # 実際のファイルパス
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    file1_path = PROJECT_ROOT / "datas" / "classification.infer.jsonl"
    file2_path = PROJECT_ROOT / "datas" / "classification.infer.qwen1.7b.jsonl"
    print(f"File1 path: {file1_path}")
    print(f"File2 path: {file2_path}")

    # ファイルが存在することを確認
    if not file1_path.exists():
        print(f"❌ ファイル1が見つかりません: {file1_path}")
        return False
    if not file2_path.exists():
        print(f"❌ ファイル2が見つかりません: {file2_path}")
        return False

    print(f"✅ ファイル1: {file1_path.name}")
    print(f"✅ ファイル2: {file2_path.name}")

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

            # GPU モードをONにする（もし存在すれば）
            print("\n6. GPUモードの設定...")
            gpu_checkbox = page.locator('#gpu')
            if await gpu_checkbox.count() > 0 and await gpu_checkbox.is_visible():
                await gpu_checkbox.check()
                is_checked = await gpu_checkbox.is_checked()
                print(f"   GPUモード: {'ON' if is_checked else 'OFF'}")
            else:
                print("   GPUモード: チェックボックスが見つかりません（APIで自動設定）")

            # フォームを送信
            print("\n7. フォームを送信...")
            submit_button = page.locator('#dualSubmitButton')
            await submit_button.click()

            # 処理中表示を待つ
            print("   処理中...")
            loading = page.locator('#loading')
            try:
                await page.wait_for_selector('#loading.active', timeout=5000)
            except:
                pass  # ロード表示がすぐに消える場合もある

            # 結果表示を待つ（最大120秒 - 大きなファイルなので時間がかかる）
            print("   結果を待っています（最大120秒）...")
            result_container = page.locator('#resultContainer')
            await page.wait_for_selector('#resultContainer.active', timeout=120000)

            # 結果タイトルを確認
            result_title = page.locator('#resultTitle')
            title_text = await result_title.text_content()
            print(f"\n8. 結果タイトル: {title_text}")

            # 結果内容を取得
            result_content = page.locator('#resultContent')
            content_text = await result_content.text_content()

            # JSONをパース
            import json
            try:
                result_json = json.loads(content_text)
                print("\n9. 比較結果:")
                print(f"   - スコア: {result_json.get('score', 'N/A')}")
                print(f"   - 意味: {result_json.get('meaning', 'N/A')}")
                print(f"   - 総行数: {result_json.get('total_lines', 'N/A')}")

                if '_metadata' in result_json:
                    metadata = result_json['_metadata']
                    print(f"\n10. メタデータ:")
                    print(f"   - 比較列: {metadata.get('column_compared', 'N/A')}")
                    print(f"   - 比較行数: {metadata.get('rows_compared', 'N/A')}")
                    print(f"   - GPU使用: {metadata.get('gpu_used', 'N/A')}")
                    print(f"   - 処理時間: {metadata.get('processing_time', 'N/A')}")

                    if 'data_repairs' in metadata:
                        repairs = metadata['data_repairs']
                        print(f"   - データ修復:")
                        print(f"     - ファイル1: {repairs.get('file1', 0)}行")
                        print(f"     - ファイル2: {repairs.get('file2', 0)}行")

                print("\n✅ 2ファイル比較が正常に完了しました！")
                return True
            except json.JSONDecodeError:
                print(f"結果のパースに失敗: {content_text[:200]}")
                return False

        except Exception as e:
            print(f"\n❌ エラー発生: {e}")
            # スクリーンショットを撮る
            await page.screenshot(path="dual_upload_error.png")
            print("エラー時のスクリーンショットを dual_upload_error.png に保存しました")
            return False

        finally:
            await browser.close()


async def main():
    """メインテスト実行"""
    print("\n" + "🎭" * 30)
    print("実際のデータファイルでのWebUIテスト開始")
    print("🎭" * 30 + "\n")

    success = await test_actual_dual_file_upload()

    print("\n" + "=" * 60)
    if success:
        print("✨ テストが成功しました！")
    else:
        print("❌ テストが失敗しました")
    print("=" * 60)

    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)