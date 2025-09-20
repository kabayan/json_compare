#!/usr/bin/env python3
"""
API機能の直接テスト（進捗トラッカー無効）
"""

import sys
import traceback
import tempfile
import os

def test_dual_file_extractor():
    """DualFileExtractorの直接テスト"""
    print("=== DualFileExtractor 直接テスト ===")

    try:
        print("1. DualFileExtractorのインポート...")
        from src.dual_file_extractor import DualFileExtractor
        print("✓ インポート成功")

        print("2. テストファイルの作成...")
        # テスト用の一時ファイル作成
        temp1 = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8')
        temp2 = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8')

        # テストデータ書き込み
        import json
        test_data1 = [
            {"text": "テスト1", "inference": "カテゴリA"},
            {"text": "テスト2", "inference": "カテゴリB"}
        ]
        test_data2 = [
            {"text": "テスト1", "inference": "カテゴリA"},
            {"text": "テスト2", "inference": "カテゴリC"}
        ]

        for data in test_data1:
            temp1.write(json.dumps(data, ensure_ascii=False) + '\n')
        for data in test_data2:
            temp2.write(json.dumps(data, ensure_ascii=False) + '\n')

        temp1.close()
        temp2.close()

        print(f"テストファイル1: {temp1.name}")
        print(f"テストファイル2: {temp2.name}")

        print("3. DualFileExtractorの初期化...")
        extractor = DualFileExtractor()
        print("✓ 初期化成功")

        print("4. 2ファイル比較実行（score）...")
        result = extractor.compare_dual_files(
            temp1.name,
            temp2.name,
            column_name="inference",
            output_type="score",
            use_gpu=False
        )
        print(f"✓ score比較成功: {result}")

        print("5. 2ファイル比較実行（file）...")
        result = extractor.compare_dual_files(
            temp1.name,
            temp2.name,
            column_name="inference",
            output_type="file",
            use_gpu=False
        )
        print(f"✓ file比較成功: 結果数={len(result) if isinstance(result, list) else 'N/A'}")

        # 一時ファイル削除
        os.remove(temp1.name)
        os.remove(temp2.name)

        return True

    except Exception as e:
        print(f"✗ エラー発生: {e}")
        print(f"トレースバック:")
        traceback.print_exc()
        return False

def test_api_function_direct():
    """API関数の直接テスト（非同期処理なし）"""
    print("\n=== API関数直接テスト ===")

    try:
        # テスト用の一時ファイル作成
        temp1 = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8')
        temp2 = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8')

        import json
        test_data1 = [
            {"text": "テスト1", "inference": "カテゴリA"},
            {"text": "テスト2", "inference": "カテゴリB"}
        ]
        test_data2 = [
            {"text": "テスト1", "inference": "カテゴリA"},
            {"text": "テスト2", "inference": "カテゴリC"}
        ]

        for data in test_data1:
            temp1.write(json.dumps(data, ensure_ascii=False) + '\n')
        for data in test_data2:
            temp2.write(json.dumps(data, ensure_ascii=False) + '\n')

        temp1.close()
        temp2.close()

        print("1. APIからの実行処理をシミュレート...")
        from src.dual_file_extractor import DualFileExtractor

        # 進捗トラッカーなしでの実行
        extractor = DualFileExtractor()
        result = extractor.compare_dual_files(
            temp1.name,
            temp2.name,
            column_name="inference",
            output_type="score",
            use_gpu=False
        )
        print(f"✓ 進捗トラッカーなしでの実行成功: {result}")

        # 一時ファイル削除
        os.remove(temp1.name)
        os.remove(temp2.name)

        return True

    except Exception as e:
        print(f"✗ エラー発生: {e}")
        print(f"トレースバック:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("API直接テストスクリプト開始")

    # 各テストを順番に実行
    results = []

    results.append(("DualFileExtractor", test_dual_file_extractor()))
    results.append(("API Function Direct", test_api_function_direct()))

    print("\n=== テスト結果サマリー ===")
    for test_name, success in results:
        status = "✓ 成功" if success else "✗ 失敗"
        print(f"{test_name}: {status}")

    # すべて成功した場合のみ0で終了
    if all(result[1] for result in results):
        print("\nすべてのテストが成功しました")
        sys.exit(0)
    else:
        print("\n一部のテストが失敗しました")
        sys.exit(1)