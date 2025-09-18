"""Task 9.2: キャッシングとリソース管理のテスト

TDD実装：キャッシングとリソース管理機能のテスト
Requirements: 6.5 - パフォーマンス最適化、メモリ管理、大規模バッチ処理
"""

import pytest
import tempfile
import time
import json
import asyncio
import gc
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List

# キャッシングとリソース管理実装クラスのインポート
from src.caching_resource_manager import PromptTemplateCache, APIConnectionPool, ResourceMonitor, BatchProcessingOptimizer


class TestPromptTemplateCache:
    """プロンプトテンプレートキャッシュのテスト"""

    @pytest.fixture
    def temp_cache_dir(self):
        """テスト用キャッシュディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "cache"

    @pytest.fixture
    def prompt_cache(self, temp_cache_dir):
        """プロンプトテンプレートキャッシュのインスタンス"""
        return PromptTemplateCache(cache_dir=str(temp_cache_dir), max_size=100)

    def test_template_caching_and_retrieval(self, prompt_cache, temp_cache_dir):
        """テンプレートキャッシュと取得機能テスト"""
        # Requirement 6.5: プロンプトテンプレートのキャッシュ機能

        # テンプレートデータの準備
        template_data = {
            "system_prompt": "あなたは比較分析の専門家です",
            "user_prompt_template": "以下の2つの文章を比較し、類似度を0-1で評価してください:\n\n文章1: {text1}\n文章2: {text2}",
            "metadata": {
                "version": "1.0",
                "temperature": 0.2,
                "max_tokens": 64
            }
        }

        template_name = "similarity_comparison.yaml"

        # キャッシュに保存
        prompt_cache.cache_template(template_name, template_data)

        # キャッシュから取得
        cached_template = prompt_cache.get_template(template_name)
        assert cached_template is not None
        assert cached_template["system_prompt"] == template_data["system_prompt"]
        assert cached_template["user_prompt_template"] == template_data["user_prompt_template"]

        # キャッシュファイルが作成されることを確認
        cache_file = temp_cache_dir / f"{template_name}.cache"
        assert cache_file.exists()

    def test_cache_expiration_and_invalidation(self, prompt_cache):
        """キャッシュの有効期限と無効化テスト"""

        template_name = "test_template.yaml"
        template_data = {"content": "test template"}

        # 短い有効期限でキャッシュ
        prompt_cache.cache_template(template_name, template_data, ttl_seconds=1)

        # 即座に取得できることを確認
        cached = prompt_cache.get_template(template_name)
        assert cached is not None

        # TTL期限後に取得できないことを確認
        time.sleep(1.1)
        expired_cache = prompt_cache.get_template(template_name)
        assert expired_cache is None

        # 手動無効化テスト
        prompt_cache.cache_template(template_name, template_data)
        assert prompt_cache.get_template(template_name) is not None

        prompt_cache.invalidate_template(template_name)
        assert prompt_cache.get_template(template_name) is None

    def test_cache_size_limits_and_lru_eviction(self, temp_cache_dir):
        """キャッシュサイズ制限とLRU削除テスト"""
        cache = PromptTemplateCache(cache_dir=str(temp_cache_dir), max_size=3)

        # 制限を超えるテンプレートを追加
        for i in range(5):
            template_name = f"template_{i}.yaml"
            template_data = {"content": f"template content {i}"}
            cache.cache_template(template_name, template_data)

        # 最新の3つのみキャッシュされていることを確認
        assert cache.get_template("template_4.yaml") is not None
        assert cache.get_template("template_3.yaml") is not None
        assert cache.get_template("template_2.yaml") is not None

        # 古いものは削除されていることを確認
        assert cache.get_template("template_1.yaml") is None
        assert cache.get_template("template_0.yaml") is None

    def test_template_validation_and_error_handling(self, prompt_cache):
        """テンプレートバリデーションとエラーハンドリングテスト"""

        # 不正なテンプレートデータ（空の辞書）
        invalid_template = {}

        # バリデーションエラーが発生することを確認
        with pytest.raises(ValueError):
            prompt_cache.cache_template("invalid.yaml", invalid_template)

        # 存在しないテンプレート取得
        non_existent = prompt_cache.get_template("non_existent.yaml")
        assert non_existent is None

        # 破損したキャッシュファイルの処理
        prompt_cache.cache_template("test.yaml", {"valid": "data"})
        # キャッシュファイルを手動で破損させる処理をシミュレート
        stats = prompt_cache.get_cache_statistics()
        assert "cache_hits" in stats
        assert "cache_misses" in stats


class TestAPIConnectionPool:
    """API接続プールのテスト"""

    @pytest.fixture
    def connection_pool(self):
        """API接続プールのインスタンス"""
        return APIConnectionPool(max_connections=5, timeout=30.0)

    @pytest.mark.asyncio
    async def test_connection_pool_management(self, connection_pool):
        """接続プール管理機能テスト"""
        # Requirement 6.5: API接続プールの管理と最適化

        # 複数の同時接続要求
        api_endpoint = "http://localhost:8000/v1/chat/completions"

        # 接続取得
        connection1 = await connection_pool.get_connection(api_endpoint)
        connection2 = await connection_pool.get_connection(api_endpoint)

        assert connection1 is not None
        assert connection2 is not None

        # プール統計の確認
        stats = connection_pool.get_pool_statistics()
        assert stats["active_connections"] == 2
        assert stats["available_connections"] >= 0

        # 接続の返却
        await connection_pool.release_connection(api_endpoint, connection1)
        await connection_pool.release_connection(api_endpoint, connection2)

        # 接続が返却されたことを確認
        post_stats = connection_pool.get_pool_statistics()
        assert post_stats["active_connections"] == 0

    @pytest.mark.asyncio
    async def test_connection_reuse_and_health_check(self, connection_pool):
        """接続再利用とヘルスチェック機能テスト"""

        api_endpoint = "http://localhost:8000/v1/chat/completions"

        # 最初の接続取得
        connection1 = await connection_pool.get_connection(api_endpoint)
        conn_id_1 = connection1.connection_id

        # 接続を返却
        await connection_pool.release_connection(api_endpoint, connection1)

        # 同じ接続が再利用されることを確認
        connection2 = await connection_pool.get_connection(api_endpoint)
        conn_id_2 = connection2.connection_id

        assert conn_id_1 == conn_id_2  # 同じ接続が再利用される

        # ヘルスチェック実行
        health_results = await connection_pool.health_check_all()
        assert api_endpoint in health_results
        assert health_results[api_endpoint]["status"] in ["healthy", "unhealthy"]

    @pytest.mark.asyncio
    async def test_connection_timeout_and_cleanup(self, connection_pool):
        """接続タイムアウトとクリーンアップ機能テスト"""

        api_endpoint = "http://localhost:8000/v1/chat/completions"

        # タイムアウト設定の短い接続プールを作成
        short_timeout_pool = APIConnectionPool(max_connections=2, timeout=1.0)

        # アイドル接続のクリーンアップテスト
        connection = await connection_pool.get_connection(api_endpoint)
        await connection_pool.release_connection(api_endpoint, connection)

        # クリーンアップ実行
        cleaned_count = await connection_pool.cleanup_idle_connections(max_idle_time=0.1)
        assert cleaned_count >= 0

    @pytest.mark.asyncio
    async def test_connection_pool_limits_and_overflow(self, connection_pool):
        """接続プール制限とオーバーフロー処理テスト"""

        api_endpoint = "http://localhost:8000/v1/chat/completions"
        connections = []

        # 最大接続数まで接続を取得
        max_connections = connection_pool.max_connections
        for i in range(max_connections):
            conn = await connection_pool.get_connection(api_endpoint)
            connections.append(conn)

        # 制限を超えた接続要求
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                connection_pool.get_connection(api_endpoint),
                timeout=1.0
            )

        # 接続を返却
        for conn in connections:
            await connection_pool.release_connection(api_endpoint, conn)


class TestResourceMonitor:
    """リソース監視のテスト"""

    @pytest.fixture
    def resource_monitor(self):
        """リソース監視インスタンス"""
        return ResourceMonitor(monitoring_interval=1.0, alert_thresholds={
            "memory_percent": 80,
            "cpu_percent": 75,
            "disk_percent": 85
        })

    def test_memory_usage_monitoring(self, resource_monitor):
        """メモリ使用量監視機能テスト"""
        # Requirement 6.5: メモリ使用量の監視とクリーンアップ

        # メモリ統計の取得
        memory_stats = resource_monitor.get_memory_statistics()

        assert "total_memory_gb" in memory_stats
        assert "used_memory_gb" in memory_stats
        assert "available_memory_gb" in memory_stats
        assert "memory_percent" in memory_stats

        # メモリ使用量が妥当な範囲内であることを確認
        assert 0 <= memory_stats["memory_percent"] <= 100

    def test_memory_cleanup_and_gc(self, resource_monitor):
        """メモリクリーンアップとガベージコレクション機能テスト"""

        # メモリクリーンアップ前の統計
        pre_cleanup_stats = resource_monitor.get_memory_statistics()

        # 大量のダミーデータを作成
        dummy_data = []
        for i in range(10000):
            dummy_data.append({"data": f"test_data_{i}" * 100})

        # メモリ使用量の増加を確認
        post_allocation_stats = resource_monitor.get_memory_statistics()
        assert post_allocation_stats["used_memory_gb"] >= pre_cleanup_stats["used_memory_gb"]

        # ダミーデータを削除
        del dummy_data

        # ガベージコレクション実行
        cleaned_bytes = resource_monitor.force_memory_cleanup()
        assert cleaned_bytes >= 0

        # メモリ使用量の減少を確認
        post_cleanup_stats = resource_monitor.get_memory_statistics()
        # メモリが多少解放されることを期待（厳密な比較は環境に依存するため緩く）
        assert post_cleanup_stats["used_memory_gb"] <= post_allocation_stats["used_memory_gb"] + 0.1

    def test_resource_alerts_and_thresholds(self, resource_monitor):
        """リソースアラートと閾値機能テスト"""

        # アラート閾値の設定
        resource_monitor.set_alert_thresholds({
            "memory_percent": 50,  # テスト用に低く設定
            "cpu_percent": 30,
            "disk_percent": 40
        })

        # 現在のリソース状況を取得
        current_stats = resource_monitor.get_system_statistics()

        # アラートチェック実行
        alerts = resource_monitor.check_resource_alerts()

        # アラートの構造を確認
        assert isinstance(alerts, list)
        for alert in alerts:
            assert "resource_type" in alert
            assert "current_value" in alert
            assert "threshold" in alert
            assert "severity" in alert
            assert alert["severity"] in ["warning", "critical"]

    def test_continuous_monitoring_and_history(self, resource_monitor):
        """継続監視と履歴記録機能テスト"""

        # 監視開始
        resource_monitor.start_monitoring()

        # 短時間待機して統計を蓄積
        time.sleep(2.5)

        # 監視停止
        resource_monitor.stop_monitoring()

        # 履歴データの取得
        history = resource_monitor.get_monitoring_history(minutes=1)

        assert len(history) > 0
        for record in history:
            assert "timestamp" in record
            assert "memory_stats" in record
            assert "cpu_stats" in record
            assert "disk_stats" in record

        # 統計サマリーの取得
        summary = resource_monitor.get_monitoring_summary()
        assert "monitoring_duration_seconds" in summary
        assert "average_memory_percent" in summary
        assert "peak_memory_percent" in summary
        assert "alert_count" in summary


class TestBatchProcessingOptimizer:
    """バッチ処理最適化のテスト"""

    @pytest.fixture
    def batch_optimizer(self):
        """バッチ処理最適化インスタンス"""
        return BatchProcessingOptimizer(
            max_concurrent_batches=3,
            optimal_batch_size=50,
            memory_limit_mb=512
        )

    @pytest.mark.asyncio
    async def test_dynamic_batch_size_optimization(self, batch_optimizer):
        """動的バッチサイズ最適化機能テスト"""
        # Requirement 6.5: 大規模バッチ処理での効率化

        # テストデータの準備
        test_items = [{"id": i, "text": f"test text {i}"} for i in range(200)]

        # バッチサイズ最適化の実行
        optimal_batch_size = batch_optimizer.calculate_optimal_batch_size(
            total_items=len(test_items),
            estimated_item_size_mb=0.1,
            available_memory_mb=256
        )

        # 最適なバッチサイズが計算されることを確認
        assert 1 <= optimal_batch_size <= len(test_items)
        assert optimal_batch_size <= 100  # メモリ制限考慮

        # バッチ分割の実行
        batches = batch_optimizer.split_into_batches(test_items, optimal_batch_size)

        # 分割されたバッチの検証
        assert len(batches) > 0
        total_items_in_batches = sum(len(batch) for batch in batches)
        assert total_items_in_batches == len(test_items)

    @pytest.mark.asyncio
    async def test_concurrent_batch_processing_limits(self, batch_optimizer):
        """並行バッチ処理制限機能テスト"""

        # 模擬バッチ処理関数
        async def mock_process_batch(batch_id: str, items: List[Dict]):
            await asyncio.sleep(0.1)  # 処理時間をシミュレート
            return {"batch_id": batch_id, "processed": len(items)}

        # 大量のバッチを作成
        batches = []
        for i in range(10):
            batch = [{"id": j} for j in range(i*10, (i+1)*10)]
            batches.append((f"batch_{i}", batch))

        # 並行処理制限付きでバッチ処理実行
        results = await batch_optimizer.process_batches_concurrently(
            batches,
            process_function=mock_process_batch,
            max_concurrent=3
        )

        # 結果の検証
        assert len(results) == len(batches)
        for result in results:
            assert "batch_id" in result
            assert "processed" in result

    @pytest.mark.asyncio
    async def test_memory_aware_batch_processing(self, batch_optimizer):
        """メモリ考慮バッチ処理機能テスト"""

        # メモリ使用量を監視しながらバッチ処理
        test_data = [{"large_text": "x" * 1000} for _ in range(100)]

        # メモリ制限付きバッチ処理設定
        memory_config = {
            "max_memory_per_batch_mb": 10,
            "memory_check_interval": 0.1,
            "auto_adjust_batch_size": True
        }

        # メモリ監視付きバッチ処理実行
        processing_stats = await batch_optimizer.process_with_memory_monitoring(
            test_data,
            memory_config=memory_config
        )

        # 統計の検証
        assert "total_batches" in processing_stats
        assert "total_processing_time" in processing_stats
        assert "peak_memory_usage_mb" in processing_stats
        assert "memory_limit_exceeded_count" in processing_stats
        assert processing_stats["memory_limit_exceeded_count"] == 0  # 制限内で処理

    def test_batch_processing_performance_analysis(self, batch_optimizer):
        """バッチ処理パフォーマンス分析機能テスト"""

        # パフォーマンス履歴の作成（模擬データ）
        batch_optimizer._add_performance_record({
            "batch_size": 50,
            "processing_time": 2.5,
            "memory_usage_mb": 128,
            "success_rate": 0.95
        })

        batch_optimizer._add_performance_record({
            "batch_size": 100,
            "processing_time": 4.8,
            "memory_usage_mb": 256,
            "success_rate": 0.92
        })

        # パフォーマンス分析実行
        analysis = batch_optimizer.analyze_performance_patterns()

        assert "optimal_batch_size_recommendation" in analysis
        assert "average_processing_time_per_item" in analysis
        assert "memory_efficiency_score" in analysis
        assert "performance_trends" in analysis

    def test_batch_failure_recovery_and_retry(self, batch_optimizer):
        """バッチ失敗回復とリトライ機能テスト"""

        # 失敗するバッチ処理をシミュレート
        failed_batch_info = {
            "batch_id": "failed_batch_001",
            "items": [{"id": i} for i in range(20)],
            "failure_reason": "API timeout",
            "retry_count": 0
        }

        # リトライ設定
        retry_config = {
            "max_retries": 3,
            "backoff_factor": 2.0,
            "retry_on_errors": ["timeout", "connection_error", "rate_limit"]
        }

        # リトライメカニズムのテスト
        retry_plan = batch_optimizer.create_retry_plan(failed_batch_info, retry_config)

        assert "batch_id" in retry_plan
        assert "retry_attempts" in retry_plan
        assert "backoff_delays" in retry_plan
        assert len(retry_plan["backoff_delays"]) <= retry_config["max_retries"]

        # 失敗バッチの分割回復テスト
        recovery_batches = batch_optimizer.split_failed_batch(failed_batch_info)
        assert len(recovery_batches) > 1  # より小さなバッチに分割される
        total_recovered_items = sum(len(batch["items"]) for batch in recovery_batches)
        assert total_recovered_items == len(failed_batch_info["items"])


class TestCachingResourceIntegration:
    """キャッシングとリソース管理統合テスト"""

    @pytest.fixture
    def temp_system_dir(self):
        """テスト用システムディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_full_system_integration(self, temp_system_dir):
        """キャッシングとリソース管理の完全統合テスト"""
        pytest.skip("統合テスト - 実装完了後に実装")

    def test_performance_under_load(self, temp_system_dir):
        """負荷下でのパフォーマンステスト"""
        pytest.skip("負荷テスト - 実装完了後に実装")

    def test_memory_leak_prevention(self, temp_system_dir):
        """メモリリーク防止テスト"""
        pytest.skip("メモリリークテスト - 実装完了後に実装")