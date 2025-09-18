#!/usr/bin/env python3
"""
JSONLフォーマット自動修正機能の統合テスト
"""

import json
import tempfile
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

def create_multiline_jsonl(file_path: str):
    """複数行にまたがるJSONLファイルを作成"""
    content = '''{
  "inference1": "これはテストテキスト1です",
  "inference2": "これはテストテキスト1です"
}
{
  "inference1": "これはテストテキスト2です",
  "inference2": "これはテストテキスト2の修正版です"
}
{
  "inference1": "これはテストテキスト3です",
  "inference2": "これはテストテキスト3の別バージョンです"
}
'''
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def create_dual_file_test_files():
    """2ファイル比較用のテストファイルを作成"""
    # ファイル1（複数行形式）
    content1 = '''{
  "id": 1,
  "inference": "最初のテキスト",
  "other": "データ1"
}
{
  "id": 2,
  "inference": "二番目のテキスト",
  "other": "データ2"
}
{
  "id": 3,
  "inference": "三番目のテキスト",
  "other": "データ3"
}
'''

    # ファイル2（複数行形式）
    content2 = '''{
  "id": 1,
  "inference": "最初のテキスト（修正）",
  "other": "データ4"
}
{
  "id": 2,
  "inference": "二番目のテキスト（修正）",
  "other": "データ5"
}
{
  "id": 3,
  "inference": "三番目のテキスト（修正）",
  "other": "データ6"
}
'''

    # 一時ファイルを作成
    file1 = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8')
    file1.write(content1)
    file1.close()

    file2 = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8')
    file2.write(content2)
    file2.close()

    return file1.name, file2.name


def test_main_module():
    """__main__モジュールのテスト"""
    print("=" * 60)
    print("1. __main__モジュールのテスト")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        create_multiline_jsonl(f.name)
        test_file = f.name

    try:
        from src.__main__ import process_jsonl_file

        print(f"\n複数行形式のJSONLファイルを作成: {test_file}")
        print("処理を実行中...")

        # scoreタイプで処理
        result = process_jsonl_file(test_file, "score")

        if isinstance(result, dict) and 'total_lines' in result:
            print(f"✅ 成功！{result['total_lines']}行を処理")
            print(f"   スコア: {result.get('score', 'N/A')}")
            return True
        else:
            print(f"❌ 失敗: 予期しない結果 - {result}")
            return False

    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if os.path.exists(test_file):
            os.unlink(test_file)
            print("テストファイルをクリーンアップしました")


def test_dual_file_extractor():
    """DualFileExtractorのテスト"""
    print("\n" + "=" * 60)
    print("2. DualFileExtractorのテスト")
    print("=" * 60)

    file1, file2 = create_dual_file_test_files()

    try:
        from src.dual_file_extractor import DualFileExtractor

        print(f"\n複数行形式のJSONLファイルを作成:")
        print(f"  - ファイル1: {file1}")
        print(f"  - ファイル2: {file2}")
        print("処理を実行中...")

        extractor = DualFileExtractor()
        result = extractor.compare_dual_files(
            file1, file2,
            column_name="inference",
            output_type="score",
            use_gpu=False
        )

        if isinstance(result, dict):
            print(f"✅ 成功！比較処理が完了")
            if '_metadata' in result:
                print(f"   比較列: {result['_metadata'].get('column_compared', 'N/A')}")
                print(f"   比較行数: {result['_metadata'].get('rows_compared', 'N/A')}")
            return True
        else:
            print(f"❌ 失敗: 予期しない結果 - {result}")
            return False

    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        for f in [file1, file2]:
            if os.path.exists(f):
                os.unlink(f)
        print("テストファイルをクリーンアップしました")


def test_jsonl_formatter_module():
    """jsonl_formatterモジュールの直接テスト"""
    print("\n" + "=" * 60)
    print("3. JSONLFormatterモジュールのテスト")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        create_multiline_jsonl(f.name)
        test_file = f.name

    try:
        from src.jsonl_formatter import JSONLFormatter, auto_fix_jsonl_file

        print(f"\n複数行形式のJSONLファイルを作成: {test_file}")

        # フォーマットチェック
        print("フォーマットチェック中...")
        is_valid = JSONLFormatter.check_format(test_file)
        print(f"  - 修正前: {'✅ 有効' if is_valid else '❌ 無効（修正が必要）'}")

        if not is_valid:
            # 自動修正
            print("自動修正を実行中...")
            fixed_path = auto_fix_jsonl_file(test_file)

            # 修正後の確認
            is_valid_after = JSONLFormatter.check_format(fixed_path)
            print(f"  - 修正後: {'✅ 有効' if is_valid_after else '❌ まだ無効'}")

            # 行数の確認
            with open(test_file, 'r') as f:
                original_lines = len(f.readlines())
            with open(fixed_path, 'r') as f:
                fixed_lines = len([line for line in f if line.strip()])

            print(f"\n行数の変化: {original_lines}行 → {fixed_lines}行")

            # 内容の検証
            with open(fixed_path, 'r') as f:
                for i, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            json.loads(line)
                            print(f"  行{i}: ✅ 有効なJSON")
                        except:
                            print(f"  行{i}: ❌ 無効なJSON")

            return is_valid_after
        else:
            print("✅ 元のファイルは既に有効な形式でした")
            return True

    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if os.path.exists(test_file):
            os.unlink(test_file)
        print("\nテストファイルをクリーンアップしました")


def main():
    """メインテスト実行"""
    print("\n" + "🧪" * 30)
    print("JSONLフォーマット自動修正機能 統合テスト")
    print("🧪" * 30 + "\n")

    results = []

    # 各モジュールをテスト
    results.append(("JSONLFormatter", test_jsonl_formatter_module()))
    results.append(("__main__", test_main_module()))
    results.append(("DualFileExtractor", test_dual_file_extractor()))

    # 結果サマリ
    print("\n" + "=" * 60)
    print("テスト結果サマリ")
    print("=" * 60)

    for module_name, success in results:
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"  {module_name}: {status}")

    all_passed = all(r[1] for r in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("✨ すべてのテストが成功しました！")
        print("JSONLフォーマット自動修正機能が正常に統合されています。")
    else:
        print("⚠️ 一部のテストが失敗しました")
        print("上記のエラーメッセージを確認してください。")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())