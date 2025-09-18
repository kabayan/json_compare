"""
DualFileExtractor: 2つのJSONLファイルから指定列を抽出して比較する機能
"""

import json
import os
import tempfile
from typing import Dict, Any, List, Optional
from pathlib import Path

from .logger import SystemLogger
from .error_handler import ErrorHandler


class DualFileExtractor:
    """2つのJSONLファイルから指定列を抽出し、比較を実行するクラス"""

    def __init__(self):
        """初期化"""
        self.logger = SystemLogger()
        self.error_handler = ErrorHandler()
        self.temp_files = []  # クリーンアップ用の一時ファイルリスト

    def compare_dual_files(
        self,
        file1_path: str,
        file2_path: str,
        column_name: str = "inference",
        output_type: str = "score",
        use_gpu: bool = False
    ) -> Dict[str, Any]:
        """
        2つのJSONLファイルから指定列を抽出して比較

        Args:
            file1_path: 1つ目のJSONLファイルパス
            file2_path: 2つ目のJSONLファイルパス
            column_name: 抽出する列名（デフォルト: inference）
            output_type: 出力タイプ（score/file）
            use_gpu: GPU使用フラグ

        Returns:
            比較結果の辞書
        """
        try:
            # ファイル検証
            self._validate_files(file1_path, file2_path, column_name)

            # 指定列の抽出
            print(f"ファイル1から'{column_name}'列を抽出中...")
            column1_data = self._extract_column(file1_path, column_name)

            print(f"ファイル2から'{column_name}'列を抽出中...")
            column2_data = self._extract_column(file2_path, column_name)

            # 行数の確認
            len1, len2 = len(column1_data), len(column2_data)
            if len1 != len2:
                print(f"警告: ファイルの行数が異なります（{len1}行 vs {len2}行）。短い方に合わせます。")
                min_len = min(len1, len2)
                column1_data = column1_data[:min_len]
                column2_data = column2_data[:min_len]

            # 一時ファイルの作成
            print("一時ファイルを作成中...")
            temp_file_path = self._create_temp_file(column1_data, column2_data)

            # 既存の比較機能を実行
            print("比較処理を実行中...")
            # __main__モジュールから関数をインポート
            from .__main__ import process_jsonl_file
            result = process_jsonl_file(temp_file_path, output_type)

            # メタデータの追加（scoreタイプの場合のみ）
            if isinstance(result, dict):
                result['_metadata'] = {
                    'source_files': {
                        'file1': os.path.basename(file1_path),
                        'file2': os.path.basename(file2_path)
                    },
                    'column_compared': column_name,
                    'rows_compared': min(len1, len2),
                    'gpu_used': use_gpu
                }

            # ログ記録
            print(f"✅ 2ファイル比較完了 - 列: {column_name}, 行数: {min(len1, len2)}")

            return result

        except Exception as e:
            error_id = self.error_handler.generate_error_id()
            self.logger.log_error(
                error_id,
                'dual_file_comparison_error',
                str(e)
            )
            raise Exception(f"比較処理に失敗しました（エラーID: {error_id}）: {str(e)}")

        finally:
            # 一時ファイルのクリーンアップ
            self._cleanup_temp_files()

    def _validate_files(self, file1_path: str, file2_path: str, column_name: str):
        """
        ファイルと列の存在を検証

        Args:
            file1_path: 1つ目のファイルパス
            file2_path: 2つ目のファイルパス
            column_name: 検証する列名
        """
        # ファイル存在確認
        if not os.path.exists(file1_path):
            raise FileNotFoundError(f"ファイル1が見つかりません: {file1_path}")

        if not os.path.exists(file2_path):
            raise FileNotFoundError(f"ファイル2が見つかりません: {file2_path}")

        # ファイル形式と列の確認
        for file_path, file_num in [(file1_path, 1), (file2_path, 2)]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if not first_line:
                        raise ValueError(f"ファイル{file_num}が空です")

                    # JSON形式の確認
                    try:
                        data = json.loads(first_line)
                    except json.JSONDecodeError:
                        # json-repairで修復を試みる
                        repaired = self.error_handler.validate_and_repair_jsonl(first_line)
                        if repaired:
                            data = json.loads(repaired.split('\n')[0])
                        else:
                            raise ValueError(f"ファイル{file_num}がJSONL形式ではありません")

                    # 列の存在確認
                    if column_name not in data:
                        available_columns = list(data.keys())
                        raise ValueError(
                            f"ファイル{file_num}に'{column_name}'列が存在しません。"
                            f"利用可能な列: {', '.join(available_columns)}"
                        )

            except Exception as e:
                if isinstance(e, (FileNotFoundError, ValueError)):
                    raise
                raise ValueError(f"ファイル{file_num}の読み込みエラー: {str(e)}")

    def _extract_column(self, file_path: str, column_name: str) -> List[str]:
        """
        JSONLファイルから指定列を抽出

        Args:
            file_path: JSONLファイルパス
            column_name: 抽出する列名

        Returns:
            抽出した値のリスト
        """
        extracted_data = []

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    # json-repairで修復を試みる
                    repaired = self.error_handler.validate_and_repair_jsonl(line)
                    if repaired:
                        data = json.loads(repaired.split('\n')[0])
                    else:
                        print(f"警告: 行{line_num}のJSON解析に失敗しました。スキップします。")
                        continue

                # 列の値を取得
                value = data.get(column_name, "")

                # 値が辞書やリストの場合はJSON文字列に変換
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                elif not isinstance(value, str):
                    value = str(value)

                extracted_data.append(value)

        return extracted_data

    def _create_temp_file(self, data1: List[str], data2: List[str]) -> str:
        """
        2つのデータリストから一時ファイルを作成

        Args:
            data1: 1つ目のデータリスト
            data2: 2つ目のデータリスト

        Returns:
            作成した一時ファイルのパス
        """
        # 一時ファイルの作成（削除は手動）
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.jsonl',
            delete=False,
            encoding='utf-8'
        ) as tmp:
            temp_path = tmp.name
            self.temp_files.append(temp_path)  # クリーンアップリストに追加

            # データをinference1/inference2として書き込み
            for val1, val2 in zip(data1, data2):
                line = {
                    "inference1": val1,
                    "inference2": val2
                }
                tmp.write(json.dumps(line, ensure_ascii=False) + '\n')

        print(f"一時ファイルを作成しました: {temp_path}")
        return temp_path

    def _cleanup_temp_files(self):
        """作成した一時ファイルをすべて削除"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"一時ファイルを削除しました: {temp_file}")
            except Exception as e:
                print(f"警告: 一時ファイル削除失敗: {temp_file} - {str(e)}")

        self.temp_files.clear()