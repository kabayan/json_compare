"""テストデータ管理システム

JSONL テストデータ生成、一時ファイル管理、フィクスチャデータローダーの実装
Requirements: 3.1, 3.2, 3.3 - テストデータ管理、一時ファイル管理、フィクスチャ管理
"""

import json
import tempfile
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union


class TestDataManagerError(Exception):
    """テストデータ管理システム専用エラークラス

    Attributes:
        original_error: 元の例外オブジェクト（存在する場合）
    """

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class TestDataManager:
    """テストデータ管理システム

    JSONL テストデータ生成、一時ファイル管理、フィクスチャデータローダーを提供します。

    Attributes:
        DEFAULT_FIXTURES_DIR: デフォルトのフィクスチャディレクトリパス
        FIXTURE_FILE_EXTENSION: フィクスチャファイルの拡張子
        JSONL_FILE_EXTENSION: JSONLファイルの拡張子
        _temp_files: 作成された一時ファイルのパスを記録するリスト
        _fixtures_dir: フィクスチャファイルのディレクトリパス
        _logger: ロガーインスタンス
    """

    # クラス定数
    DEFAULT_FIXTURES_DIR: str = "tests/fixtures"
    FIXTURE_FILE_EXTENSION: str = ".json"
    JSONL_FILE_EXTENSION: str = ".jsonl"

    def __init__(self, fixtures_dir: Optional[Union[str, Path]] = None) -> None:
        """初期化

        Args:
            fixtures_dir: フィクスチャファイルのディレクトリパス
                        （デフォルト: tests/fixtures）
        """
        self._temp_files: List[str] = []
        self._fixtures_dir: Path = Path(fixtures_dir or self.DEFAULT_FIXTURES_DIR)
        self._logger: logging.Logger = logging.getLogger(__name__)

    def generate_jsonl_file(self, records: List[Dict[str, Any]]) -> str:
        """JSONLファイルを生成する

        Args:
            records: 出力するレコードのリスト

        Returns:
            生成されたJSONLファイルのパス

        Raises:
            TestDataManagerError: ファイル生成に失敗した場合
        """
        try:
            # 一時ファイルを作成
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=self.JSONL_FILE_EXTENSION,
                prefix='test_data_'
            )

            # ファイルハンドルを閉じて、パスのみ使用
            os.close(temp_fd)

            # JSONLファイルを書き込み
            self._write_jsonl_records(temp_path, records)

            # 作成されたファイルを記録
            self._add_temp_file(temp_path)
            self._logger.info(f"Generated JSONL file: {temp_path} with {len(records)} records")

            return temp_path

        except Exception as e:
            raise TestDataManagerError(f"Failed to generate JSONL file: {str(e)}", e)

    def create_temp_file(self, content: str, extension: str) -> str:
        """一時ファイルを作成する

        Args:
            content: ファイルに書き込む内容
            extension: ファイル拡張子

        Returns:
            作成された一時ファイルのパス

        Raises:
            TestDataManagerError: ファイル作成に失敗した場合
        """
        try:
            # 一時ファイルを作成
            temp_fd, temp_path = tempfile.mkstemp(suffix=f'.{extension}', prefix='test_temp_')

            # ファイルハンドルを閉じて、パスのみ使用
            os.close(temp_fd)

            # ファイルに内容を書き込み
            self._write_file_content(temp_path, content)

            # 作成されたファイルを記録
            self._add_temp_file(temp_path)
            self._logger.info(f"Created temp file: {temp_path}")

            return temp_path

        except Exception as e:
            raise TestDataManagerError(f"Failed to create temp file: {str(e)}", e)

    def cleanup_temp_files(self) -> int:
        """一時ファイルをクリーンアップする

        Returns:
            削除されたファイルの数

        Note:
            削除に失敗したファイルがあってもエラーにはならず、削除できたファイル数を返します。
        """
        cleaned_count = 0

        for file_path in self._temp_files[:]:  # リストのコピーを作成してイテレート
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned_count += 1
                    self._logger.info(f"Cleaned up temp file: {file_path}")

                # 成功・失敗に関わらずリストから削除
                self._remove_temp_file_from_list(file_path)

            except Exception as e:
                self._logger.warning(f"Failed to clean up temp file {file_path}: {str(e)}")
                # 削除に失敗してもリストからは削除
                self._remove_temp_file_from_list(file_path)

        self._logger.info(f"Cleanup completed: {cleaned_count} files removed")
        return cleaned_count

    def get_fixture(self, name: str) -> Any:
        """フィクスチャデータを取得する

        Args:
            name: フィクスチャファイル名（拡張子なし）

        Returns:
            フィクスチャデータ（JSONオブジェクト）

        Raises:
            TestDataManagerError: フィクスチャファイルが見つからない、または読み込みに失敗した場合
        """
        fixture_path = self._fixtures_dir / f"{name}{self.FIXTURE_FILE_EXTENSION}"

        try:
            if not fixture_path.exists():
                raise TestDataManagerError(f"Fixture file not found: {fixture_path}")

            content = fixture_path.read_text(encoding='utf-8')
            fixture_data = json.loads(content)

            self._logger.info(f"Loaded fixture: {name}")
            return fixture_data

        except json.JSONDecodeError as e:
            raise TestDataManagerError(f"Invalid JSON in fixture file {fixture_path}: {str(e)}", e)
        except Exception as e:
            raise TestDataManagerError(f"Failed to load fixture {name}: {str(e)}", e)

    def get_temp_files_count(self) -> int:
        """現在管理している一時ファイルの数を取得する

        Returns:
            一時ファイルの数
        """
        return len(self._temp_files)

    def get_fixtures_dir(self) -> Path:
        """フィクスチャディレクトリのパスを取得する

        Returns:
            フィクスチャディレクトリのパス
        """
        return self._fixtures_dir

    # プライベートヘルパーメソッド

    def _write_jsonl_records(self, file_path: str, records: List[Dict[str, Any]]) -> None:
        """JSONLレコードをファイルに書き込む（内部メソッド）

        Args:
            file_path: 書き込み先ファイルパス
            records: 書き込むレコードのリスト

        Raises:
            IOError: ファイル書き込みに失敗した場合
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            for record in records:
                json.dump(record, f, ensure_ascii=False)
                f.write('\n')

    def _write_file_content(self, file_path: str, content: str) -> None:
        """ファイルに内容を書き込む（内部メソッド）

        Args:
            file_path: 書き込み先ファイルパス
            content: 書き込む内容

        Raises:
            IOError: ファイル書き込みに失敗した場合
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _add_temp_file(self, file_path: str) -> None:
        """一時ファイルリストに追加する（内部メソッド）

        Args:
            file_path: 追加するファイルパス
        """
        self._temp_files.append(file_path)

    def _remove_temp_file_from_list(self, file_path: str) -> None:
        """一時ファイルリストから削除する（内部メソッド）

        Args:
            file_path: 削除するファイルパス
        """
        if file_path in self._temp_files:
            self._temp_files.remove(file_path)