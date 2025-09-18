"""プロンプトテンプレート管理システム

YAMLファイルベースのプロンプトテンプレートの読み込み、バリデーション、
変数置換機能を提供するモジュール。
"""

import yaml
import re
from pathlib import Path
from typing import Dict, Optional, Set, Any, Union
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class PromptTemplateError(Exception):
    """プロンプトテンプレート関連のエラー"""
    pass


class PromptTemplate:
    """プロンプトテンプレート管理クラス"""

    def __init__(self, enable_cache: bool = False):
        """
        PromptTemplateインスタンスを初期化

        Args:
            enable_cache: テンプレートのキャッシュを有効にするかどうか
        """
        self.enable_cache = enable_cache
        self._cache: Dict[str, Dict] = {}
        self._variable_pattern = re.compile(r'\{([^}]+)\}')

    def load_template(self, file_path: str) -> Dict[str, Any]:
        """
        YAMLテンプレートファイルを読み込む

        Args:
            file_path: テンプレートファイルのパス

        Returns:
            読み込んだテンプレートの辞書

        Raises:
            PromptTemplateError: ファイルが見つからない、または解析に失敗した場合
        """
        # キャッシュチェック
        if self.enable_cache and file_path in self._cache:
            logger.debug(f"キャッシュからテンプレートを読み込み: {file_path}")
            return self._cache[file_path]

        # ファイル存在チェック
        path = Path(file_path)
        if not path.exists():
            raise PromptTemplateError(f"テンプレートファイルが見つかりません: {file_path}")

        try:
            # YAMLファイルを読み込み
            with open(path, 'r', encoding='utf-8') as f:
                template = yaml.safe_load(f)

            # バリデーション
            self.validate_template(template)

            # キャッシュに保存
            if self.enable_cache:
                self._cache[file_path] = template

            logger.info(f"テンプレートを読み込みました: {file_path}")
            return template

        except yaml.YAMLError as e:
            raise PromptTemplateError(f"YAMLファイルの解析に失敗しました: {e}")
        except Exception as e:
            if isinstance(e, PromptTemplateError):
                raise
            raise PromptTemplateError(f"テンプレートファイルの読み込みに失敗: {e}")

    def validate_template(self, template: Dict[str, Any]) -> bool:
        """
        テンプレート構造を検証

        Args:
            template: 検証するテンプレート辞書

        Returns:
            検証に成功した場合はTrue

        Raises:
            PromptTemplateError: 検証に失敗した場合
        """
        # 必須フィールドのチェック
        required_fields = ["prompts"]
        missing_fields = [field for field in required_fields if field not in template]

        if missing_fields:
            raise PromptTemplateError(f"必須フィールド {', '.join(missing_fields)} が不足しています")

        # promptsセクションの検証
        if not isinstance(template["prompts"], dict):
            raise PromptTemplateError("promptsフィールドは辞書である必要があります")

        # システムプロンプトとユーザープロンプトの存在確認
        prompts = template["prompts"]
        if "system" not in prompts and "user" not in prompts:
            raise PromptTemplateError("少なくともsystemまたはuserプロンプトが必要です")

        return True

    def render(
        self,
        template_str: str,
        variables: Dict[str, Any],
        strict: bool = True,
        format_numbers: bool = False
    ) -> str:
        """
        テンプレート文字列の変数を置換

        Args:
            template_str: 置換するテンプレート文字列
            variables: 置換する変数の辞書
            strict: Trueの場合、不足している変数があるとエラー
            format_numbers: 数値のフォーマット指定を適用するかどうか

        Returns:
            変数置換後の文字列

        Raises:
            PromptTemplateError: strictモードで変数が不足している場合
        """
        # 必要な変数を抽出
        required_vars = self.extract_variables(template_str)

        # strictモードの場合、不足している変数をチェック
        if strict:
            missing_vars = required_vars - set(variables.keys())
            if missing_vars:
                raise PromptTemplateError(
                    f"必要な変数が不足しています: {', '.join(missing_vars)}"
                )

        # 変数置換を実行
        result = template_str

        for var_match in self._variable_pattern.finditer(template_str):
            var_expr = var_match.group(1)
            var_name = var_expr.split(':')[0].split('.')[0]  # フォーマット指定を除いた変数名

            if var_name in variables:
                value = variables[var_name]

                # 数値フォーマットの処理
                if format_numbers and ':' in var_expr:
                    format_spec = var_expr.split(':')[1]
                    try:
                        # フォーマット文字列を適用
                        if format_spec.endswith('f'):
                            # 浮動小数点フォーマット
                            decimal_places = int(format_spec[1:-1]) if format_spec[1:-1] else 2
                            value = f"{float(value):.{decimal_places}f}"
                        elif format_spec.endswith('%'):
                            # パーセント表記（.2fと仮定）
                            value = f"{float(value):.2f}"
                    except (ValueError, TypeError):
                        # フォーマットに失敗した場合は元の値を使用
                        pass

                # 置換を実行
                result = result.replace(f"{{{var_expr}}}", str(value))
            elif not strict:
                # strictモードでない場合は変数をそのまま残す
                logger.warning(f"変数 '{var_name}' が提供されていません")

        return result

    def extract_variables(self, template_str: str) -> Set[str]:
        """
        テンプレート文字列から必要な変数を抽出

        Args:
            template_str: テンプレート文字列

        Returns:
            必要な変数名のセット
        """
        matches = self._variable_pattern.findall(template_str)
        # フォーマット指定を除いた変数名を抽出
        variables = set()
        for match in matches:
            var_name = match.split(':')[0].split('.')[0]
            variables.add(var_name)

        return variables

    def create_default_template(self, output_dir: str) -> str:
        """
        デフォルトのテンプレートファイルを作成

        Args:
            output_dir: 出力ディレクトリのパス

        Returns:
            作成したファイルのパス
        """
        default_template = {
            "version": "1.0",
            "metadata": {
                "author": "json_compare",
                "description": "デフォルトの類似度判定プロンプトテンプレート",
                "created_at": "2025-09-18"
            },
            "prompts": {
                "system": "あなたは日本語テキストの意味的類似度を評価する専門家です。"
                         "2つのテキストを比較し、その類似度を客観的に判定してください。",
                "user": """以下の2つのテキストの類似度を評価してください。

テキスト1: {text1}
テキスト2: {text2}

類似度を以下の形式で回答してください：
- スコア: 0.0-1.0の数値（0.0=全く異なる、1.0=完全一致）
- カテゴリ: 完全一致/非常に類似/類似/やや類似/低い類似度
- 理由: 判定の根拠を簡潔に説明

回答例:
スコア: 0.85
カテゴリ: 非常に類似
理由: 両テキストは同じトピックについて述べており、主要な概念が一致しています。"""
            },
            "parameters": {
                "temperature": 0.2,
                "max_tokens": 64,
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            }
        }

        # 出力ディレクトリを作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # ファイルパスを決定
        output_file = output_path / "default_similarity.yaml"

        # YAMLファイルとして保存
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(
                default_template,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False
            )

        logger.info(f"デフォルトテンプレートを作成しました: {output_file}")
        return str(output_file)

    def merge_with_defaults(
        self,
        template: Dict[str, Any],
        defaults: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        テンプレートにデフォルト値をマージ

        Args:
            template: ユーザーのテンプレート
            defaults: デフォルト値の辞書

        Returns:
            マージ後のテンプレート
        """
        if defaults is None:
            # 基本的なデフォルト値
            defaults = {
                "version": "1.0",
                "parameters": {
                    "temperature": 0.2,
                    "max_tokens": 64
                }
            }

        # 深いマージを実行
        result = defaults.copy()
        self._deep_merge(result, template)

        return result

    def _deep_merge(self, target: Dict, source: Dict) -> None:
        """
        辞書を再帰的にマージ（内部メソッド）

        Args:
            target: マージ先の辞書
            source: マージ元の辞書
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def list_available_templates(self, directory: str) -> list[str]:
        """
        指定ディレクトリ内の利用可能なテンプレートファイルをリスト

        Args:
            directory: テンプレートディレクトリのパス

        Returns:
            テンプレートファイルのパスのリスト
        """
        template_dir = Path(directory)
        if not template_dir.exists():
            return []

        # YAMLファイルを検索
        templates = []
        for yaml_file in template_dir.glob("*.yaml"):
            templates.append(str(yaml_file))
        for yml_file in template_dir.glob("*.yml"):
            templates.append(str(yml_file))

        return sorted(templates)