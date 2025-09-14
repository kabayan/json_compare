#!/usr/bin/env python3
"""JSON比較ツールのCLIエントリーポイント"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from .similarity import calculate_json_similarity, set_gpu_mode


def load_json_file(file_path: str) -> Any:
    """JSONまたはJSONLファイルを読み込む

    Args:
        file_path: ファイルパス

    Returns:
        パースされたJSONオブジェクト

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        json.JSONDecodeError: JSONパースエラー
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # JSONLファイルの場合は最初の行のみ処理
    if path.suffix == '.jsonl':
        lines = content.strip().split('\n')
        if lines:
            return json.loads(lines[0])
        else:
            return {}

    # 通常のJSONファイル
    return json.loads(content)


def process_jsonl_file(file_path: str, output_type: str) -> Any:
    """JSONLファイルを処理して各行のinference1とinference2を比較

    Args:
        file_path: 入力JSONLファイルパス
        output_type: 出力タイプ (score/file)

    Returns:
        scoreタイプ: 全体平均の辞書
        fileタイプ: 各行の詳細リスト
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    scores = []
    field_match_ratios = []
    value_similarities = []
    file_results = []
    total_lines = 0

    with open(path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue

            total_lines += 1

            try:
                # 各行をパース
                data = json.loads(line)

                # inference1とinference2を取得
                inference1 = data.get('inference1', '{}')
                inference2 = data.get('inference2', '{}')

                # 類似度計算
                score, details = calculate_json_similarity(inference1, inference2)

                # スコア収集（平均計算用）
                scores.append(float(score))
                field_match_ratios.append(float(details.get("field_match_ratio", 0)))
                value_similarities.append(float(details.get("value_similarity", 0)))

                # fileタイプの場合は詳細を保存
                if output_type == "file":
                    result = data.copy()
                    result['similarity_score'] = float(score)
                    result['similarity_details'] = {
                        "field_match_ratio": float(details.get("field_match_ratio", 0)),
                        "value_similarity": float(details.get("value_similarity", 0))
                    }
                    file_results.append(result)

            except json.JSONDecodeError as e:
                print(f"警告: {line_num}行目のJSONパースエラー: {e}", file=sys.stderr)
                continue
            except Exception as e:
                print(f"警告: {line_num}行目の処理エラー: {e}", file=sys.stderr)
                continue

    # scoreタイプの場合は全体平均を返す
    if output_type == "score":
        if scores:
            avg_score = sum(scores) / len(scores)
            avg_field_match = sum(field_match_ratios) / len(field_match_ratios)
            avg_value_sim = sum(value_similarities) / len(value_similarities)

            meaning = "完全一致" if avg_score >= 0.99 else \
                     "非常に類似" if avg_score >= 0.8 else \
                     "類似" if avg_score >= 0.6 else \
                     "やや類似" if avg_score >= 0.4 else \
                     "低い類似度"

            return {
                "file": str(file_path),
                "total_lines": total_lines,
                "score": round(avg_score, 4),
                "meaning": meaning,
                "json": {
                    "field_match_ratio": round(avg_field_match, 4),
                    "value_similarity": round(avg_value_sim, 4),
                    "final_score": round(avg_score, 4)
                }
            }
        else:
            return {
                "file": str(file_path),
                "total_lines": 0,
                "score": 0.0,
                "meaning": "データなし",
                "json": {
                    "field_match_ratio": 0.0,
                    "value_similarity": 0.0,
                    "final_score": 0.0
                }
            }
    else:
        # fileタイプの場合は詳細リストを返す
        return file_results


def format_score_output(file1: str, file2: str, score: float, details: Dict[str, Any]) -> Dict[str, Any]:
    """scoreタイプの出力フォーマットを生成

    Args:
        file1: ファイル1のパス
        file2: ファイル2のパス
        score: 類似度スコア
        details: 詳細情報

    Returns:
        フォーマット済みの出力辞書
    """
    meaning = "完全一致" if score >= 0.99 else \
             "非常に類似" if score >= 0.8 else \
             "類似" if score >= 0.6 else \
             "やや類似" if score >= 0.4 else \
             "低い類似度"

    # float32型を標準のfloat型に変換
    score = float(score)
    field_match_ratio = float(details.get("field_match_ratio", 0))
    value_similarity = float(details.get("value_similarity", 0))

    return {
        "file": f"{file1} vs {file2}",
        "score": round(score, 4),
        "meaning": meaning,
        "json": {
            "field_match_ratio": field_match_ratio,
            "value_similarity": value_similarity,
            "final_score": round(score, 4)
        }
    }


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="JSON比較ツール - JSONLファイル内のinference1とinference2を比較"
    )

    parser.add_argument(
        "input_file",
        help="入力JSONLファイルパス"
    )

    parser.add_argument(
        "-o", "--output",
        help="出力ファイルパス (省略時は標準出力)"
    )

    parser.add_argument(
        "--type",
        choices=["score", "file"],
        default="score",
        help="出力タイプ (default: score)"
    )

    parser.add_argument(
        "--gpu",
        action="store_true",
        help="GPUを使用する (default: CPU)"
    )

    args = parser.parse_args()

    try:
        # GPU使用モードを設定
        if args.gpu:
            set_gpu_mode(True)

        # JSONLファイル読み込みと処理
        results = process_jsonl_file(args.input_file, args.type)

        # 結果出力
        output_json = json.dumps(results, ensure_ascii=False, indent=2)

        if args.output:
            # ファイルに出力
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_json)
            print(f"結果を {args.output} に保存しました", file=sys.stderr)
        else:
            # 標準出力
            print(output_json)

    except FileNotFoundError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"エラー: JSONパースエラー - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"エラー: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()