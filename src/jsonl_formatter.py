#!/usr/bin/env python3
"""
JSONLファイルフォーマット修正ユーティリティ
複数行にまたがるJSONオブジェクトを1行1オブジェクト形式に自動修正
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List
import shutil


class JSONLFormatter:
    """JSONLファイルのフォーマットを修正するクラス"""

    @staticmethod
    def check_format(file_path: str) -> bool:
        """
        JSONLファイルが正しいフォーマットか確認

        Args:
            file_path: チェックするファイルのパス

        Returns:
            正しいフォーマットの場合True
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():  # 空行はスキップ
                        try:
                            json.loads(line)
                        except json.JSONDecodeError:
                            return False
            return True
        except Exception:
            return False

    @staticmethod
    def parse_multiline_json(file_path: str) -> List[dict]:
        """
        複数行にまたがる可能性のあるJSONファイルをパース

        Args:
            file_path: 入力ファイルのパス

        Returns:
            JSONオブジェクトのリスト
        """
        json_objects = []
        current_obj = ""
        brace_count = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                current_obj += line

                # ブレースカウントで完全なJSONオブジェクトを検出
                brace_count += line.count('{') - line.count('}')

                if brace_count == 0 and current_obj.strip():
                    try:
                        # JSONオブジェクトとしてパース
                        obj = json.loads(current_obj)
                        json_objects.append(obj)
                        current_obj = ""
                    except json.JSONDecodeError:
                        # 複数の単一行JSONが混在している可能性
                        for single_line in current_obj.strip().split('\n'):
                            if single_line.strip():
                                try:
                                    obj = json.loads(single_line)
                                    json_objects.append(obj)
                                except:
                                    pass
                        current_obj = ""

        return json_objects

    @classmethod
    def fix_format(cls, file_path: str, in_place: bool = False) -> Tuple[bool, str]:
        """
        JSONLファイルのフォーマットを修正

        Args:
            file_path: 修正するファイルのパス
            in_place: 元のファイルを直接修正するか

        Returns:
            (成功/失敗, 修正後のファイルパス or エラーメッセージ)
        """
        try:
            input_file = Path(file_path)

            if not input_file.exists():
                return False, f"ファイルが存在しません: {file_path}"

            # すでに正しいフォーマットの場合はそのまま返す
            if cls.check_format(file_path):
                return True, file_path

            # JSONオブジェクトをパース
            json_objects = cls.parse_multiline_json(file_path)

            if not json_objects:
                return False, "有効なJSONオブジェクトが見つかりません"

            if in_place:
                # バックアップを作成
                backup_path = input_file.with_suffix('.jsonl.bak')
                shutil.copy2(file_path, backup_path)
                output_path = file_path
            else:
                # 一時ファイルに出力
                temp_fd, output_path = tempfile.mkstemp(suffix='.jsonl')
                os.close(temp_fd)

            # 1行ずつ書き込み
            with open(output_path, 'w', encoding='utf-8') as f:
                for obj in json_objects:
                    json_line = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
                    f.write(json_line + '\n')

            return True, output_path

        except Exception as e:
            return False, str(e)

    @classmethod
    def ensure_valid_format(cls, file_path: str) -> str:
        """
        JSONLファイルが正しいフォーマットであることを保証
        必要に応じて修正した一時ファイルを返す

        Args:
            file_path: 確認/修正するファイルのパス

        Returns:
            正しいフォーマットのファイルパス（元のファイルまたは修正後の一時ファイル）

        Raises:
            ValueError: ファイルの修正に失敗した場合
        """
        # すでに正しいフォーマットならそのまま返す
        if cls.check_format(file_path):
            return file_path

        # フォーマット修正が必要
        print(f"JSONLファイルのフォーマットを修正中: {os.path.basename(file_path)}")
        success, result = cls.fix_format(file_path, in_place=False)

        if not success:
            raise ValueError(f"JSONLファイルの修正に失敗: {result}")

        print(f"✅ フォーマット修正完了")
        return result


def auto_fix_jsonl_file(file_path: str) -> str:
    """
    JSONLファイルを自動的に修正して返す便利関数

    Args:
        file_path: 処理対象のJSONLファイルパス

    Returns:
        正しいフォーマットのファイルパス

    Raises:
        ValueError: ファイルの修正に失敗した場合
    """
    return JSONLFormatter.ensure_valid_format(file_path)