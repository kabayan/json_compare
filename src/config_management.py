"""Task 7.1: YAML設定ファイル管理システム

LLM設定ファイルの管理、読み込み、マージ、バリデーション機能を提供
Requirements: 7.1, 7.2, 7.3, 7.4, 7.5

このモジュールは以下の機能を提供します：
- デフォルト設定ファイルの自動生成
- YAML設定ファイルの読み込みとパース
- 環境変数、CLIオプション、設定ファイルの優先順位管理
- 設定のバリデーションとエラーレポート
- 設定プロファイルの管理（開発/本番環境）
"""

import os
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
import copy
import datetime
from glob import glob

logger = logging.getLogger(__name__)


class ConfigManagerError(Exception):
    """設定管理関連のベースエラー"""
    pass


class ConfigValidationError(ConfigManagerError):
    """設定バリデーションエラー"""
    pass


class ConfigMergeError(ConfigManagerError):
    """設定マージエラー"""
    pass


@dataclass
class LLMConfigManager:
    """LLM設定ファイル管理クラス

    YAML設定ファイルの読み込み、マージ、バリデーション、保存機能を提供
    """
    config_dir: Path = field(default_factory=lambda: Path("config"))
    config_filename: str = "llm_config.yaml"
    current_config: Optional[Dict[str, Any]] = field(default=None, init=False)

    def __post_init__(self):
        """初期化後処理"""
        self.config_dir = Path(self.config_dir)
        self.config_file_path = self.config_dir / self.config_filename

    def get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を取得

        Returns:
            デフォルトLLM設定辞書
        """
        return {
            "llm_config": {
                "api": {
                    "url": "http://192.168.1.18:8000/v1/chat/completions",
                    "auth_token": "EMPTY",
                    "timeout": 30
                },
                "model": {
                    "name": "qwen3-14b-awq",
                    "temperature": 0.2,
                    "max_tokens": 64
                },
                "retry": {
                    "max_attempts": 3,
                    "backoff_factor": 2,
                    "max_delay": 10
                },
                "fallback": {
                    "auto_fallback": True,
                    "prompt_user": True
                }
            }
        }

    def generate_default_config_file(self) -> Path:
        """デフォルト設定ファイルを生成

        Requirement 7.1: 初回実行時のデフォルト設定ファイル生成

        Returns:
            生成された設定ファイルのパス
        """
        # 設定ディレクトリを作成
        self.config_dir.mkdir(parents=True, exist_ok=True)

        default_config = self.get_default_config()

        with open(self.config_file_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                default_config,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )

        logger.info(f"デフォルト設定ファイルを生成: {self.config_file_path}")
        return self.config_file_path

    def load_config_file(self, config_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """設定ファイルを読み込み

        Requirement 7.2: 設定ファイルの読み込み

        Args:
            config_path: 設定ファイルパス（省略時はデフォルト）

        Returns:
            読み込んだ設定辞書、またはNone（ファイル不在時）

        Raises:
            ConfigManagerError: YAML解析エラー時
        """
        if config_path is None:
            config_path = self.config_file_path

        if not config_path.exists():
            logger.warning(f"設定ファイルが見つかりません: {config_path}")
            return None

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"設定ファイルを読み込み: {config_path}")
                return config
        except yaml.YAMLError as e:
            raise ConfigManagerError(f"YAML解析エラー: {e}")

    def validate_config(self, config: Dict[str, Any]) -> None:
        """設定の妥当性を検証

        Requirement 7.3: 設定バリデーション

        Args:
            config: 検証する設定辞書

        Raises:
            ConfigValidationError: バリデーションエラー時
        """
        errors = self._collect_validation_errors(config)

        if errors:
            raise ConfigValidationError("; ".join(errors))

    def _collect_validation_errors(self, config: Dict[str, Any]) -> List[str]:
        """設定検証エラーを収集

        Args:
            config: 検証する設定辞書

        Returns:
            エラーメッセージのリスト
        """
        errors = []

        if "llm_config" not in config:
            errors.append("'llm_config'セクションが必要です")
            return errors  # 基本構造がない場合は早期リターン

        llm_config = config["llm_config"]

        # モデル設定の検証
        errors.extend(self._validate_model_config(llm_config.get("model", {})))

        # API設定の検証
        errors.extend(self._validate_api_config(llm_config.get("api", {})))

        # リトライ設定の検証
        errors.extend(self._validate_retry_config(llm_config.get("retry", {})))

        # フォールバック設定の検証
        errors.extend(self._validate_fallback_config(llm_config.get("fallback", {})))

        return errors

    def _validate_model_config(self, model_config: Dict[str, Any]) -> List[str]:
        """モデル設定の検証"""
        errors = []

        # temperature検証（0-1の範囲）
        if "temperature" in model_config:
            temp = model_config["temperature"]
            if not isinstance(temp, (int, float)) or not (0 <= temp <= 1):
                errors.append("temperatureは0.0-1.0の範囲で指定してください")

        # max_tokens検証（正数）
        if "max_tokens" in model_config:
            max_tokens = model_config["max_tokens"]
            if not isinstance(max_tokens, int) or max_tokens <= 0:
                errors.append("max_tokensは1以上の整数で指定してください")

        # モデル名検証
        if "name" in model_config:
            name = model_config["name"]
            if not isinstance(name, str) or not name.strip():
                errors.append("model nameは空でない文字列である必要があります")

        return errors

    def _validate_api_config(self, api_config: Dict[str, Any]) -> List[str]:
        """API設定の検証"""
        errors = []

        # timeout検証（正数）
        if "timeout" in api_config:
            timeout = api_config["timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                errors.append("timeoutは正数で指定してください")

        # URL検証
        if "url" in api_config:
            url = api_config["url"]
            if not isinstance(url, str) or not url.strip():
                errors.append("API URLは空でない文字列である必要があります")
            elif not (url.startswith("http://") or url.startswith("https://")):
                errors.append("API URLはhttp://またはhttps://で始まる必要があります")

        return errors

    def _validate_retry_config(self, retry_config: Dict[str, Any]) -> List[str]:
        """リトライ設定の検証"""
        errors = []

        if "max_attempts" in retry_config:
            max_attempts = retry_config["max_attempts"]
            if not isinstance(max_attempts, int) or max_attempts < 1:
                errors.append("max_attemptsは1以上の整数で指定してください")

        if "backoff_factor" in retry_config:
            backoff_factor = retry_config["backoff_factor"]
            if not isinstance(backoff_factor, (int, float)) or backoff_factor <= 0:
                errors.append("backoff_factorは正数で指定してください")

        if "max_delay" in retry_config:
            max_delay = retry_config["max_delay"]
            if not isinstance(max_delay, (int, float)) or max_delay <= 0:
                errors.append("max_delayは正数で指定してください")

        return errors

    def _validate_fallback_config(self, fallback_config: Dict[str, Any]) -> List[str]:
        """フォールバック設定の検証"""
        errors = []

        if "auto_fallback" in fallback_config:
            auto_fallback = fallback_config["auto_fallback"]
            if not isinstance(auto_fallback, bool):
                errors.append("auto_fallbackはブール値で指定してください")

        if "prompt_user" in fallback_config:
            prompt_user = fallback_config["prompt_user"]
            if not isinstance(prompt_user, bool):
                errors.append("prompt_userはブール値で指定してください")

        return errors

    def deep_merge_configs(self, base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """設定辞書の深いマージ

        Args:
            base_config: ベース設定
            override_config: 上書き設定

        Returns:
            マージされた設定辞書
        """
        result = copy.deepcopy(base_config)

        def _deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    _deep_merge(target[key], value)
                else:
                    target[key] = value
            return target

        return _deep_merge(result, override_config)

    def merge_with_cli_options(self, cli_options: Dict[str, Any]) -> Dict[str, Any]:
        """CLIオプションで設定を上書き

        Requirement 7.2: CLIオプションでの上書き

        Args:
            cli_options: CLIオプション辞書

        Returns:
            マージされた設定辞書
        """
        base_config = self.load_config_file() or self.get_default_config()

        # CLIオプションを設定構造に変換
        cli_override = {"llm_config": {"model": {}, "api": {}}}

        if "model_name" in cli_options:
            cli_override["llm_config"]["model"]["name"] = cli_options["model_name"]
        if "temperature" in cli_options:
            cli_override["llm_config"]["model"]["temperature"] = cli_options["temperature"]
        if "max_tokens" in cli_options:
            cli_override["llm_config"]["model"]["max_tokens"] = cli_options["max_tokens"]

        return self.deep_merge_configs(base_config, cli_override)

    def get_final_config(self, cli_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """最終設定を取得

        Requirement 7.4: 環境変数 > CLIオプション > 設定ファイルの優先順位

        Args:
            cli_options: CLIオプション辞書

        Returns:
            最終設定辞書
        """
        # 1. ベース設定（設定ファイル or デフォルト）
        base_config = self.load_config_file() or self.get_default_config()

        # 2. CLIオプションでの上書き
        if cli_options:
            base_config = self.merge_with_cli_options(cli_options)

        # 3. 環境変数での上書き（最高優先度）
        env_override = {"llm_config": {"model": {}, "api": {}}}

        if "VLLM_API_URL" in os.environ:
            env_override["llm_config"]["api"]["url"] = os.environ["VLLM_API_URL"]
        if "LLM_MODEL_NAME" in os.environ:
            env_override["llm_config"]["model"]["name"] = os.environ["LLM_MODEL_NAME"]
        if "LLM_TEMPERATURE" in os.environ:
            try:
                temp = float(os.environ["LLM_TEMPERATURE"])
                env_override["llm_config"]["model"]["temperature"] = temp
            except ValueError:
                logger.warning("環境変数LLM_TEMPERATUREが無効な値です")

        final_config = self.deep_merge_configs(base_config, env_override)

        # バリデーション
        self.validate_config(final_config)

        return final_config

    def set_current_config(self, config: Dict[str, Any]) -> None:
        """現在の設定を設定

        Args:
            config: 設定辞書
        """
        self.current_config = config

    def save_current_config(self, output_path: Optional[Path] = None) -> Path:
        """現在の設定を保存

        Requirement 7.5: --save-config機能

        Args:
            output_path: 出力パス（省略時はデフォルト）

        Returns:
            保存されたファイルパス
        """
        if output_path is None:
            output_path = self.config_file_path

        if self.current_config is None:
            self.current_config = self.get_default_config()

        # ディレクトリ作成
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                self.current_config,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )

        logger.info(f"設定を保存: {output_path}")
        return output_path

    def save_profile(self, profile_name: str, config: Dict[str, Any]) -> Path:
        """設定プロファイルを保存

        Task 7.2 の一部: 設定プロファイル管理

        Args:
            profile_name: プロファイル名
            config: 設定辞書

        Returns:
            保存されたファイルパス
        """
        profile_path = self.config_dir / f"llm_config_{profile_name}.yaml"

        # ディレクトリ作成
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        with open(profile_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                config,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )

        logger.info(f"プロファイル '{profile_name}' を保存: {profile_path}")
        return profile_path

    def load_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """設定プロファイルを読み込み

        Task 7.2 の一部: 設定プロファイル管理

        Args:
            profile_name: プロファイル名

        Returns:
            プロファイル設定辞書、またはNone
        """
        profile_path = self.config_dir / f"llm_config_{profile_name}.yaml"

        if not profile_path.exists():
            logger.warning(f"プロファイル '{profile_name}' が見つかりません: {profile_path}")
            return None

        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"プロファイル '{profile_name}' を読み込み: {profile_path}")
                return config
        except yaml.YAMLError as e:
            raise ConfigManagerError(f"プロファイル '{profile_name}' のYAML解析エラー: {e}")

    def export_config(
        self,
        format: str = "yaml",
        output_path: Optional[Path] = None,
        include_metadata: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """設定をエクスポート

        Task 7.2の一部: 設定のエクスポート機能

        Args:
            format: エクスポート形式（"json"または"yaml"）
            output_path: 出力パス（省略時は自動生成）
            include_metadata: メタデータを含めるかどうか
            metadata: 追加するメタデータ

        Returns:
            エクスポートされたファイルのパス

        Raises:
            ConfigManagerError: エクスポートに失敗した場合
        """
        if format not in ["json", "yaml"]:
            raise ConfigManagerError(f"サポートされていないエクスポート形式: {format}")

        if self.current_config is None:
            self.current_config = self.get_default_config()

        # 出力パスの決定
        if output_path is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"llm_config_export_{timestamp}.{format}"
            output_path = self.config_dir / filename

        # エクスポート用設定の準備
        export_data = copy.deepcopy(self.current_config)

        if include_metadata:
            export_metadata = {
                "exported_at": datetime.datetime.now().isoformat(),
                "exported_by": os.getenv("USER", "unknown"),
                "export_format": format,
                "export_version": "1.0"
            }
            if metadata:
                export_metadata.update(metadata)
            export_data["export_metadata"] = export_metadata

        # ディレクトリ作成
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if format == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            else:  # yaml
                with open(output_path, 'w', encoding='utf-8') as f:
                    yaml.dump(
                        export_data,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False
                    )

            logger.info(f"設定を{format}形式でエクスポート: {output_path}")
            return output_path

        except (IOError, OSError) as e:
            raise ConfigManagerError(f"エクスポートに失敗しました: {e}")

    def import_config(self, import_path: Path) -> Dict[str, Any]:
        """設定をインポート

        Task 7.2の一部: 設定のインポート機能

        Args:
            import_path: インポートするファイルのパス

        Returns:
            インポートされた設定辞書

        Raises:
            ConfigManagerError: インポートに失敗した場合
        """
        import_path = Path(import_path)

        if not import_path.exists():
            raise ConfigManagerError(f"インポートファイルが見つかりません: {import_path}")

        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                if import_path.suffix.lower() == ".json":
                    config = json.load(f)
                elif import_path.suffix.lower() in [".yaml", ".yml"]:
                    config = yaml.safe_load(f)
                else:
                    raise ConfigManagerError(f"サポートされていないファイル形式: {import_path.suffix}")

            # メタデータを除去
            if "_metadata" in config:
                del config["_metadata"]
            if "export_metadata" in config:
                del config["export_metadata"]

            # バリデーション
            self.validate_config(config)

            # 現在の設定として設定
            self.set_current_config(config)

            logger.info(f"設定をインポート: {import_path}")
            return config

        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ConfigManagerError(f"設定ファイルの解析に失敗しました: {e}")
        except (IOError, OSError) as e:
            raise ConfigManagerError(f"ファイルの読み込みに失敗しました: {e}")

    def reset_to_default(self) -> Dict[str, Any]:
        """設定をデフォルト値にリセット

        Task 7.2の一部: デフォルト設定へのリセット機能

        Returns:
            デフォルト設定辞書
        """
        default_config = self.get_default_config()
        self.set_current_config(default_config)
        logger.info("設定をデフォルト値にリセット")
        return default_config

    def list_profiles(self) -> List[str]:
        """利用可能なプロファイル一覧を取得

        Task 7.2の一部: プロファイル管理機能

        Returns:
            プロファイル名のリスト
        """
        profile_pattern = str(self.config_dir / "llm_config_*.yaml")
        profile_files = glob(profile_pattern)

        profiles = []
        for profile_file in profile_files:
            # ファイル名からプロファイル名を抽出
            filename = Path(profile_file).stem
            if filename.startswith("llm_config_"):
                profile_name = filename[11:]  # "llm_config_"を除去
                profiles.append(profile_name)

        return sorted(profiles)

    def delete_profile(self, profile_name: str) -> bool:
        """プロファイルを削除

        Task 7.2の一部: プロファイル管理機能

        Args:
            profile_name: 削除するプロファイル名

        Returns:
            削除に成功したらTrue

        Raises:
            ConfigManagerError: 削除に失敗した場合
        """
        profile_path = self.config_dir / f"llm_config_{profile_name}.yaml"

        if not profile_path.exists():
            logger.warning(f"プロファイル '{profile_name}' が見つかりません: {profile_path}")
            return False

        try:
            profile_path.unlink()
            logger.info(f"プロファイル '{profile_name}' を削除: {profile_path}")
            return True
        except (IOError, OSError) as e:
            raise ConfigManagerError(f"プロファイルの削除に失敗しました: {e}")

    def compare_configs(self, config1: Dict[str, Any], config2: Dict[str, Any]) -> Dict[str, Any]:
        """2つの設定を比較し差分を取得

        Task 7.2の一部: 設定差分比較機能

        Args:
            config1: 比較する設定1
            config2: 比較する設定2

        Returns:
            差分情報を含む辞書
        """
        def _compare_nested_dict(d1: Dict[str, Any], d2: Dict[str, Any], path: str = "") -> Dict[str, Any]:
            """ネストした辞書の比較"""
            differences = {
                "added": {},
                "removed": {},
                "changed": {},
                "unchanged": {}
            }

            # d1にあってd2にないキー
            for key in d1.keys() - d2.keys():
                full_path = f"{path}.{key}" if path else key
                differences["removed"][full_path] = d1[key]

            # d2にあってd1にないキー
            for key in d2.keys() - d1.keys():
                full_path = f"{path}.{key}" if path else key
                differences["added"][full_path] = d2[key]

            # 両方にあるキー
            for key in d1.keys() & d2.keys():
                full_path = f"{path}.{key}" if path else key

                if isinstance(d1[key], dict) and isinstance(d2[key], dict):
                    # 再帰的に比較
                    nested_diff = _compare_nested_dict(d1[key], d2[key], full_path)
                    for diff_type in differences:
                        differences[diff_type].update(nested_diff[diff_type])
                elif d1[key] != d2[key]:
                    differences["changed"][full_path] = {
                        "old": d1[key],
                        "new": d2[key]
                    }
                else:
                    differences["unchanged"][full_path] = d1[key]

            return differences

        return _compare_nested_dict(config1, config2)

    def create_backup(self, backup_name: Optional[str] = None) -> Path:
        """設定のバックアップを作成

        Task 7.2の一部: バックアップ機能

        Args:
            backup_name: バックアップ名（省略時は自動生成）

        Returns:
            バックアップファイルのパス
        """
        if backup_name is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"

        backup_dir = self.config_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_path = backup_dir / f"{backup_name}.yaml"

        # 現在の設定ファイルが存在しない場合はデフォルト設定を使用
        current_config = self.load_config_file() or self.get_default_config()

        # メタデータ付きでバックアップ
        backup_data = copy.deepcopy(current_config)
        backup_data["_backup_metadata"] = {
            "created_at": datetime.datetime.now().isoformat(),
            "original_config_file": str(self.config_file_path),
            "backup_name": backup_name
        }

        with open(backup_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                backup_data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )

        logger.info(f"設定のバックアップを作成: {backup_path}")
        return backup_path

    def restore_from_backup(self, backup_path: Path) -> Dict[str, Any]:
        """バックアップから設定を復元

        Task 7.2の一部: バックアップからの復元機能

        Args:
            backup_path: バックアップファイルのパス

        Returns:
            復元された設定辞書

        Raises:
            ConfigManagerError: 復元に失敗した場合
        """
        backup_path = Path(backup_path)

        if not backup_path.exists():
            raise ConfigManagerError(f"バックアップファイルが見つかりません: {backup_path}")

        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = yaml.safe_load(f)

            # バックアップメタデータを除去
            if "_backup_metadata" in backup_data:
                del backup_data["_backup_metadata"]

            # バリデーション
            self.validate_config(backup_data)

            # 現在の設定として設定
            self.set_current_config(backup_data)

            # 設定ファイルに保存
            self.save_current_config()

            logger.info(f"バックアップから設定を復元: {backup_path}")
            return backup_data

        except yaml.YAMLError as e:
            raise ConfigManagerError(f"バックアップファイルの解析に失敗しました: {e}")
        except (IOError, OSError) as e:
            raise ConfigManagerError(f"バックアップファイルの読み込みに失敗しました: {e}")


# 便利関数
def create_default_config_if_missing(config_dir: Optional[Union[str, Path]] = None) -> Path:
    """デフォルト設定ファイルが存在しない場合に作成

    Requirement 7.1: 初回実行時の設定ファイル自動生成

    Args:
        config_dir: 設定ディレクトリ

    Returns:
        設定ファイルのパス
    """
    if config_dir is None:
        config_dir = Path("config")

    manager = LLMConfigManager(config_dir=config_dir)

    if not manager.config_file_path.exists():
        return manager.generate_default_config_file()
    else:
        return manager.config_file_path