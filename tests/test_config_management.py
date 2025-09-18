"""Task 7.1: YAML設定ファイルの管理機能のテスト

TDD実装：設定ファイル管理システムのテスト
Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

import pytest
import tempfile
import os
import yaml
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.config_management import (
    LLMConfigManager,
    ConfigValidationError,
    ConfigMergeError,
    ConfigManagerError
)


class TestLLMConfigManager:
    """Requirement 7: 設定ファイル管理機能のテスト"""

    @pytest.fixture
    def temp_config_dir(self):
        """テスト用設定ディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"
            config_dir.mkdir(exist_ok=True)
            yield config_dir

    @pytest.fixture
    def sample_config_dict(self):
        """サンプル設定辞書"""
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

    def test_default_config_generation(self, temp_config_dir):
        """Requirement 7.1: デフォルト設定ファイル生成テスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # デフォルト設定ファイルが存在しない場合の生成
        default_config_path = temp_config_dir / "llm_config.yaml"
        assert not default_config_path.exists()

        config = config_manager.get_default_config()

        # 生成されたデフォルト設定をファイルに保存
        config_manager.generate_default_config_file()

        assert default_config_path.exists()

        # 生成された設定ファイルの内容確認
        with open(default_config_path, 'r', encoding='utf-8') as f:
            loaded_config = yaml.safe_load(f)

        assert "llm_config" in loaded_config
        assert "api" in loaded_config["llm_config"]
        assert "model" in loaded_config["llm_config"]
        assert loaded_config["llm_config"]["model"]["name"] == "qwen3-14b-awq"

    def test_config_file_loading(self, temp_config_dir, sample_config_dict):
        """Requirement 7.2: 設定ファイル読み込みテスト"""
        # サンプル設定ファイル作成
        config_file = temp_config_dir / "llm_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(sample_config_dict, f, default_flow_style=False, allow_unicode=True)

        config_manager = LLMConfigManager(config_dir=temp_config_dir)
        loaded_config = config_manager.load_config_file()

        assert loaded_config is not None
        assert loaded_config["llm_config"]["model"]["name"] == "qwen3-14b-awq"
        assert loaded_config["llm_config"]["api"]["timeout"] == 30

    def test_cli_option_override(self, temp_config_dir, sample_config_dict):
        """Requirement 7.2: CLIオプションによる設定上書きテスト"""
        # ベース設定ファイル作成
        config_file = temp_config_dir / "llm_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(sample_config_dict, f, default_flow_style=False, allow_unicode=True)

        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # CLIオプション（オーバーライド設定）
        cli_overrides = {
            "model_name": "custom-model",
            "temperature": 0.5,
            "max_tokens": 128
        }

        merged_config = config_manager.merge_with_cli_options(cli_overrides)

        # CLIオプションが優先されることを確認
        assert merged_config["llm_config"]["model"]["name"] == "custom-model"
        assert merged_config["llm_config"]["model"]["temperature"] == 0.5
        assert merged_config["llm_config"]["model"]["max_tokens"] == 128

        # 上書きされていない設定はそのまま
        assert merged_config["llm_config"]["api"]["timeout"] == 30

    def test_environment_variable_priority(self, temp_config_dir, sample_config_dict):
        """Requirement 7.4: 環境変数の優先順位テスト"""
        config_file = temp_config_dir / "llm_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(sample_config_dict, f, default_flow_style=False, allow_unicode=True)

        # 環境変数をモック
        env_vars = {
            "VLLM_API_URL": "http://custom-endpoint:8000/v1/chat/completions",
            "LLM_MODEL_NAME": "env-model",
            "LLM_TEMPERATURE": "0.8"
        }

        with patch.dict(os.environ, env_vars):
            config_manager = LLMConfigManager(config_dir=temp_config_dir)

            cli_overrides = {
                "temperature": 0.3  # CLIオプション
            }

            final_config = config_manager.get_final_config(cli_overrides)

            # 優先順位確認: 環境変数 > CLIオプション > 設定ファイル
            assert final_config["llm_config"]["api"]["url"] == "http://custom-endpoint:8000/v1/chat/completions"  # 環境変数
            assert final_config["llm_config"]["model"]["name"] == "env-model"  # 環境変数
            assert final_config["llm_config"]["model"]["temperature"] == 0.8  # 環境変数が最優先

    def test_config_validation(self, temp_config_dir):
        """Requirement 7.3: 設定バリデーションテスト"""
        # 不正な設定ファイル作成
        invalid_config = {
            "llm_config": {
                "model": {
                    "temperature": 2.0,  # 不正値（0-1範囲外）
                    "max_tokens": -10   # 不正値（負数）
                }
            }
        }

        config_file = temp_config_dir / "llm_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(invalid_config, f)

        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        with pytest.raises(ConfigValidationError) as exc_info:
            config_manager.validate_config(invalid_config)

        error_message = str(exc_info.value)
        assert "temperature" in error_message
        assert "max_tokens" in error_message

    def test_config_validation_success(self, temp_config_dir, sample_config_dict):
        """正しい設定のバリデーション成功テスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # 正常な設定では例外が発生しない
        try:
            config_manager.validate_config(sample_config_dict)
        except ConfigValidationError:
            pytest.fail("正常な設定でバリデーションエラーが発生")

    def test_save_current_config(self, temp_config_dir, sample_config_dict):
        """Requirement 7.5: --save-configフラグ機能テスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # 現在の設定として設定辞書を設定
        config_manager.set_current_config(sample_config_dict)

        # 設定を保存
        saved_path = config_manager.save_current_config()

        assert saved_path.exists()

        # 保存された設定の確認
        with open(saved_path, 'r', encoding='utf-8') as f:
            saved_config = yaml.safe_load(f)

        assert saved_config["llm_config"]["model"]["name"] == "qwen3-14b-awq"

    def test_config_file_not_found_error(self, temp_config_dir):
        """設定ファイル不在時のエラーハンドリング"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # 存在しない設定ファイルを読み込もうとするとNoneまたはデフォルト設定を返す
        loaded_config = config_manager.load_config_file()

        # ファイルが存在しない場合はNoneを返すかデフォルト設定を使用
        assert loaded_config is None or "llm_config" in loaded_config

    def test_invalid_yaml_format(self, temp_config_dir):
        """不正なYAMLファイル形式のエラーハンドリング"""
        # 壊れたYAMLファイル作成
        config_file = temp_config_dir / "llm_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write("invalid_yaml: [\n  unclosed_list\n")  # 不正なYAML

        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        with pytest.raises(ConfigManagerError) as exc_info:
            config_manager.load_config_file()

        assert "YAML" in str(exc_info.value) or "parse" in str(exc_info.value)

    def test_config_merge_logic(self, temp_config_dir, sample_config_dict):
        """設定マージロジックの詳細テスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # ベース設定
        base_config = sample_config_dict.copy()

        # 部分的な上書き設定
        override_config = {
            "llm_config": {
                "model": {
                    "temperature": 0.7  # この値だけ上書き
                },
                "api": {
                    "timeout": 60  # この値だけ上書き
                }
            }
        }

        merged = config_manager.deep_merge_configs(base_config, override_config)

        # マージ結果の確認
        assert merged["llm_config"]["model"]["temperature"] == 0.7  # 上書きされた
        assert merged["llm_config"]["model"]["name"] == "qwen3-14b-awq"  # 元の値保持
        assert merged["llm_config"]["api"]["timeout"] == 60  # 上書きされた
        assert merged["llm_config"]["api"]["url"] == "http://192.168.1.18:8000/v1/chat/completions"  # 元の値保持

    def test_config_profile_management(self, temp_config_dir):
        """設定プロファイル管理機能のテスト（Task 7.2の一部）"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # 開発環境プロファイル
        dev_profile = {
            "llm_config": {
                "api": {
                    "url": "http://localhost:8000/v1/chat/completions"
                },
                "model": {
                    "temperature": 0.1
                }
            }
        }

        # 本番環境プロファイル
        prod_profile = {
            "llm_config": {
                "api": {
                    "url": "http://production-server:8000/v1/chat/completions"
                },
                "model": {
                    "temperature": 0.0
                }
            }
        }

        # プロファイル保存
        config_manager.save_profile("development", dev_profile)
        config_manager.save_profile("production", prod_profile)

        # プロファイル読み込み確認
        loaded_dev = config_manager.load_profile("development")
        loaded_prod = config_manager.load_profile("production")

        assert loaded_dev["llm_config"]["api"]["url"] == "http://localhost:8000/v1/chat/completions"
        assert loaded_prod["llm_config"]["api"]["url"] == "http://production-server:8000/v1/chat/completions"


class TestConfigPersistenceAndExport:
    """Task 7.2: 設定の永続化とエクスポート機能のテスト"""

    @pytest.fixture
    def temp_config_dir(self):
        """テスト用設定ディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"
            config_dir.mkdir(exist_ok=True)
            yield config_dir

    def test_export_config_to_json(self, temp_config_dir):
        """Requirement 7.5: 設定のJSON形式エクスポートテスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # 設定をセット
        test_config = {
            "llm_config": {
                "api": {"url": "http://test:8000", "timeout": 45},
                "model": {"name": "test-model", "temperature": 0.5}
            }
        }
        config_manager.set_current_config(test_config)

        # JSON形式でエクスポート
        export_path = config_manager.export_config(format="json")

        assert export_path.exists()
        assert export_path.suffix == ".json"

        # エクスポートされた内容確認
        with open(export_path, 'r', encoding='utf-8') as f:
            exported_config = json.load(f)

        assert exported_config["llm_config"]["model"]["name"] == "test-model"

    def test_export_config_to_yaml(self, temp_config_dir):
        """設定のYAML形式エクスポートテスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        test_config = {
            "llm_config": {
                "api": {"url": "http://test:8000"},
                "model": {"name": "export-test-model"}
            }
        }
        config_manager.set_current_config(test_config)

        # YAML形式でエクスポート
        export_path = config_manager.export_config(format="yaml")

        assert export_path.exists()
        assert export_path.suffix == ".yaml"

        # エクスポートされた内容確認
        with open(export_path, 'r', encoding='utf-8') as f:
            exported_config = yaml.safe_load(f)

        assert exported_config["llm_config"]["model"]["name"] == "export-test-model"

    def test_import_config_from_json(self, temp_config_dir):
        """設定のJSON形式インポートテスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # JSONファイルを作成
        import_config = {
            "llm_config": {
                "api": {"url": "http://imported:8000"},
                "model": {"name": "imported-model", "temperature": 0.9}
            }
        }

        import_path = temp_config_dir / "import_test.json"
        with open(import_path, 'w', encoding='utf-8') as f:
            json.dump(import_config, f, ensure_ascii=False, indent=2)

        # インポート実行
        loaded_config = config_manager.import_config(import_path)

        assert loaded_config["llm_config"]["model"]["name"] == "imported-model"
        assert loaded_config["llm_config"]["model"]["temperature"] == 0.9

    def test_import_config_from_yaml(self, temp_config_dir):
        """設定のYAML形式インポートテスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        import_config = {
            "llm_config": {
                "api": {"url": "http://yaml-import:8000"},
                "model": {"name": "yaml-imported-model"}
            }
        }

        import_path = temp_config_dir / "import_test.yaml"
        with open(import_path, 'w', encoding='utf-8') as f:
            yaml.dump(import_config, f, default_flow_style=False, allow_unicode=True)

        # インポート実行
        loaded_config = config_manager.import_config(import_path)

        assert loaded_config["llm_config"]["model"]["name"] == "yaml-imported-model"

    def test_reset_to_default_config(self, temp_config_dir):
        """Requirement 7.5: デフォルト設定へのリセット機能テスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # カスタム設定をセット
        custom_config = {
            "llm_config": {
                "model": {"name": "custom-model", "temperature": 0.9}
            }
        }
        config_manager.set_current_config(custom_config)

        # デフォルトにリセット
        reset_config = config_manager.reset_to_default()

        # デフォルト値の確認
        assert reset_config["llm_config"]["model"]["name"] == "qwen3-14b-awq"
        assert reset_config["llm_config"]["model"]["temperature"] == 0.2

        # 現在の設定もリセットされることを確認
        assert config_manager.current_config == reset_config

    def test_list_available_profiles(self, temp_config_dir):
        """利用可能なプロファイル一覧取得テスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # 複数のプロファイルを作成
        dev_config = {"llm_config": {"model": {"name": "dev-model"}}}
        prod_config = {"llm_config": {"model": {"name": "prod-model"}}}
        test_config = {"llm_config": {"model": {"name": "test-model"}}}

        config_manager.save_profile("development", dev_config)
        config_manager.save_profile("production", prod_config)
        config_manager.save_profile("testing", test_config)

        # プロファイル一覧取得
        profiles = config_manager.list_profiles()

        assert "development" in profiles
        assert "production" in profiles
        assert "testing" in profiles
        assert len(profiles) == 3

    def test_delete_profile(self, temp_config_dir):
        """プロファイル削除機能のテスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # プロファイル作成
        test_config = {"llm_config": {"model": {"name": "delete-me"}}}
        config_manager.save_profile("to_delete", test_config)

        # プロファイルが存在することを確認
        profiles = config_manager.list_profiles()
        assert "to_delete" in profiles

        # プロファイル削除
        success = config_manager.delete_profile("to_delete")
        assert success is True

        # プロファイルが削除されたことを確認
        profiles = config_manager.list_profiles()
        assert "to_delete" not in profiles

        # 存在しないプロファイルの削除
        success = config_manager.delete_profile("nonexistent")
        assert success is False

    def test_export_with_metadata(self, temp_config_dir):
        """メタデータ付きエクスポート機能のテスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        test_config = {
            "llm_config": {
                "model": {"name": "metadata-test"}
            }
        }
        config_manager.set_current_config(test_config)

        # メタデータ付きエクスポート
        metadata = {
            "exported_by": "test_user",
            "export_purpose": "testing",
            "notes": "Test export with metadata"
        }

        export_path = config_manager.export_config(
            format="yaml",
            include_metadata=True,
            metadata=metadata
        )

        # メタデータが含まれていることを確認
        with open(export_path, 'r', encoding='utf-8') as f:
            exported_data = yaml.safe_load(f)

        assert "export_metadata" in exported_data
        assert exported_data["export_metadata"]["exported_by"] == "test_user"
        assert exported_data["export_metadata"]["export_purpose"] == "testing"

    def test_config_diff_comparison(self, temp_config_dir):
        """設定差分比較機能のテスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # 2つの異なる設定
        config1 = {
            "llm_config": {
                "model": {"name": "model1", "temperature": 0.2},
                "api": {"timeout": 30}
            }
        }

        config2 = {
            "llm_config": {
                "model": {"name": "model2", "temperature": 0.5},
                "api": {"timeout": 30}  # 同じ値
            }
        }

        # 差分比較実行
        diff = config_manager.compare_configs(config1, config2)

        # 差分結果の確認
        assert "llm_config.model.name" in diff["changed"]
        assert diff["changed"]["llm_config.model.name"]["old"] == "model1"
        assert diff["changed"]["llm_config.model.name"]["new"] == "model2"

        assert "llm_config.model.temperature" in diff["changed"]
        assert diff["changed"]["llm_config.model.temperature"]["old"] == 0.2
        assert diff["changed"]["llm_config.model.temperature"]["new"] == 0.5

        # 同じ値は差分に含まれない
        assert "llm_config.api.timeout" not in diff["changed"]

    def test_config_backup_and_restore(self, temp_config_dir):
        """設定のバックアップと復元機能のテスト"""
        config_manager = LLMConfigManager(config_dir=temp_config_dir)

        # 初期設定
        original_config = {
            "llm_config": {
                "model": {"name": "original-model", "temperature": 0.3}
            }
        }
        config_manager.set_current_config(original_config)
        config_manager.save_current_config()

        # バックアップ作成
        backup_path = config_manager.create_backup()
        assert backup_path.exists()

        # 設定を変更
        modified_config = {
            "llm_config": {
                "model": {"name": "modified-model", "temperature": 0.8}
            }
        }
        config_manager.set_current_config(modified_config)
        config_manager.save_current_config()

        # バックアップから復元
        restored_config = config_manager.restore_from_backup(backup_path)

        # 元の設定に復元されたことを確認
        assert restored_config["llm_config"]["model"]["name"] == "original-model"
        assert restored_config["llm_config"]["model"]["temperature"] == 0.3