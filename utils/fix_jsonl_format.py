#!/usr/bin/env python3
"""
JSONLファイルを1データ1行に修正するヘルパープログラム
複数行にまたがるJSONオブジェクトを1行にコンパクト化します
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Optional
import argparse


def fix_jsonl_file(input_path: str, output_path: Optional[str] = None,
                   backup: bool = True, verbose: bool = False) -> bool:
    """
    JSONLファイルを修正して1データ1行にする

    Args:
        input_path: 入力JSONLファイルのパス
        output_path: 出力先パス（省略時は元ファイルを上書き）
        backup: バックアップを作成するか
        verbose: 詳細情報を出力するか

    Returns:
        成功した場合True
    """
    try:
        input_file = Path(input_path)

        if not input_file.exists():
            print(f"❌ ファイルが存在しません: {input_path}")
            return False

        if not input_file.suffix == '.jsonl':
            print(f"⚠️ 警告: {input_path} はJSONLファイルではない可能性があります")

        # JSONオブジェクトを読み込む
        json_objects = []
        current_obj = ""
        brace_count = 0
        line_count = 0

        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line_count += 1
                current_obj += line

                # ブレースカウントで完全なJSONオブジェクトを検出
                brace_count += line.count('{') - line.count('}')

                if brace_count == 0 and current_obj.strip():
                    try:
                        # JSONオブジェクトとしてパース
                        obj = json.loads(current_obj)
                        json_objects.append(obj)
                        current_obj = ""

                        if verbose:
                            print(f"  ✓ オブジェクト {len(json_objects)} をパース（行 {line_count}）")
                    except json.JSONDecodeError as e:
                        # 単一行のJSONオブジェクトの可能性をチェック
                        for single_line in current_obj.strip().split('\n'):
                            if single_line.strip():
                                try:
                                    obj = json.loads(single_line)
                                    json_objects.append(obj)
                                    if verbose:
                                        print(f"  ✓ 単一行オブジェクトをパース")
                                except:
                                    pass
                        current_obj = ""

        if not json_objects:
            print(f"❌ 有効なJSONオブジェクトが見つかりません: {input_path}")
            return False

        # バックアップ作成
        if backup and not output_path:
            backup_path = input_file.with_suffix(f'.jsonl.bak')
            input_file.rename(backup_path)
            if verbose:
                print(f"📁 バックアップ作成: {backup_path}")

        # 出力先決定
        output_file = Path(output_path) if output_path else input_file

        # 1行ずつ書き込み
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, obj in enumerate(json_objects):
                # ensure_ascii=Falseで日本語をそのまま出力
                json_line = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
                f.write(json_line + '\n')

        print(f"✅ 修正完了: {output_file}")
        print(f"   - {len(json_objects)} 個のJSONオブジェクトを処理")
        print(f"   - 元のファイル: {line_count} 行 → 修正後: {len(json_objects)} 行")

        return True

    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return False


def fix_directory(directory: str, pattern: str = "*.jsonl",
                 recursive: bool = False, dry_run: bool = False,
                 verbose: bool = False) -> int:
    """
    ディレクトリ内のJSONLファイルを一括修正

    Args:
        directory: 対象ディレクトリ
        pattern: ファイルパターン（デフォルト: *.jsonl）
        recursive: サブディレクトリも処理するか
        dry_run: 実際には修正せず対象ファイルを表示のみ
        verbose: 詳細情報を出力するか

    Returns:
        処理したファイル数
    """
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"❌ ディレクトリが存在しません: {directory}")
        return 0

    # ファイルを検索
    if recursive:
        files = list(dir_path.rglob(pattern))
    else:
        files = list(dir_path.glob(pattern))

    if not files:
        print(f"⚠️ 対象ファイルが見つかりません: {pattern}")
        return 0

    print(f"📂 {len(files)} 個のファイルを処理します")

    if dry_run:
        print("\n🔍 ドライラン - 以下のファイルが処理対象です:")
        for f in files:
            print(f"   - {f}")
        return len(files)

    success_count = 0
    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] 処理中: {file_path.name}")
        if fix_jsonl_file(str(file_path), backup=True, verbose=verbose):
            success_count += 1

    print(f"\n" + "=" * 50)
    print(f"✨ 完了: {success_count}/{len(files)} ファイルを修正しました")

    return success_count


def validate_jsonl(file_path: str) -> bool:
    """
    JSONLファイルが正しいフォーマットか検証

    Args:
        file_path: 検証するファイルのパス

    Returns:
        正しいフォーマットの場合True
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            line_num = 0
            for line in f:
                line_num += 1
                if line.strip():  # 空行はスキップ
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as e:
                        print(f"❌ 行 {line_num} でエラー: {e}")
                        print(f"   内容: {line[:100]}...")
                        return False

        print(f"✅ {file_path} は正しいJSONL形式です")
        return True

    except Exception as e:
        print(f"❌ ファイル読み込みエラー: {e}")
        return False


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description='JSONLファイルを1データ1行に修正するツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 単一ファイルを修正
  python fix_jsonl_format.py data.jsonl

  # ディレクトリ内のすべてのJSONLファイルを修正
  python fix_jsonl_format.py --dir ./datas

  # サブディレクトリも含めて修正
  python fix_jsonl_format.py --dir . --recursive

  # ドライラン（実際には修正しない）
  python fix_jsonl_format.py --dir ./datas --dry-run

  # ファイルの検証のみ
  python fix_jsonl_format.py --validate data.jsonl
        """
    )

    parser.add_argument('file', nargs='?', help='修正するJSONLファイル')
    parser.add_argument('--dir', help='ディレクトリ内のファイルを一括処理')
    parser.add_argument('--pattern', default='*.jsonl',
                       help='ファイルパターン（デフォルト: *.jsonl）')
    parser.add_argument('--recursive', '-r', action='store_true',
                       help='サブディレクトリも処理')
    parser.add_argument('--output', '-o', help='出力先ファイル（単一ファイル処理時のみ）')
    parser.add_argument('--no-backup', action='store_true',
                       help='バックアップを作成しない')
    parser.add_argument('--dry-run', action='store_true',
                       help='実際には修正せず対象ファイルを表示')
    parser.add_argument('--validate', help='JSONLファイルの検証のみ実行')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='詳細情報を出力')

    args = parser.parse_args()

    # 検証モード
    if args.validate:
        sys.exit(0 if validate_jsonl(args.validate) else 1)

    # ディレクトリ処理モード
    if args.dir:
        count = fix_directory(
            args.dir,
            pattern=args.pattern,
            recursive=args.recursive,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        sys.exit(0 if count > 0 or args.dry_run else 1)

    # 単一ファイル処理モード
    if args.file:
        success = fix_jsonl_file(
            args.file,
            output_path=args.output,
            backup=not args.no_backup,
            verbose=args.verbose
        )
        sys.exit(0 if success else 1)

    # 引数なしの場合
    parser.print_help()
    sys.exit(1)


if __name__ == '__main__':
    main()