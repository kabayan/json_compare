#!/usr/bin/env python3
"""
WebUI テストケース実行スクリプト（Playwright使用）
4つのテストケースを順番に実行し、課題を報告します。
"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser

class WebUITester:
    def __init__(self):
        self.base_url = "http://localhost:18081"
        self.test_file1 = "/tmp/test_file1.jsonl"
        self.test_file2 = "/tmp/test_file2.jsonl"
        self.screenshot_dir = Path("./test_screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        self.results = []

    async def setup_browser(self):
        """ブラウザとページのセットアップ"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return await self.browser.new_page()

    async def cleanup(self):
        """リソースのクリーンアップ"""
        await self.browser.close()
        await self.playwright.stop()

    async def wait_for_results(self, page: Page, timeout: int = 30):
        """結果の表示を待機し、内容を取得"""
        print(f"結果を{timeout}秒間待機中...")

        # 結果表示エリアの出現を待機
        try:
            # 進捗表示の開始を確認
            await page.wait_for_selector("#progressContainer", timeout=10000)
            print("進捗表示が開始されました")

            # 結果表示エリアの出現を待機
            await page.wait_for_selector("#resultContainer", timeout=timeout * 1000)
            await asyncio.sleep(2)  # 結果の完全読み込みを待機

            # 結果テキストを取得
            result_element = await page.query_selector("#resultContent")
            if result_element:
                result_text = await result_element.inner_text()

                # 進捗情報も取得
                progress_info = {}
                try:
                    progress_current = await page.query_selector("#progressCurrent")
                    progress_total = await page.query_selector("#progressTotal")
                    elapsed_time = await page.query_selector("#elapsedTime")

                    if progress_current and progress_total and elapsed_time:
                        progress_info = {
                            "current": await progress_current.inner_text(),
                            "total": await progress_total.inner_text(),
                            "elapsed": await elapsed_time.inner_text()
                        }
                except:
                    pass

                return {
                    "result_text": result_text,
                    "progress_info": progress_info
                }
            return {"result_text": "結果エリアが見つかりません", "progress_info": {}}

        except Exception as e:
            return {"result_text": f"タイムアウトまたはエラー: {str(e)}", "progress_info": {}}

    async def upload_files_and_submit(self, page: Page, dual_type: str, use_llm: bool):
        """ファイルアップロードとフォーム送信"""

        # ページの完全読み込みを待機
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)

        # '📑 2ファイル比較'ボタンをクリック
        dual_compare_button = await page.query_selector('text=📑 2ファイル比較')
        if dual_compare_button:
            await dual_compare_button.click()
            await asyncio.sleep(1)
        else:
            raise Exception("'📑 2ファイル比較'ボタンが見つかりません")

        # ファイルアップロード
        file1_input = await page.query_selector('input[name="file1"]')
        if file1_input:
            await file1_input.set_input_files(self.test_file1)

        file2_input = await page.query_selector('input[name="file2"]')
        if file2_input:
            await file2_input.set_input_files(self.test_file2)

        # dual_type設定
        await page.select_option('#dual_type', dual_type)

        # use_llm設定
        llm_checkbox = await page.query_selector('#dual_use_llm')
        if llm_checkbox:
            is_checked = await llm_checkbox.is_checked()
            if use_llm and not is_checked:
                await llm_checkbox.check()
            elif not use_llm and is_checked:
                await llm_checkbox.uncheck()

        await asyncio.sleep(1)

        # フォーム送信
        submit_button = await page.query_selector('#dualForm button[type="submit"]')
        if submit_button:
            await submit_button.click()
        else:
            raise Exception("送信ボタンが見つかりません")

    async def run_test_case(self, case_name: str, dual_type: str, use_llm: bool, timeout: int):
        """個別テストケース実行"""
        print(f"\n=== {case_name} 開始 ===")

        try:
            page = await self.setup_browser()

            # UIページにアクセス
            await page.goto(f"{self.base_url}/ui")
            await page.wait_for_load_state('networkidle')

            # ファイルアップロードとフォーム送信
            await self.upload_files_and_submit(page, dual_type, use_llm)

            # 結果待機
            result_data = await self.wait_for_results(page, timeout)

            # スクリーンショット撮影
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.screenshot_dir / f"{case_name}_{timestamp}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)

            # 結果分析
            result_text = result_data["result_text"]
            progress_info = result_data["progress_info"]
            success = "エラー" not in result_text and "タイムアウト" not in result_text

            result = {
                "case": case_name,
                "dual_type": dual_type,
                "use_llm": use_llm,
                "success": success,
                "result_text": result_text,
                "progress_info": progress_info,
                "screenshot": str(screenshot_path),
                "timestamp": timestamp
            }

            self.results.append(result)

            print(f"✓ {case_name} 完了")
            print(f"成功: {success}")
            print(f"結果プレビュー: {result_text[:200]}...")

            await self.cleanup()
            return result

        except Exception as e:
            error_result = {
                "case": case_name,
                "dual_type": dual_type,
                "use_llm": use_llm,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
            self.results.append(error_result)
            print(f"✗ {case_name} 失敗: {e}")

            try:
                await self.cleanup()
            except:
                pass

            return error_result

    async def run_all_tests(self):
        """全テストケースの実行"""
        print("WebUI テストケース実行開始")
        print(f"ベースURL: {self.base_url}")
        print(f"テストファイル1: {self.test_file1}")
        print(f"テストファイル2: {self.test_file2}")

        # Case 1: Embedding + Score
        await self.run_test_case(
            "Case1_Embedding_Score",
            dual_type="score",
            use_llm=False,
            timeout=120  # 2分に延長
        )

        # Case 2: Embedding + File
        await self.run_test_case(
            "Case2_Embedding_File",
            dual_type="file",
            use_llm=False,
            timeout=120  # 2分に延長
        )

        # Case 3: LLM + Score
        await self.run_test_case(
            "Case3_LLM_Score",
            dual_type="score",
            use_llm=True,
            timeout=180  # 3分に延長
        )

        # Case 4: LLM + File
        await self.run_test_case(
            "Case4_LLM_File",
            dual_type="file",
            use_llm=True,
            timeout=180  # 3分に延長
        )

    def generate_report(self):
        """テスト結果レポート生成"""
        print("\n" + "="*60)
        print("WebUI テストケース結果レポート")
        print("="*60)

        for i, result in enumerate(self.results, 1):
            print(f"\n--- Case {i}: {result['case']} ---")
            print(f"設定: dual_type={result['dual_type']}, use_llm={result['use_llm']}")
            print(f"結果: {'成功' if result['success'] else '失敗'}")

            if result['success']:
                print("結果内容:")
                print(result['result_text'])
                if 'progress_info' in result and result['progress_info']:
                    print("進捗情報:")
                    for key, value in result['progress_info'].items():
                        print(f"  {key}: {value}")
                if 'screenshot' in result:
                    print(f"スクリーンショット: {result['screenshot']}")
            else:
                if 'error' in result:
                    print(f"エラー: {result['error']}")
                if 'result_text' in result:
                    print(f"エラー詳細: {result['result_text']}")
                if 'progress_info' in result and result['progress_info']:
                    print("取得した進捗情報:")
                    for key, value in result['progress_info'].items():
                        print(f"  {key}: {value}")

        # 課題サマリー
        print(f"\n--- 全体課題サマリー ---")
        successful_cases = sum(1 for r in self.results if r['success'])
        total_cases = len(self.results)
        print(f"成功率: {successful_cases}/{total_cases} ({successful_cases/total_cases*100:.1f}%)")

        failed_cases = [r for r in self.results if not r['success']]
        if failed_cases:
            print("失敗したケース:")
            for case in failed_cases:
                print(f"  - {case['case']}: {case.get('error', 'タイムアウトまたは結果取得失敗')}")

        # 結果をJSONファイルとして保存
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"\n詳細レポート保存先: {report_file}")

async def main():
    tester = WebUITester()
    await tester.run_all_tests()
    tester.generate_report()

if __name__ == "__main__":
    asyncio.run(main())