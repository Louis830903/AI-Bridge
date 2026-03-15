"""AI-Bridge CLI 模块

提供命令行工具和诊断功能。
"""

from aibridge.cli.doctor import DoctorCommand, run_doctor
from aibridge.cli.init_wizard import run_init_wizard

__all__ = ["DoctorCommand", "run_doctor", "run_init_wizard"]
