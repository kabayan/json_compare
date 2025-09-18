"""拡張CLI機能のテスト"""

import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

# これから実装するモジュールをインポート
from src.enhanced_cli import (
    EnhancedCLI,
    CLIConfig,
    parse_enhanced_args,
    create_similarity_calculator_from_args
)


class TestCLIConfig:
    """CLI設定クラスのテスト"""

    def test_cli_config_creation_default(self):
        """デフォルトCLI設定作成のテスト"""
        config = CLIConfig()

        assert config.calculation_method == "auto"
        assert config.llm_enabled == False
        assert config.use_gpu == False
        assert config.prompt_file is None
        assert config.model_name is None
        assert config.temperature == 0.2
        assert config.max_tokens == 64

    def test_cli_config_creation_with_llm(self):
        """LLM有効化CLI設定作成のテスト"""
        config = CLIConfig(
            calculation_method="llm",
            llm_enabled=True,
            prompt_file="custom_prompt.yaml",
            model_name="qwen3-14b-awq",
            temperature=0.3,
            max_tokens=128
        )

        assert config.calculation_method == "llm"
        assert config.llm_enabled == True
        assert config.prompt_file == "custom_prompt.yaml"
        assert config.model_name == "qwen3-14b-awq"
        assert config.temperature == 0.3
        assert config.max_tokens == 128

    def test_cli_config_validation(self):
        """CLI設定のバリデーションテスト"""
        # 無効な計算方法
        with pytest.raises(ValueError, match="無効な計算方法"):
            CLIConfig(calculation_method="invalid_method")

        # 無効な温度
        with pytest.raises(ValueError, match="temperatureは0.0から1.0"):
            CLIConfig(temperature=1.5)

        # 無効なトークン数
        with pytest.raises(ValueError, match="max_tokensは1以上"):
            CLIConfig(max_tokens=0)


class TestEnhancedCLI:
    """拡張CLIクラスのテスト"""

    @pytest.fixture
    def enhanced_cli(self):
        """EnhancedCLIインスタンスを返すフィクスチャ"""
        return EnhancedCLI()

    @pytest.fixture
    def temp_jsonl_file(self):
        """一時JSONLファイルを作成するフィクスチャ"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # テストデータ
            test_data = [
                {
                    "id": 1,
                    "inference1": '{"task": "データ処理"}',
                    "inference2": '{"task": "データの処理"}'
                },
                {
                    "id": 2,
                    "inference1": '{"name": "田中"}',
                    "inference2": '{"name": "田中太郎"}'
                }
            ]
            for data in test_data:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')

            temp_path = f.name

        yield temp_path

        # クリーンアップ
        os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_process_single_file_with_embedding(self, enhanced_cli, temp_jsonl_file):
        """埋め込みモードでの単一ファイル処理テスト"""
        config = CLIConfig(calculation_method="embedding")

        with patch('src.enhanced_cli.create_similarity_calculator_from_args') as mock_create_calc:
            mock_calculator = AsyncMock()
            mock_create_calc.return_value = mock_calculator

            # モック結果の設定
            from src.similarity_strategy import StrategyResult
            mock_results = [
                StrategyResult(score=0.8, method="embedding", processing_time=0.3),
                StrategyResult(score=0.6, method="embedding", processing_time=0.2)
            ]
            mock_calculator.calculate_batch_similarity.return_value = mock_results

            result = await enhanced_cli.process_single_file(temp_jsonl_file, config, "score")

            # 結果の検証
            assert result["summary"]["total_comparisons"] == 2
            assert result["summary"]["average_score"] == 0.7
            assert "metadata" in result

    @pytest.mark.asyncio
    async def test_process_single_file_with_llm(self, enhanced_cli, temp_jsonl_file):
        """LLMモードでの単一ファイル処理テスト"""
        config = CLIConfig(
            calculation_method="llm",
            llm_enabled=True,
            model_name="qwen3-14b-awq"
        )

        with patch('src.enhanced_cli.create_similarity_calculator_from_args') as mock_create_calc:
            mock_calculator = AsyncMock()
            mock_create_calc.return_value = mock_calculator

            # LLMモック結果の設定
            from src.similarity_strategy import StrategyResult
            mock_results = [
                StrategyResult(
                    score=0.9, method="llm", processing_time=1.5,
                    metadata={"model_used": "qwen3-14b-awq", "confidence": 0.95}
                ),
                StrategyResult(
                    score=0.7, method="llm", processing_time=1.2,
                    metadata={"model_used": "qwen3-14b-awq", "confidence": 0.85}
                )
            ]
            mock_calculator.calculate_batch_similarity.return_value = mock_results

            result = await enhanced_cli.process_single_file(temp_jsonl_file, config, "score")

            # LLM固有メタデータの確認
            assert result["summary"]["average_score"] == 0.8
            assert result["summary"]["method_breakdown"]["llm"] == 2

    @pytest.mark.asyncio
    async def test_process_dual_files_with_llm(self, enhanced_cli):
        """LLMモードでのデュアルファイル処理テスト"""
        config = CLIConfig(calculation_method="llm", llm_enabled=True)

        with patch('src.enhanced_cli.DualFileExtractor') as mock_extractor_class:
            mock_extractor = MagicMock()
            mock_extractor_class.return_value = mock_extractor

            # デュアルファイル結果のモック
            mock_extractor.compare_dual_files_enhanced.return_value = {
                "summary": {
                    "total_comparisons": 5,
                    "average_score": 0.85,
                    "method_breakdown": {"llm": 5}
                },
                "detailed_results": []
            }

            result = await enhanced_cli.process_dual_files(
                "file1.jsonl", "file2.jsonl", "inference", config, "score"
            )

            # デュアルファイル処理の確認
            mock_extractor.compare_dual_files_enhanced.assert_called_once_with(
                "file1.jsonl", "file2.jsonl", "inference", config, "score"
            )
            assert result["summary"]["total_comparisons"] == 5

    def test_create_output_with_legacy_compatibility(self, enhanced_cli):
        """レガシー互換性出力作成のテスト"""
        from src.enhanced_result_format import EnhancedResult

        enhanced_result = EnhancedResult(
            score=0.85,
            method="embedding",
            processing_time=0.5,
            input_data={"file1": "test1.json", "file2": "test2.json"},
            metadata={"field_match_ratio": 0.8, "value_similarity": 0.9}
        )

        # レガシー互換モード
        legacy_output = enhanced_cli.create_output(enhanced_result, legacy_mode=True)

        # レガシーフィールドの確認
        assert legacy_output["file"] == "test1.json vs test2.json"
        assert legacy_output["score"] == 0.85
        assert legacy_output["meaning"] == "非常に類似"
        assert legacy_output["json"]["field_match_ratio"] == 0.8
        assert "metadata" not in legacy_output  # レガシーモードではメタデータなし

        # 拡張モード
        enhanced_output = enhanced_cli.create_output(enhanced_result, legacy_mode=False)
        assert "metadata" in enhanced_output
        assert enhanced_output["metadata"]["calculation_method"] == "embedding"


class TestCLIArgParsing:
    """CLI引数解析のテスト"""

    def test_parse_enhanced_args_basic(self):
        """基本的な引数解析のテスト"""
        args = [
            "input.jsonl",
            "--type", "score",
            "--output", "result.json"
        ]

        parsed_args, config = parse_enhanced_args(args)

        assert parsed_args.input_file == "input.jsonl"
        assert parsed_args.type == "score"
        assert parsed_args.output == "result.json"
        assert config.calculation_method == "auto"
        assert config.llm_enabled == False

    def test_parse_enhanced_args_with_llm_flags(self):
        """LLMフラグ付き引数解析のテスト"""
        args = [
            "input.jsonl",
            "--llm",
            "--method", "llm",
            "--prompt-file", "custom.yaml",
            "--model", "qwen3-14b-awq",
            "--temperature", "0.3",
            "--max-tokens", "128"
        ]

        parsed_args, config = parse_enhanced_args(args)

        assert config.llm_enabled == True
        assert config.calculation_method == "llm"
        assert config.prompt_file == "custom.yaml"
        assert config.model_name == "qwen3-14b-awq"
        assert config.temperature == 0.3
        assert config.max_tokens == 128

    def test_parse_enhanced_args_dual_command_with_llm(self):
        """LLM付きデュアルコマンド引数解析のテスト"""
        args = [
            "dual",
            "file1.jsonl",
            "file2.jsonl",
            "--column", "inference",
            "--llm",
            "--method", "auto"
        ]

        parsed_args, config = parse_enhanced_args(args)

        assert parsed_args.command == "dual"
        assert parsed_args.file1 == "file1.jsonl"
        assert parsed_args.file2 == "file2.jsonl"
        assert parsed_args.column == "inference"
        assert config.llm_enabled == True
        assert config.calculation_method == "auto"
        assert config.fallback_enabled == True  # デフォルトでTrue

    def test_parse_enhanced_args_validation_errors(self):
        """引数解析バリデーションエラーのテスト"""
        # 無効な計算方法（argparseレベルでエラー）
        args = ["input.jsonl", "--method", "invalid"]
        with pytest.raises(SystemExit):  # argparse error
            parse_enhanced_args(args)

        # 無効な温度（CLIConfigレベルでエラー）
        args = ["input.jsonl", "--temperature", "1.5"]
        with pytest.raises(ValueError, match="temperatureは0.0から1.0"):
            parse_enhanced_args(args)


class TestSimilarityCalculatorFactory:
    """類似度計算機ファクトリーのテスト"""

    @pytest.mark.asyncio
    async def test_create_calculator_embedding_mode(self):
        """埋め込みモード計算機作成のテスト"""
        config = CLIConfig(calculation_method="embedding", use_gpu=True)

        with patch('src.enhanced_cli.create_similarity_calculator') as mock_create:
            mock_calculator = AsyncMock()
            mock_create.return_value = mock_calculator

            calculator = await create_similarity_calculator_from_args(config)

            mock_create.assert_called_once_with(
                use_gpu=True,
                llm_config=None
            )

    @pytest.mark.asyncio
    async def test_create_calculator_llm_mode(self):
        """LLMモード計算機作成のテスト"""
        config = CLIConfig(
            calculation_method="llm",
            llm_enabled=True,
            model_name="qwen3-14b-awq",
            temperature=0.3,
            max_tokens=128
        )

        with patch('src.enhanced_cli.create_similarity_calculator') as mock_create:
            mock_calculator = AsyncMock()
            mock_create.return_value = mock_calculator

            calculator = await create_similarity_calculator_from_args(config)

            # LLM設定が正しく渡されることを確認
            call_args = mock_create.call_args
            assert call_args.kwargs["use_gpu"] == False
            assert call_args.kwargs["llm_config"]["model"] == "qwen3-14b-awq"
            assert call_args.kwargs["llm_config"]["temperature"] == 0.3
            assert call_args.kwargs["llm_config"]["max_tokens"] == 128


class TestCLIIntegration:
    """CLI統合テスト"""

    @pytest.mark.asyncio
    async def test_end_to_end_llm_processing(self):
        """エンドツーエンドLLM処理のテスト"""
        # 一時ファイル作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            test_data = {
                "id": 1,
                "inference1": '{"task": "データ処理"}',
                "inference2": '{"task": "データの処理"}'
            }
            f.write(json.dumps(test_data, ensure_ascii=False))
            temp_path = f.name

        try:
            args = [
                temp_path,
                "--llm",
                "--method", "llm",
                "--type", "score"
            ]

            with patch('src.enhanced_cli.create_similarity_calculator_from_args') as mock_create_calc:
                mock_calculator = AsyncMock()
                mock_create_calc.return_value = mock_calculator

                # LLM結果のモック
                from src.similarity_strategy import StrategyResult
                mock_result = StrategyResult(
                    score=0.9,
                    method="llm",
                    processing_time=1.5,
                    metadata={
                        "model_used": "qwen3-14b-awq",
                        "confidence": 0.95,
                        "category": "非常に類似"
                    }
                )
                mock_calculator.calculate_batch_similarity.return_value = [mock_result]

                # CLI実行のシミュレーション
                parsed_args, config = parse_enhanced_args(args)
                enhanced_cli = EnhancedCLI()
                result = await enhanced_cli.process_single_file(temp_path, config, "score")

                # 結果検証
                assert result["summary"]["total_comparisons"] == 1
                assert result["summary"]["method_breakdown"]["llm"] == 1

        finally:
            os.unlink(temp_path)

    def test_help_message_includes_llm_options(self):
        """ヘルプメッセージにLLMオプションが含まれることのテスト"""
        args = ["--help"]

        with pytest.raises(SystemExit):
            with patch('sys.stdout') as mock_stdout:
                parse_enhanced_args(args)

        # ヘルプメッセージの確認（実際の実装では詳細をチェック）
        # この時点では基本的な構造のみテスト


class TestCLIHelpAndErrorMessages:
    """CLIヘルプとエラーメッセージのテスト"""

    def test_detailed_llm_help_message(self):
        """詳細なLLMヘルプメッセージのテスト"""
        from src.enhanced_cli import get_detailed_help

        help_text = get_detailed_help()

        # LLM関連オプションが含まれることを確認
        assert "--llm" in help_text
        assert "--model" in help_text
        assert "--temperature" in help_text
        assert "--max-tokens" in help_text
        assert "--prompt-file" in help_text

        # 使用例が含まれることを確認
        assert "使用例:" in help_text
        assert "LLMモード:" in help_text
        assert "デュアルファイル比較:" in help_text

    def test_llm_usage_examples_help(self):
        """LLM使用例ヘルプのテスト"""
        from src.enhanced_cli import get_llm_usage_examples

        examples = get_llm_usage_examples()

        # 基本的な使用例が含まれることを確認
        assert "json_compare data.jsonl --llm" in examples
        assert "dual file1.jsonl file2.jsonl --column inference --llm" in examples
        assert "--model qwen3-14b-awq" in examples
        assert "--temperature 0.3" in examples

    def test_llm_error_display_functionality(self):
        """LLM関連エラー表示機能のテスト"""
        from src.enhanced_cli import format_llm_error

        # API接続エラー
        error_msg = format_llm_error("connection_error", "接続に失敗しました")
        assert "LLMサーバーへの接続に失敗" in error_msg
        assert "フォールバック" in error_msg

        # モデル不正エラー
        error_msg = format_llm_error("invalid_model", "モデルが見つかりません")
        assert "指定されたモデル" in error_msg
        assert "利用可能なモデル" in error_msg

        # レート制限エラー
        error_msg = format_llm_error("rate_limit", "レート制限に達しました")
        assert "レート制限" in error_msg
        assert "しばらく待って" in error_msg

    def test_fallback_suggestion_messages(self):
        """フォールバック提案メッセージのテスト"""
        from src.enhanced_cli import get_fallback_suggestions

        # LLM失敗時の提案
        suggestions = get_fallback_suggestions("llm_failed")
        assert "埋め込みモード" in suggestions
        assert "--method embedding" in suggestions

        # 接続失敗時の提案
        suggestions = get_fallback_suggestions("connection_failed")
        assert "LLMサーバーの状態" in suggestions
        assert "ローカル計算" in suggestions

    def test_error_with_detailed_explanation(self):
        """詳細説明付きエラー表示のテスト"""
        from src.enhanced_cli import EnhancedCLIErrorHandler

        handler = EnhancedCLIErrorHandler()

        # LLM API エラー
        error_info = handler.format_error(
            error_type="llm_api_error",
            message="API呼び出しに失敗",
            context={"model": "qwen3-14b-awq", "endpoint": "http://192.168.1.18:8000"}
        )

        assert error_info["category"] == "LLM API エラー"
        assert "qwen3-14b-awq" in error_info["details"]
        assert "http://192.168.1.18:8000" in error_info["details"]
        assert len(error_info["suggestions"]) > 0

    def test_configuration_validation_errors(self):
        """設定検証エラーのテスト"""
        from src.enhanced_cli import validate_llm_configuration

        # 無効な温度設定
        with pytest.raises(ValueError, match="temperatureは0.0から1.0の間"):
            validate_llm_configuration({
                "temperature": 1.5,
                "max_tokens": 128,
                "model": "qwen3-14b-awq"
            })

        # 無効なトークン数
        with pytest.raises(ValueError, match="max_tokensは1以上"):
            validate_llm_configuration({
                "temperature": 0.5,
                "max_tokens": 0,
                "model": "qwen3-14b-awq"
            })

    def test_progressive_error_guidance(self):
        """段階的エラーガイダンスのテスト"""
        from src.enhanced_cli import ProgressiveErrorGuide

        guide = ProgressiveErrorGuide()

        # 初回エラー - 基本的な提案
        guidance = guide.get_guidance("llm_connection_error", attempt=1)
        assert "基本的な接続確認" in guidance

        # 複数回エラー - より詳細な提案
        guidance = guide.get_guidance("llm_connection_error", attempt=3)
        assert "詳細な診断" in guidance
        assert "代替エンドポイント" in guidance

    def test_best_practices_documentation(self):
        """ベストプラクティスドキュメント表示のテスト"""
        from src.enhanced_cli import get_best_practices

        practices = get_best_practices()

        # パフォーマンス最適化
        assert "パフォーマンス最適化" in practices
        assert "バッチサイズ" in practices

        # プロンプト設計
        assert "プロンプト設計" in practices
        assert "YAML形式" in practices

        # エラー対処
        assert "トラブルシューティング" in practices