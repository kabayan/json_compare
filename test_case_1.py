#!/usr/bin/env python3
"""
Test Case 1: Embedding + Score形式
"""

import asyncio
import json
from playwright.async_api import async_playwright

async def test_embedding_score():
    """Embedding + Score形式テスト"""
    async with async_playwright() as p:
        print("=== Test 1: Embedding + Score形式 ===")

        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # ページエラーを監視
        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        page.on("pageerror", lambda error: print(f"Page Error: {error}"))

        try:
            # 1. WebUIにアクセス
            print("1. WebUIにアクセス中...")
            await page.goto("http://localhost:18081/ui")
            await page.wait_for_load_state("networkidle")

            # 2. 「📑 2ファイル比較」ボタンをクリック
            print("2. 2ファイル比較ボタンをクリック中...")
            dual_button = await page.wait_for_selector('button[data-mode="dual"]')
            await dual_button.click()

            # 明示的にdualモードに切り替え
            await page.evaluate('switchMode("dual")')
            await page.wait_for_load_state("networkidle")

            # モードが正しく切り替わるまで待機
            await page.wait_for_timeout(1000)

            # 3. テスト用JSONLファイル2つをアップロード
            print("3. ファイルアップロード中...")
            # input[type="file"]は意図的に非表示にされているため、可視性チェックなしで取得
            file1_input = await page.query_selector('#file1')
            if file1_input:
                await file1_input.set_input_files("/home/kabayan/workspace/json_compare/test_data1.jsonl")
                print("file1アップロード完了")
            else:
                raise Exception("file1要素が見つかりません")

            file2_input = await page.query_selector('#file2')
            if file2_input:
                await file2_input.set_input_files("/home/kabayan/workspace/json_compare/test_data2.jsonl")
                print("file2アップロード完了")
            else:
                raise Exception("file2要素が見つかりません")

            await page.wait_for_timeout(1000)

            # 4. 出力形式を選択（score）
            print("4. 出力形式をscoreに設定中...")
            select_element = await page.wait_for_selector('#dual_type')
            await select_element.select_option('score')

            # 5. LLM使用チェックボックスを設定（Embedding = unchecked）
            print("5. LLM使用をuncheckedに設定中...")
            llm_checkbox = await page.wait_for_selector('#dual_use_llm')
            is_checked = await llm_checkbox.is_checked()
            if is_checked:  # LLMをoffにする（Embeddingモード）
                await llm_checkbox.click()

            await page.wait_for_timeout(500)

            # 6. 送信ボタンをクリック
            print("6. 送信ボタンをクリック中...")
            submit_button = await page.wait_for_selector('#dualSubmitButton')
            await submit_button.click()

            # 7. 結果表示を確認
            print("7. 結果表示を待機中...")
            try:
                # より長い時間待機
                await page.wait_for_selector('#resultContainer', timeout=60000)
                await page.wait_for_timeout(2000)
            except:
                print("resultContainerが見つからない、代替要素を確認中...")
                # スクリーンショットを取って状態確認
                await page.screenshot(path="/home/kabayan/workspace/json_compare/test1_after_submit.png")

                # ページ全体のテキストを確認
                page_text = await page.inner_text('body')
                print(f"ページ全体テキスト（一部）: {page_text[:1000]}...")

                # 可能な結果要素を探す
                possible_results = await page.query_selector_all('.result, .response, .output, #result, [id*="result"]')
                for i, element in enumerate(possible_results):
                    text = await element.inner_text()
                    print(f"Possible result {i}: {text[:200]}...")

                return {
                    "success": False,
                    "error": "結果表示タイムアウト - resultContainerが見つからない",
                    "page_text": page_text[:1000]
                }

            # 8. 結果のJSON構造を検証
            print("8. 結果を抽出中...")
            result_element = await page.query_selector('#resultContainer')
            if result_element:
                result_text = await result_element.inner_text()
                print(f"結果テキスト: {result_text[:500]}...")
            else:
                print("resultContainer要素が見つかりません")

            # JSONを抽出
            if '{' in result_text and '}' in result_text:
                start = result_text.find('{')
                end = result_text.rfind('}') + 1
                json_str = result_text[start:end]

                try:
                    result_json = json.loads(json_str)
                    print("JSON解析成功!")

                    # 検証
                    validation_results = {
                        "has_score": "score" in result_json,
                        "has_metadata": "_metadata" in result_json,
                        "correct_calculation_method": False,
                        "valid_structure": True
                    }

                    if "_metadata" in result_json:
                        metadata = result_json["_metadata"]
                        if "calculation_method" in metadata:
                            validation_results["correct_calculation_method"] = metadata["calculation_method"] == "embedding"

                    print(f"検証結果: {validation_results}")
                    return {
                        "success": True,
                        "results": result_json,
                        "validation": validation_results
                    }

                except json.JSONDecodeError as e:
                    print(f"JSON解析エラー: {e}")
                    return {
                        "success": False,
                        "error": f"JSON解析エラー: {e}",
                        "raw_text": result_text
                    }
            else:
                print("JSONが見つかりませんでした")
                return {
                    "success": False,
                    "error": "JSONが見つかりませんでした",
                    "raw_text": result_text
                }

        except Exception as e:
            print(f"テストエラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_embedding_score())
    print(f"\n=== Test 1結果 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))