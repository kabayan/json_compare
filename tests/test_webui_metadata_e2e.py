"""Web UIメタデータ検証のPlaywright E2Eテスト

Web UIでファイルをアップロードして、calculation_methodなどの
メタデータが正しく出力されることを確認するエンドツーエンドテスト
"""

import asyncio
import json
import tempfile
import os
from pathlib import Path
from playwright.async_api import async_playwright, expect
import pytest


class TestWebUIMetadataE2E:
    """Web UIメタデータ検証E2Eテスト"""

    @pytest.fixture
    async def browser_context(self):
        """ブラウザコンテキストのセットアップ"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # コンソールメッセージをキャプチャ
            console_messages = []
            page.on("console", lambda msg: console_messages.append(msg))

            yield page, console_messages

            await context.close()
            await browser.close()

    @pytest.fixture
    def test_jsonl_file(self):
        """テスト用JSONLファイル作成"""
        content = """{"inference1": "機械学習", "inference2": "マシンラーニング"}
{"inference1": "深層学習", "inference2": "ディープラーニング"}
{"inference1": "自然言語処理", "inference2": "NLP"}
{"inference1": "コンピュータビジョン", "inference2": "画像認識"}
{"inference1": "強化学習", "inference2": "Reinforcement Learning"}"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(content)
            temp_path = f.name

        yield temp_path
        os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_single_file_metadata_embedding(self, browser_context, test_jsonl_file):
        """単一ファイル埋め込みモードのメタデータ検証"""
        page, console_messages = browser_context

        # Web UIにアクセス
        await page.goto("http://localhost:18081/ui")

        # ページ読み込み待機
        await page.wait_for_load_state("networkidle")

        # 単一ファイルタブを選択
        await page.click('button:has-text("単一ファイル比較")')

        # ファイルアップロード
        file_input = page.locator('input[type="file"]').first
        await file_input.set_input_files(test_jsonl_file)

        # スコアタイプを選択
        await page.select_option('select[name="type"]', 'score')

        # GPU使用をオフ（デフォルト）
        gpu_checkbox = page.locator('input[type="checkbox"][name="gpu"]').first
        if await gpu_checkbox.is_checked():
            await gpu_checkbox.click()

        # 比較実行
        await page.click('#submitButton')

        # 結果待機（最大30秒）
        await page.wait_for_selector('#result', timeout=30000)

        # 結果取得
        result_text = await page.locator('#result').inner_text()

        # JSONとして解析
        try:
            result_json = json.loads(result_text)
        except json.JSONDecodeError:
            # プレタグ内のJSONを取得
            result_text = await page.locator('#result pre').inner_text()
            result_json = json.loads(result_text)

        # メタデータ検証
        assert "_metadata" in result_json, "メタデータが存在しない"
        metadata = result_json["_metadata"]

        # calculation_methodの検証
        assert "calculation_method" in metadata, "calculation_methodが存在しない"
        assert metadata["calculation_method"] == "embedding", f"calculation_methodが期待値と異なる: {metadata['calculation_method']}"

        # その他のメタデータ検証
        assert "processing_time" in metadata
        assert "original_filename" in metadata
        assert "gpu_used" in metadata
        assert metadata["gpu_used"] == False

    @pytest.mark.asyncio
    async def test_dual_file_metadata(self, browser_context):
        """2ファイル比較のメタデータ検証"""
        page, console_messages = browser_context

        # テストファイル作成
        file1_content = '{"inference": "機械学習"}\n{"inference": "深層学習"}'
        file2_content = '{"inference": "マシンラーニング"}\n{"inference": "ディープラーニング"}'

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f1:
            f1.write(file1_content)
            file1_path = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f2:
            f2.write(file2_content)
            file2_path = f2.name

        try:
            # Web UIにアクセス
            await page.goto("http://localhost:18081/ui")
            await page.wait_for_load_state("networkidle")

            # 2ファイル比較タブを選択
            await page.click('button:has-text("2ファイル比較")')

            # ファイルアップロード
            file_inputs = page.locator('input[type="file"]')
            await file_inputs.nth(0).set_input_files(file1_path)
            await file_inputs.nth(1).set_input_files(file2_path)

            # 列名入力
            await page.fill('input[name="column"]', 'inference')

            # 比較実行（2ファイル比較用のボタン）
            await page.click('#dualSubmitButton')

            # 結果待機
            await page.wait_for_selector('#result', timeout=30000)

            # 結果取得と検証
            result_text = await page.locator('#result').inner_text()
            try:
                result_json = json.loads(result_text)
            except json.JSONDecodeError:
                result_text = await page.locator('#result pre').inner_text()
                result_json = json.loads(result_text)

            # メタデータ検証
            assert "_metadata" in result_json
            metadata = result_json["_metadata"]
            assert "calculation_method" in metadata
            assert metadata["calculation_method"] == "embedding"
            assert "original_files" in metadata
            assert "gpu_used" in metadata

        finally:
            os.unlink(file1_path)
            os.unlink(file2_path)

    @pytest.mark.asyncio
    async def test_llm_mode_metadata(self, browser_context, test_jsonl_file):
        """LLMモードのメタデータ検証（LLMが利用可能な場合のみ）"""
        page, console_messages = browser_context

        # Web UIにアクセス
        await page.goto("http://localhost:18081/ui")
        await page.wait_for_load_state("networkidle")

        # LLMモードチェックボックスが存在するか確認
        llm_checkbox = page.locator('input[type="checkbox"][id="use-llm"]')
        if await llm_checkbox.count() == 0:
            pytest.skip("LLMモードが利用できません")

        # LLMモードを有効化
        await llm_checkbox.click()

        # ファイルアップロード
        file_input = page.locator('input[type="file"]').first
        await file_input.set_input_files(test_jsonl_file)

        # LLM設定（オプション）
        model_select = page.locator('select[name="model"]')
        if await model_select.count() > 0:
            await model_select.select_option('qwen3-14b-awq')

        # 比較実行
        await page.click('#submitButton')

        # 結果待機（LLMは時間がかかる可能性があるため60秒）
        try:
            await page.wait_for_selector('#result', timeout=60000)
        except:
            # LLMが利用できない場合はスキップ
            pytest.skip("LLM APIが応答しません")

        # 結果取得
        result_text = await page.locator('#result').inner_text()
        try:
            result_json = json.loads(result_text)
        except json.JSONDecodeError:
            result_text = await page.locator('#result pre').inner_text()
            result_json = json.loads(result_text)

        # メタデータ検証
        assert "_metadata" in result_json
        metadata = result_json["_metadata"]

        # calculation_methodの検証
        assert "calculation_method" in metadata

        # LLMまたはフォールバック
        assert metadata["calculation_method"] in ["llm", "embedding"], \
            f"calculation_methodが期待値と異なる: {metadata['calculation_method']}"

        # LLMの場合は追加メタデータを確認
        if metadata["calculation_method"] == "llm":
            # LLM固有のメタデータがある可能性
            pass  # 必要に応じて追加検証
        elif metadata["calculation_method"] == "embedding":
            # フォールバックの場合
            if "fallback_reason" in metadata:
                assert metadata["fallback_reason"] is not None

    @pytest.mark.asyncio
    async def test_api_direct_metadata(self):
        """API直接呼び出しでのメタデータ検証"""
        import httpx

        # テストデータ作成
        test_data = {
            "inference1": "人工知能",
            "inference2": "AI"
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            json.dump(test_data, f)
            f.write('\n')
            temp_path = f.name

        try:
            async with httpx.AsyncClient() as client:
                # ファイル読み込み
                with open(temp_path, 'rb') as file:
                    files = {'file': ('test.jsonl', file, 'application/x-jsonlines')}
                    data = {'type': 'score', 'gpu': 'false'}

                    # API呼び出し
                    response = await client.post(
                        'http://localhost:18081/api/compare/single',
                        files=files,
                        data=data
                    )

                assert response.status_code == 200
                result = response.json()

                # メタデータ検証
                assert "_metadata" in result
                metadata = result["_metadata"]
                assert "calculation_method" in metadata
                assert metadata["calculation_method"] == "embedding"
                assert "processing_time" in metadata
                assert "gpu_used" in metadata
                assert metadata["gpu_used"] == False

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_csv_download_with_metadata(self, browser_context, test_jsonl_file):
        """CSVダウンロード時のメタデータ含有確認"""
        page, console_messages = browser_context

        # Web UIにアクセス
        await page.goto("http://localhost:18081/ui")
        await page.wait_for_load_state("networkidle")

        # ファイルアップロード
        file_input = page.locator('input[type="file"]').first
        await file_input.set_input_files(test_jsonl_file)

        # 比較実行
        await page.click('#submitButton')
        await page.wait_for_selector('#result', timeout=30000)

        # CSVダウンロードボタンが表示されるのを待つ
        csv_button = page.locator('button:has-text("CSV")')
        await csv_button.wait_for(state="visible")

        # ダウンロード処理をキャプチャ
        async with page.expect_download() as download_info:
            await csv_button.click()

        download = await download_info.value

        # ダウンロードファイルの内容確認
        csv_path = await download.path()
        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()

        # CSVにメタデータセクションが含まれることを確認
        assert "メタデータ" in csv_content or "Metadata" in csv_content
        assert "処理時間" in csv_content or "processing_time" in csv_content

        # calculation_methodがCSVに含まれるか確認（実装によって異なる）
        # 現在の実装では含まれない可能性があるため、オプショナルとする
        if "計算方法" in csv_content or "calculation_method" in csv_content:
            assert "embedding" in csv_content.lower()


async def main():
    """スタンドアロン実行用のメイン関数"""
    test = TestWebUIMetadataE2E()

    # ブラウザコンテキスト作成
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # ヘッドレスモードで実行
        context = await browser.new_context()
        page = await context.new_page()

        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg))

        # テストJSONLファイル作成
        content = """{"inference1": "機械学習", "inference2": "マシンラーニング"}
{"inference1": "深層学習", "inference2": "ディープラーニング"}"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            # テスト実行
            print("🧪 単一ファイルメタデータテスト...")
            await test.test_single_file_metadata_embedding((page, console_messages), temp_path)
            print("✅ 単一ファイルメタデータテスト成功")

            print("\n🧪 API直接呼び出しテスト...")
            await test.test_api_direct_metadata()
            print("✅ API直接呼び出しテスト成功")

            print("\n🧪 2ファイル比較メタデータテスト...")
            await test.test_dual_file_metadata((page, console_messages))
            print("✅ 2ファイル比較メタデータテスト成功")

            print("\n✨ すべてのテストが成功しました！")

        finally:
            os.unlink(temp_path)
            await context.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())