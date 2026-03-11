"""
Browser Automation Tasks

A collection of automation tasks for various scenarios:
- Monitor: Price tracking, stock monitoring, news aggregation
- Checkin: Daily check-ins, ticket grabbing, reservations
- Office: Attendance, form filling, data extraction
- Publish: Multi-platform publishing, comment management
- Learning: Paper downloads, auto-play courses, auto-pagination

Example:
    from aibridge.automation.tasks import MonitorTask, CheckinTask
    
    # Create and execute a monitoring task
    task = MonitorTask()
    result = task.track_price(url, target_price=100.0)
"""

from .base import (
    TaskAction,
    TaskStatus,
    TaskStep,
    TaskConfig,
    StepResult,
    TaskResult,
    BaseTask,
    create_step,
    create_config,
)

# Monitor task and data classes
from .monitor import (
    MonitorTask,
    PriceInfo,
    StockStatus,
    NewsItem,
    MonitorResult,
)

# Checkin task and data classes
from .checkin import (
    CheckinTask,
    CheckinResult,
    BookingSlot,
    BookingResult,
)

# Office task and data classes
from .office import (
    OfficeTask,
    FormField,
    TableData,
    AttendanceResult,
    COMMON_COLUMN_COUNTS,
    DEFAULT_COLUMN_COUNT,
)

# Publish task and data classes
from .publish import (
    PublishTask,
    PublishTarget,
    Comment,
    PublishResult,
    PUBLISH_PLATFORMS,
)

# Learning task and data classes
from .learning import (
    LearningTask,
    Paper,
    VideoInfo,
    ReadingProgress,
)

# Config loader
from .config_loader import (
    ConfigLoader,
    TaskDefinition,
    create_sample_config,
    get_yaml_template,
)

__all__ = [
    # Base classes
    "TaskAction",
    "TaskStatus",
    "TaskStep",
    "TaskConfig",
    "StepResult",
    "TaskResult",
    "BaseTask",
    "create_step",
    "create_config",
    # Monitor
    "MonitorTask",
    "PriceInfo",
    "StockStatus",
    "NewsItem",
    "MonitorResult",
    # Checkin
    "CheckinTask",
    "CheckinResult",
    "BookingSlot",
    "BookingResult",
    # Office
    "OfficeTask",
    "FormField",
    "TableData",
    "AttendanceResult",
    "COMMON_COLUMN_COUNTS",
    "DEFAULT_COLUMN_COUNT",
    # Publish
    "PublishTask",
    "PublishTarget",
    "Comment",
    "PublishResult",
    "PUBLISH_PLATFORMS",
    # Learning
    "LearningTask",
    "Paper",
    "VideoInfo",
    "ReadingProgress",
    # Config loader
    "ConfigLoader",
    "TaskDefinition",
    "create_sample_config",
    "get_yaml_template",
]
