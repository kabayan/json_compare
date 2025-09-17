#!/usr/bin/env python3
"""ログシステムの実装"""

import json
import logging
import logging.handlers
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import psutil


class SystemLogger:
    """統合ログシステム"""

    def __init__(self, log_dir: str = None):
        """
        ログシステムの初期化

        Args:
            log_dir: ログディレクトリのパス
        """
        if log_dir is None:
            # デフォルトログディレクトリ
            log_dir = os.environ.get("LOG_DIR", "/tmp/json_compare/logs")

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # ログファイルのパス
        self.access_log_path = self.log_dir / "access.log"
        self.error_log_path = self.log_dir / "error.log"
        self.metrics_log_path = self.log_dir / "metrics.log"

        # ロガーの設定
        self._setup_loggers()

    def _setup_loggers(self):
        """ロガーの設定"""
        # フォーマッター
        json_formatter = JsonFormatter()
        standard_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # アクセスロガー
        self.access_logger = logging.getLogger("json_compare.access")
        self.access_logger.setLevel(logging.INFO)
        access_handler = logging.handlers.RotatingFileHandler(
            self.access_log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        access_handler.setFormatter(json_formatter)
        self.access_logger.addHandler(access_handler)

        # エラーロガー
        self.error_logger = logging.getLogger("json_compare.error")
        self.error_logger.setLevel(logging.ERROR)
        error_handler = logging.handlers.RotatingFileHandler(
            self.error_log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        error_handler.setFormatter(json_formatter)
        self.error_logger.addHandler(error_handler)

        # メトリクスロガー
        self.metrics_logger = logging.getLogger("json_compare.metrics")
        self.metrics_logger.setLevel(logging.INFO)
        metrics_handler = logging.handlers.RotatingFileHandler(
            self.metrics_log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3
        )
        metrics_handler.setFormatter(json_formatter)
        self.metrics_logger.addHandler(metrics_handler)

    def log_upload(self,
                   filename: str,
                   file_size: int,
                   processing_time: float,
                   result: str,
                   gpu_mode: bool = False,
                   error: Optional[str] = None,
                   client_ip: Optional[str] = None):
        """
        ファイルアップロードをログに記録

        Args:
            filename: アップロードされたファイル名
            file_size: ファイルサイズ（バイト）
            processing_time: 処理時間（秒）
            result: 処理結果（success/error/timeout）
            gpu_mode: GPU使用フラグ
            error: エラーメッセージ（ある場合）
            client_ip: クライアントIPアドレス
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "file_upload",
            "filename": filename,
            "file_size": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "processing_time": round(processing_time, 3),
            "result": result,
            "gpu_mode": gpu_mode,
            "client_ip": client_ip
        }

        if error:
            log_entry["error"] = error

        self.access_logger.info(json.dumps(log_entry))

    def log_error(self,
                  error_id: str,
                  error_type: str,
                  error_message: str,
                  stack_trace: Optional[str] = None,
                  context: Optional[Dict[str, Any]] = None):
        """
        エラーをログに記録

        Args:
            error_id: エラーID
            error_type: エラータイプ
            error_message: エラーメッセージ
            stack_trace: スタックトレース
            context: 追加のコンテキスト情報
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_id": error_id,
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "context": context or {}
        }

        self.error_logger.error(json.dumps(log_entry))

    def log_metrics(self):
        """システムメトリクスをログに記録"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # メモリ使用状況
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024 ** 3)

            # ディスク使用状況
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024 ** 3)

            # プロセス情報
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024 ** 2)
            process_threads = process.num_threads()

            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count
                },
                "memory": {
                    "percent": memory_percent,
                    "available_gb": round(memory_available_gb, 2)
                },
                "disk": {
                    "percent": disk_percent,
                    "free_gb": round(disk_free_gb, 2)
                },
                "process": {
                    "memory_mb": round(process_memory_mb, 2),
                    "threads": process_threads
                }
            }

            self.metrics_logger.info(json.dumps(metrics))

        except Exception as e:
            self.error_logger.error(f"Failed to collect metrics: {str(e)}")

    def cleanup_old_logs(self, days: int = 7):
        """
        古いログファイルをクリーンアップ

        Args:
            days: 保持する日数
        """
        import time
        from datetime import timedelta

        cutoff_time = time.time() - (days * 24 * 60 * 60)

        for log_file in self.log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    print(f"Deleted old log file: {log_file}")
                except Exception as e:
                    print(f"Failed to delete {log_file}: {e}")


class JsonFormatter(logging.Formatter):
    """JSON形式のログフォーマッター"""

    def format(self, record):
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }

        if hasattr(record, "extra"):
            log_obj.update(record.extra)

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


class RequestLogger:
    """HTTPリクエストのロギング"""

    def __init__(self, logger: SystemLogger):
        self.logger = logger
        self.request_start_times = {}

    def log_request_start(self, request_id: str):
        """リクエスト開始をログ"""
        self.request_start_times[request_id] = time.time()

    def log_request_end(self,
                       request_id: str,
                       method: str,
                       path: str,
                       status_code: int,
                       client_ip: Optional[str] = None):
        """
        リクエスト終了をログ

        Args:
            request_id: リクエストID
            method: HTTPメソッド
            path: リクエストパス
            status_code: レスポンスステータスコード
            client_ip: クライアントIP
        """
        start_time = self.request_start_times.pop(request_id, None)
        processing_time = time.time() - start_time if start_time else 0

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "method": method,
            "path": path,
            "status_code": status_code,
            "processing_time": round(processing_time, 3),
            "client_ip": client_ip
        }

        if status_code >= 400:
            self.logger.error_logger.warning(json.dumps(log_entry))
        else:
            self.logger.access_logger.info(json.dumps(log_entry))


class MetricsCollector:
    """メトリクス収集とモニタリング"""

    def __init__(self, logger: SystemLogger):
        self.logger = logger
        self.metrics = {
            "total_uploads": 0,
            "successful_uploads": 0,
            "failed_uploads": 0,
            "total_processing_time": 0,
            "total_file_size": 0
        }

    def record_upload(self,
                     success: bool,
                     processing_time: float,
                     file_size: int):
        """
        アップロードメトリクスを記録

        Args:
            success: 成功フラグ
            processing_time: 処理時間（秒）
            file_size: ファイルサイズ（バイト）
        """
        self.metrics["total_uploads"] += 1
        if success:
            self.metrics["successful_uploads"] += 1
        else:
            self.metrics["failed_uploads"] += 1

        self.metrics["total_processing_time"] += processing_time
        self.metrics["total_file_size"] += file_size

    def get_summary(self) -> Dict[str, Any]:
        """メトリクスサマリーを取得"""
        total = self.metrics["total_uploads"]
        if total == 0:
            return {
                "message": "No uploads yet"
            }

        return {
            "total_uploads": total,
            "successful_uploads": self.metrics["successful_uploads"],
            "failed_uploads": self.metrics["failed_uploads"],
            "success_rate": round(self.metrics["successful_uploads"] / total * 100, 1),
            "average_processing_time": round(self.metrics["total_processing_time"] / total, 2),
            "average_file_size_mb": round(self.metrics["total_file_size"] / total / (1024 * 1024), 2),
            "total_data_processed_mb": round(self.metrics["total_file_size"] / (1024 * 1024), 2)
        }

    def log_summary(self):
        """サマリーをログに記録"""
        summary = self.get_summary()
        summary["timestamp"] = datetime.now().isoformat()
        summary["event"] = "metrics_summary"
        self.logger.metrics_logger.info(json.dumps(summary))


# グローバルインスタンス
_logger = None
_request_logger = None
_metrics_collector = None


def get_logger() -> SystemLogger:
    """ロガーインスタンスを取得"""
    global _logger
    if _logger is None:
        _logger = SystemLogger()
    return _logger


def get_request_logger() -> RequestLogger:
    """リクエストロガーを取得"""
    global _request_logger
    if _request_logger is None:
        _request_logger = RequestLogger(get_logger())
    return _request_logger


def get_metrics_collector() -> MetricsCollector:
    """メトリクスコレクターを取得"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(get_logger())
    return _metrics_collector