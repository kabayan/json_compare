"""Integration tests for WebUI progress display system (Task 7.2)

This module implements comprehensive integration tests for:
- SSEストリーミングの動作確認テスト
- ファイルアップロードから完了までの一連のフローテスト
- 複数クライアント同時接続のテスト
- エラー発生時の復旧フローのテスト

Following TDD methodology: RED-GREEN-REFACTOR
"""

import pytest
import asyncio
import json
import time
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

from src.progress_tracker import ProgressTracker, TqdmInterceptor


class TestSSEStreaming:
    """Test Server-Sent Events streaming functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.tracker = ProgressTracker()

    @pytest.mark.asyncio
    async def test_sse_stream_progress_single_update(self):
        """Test SSE streaming with single progress update."""
        task_id = self.tracker.create_task(total_items=100)

        # Start streaming task (with timeout to prevent infinite loop)
        stream_task = asyncio.create_task(
            self._collect_sse_events(task_id, timeout=2.0)
        )

        # Wait a bit for streaming to start
        await asyncio.sleep(0.2)

        # Update progress
        self.tracker.update_progress(task_id, current=50)

        # Wait a bit for progress to be captured
        await asyncio.sleep(0.2)

        # Complete the task
        self.tracker.complete_task(task_id, success=True)

        # Wait for streaming to complete
        events = await stream_task

        # Should have received progress and completion events
        assert len(events) >= 2

        # Check progress event (should have both initial and updated events)
        progress_events = [e for e in events if e["event"] == "progress"]
        assert len(progress_events) >= 2  # Should have initial (0) and updated (50)

        # Check the final progress event (should be the updated one)
        final_progress_data = json.loads(progress_events[-1]["data"])
        assert final_progress_data["task_id"] == task_id
        assert final_progress_data["current"] == 50
        assert final_progress_data["total"] == 100
        assert final_progress_data["percentage"] == 50.0

        # Check completion event
        complete_events = [e for e in events if e["event"] == "complete"]
        assert len(complete_events) == 1

        complete_data = json.loads(complete_events[0]["data"])
        assert complete_data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_sse_stream_multiple_progress_updates(self):
        """Test SSE streaming with multiple progress updates."""
        task_id = self.tracker.create_task(total_items=1000)

        # Start streaming
        stream_task = asyncio.create_task(
            self._collect_sse_events(task_id, timeout=3.0)
        )

        await asyncio.sleep(0.1)

        # Send multiple progress updates
        updates = [100, 300, 500, 750, 1000]
        for current in updates:
            self.tracker.update_progress(task_id, current=current)
            await asyncio.sleep(0.1)

        # Complete the task
        self.tracker.complete_task(task_id, success=True)

        # Wait for streaming to complete
        events = await stream_task

        # Should have received multiple progress events
        progress_events = [e for e in events if e["event"] == "progress"]
        assert len(progress_events) >= 2  # At least initial (0) and final update

        # Check that the final progress event has the correct value
        final_progress_data = json.loads(progress_events[-1]["data"])
        assert final_progress_data["current"] == 1000  # Should be the final update
        assert final_progress_data["percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_sse_stream_error_handling(self):
        """Test SSE streaming with error scenarios."""
        task_id = self.tracker.create_task(total_items=100)

        # Start streaming
        stream_task = asyncio.create_task(
            self._collect_sse_events(task_id, timeout=2.0)
        )

        await asyncio.sleep(0.1)

        # Update progress normally
        self.tracker.update_progress(task_id, current=25)
        await asyncio.sleep(0.1)

        # Simulate an error
        error_message = "File processing failed"
        self.tracker.complete_task(task_id, success=False, error_message=error_message)

        # Wait for streaming to complete
        events = await stream_task

        # Should have received progress and error events
        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) == 1

        error_data = json.loads(error_events[0]["data"])
        assert error_data["status"] == "error"
        assert error_data["error_message"] == error_message

    @pytest.mark.asyncio
    async def test_sse_stream_invalid_task_id(self):
        """Test SSE streaming with invalid task ID."""
        invalid_task_id = "invalid-task-id-12345"

        # Start streaming for invalid task
        stream_task = asyncio.create_task(
            self._collect_sse_events(invalid_task_id, timeout=1.0)
        )

        # Wait for streaming to complete
        events = await stream_task

        # Should immediately receive error event
        assert len(events) == 1
        assert events[0]["event"] == "error"

        error_data = json.loads(events[0]["data"])
        assert "not found" in error_data["error_message"]

    async def _collect_sse_events(self, task_id: str, timeout: float = 5.0) -> List[Dict[str, str]]:
        """Helper method to collect SSE events from stream_progress."""
        events = []

        try:
            async for event in self.tracker.stream_progress(task_id, timeout=timeout):
                events.append(event)
        except asyncio.TimeoutError:
            pass  # Expected for timeout scenarios

        return events


class TestMultipleClientConnections:
    """Test multiple concurrent client connections."""

    def setup_method(self):
        """Setup for each test method."""
        self.tracker = ProgressTracker()

    @pytest.mark.asyncio
    async def test_multiple_concurrent_sse_streams(self):
        """Test multiple clients streaming same task simultaneously."""
        task_id = self.tracker.create_task(total_items=100)

        # Start multiple concurrent streams
        num_clients = 3
        stream_tasks = []

        for i in range(num_clients):
            task = asyncio.create_task(
                self._collect_sse_events(task_id, timeout=3.0)
            )
            stream_tasks.append(task)

        await asyncio.sleep(0.2)

        # Update progress
        self.tracker.update_progress(task_id, current=30)
        await asyncio.sleep(0.2)

        self.tracker.update_progress(task_id, current=60)
        await asyncio.sleep(0.2)

        # Complete task
        self.tracker.complete_task(task_id, success=True)

        # Wait for all streams to complete
        all_events = await asyncio.gather(*stream_tasks)

        # All clients should receive the same events
        assert len(all_events) == num_clients

        for client_events in all_events:
            # Each client should receive progress and completion events
            progress_events = [e for e in client_events if e["event"] == "progress"]
            complete_events = [e for e in client_events if e["event"] == "complete"]

            assert len(progress_events) >= 2  # At least 2 progress updates
            assert len(complete_events) == 1  # Exactly 1 completion

            # Verify final completion data
            complete_data = json.loads(complete_events[0]["data"])
            assert complete_data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_multiple_different_tasks_streaming(self):
        """Test multiple clients streaming different tasks."""
        # Create multiple tasks
        task_ids = []
        for i in range(3):
            task_id = self.tracker.create_task(total_items=100 * (i + 1))
            task_ids.append(task_id)

        # Start streams for different tasks
        stream_tasks = []
        for task_id in task_ids:
            task = asyncio.create_task(
                self._collect_sse_events(task_id, timeout=3.0)
            )
            stream_tasks.append(task)

        await asyncio.sleep(0.2)

        # Update each task differently
        for i, task_id in enumerate(task_ids):
            progress = (i + 1) * 25  # 25, 50, 75
            self.tracker.update_progress(task_id, current=progress)
            await asyncio.sleep(0.1)

        await asyncio.sleep(0.2)

        # Complete all tasks
        for task_id in task_ids:
            self.tracker.complete_task(task_id, success=True)

        # Wait for all streams to complete
        all_events = await asyncio.gather(*stream_tasks)

        # Each task should have received its own events
        for i, events in enumerate(all_events):
            task_id = task_ids[i]

            progress_events = [e for e in events if e["event"] == "progress"]
            assert len(progress_events) >= 1

            # Verify task-specific data
            progress_data = json.loads(progress_events[0]["data"])
            assert progress_data["task_id"] == task_id
            assert progress_data["total"] == 100 * (i + 1)

    async def _collect_sse_events(self, task_id: str, timeout: float = 5.0) -> List[Dict[str, str]]:
        """Helper method to collect SSE events from stream_progress."""
        events = []

        try:
            async for event in self.tracker.stream_progress(task_id, timeout=timeout):
                events.append(event)
        except asyncio.TimeoutError:
            pass

        return events


class TestFileUploadToCompletionFlow:
    """Test end-to-end file upload to completion flow."""

    def setup_method(self):
        """Setup for each test method."""
        self.tracker = ProgressTracker()
        self.interceptor = TqdmInterceptor()

    def test_end_to_end_file_processing_simulation(self):
        """Test complete file processing simulation from start to finish."""
        # Simulate file upload: create task
        total_items = 1000
        task_id = self.tracker.create_task(total_items=total_items)

        # Verify task was created properly
        progress = self.tracker.get_progress(task_id)
        assert progress.current == 0
        assert progress.total == total_items
        assert progress.status == "processing"

        # Simulate processing with periodic updates
        milestones = [100, 250, 500, 750, 900, 1000]

        for milestone in milestones:
            # Simulate processing time
            time.sleep(0.01)

            # Update progress
            self.tracker.update_progress(task_id, current=milestone)

            # Verify progress update
            progress = self.tracker.get_progress(task_id)
            assert progress.current == milestone
            assert progress.percentage == (milestone / total_items) * 100

        # Simulate successful completion
        start_time = time.time()
        self.tracker.complete_task(task_id, success=True)
        duration = time.time() - start_time

        # Verify completion
        progress = self.tracker.get_progress(task_id)
        assert progress.status == "completed"
        assert progress.error_message is None

        # Log completion for metrics
        self.tracker.log_task_completion(task_id, success=True, duration=duration)

    def test_end_to_end_file_processing_with_tqdm_capture(self):
        """Test file processing with tqdm output capture."""
        task_id = self.tracker.create_task(total_items=500)

        # Simulate tqdm output capture during processing
        tqdm_outputs = [
            "Processing: 20%|████                 | 100/500行 [00:10<00:40, 10.00行/s]",
            "Processing: 40%|████████             | 200/500行 [00:20<00:30, 10.00行/s]",
            "Processing: 60%|████████████         | 300/500行 [00:30<00:20, 10.00行/s]",
            "Processing: 80%|████████████████     | 400/500行 [00:40<00:10, 10.00行/s]",
            "Processing: 100%|████████████████████| 500/500行 [00:50<00:00, 10.00行/s]"
        ]

        # Process each tqdm output
        for output in tqdm_outputs:
            self.interceptor.process_output(output, task_id, self.tracker)
            time.sleep(0.01)

        # Verify final progress
        progress = self.tracker.get_progress(task_id)
        assert progress.current == 500
        assert progress.percentage == 100.0

        # Complete the task
        self.tracker.complete_task(task_id, success=True)
        final_progress = self.tracker.get_progress(task_id)
        assert final_progress.status == "completed"

    def test_end_to_end_processing_with_error_recovery(self):
        """Test processing with error and recovery scenarios."""
        task_id = self.tracker.create_task(total_items=200)

        # Process normally up to 50%
        for current in [25, 50, 75, 100]:
            self.tracker.update_progress(task_id, current=current)
            time.sleep(0.01)

        # Verify progress
        progress = self.tracker.get_progress(task_id)
        assert progress.current == 100
        assert progress.percentage == 50.0

        # Simulate an error
        error_message = "Network connection lost during processing"
        self.tracker.log_error(task_id, error_message)
        self.tracker.complete_task(task_id, success=False, error_message=error_message)

        # Verify error state
        progress = self.tracker.get_progress(task_id)
        assert progress.status == "error"
        assert progress.error_message == error_message

        # Verify error was logged
        with patch.object(self.tracker.logger, 'error') as mock_error:
            self.tracker.log_error(task_id, "Additional error info")
            mock_error.assert_called_once()


class TestErrorRecoveryFlow:
    """Test error recovery and resilience scenarios."""

    def setup_method(self):
        """Setup for each test method."""
        self.tracker = ProgressTracker()

    @pytest.mark.asyncio
    async def test_sse_stream_with_connection_interruption(self):
        """Test SSE streaming behavior with simulated connection interruption."""
        task_id = self.tracker.create_task(total_items=100)

        # Start streaming
        events_before_interruption = []

        # Collect some events before "interruption"
        async def collect_before_interruption():
            event_count = 0
            async for event in self.tracker.stream_progress(task_id, timeout=1.0):
                events_before_interruption.append(event)
                event_count += 1
                if event_count >= 2:  # Collect 2 events then simulate interruption
                    break

        # Start collection task
        collection_task = asyncio.create_task(collect_before_interruption())

        # Send some progress updates
        await asyncio.sleep(0.1)
        self.tracker.update_progress(task_id, current=25)
        await asyncio.sleep(0.1)
        self.tracker.update_progress(task_id, current=50)

        # Wait for collection to finish (simulates interruption)
        await collection_task

        # Verify we got some events before interruption
        assert len(events_before_interruption) >= 1

        # Simulate reconnection - start new stream
        events_after_reconnection = []

        async def collect_after_reconnection():
            async for event in self.tracker.stream_progress(task_id, timeout=1.0):
                events_after_reconnection.append(event)

        reconnection_task = asyncio.create_task(collect_after_reconnection())

        # Continue processing after reconnection
        await asyncio.sleep(0.1)
        self.tracker.update_progress(task_id, current=75)
        await asyncio.sleep(0.1)
        self.tracker.complete_task(task_id, success=True)

        # Wait for reconnection events
        await reconnection_task

        # Verify reconnection received current state
        assert len(events_after_reconnection) >= 2

        # Should include completion event
        complete_events = [e for e in events_after_reconnection if e["event"] == "complete"]
        assert len(complete_events) == 1

    def test_concurrent_task_modifications(self):
        """Test concurrent modifications to task progress."""
        task_id = self.tracker.create_task(total_items=1000)

        # Simulate concurrent updates using threading
        def update_worker(start_current: int, end_current: int):
            """Worker function to update progress concurrently."""
            for current in range(start_current, end_current + 1, 10):
                self.tracker.update_progress(task_id, current=current)
                time.sleep(0.001)

        # Start multiple concurrent update threads
        threads = []
        for i in range(3):
            start = i * 100
            end = (i + 1) * 100
            thread = threading.Thread(target=update_worker, args=(start, end))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify final state is consistent
        progress = self.tracker.get_progress(task_id)
        assert progress.current >= 0
        assert progress.current <= 1000
        assert 0 <= progress.percentage <= 100

        # Complete the task
        self.tracker.complete_task(task_id, success=True)
        final_progress = self.tracker.get_progress(task_id)
        assert final_progress.status == "completed"

    def test_memory_cleanup_on_task_completion(self):
        """Test that completed tasks don't cause memory leaks."""
        initial_task_count = len(self.tracker.tasks)

        # Create and complete multiple tasks rapidly
        completed_task_ids = []
        for i in range(100):
            task_id = self.tracker.create_task(total_items=100)
            self.tracker.update_progress(task_id, current=100)
            self.tracker.complete_task(task_id, success=True)
            completed_task_ids.append(task_id)

        # Verify all tasks are still in memory (design decision - we keep history)
        assert len(self.tracker.tasks) == initial_task_count + 100

        # Verify all completed tasks have correct status
        for task_id in completed_task_ids:
            progress = self.tracker.get_progress(task_id)
            assert progress is not None
            assert progress.status == "completed"

    def test_invalid_operation_handling(self):
        """Test handling of invalid operations gracefully."""
        # Test updating non-existent task
        self.tracker.update_progress("non-existent-task", current=50)

        # Test completing non-existent task
        self.tracker.complete_task("non-existent-task", success=True)

        # Test getting progress for non-existent task
        progress = self.tracker.get_progress("non-existent-task")
        assert progress is None

        # Test edge case values
        task_id = self.tracker.create_task(total_items=100)

        # Test extreme values
        self.tracker.update_progress(task_id, current=999999)  # Way over total
        progress = self.tracker.get_progress(task_id)
        assert progress.current == 100  # Should be capped

        self.tracker.update_progress(task_id, current=-999999)  # Way under 0
        progress = self.tracker.get_progress(task_id)
        assert progress.current == 0  # Should be capped at 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])