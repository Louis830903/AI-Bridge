"""
Office Tasks - Office Automation

Provides tasks for:
- Web attendance/clock-in: Automated punch in/out
- Form filling: Batch fill forms with data
- Resource booking: Meeting rooms, equipment
- Data extraction: Scrape tables and export
"""

import re
import csv
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from io import StringIO

from .base import BaseTask, TaskConfig, TaskResult, TaskStatus
from ..engine import SnapshotParser, PageElement
from ..semantics import ActionSemantics


@dataclass
class FormField:
    """Form field information"""
    uid: str
    name: str
    field_type: str  # textbox, combobox, checkbox, etc.
    required: bool = False
    current_value: str = ""
    options: List[str] = field(default_factory=list)  # For select/combobox


@dataclass
class TableData:
    """Extracted table data"""
    headers: List[str]
    rows: List[List[str]]
    
    def to_dicts(self) -> List[Dict[str, str]]:
        """Convert to list of dictionaries"""
        return [
            {h: row[i] if i < len(row) else "" for i, h in enumerate(self.headers)}
            for row in self.rows
        ]
    
    def to_csv(self) -> str:
        """Export as CSV string"""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(self.headers)
        writer.writerows(self.rows)
        return output.getvalue()
    
    def to_json(self) -> str:
        """Export as JSON string"""
        return json.dumps(self.to_dicts(), ensure_ascii=False, indent=2)


@dataclass
class AttendanceResult:
    """Result of attendance operation"""
    success: bool
    action: str = ""  # clock_in, clock_out
    timestamp: Optional[datetime] = None
    location: Optional[str] = None
    message: str = ""


# 常量定义
COMMON_COLUMN_COUNTS = (3, 4, 5, 6, 2, 7, 8)
DEFAULT_COLUMN_COUNT = 4


class OfficeTask(BaseTask):
    """
    Office automation tasks for attendance, forms, and data extraction.
    
    Example:
        task = OfficeTask()
        
        # Find clock-in button
        btn = task.find_clock_in_button(snapshot)
        
        # Extract form fields
        fields = task.extract_form_fields(snapshot)
        
        # Extract table data
        table = task.extract_table(snapshot)
    """
    
    def find_clock_in_button(self, snapshot: str) -> Optional[PageElement]:
        """
        Find attendance clock-in button.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PageElement for clock-in button or None
        """
        clock_keywords = ActionSemantics.get_action_keywords("clock_in")
        
        # Additional office-specific keywords
        extra_keywords = {
            "punch", "clock", "attendance", "work",
            "上班", "下班", "出勤", "工作",
        }
        
        all_keywords = list(clock_keywords | extra_keywords)
        
        return self.find_element_by_text(
            snapshot,
            all_keywords,
            element_types=["button", "link"]
        )
    
    def detect_clock_status(self, snapshot: str) -> Dict[str, Any]:
        """
        Detect current attendance status from page.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            Dict with status info: clocked_in, clocked_out, time, etc.
        """
        elements = SnapshotParser.parse(snapshot)
        
        status = {
            "clocked_in": False,
            "clocked_out": False,
            "clock_in_time": None,
            "clock_out_time": None,
        }
        
        # Time pattern for attendance records
        time_pattern = re.compile(r'\d{1,2}:\d{2}(?::\d{2})?')
        
        in_indicators = {"clocked in", "punched in", "上班打卡", "已签到", "打卡时间"}
        out_indicators = {"clocked out", "punched out", "下班打卡", "已签退"}
        
        for element in elements:
            text_lower = element.text.lower()
            
            # Check clock-in status
            for indicator in in_indicators:
                if indicator in text_lower:
                    status["clocked_in"] = True
                    time_match = time_pattern.search(element.text)
                    if time_match:
                        status["clock_in_time"] = time_match.group()
            
            # Check clock-out status
            for indicator in out_indicators:
                if indicator in text_lower:
                    status["clocked_out"] = True
                    time_match = time_pattern.search(element.text)
                    if time_match:
                        status["clock_out_time"] = time_match.group()
        
        return status
    
    def extract_form_fields(self, snapshot: str) -> List[FormField]:
        """
        Extract all form fields from page.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            List of FormField objects
        """
        elements = SnapshotParser.parse(snapshot)
        fields = []
        
        input_types = {
            "textbox", "textarea", "combobox", "listbox",
            "spinbutton", "searchbox", "checkbox", "radio",
        }
        
        for element in elements:
            if element.element_type in input_types:
                # Try to find label
                label = self._find_field_label(elements, element)
                
                fields.append(FormField(
                    uid=element.uid,
                    name=label or element.text or f"field_{element.uid}",
                    field_type=element.element_type,
                    current_value=element.text,
                ))
        
        return fields
    
    def _find_field_label(
        self, 
        elements: List[PageElement], 
        field: PageElement
    ) -> Optional[str]:
        """
        Find label text for a form field based on proximity or association.
        
        Args:
            elements: List of all page elements
            field: The form field to find label for
            
        Returns:
            Label text or None
        """
        # 优先查找 for 属性关联的 label
        for element in elements:
            if element.element_type == "label":
                if hasattr(element, 'for_id') and element.for_id == field.uid:
                    return element.text
        
        # 回退：查找位置相近的 label（简化实现）
        for element in elements:
            if element.element_type == "label":
                if 0 < len(element.text) < 50:
                    return element.text
        
        return None
    
    def map_form_fields(
        self, 
        fields: List[FormField],
        data: Dict[str, str],
    ) -> List[Tuple[str, str]]:
        """
        Map data values to form fields by matching names.
        
        Args:
            fields: List of form fields
            data: Dict of field_name -> value to fill
            
        Returns:
            List of (uid, value) tuples for filling
        """
        mappings = []
        
        for field in fields:
            field_name_lower = field.name.lower()
            
            for key, value in data.items():
                key_lower = key.lower()
                
                # Match by exact or partial name
                if key_lower == field_name_lower or key_lower in field_name_lower:
                    mappings.append((field.uid, value))
                    break
        
        return mappings
    
    def extract_table_data(self, snapshot: str) -> Optional[TableData]:
        """
        Extract table data from page snapshot.
        
        Handles various table structures including:
        - Standard HTML tables with headers
        - Grid layouts
        - List-based tables
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            TableData object or None if no table found
        """
        elements = SnapshotParser.parse(snapshot)
        
        # Collect cells by type
        headers = []
        cells = []
        
        table_types = {"cell", "gridcell", "rowheader", "columnheader"}
        
        for element in elements:
            if element.element_type == "columnheader":
                headers.append(element.text)
            elif element.element_type in table_types:
                cells.append(element.text)
        
        if not cells:
            return None
        
        # If no explicit headers, try to infer from first row
        if not headers and cells:
            # Heuristic: assume first few cells are headers if they look like labels
            # This is imperfect but works for simple tables
            pass
        
        # Organize cells into rows
        # This is a best-effort approach - actual row boundaries depend on DOM structure
        num_cols = len(headers) if headers else self._estimate_columns(cells)
        
        if num_cols == 0:
            num_cols = 1
        
        rows = []
        for i in range(0, len(cells), num_cols):
            row = cells[i:i + num_cols]
            rows.append(row)
        
        # Generate default headers if none found
        if not headers:
            headers = [f"Column {i+1}" for i in range(num_cols)]
        
        return TableData(headers=headers, rows=rows)
    
    def _estimate_columns(self, cells: List[str]) -> int:
        """
        Estimate number of columns from cell patterns.
        
        Uses common column counts as heuristic for table structures.
        
        Args:
            cells: List of cell text values
            
        Returns:
            Estimated column count
        """
        if len(cells) <= 1:
            return 1
        
        # 尝试常见的列数
        for cols in COMMON_COLUMN_COUNTS:
            if len(cells) % cols == 0:
                return cols
        
        return DEFAULT_COLUMN_COUNT
    
    def find_meeting_rooms(self, snapshot: str) -> List[Dict[str, Any]]:
        """
        Find available meeting rooms from booking page.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            List of room info dicts with name, capacity, availability
        """
        elements = SnapshotParser.parse(snapshot)
        rooms = []
        
        room_keywords = {"room", "meeting", "conference", "会议室", "房间"}
        available_keywords = {"available", "free", "open", "可用", "空闲"}
        booked_keywords = {"booked", "occupied", "busy", "已预约", "占用"}
        
        for element in elements:
            text_lower = element.text.lower()
            
            # Check if this looks like a room entry
            is_room = any(kw in text_lower for kw in room_keywords)
            
            if is_room and element.element_type in ("button", "link", "cell", "listitem"):
                available = True
                
                # Check availability
                for kw in booked_keywords:
                    if kw in text_lower:
                        available = False
                        break
                
                rooms.append({
                    "name": element.text[:50],
                    "uid": element.uid,
                    "available": available,
                    "element_type": element.element_type,
                })
        
        return rooms
    
    def extract_report_data(
        self, 
        snapshot: str,
        patterns: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract key data points from a report page.
        
        Args:
            snapshot: Page snapshot text
            patterns: Optional dict of name -> regex pattern for extraction
            
        Returns:
            Dict of extracted data points
        """
        elements = SnapshotParser.parse(snapshot)
        data = {}
        
        # Default patterns for common report fields
        default_patterns = {
            "total": r"(?:total|sum|合计|总计)[:\s]*([\d,.]+)",
            "count": r"(?:count|number|数量|个数)[:\s]*(\d+)",
            "average": r"(?:average|avg|平均)[:\s]*([\d,.]+)",
            "date": r"(?:date|日期)[:\s]*(\d{4}[-/]\d{2}[-/]\d{2})",
            "percentage": r"([\d.]+)%",
        }
        
        patterns = patterns or default_patterns
        
        # Combine all text for pattern matching
        all_text = " ".join(e.text for e in elements if e.text)
        
        for name, pattern in patterns.items():
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                data[name] = match.group(1)
        
        return data
    
    def find_export_button(self, snapshot: str) -> Optional[PageElement]:
        """
        Find export/download button for reports.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PageElement for export button or None
        """
        download_keywords = ActionSemantics.get_action_keywords("download")
        
        extra_keywords = {"export", "excel", "csv", "pdf", "导出", "下载报表"}
        all_keywords = list(download_keywords | extra_keywords)
        
        return self.find_element_by_text(
            snapshot,
            all_keywords,
            element_types=["button", "link"]
        )
