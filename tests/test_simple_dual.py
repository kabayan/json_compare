#!/usr/bin/env python3
"""
簡単な2ファイル比較テスト
"""

import json
import tempfile
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

def create_test_file1():
    """テスト用ファイル1を作成"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        data = [
            {"id": 1, "inference": "これはテストテキスト1", "score": 0.8},
            {"id": 2, "inference": "これはテストテキスト2", "score": 0.9},
            {"id": 3, "inference": "これはテストテキスト3", "score": 0.7}
        ]
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        return f.name

def create_test_file2():
    """テスト用ファイル2を作成"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        data = [
            {"id": 1, "inference": "これはテストテキスト1", "score": 0.85},
            {"id": 2, "inference": "これはテストテキスト2修正版", "score": 0.88},
            {"id": 3, "inference": "これは異なるテキスト3", "score": 0.75}
        ]
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        return f.name

def test_dual_file_comparison():
    """2ファイル比較のシンプルテスト"""
    print("=" * 60)
    print("2ファイル比較機能のテスト")
    print("=" * 60)

    # テストファイルを作成
    file1 = create_test_file1()
    file2 = create_test_file2()

    try:
        from src.dual_file_extractor import DualFileExtractor

        # DualFileExtractorのインスタンスを作成
        extractor = DualFileExtractor()

        print("\n1. デフォルト列（inference）での比較")
        print("-" * 40)

        # 比較実行
        result = extractor.compare_dual_files(
            file1,
            file2,
            column_name="inference",
            output_type="score",
            use_gpu=False
        )

        # 結果表示
        print("✅ 比較成功！")
        print(f"スコア: {result.get('score', 'N/A')}")
        print(f"意味: {result.get('meaning', 'N/A')}")
        print(f"総行数: {result.get('total_lines', 'N/A')}")
        print(f"\nメタデータ:")
        if '_metadata' in result:
            print(f"  - 比較列: {result['_metadata'].get('column_compared', 'N/A')}")
            print(f"  - 比較行数: {result['_metadata'].get('rows_compared', 'N/A')}")
            print(f"  - ファイル1: {result['_metadata'].get('source_files', {}).get('file1', 'N/A')}")
            print(f"  - ファイル2: {result['_metadata'].get('source_files', {}).get('file2', 'N/A')}")

        print("\n2. fileタイプでの詳細結果")
        print("-" * 40)

        # fileタイプで再実行
        result_detail = extractor.compare_dual_files(
            file1,
            file2,
            column_name="inference",
            output_type="file",
            use_gpu=False
        )

        if isinstance(result_detail, list):
            print(f"✅ 詳細結果取得成功！({len(result_detail)}行)")
            for i, item in enumerate(result_detail[:2], 1):  # 最初の2行のみ表示
                print(f"\n行{i}:")
                print(f"  inference1: {item.get('inference1', 'N/A')[:30]}...")
                print(f"  inference2: {item.get('inference2', 'N/A')[:30]}...")
                print(f"  類似度スコア: {item.get('similarity_score', 'N/A')}")

        print("\n" + "=" * 60)
        print("✨ すべてのテストが成功しました！")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # テストファイルのクリーンアップ
        if os.path.exists(file1):
            os.unlink(file1)
        if os.path.exists(file2):
            os.unlink(file2)
        print("\n一時ファイルをクリーンアップしました")

if __name__ == "__main__":
    success = test_dual_file_comparison()
    sys.exit(0 if success else 1)