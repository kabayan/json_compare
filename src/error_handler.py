#!/usr/bin/env python3
"""エラーハンドリングとリカバリユーティリティ"""

import json
import logging
import traceback
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path


class ErrorHandler:
    """統合的なエラーハンドリングとリカバリ機能"""

    @staticmethod
    def generate_error_id() -> str:
        """追跡可能なエラーIDを生成"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4()).split("-")[0]
        return f"ERR-{timestamp}-{unique_id}"

    @staticmethod
    def validate_jsonl_line(line: str, line_number: int) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        JSONL行を検証し、可能な場合は修復する

        Args:
            line: 検証する行
            line_number: 行番号

        Returns:
            (成功フラグ, 修復済みデータまたはNone, エラーメッセージまたはNone)
        """
        if not line.strip():
            return False, None, f"行{line_number}: 空の行"

        try:
            data = json.loads(line)

            # inference1/inference2フィールドの存在確認
            missing_fields = []
            if "inference1" not in data:
                missing_fields.append("inference1")
            if "inference2" not in data:
                missing_fields.append("inference2")

            if missing_fields:
                error_msg = f"行{line_number}: 必須フィールドが欠落: {', '.join(missing_fields)}"

                # 自動修復を試みる
                if "inference1" not in data:
                    data["inference1"] = ""
                if "inference2" not in data:
                    data["inference2"] = ""

                return True, data, f"{error_msg} (自動修復済み)"

            return True, data, None

        except json.JSONDecodeError as e:
            # JSON修復を試みる
            repaired_line = line.strip()

            # よくあるエラーパターンの修正
            if repaired_line.endswith(","):
                repaired_line = repaired_line[:-1]

            # シングルクォートをダブルクォートに置換
            if "'" in repaired_line:
                try:
                    # Python literalとして評価し、JSONに変換
                    import ast
                    data = ast.literal_eval(repaired_line)
                    if isinstance(data, dict):
                        return True, data, f"行{line_number}: シングルクォートを修正"
                except:
                    pass

            return False, None, f"行{line_number}: JSONパースエラー - {str(e)}"

    @staticmethod
    def validate_and_repair_jsonl(content: str, max_errors: int = 10) -> Tuple[List[Dict], List[str], bool]:
        """
        JSONLコンテンツ全体を検証し、可能な限り修復する

        Args:
            content: JSONLコンテンツ
            max_errors: 許容する最大エラー数

        Returns:
            (修復済みデータのリスト, エラーメッセージのリスト, 成功フラグ)
        """
        lines = content.strip().split('\n')
        repaired_data = []
        error_messages = []
        critical_errors = 0

        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue

            success, data, error_msg = ErrorHandler.validate_jsonl_line(line, i)

            if success and data:
                repaired_data.append(data)
                if error_msg:  # 修復済みの警告
                    error_messages.append(f"⚠️ {error_msg}")
            else:
                critical_errors += 1
                error_messages.append(f"❌ {error_msg}")

                if critical_errors >= max_errors:
                    error_messages.append(f"エラーが{max_errors}件を超えたため処理を中止")
                    return repaired_data, error_messages, False

        # 最低限のデータが必要
        if len(repaired_data) == 0:
            error_messages.append("有効なデータが1件もありません")
            return repaired_data, error_messages, False

        return repaired_data, error_messages, True

    @staticmethod
    def format_user_error(error_id: str, error_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        ユーザー向けのエラーメッセージを生成

        Args:
            error_id: エラーID
            error_type: エラータイプ
            details: エラーの詳細情報

        Returns:
            ユーザー向けエラーレスポンス
        """
        error_messages = {
            "file_validation": "ファイルの形式に問題があります",
            "processing_timeout": "処理がタイムアウトしました",
            "insufficient_memory": "メモリ不足により処理できません",
            "insufficient_storage": "ディスク容量が不足しています",
            "server_overload": "サーバーが混雑しています",
            "internal_error": "内部エラーが発生しました"
        }

        suggestions = {
            "file_validation": [
                "ファイルがJSONL形式であることを確認してください",
                "各行が有効なJSONオブジェクトであることを確認してください",
                "inference1とinference2フィールドが存在することを確認してください"
            ],
            "processing_timeout": [
                "より小さいファイルで再試行してください",
                "ファイルを分割して処理してください",
                "CPUモードで再試行してください（GPUが選択されている場合）"
            ],
            "insufficient_memory": [
                "より小さいファイルで再試行してください",
                "他のアプリケーションを終了してから再試行してください"
            ],
            "insufficient_storage": [
                "不要なファイルを削除してから再試行してください",
                "システム管理者に連絡してください"
            ],
            "server_overload": [
                "しばらく待ってから再試行してください",
                "混雑時を避けて再試行してください"
            ],
            "internal_error": [
                "もう一度お試しください",
                "問題が続く場合はシステム管理者に連絡してください",
                f"エラーID: {error_id} を報告してください"
            ]
        }

        return {
            "error_id": error_id,
            "error": error_messages.get(error_type, "エラーが発生しました"),
            "details": details,
            "suggestions": suggestions.get(error_type, ["もう一度お試しください"]),
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def check_system_resources() -> Tuple[bool, Optional[str]]:
        """
        システムリソースをチェック

        Returns:
            (正常フラグ, エラーメッセージまたはNone)
        """
        import psutil

        # メモリチェック（利用可能メモリが500MB未満の場合エラー）
        memory = psutil.virtual_memory()
        if memory.available < 500 * 1024 * 1024:  # 500MB
            return False, f"メモリ不足: 利用可能 {memory.available / (1024*1024):.0f}MB"

        # ディスク容量チェック（利用可能容量が100MB未満の場合エラー）
        disk = psutil.disk_usage('/')
        if disk.free < 100 * 1024 * 1024:  # 100MB
            return False, f"ディスク容量不足: 利用可能 {disk.free / (1024*1024):.0f}MB"

        # CPU使用率チェック（90%以上の場合警告）
        cpu_percent = psutil.cpu_percent(interval=0.1)
        if cpu_percent > 90:
            return True, f"CPU高負荷: {cpu_percent:.0f}%"

        return True, None


class JsonRepair:
    """JSON修復ユーティリティ"""

    @staticmethod
    def repair_json_string(json_str: str) -> Optional[Dict]:
        """
        壊れたJSON文字列を修復する

        Args:
            json_str: 修復するJSON文字列

        Returns:
            修復済みのdict、または修復不可能な場合None
        """
        # json_repairライブラリを使用
        try:
            from json_repair import repair_json
            return repair_json(json_str)
        except:
            # フォールバック: 基本的な修復を試みる
            json_str = json_str.strip()

            # 末尾のカンマを削除
            if json_str.endswith(",}") or json_str.endswith(",]"):
                json_str = json_str[:-2] + json_str[-1]

            # クォートの修復
            if json_str.count('"') % 2 != 0:
                # 不完全なクォートがある場合
                if json_str.endswith('"'):
                    json_str = json_str[:-1]
                else:
                    json_str += '"'

            try:
                return json.loads(json_str)
            except:
                return None


class ErrorRecovery:
    """エラーからのリカバリ機能"""

    @staticmethod
    def create_partial_result(processed_data: List[Dict],
                            total_lines: int,
                            errors: List[str]) -> Dict[str, Any]:
        """
        部分的な処理結果を生成

        Args:
            processed_data: 処理済みデータ
            total_lines: 全体の行数
            errors: エラーメッセージリスト

        Returns:
            部分的な結果を含むレスポンス
        """
        success_rate = len(processed_data) / total_lines * 100 if total_lines > 0 else 0

        return {
            "partial_result": True,
            "processed_lines": len(processed_data),
            "total_lines": total_lines,
            "success_rate": f"{success_rate:.1f}%",
            "errors": errors[:5],  # 最初の5件のエラーのみ
            "error_count": len(errors),
            "data": processed_data,
            "message": f"{len(processed_data)}件のデータを処理しました（{len(errors)}件のエラーをスキップ）"
        }

    @staticmethod
    def suggest_recovery_action(error_type: str, context: Dict[str, Any]) -> List[str]:
        """
        エラーに基づいてリカバリアクションを提案

        Args:
            error_type: エラータイプ
            context: エラーコンテキスト

        Returns:
            推奨アクションのリスト
        """
        suggestions = []

        if error_type == "json_parse_error":
            suggestions.append("JSONLファイルの形式を確認してください")
            suggestions.append("各行が独立した有効なJSONオブジェクトであることを確認してください")
            if "line_number" in context:
                suggestions.append(f"特に行{context['line_number']}付近を確認してください")

        elif error_type == "missing_fields":
            missing = context.get("missing_fields", [])
            suggestions.append(f"必須フィールドを追加してください: {', '.join(missing)}")
            suggestions.append("各行にinference1とinference2フィールドが必要です")

        elif error_type == "timeout":
            suggestions.append("ファイルを小さく分割してください")
            suggestions.append("処理する行数を減らしてください")
            if context.get("gpu_mode"):
                suggestions.append("CPUモードで再試行してください")

        elif error_type == "memory_error":
            suggestions.append("ファイルサイズを小さくしてください")
            suggestions.append("バッチサイズを減らしてください")
            suggestions.append("他のアプリケーションを終了してください")

        return suggestions