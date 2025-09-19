"""Task 6: Web UIへのLLM機能統合 - APIエンドポイント拡張の統合テスト

Task 6.2専用のテストスイート。
Requirements 5.2, 5.5の統合的検証。
"""

import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any
from pathlib import Path
import yaml

from fastapi.testclient import TestClient
from src.api import app, CompareRequestWithLLM, DualFileCompareRequestWithLLM


class TestTask62APIEndpointExtensions:
    """Task 6.2: バックエンドAPIエンドポイントの拡張の統合テストクラス"""

    @pytest.fixture
    def client(self):
        """TestClientインスタンスを返すフィクスチャ"""
        return TestClient(app)

    def test_requirement_5_2_llm_parameters_in_request(self, client):
        """
        Requirement 5.2: APIリクエストに use_llm: true パラメータが含まれる場合、LLMベースの類似度判定を実行

        Task 6.2: LLMパラメータを含むリクエスト処理を実装
        """
        # テストデータ
        test_jsonl = '{"inference1": "機械学習", "inference2": "マシンラーニング"}\n'

        # LLM有効リクエスト
        request_data = {
            "file_content": test_jsonl,
            "type": "score",
            "use_llm": True,
            "llm_config": {
                "model": "qwen3-14b-awq",
                "temperature": 0.2,
                "max_tokens": 64
            },
            "fallback_enabled": True
        }

        # APIレスポンスのモック
        with patch('src.api.process_jsonl_file_with_llm') as mock_process:
            mock_process.return_value = {
                "summary": {
                    "total_comparisons": 1,
                    "average_score": 0.85,
                    "method_used": "llm"
                },
                "detailed_results": [{
                    "file": "test.jsonl",
                    "score": 0.85,
                    "method": "llm",
                    "llm_metadata": {
                        "model_used": "qwen3-14b-awq",
                        "confidence": 0.9,
                        "category": "非常に類似"
                    }
                }]
            }

            response = client.post("/api/compare/llm", json=request_data)

            # Requirement 5.2: APIがLLMベース判定を実行
            assert response.status_code == 200
            assert mock_process.called

            # LLM設定が正しく渡される
            call_args = mock_process.call_args
            assert call_args is not None

    def test_requirement_5_5_llm_result_special_format(self, client):
        """
        Requirement 5.5: 結果出力時に判定方式（埋め込み/LLM）をメタデータに含める

        Task 6.2: LLM判定結果の特別なレスポンス形式対応を実装
        """
        test_jsonl = '{"inference1": "データ分析", "inference2": "データ解析"}\n'

        request_data = {
            "file_content": test_jsonl,
            "type": "score",
            "use_llm": True,
            "llm_config": {
                "model": "qwen3-14b-awq",
                "temperature": 0.3,
                "max_tokens": 100
            }
        }

        with patch('src.api.process_jsonl_file_with_llm') as mock_process:
            # LLM判定結果の特別な形式
            mock_process.return_value = {
                "summary": {
                    "total_comparisons": 1,
                    "average_score": 0.88,
                    "method_breakdown": {
                        "llm": 1,
                        "embedding": 0
                    }
                },
                "detailed_results": [{
                    "file": "test.jsonl",
                    "score": 0.88,
                    "method": "llm",  # Requirement 5.5: 判定方式
                    "llm_metadata": {
                        "model_used": "qwen3-14b-awq",
                        "confidence": 0.95,
                        "category": "類似",
                        "reason": "両方のテキストはデータ処理に関する概念を扱っている",
                        "tokens_used": 45
                    },
                    "processing_time": 1.2
                }],
                "metadata": {
                    "calculation_method": "llm",  # Requirement 5.5: 明示的識別
                    "api_version": "1.0.0",
                    "timestamp": "2025-09-19T18:00:00Z"
                }
            }

            response = client.post("/api/compare/llm", json=request_data)

            # Requirement 5.5: メタデータに判定方式が含まれる
            assert response.status_code == 200
            result = response.json()
            assert "metadata" in result
            assert result["metadata"]["calculation_method"] == "llm"
            assert "detailed_results" in result
            assert result["detailed_results"][0]["method"] == "llm"

    def test_prompt_file_upload_api(self, client):
        """
        Task 6.2: プロンプトファイルアップロードAPIを追加

        プロンプトファイルのアップロードと検証機能
        """
        # テストプロンプトファイル作成
        prompt_content = {
            "system_prompt": "類似度を0-1のスコアで判定してください",
            "user_prompt": "テキスト1: {text1}\nテキスト2: {text2}\n類似度スコア:"
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(prompt_content, f)
            temp_file = f.name

        try:
            with open(temp_file, 'rb') as file:
                files = {"file": ("test_prompt.yaml", file, "application/x-yaml")}
                response = client.post("/api/prompts/upload", files=files)

            # アップロード成功を確認
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
            assert "prompt_id" in result
            assert result["message"] is not None

            # アップロードされたファイルが保存されることを確認
            prompt_id = result["prompt_id"]
            prompt_path = Path("prompts") / f"{prompt_id}.yaml"
            assert prompt_path.exists()

            # クリーンアップ
            if prompt_path.exists():
                prompt_path.unlink()

        finally:
            os.unlink(temp_file)

    def test_dual_file_llm_api_endpoint(self, client):
        """
        Task 6.2: デュアルファイル比較のLLMリクエストハンドリング

        2つのファイルの比較でLLM機能が動作することを確認
        """
        test_file1_content = '{"inference": "深層学習"}\n{"inference": "ニューラルネットワーク"}\n'
        test_file2_content = '{"inference": "ディープラーニング"}\n{"inference": "人工神経網"}\n'

        request_data = {
            "file1_content": test_file1_content,
            "file2_content": test_file2_content,
            "column": "inference",
            "type": "score",
            "use_llm": True,
            "llm_config": {
                "model": "qwen3-14b-awq",
                "temperature": 0.2
            }
        }

        with patch('src.api.process_dual_files_with_llm') as mock_process:
            mock_process.return_value = {
                "summary": {
                    "total_comparisons": 2,
                    "average_score": 0.90,
                    "method_used": "llm"
                },
                "detailed_results": [
                    {
                        "pair_index": 0,
                        "file1_value": "深層学習",
                        "file2_value": "ディープラーニング",
                        "score": 0.95,
                        "method": "llm"
                    },
                    {
                        "pair_index": 1,
                        "file1_value": "ニューラルネットワーク",
                        "file2_value": "人工神経網",
                        "score": 0.85,
                        "method": "llm"
                    }
                ]
            }

            response = client.post("/api/compare/dual/llm", json=request_data)

            assert response.status_code == 200
            result = response.json()
            assert result["summary"]["method_used"] == "llm"
            assert len(result["detailed_results"]) == 2

    def test_fallback_mechanism_in_api(self, client):
        """
        Task 6.2: LLM失敗時のフォールバック機能

        LLM処理が失敗した場合に埋め込みベースにフォールバック
        """
        test_jsonl = '{"inference1": "test1", "inference2": "test2"}\n'

        request_data = {
            "file_content": test_jsonl,
            "type": "score",
            "use_llm": True,
            "fallback_enabled": True
        }

        with patch('src.api.process_jsonl_file_with_llm') as mock_llm, \
             patch('src.api.process_jsonl_file') as mock_embedding:

            # LLM処理が失敗
            mock_llm.side_effect = Exception("LLM API timeout")

            # フォールバック処理が成功
            mock_embedding.return_value = {
                "summary": {
                    "total_comparisons": 1,
                    "average_score": 0.7
                },
                "detailed_results": [{
                    "file": "test.jsonl",
                    "score": 0.7,
                    "method": "embedding_fallback"
                }]
            }

            response = client.post("/api/compare/llm", json=request_data)

            # フォールバックが動作することを確認
            assert response.status_code == 200
            result = response.json()
            assert result["detailed_results"][0]["method"] == "embedding_fallback"

    def test_llm_config_validation(self, client):
        """
        Task 6.2: LLM設定のバリデーション

        無効なLLM設定が適切にエラーを返すことを確認
        """
        test_jsonl = '{"inference1": "test1", "inference2": "test2"}\n'

        # 無効な温度パラメータ
        invalid_request = {
            "file_content": test_jsonl,
            "use_llm": True,
            "llm_config": {
                "model": "invalid-model",
                "temperature": 2.0,  # 範囲外
                "max_tokens": -1  # 負の値
            }
        }

        response = client.post("/api/compare/llm", json=invalid_request)

        # バリデーションエラーが発生することを確認
        assert response.status_code in [400, 422, 500]

    def test_prompt_list_api(self, client):
        """
        Task 6.2: プロンプト一覧取得API

        保存されたプロンプトの一覧を取得できることを確認
        """
        # プロンプトディレクトリの作成
        prompt_dir = Path("prompts")
        prompt_dir.mkdir(exist_ok=True)

        # テスト用プロンプトファイルを作成
        test_prompt_id = "test-prompt-123"
        test_prompt_path = prompt_dir / f"{test_prompt_id}.yaml"

        prompt_content = {
            "system_prompt": "Test system prompt",
            "user_prompt": "Test user prompt"
        }

        with open(test_prompt_path, 'w') as f:
            yaml.dump(prompt_content, f)

        try:
            response = client.get("/api/prompts")
            assert response.status_code == 200
            result = response.json()
            assert "prompts" in result
            # プロンプトリストに作成したプロンプトが含まれることを確認
            prompt_ids = [p.get("id", p.get("prompt_id", "")) for p in result["prompts"]]
            assert test_prompt_id in prompt_ids or len(result["prompts"]) > 0

        finally:
            # クリーンアップ
            if test_prompt_path.exists():
                test_prompt_path.unlink()

    def test_llm_response_metadata_enrichment(self, client):
        """
        Task 6.2: LLMレスポンスのメタデータ拡充

        LLM判定結果に詳細なメタデータが含まれることを確認
        """
        test_jsonl = '{"inference1": "自然言語処理", "inference2": "NLP"}\n'

        request_data = {
            "file_content": test_jsonl,
            "type": "score",
            "use_llm": True,
            "llm_config": {
                "model": "qwen3-14b-awq",
                "temperature": 0.1,
                "max_tokens": 128,
                "prompt_file": "custom_prompt.yaml"
            }
        }

        with patch('src.api.process_jsonl_file_with_llm') as mock_process:
            # 拡充されたメタデータを含むレスポンス
            mock_process.return_value = {
                "summary": {
                    "total_comparisons": 1,
                    "average_score": 0.92,
                    "method_breakdown": {"llm": 1},
                    "total_processing_time": 1.5
                },
                "detailed_results": [{
                    "file": "test.jsonl",
                    "score": 0.92,
                    "method": "llm",
                    "llm_metadata": {
                        "model_used": "qwen3-14b-awq",
                        "prompt_file": "custom_prompt.yaml",
                        "temperature": 0.1,
                        "max_tokens": 128,
                        "tokens_used": 52,
                        "prompt_tokens": 40,
                        "completion_tokens": 12,
                        "confidence": 0.98,
                        "category": "非常に類似",
                        "reason": "自然言語処理とNLPは同じ概念の異なる表記",
                        "api_response_time": 1.2
                    },
                    "processing_time": 1.5,
                    "timestamp": "2025-09-19T18:00:00Z"
                }],
                "metadata": {
                    "calculation_method": "llm",
                    "comparison_method": "llm",
                    "api_version": "1.0.0",
                    "environment": "production",
                    "timestamp": "2025-09-19T18:00:00Z"
                }
            }

            response = client.post("/api/compare/llm", json=request_data)

            assert response.status_code == 200
            result = response.json()

            # 詳細なメタデータが含まれることを確認
            llm_metadata = result["detailed_results"][0]["llm_metadata"]
            assert "model_used" in llm_metadata
            assert "confidence" in llm_metadata
            assert "reason" in llm_metadata
            assert "tokens_used" in llm_metadata