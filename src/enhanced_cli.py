"""拡張CLI機能

LLMベース類似度判定機能を統合した拡張CLIインターフェース。
既存のCLI互換性を保ちながら、新しいLLM機能とメタデータ管理を提供。
"""

import argparse
import asyncio
import json
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .similarity_strategy import create_similarity_calculator, SimilarityCalculator
from .enhanced_result_format import (
    EnhancedResult,
    ResultFormatter,
    CompatibilityLayer,
    create_enhanced_result_from_strategy
)
from .dual_file_extractor import DualFileExtractor

logger = logging.getLogger(__name__)


@dataclass
class CLIConfig:
    """CLI設定クラス"""
    calculation_method: str = "auto"  # "auto", "embedding", "llm"
    llm_enabled: bool = False
    use_gpu: bool = False
    prompt_file: Optional[str] = None
    model_name: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 64
    fallback_enabled: bool = True
    legacy_mode: bool = False
    verbose: bool = False
    # テスト互換性のための追加フィールド
    input_file: Optional[str] = None
    output_type: str = "score"
    dual_mode: bool = False
    dual_file1: Optional[str] = None
    dual_file2: Optional[str] = None
    dual_column: str = "inference"
    strategy_method: Optional[str] = None

    def __post_init__(self):
        """設定値のバリデーション"""
        valid_methods = ["auto", "embedding", "llm"]
        if self.calculation_method not in valid_methods:
            raise ValueError(f"無効な計算方法: {self.calculation_method}")

        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError("temperatureは0.0から1.0の範囲で指定してください")

        if self.max_tokens < 1:
            raise ValueError("max_tokensは1以上である必要があります")

    def to_llm_config(self) -> Optional[Dict[str, Any]]:
        """LLM設定辞書を生成"""
        if not self.llm_enabled:
            return None

        config = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        if self.model_name:
            config["model"] = self.model_name

        return config


class EnhancedCLI:
    """拡張CLIクラス"""

    def __init__(self):
        """初期化"""
        self.result_formatter = ResultFormatter()
        self.compatibility_layer = CompatibilityLayer()

    async def process_single_file(
        self,
        file_path: str,
        config: CLIConfig,
        output_type: str
    ) -> Dict[str, Any]:
        """
        単一ファイルの処理（拡張版）

        Args:
            file_path: 入力ファイルパス
            config: CLI設定
            output_type: 出力タイプ

        Returns:
            処理結果
        """
        # 類似度計算機の作成
        calculator = await create_similarity_calculator_from_args(config)

        # JSONLファイルの読み込みと解析
        json_pairs = []
        original_data = []

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)
                    inference1 = data.get('inference1', '{}')
                    inference2 = data.get('inference2', '{}')

                    json_pairs.append((inference1, inference2))
                    original_data.append(data)

                except json.JSONDecodeError as e:
                    logger.warning(f"{line_num}行目のJSONパースエラー: {e}")
                    continue

        if not json_pairs:
            return {
                "summary": {
                    "total_comparisons": 0,
                    "average_score": 0.0,
                    "total_processing_time": 0.0,
                    "method_breakdown": {}
                },
                "detailed_results": [],
                "metadata": self.result_formatter.metadata_collector.collect_system_metadata()
            }

        # バッチ類似度計算
        strategy_results = await calculator.calculate_batch_similarity(
            json_pairs,
            method=config.calculation_method,
            sequential=True,  # LLM使用時はレート制限対応
            fallback_enabled=config.fallback_enabled
        )

        # 拡張結果の作成
        enhanced_results = []
        for i, (strategy_result, original_row) in enumerate(zip(strategy_results, original_data)):
            enhanced_result = create_enhanced_result_from_strategy(
                strategy_result,
                input_data={
                    "file": file_path,
                    "line_number": i + 1,
                    "original_row": original_row
                }
            )
            enhanced_results.append(enhanced_result)

        # バッチ結果のフォーマット
        return self.result_formatter.format_batch_results(enhanced_results, output_type)

    async def process_dual_files(
        self,
        file1: str,
        file2: str,
        column: str,
        config: CLIConfig,
        output_type: str
    ) -> Dict[str, Any]:
        """
        デュアルファイルの処理（拡張版）

        Args:
            file1: ファイル1のパス
            file2: ファイル2のパス
            column: 比較する列名
            config: CLI設定
            output_type: 出力タイプ

        Returns:
            処理結果
        """
        # DualFileExtractorの拡張版を使用
        extractor = DualFileExtractor()

        # 拡張メソッドが存在しない場合は後方互換性のため実装
        if hasattr(extractor, 'compare_dual_files_enhanced'):
            result = extractor.compare_dual_files_enhanced(
                file1, file2, column, config, output_type
            )
            # awaitableでない場合はそのまま返す
            if hasattr(result, '__await__'):
                return await result
            else:
                return result
        else:
            # 既存メソッドを使用してから拡張フォーマットに変換
            results = extractor.compare_dual_files(file1, file2, column, output_type, config.use_gpu)

            # 結果を拡張フォーマットに変換
            enhanced_results = []
            if isinstance(results, list):
                for result in results:
                    enhanced_result = EnhancedResult(
                        score=result.get("similarity_score", 0.0),
                        method="embedding",  # 既存実装は埋め込みベース
                        processing_time=0.0,  # 既存実装では不明
                        input_data={"original_row": result},
                        metadata=result.get("similarity_details", {})
                    )
                    enhanced_results.append(enhanced_result)
            else:
                # score タイプの場合
                enhanced_result = EnhancedResult(
                    score=results.get("score", 0.0),
                    method="embedding",
                    processing_time=0.0,
                    input_data={"file1": file1, "file2": file2},
                    metadata=results.get("json", {})
                )
                enhanced_results = [enhanced_result]

            return self.result_formatter.format_batch_results(enhanced_results, output_type)

    def process_file(self, config: CLIConfig) -> Dict[str, Any]:
        """
        ファイル処理（テスト互換性のための汎用メソッド）

        Args:
            config: CLI設定

        Returns:
            処理結果
        """
        if hasattr(config, 'dual_mode') and config.dual_mode:
            # デュアルファイル処理
            return asyncio.run(self.process_dual_files(
                config.dual_file1,
                config.dual_file2,
                config.dual_column,
                config,
                getattr(config, 'output_type', 'score')
            ))
        elif hasattr(config, 'input_file') and config.input_file:
            # 単一ファイル処理
            return asyncio.run(self.process_single_file(
                config.input_file,
                config,
                getattr(config, 'output_type', 'score')
            ))
        else:
            raise ValueError("有効な入力ファイルが指定されていません")

    def create_output(
        self,
        enhanced_result: EnhancedResult,
        legacy_mode: bool = False
    ) -> Dict[str, Any]:
        """
        出力の作成

        Args:
            enhanced_result: 拡張結果
            legacy_mode: レガシー互換モード

        Returns:
            フォーマット済み出力
        """
        if legacy_mode:
            return self.compatibility_layer.convert_to_legacy_format(enhanced_result)
        else:
            return self.result_formatter.format_score_output(enhanced_result)


def create_parser() -> argparse.ArgumentParser:
    """テスト互換性のための簡易パーサー作成関数"""
    return create_enhanced_argument_parser()


def create_enhanced_argument_parser() -> argparse.ArgumentParser:
    """拡張引数パーサーを作成"""
    parser = argparse.ArgumentParser(
        description="JSON比較ツール（LLM対応版）（vLLM API対応） - JSONLファイル内のinference列を比較",
        usage="json_compare [input_file] [options] | json_compare dual file1 file2 [options]"
    )

    # 位置引数の処理を修正
    parser.add_argument('input_file', nargs='?', help='入力JSONLファイルパス')

    # 基本オプション
    parser.add_argument('--type', choices=['score', 'file'], default='score',
                      help='出力タイプ (default: score)')
    parser.add_argument('-o', '--output', help='出力ファイルパス')
    parser.add_argument('--gpu', action='store_true', help='GPUを使用する')

    # LLM関連オプション
    llm_group = parser.add_argument_group('LLM options', 'LLMベース類似度判定オプション（vLLM API対応）')
    llm_group.add_argument('--llm', action='store_true',
                          help='LLMベース判定を有効化')
    llm_group.add_argument('--method', choices=['auto', 'embedding', 'llm'],
                          default='auto',
                          help='計算方法の選択 (default: auto)')
    llm_group.add_argument('--prompt-file',
                          help='プロンプトテンプレートファイルのパス')
    llm_group.add_argument('--model', '--llm-model', dest='llm_model',
                          help='使用するLLMモデル名 (default: qwen3-14b-awq)')
    llm_group.add_argument('--temperature', type=float, default=0.2,
                          help='LLM生成温度 (0.0-1.0, default: 0.2)')
    llm_group.add_argument('--max-tokens', type=int, default=64,
                          help='最大トークン数 (default: 64)')
    llm_group.add_argument('--no-fallback', action='store_false', dest='fallback_enabled',
                          default=True, help='フォールバック機能を無効化')

    # 出力オプション
    output_group = parser.add_argument_group('Output options', '出力制御オプション')
    output_group.add_argument('--legacy', action='store_true',
                             help='レガシー互換出力フォーマット')
    output_group.add_argument('--verbose', '-v', action='store_true',
                             help='詳細ログ出力')

    # デュアルファイル用の隠し引数（サブコマンドとしても使用可能）
    parser.add_argument('--dual', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--file1', help=argparse.SUPPRESS)
    parser.add_argument('--file2', help=argparse.SUPPRESS)
    parser.add_argument('--column', default='inference', help=argparse.SUPPRESS)

    return parser


def create_single_file_parser() -> argparse.ArgumentParser:
    """単一ファイル処理用パーサーを作成"""
    parser = argparse.ArgumentParser(
        description="JSON比較ツール（LLM対応版）（vLLM API対応） - JSONLファイル内のinference列を比較"
    )

    parser.add_argument('input_file', help='入力JSONLファイルパス')
    parser.add_argument('--type', choices=['score', 'file'], default='score',
                       help='出力タイプ (default: score)')
    parser.add_argument('-o', '--output', help='出力ファイルパス')
    parser.add_argument('--gpu', action='store_true', help='GPUを使用する')

    # LLM関連オプション
    llm_group = parser.add_argument_group('LLM options', 'LLMベース類似度判定オプション（vLLM API対応）')
    llm_group.add_argument('--llm', action='store_true', help='LLMベース判定を有効化')
    llm_group.add_argument('--method', choices=['auto', 'embedding', 'llm'], default='auto',
                          help='計算方法の選択 (default: auto)')
    llm_group.add_argument('--prompt-file', help='プロンプトテンプレートファイルのパス')
    llm_group.add_argument('--model', '--llm-model', dest='llm_model', help='使用するLLMモデル名')
    llm_group.add_argument('--temperature', type=float, default=0.2,
                          help='LLM生成温度 (0.0-1.0, default: 0.2)')
    llm_group.add_argument('--max-tokens', type=int, default=64,
                          help='最大トークン数 (default: 64)')
    llm_group.add_argument('--no-fallback', action='store_false', dest='fallback_enabled',
                          default=True, help='フォールバック機能を無効化')

    # 出力オプション
    output_group = parser.add_argument_group('Output options', '出力制御オプション')
    output_group.add_argument('--legacy', action='store_true',
                             help='レガシー互換出力フォーマット')
    output_group.add_argument('--verbose', '-v', action='store_true', help='詳細ログ出力')

    return parser


def create_dual_file_parser() -> argparse.ArgumentParser:
    """デュアルファイル処理用パーサーを作成"""
    parser = argparse.ArgumentParser(
        description="JSON比較ツール（LLM対応版）（vLLM API対応） - 2つのJSONLファイルの指定列を比較"
    )

    parser.add_argument('file1', help='1つ目のJSONLファイル')
    parser.add_argument('file2', help='2つ目のJSONLファイル')
    parser.add_argument('--column', default='inference', help='比較する列名 (default: inference)')
    parser.add_argument('--type', choices=['score', 'file'], default='score',
                       help='出力タイプ (default: score)')
    parser.add_argument('-o', '--output', help='出力ファイルパス')
    parser.add_argument('--gpu', action='store_true', help='GPUを使用する')

    # LLM関連オプション
    llm_group = parser.add_argument_group('LLM options', 'LLMベース類似度判定オプション（vLLM API対応）')
    llm_group.add_argument('--llm', action='store_true', help='LLMベース判定を有効化')
    llm_group.add_argument('--method', choices=['auto', 'embedding', 'llm'], default='auto',
                          help='計算方法の選択 (default: auto)')
    llm_group.add_argument('--prompt-file', help='プロンプトテンプレートファイルのパス')
    llm_group.add_argument('--model', '--llm-model', dest='llm_model', help='使用するLLMモデル名')
    llm_group.add_argument('--temperature', type=float, default=0.2,
                          help='LLM生成温度 (0.0-1.0, default: 0.2)')
    llm_group.add_argument('--max-tokens', type=int, default=64,
                          help='最大トークン数 (default: 64)')
    llm_group.add_argument('--no-fallback', action='store_false', dest='fallback_enabled',
                          default=True, help='フォールバック機能を無効化')

    # 出力オプション
    output_group = parser.add_argument_group('Output options', '出力制御オプション')
    output_group.add_argument('--legacy', action='store_true',
                             help='レガシー互換出力フォーマット')
    output_group.add_argument('--verbose', '-v', action='store_true', help='詳細ログ出力')

    return parser


def parse_enhanced_args(args: List[str] = None) -> Tuple[argparse.Namespace, CLIConfig]:
    """
    拡張引数を解析

    Args:
        args: 解析する引数リスト（Noneの場合はsys.argvを使用）

    Returns:
        解析された引数とCLI設定のタプル
    """
    if args is None:
        args = sys.argv[1:]

    # 引数の前処理：最初の引数が"dual"かどうかをチェック
    if len(args) > 0 and args[0] == "dual":
        # dualコマンドとして解析
        parser = create_dual_file_parser()
        parsed_args = parser.parse_args(args[1:])  # "dual"を除去
        parsed_args.command = "dual"
    else:
        # 統一パーサーで解析
        parser = create_enhanced_argument_parser()
        parsed_args = parser.parse_args(args)
        parsed_args.command = getattr(parsed_args, 'command', None)

    # CLI設定の作成
    config = CLIConfig(
        calculation_method=getattr(parsed_args, 'method', 'auto'),
        llm_enabled=getattr(parsed_args, 'llm', False),
        use_gpu=getattr(parsed_args, 'gpu', False),
        prompt_file=getattr(parsed_args, 'prompt_file', None),
        model_name=getattr(parsed_args, 'llm_model', None),
        temperature=getattr(parsed_args, 'temperature', 0.2),
        max_tokens=getattr(parsed_args, 'max_tokens', 64),
        fallback_enabled=getattr(parsed_args, 'fallback_enabled', True),
        legacy_mode=getattr(parsed_args, 'legacy', False),
        verbose=getattr(parsed_args, 'verbose', False),
        # テスト互換性用の追加フィールド
        input_file=getattr(parsed_args, 'input_file', None),
        output_type=getattr(parsed_args, 'type', 'score'),
        dual_mode=getattr(parsed_args, 'dual', False),
        dual_file1=getattr(parsed_args, 'file1', None),
        dual_file2=getattr(parsed_args, 'file2', None),
        dual_column=getattr(parsed_args, 'column', 'inference'),
        strategy_method=getattr(parsed_args, 'method', None)
    )

    return parsed_args, config


async def create_similarity_calculator_from_args(config: CLIConfig) -> SimilarityCalculator:
    """
    CLI設定から類似度計算機を作成

    Args:
        config: CLI設定

    Returns:
        設定済みの類似度計算機
    """
    llm_config = config.to_llm_config()

    return await create_similarity_calculator(
        use_gpu=config.use_gpu,
        llm_config=llm_config
    )


async def main_enhanced():
    """拡張メイン処理"""
    try:
        # 引数解析
        parsed_args, config = parse_enhanced_args()

        # ログ設定
        if config.verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.WARNING)

        # CLI実行
        enhanced_cli = EnhancedCLI()

        if parsed_args.command == 'dual':
            # デュアルファイル処理
            result = await enhanced_cli.process_dual_files(
                parsed_args.file1,
                parsed_args.file2,
                parsed_args.column,
                config,
                parsed_args.type
            )
        elif parsed_args.input_file:
            # 単一ファイル処理
            result = await enhanced_cli.process_single_file(
                parsed_args.input_file,
                config,
                parsed_args.type
            )
        else:
            # ヘルプ表示
            parser = create_enhanced_argument_parser()
            parser.print_help()
            sys.exit(1)

        # 結果出力
        output_json = json.dumps(result, ensure_ascii=False, indent=2)

        if parsed_args.output:
            # ファイル出力
            with open(parsed_args.output, 'w', encoding='utf-8') as f:
                f.write(output_json)
            print(f"結果を {parsed_args.output} に保存しました", file=sys.stderr)
        else:
            # 標準出力
            print(output_json)

    except Exception as e:
        if config.verbose if 'config' in locals() else False:
            import traceback
            traceback.print_exc(file=sys.stderr)
        else:
            print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)


# ヘルプ・エラーメッセージ機能
def get_detailed_help() -> str:
    """詳細なヘルプメッセージを取得"""
    help_text = """
JSON比較ツール - 拡張LLM対応版

使用法:
    json_compare input.jsonl [オプション]
    json_compare dual file1.jsonl file2.jsonl [オプション]

基本オプション:
    --type {score,file}     出力形式を指定 (デフォルト: score)
    --output FILE           結果をファイルに出力
    --verbose              詳細ログを有効化

計算方法オプション:
    --method {auto,embedding,llm}  計算方法を指定 (デフォルト: auto)
    --llm                   LLMモードを有効化
    --gpu                   GPU計算を使用

LLMオプション:
    --model MODEL           使用するLLMモデル名 (デフォルト: qwen3-14b-awq)
    --temperature TEMP      生成温度 0.0-1.0 (デフォルト: 0.2)
    --max-tokens TOKENS     最大トークン数 (デフォルト: 64)
    --prompt-file FILE      カスタムプロンプトファイル (.yaml)

使用例:
    # 基本的な使用
    json_compare data.jsonl

    # LLMモード:
    json_compare data.jsonl --llm --model qwen3-14b-awq

    # デュアルファイル比較:
    json_compare dual file1.jsonl file2.jsonl --column inference --llm

    # カスタムプロンプト:
    json_compare data.jsonl --llm --prompt-file custom_prompt.yaml

詳細: https://github.com/your-repo/json_compare
"""
    return help_text.strip()


def get_llm_usage_examples() -> str:
    """LLM使用例を取得"""
    examples = """
LLM機能の使用例:

1. 基本的なLLM使用:
   json_compare data.jsonl --llm

2. 特定モデルの指定:
   json_compare data.jsonl --llm --model qwen3-14b-awq

3. 生成パラメータの調整:
   json_compare data.jsonl --llm --temperature 0.3 --max-tokens 128

4. デュアルファイル比較:
   json_compare dual file1.jsonl file2.jsonl --column inference --llm

5. カスタムプロンプト使用:
   json_compare data.jsonl --llm --prompt-file my_prompt.yaml

6. 詳細ログ付き:
   json_compare data.jsonl --llm --verbose

LLMサーバー設定:
    環境変数 LLM_BASE_URL でエンドポイントを指定
    例: export LLM_BASE_URL=http://192.168.1.18:8000
"""
    return examples.strip()


def format_llm_error(error_type: str, message: str) -> str:
    """LLM関連エラーをフォーマット"""
    error_messages = {
        "connection_error": f"""
LLMサーバーへの接続に失敗しました: {message}

対処法:
1. LLMサーバーが起動していることを確認
2. 環境変数 LLM_BASE_URL が正しく設定されていることを確認
3. ネットワーク接続を確認

フォールバック: --method embedding で埋め込みモードに切り替え可能
""",
        "invalid_model": f"""
指定されたモデルが見つかりません: {message}

対処法:
1. 利用可能なモデル一覧を確認
2. モデル名のスペルを確認
3. LLMサーバーにモデルがロードされていることを確認

デフォルトモデル qwen3-14b-awq を使用することを推奨
""",
        "rate_limit": f"""
レート制限に達しました: {message}

対処法:
1. しばらく待ってから再実行
2. バッチサイズを小さくする
3. 並行処理数を減らす

レート制限解除後に自動的に再試行されます
""",
        "parsing_error": f"""
LLM応答の解析に失敗しました: {message}

対処法:
1. プロンプトファイルの形式を確認
2. 温度パラメータを下げる（より確定的な出力）
3. 異なるモデルを試す

自動的に埋め込みモードにフォールバックします
"""
    }

    return error_messages.get(error_type, f"LLMエラー: {message}").strip()


def get_fallback_suggestions(error_context: str) -> str:
    """フォールバック提案メッセージを取得"""
    suggestions = {
        "llm_failed": """
LLM計算に失敗しました。以下の代替手段をお試しください:

1. 埋め込みモードに切り替え:
   --method embedding

2. GPU加速を使用:
   --gpu

3. ローカル計算のみ:
   --method embedding --no-llm
""",
        "connection_failed": """
LLMサーバーに接続できません。以下を確認してください:

1. LLMサーバーの状態確認:
   curl http://192.168.1.18:8000/health

2. ローカル計算に切り替え:
   --method embedding

3. 設定確認:
   echo $LLM_BASE_URL
"""
    }

    return suggestions.get(error_context, "代替手段を検討してください").strip()


class EnhancedCLIErrorHandler:
    """拡張CLIエラーハンドラー"""

    def __init__(self):
        self.error_categories = {
            "llm_api_error": "LLM API エラー",
            "configuration_error": "設定エラー",
            "file_error": "ファイルエラー",
            "validation_error": "バリデーションエラー"
        }

    def format_error(self, error_type: str, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """詳細なエラー情報をフォーマット"""
        context = context or {}

        error_info = {
            "category": self.error_categories.get(error_type, "不明なエラー"),
            "message": message,
            "details": self._build_details(error_type, context),
            "suggestions": self._get_suggestions(error_type, context)
        }

        return error_info

    def _build_details(self, error_type: str, context: Dict[str, Any]) -> str:
        """エラー詳細を構築"""
        if error_type == "llm_api_error":
            model = context.get("model", "不明")
            endpoint = context.get("endpoint", "不明")
            return f"モデル: {model}, エンドポイント: {endpoint}"

        return "詳細情報なし"

    def _get_suggestions(self, error_type: str, context: Dict[str, Any]) -> List[str]:
        """エラーごとの提案を取得"""
        suggestions_map = {
            "llm_api_error": [
                "LLMサーバーの状態を確認",
                "ネットワーク接続を確認",
                "埋め込みモードに切り替え",
                "設定ファイルを確認"
            ],
            "configuration_error": [
                "設定値を確認",
                "環境変数を確認",
                "デフォルト値を使用"
            ]
        }

        return suggestions_map.get(error_type, ["サポートに連絡"])


def validate_llm_configuration(config: Dict[str, Any]) -> None:
    """LLM設定を検証"""
    temperature = config.get("temperature", 0.2)
    max_tokens = config.get("max_tokens", 64)

    if not (0.0 <= temperature <= 1.0):
        raise ValueError("temperatureは0.0から1.0の間で指定してください")

    if max_tokens < 1:
        raise ValueError("max_tokensは1以上で指定してください")


class ProgressiveErrorGuide:
    """段階的エラーガイダンス"""

    def __init__(self):
        self.error_history = {}

    def get_guidance(self, error_type: str, attempt: int = 1) -> str:
        """試行回数に応じたガイダンスを取得"""
        if attempt == 1:
            return self._get_basic_guidance(error_type)
        elif attempt <= 3:
            return self._get_intermediate_guidance(error_type)
        else:
            return self._get_advanced_guidance(error_type)

    def _get_basic_guidance(self, error_type: str) -> str:
        """基本的なガイダンス"""
        basic_guides = {
            "llm_connection_error": """
基本的な接続確認:
1. LLMサーバーが起動していることを確認
2. ネットワーク接続を確認
3. 環境変数 LLM_BASE_URL を確認
"""
        }
        return basic_guides.get(error_type, "基本的なトラブルシューティングを実行")

    def _get_intermediate_guidance(self, error_type: str) -> str:
        """中級ガイダンス"""
        intermediate_guides = {
            "llm_connection_error": """
詳細な診断:
1. curl でエンドポイントの応答を確認
2. ファイアウォール設定を確認
3. プロキシ設定を確認
4. 代替エンドポイントを試す
"""
        }
        return intermediate_guides.get(error_type, "詳細な診断を実行")

    def _get_advanced_guidance(self, error_type: str) -> str:
        """上級ガイダンス"""
        advanced_guides = {
            "llm_connection_error": """
詳細な診断:
1. システム管理者に連絡
2. 代替設定を試す
3. ログファイルを確認
4. バックアップシステムを使用
"""
        }
        return advanced_guides.get(error_type, "高度なトラブルシューティングを実行")


def get_best_practices() -> str:
    """ベストプラクティスドキュメントを取得"""
    practices = """
JSON比較ツール - ベストプラクティス

## パフォーマンス最適化

1. バッチサイズの調整:
   - 大きなファイル: バッチサイズを小さくして、メモリ使用量を制御
   - 小さなファイル: バッチサイズを大きくして、効率を向上

2. GPU使用:
   - 埋め込み計算で --gpu オプションを使用
   - CUDAが利用可能な環境で推奨

3. LLM設定最適化:
   - 短いテキスト: 温度を低めに設定 (0.1-0.3)
   - 長いテキスト: 適度な温度設定 (0.3-0.5)

## プロンプト設計

1. YAML形式プロンプト:
   - 構造化されたプロンプトテンプレートを使用
   - 変数 {text1}, {text2} を適切に配置

2. 例示の活用:
   - Few-shot学習で精度向上
   - 類似度判定の基準を明確化

## トラブルシューティング

1. 接続エラー:
   - LLMサーバーの状態確認
   - ネットワーク設定の確認

2. パフォーマンス問題:
   - バッチサイズの調整
   - 計算方法の変更

3. 精度問題:
   - プロンプトの最適化
   - 温度パラメータの調整

## 運用のコツ

1. ログ活用:
   - --verbose でデバッグ情報を確認
   - エラーログの定期的なチェック

2. バックアップ戦略:
   - フォールバック計算の活用
   - 複数の計算方法の併用

3. 継続的改善:
   - 結果の品質評価
   - パラメータの継続的調整
"""
    return practices.strip()


if __name__ == "__main__":
    asyncio.run(main_enhanced())