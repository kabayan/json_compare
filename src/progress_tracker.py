"""Progress tracking module for WebUI real-time progress display."""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
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

    async def stream_progress(self, task_id: str):
        """Stream progress updates via SSE (Server-Sent Events).

        Args:
            task_id: Task ID to stream progress for

        Yields:
            SSE events with progress data
        """
        # This will be implemented in task 3 (SSE implementation)
        # For now, just a placeholder
        pass