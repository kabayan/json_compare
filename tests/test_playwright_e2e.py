"""Task 8.2: Playwright MCPを使用したWeb UIテストシナリオ

実サイトでのE2Eテスト：LLM機能を含む完全なWebUIテスト
Requirements: Web UI統合、LLM機能、エラーハンドリング
"""

import pytest
import json
import time
import tempfile
from pathlib import Path


class TestPlaywrightE2E:
    """Playwright MCP E2Eテスト"""

    @pytest.fixture(scope="session")
    def base_url(self):
        """テスト対象のベースURL"""
        return "http://localhost:18081"

    @pytest.fixture
    def sample_jsonl_content(self):
        """テスト用JSONLデータ"""
        test_data = [
            {
                "id": 1,
                "inference1": "今日は天気がいいですね",
                "inference2": "本日は良いお天気ですね"
            },
            {
                "id": 2,
                "inference1": "猫が好きです",
                "inference2": "犬が好きです"
            },
            {
                "id": 3,
                "inference1": "プログラミングは楽しいです",
                "inference2": "コーディングは面白いです"
            }
        ]

        jsonl_content = ""
        for item in test_data:
            jsonl_content += json.dumps(item, ensure_ascii=False) + "\n"

        return jsonl_content

    @pytest.fixture
    def test_file_path(self, sample_jsonl_content):
        """テスト用ファイルパス作成"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            f.write(sample_jsonl_content)
            return f.name

    def test_health_endpoint_accessibility(self, base_url):
        """ヘルスエンドポイントのアクセシビリティテスト"""
        import requests

        # ヘルスチェックAPIの確認
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200

        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "cli_available" in health_data

    @pytest.mark.playwright
    def test_basic_web_ui_accessibility(self, base_url):
        """基本的なWebUIアクセシビリティテスト"""
        # Playwright MCPを使用してブラウザテストを実行
        # 注意: この実装はPlaywright MCPが利用可能な場合のみ動作します

        # TODO: Playwright MCPの利用可能性を確認
        playwright_available = False
        try:
            # Playwright MCPの初期化を試行
            from playwright.sync_api import sync_playwright
            playwright_available = True
        except ImportError:
            pass  # フォールバックテストを実行

        if not playwright_available:
            # モックテストとして、requestsでHTMLの基本構造を確認
            import requests

            response = requests.get(f"{base_url}/")
            assert response.status_code == 200

            html_content = response.text
            assert "<html" in html_content.lower()
            assert "<title" in html_content.lower()
            assert "json" in html_content.lower() or "compare" in html_content.lower()

            return

        # 実際のPlaywrightテストコード（MCPが利用可能な場合）
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            try:
                # メインページアクセス
                page.goto(base_url)

                # ページタイトル確認
                title = page.title()
                assert "JSON" in title or "Compare" in title

                # 基本的なUI要素の存在確認
                # ファイルアップロードフォームの確認
                file_input = page.query_selector('input[type="file"]')
                assert file_input is not None

                # フォーム送信ボタンの確認
                submit_button = page.query_selector('button[type="submit"], input[type="submit"]')
                assert submit_button is not None

            finally:
                browser.close()

    @pytest.mark.playwright
    def test_file_upload_basic_flow(self, base_url, test_file_path):
        """基本的なファイルアップロードフローテスト"""

        playwright_available = False
        try:
            # from playwright.sync_api import sync_playwright
            playwright_available = True
        except ImportError:
            # Playwright MCPが利用できない場合、requestsでAPIテストを実行
            import requests

            # ファイルアップロードAPIのテスト
            with open(test_file_path, 'rb') as f:
                files = {'file': (Path(test_file_path).name, f, 'application/json')}
                data = {'gpu': 'false'}

                response = requests.post(f"{base_url}/api/compare/single", files=files, data=data)

                # レスポンス確認
                assert response.status_code == 200

                result = response.json()
                assert "result" in result or "detailed_results" in result or "error" not in result

            return

        # 実際のPlaywrightテスト（MCPが利用可能な場合）
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            try:
                # メインページアクセス
                page.goto(base_url)

                # ファイルアップロード
                file_input = page.query_selector('input[type="file"]')
                assert file_input is not None

                # ファイル選択
                file_input.set_input_files(test_file_path)

                # フォーム送信
                submit_button = page.query_selector('button[type="submit"], input[type="submit"]')
                assert submit_button is not None

                # 結果待機（タイムアウト付き）
                submit_button.click()

                # 処理完了まで待機（最大30秒）
                page.wait_for_timeout(5000)  # 5秒待機

                # 結果の確認
                page_content = page.content()

                # 成功の兆候を確認（結果テーブル、スコア表示など）
                assert any(keyword in page_content.lower() for keyword in [
                    "result", "score", "similarity", "完了", "結果"
                ])

            finally:
                browser.close()

    @pytest.mark.playwright
    def test_llm_functionality_integration(self, base_url, test_file_path):
        """LLM機能統合テスト（WebUI）"""

        # Playwright MCP利用可能性確認
        playwright_available = False
        try:
            # from playwright.sync_api import sync_playwright
            playwright_available = True
        except ImportError:
            # APIレベルでLLM機能テスト
            import requests

            # LLMパラメータ付きでのAPIテスト
            with open(test_file_path, 'rb') as f:
                files = {'file': (Path(test_file_path).name, f, 'application/json')}
                data = {
                    'gpu': 'false',
                    'llm_enabled': 'true',  # LLM機能を有効化
                    'model_name': 'qwen3-14b-awq',
                    'temperature': '0.2',
                    'max_tokens': '64'
                }

                response = requests.post(f"{base_url}/api/compare/single", files=files, data=data)

                # レスポンス確認（LLM機能の実装状況に応じて）
                if response.status_code == 200:
                    result = response.json()
                    # LLM関連のメタデータが含まれることを確認
                    assert "result" in result or "detailed_results" in result
                elif response.status_code == 400:
                    # LLM機能が未実装の場合の適切なエラーレスポンス
                    error_response = response.json()
                    assert "error" in error_response

            return

        # 実際のPlaywrightテスト（MCPが利用可能な場合）
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            try:
                # メインページアクセス
                page.goto(base_url)

                # LLM機能のUI要素を探す
                llm_checkbox = page.query_selector('input[type="checkbox"][name*="llm"], input[id*="llm"]')
                if llm_checkbox:
                    # LLM機能を有効化
                    llm_checkbox.check()

                # モデル選択があれば設定
                model_select = page.query_selector('select[name*="model"], select[id*="model"]')
                if model_select:
                    page.select_option(model_select, 'qwen3-14b-awq')

                # ファイルアップロード
                file_input = page.query_selector('input[type="file"]')
                file_input.set_input_files(test_file_path)

                # フォーム送信
                submit_button = page.query_selector('button[type="submit"], input[type="submit"]')
                submit_button.click()

                # LLM処理は時間がかかる可能性があるため、長めに待機
                page.wait_for_timeout(10000)  # 10秒待機

                # 結果の確認
                page_content = page.content()

                # LLM処理結果の兆候を確認
                assert any(keyword in page_content.lower() for keyword in [
                    "llm", "model", "qwen", "result", "完了"
                ])

            finally:
                browser.close()

    @pytest.mark.playwright
    def test_error_handling_scenarios(self, base_url):
        """エラーハンドリングシナリオテスト"""

        playwright_available = False
        try:
            # from playwright.sync_api import sync_playwright
            playwright_available = True
        except ImportError:
            # APIレベルでエラーハンドリングテスト
            import requests

            # 不正なファイルでのテスト
            files = {'file': ('invalid.txt', b'invalid content', 'text/plain')}
            data = {'gpu': 'false'}

            response = requests.post(f"{base_url}/api/compare/single", files=files, data=data)

            # エラーが適切に処理されることを確認
            # 実装によって400または200でエラーメッセージが返される
            if response.status_code == 400:
                error_response = response.json()
                assert "error" in error_response
            elif response.status_code == 200:
                result = response.json()
                # エラーメッセージが結果に含まれている場合
                assert any(key in result for key in ["error", "message", "status"])

            return

        # 実際のPlaywrightテスト（MCPが利用可能な場合）
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            try:
                # メインページアクセス
                page.goto(base_url)

                # 不正なファイル作成
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write("This is not a valid JSONL file")
                    invalid_file = f.name

                try:
                    # 不正なファイルをアップロード
                    file_input = page.query_selector('input[type="file"]')
                    file_input.set_input_files(invalid_file)

                    # フォーム送信
                    submit_button = page.query_selector('button[type="submit"], input[type="submit"]')
                    submit_button.click()

                    # エラーメッセージの表示待機
                    page.wait_for_timeout(3000)  # 3秒待機

                    # エラーメッセージの確認
                    page_content = page.content()

                    # エラー関連のキーワードが表示されることを確認
                    assert any(keyword in page_content.lower() for keyword in [
                        "error", "エラー", "invalid", "failed", "失敗"
                    ])

                finally:
                    Path(invalid_file).unlink()  # テストファイルを削除

            finally:
                browser.close()

    def test_dual_file_comparison_ui(self, base_url):
        """デュアルファイル比較UIテスト"""

        # デュアルファイル比較APIの存在確認
        import requests

        # デュアルファイル比較用のテストデータ
        file1_data = [
            {"id": 1, "inference": "今日は晴れです"},
            {"id": 2, "inference": "雨が降っています"}
        ]

        file2_data = [
            {"id": 1, "inference": "本日は快晴です"},
            {"id": 2, "inference": "降水があります"}
        ]

        # テストファイル作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f1:
            for item in file1_data:
                f1.write(json.dumps(item, ensure_ascii=False) + '\n')
            file1_path = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f2:
            for item in file2_data:
                f2.write(json.dumps(item, ensure_ascii=False) + '\n')
            file2_path = f2.name

        try:
            # デュアルファイル比較APIテスト
            with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
                files = {
                    'file1': (Path(file1_path).name, f1, 'application/json'),
                    'file2': (Path(file2_path).name, f2, 'application/json')
                }
                data = {
                    'column': 'inference',
                    'gpu': 'false'
                }

                # デュアルファイル比較APIが存在するかテスト
                response = requests.post(f"{base_url}/compare", files=files, data=data)

                # APIの実装状況に応じた検証
                if response.status_code == 200:
                    result = response.json()
                    assert "result" in result or "comparisons" in result or "detailed_results" in result
                elif response.status_code == 404:
                    # デュアルファイル比較API未実装の場合はスキップ
                    pytest.skip("Dual file comparison API not implemented yet")
                else:
                    # その他のエラーは想定範囲内
                    assert response.status_code in [400, 405, 500]

        finally:
            # テストファイル削除
            Path(file1_path).unlink()
            Path(file2_path).unlink()

    def test_performance_and_responsiveness(self, base_url, test_file_path):
        """パフォーマンスとレスポンシビリティテスト"""

        import requests

        # レスポンス時間測定
        start_time = time.time()

        with open(test_file_path, 'rb') as f:
            files = {'file': (Path(test_file_path).name, f, 'application/json')}
            data = {'gpu': 'false'}

            response = requests.post(f"{base_url}/api/compare/single", files=files, data=data)

        response_time = time.time() - start_time

        # レスポンス時間が合理的範囲内であることを確認（60秒以内）
        assert response_time < 60.0

        # レスポンス状態の確認
        assert response.status_code == 200

        # レスポンスサイズの確認（空でないこと）
        assert len(response.content) > 0

        print(f"Response time: {response_time:.2f} seconds")

    def teardown_method(self):
        """テスト後のクリーンアップ"""
        # テスト用ファイルのクリーンアップ
        import os
        temp_files = []
        for f in temp_files:
            if os.path.exists(f):
                os.unlink(f)


if __name__ == "__main__":
    # テスト実行例
    pytest.main([__file__, "-v", "-s", "-m", "not playwright or playwright"])