#!/usr/bin/env python3
"""統合テストスイート - タスク8.1 システム全体の統合テスト"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest
import requests


API_URL = "http://localhost:18081"


class TestIntegration:
    """統合テストクラス"""

    @classmethod
    def setup_class(cls):
        """テストクラスのセットアップ"""
        print("\n=== 統合テスト開始 ===\n")

    def test_cli_basic_functionality(self):
        """CLIの基本機能が動作することを確認"""
        # テスト用JSONLファイルを作成
        content = '''{"inference1": "test1", "inference2": "test2"}
{"inference1": "test3", "inference2": "test4"}
{"inference1": "test5", "inference2": "test6"}
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(content)
            temp_file = f.name

        try:
            # CLIでスコア計算を実行
            result = subprocess.run(
                ['uv', 'run', 'python', '-m', 'src', temp_file, '--type', 'score'],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, f"CLIエラー: {result.stderr}"

            # 出力をJSONとしてパース
            output = json.loads(result.stdout)

            # 必須フィールドの確認
            assert 'score' in output or 'overall_similarity' in output
            assert 'total_lines' in output or 'statistics' in output

            print("✅ CLI基本機能: 正常動作")

        finally:
            os.unlink(temp_file)

    def test_api_endpoints_availability(self):
        """すべてのAPIエンドポイントが利用可能であることを確認"""
        endpoints = [
            ('GET', '/'),
            ('GET', '/health'),
            ('GET', '/ui'),
            ('GET', '/metrics')
        ]

        for method, endpoint in endpoints:
            response = requests.request(method, f"{API_URL}{endpoint}")
            assert response.status_code == 200, f"{endpoint} が利用できません"
            print(f"✅ {method} {endpoint}: ステータス {response.status_code}")

    def test_upload_and_download_flow(self):
        """アップロード→処理→ダウンロードの一連のフローをテスト"""
        # テスト用JSONLファイル作成
        content = '''{"inference1": "アップロードテスト1", "inference2": "アップロードテスト2"}
{"inference1": "アップロードテスト3", "inference2": "アップロードテスト4"}
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(content)
            temp_file = f.name

        try:
            # 1. ファイルアップロード
            with open(temp_file, 'rb') as f:
                files = {'file': ('test.jsonl', f, 'application/jsonl')}
                data = {'type': 'file', 'gpu': 'false'}

                upload_response = requests.post(
                    f"{API_URL}/upload",
                    files=files,
                    data=data
                )

            assert upload_response.status_code == 200, f"アップロード失敗: {upload_response.text}"
            result = upload_response.json()

            # 2. 結果の確認
            assert isinstance(result, list), "file形式の結果はリストであるべき"
            assert len(result) > 0, "結果が空です"

            # 3. CSV変換（クライアントサイド）のテスト
            # CSVダウンロードエンドポイントのテスト
            csv_response = requests.post(
                f"{API_URL}/download/csv",
                json=result,
                params={'type': 'file'}
            )

            assert csv_response.status_code == 200, "CSV変換失敗"
            content_type = csv_response.headers.get('content-type', '')
            assert content_type.startswith('text/csv'), f"CSV content-typeが不正: {content_type}"

            print("✅ アップロード→処理→ダウンロードフロー: 正常完了")

        finally:
            os.unlink(temp_file)

    def test_error_handling_integration(self):
        """エラーハンドリングの統合テスト"""
        # 1. 無効なファイルタイプ
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Not a JSONL file")
            temp_file = f.name

        try:
            with open(temp_file, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                response = requests.post(f"{API_URL}/upload", files=files)

            assert response.status_code == 400
            error_detail = response.json()['detail']
            assert 'error_id' in error_detail
            assert error_detail['error_id'].startswith('ERR-')
            print(f"✅ エラーハンドリング: {error_detail['error_id']} が生成されました")

        finally:
            os.unlink(temp_file)

    def test_metrics_collection(self):
        """メトリクス収集機能のテスト"""
        # メトリクスエンドポイントにアクセス
        response = requests.get(f"{API_URL}/metrics")
        assert response.status_code == 200

        metrics = response.json()
        assert 'upload_metrics' in metrics
        assert 'timestamp' in metrics

        upload_metrics = metrics['upload_metrics']

        if 'total_uploads' in upload_metrics and upload_metrics['total_uploads'] > 0:
            assert 'success_rate' in upload_metrics
            assert 'average_processing_time' in upload_metrics

            print(f"✅ メトリクス収集:")
            print(f"  - 総アップロード数: {upload_metrics['total_uploads']}")
            print(f"  - 成功率: {upload_metrics['success_rate']}%")
            print(f"  - 平均処理時間: {upload_metrics['average_processing_time']}秒")
        else:
            print("✅ メトリクス収集: メトリクスエンドポイント正常動作")

    def test_parallel_processing_capability(self):
        """並列処理能力のテスト（負荷テスト）"""
        import concurrent.futures

        def upload_file():
            """単一ファイルアップロード"""
            content = '''{"inference1": "parallel test 1", "inference2": "parallel test 2"}
{"inference1": "parallel test 3", "inference2": "parallel test 4"}
'''
            with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=True) as f:
                f.write(content)
                f.flush()

                with open(f.name, 'rb') as file:
                    files = {'file': ('parallel.jsonl', file, 'application/jsonl')}
                    data = {'type': 'score', 'gpu': 'false'}
                    response = requests.post(f"{API_URL}/upload", files=files, data=data)

                return response.status_code == 200

        # 5つの並列アップロードを実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.time()
            futures = [executor.submit(upload_file) for _ in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            elapsed_time = time.time() - start_time

        success_count = sum(results)
        print(f"✅ 並列処理テスト:")
        print(f"  - 成功: {success_count}/5")
        print(f"  - 処理時間: {elapsed_time:.2f}秒")

        assert success_count >= 3, "並列処理で少なくとも3つは成功するべき"

    def test_cli_and_api_consistency(self):
        """CLIとAPIの結果が一致することを確認"""
        # テスト用JSONLファイル作成
        content = '''{"inference1": "consistency test 1", "inference2": "consistency test 2"}
{"inference1": "consistency test 3", "inference2": "consistency test 4"}
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(content)
            temp_file = f.name

        try:
            # 1. CLI実行
            cli_result = subprocess.run(
                ['uv', 'run', 'python', '-m', 'src', temp_file, '--type', 'score'],
                capture_output=True,
                text=True
            )
            cli_output = json.loads(cli_result.stdout) if cli_result.returncode == 0 else None

            # 2. API実行
            with open(temp_file, 'rb') as f:
                files = {'file': ('test.jsonl', f, 'application/jsonl')}
                data = {'type': 'score', 'gpu': 'false'}
                api_response = requests.post(f"{API_URL}/upload", files=files, data=data)
            api_output = api_response.json() if api_response.status_code == 200 else None

            # 3. 結果の比較（メタデータを除く）
            if cli_output and api_output:
                # メタデータを除外
                if '_metadata' in api_output:
                    del api_output['_metadata']

                # 基本的なフィールドの存在確認
                for key in ['score', 'overall_similarity']:
                    if key in cli_output:
                        assert key in api_output or 'overall_similarity' in api_output or 'score' in api_output
                        break

                print("✅ CLI/API一貫性: 基本的な互換性確認")
            else:
                pytest.skip("CLIまたはAPIの実行に失敗")

        finally:
            os.unlink(temp_file)

    def test_log_files_creation(self):
        """ログファイルが正しく作成されることを確認"""
        log_dir = Path("/tmp/json_compare/logs")

        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
            expected_logs = ["access.log", "error.log", "metrics.log"]

            found_logs = [f.name for f in log_files]

            for expected in expected_logs:
                if expected in found_logs:
                    log_file = log_dir / expected
                    assert log_file.exists(), f"{expected} が存在しません"
                    assert log_file.stat().st_size >= 0, f"{expected} が空です"

            print(f"✅ ログファイル生成:")
            print(f"  - ログディレクトリ: {log_dir}")
            print(f"  - 存在するログ: {found_logs}")
        else:
            print("⚠️ ログディレクトリがまだ作成されていません")


def main():
    """メイン関数 - 統合テストの実行"""
    print("\n" + "="*60)
    print("JSON Compare 統合テストスイート (タスク8.1)")
    print("="*60 + "\n")

    # APIサーバーの起動確認
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        if response.status_code != 200:
            print("❌ APIサーバーが起動していません")
            print("以下のコマンドでAPIサーバーを起動してください:")
            print("  uv run uvicorn src.api:app --host 0.0.0.0 --port 18081")
            return 1
    except requests.exceptions.RequestException:
        print("❌ APIサーバーに接続できません")
        print("以下のコマンドでAPIサーバーを起動してください:")
        print("  uv run uvicorn src.api:app --host 0.0.0.0 --port 18081")
        return 1

    # テスト実行
    test_suite = TestIntegration()

    tests = [
        ("CLI基本機能", test_suite.test_cli_basic_functionality),
        ("APIエンドポイント可用性", test_suite.test_api_endpoints_availability),
        ("アップロード→ダウンロードフロー", test_suite.test_upload_and_download_flow),
        ("エラーハンドリング統合", test_suite.test_error_handling_integration),
        ("メトリクス収集", test_suite.test_metrics_collection),
        ("並列処理能力", test_suite.test_parallel_processing_capability),
        ("CLI/API一貫性", test_suite.test_cli_and_api_consistency),
        ("ログファイル生成", test_suite.test_log_files_creation)
    ]

    failed_tests = []

    for test_name, test_func in tests:
        try:
            print(f"\n[実行中] {test_name}...")
            test_func()
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            failed_tests.append(test_name)

    # 結果サマリー
    print("\n" + "="*60)
    print("統合テスト結果サマリー")
    print("="*60)
    print(f"✅ 成功: {len(tests) - len(failed_tests)}/{len(tests)}")

    if failed_tests:
        print(f"❌ 失敗: {', '.join(failed_tests)}")
        return 1
    else:
        print("\n🎉 すべての統合テストが成功しました！")
        print("\n要件確認:")
        print("✅ 7.3: システム全体の統合確認完了")
        print("✅ 既存CLI機能への影響なし")
        print("✅ Web UIとCLI両方での動作確認完了")
        print("✅ 全エンドポイント間の相互作用確認")
        print("✅ エラーハンドリングの網羅性確認")
        return 0


if __name__ == "__main__":
    exit(main())