"""
Base Task Framework

Provides the foundational classes for all browser automation tasks.
Reuses SnapshotParser and PageElement from the nurture engine.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from enum import Enum
from datetime import datetime

from ..engine import SnapshotParser, PageElement
from ..semantics import ActionSemantics


class TaskAction(Enum):
    """Task action types"""
    NAVIGATE = "navigate"       # Navigate to URL
    CLICK = "click"             # Click element
    FILL = "fill"               # Fill input field
    EXTRACT = "extract"         # Extract text/data
    WAIT = "wait"               # Wait for element/time
    SCREENSHOT = "screenshot"   # Take screenshot
    SCROLL = "scroll"           # Scroll page
    SUBMIT = "submit"           # Submit form
    SELECT = "select"           # Select option
    HOVER = "hover"             # Hover element


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskStep:
    """Single step in a task"""
    action: TaskAction
    target: Optional[str] = None        # Semantic keywords or uid
    value: Optional[str] = None         # Value for fill/select
    wait_after: float = 0.5             # Wait time after action (seconds)
    optional: bool = False              # If True, failure won't stop task
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskStep':
        """Create TaskStep from dictionary"""
        action = TaskAction(data.get('action', 'click'))
        return cls(
            action=action,
            target=data.get('target'),
            value=data.get('value'),
            wait_after=data.get('wait_after', 0.5),
            optional=data.get('optional', False),
        )


@dataclass
class TaskConfig:
    """Task configuration"""
    name: str
    url: str
    steps: List[TaskStep] = field(default_factory=list)
    schedule: Optional[str] = None      # Cron expression
    retry: int = 3
    timeout: int = 30                   # Seconds
    tags: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskConfig':
        """Create TaskConfig from dictionary"""
        steps = [TaskStep.from_dict(s) for s in data.get('steps', [])]
        return cls(
            name=data.get('name', 'Unnamed Task'),
            url=data.get('url', ''),
            steps=steps,
            schedule=data.get('schedule'),
            retry=data.get('retry', 3),
            timeout=data.get('timeout', 30),
            tags=data.get('tags', []),
        )


@dataclass
class StepResult:
    """Result of a single step execution"""
    step: TaskStep
    status: TaskStatus
    data: Any = None                    # Extracted data
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class TaskResult:
    """Result of task execution"""
    config: TaskConfig
    status: TaskStatus
    step_results: List[StepResult] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    
    @property
    def duration_seconds(self) -> float:
        """Total execution time in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0
    
    @property
    def extracted_data(self) -> Dict[str, Any]:
        """Collect all extracted data from steps"""
        data = {}
        for i, result in enumerate(self.step_results):
            if result.data is not None:
                data[f"step_{i}"] = result.data
        return data


class BaseTask:
    """
    Base class for all automation tasks.
    
    Provides common utilities:
    - Element finding by semantic keywords
    - Text extraction with regex
    - Form field detection
    - Table data extraction
    
    Example:
        class MyTask(BaseTask):
            def execute(self, config: TaskConfig) -> TaskResult:
                # Custom implementation
                pass
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.semantics = ActionSemantics()
    
    def find_element_by_text(
        self, 
        snapshot: str, 
        keywords: List[str],
        element_types: Optional[List[str]] = None,
    ) -> Optional[PageElement]:
        """
        Find element by matching text against keywords.
        
        Args:
            snapshot: Page snapshot text
            keywords: List of keywords to match
            element_types: Filter by element types (button, link, textbox, etc.)
            
        Returns:
            First matching PageElement or None
        """
        elements = SnapshotParser.parse(snapshot)
        
        for element in elements:
            # Filter by element type if specified
            if element_types and element.element_type not in element_types:
                continue
            
            # Match against keywords
            text_lower = element.text.lower()
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return element
        
        return None
    
    def find_elements_by_text(
        self, 
        snapshot: str, 
        keywords: List[str],
        element_types: Optional[List[str]] = None,
        max_count: int = 10,
    ) -> List[PageElement]:
        """
        Find all elements matching keywords.
        
        Args:
            snapshot: Page snapshot text
            keywords: List of keywords to match
            element_types: Filter by element types
            max_count: Maximum number of elements to return
            
        Returns:
            List of matching PageElements
        """
        elements = SnapshotParser.parse(snapshot)
        matches = []
        
        for element in elements:
            if len(matches) >= max_count:
                break
            
            # Filter by element type if specified
            if element_types and element.element_type not in element_types:
                continue
            
            # Match against keywords
            text_lower = element.text.lower()
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    matches.append(element)
                    break
        
        return matches
    
    def find_input_fields(self, snapshot: str) -> List[PageElement]:
        """
        Find all input fields (textbox, textarea, combobox, etc.)
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            List of input field elements
        """
        elements = SnapshotParser.parse(snapshot)
        input_types = {'textbox', 'textarea', 'combobox', 'spinbutton', 'searchbox'}
        return [e for e in elements if e.element_type in input_types]
    
    def find_buttons(self, snapshot: str) -> List[PageElement]:
        """
        Find all button elements.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            List of button elements
        """
        elements = SnapshotParser.parse(snapshot)
        return [e for e in elements if e.element_type == 'button' and not e.disabled]
    
    def find_links(self, snapshot: str) -> List[PageElement]:
        """
        Find all link elements.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            List of link elements
        """
        elements = SnapshotParser.parse(snapshot)
        return [e for e in elements if e.element_type == 'link']
    
    def extract_text(self, snapshot: str, pattern: str) -> List[str]:
        """
        Extract text matching regex pattern from snapshot.
        
        Args:
            snapshot: Page snapshot text
            pattern: Regex pattern
            
        Returns:
            List of matched strings
        """
        elements = SnapshotParser.parse(snapshot)
        matches = []
        
        regex = re.compile(pattern, re.IGNORECASE)
        for element in elements:
            found = regex.findall(element.text)
            matches.extend(found)
        
        return matches
    
    def extract_numbers(self, snapshot: str) -> List[float]:
        """
        Extract all numbers from snapshot.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            List of numbers
        """
        # Pattern matches integers, decimals, and currency formats
        pattern = r'[\d,]+\.?\d*'
        text_matches = self.extract_text(snapshot, pattern)
        
        numbers = []
        for match in text_matches:
            try:
                # Remove commas and convert
                clean = match.replace(',', '')
                if clean and clean != '.':
                    numbers.append(float(clean))
            except ValueError:
                continue
        
        return numbers
    
    def extract_table_data(self, snapshot: str) -> List[Dict[str, str]]:
        """
        Extract table data from snapshot (best effort).
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            List of row dictionaries
        """
        elements = SnapshotParser.parse(snapshot)
        
        # Find elements that look like table cells
        rows = []
        current_row = []
        
        for element in elements:
            if element.element_type in ('cell', 'gridcell', 'rowheader', 'columnheader'):
                current_row.append(element.text)
            elif element.element_type == 'row':
                if current_row:
                    rows.append(current_row)
                current_row = []
        
        if current_row:
            rows.append(current_row)
        
        # Convert to list of dicts using first row as headers
        if len(rows) < 2:
            return [{'value': cell} for row in rows for cell in row]
        
        headers = rows[0]
        result = []
        for row in rows[1:]:
            row_dict = {}
            for i, cell in enumerate(row):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row_dict[key] = cell
            result.append(row_dict)
        
        return result
    
    def execute(self, config: TaskConfig) -> TaskResult:
        """
        Execute the task. Override in subclasses.
        
        Args:
            config: Task configuration
            
        Returns:
            TaskResult with execution details
        """
        raise NotImplementedError("Subclasses must implement execute()")


# Convenience functions
def create_step(
    action: str, 
    target: Optional[str] = None, 
    value: Optional[str] = None,
    wait_after: float = 0.5,
    optional: bool = False,
) -> TaskStep:
    """
    Create a task step quickly.
    
    Args:
        action: Action type string (click, fill, navigate, etc.)
        target: Target element selector or keywords
        value: Value for fill/select actions
        wait_after: Wait time after action in seconds
        optional: Whether step failure should stop the task
        
    Returns:
        TaskStep instance
    """
    return TaskStep(
        action=TaskAction(action),
        target=target,
        value=value,
        wait_after=wait_after,
        optional=optional,
    )


def create_config(
    name: str, 
    url: str, 
    steps: List[TaskStep],
    schedule: Optional[str] = None,
    retry: int = 3,
    timeout: int = 30,
) -> TaskConfig:
    """
    Create a task config quickly.
    
    Args:
        name: Task name
        url: Target URL
        steps: List of task steps
        schedule: Optional cron expression for scheduling
        retry: Number of retries on failure
        timeout: Timeout in seconds
        
    Returns:
        TaskConfig instance
    """
    return TaskConfig(
        name=name, 
        url=url, 
        steps=steps,
        schedule=schedule,
        retry=retry,
        timeout=timeout,
    )
