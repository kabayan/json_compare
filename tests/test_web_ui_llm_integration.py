"""Web UI LLM機能統合のテスト

Task 6のTDD実装：Web UIへのLLM機能統合
- LLMベース判定チェックボックス
- プロンプトファイル選択インターフェース
- LLMモード時の追加設定フォーム
- バックエンドAPIの拡張
"""

import pytest
import tempfile
import json
import os
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from pathlib import Path

# 実装予定のモジュールをインポート
from src.api import app
from src.enhanced_cli import CLIConfig


class TestWebUILLMIntegration:
    """Web UI LLM統合のテスト"""

    @pytest.fixture
    def client(self):
        """FastAPIテストクライアント"""
        return TestClient(app)

    @pytest.fixture
    def temp_jsonl_file(self):
        """テスト用JSONLファイル"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            test_data = [
                {
                    "id": 1,
                    "inference1": '{"task": "データ処理"}',
                    "inference2": '{"task": "データの処理"}'
                }
            ]
            for data in test_data:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            temp_path = f.name

        yield temp_path
        os.unlink(temp_path)

    @pytest.fixture
    def temp_prompt_file(self):
        """テスト用プロンプトファイル"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            prompt_content = """
version: "1.0"
system_prompt: "あなたは2つのテキストの類似度を判定するAIアシスタントです。"
user_prompt: |
  以下の2つのテキストの類似度を評価してください：

  テキスト1: {text1}
  テキスト2: {text2}

  0.0から1.0のスコアで評価し、その理由も説明してください。
"""
            f.write(prompt_content)
            temp_path = f.name

        yield temp_path
        os.unlink(temp_path)

    def test_ui_includes_llm_checkbox(self, client):
        """UI画面にLLMベース判定チェックボックスが含まれることのテスト"""
        response = client.get("/ui")
        assert response.status_code == 200

        html_content = response.text

        # LLMチェックボックスの存在確認
        assert 'id="use_llm"' in html_content
        assert 'type="checkbox"' in html_content
        assert 'LLMベース判定を使用' in html_content

    def test_ui_includes_prompt_file_selection(self, client):
        """UI画面にプロンプトファイル選択オプションが含まれることのテスト"""
        response = client.get("/ui")
        assert response.status_code == 200

        html_content = response.text

        # プロンプトファイル選択の存在確認
        assert 'id="prompt_file"' in html_content
        assert 'accept=".yaml,.yml"' in html_content
        assert 'プロンプトファイル' in html_content

    def test_ui_includes_llm_config_form(self, client):
        """UI画面にLLM設定フォームが含まれることのテスト"""
        response = client.get("/ui")
        assert response.status_code == 200

        html_content = response.text

        # LLM設定フォームの存在確認
        assert 'id="model_name"' in html_content
        assert 'id="temperature"' in html_content
        assert 'id="max_tokens"' in html_content
        assert 'qwen3-14b-awq' in html_content  # デフォルトモデル

    def test_ui_llm_form_visibility_toggle(self, client):
        """LLMチェックボックスによるフォーム表示切り替えのテスト"""
        response = client.get("/ui")
        assert response.status_code == 200

        html_content = response.text

        # JavaScriptによる表示制御の確認
        assert 'id="llm_config_section"' in html_content
        assert 'toggleLLMConfig' in html_content
        assert 'display: none' in html_content  # 初期状態は非表示

    def test_api_compare_with_llm_parameters(self, client, temp_jsonl_file):
        """APIがLLMパラメータ付きリクエストを処理することのテスト"""
        from src.api import CompareRequestWithLLM

        request_data = {
            "file_content": Path(temp_jsonl_file).read_text(),
            "type": "score",
            "use_llm": True,
            "llm_config": {
                "model": "qwen3-14b-awq",
                "temperature": 0.3,
                "max_tokens": 128
            }
        }

        with patch('src.api.process_jsonl_file_with_llm') as mock_process:
            # モックレスポンスの設定
            mock_process.return_value = {
                "summary": {
                    "total_comparisons": 1,
                    "average_score": 0.9,
                    "method_breakdown": {"llm": 1}
                },
                "detailed_results": [
                    {
                        "file": "test_file.jsonl",
                        "score": 0.9,
                        "method": "llm",
                        "metadata": {"model_used": "qwen3-14b-awq"}
                    }
                ]
            }

            response = client.post("/api/compare/llm", json=request_data)

            assert response.status_code == 200
            result = response.json()
            assert result["summary"]["method_breakdown"]["llm"] == 1
            assert result["detailed_results"][0]["method"] == "llm"

    def test_api_prompt_upload(self, client, temp_prompt_file):
        """プロンプトファイルアップロードAPIのテスト"""
        with open(temp_prompt_file, 'rb') as f:
            response = client.post(
                "/api/prompts/upload",
                files={"file": ("test_prompt.yaml", f, "application/yaml")}
            )

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert "prompt_id" in result

    def test_api_prompt_list(self, client):
        """プロンプト一覧取得APIのテスト"""
        response = client.get("/api/prompts")

        assert response.status_code == 200
        result = response.json()
        assert "prompts" in result
        assert isinstance(result["prompts"], list)

        # デフォルトプロンプトが含まれることを確認
        prompt_names = [p["name"] for p in result["prompts"]]
        assert "default_similarity.yaml" in prompt_names

    def test_api_dual_file_compare_with_llm(self, client, temp_jsonl_file):
        """デュアルファイル比較でのLLM使用テスト"""
        request_data = {
            "file1_content": Path(temp_jsonl_file).read_text(),
            "file2_content": Path(temp_jsonl_file).read_text(),
            "column": "inference",
            "type": "score",
            "use_llm": True,
            "llm_config": {
                "model": "qwen3-14b-awq",
                "temperature": 0.2,
                "max_tokens": 64
            }
        }

        with patch('src.api.process_dual_files_with_llm') as mock_process:
            mock_process.return_value = {
                "summary": {
                    "total_comparisons": 1,
                    "average_score": 0.85,
                    "method_breakdown": {"llm": 1}
                },
                "detailed_results": []
            }

            response = client.post("/api/compare/dual/llm", json=request_data)

            assert response.status_code == 200
            result = response.json()
            assert result["summary"]["method_breakdown"]["llm"] == 1

    def test_api_error_handling_llm_failure(self, client, temp_jsonl_file):
        """LLM失敗時のエラーハンドリングテスト"""
        request_data = {
            "file_content": Path(temp_jsonl_file).read_text(),
            "type": "score",
            "use_llm": True,
            "fallback_enabled": False  # フォールバックを無効化してエラーをテスト
        }

        with patch('src.api.process_jsonl_file_with_llm') as mock_process:
            # LLM処理失敗をシミュレート
            mock_process.side_effect = Exception("LLM API connection failed")

            response = client.post("/api/compare/llm", json=request_data)

            assert response.status_code == 500
            error_detail = response.json()
            assert "detail" in error_detail
            assert "LLM API connection failed" in error_detail["detail"]


class TestLLMConfigValidation:
    """LLM設定検証のテスト"""

    def test_validate_llm_config_valid_parameters(self):
        """有効なLLM設定のバリデーションテスト"""
        from src.api import validate_llm_config

        config = {
            "model": "qwen3-14b-awq",
            "temperature": 0.3,
            "max_tokens": 128,
            "prompt_file": "custom_prompt.yaml"
        }

        # バリデーションが成功することを確認
        result = validate_llm_config(config)
        assert result is True

    def test_validate_llm_config_invalid_temperature(self):
        """無効な温度設定のバリデーションテスト"""
        from src.api import validate_llm_config

        config = {
            "model": "qwen3-14b-awq",
            "temperature": 1.5,  # 無効な値
            "max_tokens": 128
        }

        with pytest.raises(ValueError, match="temperature"):
            validate_llm_config(config)

    def test_validate_llm_config_invalid_max_tokens(self):
        """無効な最大トークン数のバリデーションテスト"""
        from src.api import validate_llm_config

        config = {
            "model": "qwen3-14b-awq",
            "temperature": 0.3,
            "max_tokens": 0  # 無効な値
        }

        with pytest.raises(ValueError, match="max_tokens"):
            validate_llm_config(config)

    def test_validate_prompt_file_format(self):
        """プロンプトファイル形式のバリデーションテスト"""
        from src.api import validate_prompt_file

        # 有効なプロンプトファイル
        valid_prompt = {
            "version": "1.0",
            "system_prompt": "You are an AI assistant.",
            "user_prompt": "Compare {text1} and {text2}."
        }

        result = validate_prompt_file(valid_prompt)
        assert result is True

        # 無効なプロンプトファイル（必須フィールド不足）
        invalid_prompt = {
            "version": "1.0"
            # user_prompt が不足
        }

        with pytest.raises(ValueError, match="user_prompt"):
            validate_prompt_file(invalid_prompt)


class TestUIInteractionFlow:
    """UI操作フローのテスト"""

    @pytest.fixture
    def client(self):
        """FastAPIテストクライアント"""
        return TestClient(app)

    @pytest.fixture
    def temp_jsonl_file(self):
        """テスト用JSONLファイル"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            test_data = [
                {
                    "id": 1,
                    "inference1": '{"task": "データ処理"}',
                    "inference2": '{"task": "データの処理"}'
                }
            ]
            for data in test_data:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            temp_path = f.name

        yield temp_path
        os.unlink(temp_path)

    @pytest.fixture
    def temp_prompt_file(self):
        """テスト用プロンプトファイル"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            prompt_content = """
version: "1.0"
system_prompt: "あなたは2つのテキストの類似度を判定するAIアシスタントです。"
user_prompt: |
  以下の2つのテキストの類似度を評価してください：

  テキスト1: {text1}
  テキスト2: {text2}

  0.0から1.0のスコアで評価し、その理由も説明してください。
"""
            f.write(prompt_content)
            temp_path = f.name

        yield temp_path
        os.unlink(temp_path)

    def test_complete_llm_workflow(self, client, temp_jsonl_file, temp_prompt_file):
        """完全なLLMワークフローのテスト"""
        # Step 1: プロンプトファイルのアップロード
        with open(temp_prompt_file, 'rb') as f:
            prompt_response = client.post(
                "/api/prompts/upload",
                files={"file": ("custom_prompt.yaml", f, "application/yaml")}
            )
        assert prompt_response.status_code == 200
        prompt_id = prompt_response.json()["prompt_id"]

        # Step 2: LLMベース比較の実行
        request_data = {
            "file_content": Path(temp_jsonl_file).read_text(),
            "type": "score",
            "use_llm": True,
            "prompt_id": prompt_id,
            "llm_config": {
                "model": "qwen3-14b-awq",
                "temperature": 0.2,
                "max_tokens": 64
            }
        }

        with patch('src.api.process_jsonl_file_with_llm') as mock_process:
            mock_process.return_value = {
                "summary": {"total_comparisons": 1, "average_score": 0.9},
                "detailed_results": [{"score": 0.9, "method": "llm"}]
            }

            compare_response = client.post("/api/compare/llm", json=request_data)

        assert compare_response.status_code == 200
        result = compare_response.json()
        assert result["summary"]["total_comparisons"] == 1

    def test_fallback_to_embedding_on_llm_failure(self, client, temp_jsonl_file):
        """LLM失敗時の埋め込みモードフォールバックテスト"""
        request_data = {
            "file_content": Path(temp_jsonl_file).read_text(),
            "type": "score",
            "use_llm": True,
            "fallback_enabled": True
        }

        with patch('src.api.process_jsonl_file_with_llm') as mock_llm_process:
            with patch('src.api.process_jsonl_file') as mock_embedding_process:
                # LLM処理を失敗させる
                mock_llm_process.side_effect = Exception("LLM API failed")

                # 埋め込み処理は成功させる
                mock_embedding_process.return_value = {
                    "summary": {"total_comparisons": 1, "average_score": 0.7},
                    "detailed_results": [{"score": 0.7, "method": "embedding_fallback"}]
                }

                response = client.post("/api/compare/llm", json=request_data)

        assert response.status_code == 200
        result = response.json()
        # フォールバックが機能し、埋め込みモードで処理されることを確認
        assert result["detailed_results"][0]["method"] == "embedding_fallback"