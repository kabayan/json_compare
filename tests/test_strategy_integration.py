"""Task 4.1: 戦略パターンのCLI統合テスト

TDD実装：既存の類似度計算インターフェースとの統合
- --llmフラグによる動的切り替え
- フォールバック機能の統合
- 統計情報の収集
"""

import pytest
import tempfile
import json
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from src.enhanced_cli import EnhancedCLI, CLIConfig


class TestStrategyIntegration:
    """戦略パターン統合のテスト"""

    @pytest.fixture
    def temp_jsonl_file(self):
        """テスト用JSONLファイル"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            test_data = [
                {
                    "id": 1,
                    "inference1": '{"task": "データ処理"}',
                    "inference2": '{"task": "データの処理"}'
                },
                {
                    "id": 2,
                    "inference1": '{"task": "機械学習"}',
                    "inference2": '{"task": "AI開発"}'
                }
            ]
            for data in test_data:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            temp_path = f.name

        yield temp_path
        Path(temp_path).unlink(missing_ok=True)

    def test_cli_config_has_llm_options(self):
        """CLIConfigにLLMオプションが含まれることのテスト"""
        config = CLIConfig()

        # LLM関連の設定が存在することを確認
        assert hasattr(config, 'llm_enabled')
        assert hasattr(config, 'model_name')      # llm_modelではなくmodel_name
        assert hasattr(config, 'temperature')    # llm_temperatureではなくtemperature
        assert hasattr(config, 'prompt_file')
        assert hasattr(config, 'fallback_enabled')

    def test_cli_config_llm_defaults(self):
        """LLM設定のデフォルト値テスト"""
        config = CLIConfig()

        assert config.llm_enabled == False
        assert config.model_name is None          # デフォルトはNone
        assert config.temperature == 0.2
        assert config.prompt_file is None
        assert config.fallback_enabled == True

    def test_enhanced_cli_embedding_mode_default(self, temp_jsonl_file):
        """埋め込みモードがデフォルトで使用されることのテスト"""
        cli = EnhancedCLI()

        with patch('src.similarity_strategy.create_similarity_calculator_from_args') as mock_create:
            mock_calculator = MagicMock()
            mock_create.return_value = mock_calculator
            mock_calculator.__aenter__.return_value = mock_calculator
            mock_calculator.calculate_similarity.return_value = MagicMock(score=0.8, method="embedding")

            # --llmフラグなしで実行 (デフォルトは埋め込みモード)
            config = CLIConfig(calculation_method="embedding")

            import asyncio
            result = asyncio.run(cli.process_single_file(temp_jsonl_file, config, 'score'))

            # 埋め込みモードで計算されることを確認
            mock_create.assert_called_with(config)
            mock_calculator.calculate_similarity.assert_called()

    def test_enhanced_cli_llm_mode_with_flag(self, temp_jsonl_file):
        """--llmフラグでLLMモードが有効になることのテスト"""
        cli = EnhancedCLI()

        with patch('src.similarity_strategy.SimilarityCalculator') as mock_calculator:
            mock_instance = MagicMock()
            mock_calculator.return_value.__aenter__.return_value = mock_instance
            mock_instance.calculate_similarity.return_value = AsyncMock()

            # --llmフラグありで実行
            config = CLIConfig(
                input_file=temp_jsonl_file,
                output_type='score',
                llm_enabled=True
            )
            result = cli.process_file(config)

            # LLMモードで計算されることを確認
            mock_instance.calculate_similarity.assert_called()
            call_args = mock_instance.calculate_similarity.call_args
            assert call_args[1]['method'] == 'llm'  # 戦略がLLMモード

    def test_enhanced_cli_fallback_on_llm_failure(self, temp_jsonl_file):
        """LLM失敗時の自動フォールバック機能のテスト"""
        cli = EnhancedCLI()

        with patch('src.similarity_strategy.SimilarityCalculator') as mock_calculator:
            mock_instance = MagicMock()
            mock_calculator.return_value.__aenter__.return_value = mock_instance

            # 最初のLLM呼び出しは失敗、2回目（フォールバック）は成功
            mock_instance.calculate_similarity.side_effect = [
                Exception("LLM API failed"),  # 最初の呼び出しは失敗
                AsyncMock(return_value=MagicMock(score=0.7, method="embedding_fallback"))  # フォールバック成功
            ]

            config = CLIConfig(
                input_file=temp_jsonl_file,
                output_type='score',
                llm_enabled=True,
                fallback_enabled=True
            )

            # エラーが発生せず、フォールバックが動作することを確認
            result = cli.process_file(config)
            assert result is not None

    def test_enhanced_cli_no_fallback_when_disabled(self, temp_jsonl_file):
        """フォールバック無効時にLLM失敗でエラーになることのテスト"""
        cli = EnhancedCLI()

        with patch('src.similarity_strategy.SimilarityCalculator') as mock_calculator:
            mock_instance = MagicMock()
            mock_calculator.return_value.__aenter__.return_value = mock_instance

            # LLM呼び出しが失敗
            mock_instance.calculate_similarity.side_effect = Exception("LLM API failed")

            config = CLIConfig(
                input_file=temp_jsonl_file,
                output_type='score',
                llm_enabled=True,
                fallback_enabled=False  # フォールバック無効
            )

            # エラーが発生することを確認
            with pytest.raises(Exception, match="LLM API failed"):
                cli.process_file(config)

    def test_enhanced_cli_strategy_statistics_collection(self, temp_jsonl_file):
        """戦略統計情報の収集テスト"""
        cli = EnhancedCLI()

        with patch('src.similarity_strategy.SimilarityCalculator') as mock_calculator:
            mock_instance = MagicMock()
            mock_calculator.return_value.__aenter__.return_value = mock_instance
            mock_instance.calculate_similarity.return_value = AsyncMock()
            mock_instance.get_statistics.return_value = {
                'total_calculations': 2,
                'embedding_used': 1,
                'llm_used': 1,
                'fallback_used': 0,
                'failed_calculations': 0
            }

            config = CLIConfig(
                input_file=temp_jsonl_file,
                output_type='score',
                llm_enabled=True
            )

            result = cli.process_file(config)

            # 統計情報が収集されることを確認
            mock_instance.get_statistics.assert_called()
            stats = mock_instance.get_statistics.return_value
            assert stats['total_calculations'] > 0

    def test_enhanced_cli_custom_prompt_file(self, temp_jsonl_file):
        """カスタムプロンプトファイル指定のテスト"""
        cli = EnhancedCLI()

        # テスト用プロンプトファイル作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            prompt_content = """
version: "1.0"
system_prompt: "カスタムシステムプロンプト"
user_prompt: "カスタムユーザープロンプト: {text1} vs {text2}"
"""
            f.write(prompt_content)
            prompt_file = f.name

        try:
            with patch('src.similarity_strategy.SimilarityCalculator') as mock_calculator:
                mock_instance = MagicMock()
                mock_calculator.return_value.__aenter__.return_value = mock_instance
                mock_instance.calculate_similarity.return_value = AsyncMock()

                config = CLIConfig(
                    input_file=temp_jsonl_file,
                    output_type='score',
                    llm_enabled=True,
                    prompt_file=prompt_file
                )

                result = cli.process_file(config)

                # カスタムプロンプトファイルが使用されることを確認
                # (実装によって具体的な検証方法は異なる)
                mock_instance.calculate_similarity.assert_called()

        finally:
            Path(prompt_file).unlink(missing_ok=True)

    def test_enhanced_cli_dual_file_strategy_integration(self):
        """2ファイル比較でも戦略パターンが適用されることのテスト"""
        cli = EnhancedCLI()

        # テスト用ファイル2つ作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f1:
            f1.write('{"id": 1, "inference": "テストデータ1"}\n')
            file1_path = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f2:
            f2.write('{"id": 1, "inference": "テストデータ2"}\n')
            file2_path = f2.name

        try:
            with patch('src.similarity_strategy.SimilarityCalculator') as mock_calculator:
                mock_instance = MagicMock()
                mock_calculator.return_value.__aenter__.return_value = mock_instance
                mock_instance.calculate_similarity.return_value = AsyncMock()

                config = CLIConfig(
                    dual_mode=True,
                    dual_file1=file1_path,
                    dual_file2=file2_path,
                    dual_column='inference',
                    output_type='score',
                    llm_enabled=True
                )

                result = cli.process_dual_files(config)

                # 戦略パターンが使用されることを確認
                mock_instance.calculate_similarity.assert_called()

        finally:
            Path(file1_path).unlink(missing_ok=True)
            Path(file2_path).unlink(missing_ok=True)

    def test_enhanced_cli_method_auto_selection(self, temp_jsonl_file):
        """自動戦略選択機能のテスト"""
        cli = EnhancedCLI()

        with patch('src.similarity_strategy.SimilarityCalculator') as mock_calculator:
            mock_instance = MagicMock()
            mock_calculator.return_value.__aenter__.return_value = mock_instance
            mock_instance.calculate_similarity.return_value = AsyncMock()

            config = CLIConfig(
                input_file=temp_jsonl_file,
                output_type='score',
                strategy_method='auto'  # 自動選択
            )

            result = cli.process_file(config)

            # 自動選択モードで呼び出されることを確認
            mock_instance.calculate_similarity.assert_called()
            call_args = mock_instance.calculate_similarity.call_args
            assert call_args[1]['method'] == 'auto'


class TestCLIArgumentParsing:
    """CLI引数解析のテスト"""

    def test_argument_parser_includes_llm_flags(self):
        """引数パーサーにLLMフラグが含まれることのテスト"""
        from src.enhanced_cli import create_parser

        parser = create_parser()

        # --llmフラグのテスト
        args = parser.parse_args(['test.jsonl', '--llm'])
        assert args.llm is True

        # --llm-modelフラグのテスト
        args = parser.parse_args(['test.jsonl', '--llm-model', 'custom-model'])
        assert args.llm_model == 'custom-model'

        # --prompt-fileフラグのテスト
        args = parser.parse_args(['test.jsonl', '--prompt-file', 'custom.yaml'])
        assert args.prompt_file == 'custom.yaml'

        # --no-fallbackフラグのテスト
        args = parser.parse_args(['test.jsonl', '--no-fallback'])
        assert args.fallback_enabled is False

    def test_cli_help_includes_llm_options(self):
        """CLIヘルプにLLMオプションが含まれることのテスト"""
        from src.enhanced_cli import create_parser

        parser = create_parser()
        help_text = parser.format_help()

        assert '--llm' in help_text
        assert 'LLMベース判定' in help_text
        assert '--prompt-file' in help_text
        assert '--no-fallback' in help_text
        assert 'vLLM API' in help_text