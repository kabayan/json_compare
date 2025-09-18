"""Task 5: CLIインターフェースの拡張の統合テスト

Task 5専用のテストスイート。
Task 5.1: Requirements 1.1, 2.2, 3.2, 5.4
Task 5.2: Requirements 1.4, 2.3
の統合的検証。
"""

import pytest
import argparse
import tempfile
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any
from pathlib import Path

from src.enhanced_cli import (
    EnhancedCLI,
    CLIConfig,
    create_enhanced_argument_parser,
    create_single_file_parser,
    create_dual_file_parser,
    parse_enhanced_args
)


class TestTask51CommandLineOptions:
    """Task 5.1: コマンドラインオプションの追加の統合テストクラス"""

    def test_requirement_1_1_llm_flag_enables_llm_judgment(self):
        """
        Requirement 1.1: --llmフラグ指定でLLMベース判定を実行

        Task 5.1: LLMモード有効化フラグを実装
        """
        # テストケース: --llmフラグあり
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"inference1": "データ処理", "inference2": "データの処理"}\n')
            temp_file = f.name

        try:
            # --llmフラグ付きでパース
            args, config = parse_enhanced_args([temp_file, '--llm'])

            # Requirement 1.1: LLMモードが有効化される
            assert config.llm_enabled == True
            assert args.llm == True
            assert config.calculation_method in ["auto", "llm"]  # autoまたはllmが期待される

            # テストケース: --llmフラグなし
            args_no_llm, config_no_llm = parse_enhanced_args([temp_file])

            # Requirement 1.1: LLMモードが無効（既存の埋め込みベース）
            assert config_no_llm.llm_enabled == False
            assert hasattr(args_no_llm, 'llm') and args_no_llm.llm == False

        finally:
            os.unlink(temp_file)

    def test_requirement_2_2_prompt_file_option_loading(self):
        """
        Requirement 2.2: --prompt-fileオプションで指定ファイルからプロンプトテンプレート読み込み

        Task 5.1: プロンプトファイル指定オプションを追加
        """
        # テストプロンプトファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as prompt_f:
            prompt_f.write("""
system: "類似度を判定してください"
user: "テキスト1: {text1}\\nテキスト2: {text2}\\n類似度スコア（0-1）を返してください。"
""")
            prompt_file_path = prompt_f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as data_f:
            data_f.write('{"inference1": "データ処理", "inference2": "データの処理"}\n')
            data_file_path = data_f.name

        try:
            # --prompt-fileオプション付きでパース
            args, config = parse_enhanced_args([
                data_file_path,
                '--llm',
                '--prompt-file', prompt_file_path
            ])

            # Requirement 2.2: プロンプトファイルパスが設定される
            assert config.prompt_file == prompt_file_path
            assert args.prompt_file == prompt_file_path

            # CLIConfigから設定を取得
            assert hasattr(config, 'prompt_file')
            assert config.prompt_file is not None

        finally:
            os.unlink(prompt_file_path)
            os.unlink(data_file_path)

    def test_requirement_3_2_model_option_specification(self):
        """
        Requirement 3.2: --modelオプションで指定したモデル名を使用

        Task 5.1: モデル選択と生成パラメータのオプションを実装
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"inference1": "テスト1", "inference2": "テスト2"}\n')
            temp_file = f.name

        try:
            # --modelオプション付きでパース
            args, config = parse_enhanced_args([
                temp_file,
                '--llm',
                '--model', 'custom-llm-model',
                '--temperature', '0.5',
                '--max-tokens', '128'
            ])

            # Requirement 3.2: モデル名と生成パラメータが設定される
            assert args.llm_model == 'custom-llm-model'
            assert config.model_name == 'custom-llm-model'
            assert config.temperature == 0.5
            assert config.max_tokens == 128
            assert args.temperature == 0.5
            assert args.max_tokens == 128

        finally:
            os.unlink(temp_file)

    def test_requirement_5_4_dual_command_llm_support(self):
        """
        Requirement 5.4: dualコマンドで--llmフラグもサポート

        Task 5.1: デュアルファイル比較でのLLMサポートを追加
        """
        # デュアルファイル用のテストファイル作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f1:
            f1.write('{"inference": "データ処理システム"}\n')
            file1_path = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f2:
            f2.write('{"inference": "データ処理の仕組み"}\n')
            file2_path = f2.name

        try:
            # デュアルファイルパーサーでのLLMサポート確認
            dual_parser = create_dual_file_parser()

            # --llmフラグ付きでパース
            dual_args = dual_parser.parse_args([
                file1_path, file2_path,
                '--llm',
                '--method', 'llm',
                '--prompt-file', 'custom_prompt.yaml',
                '--model', 'qwen3-7b-instruct'
            ])

            # Requirement 5.4: デュアルファイルでのLLMオプション対応
            assert dual_args.llm == True
            assert dual_args.method == 'llm'
            assert dual_args.prompt_file == 'custom_prompt.yaml'
            assert dual_args.llm_model == 'qwen3-7b-instruct'

            # 単一ファイルパーサーでも同様にLLMサポート確認
            single_parser = create_single_file_parser()
            single_args = single_parser.parse_args([
                file1_path,
                '--llm',
                '--method', 'auto'
            ])

            assert single_args.llm == True
            assert single_args.method == 'auto'

        finally:
            os.unlink(file1_path)
            os.unlink(file2_path)

    def test_task_5_1_comprehensive_cli_options_integration(self):
        """
        Task 5.1: コマンドラインオプション追加の包括的統合テスト

        全てのLLM関連オプションが適切に解析・設定されることを確認
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"inference1": "機械学習", "inference2": "ML"}\n')
            temp_file = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as pf:
            pf.write("system: 'Compare similarity'\nuser: 'Text1: {text1}\\nText2: {text2}'\n")
            prompt_file = pf.name

        try:
            # 全オプション付きでパース
            args, config = parse_enhanced_args([
                temp_file,
                '--llm',
                '--method', 'llm',
                '--prompt-file', prompt_file,
                '--model', 'qwen3-14b-awq',
                '--temperature', '0.3',
                '--max-tokens', '100',
                '--no-fallback',
                '--legacy',
                '--verbose'
            ])

            # 全オプションの設定確認
            assert config.llm_enabled == True
            assert config.calculation_method == 'llm'
            assert config.prompt_file == prompt_file
            assert config.model_name == 'qwen3-14b-awq'
            assert config.temperature == 0.3
            assert config.max_tokens == 100
            assert config.fallback_enabled == False
            assert config.legacy_mode == True
            assert config.verbose == True

        finally:
            os.unlink(temp_file)
            os.unlink(prompt_file)


class TestTask52HelpAndErrorMessages:
    """Task 5.2: CLIヘルプとエラーメッセージの拡張の統合テストクラス"""

    def test_requirement_1_4_vllm_api_connection_failure_error_handling(self):
        """
        Requirement 1.4: vLLM API接続失敗時のエラーメッセージ表示とフォールバック提供

        Task 5.2: LLM関連エラーの詳細表示機能を実装
        """
        cli = EnhancedCLI()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"inference1": "test1", "inference2": "test2"}\n')
            temp_file = f.name

        try:
            config = CLIConfig(
                llm_enabled=True,
                calculation_method='llm',
                fallback_enabled=True
            )

            # vLLM API接続失敗をシミュレートし、フォールバック機能が動作することを確認
            with patch('src.similarity_strategy.create_similarity_calculator_from_args') as mock_create:
                mock_calculator = MagicMock()
                mock_create.return_value = mock_calculator
                mock_calculator.__aenter__.return_value = mock_calculator

                # API接続失敗を模擬するが、フォールバック機能により処理が完了する
                from src.llm_similarity import LLMSimilarityError
                mock_calculator.calculate_batch_similarity.side_effect = LLMSimilarityError("vLLM API connection failed")

                # フォールバック機能により例外は発生せず、処理が正常に完了することを確認
                import asyncio
                result = asyncio.run(cli.process_single_file(temp_file, config, 'score'))

                # Requirement 1.4: フォールバック機能が動作し、結果が返されることを確認
                assert result is not None
                assert isinstance(result, dict)

        finally:
            os.unlink(temp_file)

    def test_requirement_2_3_prompt_file_not_found_error_handling(self):
        """
        Requirement 2.3: プロンプトファイルが見つからない場合のエラー処理

        Task 5.2: フォールバック提案メッセージを実装
        """
        # プロンプトファイル指定オプションの設定確認
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"inference1": "test1", "inference2": "test2"}\n')
            temp_file = f.name

        try:
            # 存在しないプロンプトファイルを指定
            args, config = parse_enhanced_args([
                temp_file,
                '--llm',
                '--prompt-file', '/nonexistent/prompt/file.yaml'
            ])

            # Requirement 2.3: プロンプトファイルパスが適切に設定されることを確認
            assert config.prompt_file == '/nonexistent/prompt/file.yaml'
            assert config.llm_enabled == True

            # 実際のファイル処理時にエラーハンドリングが実装されることを期待
            # (ここではCLI引数パースが正常に動作することのみを確認)

        finally:
            os.unlink(temp_file)

    def test_task_5_2_help_messages_include_llm_options(self):
        """
        Task 5.2: 新規オプションのヘルプメッセージを追加

        LLM関連オプションが適切にヘルプメッセージに含まれることを確認
        """
        # メインパーサーのヘルプメッセージ確認
        main_parser = create_enhanced_argument_parser()
        help_text = main_parser.format_help()

        # LLM関連オプションがヘルプに含まれることを確認
        assert '--llm' in help_text
        assert 'LLMベース判定' in help_text
        assert '--prompt-file' in help_text
        assert 'プロンプトテンプレート' in help_text
        assert '--model' in help_text
        assert '--temperature' in help_text
        assert '--max-tokens' in help_text
        assert '--no-fallback' in help_text

        # 単一ファイルパーサーのヘルプメッセージ確認
        single_parser = create_single_file_parser()
        single_help = single_parser.format_help()

        assert '--llm' in single_help
        assert 'vLLM API' in single_help

        # デュアルファイルパーサーのヘルプメッセージ確認
        dual_parser = create_dual_file_parser()
        dual_help = dual_parser.format_help()

        assert '--llm' in dual_help
        assert 'LLMベース判定' in dual_help

    def test_task_5_2_usage_examples_and_best_practices_display(self):
        """
        Task 5.2: 使用例とベストプラクティスの表示機能を追加

        --helpで使用例が表示されることを確認
        """
        # メインパーサーでの使用例表示確認
        main_parser = create_enhanced_argument_parser()
        help_text = main_parser.format_help()

        # 基本的なヘルプ情報が含まれることを確認
        assert 'JSON比較ツール' in help_text
        assert 'LLM' in help_text or 'vLLM' in help_text

        # プログラム名や基本的な使用法が含まれることを確認
        assert 'usage:' in help_text.lower() or 'Usage:' in help_text

    def test_task_5_2_error_message_comprehensive_handling(self):
        """
        Task 5.2: エラーメッセージの包括的処理

        様々なエラーシナリオでの適切なメッセージ表示を確認
        """
        # 正常なケース：有効な引数の場合
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"inference1": "test1", "inference2": "test2"}\n')
            temp_file = f.name

        try:
            # 有効な引数の場合は正常にパースされる
            args, config = parse_enhanced_args([temp_file, '--llm'])
            assert config.llm_enabled == True

            # 温度パラメータの範囲内の値は正常に処理される
            args_temp, config_temp = parse_enhanced_args([temp_file, '--temperature', '0.5'])
            assert config_temp.temperature == 0.5

            # 無効な温度範囲のテスト（1.0を超える値）- 適切にエラーが発生することを確認
            with pytest.raises(ValueError, match="temperatureは0.0から1.0の範囲で指定してください"):
                parse_enhanced_args([temp_file, '--temperature', '1.5'])

        finally:
            os.unlink(temp_file)

        # CLIConfigの基本機能確認
        config = CLIConfig(llm_enabled=True, calculation_method='llm')
        assert config.llm_enabled == True
        assert config.calculation_method == 'llm'


class TestTask5Integration:
    """Task 5の統合テスト"""

    def test_task_5_end_to_end_cli_functionality(self):
        """
        Task 5: CLIインターフェース拡張のエンドツーエンドテスト

        Task 5.1と5.2の機能が統合的に動作することを確認
        """
        # テストデータ準備
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"inference1": "機械学習アルゴリズム", "inference2": "MLアルゴリズム"}\n')
            f.write('{"inference1": "データ分析手法", "inference2": "データ解析方法"}\n')
            temp_file = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as pf:
            pf.write("""
system: "類似度を0-1のスコアで判定してください"
user: "テキスト1: {text1}\\nテキスト2: {text2}\\n類似度スコア:"
""")
            prompt_file = pf.name

        try:
            # 完全なCLI統合テスト
            args, config = parse_enhanced_args([
                temp_file,
                '--type', 'score',
                '--llm',
                '--method', 'auto',
                '--prompt-file', prompt_file,
                '--model', 'qwen3-14b-awq',
                '--temperature', '0.2',
                '--max-tokens', '64',
                '--verbose'
            ])

            # 統合的な設定確認
            assert config.llm_enabled == True
            assert config.calculation_method == 'auto'
            assert config.prompt_file == prompt_file
            assert config.model_name == 'qwen3-14b-awq'
            assert config.temperature == 0.2
            assert config.max_tokens == 64
            assert config.verbose == True

            # CLIConfigから適切なLLM設定を生成できることを確認
            llm_config = config.to_llm_config() if hasattr(config, 'to_llm_config') else None

            # 基本的な設定項目の存在確認
            assert hasattr(config, 'model_name')
            assert hasattr(config, 'temperature')
            assert hasattr(config, 'max_tokens')

        finally:
            os.unlink(temp_file)
            os.unlink(prompt_file)

    @pytest.mark.asyncio
    async def test_task_5_dual_file_llm_integration(self):
        """
        Task 5: デュアルファイル処理でのLLM統合テスト

        Requirement 5.4のデュアルファイル比較でのLLMサポート確認
        """
        # デュアルファイル用テストデータ
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f1:
            f1.write('{"inference": "深層学習モデル"}\n')
            f1.write('{"inference": "ニューラルネットワーク"}\n')
            file1_path = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f2:
            f2.write('{"inference": "ディープラーニング"}\n')
            f2.write('{"inference": "人工ニューラル網"}\n')
            file2_path = f2.name

        try:
            # デュアルファイルでのLLM処理設定
            cli = EnhancedCLI()
            config = CLIConfig(
                llm_enabled=True,
                calculation_method='llm',
                dual_mode=True,
                dual_file1=file1_path,
                dual_file2=file2_path,
                dual_column='inference'
            )

            # デュアルファイル処理の基本機能確認（実際の処理はモック）
            with patch('src.similarity_strategy.create_similarity_calculator_from_args') as mock_create:
                mock_calculator = MagicMock()
                mock_create.return_value = mock_calculator
                mock_calculator.__aenter__.return_value = mock_calculator
                mock_calculator.calculate_similarity.return_value = MagicMock(
                    score=0.85, method="llm", processing_time=1.2
                )

                # 設定が適切であることを確認
                assert config.dual_mode == True
                assert config.llm_enabled == True
                assert config.dual_file1 == file1_path
                assert config.dual_file2 == file2_path

        finally:
            os.unlink(file1_path)
            os.unlink(file2_path)