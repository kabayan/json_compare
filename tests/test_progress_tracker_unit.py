"""Unit tests for ProgressTracker backend functionality (Task 7.1)

This module implements comprehensive unit tests for:
- ProgressTracker各メソッドのテスト
- tqdm出力パーサーの正確性テスト
- 時間計算と推定ロジックのテスト
- エラーハンドリングのテストケース

Following TDD methodology: RED-GREEN-REFACTOR
"""

import pytest
import time
import uuid
import json
import asyncio
import logging
import tempfile
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.progress_tracker import (
    ProgressTracker,
    ProgressData,
    TaskData,
    TqdmInterceptor,
    TqdmCaptureStream
)


class TestProgressTrackerCore:
    """Test core ProgressTracker functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.tracker = ProgressTracker()

    def test_create_task_should_return_valid_task_id(self):
        """Test that create_task returns a valid UUID task ID."""
        task_id = self.tracker.create_task(total_items=100)

        # Task ID should be a valid UUID string
        assert isinstance(task_id, str)
        assert len(task_id) == 36  # UUID format: 8-4-4-4-12
        assert task_id.count('-') == 4

        # Should be able to parse as UUID
        parsed_uuid = uuid.UUID(task_id)
        assert str(parsed_uuid) == task_id

    def test_create_task_should_store_task_data(self):
        """Test that create_task properly stores task data."""
        total_items = 500
        task_id = self.tracker.create_task(total_items=total_items)

        # Task should exist in tracker
        assert task_id in self.tracker.tasks

        # Task data should be correct
        task = self.tracker.tasks[task_id]
        assert task.task_id == task_id
        assert task.total_items == total_items
        assert task.current_items == 0
        assert task.status == "processing"
        assert isinstance(task.created_at, datetime)

    def test_update_progress_with_valid_task_id(self):
        """Test updating progress with valid task ID."""
        task_id = self.tracker.create_task(total_items=100)

        # Update progress
        self.tracker.update_progress(task_id, current=25)

        # Check task was updated
        task = self.tracker.tasks[task_id]
        assert task.current_items == 25
        assert len(task.update_times) == 1
        assert len(task.update_counts) == 1

    def test_update_progress_with_invalid_task_id(self):
        """Test updating progress with invalid task ID should not raise error."""
        # Should not raise exception
        self.tracker.update_progress("invalid-task-id", current=50)

        # No tasks should be created
        assert len(self.tracker.tasks) == 0

    def test_update_progress_caps_current_at_total(self):
        """Test that current progress is capped at total."""
        task_id = self.tracker.create_task(total_items=100)

        # Try to update beyond total
        self.tracker.update_progress(task_id, current=150)

        # Should be capped at total
        task = self.tracker.tasks[task_id]
        assert task.current_items == 100

    def test_update_progress_ignores_completed_tasks(self):
        """Test that progress updates are ignored for completed tasks."""
        task_id = self.tracker.create_task(total_items=100)
        self.tracker.complete_task(task_id, success=True)

        # Try to update completed task
        self.tracker.update_progress(task_id, current=50)

        # Should remain at 0 (not updated)
        task = self.tracker.tasks[task_id]
        assert task.current_items == 0
        assert task.status == "completed"

    def test_get_progress_with_valid_task_id(self):
        """Test getting progress data with valid task ID."""
        task_id = self.tracker.create_task(total_items=200)
        self.tracker.update_progress(task_id, current=50)

        progress = self.tracker.get_progress(task_id)

        assert progress is not None
        assert isinstance(progress, ProgressData)
        assert progress.task_id == task_id
        assert progress.total == 200
        assert progress.current == 50
        assert progress.percentage == 25.0  # 50/200 * 100
        assert progress.status == "processing"

    def test_get_progress_with_invalid_task_id(self):
        """Test getting progress with invalid task ID returns None."""
        progress = self.tracker.get_progress("invalid-task-id")
        assert progress is None

    def test_complete_task_success(self):
        """Test marking task as successfully completed."""
        task_id = self.tracker.create_task(total_items=100)

        self.tracker.complete_task(task_id, success=True)

        task = self.tracker.tasks[task_id]
        assert task.status == "completed"
        assert task.error is None

    def test_complete_task_failure(self):
        """Test marking task as failed with error message."""
        task_id = self.tracker.create_task(total_items=100)
        error_message = "Processing failed due to invalid data"

        self.tracker.complete_task(task_id, success=False, error_message=error_message)

        task = self.tracker.tasks[task_id]
        assert task.status == "error"
        assert task.error == error_message

    def test_complete_task_ignores_invalid_task_id(self):
        """Test completing invalid task ID should not raise error."""
        # Should not raise exception
        self.tracker.complete_task("invalid-task-id", success=True)

        # No tasks should be created
        assert len(self.tracker.tasks) == 0


class TestProgressTrackerTimeCalculations:
    """Test time calculation and estimation logic."""

    def setup_method(self):
        """Setup for each test method."""
        self.tracker = ProgressTracker()

    def test_elapsed_time_calculation(self):
        """Test elapsed time calculation."""
        task_id = self.tracker.create_task(total_items=100)

        # Get initial start time
        start_time = self.tracker.tasks[task_id].start_time

        # Simulate some time passing
        time.sleep(0.1)

        progress = self.tracker.get_progress(task_id)
        assert progress.elapsed_time >= 0.1
        assert progress.elapsed_time < 1.0  # Should be reasonable

    def test_processing_speed_calculation_with_history(self):
        """Test processing speed calculation using speed history."""
        task_id = self.tracker.create_task(total_items=1000)

        # Simulate progress updates with time gaps
        with patch('time.time') as mock_time:
            mock_time.side_effect = [100.0, 101.0, 102.0, 103.0]  # 1 second intervals

            self.tracker.update_progress(task_id, current=10)  # t=100
            mock_time.return_value = 101.0
            self.tracker.update_progress(task_id, current=20)  # t=101, speed=10/s
            mock_time.return_value = 102.0
            self.tracker.update_progress(task_id, current=35)  # t=102, speed=15/s

            progress = self.tracker.get_progress(task_id)
            # Average speed should be (10+15)/2 = 12.5
            assert abs(progress.processing_speed - 12.5) < 0.1

    def test_processing_speed_fallback_calculation(self):
        """Test processing speed fallback to overall average."""
        task_id = self.tracker.create_task(total_items=100)

        with patch('time.time') as mock_time:
            # Set start time and current time
            start_time = 100.0
            current_time = 110.0  # 10 seconds later

            # Set start time in task
            self.tracker.tasks[task_id].start_time = start_time
            mock_time.return_value = current_time

            # Update progress (no speed history yet)
            self.tracker.update_progress(task_id, current=50)

            progress = self.tracker.get_progress(task_id)
            # Speed should be 50 items / 10 seconds = 5.0 items/s
            assert abs(progress.processing_speed - 5.0) < 0.1

    def test_estimated_remaining_time_calculation(self):
        """Test estimated remaining time calculation."""
        task_id = self.tracker.create_task(total_items=100)

        with patch('time.time') as mock_time:
            mock_time.side_effect = [100.0, 101.0, 102.0]

            # Progress to 10% (minimum for estimation)
            self.tracker.update_progress(task_id, current=10)  # t=100
            mock_time.return_value = 101.0
            self.tracker.update_progress(task_id, current=20)  # t=101, speed=10/s

            progress = self.tracker.get_progress(task_id)

            # Remaining items: 80, Speed: 10/s, Estimated time: 8s
            assert progress.estimated_remaining is not None
            assert abs(progress.estimated_remaining - 8.0) < 0.1

    def test_estimated_remaining_time_insufficient_progress(self):
        """Test that estimation requires at least 10% progress."""
        task_id = self.tracker.create_task(total_items=1000)

        # Only 5% progress (50/1000)
        self.tracker.update_progress(task_id, current=50)

        progress = self.tracker.get_progress(task_id)
        assert progress.estimated_remaining is None

    def test_slow_processing_warning(self):
        """Test slow processing warning detection."""
        task_id = self.tracker.create_task(total_items=100)

        with patch('time.time') as mock_time:
            mock_time.side_effect = [100.0, 102.0, 104.5]  # Slow updates

            self.tracker.update_progress(task_id, current=1)   # t=100
            mock_time.return_value = 102.0
            self.tracker.update_progress(task_id, current=2)   # t=102, speed=0.5/s (slow)

            progress = self.tracker.get_progress(task_id)
            assert progress.slow_processing_warning is True

    def test_normal_processing_speed_no_warning(self):
        """Test that normal processing speed doesn't trigger warning."""
        task_id = self.tracker.create_task(total_items=100)

        with patch('time.time') as mock_time:
            mock_time.side_effect = [100.0, 100.5, 101.0]  # Fast updates

            self.tracker.update_progress(task_id, current=10)  # t=100
            mock_time.return_value = 100.5
            self.tracker.update_progress(task_id, current=20)  # t=100.5, speed=20/s (fast)

            progress = self.tracker.get_progress(task_id)
            assert progress.slow_processing_warning is False


class TestTqdmInterceptor:
    """Test tqdm output parsing functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.interceptor = TqdmInterceptor()

    def test_parse_tqdm_output_valid_format(self):
        """Test parsing valid tqdm output format."""
        # Typical tqdm output format
        output = "Progress: 75%|████████████████████     | 750/1000行 [00:45<00:15, 16.67行/s]"

        result = self.interceptor.parse_tqdm_output(output)

        assert result is not None
        assert result["percentage"] == 75.0
        assert result["current"] == 750
        assert result["total"] == 1000

    def test_parse_tqdm_output_different_descriptions(self):
        """Test parsing tqdm output with different descriptions."""
        outputs = [
            "Processing files: 50%|██████████          | 500/1000行 [01:30<01:30, 5.56行/s]",
            "Loading data: 25%|█████               | 250/1000行 [00:30<01:30, 8.33行/s]",
            "Comparing: 100%|████████████████████| 1000/1000行 [02:00<00:00, 8.33行/s]"
        ]

        expected_results = [
            {"percentage": 50.0, "current": 500, "total": 1000},
            {"percentage": 25.0, "current": 250, "total": 1000},
            {"percentage": 100.0, "current": 1000, "total": 1000}
        ]

        for output, expected in zip(outputs, expected_results):
            result = self.interceptor.parse_tqdm_output(output)
            assert result == expected

    def test_parse_tqdm_output_invalid_format(self):
        """Test parsing invalid tqdm output returns None."""
        invalid_outputs = [
            "Regular log message without progress",
            "Error: File not found",
            "75% complete but wrong format",
            "",
            None,
            123  # Non-string input
        ]

        for output in invalid_outputs:
            result = self.interceptor.parse_tqdm_output(output)
            assert result is None

    def test_parse_tqdm_output_edge_cases(self):
        """Test parsing edge cases."""
        edge_cases = [
            ("0%|                    | 0/1000行 [00:00<?, ?行/s]", {"percentage": 0.0, "current": 0, "total": 1000}),
            ("1%|                    | 1/100行 [00:01<01:39, 1.00行/s]", {"percentage": 1.0, "current": 1, "total": 100}),
            ("99%|███████████████████▉| 99/100行 [01:39<00:01, 1.00行/s]", {"percentage": 99.0, "current": 99, "total": 100})
        ]

        for output, expected in edge_cases:
            result = self.interceptor.parse_tqdm_output(output)
            assert result == expected

    def test_process_output_updates_progress_tracker(self):
        """Test that process_output updates ProgressTracker correctly."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=1000)

        # Simulate tqdm output
        output = "Processing: 50%|██████████          | 500/1000行 [01:00<01:00, 8.33行/s]"

        self.interceptor.process_output(output, task_id, tracker)

        # Check that progress was updated
        progress = tracker.get_progress(task_id)
        assert progress.current == 500

    def test_process_output_ignores_invalid_output(self):
        """Test that process_output ignores invalid output."""
        tracker = ProgressTracker()
        task_id = tracker.create_task(total_items=1000)

        # Invalid outputs should not update progress
        invalid_outputs = ["", "Invalid output", None]

        for output in invalid_outputs:
            self.interceptor.process_output(output, task_id, tracker)

        # Progress should remain at 0
        progress = tracker.get_progress(task_id)
        assert progress.current == 0


class TestProgressTrackerErrorHandling:
    """Test error handling functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.tracker = ProgressTracker()

    def test_zero_total_items_handling(self):
        """Test handling of zero total items."""
        task_id = self.tracker.create_task(total_items=0)

        progress = self.tracker.get_progress(task_id)
        assert progress.total == 0
        assert progress.percentage == 0.0

        # Update should cap at 0
        self.tracker.update_progress(task_id, current=10)
        progress = self.tracker.get_progress(task_id)
        assert progress.current == 0

    def test_negative_progress_values(self):
        """Test handling of negative progress values."""
        task_id = self.tracker.create_task(total_items=100)

        # Negative current should be handled gracefully
        self.tracker.update_progress(task_id, current=-10)

        progress = self.tracker.get_progress(task_id)
        # Implementation should handle this gracefully
        assert progress.current >= 0

    def test_multiple_completion_calls(self):
        """Test that multiple completion calls don't change status."""
        task_id = self.tracker.create_task(total_items=100)

        # Complete as success
        self.tracker.complete_task(task_id, success=True)
        assert self.tracker.tasks[task_id].status == "completed"

        # Try to complete as error (should be ignored)
        self.tracker.complete_task(task_id, success=False, error_message="Some error")
        assert self.tracker.tasks[task_id].status == "completed"  # Should not change
        assert self.tracker.tasks[task_id].error is None  # Should not change

    def test_concurrent_task_creation(self):
        """Test concurrent task creation generates unique IDs."""
        # Create multiple tasks rapidly
        task_ids = []
        for _ in range(100):
            task_id = self.tracker.create_task(total_items=100)
            task_ids.append(task_id)

        # All task IDs should be unique
        assert len(set(task_ids)) == 100
        assert len(self.tracker.tasks) == 100


class TestProgressTrackerLogging:
    """Test logging integration functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.tracker = ProgressTracker()
        # Ensure we have a clean logger for testing
        self.original_handlers = self.tracker.logger.handlers[:]

    def teardown_method(self):
        """Cleanup after each test."""
        # Restore original handlers
        self.tracker.logger.handlers = self.original_handlers

    def test_log_progress_creates_log_entry(self):
        """Test that log_progress creates appropriate log entry."""
        with patch.object(self.tracker.logger, 'info') as mock_info:
            task_id = "test-task-123"
            message = "Processing item 50 of 100"

            self.tracker.log_progress(task_id, message)

            mock_info.assert_called_once_with(f"Progress [{task_id}]: {message}")

    def test_log_task_creation(self):
        """Test logging of task creation."""
        with patch.object(self.tracker.logger, 'info') as mock_info:
            task_id = "test-task-456"
            total_items = 500

            self.tracker.log_task_creation(task_id, total_items)

            mock_info.assert_called_once_with(f"Task created: {task_id} with {total_items} items")

    def test_log_task_completion_success(self):
        """Test logging of successful task completion."""
        with patch.object(self.tracker.logger, 'info') as mock_info:
            task_id = "test-task-789"
            duration = 45.67

            self.tracker.log_task_completion(task_id, success=True, duration=duration)

            mock_info.assert_called_once_with(f"Task completed: {task_id} (success) in {duration:.2f}s")

    def test_log_task_completion_failure(self):
        """Test logging of failed task completion."""
        with patch.object(self.tracker.logger, 'info') as mock_info:
            task_id = "test-task-999"
            duration = 30.12

            self.tracker.log_task_completion(task_id, success=False, duration=duration)

            mock_info.assert_called_once_with(f"Task completed: {task_id} (failed) in {duration:.2f}s")

    def test_log_error_with_exception(self):
        """Test error logging with exception."""
        with patch.object(self.tracker.logger, 'error') as mock_error:
            task_id = "test-task-error"
            error_message = "File not found"
            exception = FileNotFoundError("test.json not found")

            self.tracker.log_error(task_id, error_message, exception)

            expected_msg = f"Error in task {task_id}: {error_message} - Exception: {str(exception)}"
            mock_error.assert_called_once_with(expected_msg)

    def test_log_error_without_exception(self):
        """Test error logging without exception."""
        with patch.object(self.tracker.logger, 'error') as mock_error:
            task_id = "test-task-error2"
            error_message = "Invalid data format"

            self.tracker.log_error(task_id, error_message)

            expected_msg = f"Error in task {task_id}: {error_message}"
            mock_error.assert_called_once_with(expected_msg)

    def test_log_warning(self):
        """Test warning logging."""
        with patch.object(self.tracker.logger, 'warning') as mock_warning:
            task_id = "test-task-warn"
            warning_message = "Processing is slower than expected"

            self.tracker.log_warning(task_id, warning_message)

            mock_warning.assert_called_once_with(f"Warning in task {task_id}: {warning_message}")

    def test_log_exception(self):
        """Test exception logging."""
        with patch.object(self.tracker.logger, 'exception') as mock_exception:
            task_id = "test-task-exception"
            exception = ValueError("Invalid input parameter")

            self.tracker.log_exception(task_id, exception)

            mock_exception.assert_called_once_with(f"Exception in task {task_id}: {str(exception)}")


class TestProgressTrackerMetrics:
    """Test metrics collection functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.tracker = ProgressTracker()

    def test_record_metrics(self):
        """Test metrics recording."""
        task_id = self.tracker.create_task(total_items=100)
        metrics = {
            "cpu_usage": 45.2,
            "memory_usage": 512.8,
            "file_size": 1024000
        }

        self.tracker.record_metrics(task_id, metrics)

        # Check metrics were stored
        assert task_id in self.tracker.metrics_data
        stored_metrics = self.tracker.metrics_data[task_id]
        assert stored_metrics["cpu_usage"] == 45.2
        assert stored_metrics["memory_usage"] == 512.8
        assert stored_metrics["file_size"] == 1024000
        assert "timestamp" in stored_metrics

    def test_get_performance_metrics(self):
        """Test getting performance metrics."""
        task_id = self.tracker.create_task(total_items=100)
        self.tracker.update_progress(task_id, current=50)

        # Record some custom metrics
        custom_metrics = {"custom_metric": 123.45}
        self.tracker.record_metrics(task_id, custom_metrics)

        metrics = self.tracker.get_performance_metrics(task_id)

        assert metrics is not None
        assert metrics["task_id"] == task_id
        assert metrics["processing_speed"] >= 0
        assert metrics["percentage"] == 50.0
        assert metrics["custom_metric"] == 123.45

    def test_get_performance_metrics_invalid_task(self):
        """Test getting metrics for invalid task returns None."""
        metrics = self.tracker.get_performance_metrics("invalid-task-id")
        assert metrics is None

    def test_export_metrics_json_format(self):
        """Test exporting metrics in JSON format."""
        task_id1 = self.tracker.create_task(total_items=100)
        task_id2 = self.tracker.create_task(total_items=200)

        self.tracker.update_progress(task_id1, current=25)
        self.tracker.update_progress(task_id2, current=100)

        exported = self.tracker.export_metrics(format="json")

        # Should be valid JSON
        data = json.loads(exported)
        assert task_id1 in data
        assert task_id2 in data
        assert data[task_id1]["percentage"] == 25.0
        assert data[task_id2]["percentage"] == 50.0

    def test_export_metrics_string_format(self):
        """Test exporting metrics in string format."""
        task_id = self.tracker.create_task(total_items=100)

        exported = self.tracker.export_metrics(format="string")

        # Should be string representation
        assert isinstance(exported, str)
        assert task_id in exported


if __name__ == "__main__":
    pytest.main([__file__, "-v"])