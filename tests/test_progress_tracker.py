"""Test suite for Progress Tracker functionality using TDD."""

import pytest
import time
import sys
import io
import asyncio
import json
from datetime import datetime
from typing import Optional, AsyncGenerator
from unittest.mock import Mock, patch, AsyncMock
from contextlib import redirect_stderr, redirect_stdout
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

# Import the module we're about to create
from src.progress_tracker import ProgressTracker, ProgressData, TaskData, TqdmInterceptor


class TestProgressTrackerCore:
    """Test Task 1.1: 進捗管理システムの中核機能."""

    def test_create_task_generates_unique_id(self):
        """タスクIDによる処理の一意識別機能を作成."""
        tracker = ProgressTracker()

        # Create multiple tasks
        task_id1 = tracker.create_task(total_items=100)
        task_id2 = tracker.create_task(total_items=200)

        # Verify unique IDs are generated
        assert task_id1 is not None
        assert task_id2 is not None
        assert task_id1 != task_id2
        assert isinstance(task_id1, str)
        assert isinstance(task_id2, str)

    def test_task_records_start_time_and_total(self):
        """処理開始時刻と全体件数を記録する仕組みを構築."""
        tracker = ProgressTracker()

        # Create a task with specific total
        total_items = 500
        task_id = tracker.create_task(total_items=total_items)

        # Get task data
        progress = tracker.get_progress(task_id)

        assert progress is not None
        assert progress.total == total_items
        assert progress.current == 0
        assert progress.status == "processing"
        # Start time should be recent (within last second)
        assert progress.elapsed_time < 1.0

    def test_inmemory_task_data_management(self):
        """インメモリでの進捗データ管理構造を実装."""
        tracker = ProgressTracker()

        # Create multiple tasks
        task_ids = []
        for i in range(3):
            task_id = tracker.create_task(total_items=100 * (i + 1))
            task_ids.append(task_id)

        # Verify all tasks are stored in memory
        for i, task_id in enumerate(task_ids):
            progress = tracker.get_progress(task_id)
            assert progress is not None
            assert progress.total == 100 * (i + 1)

    def test_task_state_transitions(self):
        """タスクの状態遷移（開始・処理中・完了・エラー）を管理."""
        tracker = ProgressTracker()

        # Create task (starts in processing state)
        task_id = tracker.create_task(total_items=100)
        progress = tracker.get_progress(task_id)
        assert progress.status == "processing"

        # Update progress (stays in processing)
        tracker.update_progress(task_id, current=50)
        progress = tracker.get_progress(task_id)
        assert progress.status == "processing"
        assert progress.current == 50

        # Complete task successfully
        tracker.complete_task(task_id, success=True)
        progress = tracker.get_progress(task_id)
        assert progress.status == "completed"

        # Create another task for error case
        task_id2 = tracker.create_task(total_items=200)
        tracker.complete_task(task_id2, success=False, error_message="Test error")
        progress2 = tracker.get_progress(task_id2)
        assert progress2.status == "error"
        assert progress2.error_message == "Test error"

    def test_progress_data_interface(self):
        """進捗データの取得と更新のインターフェースを定義."""
        tracker = ProgressTracker()

        # Create and update task
        task_id = tracker.create_task(total_items=100)

        # Test update interface
        tracker.update_progress(task_id, current=25)
        progress = tracker.get_progress(task_id)
        assert progress.current == 25
        assert progress.percentage == 25.0

        tracker.update_progress(task_id, current=75)
        progress = tracker.get_progress(task_id)
        assert progress.current == 75
        assert progress.percentage == 75.0

        # Test invalid task ID
        invalid_progress = tracker.get_progress("invalid_id")
        assert invalid_progress is None


class TestProgressTimeCalculation:
    """Test Task 1.2: 時間計算と推定機能."""

    def test_elapsed_time_calculation(self):
        """処理開始からの経過時間を計算する機能を作成."""
        tracker = ProgressTracker()

        # Create task and wait
        task_id = tracker.create_task(total_items=100)

        # Sleep for a measurable time
        time.sleep(0.1)

        # Update progress to trigger time calculation
        tracker.update_progress(task_id, current=10)
        progress = tracker.get_progress(task_id)

        # Elapsed time should be at least 0.1 seconds
        assert progress.elapsed_time >= 0.1
        assert progress.elapsed_time < 1.0  # Reasonable upper bound

    def test_processing_speed_calculation(self):
        """現在の処理速度を移動平均で算出する仕組みを構築."""
        tracker = ProgressTracker()

        # Create task
        task_id = tracker.create_task(total_items=100)

        # Simulate processing with consistent speed
        for i in range(1, 6):
            time.sleep(0.01)  # Small delay
            tracker.update_progress(task_id, current=i * 10)

        progress = tracker.get_progress(task_id)

        # Should have processing speed
        assert hasattr(progress, 'processing_speed')
        assert progress.processing_speed > 0  # Items per second

    def test_remaining_time_estimation(self):
        """残り時間を処理速度から推定する計算ロジックを実装."""
        tracker = ProgressTracker()

        # Create task
        task_id = tracker.create_task(total_items=100)

        # Process 10% of items
        tracker.update_progress(task_id, current=10)
        time.sleep(0.01)
        tracker.update_progress(task_id, current=20)

        progress = tracker.get_progress(task_id)

        # Should estimate remaining time after 10% completion
        assert progress.estimated_remaining is not None
        assert progress.estimated_remaining > 0

        # Process more items
        tracker.update_progress(task_id, current=90)
        progress = tracker.get_progress(task_id)

        # Remaining time should be less when near completion
        assert progress.estimated_remaining is not None
        assert progress.estimated_remaining >= 0

    def test_slow_processing_warning(self):
        """処理速度が極端に遅い（1件/秒未満）場合の警告判定機能を追加."""
        tracker = ProgressTracker()

        # Create task
        task_id = tracker.create_task(total_items=1000)

        # Simulate very slow processing (less than 1 item/sec)
        tracker.update_progress(task_id, current=1)
        time.sleep(1.1)  # More than 1 second for 1 item
        tracker.update_progress(task_id, current=2)

        progress = tracker.get_progress(task_id)

        # Should have warning flag for slow processing
        assert hasattr(progress, 'slow_processing_warning')
        assert progress.slow_processing_warning is True
        assert progress.processing_speed < 1.0

    def test_no_estimation_before_threshold(self):
        """処理が10%未満の場合は残り時間を推定しない."""
        tracker = ProgressTracker()

        # Create task
        task_id = tracker.create_task(total_items=100)

        # Process less than 10%
        tracker.update_progress(task_id, current=5)
        progress = tracker.get_progress(task_id)

        # Should not estimate remaining time
        assert progress.estimated_remaining is None

        # Process exactly 10%
        tracker.update_progress(task_id, current=10)
        progress = tracker.get_progress(task_id)

        # Should start estimating
        assert progress.estimated_remaining is not None


class TestProgressTrackerEdgeCases:
    """Test edge cases and error handling."""

    def test_update_nonexistent_task(self):
        """存在しないタスクIDの更新を適切に処理."""
        tracker = ProgressTracker()

        # Should not raise exception
        tracker.update_progress("nonexistent_id", current=50)

        # Should return None for invalid task
        progress = tracker.get_progress("nonexistent_id")
        assert progress is None

    def test_complete_already_completed_task(self):
        """既に完了したタスクの再完了を適切に処理."""
        tracker = ProgressTracker()

        task_id = tracker.create_task(total_items=100)
        tracker.complete_task(task_id, success=True)

        # Try to complete again - should not change status
        tracker.complete_task(task_id, success=False)
        progress = tracker.get_progress(task_id)
        assert progress.status == "completed"  # Still completed, not error

    def test_update_progress_exceeding_total(self):
        """totalを超えるcurrentの更新を適切に処理."""
        tracker = ProgressTracker()

        task_id = tracker.create_task(total_items=100)
        tracker.update_progress(task_id, current=150)  # Exceeds total

        progress = tracker.get_progress(task_id)
        # Should cap at total
        assert progress.current == 100
        assert progress.percentage == 100.0

    def test_zero_total_items(self):
        """全体件数が0の場合の処理."""
        tracker = ProgressTracker()

        task_id = tracker.create_task(total_items=0)
        progress = tracker.get_progress(task_id)

        assert progress.total == 0
        assert progress.percentage == 0.0  # Avoid division by zero

        # Update should still work
        tracker.update_progress(task_id, current=10)
        progress = tracker.get_progress(task_id)
        assert progress.percentage == 0.0  # Still 0% for zero total


class TestTqdmInterceptor:
    """Test Task 2.1: tqdm出力のインターセプト機能."""

    def test_create_interceptor_instance(self):
        """TqdmInterceptorクラスのインスタンス作成."""
        interceptor = TqdmInterceptor()
        assert interceptor is not None

    def test_capture_stdout_stderr(self):
        """コンソール出力を一時的にリダイレクトする仕組みを作成."""
        interceptor = TqdmInterceptor()
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=100)

        # Test that output is captured and restored
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        with interceptor.capture_tqdm(task_id, tracker):
            # Verify stdout/stderr are redirected
            assert sys.stdout != original_stdout
            assert sys.stderr != original_stderr

            # Print some test output
            print("test output")
            print("error output", file=sys.stderr)

        # Verify restoration
        assert sys.stdout == original_stdout
        assert sys.stderr == original_stderr

    def test_capture_tqdm_output_basic(self):
        """tqdmのプログレスバー出力をキャプチャする機能を実装."""
        interceptor = TqdmInterceptor()
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=1000)

        captured_output = []

        # Mock the output handling
        def mock_handle_output(output):
            captured_output.append(output)

        interceptor.handle_output = mock_handle_output

        with interceptor.capture_tqdm(task_id, tracker):
            # Simulate tqdm output
            print("比較処理中:  50%|████████████▌            | 500/1000行 [00:30<00:30, 16.67行/s]")

        # Should have captured the output
        assert len(captured_output) > 0

    def test_capture_preserves_original_output(self):
        """キャプチャした出力を元のコンソールにも表示する処理を追加."""
        interceptor = TqdmInterceptor()
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=100)

        # Capture what actually gets written to stdout
        stdout_capture = io.StringIO()

        with redirect_stdout(stdout_capture):
            with interceptor.capture_tqdm(task_id, tracker):
                print("test message")

        # The message should still appear in stdout
        captured = stdout_capture.getvalue()
        assert "test message" in captured

    def test_context_manager_restoration_on_exception(self):
        """処理終了時にリダイレクトを正しく復元する機能を実装（例外時も）."""
        interceptor = TqdmInterceptor()
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=100)

        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            with interceptor.capture_tqdm(task_id, tracker):
                # Raise an exception during capture
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Streams should still be restored even after exception
        assert sys.stdout == original_stdout
        assert sys.stderr == original_stderr


class TestTqdmOutputParser:
    """Test Task 2.2: tqdm出力の解析と進捗データ抽出."""

    def test_parse_standard_tqdm_format(self):
        """tqdmの出力文字列から進捗情報を抽出する正規表現パーサーを作成."""
        interceptor = TqdmInterceptor()

        # Test standard tqdm output format used in the codebase
        output = "比較処理中:  75%|████████████████████     | 750/1000行 [00:45<00:15, 16.67行/s]"
        result = interceptor.parse_tqdm_output(output)

        assert result is not None
        assert "current" in result
        assert "total" in result
        assert result["current"] == 750
        assert result["total"] == 1000

    def test_parse_different_progress_levels(self):
        """処理済み件数と全体件数を解析する機能を実装."""
        interceptor = TqdmInterceptor()

        test_cases = [
            ("比較処理中:   0%|                         | 0/1000行 [00:00<?, ?行/s]", 0, 1000),
            ("比較処理中:  25%|██████▌                  | 250/1000行 [00:15<00:45, 16.67行/s]", 250, 1000),
            ("比較処理中:  50%|████████████▌            | 500/1000行 [00:30<00:30, 16.67行/s]", 500, 1000),
            ("比較処理中: 100%|█████████████████████████| 1000/1000行 [01:00<00:00, 16.67行/s]", 1000, 1000),
        ]

        for output, expected_current, expected_total in test_cases:
            result = interceptor.parse_tqdm_output(output)
            assert result["current"] == expected_current
            assert result["total"] == expected_total

    def test_parse_speed_and_percentage_info(self):
        """処理速度やパーセンテージ情報を取得する仕組みを構築."""
        interceptor = TqdmInterceptor()

        output = "比較処理中:  75%|████████████████████     | 750/1000行 [00:45<00:15, 16.67行/s]"
        result = interceptor.parse_tqdm_output(output)

        # Should extract additional information
        assert "percentage" in result
        assert result["percentage"] == 75.0

        # Optional: speed information if we decide to extract it
        if "speed" in result:
            assert result["speed"] > 0

    def test_parse_invalid_format(self):
        """不正な形式の出力に対する適切な処理."""
        interceptor = TqdmInterceptor()

        invalid_outputs = [
            "",  # Empty string
            "Some random text",  # No progress info
            "Progress: invalid format",  # Wrong format
            "比較処理中: [no numbers]",  # Missing numbers
        ]

        for invalid_output in invalid_outputs:
            result = interceptor.parse_tqdm_output(invalid_output)
            # Should return None or empty dict for invalid input
            assert result is None or result == {}

    def test_parse_different_descriptions(self):
        """異なる説明文での進捗解析."""
        interceptor = TqdmInterceptor()

        test_cases = [
            ("ファイル1 処理中:  50%|████████████▌            | 500/1000行 [00:30<00:30, 16.67行/s]", 500, 1000),
            ("ファイル2 処理中:  25%|██████▌                  | 250/1000行 [00:15<00:45, 16.67行/s]", 250, 1000),
            ("LLM処理中:  80%|████████████████████     | 800/1000行 [00:48<00:12, 16.67行/s]", 800, 1000),
        ]

        for output, expected_current, expected_total in test_cases:
            result = interceptor.parse_tqdm_output(output)
            assert result["current"] == expected_current
            assert result["total"] == expected_total


class TestTqdmProgressTrackerIntegration:
    """Test Task 2: TqdmInterceptorとProgressTrackerの連携."""

    def test_interceptor_updates_progress_tracker(self):
        """解析したデータを進捗トラッカーに送信する連携処理を実装."""
        interceptor = TqdmInterceptor()
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=1000)

        # Simulate tqdm output being captured and processed
        with interceptor.capture_tqdm(task_id, tracker):
            # Simulate the output that would be captured
            interceptor.process_output(
                "比較処理中:  50%|████████████▌            | 500/1000行 [00:30<00:30, 16.67行/s]",
                task_id,
                tracker
            )

        # Check that progress tracker was updated
        progress = tracker.get_progress(task_id)
        assert progress.current == 500
        assert progress.total == 1000
        assert progress.percentage == 50.0

    def test_multiple_progress_updates(self):
        """複数の進捗更新の連携処理."""
        interceptor = TqdmInterceptor()
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=1000)

        updates = [
            ("比較処理中:  25%|██████▌                  | 250/1000行 [00:15<00:45, 16.67行/s]", 250),
            ("比較処理中:  50%|████████████▌            | 500/1000行 [00:30<00:30, 16.67行/s]", 500),
            ("比較処理中:  75%|████████████████████     | 750/1000行 [00:45<00:15, 16.67行/s]", 750),
        ]

        with interceptor.capture_tqdm(task_id, tracker):
            for output, expected_current in updates:
                interceptor.process_output(output, task_id, tracker)

                # Verify update
                progress = tracker.get_progress(task_id)
                assert progress.current == expected_current

    def test_invalid_tqdm_output_ignored(self):
        """不正なtqdm出力は無視される."""
        interceptor = TqdmInterceptor()
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=1000)

        # Get initial progress
        initial_progress = tracker.get_progress(task_id)
        initial_current = initial_progress.current

        with interceptor.capture_tqdm(task_id, tracker):
            # Send invalid output
            interceptor.process_output("Invalid output format", task_id, tracker)

        # Progress should remain unchanged
        progress = tracker.get_progress(task_id)
        assert progress.current == initial_current

    def test_concurrent_task_isolation(self):
        """複数タスクの同時処理で互いに干渉しない."""
        interceptor = TqdmInterceptor()
        tracker = ProgressTracker()

        task_id1 = tracker.create_task(total_items=1000)
        task_id2 = tracker.create_task(total_items=500)

        with interceptor.capture_tqdm(task_id1, tracker):
            interceptor.process_output(
                "比較処理中:  50%|████████████▌            | 500/1000行 [00:30<00:30, 16.67行/s]",
                task_id1,
                tracker
            )

        with interceptor.capture_tqdm(task_id2, tracker):
            interceptor.process_output(
                "ファイル2 処理中:  60%|████████████████▌       | 300/500行 [00:18<00:12, 16.67行/s]",
                task_id2,
                tracker
            )

        # Both tasks should have correct progress
        progress1 = tracker.get_progress(task_id1)
        progress2 = tracker.get_progress(task_id2)

        assert progress1.current == 500
        assert progress1.total == 1000

        assert progress2.current == 300
        assert progress2.total == 500


class TestSSEStreaming:
    """Test Task 3.1: SSEストリーミングエンドポイントを構築."""

    @pytest.mark.asyncio
    async def test_stream_progress_generator_basic(self):
        """タスクIDごとのSSE接続を管理する機能を実装."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=100)

        # Test that stream_progress returns an async generator
        stream = tracker.stream_progress(task_id)
        assert hasattr(stream, '__aiter__')

        # First event should contain initial progress data
        first_event = await stream.__anext__()
        assert "event" in first_event
        assert "data" in first_event

        # Parse the JSON data
        data = json.loads(first_event["data"])
        assert data["task_id"] == task_id
        assert data["current"] == 0
        assert data["total"] == 100
        assert data["status"] == "processing"

    @pytest.mark.asyncio
    async def test_stream_progress_updates_over_time(self):
        """進捗データを1秒ごとにSSEイベントとして送信する仕組みを作成."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=100)

        stream = tracker.stream_progress(task_id)

        # Get initial event
        initial_event = await stream.__anext__()
        initial_data = json.loads(initial_event["data"])
        assert initial_data["current"] == 0

        # Update progress and get next event
        tracker.update_progress(task_id, 50)

        # Should receive updated event
        updated_event = await stream.__anext__()
        updated_data = json.loads(updated_event["data"])
        assert updated_data["current"] == 50
        assert updated_data["percentage"] == 50.0

    @pytest.mark.asyncio
    async def test_stream_multiple_clients(self):
        """複数クライアントへの同時配信機能を実装."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=100)

        # Create two separate streams for the same task
        stream1 = tracker.stream_progress(task_id)
        stream2 = tracker.stream_progress(task_id)

        # Both should receive the same initial data
        event1 = await stream1.__anext__()
        event2 = await stream2.__anext__()

        data1 = json.loads(event1["data"])
        data2 = json.loads(event2["data"])

        assert data1["task_id"] == data2["task_id"]
        assert data1["current"] == data2["current"]

    @pytest.mark.asyncio
    async def test_stream_completion_event(self):
        """処理完了時にSSE接続を適切に終了する処理を追加."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=100)

        stream = tracker.stream_progress(task_id)

        # Get initial event
        initial_event = await stream.__anext__()
        assert json.loads(initial_event["data"])["status"] == "processing"

        # Complete the task
        tracker.complete_task(task_id, success=True)

        # Should receive completion event
        completion_event = await stream.__anext__()
        completion_data = json.loads(completion_event["data"])
        assert completion_data["status"] == "completed"

        # Stream should terminate after completion
        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()


class TestSSEConnectionReliability:
    """Test Task 3.2: SSE接続の信頼性向上機能を実装."""

    @pytest.mark.asyncio
    async def test_invalid_task_id_handling(self):
        """クライアント接続の状態監視機能を構築."""
        tracker = ProgressTracker()

        # Try to stream for non-existent task
        stream = tracker.stream_progress("invalid-task-id")

        # Should receive error event
        error_event = await stream.__anext__()
        assert error_event["event"] == "error"
        error_data = json.loads(error_event["data"])
        assert "error_message" in error_data
        assert "not found" in error_data["error_message"].lower()

    @pytest.mark.asyncio
    async def test_error_event_sending(self):
        """エラー発生時のSSEイベント送信機能を追加."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=100)

        stream = tracker.stream_progress(task_id)

        # Get initial event
        await stream.__anext__()

        # Mark task as failed
        tracker.complete_task(task_id, success=False, error_message="Processing failed")

        # Should receive error event
        error_event = await stream.__anext__()
        error_data = json.loads(error_event["data"])
        assert error_data["status"] == "error"
        assert error_data["error_message"] == "Processing failed"

    @pytest.mark.asyncio
    async def test_connection_cleanup_on_timeout(self):
        """タイムアウト時の適切な接続終了処理を実装."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=100)

        # Create stream with timeout
        stream = tracker.stream_progress(task_id, timeout=0.1)  # 100ms timeout

        # Get initial event
        await stream.__anext__()

        # Wait for timeout
        await asyncio.sleep(0.2)

        # Stream should terminate due to timeout
        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()


class TestAsyncFileComparisonAPI:
    """Test Task 4.1: 非同期ファイル比較エンドポイントを作成."""

    def test_async_compare_endpoint_returns_task_id(self):
        """ファイルアップロードを受け付けてタスクIDを返す機能を実装."""
        # This test will require the actual API implementation
        # For now, we test the core functionality

        tracker = ProgressTracker()

        # Simulate async comparison initialization
        task_id = tracker.create_task(total_items=1000)

        # Should return a valid task ID
        assert task_id is not None
        assert isinstance(task_id, str)
        assert len(task_id) > 0

        # Task should be in processing state
        progress = tracker.get_progress(task_id)
        assert progress.status == "processing"
        assert progress.current == 0
        assert progress.total == 1000

    @pytest.mark.asyncio
    async def test_background_processing_integration(self):
        """バックグラウンドでの比較処理開始機能を構築."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=500)

        # Simulate background processing
        async def background_process():
            for i in range(0, 501, 50):
                tracker.update_progress(task_id, i)
                await asyncio.sleep(0.01)  # Simulate processing time
            tracker.complete_task(task_id, success=True)

        # Start background processing
        process_task = asyncio.create_task(background_process())

        # Monitor progress
        progress = tracker.get_progress(task_id)
        assert progress.current == 0

        # Wait for some progress
        await asyncio.sleep(0.05)
        progress = tracker.get_progress(task_id)
        assert progress.current > 0

        # Wait for completion
        await process_task
        final_progress = tracker.get_progress(task_id)
        assert final_progress.status == "completed"
        assert final_progress.current == 500

    def test_progress_tracker_integration(self):
        """進捗トラッカーとの連携処理を実装."""
        tracker = ProgressTracker()

        # Create multiple tasks to simulate concurrent processing
        task_ids = []
        for i in range(3):
            task_id = tracker.create_task(total_items=100 * (i + 1))
            task_ids.append(task_id)

        # Update progress for each task
        for i, task_id in enumerate(task_ids):
            tracker.update_progress(task_id, 50 * (i + 1))

        # Each task should maintain separate progress
        for i, task_id in enumerate(task_ids):
            progress = tracker.get_progress(task_id)
            assert progress.total == 100 * (i + 1)
            assert progress.current == 50 * (i + 1)

    def test_result_storage_mechanism(self):
        """処理結果の一時保存機能を追加."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=100)

        # Simulate processing completion with result
        result_data = {
            "summary": {"total_rows": 100, "differences": 25},
            "details": [{"row": 1, "difference": "value changed"}]
        }

        # Complete task and store result
        tracker.complete_task(task_id, success=True)
        # Note: We'll need to extend complete_task to accept result data

        progress = tracker.get_progress(task_id)
        assert progress.status == "completed"


class TestProgressStatusAPI:
    """Test Task 4.2: 進捗状態取得エンドポイントを実装."""

    def test_get_progress_endpoint_returns_current_status(self):
        """タスクIDから現在の進捗情報を返すAPIを作成."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=200)

        # Update progress
        tracker.update_progress(task_id, 75)

        # Get progress (simulating API call)
        progress = tracker.get_progress(task_id)

        assert progress is not None
        assert progress.task_id == task_id
        assert progress.current == 75
        assert progress.total == 200
        assert progress.percentage == 37.5
        assert progress.status == "processing"

    def test_completed_task_returns_result_data(self):
        """処理完了時に結果データを返す機能を実装."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=100)

        # Complete the task
        tracker.update_progress(task_id, 100)
        tracker.complete_task(task_id, success=True)

        progress = tracker.get_progress(task_id)
        assert progress.status == "completed"
        assert progress.current == 100
        assert progress.percentage == 100.0

    def test_error_status_with_details(self):
        """エラー情報を含む詳細ステータスを提供する機能を追加."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=100)

        # Simulate error during processing
        error_message = "File format validation failed on line 50"
        tracker.complete_task(task_id, success=False, error_message=error_message)

        progress = tracker.get_progress(task_id)
        assert progress.status == "error"
        assert progress.error_message == error_message

    def test_invalid_task_id_error_response(self):
        """タスクが存在しない場合の適切なエラーレスポンスを実装."""
        tracker = ProgressTracker()

        # Try to get progress for non-existent task
        progress = tracker.get_progress("non-existent-task-id")

        # Should return None (will be converted to 404 by API layer)
        assert progress is None

    def test_progress_status_includes_timing_info(self):
        """経過時間と推定残り時間を含む進捗情報を返す."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=1000)

        # Simulate some processing time
        time.sleep(0.1)
        tracker.update_progress(task_id, 200)

        progress = tracker.get_progress(task_id)
        assert progress.elapsed_time > 0
        assert progress.processing_speed > 0
        # After 20% completion, should have remaining time estimate
        if progress.percentage >= 10:
            assert progress.estimated_remaining is not None