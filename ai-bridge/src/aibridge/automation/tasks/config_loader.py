"""
Task Configuration Loader

Load and manage task configurations from YAML files.
"""

import os
import logging
import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

from .base import TaskConfig, TaskStep, TaskAction

logger = logging.getLogger(__name__)


@dataclass
class TaskDefinition:
    """Complete task definition from config"""
    name: str
    type: str  # monitor, checkin, office, publish, learning
    config: TaskConfig
    enabled: bool = True
    tags: Optional[List[str]] = field(default_factory=list)


class ConfigLoader:
    """
    Load task configurations from YAML files.
    
    Example:
        loader = ConfigLoader()
        
        # Load from file
        tasks = loader.load_file("my_tasks.yaml")
        
        # Load from directory
        tasks = loader.load_directory("./configs/")
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize loader.
        
        Args:
            base_dir: Base directory for config files
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
    
    def load_file(self, filepath: str) -> List[TaskDefinition]:
        """
        Load tasks from a YAML file.
        
        Args:
            filepath: Path to YAML file
            
        Returns:
            List of TaskDefinition objects
        """
        path = Path(filepath)
        if not path.is_absolute():
            path = self.base_dir / path
        
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return self._parse_config(data)
    
    def load_directory(self, dirpath: str) -> List[TaskDefinition]:
        """
        Load all YAML configs from a directory.
        
        Args:
            dirpath: Path to directory
            
        Returns:
            List of TaskDefinition objects
        """
        path = Path(dirpath)
        if not path.is_absolute():
            path = self.base_dir / path
        
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        
        tasks = []
        for file in path.glob("*.yaml"):
            try:
                tasks.extend(self.load_file(str(file)))
            except Exception as e:
                logger.warning(f"Failed to load {file}: {e}")
        
        for file in path.glob("*.yml"):
            try:
                tasks.extend(self.load_file(str(file)))
            except Exception as e:
                logger.warning(f"Failed to load {file}: {e}")
        
        return tasks
    
    def _parse_config(self, data: Dict[str, Any]) -> List[TaskDefinition]:
        """Parse YAML data into TaskDefinition objects"""
        tasks = []
        
        # Handle single task or list of tasks
        task_list = data.get('tasks', [data])
        
        for task_data in task_list:
            try:
                task = self._parse_task(task_data)
                if task:
                    tasks.append(task)
            except Exception as e:
                logger.warning(f"Failed to parse task: {e}")
        
        return tasks
    
    def _parse_task(self, data: Dict[str, Any]) -> Optional[TaskDefinition]:
        """Parse a single task definition"""
        if not data:
            return None
        
        name = data.get('name', 'Unnamed Task')
        task_type = data.get('type', 'generic')
        enabled = data.get('enabled', True)
        tags = data.get('tags', [])
        
        # Parse steps
        steps = []
        for step_data in data.get('steps', []):
            step = self._parse_step(step_data)
            if step:
                steps.append(step)
        
        config = TaskConfig(
            name=name,
            url=data.get('url', ''),
            steps=steps,
            schedule=data.get('schedule'),
            retry=data.get('retry', 3),
            timeout=data.get('timeout', 30),
            tags=tags,
        )
        
        return TaskDefinition(
            name=name,
            type=task_type,
            config=config,
            enabled=enabled,
            tags=tags,
        )
    
    def _parse_step(self, data: Dict[str, Any]) -> Optional[TaskStep]:
        """Parse a single step"""
        if not data:
            return None
        
        action_str = data.get('action', 'click')
        
        try:
            action = TaskAction(action_str)
        except ValueError:
            logger.warning(f"Unknown action '{action_str}', using 'click'")
            action = TaskAction.CLICK
        
        return TaskStep(
            action=action,
            target=data.get('target'),
            value=data.get('value'),
            wait_after=data.get('wait_after', 0.5),
            optional=data.get('optional', False),
        )


# YAML template for reference
YAML_TEMPLATE = '''
# Task Configuration Template
# Place this file in your configs directory

tasks:
  # Example: Daily check-in task
  - name: "V2EX Daily Check-in"
    type: checkin
    url: "https://www.v2ex.com/mission/daily"
    enabled: true
    schedule: "0 9 * * *"  # 9am daily
    tags: ["daily", "checkin"]
    steps:
      - action: click
        target: "领取"
        wait_after: 1.0

  # Example: Price monitoring task
  - name: "Monitor GPU Price"
    type: monitor
    url: "https://example.com/product/rtx4090"
    enabled: true
    schedule: "*/30 * * * *"  # Every 30 minutes
    tags: ["monitor", "price"]
    steps:
      - action: extract
        target: "price"
      - action: screenshot

  # Example: Web attendance
  - name: "Morning Clock In"
    type: office
    url: "https://hr.example.com/attendance"
    enabled: true
    schedule: "0 9 * * 1-5"  # 9am Mon-Fri
    tags: ["office", "attendance"]
    steps:
      - action: click
        target: "上班打卡"
        wait_after: 2.0

  # Example: Course auto-play
  - name: "Continue Course"
    type: learning
    url: "https://course.example.com/my-course"
    enabled: false
    tags: ["learning", "video"]
    steps:
      - action: click
        target: "继续学习"
      - action: click
        target: "播放"

# Action types:
# - navigate: Go to URL
# - click: Click element
# - fill: Fill input field
# - extract: Extract data
# - wait: Wait for element/time
# - screenshot: Take screenshot
# - scroll: Scroll page
# - submit: Submit form
# - select: Select option
# - hover: Hover element

# Schedule format (cron):
# minute hour day month weekday
# Examples:
# "0 9 * * *"     - 9am daily
# "*/30 * * * *"  - Every 30 minutes
# "0 9 * * 1-5"   - 9am Monday to Friday
# "0 0 1 * *"     - 1st of each month
'''


def create_sample_config(output_path: str = "sample_tasks.yaml"):
    """
    Create a sample configuration file.
    
    Args:
        output_path: Path to write sample config
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(YAML_TEMPLATE)
    logger.info(f"Sample config created: {output_path}")


def get_yaml_template() -> str:
    """Get the YAML template string"""
    return YAML_TEMPLATE
