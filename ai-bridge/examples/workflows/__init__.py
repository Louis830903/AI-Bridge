"""
AI-Bridge 工作流示例
Workflow examples for AI-Bridge

可用工作流:
- daily_report: 每日报告自动化
- cross_platform_sync: 跨平台信息同步
"""

from .daily_report import DailyReportWorkflow
from .cross_platform_sync import CrossPlatformSyncWorkflow

__all__ = [
    "DailyReportWorkflow",
    "CrossPlatformSyncWorkflow",
]
