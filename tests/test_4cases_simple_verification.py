"""4ケース操作結果確認シンプルテスト

Task 14で実装した4つの組み合わせの動作を実際のWebUIで確認：
1. embedding + score
2. embedding + file
3. llm + score
4. llm + file

各ケースで正しく結果が出力されているかを確認
"""

import asyncio
import tempfile
import json
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime

class SimpleFourCasesVerifier:
    """4ケース簡易検証"""

    def __init__(self):
        self.base_url = "http://localhost:18081"
        self.test_results = []

        # テスト用ファイル準備
        self.test_files = self._prepare_test_files()

    def _prepare_test_files(self) -> dict:
        """小さなテスト用JSONLファイルを準備"""
        test_data_1 = [
            {"text": "Hello", "inference": "greeting"},
            {"text": "Goodbye", "inference": "farewell"}
        ]

        test_data_2 = [
            {"text": "Hello", "inference": "greeting"},
            {"text": "Goodbye", "inference": "parting"}
        ]

        temp_dir = Path("/tmp/simple_4cases")
        temp_dir.mkdir(exist_ok=True)

        file1_path = temp_dir / "test1.jsonl"
        file2_path = temp_dir / "test2.jsonl"

        with open(file1_path, 'w', encoding='utf-8') as f:
            for item in test_data_1:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        with open(file2_path, 'w', encoding='utf-8') as f:
            for item in test_data_2:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        return {"file1": str(file1_path), "file2": str(file2_path)}

    async def test_case(self, page, case_name: str, use_llm: bool, output_type: str):
        """1つのケースをテスト"""
        print(f"\n=== {case_name} テスト開始 ===")

        try:
            # WebUIページに移動
            await page.goto(f"{self.base_url}/ui")
            await page.wait_for_load_state('networkidle')

            # 2ファイル比較モードに切り替え
            dual_button = page.locator('button:has-text("📑 2ファイル比較")')
            await dual_button.click()
            await page.wait_for_timeout(1000)

            # ファイルアップロード
            await page.locator('#file1').set_input_files(self.test_files["file1"])
            await page.locator('#file2').set_input_files(self.test_files["file2"])

            # 出力形式選択
            await page.locator('#dual_type').select_option(output_type)

            # LLM使用設定
            llm_checkbox = page.locator('#dual_use_llm')
            if use_llm:
                await llm_checkbox.check()
            else:
                await llm_checkbox.uncheck()

            await page.wait_for_timeout(500)

            # 送信
            submit_button = page.locator('#dualForm button[type="submit"]')
            await submit_button.click()

            print(f"✅ {case_name}: 送信完了")

            # 結果を待機（最大30秒）
            try:
                await page.wait_for_selector('#resultContainer', timeout=30000, state='visible')
                print(f"✅ {case_name}: 結果表示確認")

                # 結果内容を取得
                result_content = await page.locator('#resultContent').text_content()

                # 結果の基本検証
                if result_content and len(result_content.strip()) > 0:
                    # JSONとして解析可能か確認
                    try:
                        result_data = json.loads(result_content)

                        # 基本構造確認
                        has_score = 'score' in result_data
                        has_metadata = '_metadata' in result_data

                        if output_type == 'file':
                            has_detailed_results = 'detailed_results' in result_data
                        else:
                            has_detailed_results = True  # scoreタイプでは不要

                        calculation_method = result_data.get('_metadata', {}).get('calculation_method', '')
                        expected_method = 'llm' if use_llm else 'embedding'

                        success = (
                            has_score and
                            has_metadata and
                            has_detailed_results and
                            (expected_method in calculation_method.lower() if calculation_method else False)
                        )

                        self.test_results.append({
                            'case': case_name,
                            'success': success,
                            'has_score': has_score,
                            'has_metadata': has_metadata,
                            'has_detailed_results': has_detailed_results,
                            'calculation_method': calculation_method,
                            'expected_method': expected_method,
                            'result_length': len(result_content),
                            'timestamp': datetime.now().isoformat()
                        })

                        if success:
                            print(f"✅ {case_name}: 結果検証成功")
                            print(f"   - スコア: {result_data.get('score', 'N/A')}")
                            print(f"   - 計算方法: {calculation_method}")
                        else:
                            print(f"❌ {case_name}: 結果検証失敗")
                            print(f"   - スコア有: {has_score}")
                            print(f"   - メタデータ有: {has_metadata}")
                            print(f"   - 計算方法: {calculation_method} (期待: {expected_method})")

                    except json.JSONDecodeError:
                        print(f"❌ {case_name}: JSON解析エラー")
                        self.test_results.append({
                            'case': case_name,
                            'success': False,
                            'error': 'JSON解析失敗',
                            'result_preview': result_content[:100],
                            'timestamp': datetime.now().isoformat()
                        })

                else:
                    print(f"❌ {case_name}: 結果が空")
                    self.test_results.append({
                        'case': case_name,
                        'success': False,
                        'error': '結果が空',
                        'timestamp': datetime.now().isoformat()
                    })

            except Exception as e:
                print(f"❌ {case_name}: 結果待機タイムアウト - {e}")
                self.test_results.append({
                    'case': case_name,
                    'success': False,
                    'error': f'結果待機タイムアウト: {e}',
                    'timestamp': datetime.now().isoformat()
                })

        except Exception as e:
            print(f"❌ {case_name}: テスト実行エラー - {e}")
            self.test_results.append({
                'case': case_name,
                'success': False,
                'error': f'実行エラー: {e}',
                'timestamp': datetime.now().isoformat()
            })

    async def run_all_cases(self):
        """4ケース全て実行"""
        print("=== 4ケース操作結果確認テスト開始 ===")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # 4つのケース
                test_cases = [
                    ("1. Embedding + Score", False, "score"),
                    ("2. Embedding + File", False, "file"),
                    ("3. LLM + Score", True, "score"),
                    ("4. LLM + File", True, "file")
                ]

                for case_name, use_llm, output_type in test_cases:
                    await self.test_case(page, case_name, use_llm, output_type)
                    await page.wait_for_timeout(2000)  # ケース間の待機

            finally:
                await browser.close()

        # 結果サマリー
        self.print_summary()

    def print_summary(self):
        """結果サマリー表示"""
        print("\n" + "="*60)
        print("           4ケース操作結果確認 - 最終結果           ")
        print("="*60)

        total_cases = len(self.test_results)
        successful_cases = sum(1 for result in self.test_results if result.get('success', False))

        print(f"総ケース数: {total_cases}")
        print(f"成功ケース: {successful_cases}")
        print(f"成功率: {(successful_cases/total_cases)*100:.1f}%" if total_cases > 0 else "N/A")

        print("\n--- ケース別詳細 ---")
        for i, result in enumerate(self.test_results, 1):
            status = "✅ 成功" if result.get('success', False) else "❌ 失敗"
            print(f"{i}. {result['case']}: {status}")

            if not result.get('success', False) and 'error' in result:
                print(f"   エラー: {result['error']}")
            elif result.get('success', False):
                method = result.get('calculation_method', 'N/A')
                print(f"   計算方法: {method}")

        print("\n" + "="*60)

        # 失敗があった場合の詳細
        failed_cases = [r for r in self.test_results if not r.get('success', False)]
        if failed_cases:
            print("\n⚠️  失敗ケースの詳細:")
            for case in failed_cases:
                print(f"- {case['case']}: {case.get('error', '詳細不明')}")

        if successful_cases == total_cases:
            print("\n🎉 全ケース成功！Task 14検証システムの動作確認完了")
        else:
            print(f"\n⚠️  {total_cases - successful_cases}ケースで問題が発生しました")


async def main():
    """メイン実行"""
    verifier = SimpleFourCasesVerifier()
    await verifier.run_all_cases()


if __name__ == "__main__":
    asyncio.run(main())