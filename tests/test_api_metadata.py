#!/usr/bin/env python3
"""APIメタデータ検証のシンプルなテスト"""

import requests
import json
import tempfile
import os


def test_single_file_metadata():
    """単一ファイルアップロードのメタデータテスト"""
    print("🧪 単一ファイルアップロードのメタデータテスト...")

    # テストデータ作成
    test_data = [
        {"inference1": "機械学習", "inference2": "マシンラーニング"},
        {"inference1": "深層学習", "inference2": "ディープラーニング"},
        {"inference1": "自然言語処理", "inference2": "NLP"}
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        for item in test_data:
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')
        temp_path = f.name

    try:
        # APIリクエスト
        with open(temp_path, 'rb') as file:
            files = {'file': ('test.jsonl', file, 'application/x-jsonlines')}
            data = {'type': 'score', 'gpu': 'false'}

            response = requests.post(
                'http://localhost:18081/api/compare/single',
                files=files,
                data=data
            )

        print(f"ステータスコード: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(json.dumps(result, ensure_ascii=False, indent=2))

            # メタデータ検証
            assert "_metadata" in result, "❌ _metadata が存在しません"
            metadata = result["_metadata"]

            assert "calculation_method" in metadata, "❌ calculation_method が存在しません"
            assert metadata["calculation_method"] == "embedding", \
                f"❌ calculation_method が期待値と異なります: {metadata['calculation_method']}"

            assert "processing_time" in metadata, "❌ processing_time が存在しません"
            assert "original_filename" in metadata, "❌ original_filename が存在しません"
            assert "gpu_used" in metadata, "❌ gpu_used が存在しません"
            assert metadata["gpu_used"] == False, f"❌ gpu_used が期待値と異なります: {metadata['gpu_used']}"

            print("✅ 単一ファイルメタデータテスト成功！")
            return True
        else:
            print(f"❌ エラー: {response.text}")
            return False

    finally:
        os.unlink(temp_path)


def test_dual_file_metadata():
    """2ファイル比較のメタデータテスト"""
    print("\n🧪 2ファイル比較のメタデータテスト...")

    # テストファイル作成
    file1_data = [
        {"inference": "機械学習"},
        {"inference": "深層学習"}
    ]
    file2_data = [
        {"inference": "マシンラーニング"},
        {"inference": "ディープラーニング"}
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f1:
        for item in file1_data:
            json.dump(item, f1, ensure_ascii=False)
            f1.write('\n')
        file1_path = f1.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f2:
        for item in file2_data:
            json.dump(item, f2, ensure_ascii=False)
            f2.write('\n')
        file2_path = f2.name

    try:
        # APIリクエスト
        with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
            files = {
                'file1': ('file1.jsonl', f1, 'application/x-jsonlines'),
                'file2': ('file2.jsonl', f2, 'application/x-jsonlines')
            }
            data = {
                'column': 'inference',
                'type': 'score',
                'gpu': 'false'
            }

            response = requests.post(
                'http://localhost:18081/api/compare/dual',
                files=files,
                data=data
            )

        print(f"ステータスコード: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(json.dumps(result, ensure_ascii=False, indent=2))

            # メタデータ検証
            assert "_metadata" in result, "❌ _metadata が存在しません"
            metadata = result["_metadata"]

            assert "calculation_method" in metadata, "❌ calculation_method が存在しません"
            assert metadata["calculation_method"] == "embedding", \
                f"❌ calculation_method が期待値と異なります: {metadata['calculation_method']}"

            assert "processing_time" in metadata, "❌ processing_time が存在しません"
            assert "original_files" in metadata, "❌ original_files が存在しません"
            assert "gpu_used" in metadata, "❌ gpu_used が存在しません"

            print("✅ 2ファイルメタデータテスト成功！")
            return True
        else:
            print(f"❌ エラー: {response.text}")
            return False

    finally:
        os.unlink(file1_path)
        os.unlink(file2_path)


def main():
    """メイン関数"""
    print("=" * 50)
    print("APIメタデータ検証テスト")
    print("=" * 50)

    # APIサーバーの確認
    try:
        response = requests.get('http://localhost:18081/health')
        if response.status_code != 200:
            print("❌ APIサーバーが起動していません")
            return
    except requests.exceptions.ConnectionError:
        print("❌ APIサーバーに接続できません（http://localhost:18081）")
        return

    # テスト実行
    results = []

    results.append(test_single_file_metadata())
    results.append(test_dual_file_metadata())

    # 結果サマリー
    print("\n" + "=" * 50)
    if all(results):
        print("✨ すべてのテストが成功しました！")
        print("📌 calculation_method メタデータが正しく出力されています。")
    else:
        print("❌ 一部のテストが失敗しました")
    print("=" * 50)


if __name__ == "__main__":
    main()