#!/usr/bin/env python3
"""CSV変換機能のテスト"""

import json
import sys
from pathlib import Path

import pytest

# パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# テスト対象モジュールをインポート
from src.api import json_to_csv


def test_json_to_csv_score_mode():
    """scoreモードのCSV変換テスト"""
    # スコアモードのサンプルデータ
    score_data = {
        "overall_similarity": 0.8765,
        "statistics": {
            "mean": 0.8765,
            "median": 0.8901,
            "std_dev": 0.0543,
            "min": 0.7234,
            "max": 0.9456
        },
        "_metadata": {
            "processing_time": "2.34秒",
            "original_filename": "test.jsonl",
            "gpu_used": True
        }
    }

    # CSV変換
    csv_content = json_to_csv(score_data, "score")

    # BOMが含まれることを確認
    assert csv_content.startswith('\uFEFF')

    # BOMを除いた内容をチェック（改行コードを統一）
    csv_content_no_bom = csv_content[1:].replace('\r\n', '\n').replace('\r', '\n')
    csv_lines = csv_content_no_bom.strip().split('\n')

    # ヘッダーの確認
    assert csv_lines[0] == "項目,値"

    # 各値の確認
    assert "全体類似度,0.8765" in csv_content
    assert "平均類似度,0.8765" in csv_content
    assert "中央値,0.8901" in csv_content
    assert "標準偏差,0.0543" in csv_content
    assert "最小値,0.7234" in csv_content
    assert "最大値,0.9456" in csv_content

    # メタデータの確認
    assert "処理時間,2.34秒" in csv_content
    assert "元ファイル名,test.jsonl" in csv_content
    assert "GPU使用,有" in csv_content


def test_json_to_csv_file_mode():
    """fileモードのCSV変換テスト"""
    # ファイルモードのサンプルデータ
    file_data = [
        {
            "line_number": 1,
            "similarity": 0.8765,
            "inference1": "この文章はテストです",
            "inference2": "この文書は試験です"
        },
        {
            "line_number": 2,
            "similarity": 0.9234,
            "inference1": "機械学習は便利です",
            "inference2": "機械学習は有用です"
        },
        {
            "line_number": 3,
            "similarity": 0.7891,
            "inference1": "CSVファイルを生成します",
            "inference2": "カンマ区切りファイルを作成します"
        }
    ]

    # CSV変換
    csv_content = json_to_csv(file_data, "file")

    # BOMが含まれることを確認
    assert csv_content.startswith('\uFEFF')

    # BOMを除いた内容をチェック（改行コードを統一）
    csv_content_no_bom = csv_content[1:].replace('\r\n', '\n').replace('\r', '\n')
    csv_lines = csv_content_no_bom.strip().split('\n')

    # ヘッダーの確認
    assert csv_lines[0] == "行番号,類似度,推論1,推論2"

    # 各行のデータ確認（CSVライブラリは必要に応じて引用符を追加する）
    assert '1,0.8765' in csv_lines[1]
    assert 'この文章はテストです' in csv_lines[1]
    assert 'この文書は試験です' in csv_lines[1]

    assert '2,0.9234' in csv_lines[2]
    assert '機械学習は便利です' in csv_lines[2]
    assert '機械学習は有用です' in csv_lines[2]

    assert '3,0.7891' in csv_lines[3]
    assert 'CSVファイルを生成します' in csv_lines[3]
    assert 'カンマ区切りファイルを作成します' in csv_lines[3]


def test_json_to_csv_with_quotes():
    """ダブルクォートを含むデータのエスケープテスト"""
    file_data = [
        {
            "line_number": 1,
            "similarity": 0.8765,
            "inference1": 'これは"テスト"です',
            "inference2": 'これも"テスト"です'
        }
    ]

    # CSV変換
    csv_content = json_to_csv(file_data, "file")

    # ダブルクォートが適切にエスケープされていることを確認
    # CSVでは " は "" でエスケープされる
    assert '"これは""テスト""です"' in csv_content
    assert '"これも""テスト""です"' in csv_content


def test_json_to_csv_empty_data():
    """空データの処理テスト"""
    # scoreモードで空のデータ
    score_data = {}
    csv_content = json_to_csv(score_data, "score")
    assert csv_content.startswith('\uFEFF')
    assert "項目,値" in csv_content

    # fileモードで空のデータ
    file_data = []
    csv_content = json_to_csv(file_data, "file")
    assert csv_content == '\uFEFF'


def test_json_to_csv_missing_fields():
    """一部フィールドが欠けているデータのテスト"""
    # statisticsの一部が欠けているケース
    score_data = {
        "overall_similarity": 0.8765,
        "statistics": {
            "mean": 0.8765,
            "median": 0.8901
            # std_dev, min, maxが欠けている
        }
    }

    csv_content = json_to_csv(score_data, "score")

    # 存在するフィールドは表示される
    assert "全体類似度,0.8765" in csv_content
    assert "平均類似度,0.8765" in csv_content
    assert "中央値,0.8901" in csv_content

    # 欠けているフィールドは0として表示
    assert "標準偏差,0.0000" in csv_content
    assert "最小値,0.0000" in csv_content
    assert "最大値,0.0000" in csv_content


def test_json_to_csv_gpu_false():
    """GPU未使用の場合のメタデータテスト"""
    score_data = {
        "overall_similarity": 0.8765,
        "_metadata": {
            "processing_time": "5.67秒",
            "original_filename": "test.jsonl",
            "gpu_used": False
        }
    }

    csv_content = json_to_csv(score_data, "score")
    assert "GPU使用,無" in csv_content


if __name__ == "__main__":
    # テスト実行
    pytest.main([__file__, "-v"])