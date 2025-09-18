"""Task 9.1: LLMメトリクス収集とログ記録の強化のテスト

TDD実装：LLM特化のメトリクス収集機能のテスト
Requirements: 6.1 - パフォーマンスとエラーハンドリング
"""

import pytest
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# LLMメトリクス実装クラスのインポート
from src.llm_metrics import LLMMetricsCollector, LLMEventLogger


class TestLLMMetricsCollector:
    """LLMメトリクス収集のテスト"""

    @pytest.fixture
    def temp_log_dir(self):
        """テスト用ログディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "logs"

    @pytest.fixture
    def metrics_collector(self, temp_log_dir):
        """LLMメトリクスコレクターのインスタンス"""
        return LLMMetricsCollector(log_dir=str(temp_log_dir))

    def test_api_call_timing_recording(self, metrics_collector):
        """API呼び出し応答時間の記録機能テスト"""
        # Requirement 6.1: API呼び出し応答時間の記録

        # API呼び出し開始
        request_id = "test_request_001"
        model_name = "qwen3-14b-awq"
        metrics_collector.start_api_call(request_id, model_name)

        # 模擬処理時間
        time.sleep(0.1)

        # API呼び出し完了記録
        response_tokens = 64
        success = True
        metrics_collector.end_api_call(
            request_id,
            success=success,
            response_tokens=response_tokens,
            error=None
        )

        # 記録されたメトリクスを確認
        stats = metrics_collector.get_api_statistics()
        assert stats["total_api_calls"] == 1
        assert stats["successful_api_calls"] == 1
        assert stats["models"][model_name]["total_calls"] == 1
        assert stats["models"][model_name]["success_rate"] == 100.0
        assert stats["average_response_time"] > 0.1
        assert stats["total_response_tokens"] == 64

    def test_error_rate_and_fallback_statistics(self, metrics_collector):
        """エラー率とフォールバック使用率の統計テスト"""
        # Requirement 6.1: エラー率とフォールバック使用率の統計

        # 成功したAPI呼び出し
        metrics_collector.record_api_result("req1", "qwen3-14b-awq", True, 1.2, fallback_used=False)

        # 失敗してフォールバックしたAPI呼び出し
        metrics_collector.record_api_result("req2", "qwen3-14b-awq", False, 2.5, fallback_used=True, error="timeout")

        # 失敗でフォールバックなしのAPI呼び出し
        metrics_collector.record_api_result("req3", "qwen3-14b-awq", False, 0.5, fallback_used=False, error="connection_error")

        stats = metrics_collector.get_statistics()

        # エラー率の確認
        assert stats["total_requests"] == 3
        assert stats["successful_requests"] == 1
        assert stats["failed_requests"] == 2
        assert stats["error_rate"] == pytest.approx(66.7, rel=0.1)

        # フォールバック使用率の確認
        assert stats["fallback_used_count"] == 1
        assert stats["fallback_usage_rate"] == pytest.approx(33.3, rel=0.1)

    def test_model_specific_success_tracking(self, metrics_collector):
        """モデル別の成功率追跡機能テスト"""
        # Requirement 6.1: モデル別の成功率追跡機能

        # Model 1のテスト結果
        for i in range(8):  # 8回成功
            metrics_collector.record_api_result(f"req1_{i}", "qwen3-14b-awq", True, 1.0)
        for i in range(2):  # 2回失敗
            metrics_collector.record_api_result(f"req1_fail_{i}", "qwen3-14b-awq", False, 0.5, error="timeout")

        # Model 2のテスト結果
        for i in range(6):  # 6回成功
            metrics_collector.record_api_result(f"req2_{i}", "llama-7b", True, 1.5)
        for i in range(4):  # 4回失敗
            metrics_collector.record_api_result(f"req2_fail_{i}", "llama-7b", False, 0.8, error="rate_limit")

        model_stats = metrics_collector.get_model_statistics()

        # Model 1の統計確認
        qwen_stats = model_stats["qwen3-14b-awq"]
        assert qwen_stats["total_calls"] == 10
        assert qwen_stats["successful_calls"] == 8
        assert qwen_stats["failed_calls"] == 2
        assert qwen_stats["success_rate"] == 80.0
        assert qwen_stats["average_response_time"] == pytest.approx(0.9, rel=0.1)

        # Model 2の統計確認
        llama_stats = model_stats["llama-7b"]
        assert llama_stats["total_calls"] == 10
        assert llama_stats["successful_calls"] == 6
        assert llama_stats["failed_calls"] == 4
        assert llama_stats["success_rate"] == 60.0
        assert llama_stats["average_response_time"] == pytest.approx(1.26, rel=0.1)

    def test_error_type_classification(self, metrics_collector):
        """エラータイプ別の分類テスト"""

        # 異なるタイプのエラーを記録
        errors = [
            ("timeout", 3),
            ("connection_error", 2),
            ("rate_limit", 1),
            ("invalid_response", 4)
        ]

        for error_type, count in errors:
            for i in range(count):
                metrics_collector.record_api_result(
                    f"req_{error_type}_{i}",
                    "qwen3-14b-awq",
                    False,
                    1.0,
                    error=error_type
                )

        error_stats = metrics_collector.get_error_statistics()

        assert error_stats["timeout"] == 3
        assert error_stats["connection_error"] == 2
        assert error_stats["rate_limit"] == 1
        assert error_stats["invalid_response"] == 4
        assert error_stats["total_errors"] == 10

    def test_metrics_persistence(self, metrics_collector, temp_log_dir):
        """メトリクスの永続化テスト"""

        # メトリクスデータの記録
        metrics_collector.record_api_result("req1", "qwen3-14b-awq", True, 1.5)
        metrics_collector.record_api_result("req2", "qwen3-14b-awq", False, 2.0, error="timeout")

        # メトリクスをファイルに保存
        metrics_collector.save_metrics_to_file()

        # ファイルが作成されることを確認
        metrics_file = temp_log_dir / "llm_metrics.json"
        assert metrics_file.exists()

        # 保存されたデータを読み込んで確認
        with open(metrics_file, 'r') as f:
            saved_metrics = json.load(f)

        assert saved_metrics["statistics"]["total_requests"] == 2
        assert saved_metrics["statistics"]["successful_requests"] == 1
        assert saved_metrics["statistics"]["failed_requests"] == 1


class TestLLMEventLogger:
    """LLMイベントロガーのテスト"""

    @pytest.fixture
    def temp_log_dir(self):
        """テスト用ログディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "logs"

    @pytest.fixture
    def event_logger(self, temp_log_dir):
        """LLMイベントロガーのインスタンス"""
        return LLMEventLogger(log_dir=str(temp_log_dir))

    def test_structured_llm_event_logging(self, event_logger, temp_log_dir):
        """構造化LLMイベントログ記録テスト"""
        # Requirement 6.1: 構造化ログへのLLM関連イベント記録

        # LLM API呼び出しイベント
        event_logger.log_llm_api_call(
            request_id="req_001",
            model_name="qwen3-14b-awq",
            prompt_tokens=120,
            temperature=0.2,
            max_tokens=64,
            prompt_file="default_similarity.yaml"
        )

        # LLM応答受信イベント
        event_logger.log_llm_response(
            request_id="req_001",
            success=True,
            response_tokens=45,
            processing_time=1.8,
            raw_response="スコア: 0.8\nカテゴリ: 類似\n理由: 意味的に類似している"
        )

        # LLMフォールバックイベント
        event_logger.log_llm_fallback(
            request_id="req_002",
            original_error="API timeout after 30 seconds",
            fallback_method="embedding",
            fallback_success=True
        )

        # ログファイルが作成されることを確認
        log_file = temp_log_dir / "llm_events.log"
        assert log_file.exists()

        # ログの内容を確認
        with open(log_file, 'r') as f:
            log_lines = f.readlines()

        assert len(log_lines) == 3

        # API呼び出しログの検証
        api_call_log = json.loads(log_lines[0])
        assert api_call_log["event_type"] == "llm_api_call"
        assert api_call_log["request_id"] == "req_001"
        assert api_call_log["model_name"] == "qwen3-14b-awq"
        assert api_call_log["prompt_tokens"] == 120

        # 応答ログの検証
        response_log = json.loads(log_lines[1])
        assert response_log["event_type"] == "llm_response"
        assert response_log["success"] == True
        assert response_log["processing_time"] == 1.8

        # フォールバックログの検証
        fallback_log = json.loads(log_lines[2])
        assert fallback_log["event_type"] == "llm_fallback"
        assert fallback_log["fallback_method"] == "embedding"

    def test_performance_threshold_alerts(self, event_logger):
        """パフォーマンス閾値アラートテスト"""

        # 応答時間が閾値を超えた場合のアラート
        event_logger.log_performance_alert(
            alert_type="slow_response",
            model_name="qwen3-14b-awq",
            response_time=8.5,
            threshold=5.0,
            details={"request_id": "slow_req_001", "prompt_tokens": 200}
        )

        # 高いエラー率の場合のアラート
        event_logger.log_performance_alert(
            alert_type="high_error_rate",
            model_name="qwen3-14b-awq",
            error_rate=35.0,
            threshold=10.0,
            details={"time_window": "last_hour", "total_requests": 100}
        )

        alerts = event_logger.get_recent_alerts(minutes=5)
        assert len(alerts) == 2
        assert alerts[0]["alert_type"] == "slow_response"
        assert alerts[1]["alert_type"] == "high_error_rate"

    def test_batch_processing_metrics(self, event_logger):
        """バッチ処理メトリクステスト"""

        # バッチ処理開始
        batch_id = "batch_001"
        event_logger.start_batch_processing(
            batch_id=batch_id,
            total_items=100,
            processing_mode="llm",
            model_name="qwen3-14b-awq"
        )

        # バッチ進捗更新
        event_logger.update_batch_progress(
            batch_id=batch_id,
            completed_items=50,
            failed_items=3,
            current_processing_time=45.2
        )

        # バッチ処理完了
        event_logger.complete_batch_processing(
            batch_id=batch_id,
            total_completed=97,
            total_failed=3,
            total_processing_time=89.7,
            fallback_used=2
        )

        batch_stats = event_logger.get_batch_statistics(batch_id)
        assert batch_stats["total_items"] == 100
        assert batch_stats["completion_rate"] == 97.0
        assert batch_stats["error_rate"] == 3.0
        assert batch_stats["total_processing_time"] == 89.7
        assert batch_stats["fallback_used"] == 2


class TestMetricsIntegration:
    """メトリクス統合テスト"""

    @pytest.fixture
    def temp_log_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "logs"

    def test_metrics_integration_with_llm_similarity(self, temp_log_dir):
        """LLMSimilarityクラスとのメトリクス統合テスト"""
        pytest.skip("統合テスト - 実装完了後に実装")

        # この統合テストは、LLMSimilarityクラスが
        # 自動的にメトリクスを記録することを確認する

    def test_metrics_api_endpoint(self, temp_log_dir):
        """メトリクスAPIエンドポイントテスト"""
        pytest.skip("API統合テスト - 実装完了後に実装")

        # /api/metrics エンドポイントが
        # LLM関連のメトリクスを返すことを確認する

    def test_real_time_metrics_dashboard(self, temp_log_dir):
        """リアルタイムメトリクスダッシュボードテスト"""
        pytest.skip("UI統合テスト - 実装完了後に実装")

        # Web UIでLLMメトリクスが表示されることを確認する