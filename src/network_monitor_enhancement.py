"""Network Monitor Enhancement for Dual File Comparison

Task 13.3の実装：
- 2ファイル比較時のHTTPリクエスト/レスポンス監視機能を構築
- APIエンドポイント正確性検証（validateAPIEndpoint）メソッドを実装
- HTTPRequestRecord構造でのリクエスト記録とタイミング情報取得
- リアルタイムネットワーク監視による即座検証機能を構築
- recordedRequestsによる完全なAPI呼び出し履歴の記録機能を実装

Requirements: 10.5, 10.10 - 2ファイル比較検証システム

Modules:
- NetworkMonitorEnhancement: メインのネットワーク監視クラス
- HTTPRequestRecord: HTTPリクエスト/レスポンス記録のデータクラス
- ValidationResult: 検証結果のデータクラス（dual_file_test_management_frameworkから再エクスポート）

Design Patterns:
- Observer Pattern: リアルタイム監視とイベント通知
- Strategy Pattern: 異なる検証ルールの適用
- Factory Pattern: リクエストレコードの生成

Key Features:
- Thread-safe monitoring operations with locking
- Real-time request capture with callback support
- Immediate validation for instant feedback
- Dual file comparison specific filtering
- Comprehensive endpoint accuracy verification
- Timing information capture with millisecond precision
"""

import asyncio
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Literal, Callable
from datetime import datetime
from urllib.parse import urlparse

# 既存のValidationResultをインポート
from .dual_file_test_management_framework import ValidationResult, ValidationError, ValidationWarning


@dataclass
class HTTPRequestRecord:
    """HTTPリクエスト/レスポンス記録

    Attributes:
        url: リクエストURL
        method: HTTPメソッド
        headers: リクエストヘッダー
        body: リクエストボディ
        response: レスポンス情報
        timestamp: リクエスト開始時刻
        duration: リクエスト処理時間（ミリ秒）
        metadata: 追加のメタデータ
    """
    url: str
    method: str
    headers: Dict[str, str]
    body: Any
    response: Dict[str, Any]
    timestamp: float
    duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class NetworkMonitorEnhancementError(Exception):
    """Network Monitor Enhancement専用エラークラス"""
    pass


class NetworkMonitorEnhancement:
    """Network Monitor Enhancement

    2ファイル比較時のHTTPリクエスト/レスポンス監視と検証を行う。
    リアルタイムネットワーク監視による即座検証機能を提供する。
    """

    def __init__(self):
        """ネットワークモニターの初期化"""
        self._is_monitoring = False
        self._recorded_requests: List[HTTPRequestRecord] = []
        self._logger = logging.getLogger(__name__)
        self._request_callbacks: List[Callable[[HTTPRequestRecord], None]] = []
        self._validation_enabled = False
        self._dual_file_mode = False
        self._monitoring_lock = threading.Lock()

    def isMonitoring(self) -> bool:
        """監視状態を取得

        Returns:
            bool: 監視中の場合True
        """
        return self._is_monitoring

    def startMonitoring(self) -> None:
        """ネットワーク監視を開始

        Raises:
            NetworkMonitorEnhancementError: 監視開始に失敗した場合
        """
        with self._monitoring_lock:
            if self._is_monitoring:
                self._logger.warning("Monitoring is already active")
                return

            try:
                self._is_monitoring = True
                self._recorded_requests.clear()
                self._logger.info("Network monitoring started")
            except Exception as e:
                self._logger.error(f"Failed to start monitoring: {e}")
                raise NetworkMonitorEnhancementError(f"Failed to start monitoring: {e}") from e

    def stopMonitoring(self) -> None:
        """ネットワーク監視を停止

        Raises:
            NetworkMonitorEnhancementError: 監視停止に失敗した場合
        """
        with self._monitoring_lock:
            if not self._is_monitoring:
                self._logger.warning("Monitoring is not active")
                return

            try:
                self._is_monitoring = False
                self._logger.info(f"Network monitoring stopped. Recorded {len(self._recorded_requests)} requests")
            except Exception as e:
                self._logger.error(f"Failed to stop monitoring: {e}")
                raise NetworkMonitorEnhancementError(f"Failed to stop monitoring: {e}") from e

    def getRecordedRequests(self) -> List[HTTPRequestRecord]:
        """記録されたHTTPリクエストを取得

        Returns:
            List[HTTPRequestRecord]: 記録されたリクエストのリスト
        """
        with self._monitoring_lock:
            return self._recorded_requests.copy()

    def validateAPIEndpoint(
        self,
        expectedEndpoint: str,
        actualRequest: HTTPRequestRecord
    ) -> ValidationResult:
        """APIエンドポイントの正確性を検証

        Args:
            expectedEndpoint: 期待されるエンドポイント
            actualRequest: 実際のリクエスト記録

        Returns:
            ValidationResult: 検証結果
        """
        try:
            self._logger.info(f"Validating endpoint: expected={expectedEndpoint}, actual={actualRequest.url}")

            errors = []
            warnings = []

            # URLからパスを抽出
            parsed_url = urlparse(actualRequest.url)
            actual_path = parsed_url.path

            # エンドポイントの一致を確認
            if not actual_path.endswith(expectedEndpoint):
                errors.append(ValidationError(
                    message=f"Endpoint mismatch: expected '{expectedEndpoint}', got '{actual_path}'",
                    code="ENDPOINT_MISMATCH",
                    details={
                        "expected_endpoint": expectedEndpoint,
                        "actual_path": actual_path,
                        "full_url": actualRequest.url
                    }
                ))

            # HTTPメソッドの確認（一般的にPOSTを期待）
            if actualRequest.method.upper() not in ["POST", "GET"]:
                warnings.append(ValidationWarning(
                    message=f"Unusual HTTP method: {actualRequest.method}",
                    code="UNUSUAL_METHOD",
                    details={"method": actualRequest.method}
                ))

            # レスポンスステータスの確認
            response_status = actualRequest.response.get("status")
            if response_status and response_status != 200:
                errors.append(ValidationError(
                    message=f"Non-200 response status: {response_status}",
                    code="NON_200_STATUS",
                    details={"status": response_status}
                ))

            is_valid = len(errors) == 0

            return ValidationResult(
                isValid=is_valid,
                errors=errors,
                warnings=warnings,
                details={
                    "endpoint_match": actual_path.endswith(expectedEndpoint),
                    "expected_endpoint": expectedEndpoint,
                    "actual_path": actual_path,
                    "request_method": actualRequest.method,
                    "response_status": response_status,
                    "validation_timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            self._logger.error(f"Endpoint validation failed: {e}")
            return ValidationResult(
                isValid=False,
                errors=[ValidationError(
                    message=f"Validation error: {str(e)}",
                    code="VALIDATION_ERROR",
                    details={"exception": str(e)}
                )],
                warnings=[],
                details={}
            )

    def recordRequest(self, request: HTTPRequestRecord) -> None:
        """HTTPリクエストを記録

        Args:
            request: 記録するリクエスト情報
        """
        if not self._is_monitoring:
            self._logger.warning("Attempted to record request while monitoring is disabled")
            return

        with self._monitoring_lock:
            self._recorded_requests.append(request)
            self._logger.debug(f"Recorded request: {request.method} {request.url}")

            # コールバック関数を実行
            for callback in self._request_callbacks:
                try:
                    callback(request)
                except Exception as e:
                    self._logger.error(f"Request callback failed: {e}")

    def clearRequestHistory(self) -> None:
        """リクエスト履歴をクリア"""
        with self._monitoring_lock:
            count = len(self._recorded_requests)
            self._recorded_requests.clear()
            self._logger.info(f"Cleared {count} recorded requests")

    def createRequestRecord(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        body: Any,
        start_time: float
    ) -> HTTPRequestRecord:
        """リクエストレコードを作成

        Args:
            url: リクエストURL
            method: HTTPメソッド
            headers: リクエストヘッダー
            body: リクエストボディ
            start_time: リクエスト開始時刻

        Returns:
            HTTPRequestRecord: 作成されたリクエストレコード
        """
        return HTTPRequestRecord(
            url=url,
            method=method,
            headers=headers,
            body=body,
            response={},  # 後で設定される
            timestamp=start_time,
            duration=0.0,  # 後で計算される
            metadata={"created_at": datetime.now().isoformat()}
        )

    def completeRequestRecord(
        self,
        request: HTTPRequestRecord,
        response: Dict[str, Any],
        end_time: float
    ) -> None:
        """リクエストレコードを完成させる

        Args:
            request: 完成させるリクエストレコード
            response: レスポンス情報
            end_time: リクエスト終了時刻
        """
        request.response = response
        request.duration = (end_time - request.timestamp) * 1000  # ミリ秒に変換
        request.metadata["completed_at"] = datetime.now().isoformat()

        self._logger.debug(f"Completed request record: {request.method} {request.url} in {request.duration:.1f}ms")

    # リアルタイム監視機能

    def startRealTimeMonitoring(self) -> None:
        """リアルタイム監視を開始"""
        self.startMonitoring()
        self._logger.info("Real-time monitoring enabled")

    def stopRealTimeMonitoring(self) -> None:
        """リアルタイム監視を停止"""
        self.stopMonitoring()
        self._logger.info("Real-time monitoring disabled")

    def onRequestCaptured(self, callback: Callable[[HTTPRequestRecord], None]) -> None:
        """リクエストキャプチャ時のコールバックを登録

        Args:
            callback: リクエストキャプチャ時に呼び出される関数
        """
        self._request_callbacks.append(callback)
        self._logger.debug("Request capture callback registered")

    # 即座検証機能

    def enableImmediateValidation(self, enabled: bool = True) -> None:
        """即座検証機能を有効/無効にする

        Args:
            enabled: 有効にする場合True
        """
        self._validation_enabled = enabled
        self._logger.info(f"Immediate validation {'enabled' if enabled else 'disabled'}")

    def validateRequestImmediately(
        self,
        request: HTTPRequestRecord,
        expected_endpoint: str
    ) -> ValidationResult:
        """リクエストを即座に検証

        Args:
            request: 検証するリクエスト
            expected_endpoint: 期待されるエンドポイント

        Returns:
            ValidationResult: 検証結果
        """
        if not self._validation_enabled:
            self._logger.warning("Immediate validation is disabled")
            return ValidationResult(
                isValid=True,
                errors=[],
                warnings=[ValidationWarning(
                    message="Immediate validation is disabled",
                    code="VALIDATION_DISABLED"
                )],
                details={}
            )

        return self.validateAPIEndpoint(expected_endpoint, request)

    # 2ファイル比較専用機能

    def enableDualFileMonitoring(self, enabled: bool = True) -> None:
        """2ファイル比較専用監視を有効/無効にする

        Args:
            enabled: 有効にする場合True
        """
        self._dual_file_mode = enabled
        self._logger.info(f"Dual file monitoring {'enabled' if enabled else 'disabled'}")

    def filterDualFileRequests(self) -> List[HTTPRequestRecord]:
        """2ファイル比較関連のリクエストのみをフィルタ

        Returns:
            List[HTTPRequestRecord]: 2ファイル比較関連のリクエストのリスト
        """
        dual_file_requests = []

        for request in self._recorded_requests:
            # 2ファイル比較関連のエンドポイントをチェック
            if any(endpoint in request.url for endpoint in ["/api/compare/dual", "/api/compare/dual/llm"]):
                dual_file_requests.append(request)

        self._logger.info(f"Filtered {len(dual_file_requests)} dual file requests from {len(self._recorded_requests)} total")
        return dual_file_requests

    def getMonitoringStatistics(self) -> Dict[str, Any]:
        """監視統計情報を取得

        Returns:
            Dict[str, Any]: 監視統計情報
        """
        with self._monitoring_lock:
            total_requests = len(self._recorded_requests)
            dual_file_requests = len(self.filterDualFileRequests())

            if total_requests > 0:
                average_duration = sum(req.duration for req in self._recorded_requests) / total_requests
                success_count = sum(1 for req in self._recorded_requests if req.response.get("status") == 200)
                success_rate = success_count / total_requests
            else:
                average_duration = 0.0
                success_rate = 0.0

            return {
                "is_monitoring": self._is_monitoring,
                "total_requests": total_requests,
                "dual_file_requests": dual_file_requests,
                "average_duration_ms": round(average_duration, 2),
                "success_rate": round(success_rate, 3),
                "validation_enabled": self._validation_enabled,
                "dual_file_mode": self._dual_file_mode,
                "callback_count": len(self._request_callbacks)
            }