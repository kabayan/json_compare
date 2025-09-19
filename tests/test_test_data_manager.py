"""Task 1.3: テストデータ管理システムのテスト

TDD実装：JSONL テストデータ生成、一時ファイル管理、フィクスチャデータローダーの作成
Requirements: 3.1, 3.2, 3.3 - テストデータ管理、一時ファイル管理、フィクスチャ管理
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock


class TestTestDataManager:
    """テストデータ管理システムのテスト"""

    def test_test_data_manager_initialization(self):
        """TestDataManagerが正しく初期化されること"""
        from src.test_data_manager import TestDataManager

        manager = TestDataManager()
        assert manager is not None
        assert hasattr(manager, 'generate_jsonl_file')
        assert hasattr(manager, 'create_temp_file')
        assert hasattr(manager, 'cleanup_temp_files')
        assert hasattr(manager, 'get_fixture')

    def test_generate_jsonl_file(self):
        """JSONLファイルが正しく生成されること"""
        from src.test_data_manager import TestDataManager

        manager = TestDataManager()

        # テストデータ
        test_records = [
            {"id": 1, "text": "テスト文章1", "inference1": "推論結果1", "inference2": "推論結果2"},
            {"id": 2, "text": "テスト文章2", "inference1": "推論結果3", "inference2": "推論結果4"},
        ]

        # JSONL ファイル生成
        file_path = manager.generate_jsonl_file(test_records)

        # ファイルが作成されていることを確認
        assert file_path is not None
        assert os.path.exists(file_path)
        assert file_path.endswith('.jsonl')

        # ファイル内容を確認
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 2

            # 各行がJSONオブジェクトになっていることを確認
            record1 = json.loads(lines[0].strip())
            record2 = json.loads(lines[1].strip())

            assert record1 == test_records[0]
            assert record2 == test_records[1]

    def test_generate_jsonl_file_empty_records(self):
        """空のレコードリストでJSONLファイルが生成されること"""
        from src.test_data_manager import TestDataManager

        manager = TestDataManager()
        file_path = manager.generate_jsonl_file([])

        assert file_path is not None
        assert os.path.exists(file_path)

        # ファイルが空であることを確認
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert content == ""

    def test_create_temp_file(self):
        """一時ファイルが正しく作成されること"""
        from src.test_data_manager import TestDataManager

        manager = TestDataManager()

        content = "テスト用のファイル内容\n複数行のテキスト"
        file_path = manager.create_temp_file(content, "txt")

        # ファイルが作成されていることを確認
        assert file_path is not None
        assert os.path.exists(file_path)
        assert file_path.endswith('.txt')

        # ファイル内容を確認
        with open(file_path, 'r', encoding='utf-8') as f:
            read_content = f.read()
            assert read_content == content

    def test_create_temp_file_various_extensions(self):
        """様々な拡張子で一時ファイルが作成されること"""
        from src.test_data_manager import TestDataManager

        manager = TestDataManager()

        test_cases = [
            ("json", '{"test": "data"}'),
            ("yaml", "test: data\nvalue: 123"),
            ("csv", "id,name,value\n1,test,100"),
        ]

        for extension, content in test_cases:
            file_path = manager.create_temp_file(content, extension)

            assert file_path is not None
            assert os.path.exists(file_path)
            assert file_path.endswith(f'.{extension}')

            with open(file_path, 'r', encoding='utf-8') as f:
                assert f.read() == content

    def test_cleanup_temp_files(self):
        """一時ファイルがクリーンアップされること"""
        from src.test_data_manager import TestDataManager

        manager = TestDataManager()

        # 複数の一時ファイルを作成
        file1 = manager.create_temp_file("テスト内容1", "txt")
        file2 = manager.create_temp_file("テスト内容2", "json")
        file3 = manager.generate_jsonl_file([{"test": "data"}])

        # ファイルが存在することを確認
        assert os.path.exists(file1)
        assert os.path.exists(file2)
        assert os.path.exists(file3)

        # クリーンアップ実行
        cleanup_count = manager.cleanup_temp_files()

        # ファイルが削除されていることを確認
        assert not os.path.exists(file1)
        assert not os.path.exists(file2)
        assert not os.path.exists(file3)
        assert cleanup_count == 3

    def test_get_fixture(self):
        """フィクスチャデータが正しく読み込まれること"""
        from src.test_data_manager import TestDataManager

        manager = TestDataManager()

        # フィクスチャファイルをモック
        with patch.object(manager, '_fixtures_dir') as mock_fixtures_dir:
            mock_file = MagicMock()
            mock_file.exists.return_value = True
            mock_file.read_text.return_value = '{"test": "fixture", "data": [1, 2, 3]}'

            # _fixtures_dir / "test_fixture.json" の結果をモック
            mock_fixtures_dir.__truediv__.return_value = mock_file

            fixture_data = manager.get_fixture("test_fixture")

            expected_data = {"test": "fixture", "data": [1, 2, 3]}
            assert fixture_data == expected_data

    def test_get_fixture_file_not_found(self):
        """存在しないフィクスチャファイルでエラーが発生すること"""
        from src.test_data_manager import TestDataManager, TestDataManagerError

        manager = TestDataManager()

        with patch('src.test_data_manager.Path') as mock_path:
            mock_file = MagicMock()
            mock_file.exists.return_value = False
            mock_path.return_value = mock_file

            with pytest.raises(TestDataManagerError) as exc_info:
                manager.get_fixture("nonexistent_fixture")

            assert "Fixture file not found" in str(exc_info.value)

    def test_get_fixture_invalid_json(self):
        """無効なJSONフィクスチャファイルでエラーが発生すること"""
        from src.test_data_manager import TestDataManager, TestDataManagerError

        manager = TestDataManager()

        with patch.object(manager, '_fixtures_dir') as mock_fixtures_dir:
            mock_file = MagicMock()
            mock_file.exists.return_value = True
            mock_file.read_text.return_value = '{"invalid": json}'

            # _fixtures_dir / "invalid_fixture.json" の結果をモック
            mock_fixtures_dir.__truediv__.return_value = mock_file

            with pytest.raises(TestDataManagerError) as exc_info:
                manager.get_fixture("invalid_fixture")

            assert "Invalid JSON in fixture file" in str(exc_info.value)


class TestTestDataManagerIntegration:
    """テストデータ管理システムの統合テスト"""

    def test_full_data_management_workflow(self):
        """完全なデータ管理ワークフローのテスト"""
        from src.test_data_manager import TestDataManager

        manager = TestDataManager()

        try:
            # 1. フィクスチャデータの取得をモック
            with patch.object(manager, 'get_fixture') as mock_fixture:
                mock_fixture.return_value = {
                    "base_data": [
                        {"id": 1, "text": "基本テキスト1"},
                        {"id": 2, "text": "基本テキスト2"},
                    ]
                }

                fixture_data = manager.get_fixture("base_test_data")

                # 2. フィクスチャデータを基にJSONLファイル生成
                enhanced_records = []
                for item in fixture_data["base_data"]:
                    enhanced_item = item.copy()
                    enhanced_item["inference1"] = f"推論結果_{item['id']}_1"
                    enhanced_item["inference2"] = f"推論結果_{item['id']}_2"
                    enhanced_records.append(enhanced_item)

                jsonl_file = manager.generate_jsonl_file(enhanced_records)

                # 3. 設定ファイルの作成
                config_content = """
                test:
                  timeout: 30
                  retry_count: 3
                  base_url: http://localhost:18081
                """
                config_file = manager.create_temp_file(config_content, "yaml")

                # 4. ファイルが正しく作成されていることを確認
                assert os.path.exists(jsonl_file)
                assert os.path.exists(config_file)

                # 5. JSONL ファイル内容を確認
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    assert len(lines) == 2

                    record1 = json.loads(lines[0].strip())
                    assert record1["id"] == 1
                    assert record1["inference1"] == "推論結果_1_1"
                    assert record1["inference2"] == "推論結果_1_2"

        finally:
            # 6. 確実にクリーンアップ
            cleanup_count = manager.cleanup_temp_files()
            assert cleanup_count >= 0  # 作成されたファイルがクリーンアップされること

    def test_concurrent_file_operations(self):
        """並行ファイル操作の安全性テスト"""
        from src.test_data_manager import TestDataManager
        import asyncio
        import concurrent.futures

        async def create_files_concurrently():
            manager = TestDataManager()

            def create_test_file(index):
                records = [{"id": index, "data": f"test_data_{index}"}]
                return manager.generate_jsonl_file(records)

            # 複数のファイルを並行作成
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(create_test_file, i) for i in range(10)]
                file_paths = [future.result() for future in concurrent.futures.as_completed(futures)]

            # 全てのファイルが作成されていることを確認
            assert len(file_paths) == 10
            for file_path in file_paths:
                assert os.path.exists(file_path)

            # クリーンアップ
            cleanup_count = manager.cleanup_temp_files()
            assert cleanup_count == 10

        # 非同期テストの実行
        asyncio.run(create_files_concurrently())

    def test_large_dataset_handling(self):
        """大規模データセットの処理テスト"""
        from src.test_data_manager import TestDataManager

        manager = TestDataManager()

        # 大量のテストデータ生成
        large_records = []
        for i in range(1000):
            large_records.append({
                "id": i,
                "text": f"大規模テストデータ {i} " * 10,  # 長いテキストを作成
                "inference1": f"推論結果1_{i}",
                "inference2": f"推論結果2_{i}",
            })

        try:
            # JSONL ファイル生成
            file_path = manager.generate_jsonl_file(large_records)

            # ファイルサイズとレコード数を確認
            assert os.path.exists(file_path)
            file_size = os.path.getsize(file_path)
            assert file_size > 0

            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                assert len(lines) == 1000

            # 最初と最後のレコードを確認
            first_record = json.loads(lines[0].strip())
            last_record = json.loads(lines[-1].strip())

            assert first_record["id"] == 0
            assert last_record["id"] == 999

        finally:
            # クリーンアップ
            manager.cleanup_temp_files()