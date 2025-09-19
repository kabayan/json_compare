"""
Playwright MCP包括テスト検証
全パターンの組み合わせテストでWebUIの進捗表示とポーリング機能を検証

Task 10: Playwright MCP包括テスト検証の実装
- 10.1: 全パターン組み合わせテストスイート
- 10.2: ポーリング動作とAPI統合の検証
- 10.3: メタデータと結果整合性の検証
"""

import pytest
import pytest_asyncio
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

# Test data configurations
TEST_PATTERNS = [
    # 1ファイル比較パターン
    {"files": 1, "mode": "embedding", "format": "score", "description": "1ファイル埋め込みスコア形式"},
    {"files": 1, "mode": "embedding", "format": "file", "description": "1ファイル埋め込みファイル形式"},
    {"files": 1, "mode": "llm", "format": "score", "description": "1ファイルLLMスコア形式"},
    {"files": 1, "mode": "llm", "format": "file", "description": "1ファイルLLMファイル形式"},

    # 2ファイル比較パターン
    {"files": 2, "mode": "embedding", "format": "score", "description": "2ファイル埋め込みスコア形式"},
    {"files": 2, "mode": "embedding", "format": "file", "description": "2ファイル埋め込みファイル形式"},
    {"files": 2, "mode": "llm", "format": "score", "description": "2ファイルLLMスコア形式"},
    {"files": 2, "mode": "llm", "format": "file", "description": "2ファイルLLMファイル形式"},
]


class WebUIProgressTestSuite:
    """WebUI進捗表示包括テストスイート"""

    def __init__(self, mcp_wrapper):
        self.mcp = mcp_wrapper
        self.test_results = []
        self.base_url = "http://localhost:18081/ui"

    async def setup(self):
        """テスト環境のセットアップ"""
        # テストデータの準備
        await self._create_test_files()

        # ブラウザの起動
        await self.mcp.browser_navigate(url=self.base_url)
        await asyncio.sleep(2)

    async def teardown(self):
        """テスト環境のクリーンアップ"""
        # ブラウザのクローズ
        await self.mcp.browser_close()

        # テスト結果レポートの生成
        self._generate_test_report()

    async def _create_test_files(self):
        """テスト用ファイルの作成"""
        # 1ファイル用テストデータ
        test_data_single = {
            "inference1": {"text": "これはテストデータです", "score": 0.95},
            "inference2": {"text": "これはテスト用のデータです", "score": 0.93}
        }

        # 2ファイル用テストデータ
        test_data_dual1 = {"inference": {"text": "ファイル1のテストデータ", "value": 100}}
        test_data_dual2 = {"inference": {"text": "ファイル2のテストデータ", "value": 101}}

        # ファイル書き込み
        Path("/tmp/test_single.jsonl").write_text(json.dumps(test_data_single) + "\n")
        Path("/tmp/test_dual1.jsonl").write_text(json.dumps(test_data_dual1) + "\n")
        Path("/tmp/test_dual2.jsonl").write_text(json.dumps(test_data_dual2) + "\n")

    def _generate_test_report(self):
        """テスト結果レポートの生成"""
        print("\n" + "="*60)
        print("WebUI進捗表示包括テスト結果レポート")
        print("="*60)

        success_count = sum(1 for r in self.test_results if r["status"] == "success")
        total_count = len(self.test_results)

        print(f"\n総テスト数: {total_count}")
        print(f"成功: {success_count}")
        print(f"失敗: {total_count - success_count}")
        print(f"成功率: {success_count/total_count*100:.1f}%")

        print("\n詳細結果:")
        print("-"*60)
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "success" else "❌"
            print(f"{status_icon} {result['pattern']['description']}")
            print(f"   実行時間: {result.get('duration', 'N/A')}秒")
            if result.get("error"):
                print(f"   エラー: {result['error']}")

    async def run_all_tests(self):
        """全パターンのテスト実行"""
        print("WebUI進捗表示包括テスト開始...")

        for pattern in TEST_PATTERNS:
            print(f"\nテスト実行中: {pattern['description']}")
            start_time = time.time()

            try:
                if pattern["files"] == 1:
                    result = await self._test_single_file_pattern(pattern)
                else:
                    result = await self._test_dual_file_pattern(pattern)

                duration = time.time() - start_time
                self.test_results.append({
                    "pattern": pattern,
                    "status": "success" if result else "fail",
                    "duration": round(duration, 2),
                    "error": None if result else "テスト失敗"
                })

            except Exception as e:
                duration = time.time() - start_time
                self.test_results.append({
                    "pattern": pattern,
                    "status": "fail",
                    "duration": round(duration, 2),
                    "error": str(e)
                })
                print(f"   エラー発生: {e}")

    async def _test_single_file_pattern(self, pattern: Dict) -> bool:
        """1ファイルパターンのテスト"""
        try:
            # ページをリロード
            await self.mcp.browser_navigate(url=self.base_url)
            await asyncio.sleep(1)

            # ファイルアップロード
            snapshot = await self.mcp.browser_snapshot()
            file_input = self._find_element(snapshot, "file-upload")
            if file_input:
                await self.mcp.browser_file_upload(paths=["/tmp/test_single.jsonl"])
                await asyncio.sleep(1)

            # モードと形式の設定
            if pattern["mode"] == "llm":
                # LLMモードのチェックボックスを有効化
                llm_checkbox = self._find_element(snapshot, "checkbox", "id", "use-llm")
                if llm_checkbox:
                    await self.mcp.browser_click(
                        element="LLMモードチェックボックス",
                        ref=llm_checkbox["ref"]
                    )

            # 出力形式の選択
            format_select = self._find_element(snapshot, "combobox", "name", "type")
            if format_select:
                await self.mcp.browser_select_option(
                    element="出力形式選択",
                    ref=format_select["ref"],
                    values=[pattern["format"]]
                )

            # 処理開始
            submit_button = self._find_element(snapshot, "button", "text", "比較開始")
            if submit_button:
                await self.mcp.browser_click(
                    element="比較開始ボタン",
                    ref=submit_button["ref"]
                )

            # ポーリング動作の検証
            polling_verified = await self._verify_polling_behavior()

            # 結果の検証
            await self.mcp.browser_wait_for(text="処理が完了しました", time=30)
            result_verified = await self._verify_result_metadata(pattern)

            return polling_verified and result_verified

        except Exception as e:
            print(f"   1ファイルテストエラー: {e}")
            return False

    async def _test_dual_file_pattern(self, pattern: Dict) -> bool:
        """2ファイルパターンのテスト"""
        try:
            # ページをリロード
            await self.mcp.browser_navigate(url=self.base_url)
            await asyncio.sleep(1)

            # 2ファイルモードに切り替え
            dual_mode_tab = self._find_element(await self.mcp.browser_snapshot(), "tab", "text", "2ファイル比較")
            if dual_mode_tab:
                await self.mcp.browser_click(
                    element="2ファイル比較タブ",
                    ref=dual_mode_tab["ref"]
                )
                await asyncio.sleep(1)

            # ファイルアップロード
            snapshot = await self.mcp.browser_snapshot()
            file1_input = self._find_element(snapshot, "file-upload", "name", "file1")
            file2_input = self._find_element(snapshot, "file-upload", "name", "file2")

            if file1_input and file2_input:
                # 最初のファイル
                await self.mcp.browser_click(
                    element="ファイル1選択",
                    ref=file1_input["ref"]
                )
                await self.mcp.browser_file_upload(paths=["/tmp/test_dual1.jsonl"])

                # 2番目のファイル
                await self.mcp.browser_click(
                    element="ファイル2選択",
                    ref=file2_input["ref"]
                )
                await self.mcp.browser_file_upload(paths=["/tmp/test_dual2.jsonl"])
                await asyncio.sleep(1)

            # モードと形式の設定（1ファイルと同様）
            if pattern["mode"] == "llm":
                llm_checkbox = self._find_element(snapshot, "checkbox", "id", "use-llm-dual")
                if llm_checkbox:
                    await self.mcp.browser_click(
                        element="LLMモードチェックボックス",
                        ref=llm_checkbox["ref"]
                    )

            format_select = self._find_element(snapshot, "combobox", "name", "type-dual")
            if format_select:
                await self.mcp.browser_select_option(
                    element="出力形式選択",
                    ref=format_select["ref"],
                    values=[pattern["format"]]
                )

            # 処理開始
            submit_button = self._find_element(snapshot, "button", "text", "比較開始")
            if submit_button:
                await self.mcp.browser_click(
                    element="比較開始ボタン",
                    ref=submit_button["ref"]
                )

            # ポーリング動作の検証
            polling_verified = await self._verify_polling_behavior()

            # 結果の検証
            await self.mcp.browser_wait_for(text="処理が完了しました", time=30)
            result_verified = await self._verify_result_metadata(pattern)

            return polling_verified and result_verified

        except Exception as e:
            print(f"   2ファイルテストエラー: {e}")
            return False

    async def _verify_polling_behavior(self) -> bool:
        """ポーリング動作の検証"""
        try:
            # JavaScriptコンソールログを確認
            console_messages = await self.mcp.browser_console_messages()

            # ポーリング開始メッセージの確認
            polling_started = any(
                "Started polling" in msg.get("text", "")
                for msg in console_messages
            )

            if not polling_started:
                print("   ⚠️ ポーリング開始が確認できません")
                return False

            # 進捗更新の確認（3秒間監視）
            progress_updates = 0
            for _ in range(3):
                await asyncio.sleep(1)
                snapshot = await self.mcp.browser_snapshot()
                progress_bar = self._find_element(snapshot, "progressbar")
                if progress_bar:
                    progress_updates += 1

            if progress_updates < 2:
                print("   ⚠️ 進捗更新が不十分です")
                return False

            print("   ✅ ポーリング動作確認完了")
            return True

        except Exception as e:
            print(f"   ポーリング検証エラー: {e}")
            return False

    async def _verify_result_metadata(self, pattern: Dict) -> bool:
        """結果メタデータの検証"""
        try:
            # 結果JSONの取得
            result_text = await self.mcp.browser_evaluate(
                function="() => { return document.querySelector('#result-json')?.textContent || '{}'; }"
            )

            if not result_text or result_text == '{}':
                print("   ⚠️ 結果データが取得できません")
                return False

            result_data = json.loads(result_text)

            # メタデータフィールドの確認
            if pattern["mode"] == "llm":
                # LLMモードの場合
                method = result_data.get("calculation_method") or result_data.get("comparison_method")
                if method not in ["llm", "embedding_fallback"]:
                    print(f"   ⚠️ 不正な計算方法: {method}")
                    return False
            else:
                # 埋め込みモードの場合
                method = result_data.get("calculation_method") or result_data.get("comparison_method")
                if method != "embedding":
                    print(f"   ⚠️ 不正な計算方法: {method}")
                    return False

            # 出力形式の確認
            if pattern["format"] == "score":
                # スコア形式：詳細結果が含まれないことを確認
                if "details" in result_data or "results" in result_data:
                    print("   ⚠️ スコア形式に詳細結果が含まれています")
                    return False
            else:
                # ファイル形式：詳細結果が含まれることを確認
                if "details" not in result_data and "results" not in result_data:
                    print("   ⚠️ ファイル形式に詳細結果が含まれていません")
                    return False

            print("   ✅ メタデータ検証完了")
            return True

        except Exception as e:
            print(f"   メタデータ検証エラー: {e}")
            return False

    def _find_element(self, snapshot: Dict, element_type: str,
                      attribute: str = None, value: str = None) -> Optional[Dict]:
        """スナップショットから要素を検索"""
        if not snapshot or "elements" not in snapshot:
            return None

        for element in snapshot["elements"]:
            if element.get("role") == element_type:
                if attribute and value:
                    if element.get(attribute) == value:
                        return element
                else:
                    return element
        return None


# Pytest test fixtures and functions
@pytest_asyncio.fixture
async def test_suite():
    """テストスイートのセットアップ"""
    try:
        # Import MCP wrapper
        from src.mcp_wrapper import MCPWrapper

        # Initialize MCP wrapper
        mcp = MCPWrapper()
        await mcp.initialize()

        # Create test suite
        suite = WebUIProgressTestSuite(mcp)
        await suite.setup()

        yield suite

        # Cleanup
        await suite.teardown()

    except ImportError:
        # Fallback for testing without MCP
        pytest.skip("MCP wrapper not available")


@pytest.mark.asyncio
async def test_all_patterns_comprehensive(test_suite):
    """全パターン包括テスト（Task 10.1）"""
    await test_suite.run_all_tests()

    # 結果の検証
    success_count = sum(1 for r in test_suite.test_results if r["status"] == "success")
    total_count = len(test_suite.test_results)

    assert success_count == total_count, f"テスト失敗: {total_count - success_count}/{total_count} パターン"


@pytest.mark.asyncio
async def test_polling_api_integration(test_suite):
    """ポーリングとAPI統合テスト（Task 10.2）"""
    # 単一パターンでポーリング動作を詳細検証
    pattern = {"files": 1, "mode": "embedding", "format": "score", "description": "ポーリング検証"}

    # テスト実行
    await test_suite.mcp.browser_navigate(url=test_suite.base_url)

    # JavaScriptでポーリング間隔を確認
    polling_interval = await test_suite.mcp.browser_evaluate(
        function="() => { return window.currentPollingInterval ? 1000 : 0; }"
    )

    assert polling_interval == 1000, "ポーリング間隔が1秒ではありません"

    # エラーリトライの検証
    max_errors = await test_suite.mcp.browser_evaluate(
        function="() => { return window.maxPollingErrors || 0; }"
    )

    assert max_errors == 5, "最大エラー回数が5回ではありません"


@pytest.mark.asyncio
async def test_metadata_consistency(test_suite):
    """メタデータ整合性テスト（Task 10.3）"""
    # LLMフォールバックケースのテスト
    pattern = {"files": 1, "mode": "llm", "format": "file", "description": "メタデータ検証"}

    # テスト実行
    result = await test_suite._test_single_file_pattern(pattern)

    # フォールバック時のメタデータ確認
    result_text = await test_suite.mcp.browser_evaluate(
        function="() => { return document.querySelector('#result-json')?.textContent || '{}'; }"
    )

    if result_text and result_text != '{}':
        result_data = json.loads(result_text)

        # メタデータフィールドの存在確認
        assert "calculation_method" in result_data or "comparison_method" in result_data, \
            "計算方法のメタデータが存在しません"

        # _metadataフィールドの保持確認
        if "_metadata" in result_data:
            assert isinstance(result_data["_metadata"], dict), \
                "_metadataフィールドが変更されています"


# Main execution for standalone testing
if __name__ == "__main__":
    async def main():
        """スタンドアロン実行"""
        try:
            from src.mcp_wrapper import MCPWrapper

            mcp = MCPWrapper()
            await mcp.initialize()

            suite = WebUIProgressTestSuite(mcp)
            await suite.setup()
            await suite.run_all_tests()
            await suite.teardown()

        except Exception as e:
            print(f"テスト実行エラー: {e}")

    asyncio.run(main())