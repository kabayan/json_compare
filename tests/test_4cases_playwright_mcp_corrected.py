"""
Playwright MCP 4ケース検証テスト（修正版）
WebUIの4つの組み合わせを正しくテストし、課題を報告

テストケース：
1. Embedding + Score形式
2. Embedding + File形式
3. LLM + Score形式
4. LLM + File形式
"""

import json
import time
from pathlib import Path
from datetime import datetime

def prepare_test_files():
    """テスト用ファイル準備"""
    # 小さなテストデータ（処理が速い）
    test_data_1 = [
        {"text": "テスト1", "inference": "カテゴリA"},
        {"text": "テスト2", "inference": "カテゴリB"}
    ]

    test_data_2 = [
        {"text": "テスト1", "inference": "カテゴリA"},
        {"text": "テスト2", "inference": "カテゴリC"}
    ]

    # ファイル作成
    file1_path = Path("/tmp/test_file1.jsonl")
    file2_path = Path("/tmp/test_file2.jsonl")

    with open(file1_path, 'w', encoding='utf-8') as f:
        for item in test_data_1:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    with open(file2_path, 'w', encoding='utf-8') as f:
        for item in test_data_2:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"✅ テストファイル作成完了:")
    print(f"   - {file1_path}")
    print(f"   - {file2_path}")

    return str(file1_path), str(file2_path)

def create_test_plan():
    """テスト実行計画作成"""

    file1, file2 = prepare_test_files()

    test_cases = [
        {
            "name": "Case 1: Embedding + Score",
            "steps": [
                "1. http://localhost:18081/ui にアクセス",
                "2. '📑 2ファイル比較'ボタンをクリック",
                f"3. file1に {file1} をアップロード",
                f"4. file2に {file2} をアップロード",
                "5. #dual_typeで'score'を選択",
                "6. #dual_use_llmのチェックを外す（OFF）",
                "7. #dualFormの送信ボタンをクリック",
                "8. 結果表示を待機（最大30秒）",
                "9. #resultContainerの内容を確認"
            ],
            "expected": {
                "output_type": "score",
                "calculation_method": "embedding",
                "fields": ["score", "_metadata", "total_lines", "processing_time"]
            }
        },
        {
            "name": "Case 2: Embedding + File",
            "steps": [
                "1. http://localhost:18081/ui にアクセス",
                "2. '📑 2ファイル比較'ボタンをクリック",
                f"3. file1に {file1} をアップロード",
                f"4. file2に {file2} をアップロード",
                "5. #dual_typeで'file'を選択",
                "6. #dual_use_llmのチェックを外す（OFF）",
                "7. #dualFormの送信ボタンをクリック",
                "8. 結果表示を待機（最大30秒）",
                "9. #resultContainerの内容を確認"
            ],
            "expected": {
                "output_type": "file",
                "calculation_method": "embedding",
                "fields": ["detailed_results", "_metadata", "total_lines", "processing_time"]
            }
        },
        {
            "name": "Case 3: LLM + Score",
            "steps": [
                "1. http://localhost:18081/ui にアクセス",
                "2. '📑 2ファイル比較'ボタンをクリック",
                f"3. file1に {file1} をアップロード",
                f"4. file2に {file2} をアップロード",
                "5. #dual_typeで'score'を選択",
                "6. #dual_use_llmにチェックを入れる（ON）",
                "7. LLM設定が表示されたら確認",
                "8. #dualFormの送信ボタンをクリック",
                "9. 結果表示を待機（最大60秒、LLMは時間がかかる）",
                "10. #resultContainerの内容を確認"
            ],
            "expected": {
                "output_type": "score",
                "calculation_method": "llm",
                "fields": ["score", "_metadata", "total_lines", "processing_time"]
            }
        },
        {
            "name": "Case 4: LLM + File",
            "steps": [
                "1. http://localhost:18081/ui にアクセス",
                "2. '📑 2ファイル比較'ボタンをクリック",
                f"3. file1に {file1} をアップロード",
                f"4. file2に {file2} をアップロード",
                "5. #dual_typeで'file'を選択",
                "6. #dual_use_llmにチェックを入れる（ON）",
                "7. LLM設定が表示されたら確認",
                "8. #dualFormの送信ボタンをクリック",
                "9. 結果表示を待機（最大60秒、LLMは時間がかかる）",
                "10. #resultContainerの内容を確認"
            ],
            "expected": {
                "output_type": "file",
                "calculation_method": "llm",
                "fields": ["detailed_results", "_metadata", "total_lines", "processing_time"]
            }
        }
    ]

    return test_cases

def generate_playwright_test_report():
    """Playwright MCP実行用レポート生成"""

    test_cases = create_test_plan()

    print("\n" + "="*80)
    print("         Playwright MCP 4ケース検証テスト実行計画         ")
    print("="*80)

    print("\n## Playwright MCPを使用した実行手順")
    print("\nPlaywright MCPエージェントに以下を実行してもらう：")

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n### {test_case['name']}")
        print("実行ステップ:")
        for step in test_case['steps']:
            print(f"   {step}")

        print("\n期待される結果:")
        print(f"   - 出力形式: {test_case['expected']['output_type']}")
        print(f"   - 計算方法: {test_case['expected']['calculation_method']}")
        print(f"   - 必須フィールド: {', '.join(test_case['expected']['fields'])}")

        print("\n検証項目:")
        print("   1. 処理が正常に完了するか")
        print("   2. エラーが発生しないか")
        print("   3. 結果にscoreフィールドが含まれるか")
        print("   4. _metadataにcalculation_methodが正しく設定されているか")
        print("   5. 進捗表示（ポーリング）が動作するか")

    print("\n## 課題報告のポイント")
    print("1. 各ケースでの成功/失敗状況")
    print("2. エラーが発生した場合の詳細（エラーメッセージ、発生タイミング）")
    print("3. 期待値と実際の結果の差異")
    print("4. 改善提案")

    print("\n## 実行環境の確認事項")
    print("- APIサーバー起動確認: http://localhost:18081/health")
    print("- ディスク空き容量確認: df -h")
    print("- サーバーログ確認: tail -f /tmp/json_compare/logs/error.log")

    print("\n" + "="*80)
    print("テストファイル準備完了。Playwright MCPで実行してください。")
    print("="*80)

    # テスト結果記録用テンプレート
    results_template = {
        "timestamp": datetime.now().isoformat(),
        "test_cases": [
            {
                "name": tc["name"],
                "status": "pending",
                "error": None,
                "actual_result": None,
                "validation": {
                    "has_score": None,
                    "has_metadata": None,
                    "calculation_method_match": None,
                    "output_type_match": None
                }
            }
            for tc in test_cases
        ]
    }

    # 結果テンプレートを保存
    result_file = Path("/tmp/playwright_mcp_test_results.json")
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results_template, f, ensure_ascii=False, indent=2)

    print(f"\n結果記録テンプレート作成: {result_file}")

    return test_cases

if __name__ == "__main__":
    # テスト計画生成と表示
    test_cases = generate_playwright_test_report()

    print("\n📝 Playwright MCPエージェントへの指示:")
    print("---")
    print("上記の4つのテストケースを順番に実行し、")
    print("各ケースで以下を確認してください：")
    print("1. WebUIの操作が正常に行えるか")
    print("2. 結果が正しく表示されるか")
    print("3. エラーが発生しないか")
    print("4. 期待される構造の結果が返ってくるか")
    print("---")