"""Task 9.1: LLMメトリクス収集とログ記録の強化

TDD GREEN段階：LLM特化のメトリクス収集機能の実装
Requirements: 6.1 - パフォーマンスとエラーハンドリング
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict

from .logger import SystemLogger


@dataclass
class APICallRecord:
    """API呼び出し記録"""
    request_id: str
    model_name: str
    start_time: float
    end_time: Optional[float] = None
    success: Optional[bool] = None
    response_tokens: int = 0
    error: Optional[str] = None
    fallback_used: bool = False
    processing_time: Optional[float] = None


@dataclass
class BatchProcessingRecord:
    """バッチ処理記録"""
    batch_id: str
    total_items: int
    processing_mode: str
    model_name: str
    start_time: float
    completed_items: int = 0
    failed_items: int = 0
    current_processing_time: float = 0.0
    end_time: Optional[float] = None
    total_processing_time: Optional[float] = None
    fallback_used: int = 0


@dataclass
class PerformanceAlert:
    """パフォーマンスアラート"""
    alert_type: str
    timestamp: datetime
    model_name: Optional[str] = None
    response_time: Optional[float] = None
    error_rate: Optional[float] = None
    threshold: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class LLMMetricsCollector:
    """LLMメトリクス収集クラス"""

    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.log_dir.mkdir(exist_ok=True, parents=True)

        # API呼び出し記録
        self._api_calls: Dict[str, APICallRecord] = {}
        self._completed_calls: List[APICallRecord] = []

        # 統計情報
        self._lock = threading.Lock()

        # システムロガーとの統合
        self._logger = SystemLogger()

    def start_api_call(self, request_id: str, model_name: str) -> None:
        """API呼び出し開始記録"""
        with self._lock:
            record = APICallRecord(
                request_id=request_id,
                model_name=model_name,
                start_time=time.time()
            )
            self._api_calls[request_id] = record

            self._logger.access_logger.info(
                json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "event_type": "llm_api_start",
                    "request_id": request_id,
                    "model_name": model_name,
                    "message": f"LLM API call started: {request_id} with {model_name}"
                })
            )

    def end_api_call(self, request_id: str, success: bool,
                    response_tokens: int = 0, error: Optional[str] = None) -> None:
        """API呼び出し終了記録"""
        with self._lock:
            if request_id not in self._api_calls:
                self._logger.error_logger.warning(
                    json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "event_type": "api_record_not_found",
                        "request_id": request_id,
                        "message": f"API call record not found: {request_id}"
                    })
                )
                return

            record = self._api_calls[request_id]
            record.end_time = time.time()
            record.success = success
            record.response_tokens = response_tokens
            record.error = error
            record.processing_time = record.end_time - record.start_time

            # 完了記録に移動
            self._completed_calls.append(record)
            del self._api_calls[request_id]

            self._logger.access_logger.info(
                json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "event_type": "llm_api_end",
                    "request_id": request_id,
                    "success": success,
                    "processing_time": record.processing_time,
                    "response_tokens": response_tokens,
                    "error": error,
                    "message": f"LLM API call completed: {request_id}, success: {success}"
                })
            )

    def record_api_result(self, request_id: str, model_name: str, success: bool,
                         processing_time: float, fallback_used: bool = False,
                         error: Optional[str] = None) -> None:
        """API結果の直接記録"""
        with self._lock:
            record = APICallRecord(
                request_id=request_id,
                model_name=model_name,
                start_time=time.time() - processing_time,
                end_time=time.time(),
                success=success,
                processing_time=processing_time,
                fallback_used=fallback_used,
                error=error
            )

            self._completed_calls.append(record)

    def get_api_statistics(self) -> Dict[str, Any]:
        """API統計情報取得"""
        with self._lock:
            if not self._completed_calls:
                return {
                    "total_api_calls": 0,
                    "successful_api_calls": 0,
                    "average_response_time": 0.0,
                    "total_response_tokens": 0,
                    "models": {}
                }

            successful_calls = [call for call in self._completed_calls if call.success]
            model_stats = defaultdict(lambda: {"total_calls": 0, "success_rate": 0.0})

            for call in self._completed_calls:
                model_stats[call.model_name]["total_calls"] += 1

            for model, stats in model_stats.items():
                successful_model_calls = len([
                    call for call in self._completed_calls
                    if call.model_name == model and call.success
                ])
                stats["success_rate"] = (successful_model_calls / stats["total_calls"]) * 100

            return {
                "total_api_calls": len(self._completed_calls),
                "successful_api_calls": len(successful_calls),
                "average_response_time": sum(
                    call.processing_time or 0 for call in self._completed_calls
                ) / len(self._completed_calls),
                "total_response_tokens": sum(call.response_tokens for call in self._completed_calls),
                "models": dict(model_stats)
            }

    def get_statistics(self) -> Dict[str, Any]:
        """全般統計情報取得"""
        with self._lock:
            total_requests = len(self._completed_calls)
            if total_requests == 0:
                return {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "error_rate": 0.0,
                    "fallback_used_count": 0,
                    "fallback_usage_rate": 0.0
                }

            successful_requests = len([call for call in self._completed_calls if call.success])
            failed_requests = total_requests - successful_requests
            fallback_used_count = len([call for call in self._completed_calls if call.fallback_used])

            return {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "error_rate": (failed_requests / total_requests) * 100,
                "fallback_used_count": fallback_used_count,
                "fallback_usage_rate": (fallback_used_count / total_requests) * 100
            }

    def get_model_statistics(self) -> Dict[str, Dict[str, Any]]:
        """モデル別統計情報取得"""
        with self._lock:
            model_stats = defaultdict(lambda: {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "success_rate": 0.0,
                "average_response_time": 0.0,
                "total_processing_time": 0.0
            })

            for call in self._completed_calls:
                stats = model_stats[call.model_name]
                stats["total_calls"] += 1

                if call.success:
                    stats["successful_calls"] += 1
                else:
                    stats["failed_calls"] += 1

                if call.processing_time:
                    stats["total_processing_time"] += call.processing_time

            # 計算処理
            for model, stats in model_stats.items():
                if stats["total_calls"] > 0:
                    stats["success_rate"] = (stats["successful_calls"] / stats["total_calls"]) * 100
                    stats["average_response_time"] = stats["total_processing_time"] / stats["total_calls"]

            return dict(model_stats)

    def get_error_statistics(self) -> Dict[str, Any]:
        """エラー統計情報取得"""
        with self._lock:
            error_counts = defaultdict(int)
            total_errors = 0

            for call in self._completed_calls:
                if call.error:
                    error_counts[call.error] += 1
                    total_errors += 1

            error_stats = dict(error_counts)
            error_stats["total_errors"] = total_errors

            return error_stats

    def save_metrics_to_file(self) -> None:
        """メトリクスをファイルに保存"""
        metrics_file = self.log_dir / "llm_metrics.json"

        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "statistics": self.get_statistics(),
            "api_statistics": self.get_api_statistics(),
            "model_statistics": self.get_model_statistics(),
            "error_statistics": self.get_error_statistics()
        }

        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, ensure_ascii=False, indent=2)

        self._logger.access_logger.info(
            json.dumps({
                "timestamp": datetime.now().isoformat(),
                "event_type": "metrics_saved",
                "file_path": str(metrics_file),
                "message": f"Metrics saved to {metrics_file}"
            })
        )


class LLMEventLogger:
    """LLMイベントロガークラス"""

    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.log_dir.mkdir(exist_ok=True, parents=True)

        # ログファイル設定
        self.events_log_file = self.log_dir / "llm_events.log"

        # アラート履歴
        self._alerts: deque = deque(maxlen=1000)  # 最新1000件まで保持
        self._lock = threading.Lock()

        # バッチ処理記録
        self._batch_records: Dict[str, BatchProcessingRecord] = {}

        # システムロガーとの統合
        self._logger = SystemLogger()

    def _write_event_log(self, event_data: Dict[str, Any]) -> None:
        """イベントログをファイルに書き込み"""
        event_data["timestamp"] = datetime.now().isoformat()

        with open(self.events_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event_data, ensure_ascii=False) + '\n')

    def log_llm_api_call(self, request_id: str, model_name: str,
                        prompt_tokens: int, temperature: float,
                        max_tokens: int, prompt_file: str) -> None:
        """LLM API呼び出しイベントログ"""
        event_data = {
            "event_type": "llm_api_call",
            "request_id": request_id,
            "model_name": model_name,
            "prompt_tokens": prompt_tokens,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "prompt_file": prompt_file
        }

        self._write_event_log(event_data)
        self._logger.access_logger.info(
            json.dumps({
                "timestamp": datetime.now().isoformat(),
                "message": f"LLM API call logged: {request_id}",
                **event_data
            })
        )

    def log_llm_response(self, request_id: str, success: bool,
                        response_tokens: int, processing_time: float,
                        raw_response: str) -> None:
        """LLM応答受信イベントログ"""
        event_data = {
            "event_type": "llm_response",
            "request_id": request_id,
            "success": success,
            "response_tokens": response_tokens,
            "processing_time": processing_time,
            "raw_response": raw_response
        }

        self._write_event_log(event_data)
        self._logger.access_logger.info(
            json.dumps({
                "timestamp": datetime.now().isoformat(),
                "message": f"LLM response logged: {request_id}",
                **event_data
            })
        )

    def log_llm_fallback(self, request_id: str, original_error: str,
                        fallback_method: str, fallback_success: bool) -> None:
        """LLMフォールバックイベントログ"""
        event_data = {
            "event_type": "llm_fallback",
            "request_id": request_id,
            "original_error": original_error,
            "fallback_method": fallback_method,
            "fallback_success": fallback_success
        }

        self._write_event_log(event_data)
        self._logger.error_logger.warning(
            json.dumps({
                "timestamp": datetime.now().isoformat(),
                "message": f"LLM fallback logged: {request_id}",
                **event_data
            })
        )

    def log_performance_alert(self, alert_type: str, model_name: Optional[str] = None,
                             response_time: Optional[float] = None,
                             error_rate: Optional[float] = None,
                             threshold: Optional[float] = None,
                             details: Optional[Dict[str, Any]] = None) -> None:
        """パフォーマンスアラートログ"""
        alert = PerformanceAlert(
            alert_type=alert_type,
            timestamp=datetime.now(),
            model_name=model_name,
            response_time=response_time,
            error_rate=error_rate,
            threshold=threshold,
            details=details
        )

        with self._lock:
            self._alerts.append(alert)

        alert_data = asdict(alert)
        alert_data["timestamp"] = alert.timestamp.isoformat()
        alert_data["event_type"] = "performance_alert"

        self._write_event_log(alert_data)
        self._logger.error_logger.error(
            json.dumps({
                "timestamp": datetime.now().isoformat(),
                "message": f"Performance alert: {alert_type}",
                **alert_data
            })
        )

    def get_recent_alerts(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """最近のアラート取得"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        with self._lock:
            recent_alerts = [
                asdict(alert) for alert in self._alerts
                if alert.timestamp >= cutoff_time
            ]

        # timestampをISO文字列に変換
        for alert in recent_alerts:
            if isinstance(alert.get("timestamp"), datetime):
                alert["timestamp"] = alert["timestamp"].isoformat()

        return recent_alerts

    def start_batch_processing(self, batch_id: str, total_items: int,
                              processing_mode: str, model_name: str) -> None:
        """バッチ処理開始ログ"""
        record = BatchProcessingRecord(
            batch_id=batch_id,
            total_items=total_items,
            processing_mode=processing_mode,
            model_name=model_name,
            start_time=time.time()
        )

        with self._lock:
            self._batch_records[batch_id] = record

        event_data = {
            "event_type": "batch_start",
            "batch_id": batch_id,
            "total_items": total_items,
            "processing_mode": processing_mode,
            "model_name": model_name
        }

        self._write_event_log(event_data)
        self._logger.access_logger.info(
            json.dumps({
                "timestamp": datetime.now().isoformat(),
                "message": f"Batch processing started: {batch_id}",
                **event_data
            })
        )

    def update_batch_progress(self, batch_id: str, completed_items: int,
                             failed_items: int, current_processing_time: float) -> None:
        """バッチ進捗更新ログ"""
        with self._lock:
            if batch_id not in self._batch_records:
                self._logger.error_logger.warning(
                    json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "event_type": "batch_record_not_found",
                        "batch_id": batch_id,
                        "message": f"Batch record not found: {batch_id}"
                    })
                )
                return

            record = self._batch_records[batch_id]
            record.completed_items = completed_items
            record.failed_items = failed_items
            record.current_processing_time = current_processing_time

        event_data = {
            "event_type": "batch_progress",
            "batch_id": batch_id,
            "completed_items": completed_items,
            "failed_items": failed_items,
            "current_processing_time": current_processing_time
        }

        self._write_event_log(event_data)

    def complete_batch_processing(self, batch_id: str, total_completed: int,
                                 total_failed: int, total_processing_time: float,
                                 fallback_used: int = 0) -> None:
        """バッチ処理完了ログ"""
        with self._lock:
            if batch_id not in self._batch_records:
                self._logger.error_logger.warning(
                    json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "event_type": "batch_record_not_found",
                        "batch_id": batch_id,
                        "message": f"Batch record not found: {batch_id}"
                    })
                )
                return

            record = self._batch_records[batch_id]
            record.completed_items = total_completed
            record.failed_items = total_failed
            record.end_time = time.time()
            record.total_processing_time = total_processing_time
            record.fallback_used = fallback_used

        event_data = {
            "event_type": "batch_complete",
            "batch_id": batch_id,
            "total_completed": total_completed,
            "total_failed": total_failed,
            "total_processing_time": total_processing_time,
            "fallback_used": fallback_used
        }

        self._write_event_log(event_data)
        self._logger.access_logger.info(
            json.dumps({
                "timestamp": datetime.now().isoformat(),
                "message": f"Batch processing completed: {batch_id}",
                **event_data
            })
        )

    def get_batch_statistics(self, batch_id: str) -> Dict[str, Any]:
        """バッチ統計情報取得"""
        with self._lock:
            if batch_id not in self._batch_records:
                return {}

            record = self._batch_records[batch_id]

            completion_rate = (record.completed_items / record.total_items) * 100 if record.total_items > 0 else 0
            error_rate = (record.failed_items / record.total_items) * 100 if record.total_items > 0 else 0

            return {
                "total_items": record.total_items,
                "completed_items": record.completed_items,
                "failed_items": record.failed_items,
                "completion_rate": completion_rate,
                "error_rate": error_rate,
                "total_processing_time": record.total_processing_time or record.current_processing_time,
                "fallback_used": record.fallback_used
            }