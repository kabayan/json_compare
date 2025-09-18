"""
DualFileExtractorのテスト
"""

import os
import sys
import json
import tempfile
import pytest
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dual_file_extractor import DualFileExtractor


class TestDualFileExtractor:
    """DualFileExtractorのテストクラス"""

    @pytest.fixture
    def sample_file1(self):
        """テスト用のサンプルファイル1を作成"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            data = [
                {"id": 1, "inference": "これは最初のテキストです", "score": 0.8},
                {"id": 2, "inference": "二番目のテキスト", "score": 0.9},
                {"id": 3, "inference": "三番目のテキストサンプル", "score": 0.7}
            ]
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            return f.name

    @pytest.fixture
    def sample_file2(self):
        """テスト用のサンプルファイル2を作成"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            data = [
                {"id": 1, "inference": "これは最初のテキストです", "score": 0.85},
                {"id": 2, "inference": "二番目のテキスト", "score": 0.88},
                {"id": 3, "inference": "異なる三番目のテキスト", "score": 0.75}
            ]
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            return f.name

    @pytest.fixture
    def sample_file_custom_column(self):
        """カスタム列名のサンプルファイル"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            data = [
                {"id": 1, "custom_text": "カスタム列のテキスト1"},
                {"id": 2, "custom_text": "カスタム列のテキスト2"}
            ]
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            return f.name

    @pytest.fixture
    def extractor(self):
        """DualFileExtractorのインスタンスを作成"""
        return DualFileExtractor()

    def test_compare_dual_files_default_column(self, extractor, sample_file1, sample_file2):
        """デフォルト列（inference）での比較テスト"""
        try:
            result = extractor.compare_dual_files(
                sample_file1,
                sample_file2,
                output_type="score"
            )

            # 結果の検証
            assert 'score' in result
            assert 'meaning' in result
            assert 'json' in result
            assert '_metadata' in result
            assert result['_metadata']['column_compared'] == 'inference'
            assert result['_metadata']['rows_compared'] == 3
            assert result['total_lines'] == 3

        finally:
            # クリーンアップ
            os.unlink(sample_file1)
            os.unlink(sample_file2)

    def test_compare_dual_files_custom_column(self, extractor, sample_file_custom_column):
        """カスタム列での比較テスト"""
        try:
            # 2つ目のファイルも同じ構造で作成
            with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
                data = [
                    {"id": 1, "custom_text": "カスタム列のテキスト1"},
                    {"id": 2, "custom_text": "異なるカスタム列のテキスト"}
                ]
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
                file2_name = f.name

            result = extractor.compare_dual_files(
                sample_file_custom_column,
                file2_name,
                column_name="custom_text",
                output_type="score"
            )

            # 結果の検証
            assert '_metadata' in result
            assert result['_metadata']['column_compared'] == 'custom_text'
            assert result['_metadata']['rows_compared'] == 2

        finally:
            # クリーンアップ
            os.unlink(sample_file_custom_column)
            if 'file2_name' in locals():
                os.unlink(file2_name)

    def test_compare_dual_files_file_type(self, extractor, sample_file1, sample_file2):
        """fileタイプでの詳細結果取得テスト"""
        try:
            result = extractor.compare_dual_files(
                sample_file1,
                sample_file2,
                output_type="file"
            )

            # 結果の検証
            assert isinstance(result, list)
            assert len(result) == 3
            for item in result:
                assert 'inference1' in item
                assert 'inference2' in item
                assert 'similarity_score' in item
                assert 'similarity_details' in item

        finally:
            # クリーンアップ
            os.unlink(sample_file1)
            os.unlink(sample_file2)

    def test_file_not_found_error(self, extractor):
        """ファイルが見つからない場合のエラーテスト"""
        with pytest.raises(FileNotFoundError, match="ファイル1が見つかりません"):
            extractor.compare_dual_files(
                "nonexistent_file1.jsonl",
                "nonexistent_file2.jsonl"
            )

    def test_missing_column_error(self, extractor, sample_file1, sample_file2):
        """存在しない列を指定した場合のエラーテスト"""
        try:
            with pytest.raises(ValueError, match="列が存在しません"):
                extractor.compare_dual_files(
                    sample_file1,
                    sample_file2,
                    column_name="nonexistent_column"
                )
        finally:
            # クリーンアップ
            os.unlink(sample_file1)
            os.unlink(sample_file2)

    def test_different_row_counts_warning(self, extractor, sample_file1):
        """行数が異なるファイルの処理テスト"""
        # 行数が少ないファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            data = [
                {"id": 1, "inference": "テキスト1"},
                {"id": 2, "inference": "テキスト2"}
            ]
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            file2_name = f.name

        try:
            result = extractor.compare_dual_files(
                sample_file1,  # 3行
                file2_name,     # 2行
                output_type="score"
            )

            # 短い方に合わせた行数になることを確認
            assert result['_metadata']['rows_compared'] == 2
            assert result['total_lines'] == 2

        finally:
            # クリーンアップ
            os.unlink(sample_file1)
            os.unlink(file2_name)

    def test_temp_file_cleanup(self, extractor, sample_file1, sample_file2):
        """一時ファイルが適切にクリーンアップされることをテスト"""
        try:
            # 比較実行前の一時ファイル数を取得
            temp_dir = tempfile.gettempdir()
            before_files = set(os.listdir(temp_dir))

            # 比較実行
            result = extractor.compare_dual_files(
                sample_file1,
                sample_file2,
                output_type="score"
            )

            # 比較実行後の一時ファイル数を取得
            after_files = set(os.listdir(temp_dir))

            # 新しく残った一時ファイルがないことを確認
            new_files = after_files - before_files
            temp_files_remaining = [f for f in new_files if 'json_compare_' in f]
            assert len(temp_files_remaining) == 0, f"一時ファイルが残っています: {temp_files_remaining}"

        finally:
            # クリーンアップ
            os.unlink(sample_file1)
            os.unlink(sample_file2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])