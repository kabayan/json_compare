"""
Playwright MCP 包括的WebUI進捗表示テスト
全パターンの組み合わせでポーリング機能を検証
"""

import asyncio
import json
import time
from pathlib import Path


async def test_single_file_embedding_score():
    """1ファイル埋め込みモード・スコア形式テスト"""
    print("\n=== Testing: 1ファイル埋め込みモード・スコア形式 ===")

    # テストデータ作成
    test_data = [
        {"inference1": {"text": "これはテスト1です", "score": 0.95},
         "inference2": {"text": "これはテスト1の変形です", "score": 0.93}},
        {"inference1": {"text": "別のテストデータ", "score": 0.87},
         "inference2": {"text": "別のテスト用データ", "score": 0.89}}
    ]

    test_file = "/tmp/test_embedding_score.jsonl"
    with open(test_file, 'w', encoding='utf-8') as f:
        for item in test_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    # ブラウザでテスト実行
    # 注: このテストはPlaywright MCPツールを使って手動実行する必要があります
    print(f"テストファイル作成: {test_file}")
    print("次の手順でテストを実行してください:")
    print("1. browser_navigate でWebUIを開く (http://localhost:18081/ui)")
    print("2. ファイルをアップロード")
    print("3. 埋め込みモード・スコア形式を選択")
    print("4. 処理を実行")
    print("5. ポーリング動作を確認")

    return test_file


async def test_single_file_llm_file():
    """1ファイルLLMモード・ファイル形式テスト"""
    print("\n=== Testing: 1ファイルLLMモード・ファイル形式 ===")

    # テストデータ作成
    test_data = [
        {"inference1": {"text": "LLMテスト1", "score": 0.88},
         "inference2": {"text": "LLMテスト1の変形", "score": 0.86}},
        {"inference1": {"text": "LLMテスト2", "score": 0.92},
         "inference2": {"text": "LLMテスト2の変形", "score": 0.90}}
    ]

    test_file = "/tmp/test_llm_file.jsonl"
    with open(test_file, 'w', encoding='utf-8') as f:
        for item in test_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"テストファイル作成: {test_file}")
    print("LLMモードを有効にしてファイル形式で出力")

    return test_file


async def test_dual_file_embedding():
    """2ファイル埋め込みモード比較テスト"""
    print("\n=== Testing: 2ファイル埋め込みモード比較 ===")

    # ファイル1作成
    data1 = [
        {"inference": {"text": "ファイル1のテキスト1", "score": 0.91}},
        {"inference": {"text": "ファイル1のテキスト2", "score": 0.85}}
    ]

    file1 = "/tmp/test_dual_1.jsonl"
    with open(file1, 'w', encoding='utf-8') as f:
        for item in data1:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    # ファイル2作成
    data2 = [
        {"inference": {"text": "ファイル2のテキスト1", "score": 0.89}},
        {"inference": {"text": "ファイル2のテキスト2", "score": 0.87}}
    ]

    file2 = "/tmp/test_dual_2.jsonl"
    with open(file2, 'w', encoding='utf-8') as f:
        for item in data2:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"テストファイル作成: {file1}, {file2}")
    print("2ファイル比較モードで実行")

    return file1, file2


async def verify_polling_behavior():
    """ポーリング動作の検証"""
    print("\n=== Verifying: ポーリング動作 ===")
    print("確認項目:")
    print("1. setIntervalが1秒間隔で動作しているか")
    print("2. /api/progress/{task_id}エンドポイントが呼ばれているか")
    print("3. 進捗表示が更新されているか")
    print("4. 処理完了時にclearIntervalが実行されているか")
    print("5. エラー時にリトライが最大5回まで行われるか")


async def verify_metadata_consistency():
    """メタデータ整合性の検証"""
    print("\n=== Verifying: メタデータ整合性 ===")
    print("確認項目:")
    print("1. calculation_methodまたはcomparison_methodが正しく設定されているか")
    print("2. APIレスポンスのフィールドが変更されていないか")
    print("3. _metadataフィールドが保持されているか")
    print("4. ダウンロードファイルが元の構造を維持しているか")


def generate_test_report(results):
    """テストレポートの生成"""
    print("\n" + "="*50)
    print("テストレポート")
    print("="*50)

    # パターン別結果
    patterns = [
        "1ファイル埋め込みスコア",
        "1ファイル埋め込みファイル",
        "1ファイルLLMスコア",
        "1ファイルLLMファイル",
        "2ファイル埋め込みスコア",
        "2ファイル埋め込みファイル",
        "2ファイルLLMスコア",
        "2ファイルLLMファイル"
    ]

    print("\n【パターン別テスト結果】")
    for i, pattern in enumerate(patterns, 1):
        status = results.get(pattern, "未実行")
        print(f"{i}. {pattern}: {status}")

    print("\n【ポーリング動作検証】")
    polling_items = [
        "setInterval 1秒間隔",
        "API呼び出し確認",
        "進捗表示更新",
        "clearInterval実行",
        "エラーリトライ"
    ]

    for item in polling_items:
        status = results.get(f"polling_{item}", "未検証")
        print(f"- {item}: {status}")

    print("\n【メタデータ整合性】")
    metadata_items = [
        "calculation_method設定",
        "APIレスポンス保持",
        "_metadataフィールド",
        "ダウンロード構造"
    ]

    for item in metadata_items:
        status = results.get(f"metadata_{item}", "未検証")
        print(f"- {item}: {status}")

    print("\n" + "="*50)


if __name__ == "__main__":
    print("Playwright MCP 包括的テスト開始")
    print("="*50)

    # テストファイル作成
    asyncio.run(test_single_file_embedding_score())
    asyncio.run(test_single_file_llm_file())
    asyncio.run(test_dual_file_embedding())

    # 検証項目の説明
    asyncio.run(verify_polling_behavior())
    asyncio.run(verify_metadata_consistency())

    # レポート生成（手動実行後に更新）
    results = {
        "1ファイル埋め込みスコア": "実行待ち",
        "1ファイル埋め込みファイル": "実行待ち",
        "1ファイルLLMスコア": "実行待ち",
        "1ファイルLLMファイル": "実行待ち",
        "2ファイル埋め込みスコア": "実行待ち",
        "2ファイル埋め込みファイル": "実行待ち",
        "2ファイルLLMスコア": "実行待ち",
        "2ファイルLLMファイル": "実行待ち"
    }

    generate_test_report(results)

    print("\n手動テスト手順:")
    print("1. Playwright MCPツールを使用してブラウザを起動")
    print("2. 各パターンのテストを実行")
    print("3. ポーリング動作を確認")
    print("4. メタデータを検証")
    print("5. 結果をレポートに記録")