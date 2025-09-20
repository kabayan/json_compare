#!/usr/bin/env python3
"""
WebUI Playwright MCPテスト実行スクリプト
4つの組み合わせテスト：
1. Embedding + Score形式
2. Embedding + File形式
3. LLM + Score形式
4. LLM + File形式
"""

import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright

class WebUITester:
    def __init__(self):
        self.base_url = "http://localhost:18081"
        self.test_file1_path = "/home/kabayan/workspace/json_compare/test_data1.jsonl"
        self.test_file2_path = "/home/kabayan/workspace/json_compare/test_data2.jsonl"

    async def setup_browser(self):
        """ブラウザセットアップ"""
        self.playwright = await async_playwright().start()
        # ヘッドレスモードで実行（GUI環境でない場合）
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

        # コンソールエラーを監視
        self.page.on("console", lambda msg: print(f"Console: {msg.text}"))
        self.page.on("pageerror", lambda error: print(f"Page Error: {error}"))

    async def teardown_browser(self):
        """ブラウザクリーンアップ"""
        await self.browser.close()
        await self.playwright.stop()

    async def navigate_to_dual_file_compare(self):
        """2ファイル比較ページにナビゲート"""
        print("WebUIにアクセス中...")
        await self.page.goto(f"{self.base_url}/ui")
        await self.page.wait_for_load_state("networkidle")

        print("「📑 2ファイル比較」ボタンをクリック中...")
        dual_compare_button = await self.page.wait_for_selector('button:has-text("📑 2ファイル比較")')
        await dual_compare_button.click()
        await self.page.wait_for_load_state("networkidle")

    async def upload_test_files(self):
        """テスト用ファイルをアップロード"""
        print("ファイルアップロード中...")

        # ファイル1をアップロード
        file1_input = await self.page.wait_for_selector('input[type="file"]:nth-of-type(1)')
        await file1_input.set_input_files(self.test_file1_path)

        # ファイル2をアップロード
        file2_input = await self.page.wait_for_selector('input[type="file"]:nth-of-type(2)')
        await file2_input.set_input_files(self.test_file2_path)

        # ファイルアップロード後の少し待機
        await self.page.wait_for_timeout(1000)

    async def set_output_format(self, format_type: str):
        """出力形式を設定（score/file）"""
        print(f"出力形式を{format_type}に設定中...")

        # dual_typeセレクタを見つけて設定
        select_element = await self.page.wait_for_selector('#dual_type')
        await select_element.select_option(format_type)

    async def set_llm_usage(self, use_llm: bool):
        """LLM使用設定"""
        print(f"LLM使用を{use_llm}に設定中...")

        # dual_use_llmチェックボックスを見つけて設定
        checkbox = await self.page.wait_for_selector('#dual_use_llm')

        # 現在の状態を確認
        is_checked = await checkbox.is_checked()

        # 必要に応じてクリック
        if (use_llm and not is_checked) or (not use_llm and is_checked):
            await checkbox.click()

    async def submit_form(self):
        """フォーム送信"""
        print("送信ボタンをクリック中...")

        submit_button = await self.page.wait_for_selector('button[type="submit"]')
        await submit_button.click()

    async def wait_for_results(self, timeout=30000):
        """結果表示を待機"""
        print("結果表示を待機中...")

        try:
            # resultContainerが表示されるまで待機
            await self.page.wait_for_selector('#resultContainer', timeout=timeout)

            # 結果が完全に読み込まれるまで少し待機
            await self.page.wait_for_timeout(2000)

            return True
        except Exception as e:
            print(f"結果表示タイムアウト: {e}")
            return False

    async def extract_results(self):
        """結果を抽出"""
        print("結果を抽出中...")

        try:
            # resultContainerの内容を取得
            result_element = await self.page.query_selector('#resultContainer')
            if not result_element:
                return None

            result_text = await result_element.inner_text()

            # JSONが含まれているかチェック
            if '{' in result_text and '}' in result_text:
                # JSON部分を抽出して解析
                start = result_text.find('{')
                end = result_text.rfind('}') + 1
                json_str = result_text[start:end]

                try:
                    result_json = json.loads(json_str)
                    return result_json
                except json.JSONDecodeError as e:
                    print(f"JSON解析エラー: {e}")
                    return {"raw_text": result_text}
            else:
                return {"raw_text": result_text}

        except Exception as e:
            print(f"結果抽出エラー: {e}")
            return None

    async def validate_results(self, results, expected_method, expected_format):
        """結果を検証"""
        print("結果を検証中...")

        validation_results = {
            "has_score": False,
            "has_metadata": False,
            "correct_calculation_method": False,
            "has_detailed_results": False,
            "valid_structure": False
        }

        if not results:
            return validation_results

        # JSON結果の場合
        if isinstance(results, dict) and "raw_text" not in results:
            # scoreフィールドの存在確認
            if "score" in results:
                validation_results["has_score"] = True

            # _metadataフィールドの存在確認
            if "_metadata" in results:
                validation_results["has_metadata"] = True
                metadata = results["_metadata"]

                # calculation_methodの確認
                if "calculation_method" in metadata:
                    if metadata["calculation_method"] == expected_method:
                        validation_results["correct_calculation_method"] = True

            # fileタイプの場合はdetailed_resultsの存在確認
            if expected_format == "file":
                if "detailed_results" in results:
                    validation_results["has_detailed_results"] = True

            validation_results["valid_structure"] = True

        return validation_results

    async def run_test_case(self, case_name, use_llm, output_format):
        """単一テストケースを実行"""
        print(f"\n=== {case_name} テスト開始 ===")

        try:
            # 2ファイル比較ページにナビゲート
            await self.navigate_to_dual_file_compare()

            # ファイルアップロード
            await self.upload_test_files()

            # 設定
            await self.set_output_format(output_format)
            await self.set_llm_usage(use_llm)

            # フォーム送信
            await self.submit_form()

            # 結果待機
            success = await self.wait_for_results()
            if not success:
                return {
                    "case_name": case_name,
                    "success": False,
                    "error": "結果表示タイムアウト"
                }

            # 結果抽出
            results = await self.extract_results()

            # 結果検証
            expected_method = "llm" if use_llm else "embedding"
            validation = await self.validate_results(results, expected_method, output_format)

            print(f"{case_name} テスト完了")

            return {
                "case_name": case_name,
                "success": True,
                "results": results,
                "validation": validation,
                "expected_method": expected_method,
                "expected_format": output_format
            }

        except Exception as e:
            print(f"{case_name} テストエラー: {e}")
            return {
                "case_name": case_name,
                "success": False,
                "error": str(e)
            }

    async def run_all_tests(self):
        """全テストケースを実行"""
        print("=== WebUI Playwright MCPテスト開始 ===")

        await self.setup_browser()

        test_cases = [
            ("Test 1: Embedding + Score形式", False, "score"),
            ("Test 2: Embedding + File形式", False, "file"),
            ("Test 3: LLM + Score形式", True, "score"),
            ("Test 4: LLM + File形式", True, "file"),
        ]

        results = []

        for case_name, use_llm, output_format in test_cases:
            result = await self.run_test_case(case_name, use_llm, output_format)
            results.append(result)

            # テスト間で少し休憩
            await self.page.wait_for_timeout(2000)

        await self.teardown_browser()

        return results

def main():
    """メイン実行関数"""
    async def run():
        tester = WebUITester()
        results = await tester.run_all_tests()

        print("\n=== テスト結果サマリー ===")
        for result in results:
            print(f"\n{result['case_name']}: {'✓' if result['success'] else '✗'}")
            if result['success']:
                validation = result['validation']
                print(f"  - Score field: {'✓' if validation['has_score'] else '✗'}")
                print(f"  - Metadata field: {'✓' if validation['has_metadata'] else '✗'}")
                print(f"  - Correct method: {'✓' if validation['correct_calculation_method'] else '✗'}")
                if result['expected_format'] == 'file':
                    print(f"  - Detailed results: {'✓' if validation['has_detailed_results'] else '✗'}")
            else:
                print(f"  - Error: {result.get('error', 'Unknown error')}")

        return results

    return asyncio.run(run())

if __name__ == "__main__":
    results = main()