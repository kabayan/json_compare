#!/usr/bin/env python3
"""
埋め込みモデルの動作確認スクリプト
"""

import sys
import traceback

def test_embedding_model():
    """埋め込みモデルのテスト"""
    print("=== 埋め込みモデル動作確認 ===")

    try:
        print("1. 埋め込みモジュールのインポート...")
        from src.embedding import JapaneseEmbedding
        print("✓ インポート成功")

        print("2. 埋め込みモデルの初期化...")
        embedding = JapaneseEmbedding(use_gpu=False)
        print("✓ 初期化成功")

        print("3. 類似度計算テスト...")
        text1 = "カテゴリA"
        text2 = "カテゴリB"
        similarity = embedding.calculate_similarity(text1, text2)
        print(f"✓ 類似度計算成功: {similarity}")

        return True

    except Exception as e:
        print(f"✗ エラー発生: {e}")
        print(f"トレースバック:")
        traceback.print_exc()
        return False

def test_similarity_function():
    """similarity.pyの関数テスト"""
    print("\n=== similarity.py 関数テスト ===")

    try:
        print("1. similarity関数のインポート...")
        from src.similarity import calculate_json_similarity
        print("✓ インポート成功")

        print("2. JSON類似度計算テスト...")
        json1 = "カテゴリA"
        json2 = "カテゴリB"
        score, details = calculate_json_similarity(json1, json2)
        print(f"✓ 類似度計算成功: score={score}, details={details}")

        return True

    except Exception as e:
        print(f"✗ エラー発生: {e}")
        print(f"トレースバック:")
        traceback.print_exc()
        return False

def test_process_jsonl():
    """process_jsonl_file関数のテスト"""
    print("\n=== process_jsonl_file 関数テスト ===")

    try:
        print("1. __main__関数のインポート...")
        from src.__main__ import process_jsonl_file
        print("✓ インポート成功")

        print("2. 一時ファイルでのテスト...")
        import tempfile
        import json

        # テスト用の一時ファイル作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as tmp:
            test_data = [
                {"inference1": "カテゴリA", "inference2": "カテゴリA"},
                {"inference1": "カテゴリB", "inference2": "カテゴリC"}
            ]
            for data in test_data:
                tmp.write(json.dumps(data, ensure_ascii=False) + '\n')
            temp_path = tmp.name

        print(f"テストファイル作成: {temp_path}")

        print("3. process_jsonl_file実行...")
        result = process_jsonl_file(temp_path, "score")
        print(f"✓ 処理成功: {result}")

        # 一時ファイル削除
        import os
        os.remove(temp_path)

        return True

    except Exception as e:
        print(f"✗ エラー発生: {e}")
        print(f"トレースバック:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("デバッグスクリプト開始")

    # 各テストを順番に実行
    results = []

    results.append(("Embedding Model", test_embedding_model()))
    results.append(("Similarity Function", test_similarity_function()))
    results.append(("Process JSONL", test_process_jsonl()))

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