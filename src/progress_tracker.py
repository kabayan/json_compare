"""Progress tracking module for WebUI real-time progress display."""

import io
import re
import sys
import time
import uuid
import json
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator
from collections import deque


@dataclass
class ProgressData:
    """Progress data for a task at a specific point in time."""
    task_id: str
    total: int
    current: int
    percentage: float
    elapsed_time: float
    estimated_remaining: Optional[float] = None
    status: str = "processing"  # processing, completed, error
    error_message: Optional[str] = None
    processing_speed: float = 0.0  # items per second
    slow_processing_warning: bool = False


@dataclass
class TaskData:
    """Internal task data structure."""
    task_id: str
    created_at: datetime
    total_items: int
    current_items: int = 0
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    status: str = "processing"
    result: Optional[Dict] = None
    error: Optional[str] = None
    speed_history: deque = field(default_factory=lambda: deque(maxlen=10))  # Keep last 10 speed measurements
    update_times: List[float] = field(default_factory=list)
    update_counts: List[int] = field(default_factory=list)


class ProgressTracker:
    """Manages progress tracking for multiple tasks."""

    def __init__(self):
        """Initialize the progress tracker."""
        self.tasks: Dict[str, TaskData] = {}

    def create_task(self, total_items: int) -> str:
        """Create a new task and return its unique ID.

        Args:
            total_items: Total number of items to process

        Returns:
            Unique task ID
        """
        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Create task data
        task_data = TaskData(
            task_id=task_id,
            created_at=datetime.now(),
            total_items=total_items
        )

        # Store in memory
        self.tasks[task_id] = task_data

        return task_id

    def update_progress(self, task_id: str, current: int) -> None:
        """Update the progress of a task.

        Args:
            task_id: Task ID to update
            current: Current number of processed items
        """
        if task_id not in self.tasks:
            return  # Silently ignore invalid task IDs

        task = self.tasks[task_id]

        # Prevent updates to completed/error tasks
        if task.status in ["completed", "error"]:
            return

        # Cap current at total
        if task.total_items > 0:
            current = min(current, task.total_items)
        else:
            current = 0  # For zero total, keep current at 0

        # Calculate speed if we have previous updates
        now = time.time()
        if task.update_times:
            # Calculate speed from last update
            time_diff = now - task.update_times[-1]
            if time_diff > 0:
                items_processed = current - task.update_counts[-1]
                speed = items_processed / time_diff
                task.speed_history.append(speed)

        # Update task data
        task.current_items = current
        task.last_update = now
        task.update_times.append(now)
        task.update_counts.append(current)

    def get_progress(self, task_id: str) -> Optional[ProgressData]:
        """Get the current progress of a task.

        Args:
            task_id: Task ID to query

        Returns:
            ProgressData or None if task doesn't exist
        """
        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]

        # Calculate percentage
        if task.total_items > 0:
            percentage = (task.current_items / task.total_items) * 100.0
        else:
            percentage = 0.0

        # Calculate elapsed time
        elapsed_time = time.time() - task.start_time

        # Calculate average processing speed
        processing_speed = 0.0
        if task.speed_history:
            # Use moving average of recent speeds
            processing_speed = sum(task.speed_history) / len(task.speed_history)
        elif task.current_items > 0 and elapsed_time > 0:
            # Fallback to overall average
            processing_speed = task.current_items / elapsed_time

        # Estimate remaining time if we have enough data (10% completion)
        estimated_remaining = None
        if task.total_items > 0:
            progress_ratio = task.current_items / task.total_items
            if progress_ratio >= 0.1 and processing_speed > 0:
                remaining_items = task.total_items - task.current_items
                estimated_remaining = remaining_items / processing_speed

        # Check for slow processing warning
        slow_processing_warning = processing_speed < 1.0 and processing_speed > 0

        return ProgressData(
            task_id=task_id,
            total=task.total_items,
            current=task.current_items,
            percentage=percentage,
            elapsed_time=elapsed_time,
            estimated_remaining=estimated_remaining,
            status=task.status,
            error_message=task.error,
            processing_speed=processing_speed,
            slow_processing_warning=slow_processing_warning
        )

    def complete_task(self, task_id: str, success: bool = True, error_message: Optional[str] = None) -> None:
        """Mark a task as completed or failed.

        Args:
            task_id: Task ID to complete
            success: True for successful completion, False for error
            error_message: Error message if success is False
        """
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]

        # Don't change status if already completed/error
        if task.status in ["completed", "error"]:
            return

        if success:
            task.status = "completed"
        else:
            task.status = "error"
            task.error = error_message

    async def stream_progress(self, task_id: str, timeout: Optional[float] = None) -> AsyncGenerator[Dict[str, str], None]:
        """Stream progress updates via SSE (Server-Sent Events).

        Args:
            task_id: Task ID to stream progress for
            timeout: Optional timeout in seconds

        Yields:
            SSE events with progress data
        """
        start_time = time.time()
        last_progress = None

        # Check if task exists
        if task_id not in self.tasks:
            yield {
                "event": "error",
                "data": json.dumps({
                    "error_message": f"Task {task_id} not found"
                })
            }
            return

        while True:
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                break

            # Get current progress
            progress = self.get_progress(task_id)
            if progress is None:
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error_message": f"Task {task_id} not found"
                    })
                }
                break

            # Only send if progress has changed or first time
            if last_progress is None or (
                progress.current != last_progress.current or
                progress.status != last_progress.status
            ):
                event_type = "progress"
                if progress.status == "completed":
                    event_type = "complete"
                elif progress.status == "error":
                    event_type = "error"

                event_data = {
                    "task_id": progress.task_id,
                    "current": progress.current,
                    "total": progress.total,
                    "percentage": progress.percentage,
                    "elapsed_seconds": progress.elapsed_time,
                    "status": progress.status
                }

                if progress.estimated_remaining is not None:
                    event_data["remaining_seconds"] = progress.estimated_remaining

                if progress.error_message:
                    event_data["error_message"] = progress.error_message

                yield {
                    "event": event_type,
                    "data": json.dumps(event_data)
                }

                last_progress = progress

                # Stop streaming if task is completed or errored
                if progress.status in ["completed", "error"]:
                    break

            # Wait before next check
            await asyncio.sleep(0.1)  # Check every 100ms for tests


class TqdmCaptureStream:
    """Custom stream for capturing tqdm output while preserving original output."""

    def __init__(self, original_stream, interceptor, task_id, progress_tracker):
        """Initialize the capture stream.

        Args:
            original_stream: Original stdout/stderr
            interceptor: TqdmInterceptor instance
            task_id: Task ID for progress tracking
            progress_tracker: ProgressTracker instance
        """
        self.original_stream = original_stream
        self.interceptor = interceptor
        self.task_id = task_id
        self.progress_tracker = progress_tracker
        self.buffer = io.StringIO()

    def write(self, text):
        """Write text to both captured buffer and original stream."""
        # Write to original stream to preserve output
        if hasattr(self.original_stream, 'write'):
            self.original_stream.write(text)

        # Capture for processing
        self.buffer.write(text)

        # Process the captured output if it looks like tqdm
        if self.interceptor and hasattr(self.interceptor, 'process_output'):
            self.interceptor.process_output(text, self.task_id, self.progress_tracker)

        # Also call handle_output if it exists (for testing)
        if self.interceptor and hasattr(self.interceptor, 'handle_output'):
            self.interceptor.handle_output(text)

        return len(text)

    def flush(self):
        """Flush both streams."""
        if hasattr(self.original_stream, 'flush'):
            self.original_stream.flush()
        self.buffer.flush()

    def __getattr__(self, name):
        """Delegate other attributes to original stream."""
        return getattr(self.original_stream, name)


class TqdmInterceptor:
    """Intercepts tqdm output and extracts progress information."""

    def __init__(self):
        """Initialize the TqdmInterceptor."""
        self.captured_streams = {}

    @contextmanager
    def capture_tqdm(self, task_id: str, progress_tracker: 'ProgressTracker'):
        """Context manager to capture tqdm output and send to ProgressTracker.

        Args:
            task_id: Task ID to associate with captured progress
            progress_tracker: ProgressTracker instance to update

        Yields:
            None
        """
        # Save original streams
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            # Replace streams with capturing versions
            sys.stdout = TqdmCaptureStream(original_stdout, self, task_id, progress_tracker)
            sys.stderr = TqdmCaptureStream(original_stderr, self, task_id, progress_tracker)

            yield

        finally:
            # Always restore original streams
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def parse_tqdm_output(self, output: str) -> Optional[Dict[str, any]]:
        """Parse tqdm output string to extract progress information.

        Args:
            output: tqdm output string

        Returns:
            Dictionary with progress info or None if invalid format
            Expected keys: current, total, percentage
        """
        if not output or not isinstance(output, str):
            return None

        # Regex pattern to match tqdm output format
        # Format: "Description: 75%|████████████████████     | 750/1000行 [00:45<00:15, 16.67行/s]"
        pattern = r'.*?(\d+)%\|.*?\|\s*(\d+)/(\d+)行\s*\['

        match = re.search(pattern, output)
        if not match:
            return None

        try:
            percentage = float(match.group(1))
            current = int(match.group(2))
            total = int(match.group(3))

            return {
                "percentage": percentage,
                "current": current,
                "total": total
            }
        except (ValueError, IndexError):
            return None

    def process_output(self, output: str, task_id: str, progress_tracker: 'ProgressTracker') -> None:
        """Process captured output and update progress tracker.

        Args:
            output: Captured output string
            task_id: Task ID to update
            progress_tracker: ProgressTracker instance
        """
        if not output or not output.strip():
            return

        # Parse the output to extract progress info
        progress_info = self.parse_tqdm_output(output)
        if progress_info:
            # Update the progress tracker with extracted information
            current = progress_info.get("current", 0)
            progress_tracker.update_progress(task_id, current)

    def handle_output(self, output: str) -> None:
        """Handle captured output (for testing/mocking purposes).

        Args:
            output: Captured output string
        """
        # This method is primarily for testing
        pass