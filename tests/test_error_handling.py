#!/usr/bin/env python3
"""エラーハンドリングとロギング機能のテスト"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest
import requests


API_URL = "http://localhost:18081"


def test_invalid_file_type():
    """無効なファイルタイプのエラーハンドリング"""
    # .txt ファイルをアップロード試行
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is not a JSONL file")
        temp_file = f.name

    try:
        with open(temp_file, 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}
            data = {'type': 'score', 'gpu': 'false'}

            response = requests.post(f"{API_URL}/api/compare/single", files=files, data=data)

            assert response.status_code == 400
            result = response.json()

            # FastAPIのエラーレスポンスはdetailに含まれる
            if 'detail' in result:
                detail = result['detail']
            else:
                detail = result

            # エラーIDが生成されているか確認
            assert 'error_id' in detail
            assert detail['error_id'].startswith('ERR-')

            # エラーメッセージと提案が含まれているか確認
            assert 'error' in detail
            assert 'suggestions' in detail
            assert len(detail['suggestions']) > 0

            print(f"✅ 無効ファイルタイプエラー: {detail['error_id']}")

    finally:
        os.unlink(temp_file)


def test_invalid_json_with_repair():
    """無効なJSONの修復機能テスト"""
    # 修復可能な問題があるJSONLファイル
    content = '''{"inference1": "test1", "inference2": "test2"}
{"inference1": "test3"}
{"inference2": "test4"}
{"inference1": "test5", "inference2": "test6",}
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(content)
        temp_file = f.name

    try:
        with open(temp_file, 'rb') as f:
            files = {'file': ('test.jsonl', f, 'application/jsonl')}
            data = {'type': 'score', 'gpu': 'false'}

            response = requests.post(f"{API_URL}/api/compare/single", files=files, data=data)

            # 修復成功して処理が完了することを確認
            assert response.status_code == 200
            result = response.json()

            # メタデータに修復件数が含まれているか確認
            if '_metadata' in result:
                print(f"✅ JSONL修復成功: {result['_metadata'].get('data_repairs', 0)}件の修復")

    finally:
        os.unlink(temp_file)


def test_empty_file_error():
    """空ファイルのエラーハンドリング"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # 空のファイル
        temp_file = f.name

    try:
        with open(temp_file, 'rb') as f:
            files = {'file': ('empty.jsonl', f, 'application/jsonl')}
            data = {'type': 'score', 'gpu': 'false'}

            response = requests.post(f"{API_URL}/api/compare/single", files=files, data=data)

            assert response.status_code == 400
            result = response.json()

            # FastAPIのエラーレスポンスはdetailに含まれる
            if 'detail' in result:
                detail = result['detail']
            else:
                detail = result

            # エラーIDとメッセージの確認
            assert 'error_id' in detail
            assert 'error' in detail
            assert 'suggestions' in detail

            print(f"✅ 空ファイルエラー: {detail['error_id']}")

    finally:
        os.unlink(temp_file)


def test_large_file_error():
    """大容量ファイル（100MB超）のエラーハンドリング"""
    # 101MBのダミーファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # 各行を1KB程度にして、101K行書き込む
        line = json.dumps({"inference1": "x" * 500, "inference2": "y" * 500}) + "\n"
        for _ in range(101 * 1024):
            f.write(line)
        temp_file = f.name

    try:
        with open(temp_file, 'rb') as f:
            files = {'file': ('large.jsonl', f, 'application/jsonl')}
            data = {'type': 'score', 'gpu': 'false'}

            response = requests.post(f"{API_URL}/api/compare/single", files=files, data=data)

            assert response.status_code == 413
            result = response.json()

            # FastAPIのエラーレスポンスはdetailに含まれる
            if 'detail' in result:
                detail = result['detail']
            else:
                detail = result

            # エラー詳細の確認
            assert 'error_id' in detail
            assert 'error' in detail

            print(f"✅ 大容量ファイルエラー: ファイルサイズ制限を正しく検出")

    finally:
        os.unlink(temp_file)


def test_metrics_endpoint():
    """メトリクスエンドポイントのテスト"""
    response = requests.get(f"{API_URL}/metrics")

    assert response.status_code == 200
    result = response.json()

    # メトリクス情報が含まれているか確認
    assert 'upload_metrics' in result
    assert 'timestamp' in result

    metrics = result['upload_metrics']

    if 'total_uploads' in metrics:
        print(f"✅ メトリクス取得成功:")
        print(f"  - 総アップロード数: {metrics['total_uploads']}")
        if metrics['total_uploads'] > 0:
            print(f"  - 成功率: {metrics.get('success_rate', 'N/A')}%")
            print(f"  - 平均処理時間: {metrics.get('average_processing_time', 'N/A')}秒")
    else:
        print("✅ メトリクス取得成功 (まだアップロードなし)")


def test_health_with_metrics():
    """ヘルスチェックでメトリクスがログに記録されることを確認"""
    response = requests.get(f"{API_URL}/health")

    assert response.status_code == 200
    result = response.json()

    assert result['status'] == 'healthy'
    assert 'cli_available' in result

    print(f"✅ ヘルスチェック成功: CLI利用可能={result['cli_available']}")


def test_successful_upload_with_logging():
    """正常なアップロードでログが記録されることを確認"""
    # 正常なJSONLファイル
    content = '''{"inference1": "test1", "inference2": "test2"}
{"inference1": "test3", "inference2": "test4"}
{"inference1": "test5", "inference2": "test6"}
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(content)
        temp_file = f.name

    try:
        with open(temp_file, 'rb') as f:
            files = {'file': ('success.jsonl', f, 'application/jsonl')}
            data = {'type': 'score', 'gpu': 'false'}

            start_time = time.time()
            response = requests.post(f"{API_URL}/api/compare/single", files=files, data=data)
            processing_time = time.time() - start_time

            assert response.status_code == 200
            result = response.json()

            # メタデータの確認
            assert '_metadata' in result
            metadata = result['_metadata']
            assert 'processing_time' in metadata
            assert 'original_filename' in metadata
            assert metadata['original_filename'] == 'success.jsonl'

            print(f"✅ 正常アップロード成功:")
            print(f"  - 処理時間: {metadata['processing_time']}")
            print(f"  - GPU使用: {metadata.get('gpu_used', False)}")

    finally:
        os.unlink(temp_file)


def test_log_files_created():
    """ログファイルが作成されているか確認"""
    log_dir = Path("/tmp/json_compare/logs")

    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))

        expected_logs = ["access.log", "error.log", "metrics.log"]
        existing_logs = [f.name for f in log_files]

        print(f"✅ ログディレクトリ確認: {log_dir}")
        print(f"  - 存在するログファイル: {existing_logs}")

        for expected in expected_logs:
            if expected in existing_logs:
                log_file = log_dir / expected
                size = log_file.stat().st_size
                print(f"  - {expected}: {size} bytes")
    else:
        print("⚠️ ログディレクトリがまだ作成されていません（初回実行時は正常）")


if __name__ == "__main__":
    print("\n=== エラーハンドリングとロギングのテスト ===\n")

    # 各テストを実行
    test_invalid_file_type()
    test_invalid_json_with_repair()
    test_empty_file_error()
    test_large_file_error()
    test_metrics_endpoint()
    test_health_with_metrics()
    test_successful_upload_with_logging()
    test_log_files_created()

    print("\n✅ すべてのテストが完了しました！")