"""プロンプトテンプレート管理システムのテスト"""

import pytest
from pathlib import Path
import yaml
import tempfile
import os
from typing import Dict, Optional

# これから実装するモジュールをインポート
from src.prompt_template import PromptTemplate, PromptTemplateError


class TestPromptTemplate:
    """プロンプトテンプレート管理のテストクラス"""

    def test_load_yaml_template_file(self, tmp_path):
        """YAMLテンプレートファイルを読み込むテスト"""
        # テスト用のYAMLファイルを作成
        template_content = {
            "version": "1.0",
            "metadata": {
                "author": "test_user",
                "description": "テスト用テンプレート"
            },
            "prompts": {
                "system": "あなたは類似度判定の専門家です。",
                "user": "以下の2つのテキストの類似度を評価してください。\n\nテキスト1: {text1}\nテキスト2: {text2}"
            },
            "parameters": {
                "temperature": 0.2,
                "max_tokens": 64
            }
        }

        template_file = tmp_path / "test_template.yaml"
        with open(template_file, "w", encoding="utf-8") as f:
            yaml.dump(template_content, f, allow_unicode=True)

        # PromptTemplateインスタンスを作成して読み込み
        pt = PromptTemplate()
        loaded_template = pt.load_template(str(template_file))

        # アサーション
        assert loaded_template is not None
        assert loaded_template["version"] == "1.0"
        assert loaded_template["prompts"]["system"] == "あなたは類似度判定の専門家です。"
        assert loaded_template["parameters"]["temperature"] == 0.2

    def test_validate_template_structure(self):
        """テンプレート構造のバリデーションテスト"""
        pt = PromptTemplate()

        # 正しい構造のテンプレート
        valid_template = {
            "version": "1.0",
            "prompts": {
                "system": "System prompt",
                "user": "User prompt with {text1} and {text2}"
            }
        }
        assert pt.validate_template(valid_template) is True

        # 必須フィールドが欠けているテンプレート
        invalid_template = {
            "version": "1.0"
            # prompts フィールドが欠けている
        }
        with pytest.raises(PromptTemplateError, match="必須フィールド.*が不足"):
            pt.validate_template(invalid_template)

    def test_variable_substitution(self):
        """変数置換のテスト"""
        pt = PromptTemplate()

        # テンプレート文字列
        template_str = "比較対象:\nテキスト1: {text1}\nテキスト2: {text2}\n評価基準: {criteria}"

        # 変数辞書
        variables = {
            "text1": "これはサンプルテキスト1です",
            "text2": "これはサンプルテキスト2です",
            "criteria": "意味的類似度"
        }

        # 変数置換
        result = pt.render(template_str, variables)

        # アサーション
        assert "これはサンプルテキスト1です" in result
        assert "これはサンプルテキスト2です" in result
        assert "意味的類似度" in result
        assert "{text1}" not in result
        assert "{text2}" not in result

    def test_missing_template_file(self):
        """存在しないテンプレートファイルの処理テスト"""
        pt = PromptTemplate()

        # 存在しないファイルパス
        non_existent_file = "/tmp/non_existent_template.yaml"

        # エラーが適切に発生することを確認
        with pytest.raises(PromptTemplateError, match="テンプレートファイルが見つかりません"):
            pt.load_template(non_existent_file)

    def test_invalid_yaml_format(self, tmp_path):
        """不正なYAML形式の処理テスト"""
        # 不正なYAMLファイルを作成
        invalid_yaml_file = tmp_path / "invalid.yaml"
        with open(invalid_yaml_file, "w") as f:
            f.write("{ invalid: yaml: content: }")

        pt = PromptTemplate()

        # YAML解析エラーが適切に処理されることを確認
        with pytest.raises(PromptTemplateError, match="YAMLファイルの解析に失敗"):
            pt.load_template(str(invalid_yaml_file))

    def test_missing_variables_warning(self):
        """不足している変数の警告テスト"""
        pt = PromptTemplate()

        template_str = "テキスト1: {text1}\nテキスト2: {text2}\n基準: {criteria}"

        # 不完全な変数辞書
        variables = {
            "text1": "サンプル1"
            # text2とcriteriaが不足
        }

        # 警告付きで置換を実行
        result = pt.render(template_str, variables, strict=False)

        # 提供された変数は置換される
        assert "サンプル1" in result
        # 不足している変数はそのまま残る
        assert "{text2}" in result
        assert "{criteria}" in result

    def test_default_template_creation(self, tmp_path):
        """デフォルトテンプレートの作成テスト"""
        # デフォルトテンプレートのディレクトリ
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()

        pt = PromptTemplate()

        # デフォルトテンプレートを作成
        default_file = pt.create_default_template(str(template_dir))

        # ファイルが作成されたことを確認
        assert Path(default_file).exists()

        # 内容が正しいことを確認
        loaded = pt.load_template(default_file)
        assert loaded["prompts"]["system"] is not None
        assert loaded["prompts"]["user"] is not None
        assert "{text1}" in loaded["prompts"]["user"]
        assert "{text2}" in loaded["prompts"]["user"]

    def test_template_caching(self, tmp_path):
        """テンプレートのキャッシュ機能テスト"""
        # テスト用テンプレートファイル
        template_file = tmp_path / "cached_template.yaml"
        template_content = {
            "version": "1.0",
            "prompts": {
                "system": "システムプロンプト",
                "user": "ユーザープロンプト"
            }
        }

        with open(template_file, "w", encoding="utf-8") as f:
            yaml.dump(template_content, f, allow_unicode=True)

        pt = PromptTemplate(enable_cache=True)

        # 初回読み込み
        template1 = pt.load_template(str(template_file))

        # 2回目の読み込み（キャッシュから）
        template2 = pt.load_template(str(template_file))

        # 同じオブジェクトであることを確認
        assert template1 is template2

    def test_extract_required_variables(self):
        """テンプレートから必要な変数を抽出するテスト"""
        pt = PromptTemplate()

        template_str = "テキスト1: {text1}\nテキスト2: {text2}\n基準: {criteria}\n重複: {text1}"

        # 必要な変数を抽出
        variables = pt.extract_variables(template_str)

        # セットで返されることを確認（重複は除外）
        assert variables == {"text1", "text2", "criteria"}

    def test_template_with_special_characters(self):
        """特殊文字を含むテンプレートのテスト"""
        pt = PromptTemplate()

        # 特殊文字を含むテンプレート
        template_str = "評価: {score:.2f}%\n詳細: {details}"

        variables = {
            "score": 85.456,
            "details": "テスト\n改行\tタブ\"引用符'"
        }

        # 正しく置換されることを確認
        result = pt.render(template_str, variables, format_numbers=True)

        assert "85.46%" in result  # フォーマット指定が適用される
        assert "テスト\n改行\tタブ\"引用符'" in result