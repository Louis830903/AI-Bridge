"""
Checkin Tasks - Daily Check-ins and Time-sensitive Operations

Provides tasks for:
- Website check-ins: Daily sign-ins for forums, points, memberships
- Ticket/flash sales: Rapid clicking for limited items
- Reservations: Booking appointments, restaurant reservations
"""

import re
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from .base import BaseTask, TaskConfig, TaskResult, TaskStatus
from ..engine import SnapshotParser, PageElement
from ..semantics import ActionSemantics


@dataclass
class CheckinResult:
    """Result of check-in operation"""
    success: bool
    already_checked: bool = False
    points_earned: Optional[int] = None
    consecutive_days: Optional[int] = None
    message: str = ""
    button_uid: Optional[str] = None


@dataclass
class BookingSlot:
    """Available booking time slot"""
    time: str
    available: bool = True
    uid: Optional[str] = None
    label: str = ""


@dataclass
class BookingResult:
    """Result of booking operation"""
    success: bool
    slot: Optional[BookingSlot] = None
    confirmation: Optional[str] = None
    message: str = ""


class CheckinTask(BaseTask):
    """
    Check-in and time-sensitive automation tasks.
    
    Example:
        task = CheckinTask()
        
        # Find and click check-in button
        result = task.find_checkin_button(snapshot)
        
        # Find available time slots
        slots = task.find_booking_slots(snapshot)
    """
    
    def find_checkin_button(self, snapshot: str) -> CheckinResult:
        """
        Find check-in button on page and return its info.
        
        Handles various check-in patterns:
        - Direct "Check in" / "Sign in" buttons
        - "Daily rewards" type buttons
        - Already checked-in states
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            CheckinResult with button info
        """
        elements = SnapshotParser.parse(snapshot)
        checkin_keywords = ActionSemantics.get_action_keywords("checkin")
        clock_in_keywords = ActionSemantics.get_action_keywords("clock_in")
        
        all_keywords = checkin_keywords | clock_in_keywords
        
        # Already checked indicators
        already_checked = {
            "already checked", "checked in", "signed in", "completed",
            "已签到", "已打卡", "今日已签", "签到成功", "打卡成功",
        }
        
        # Check if already checked in
        for element in elements:
            text_lower = element.text.lower()
            for indicator in already_checked:
                if indicator in text_lower:
                    return CheckinResult(
                        success=True,
                        already_checked=True,
                        message=f"Already checked in: {element.text}",
                    )
        
        # Find clickable check-in button
        for element in elements:
            if element.element_type not in ("button", "link"):
                continue
            
            if element.disabled or element.pressed:
                continue
            
            text_lower = element.text.lower()
            for keyword in all_keywords:
                if keyword.lower() in text_lower:
                    return CheckinResult(
                        success=True,
                        already_checked=False,
                        button_uid=element.uid,
                        message=f"Found check-in button: {element.text}",
                    )
        
        return CheckinResult(
            success=False,
            message="No check-in button found",
        )
    
    def find_login_button(self, snapshot: str) -> Optional[PageElement]:
        """
        Find login button on page.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PageElement for login button or None
        """
        login_keywords = ActionSemantics.get_action_keywords("login")
        return self.find_element_by_text(
            snapshot, 
            list(login_keywords),
            element_types=["button", "link"]
        )
    
    def find_booking_slots(
        self, 
        snapshot: str,
        date_filter: Optional[str] = None,
    ) -> List[BookingSlot]:
        """
        Find available booking/appointment time slots.
        
        Args:
            snapshot: Page snapshot text
            date_filter: Optional date string to filter by
            
        Returns:
            List of available BookingSlot objects
        """
        elements = SnapshotParser.parse(snapshot)
        slots = []
        
        # Time patterns
        time_patterns = [
            r'\d{1,2}:\d{2}',           # 10:30
            r'\d{1,2}\s*[ap]m',          # 10am, 2 pm
            r'\d{1,2}\u65f6\d{2}\u5206',  # 10时30分
            r'\d{1,2}\u70b9',             # 10点
        ]
        
        time_regex = re.compile('|'.join(time_patterns), re.IGNORECASE)
        
        # Booking-related keywords
        booking_keywords = ActionSemantics.get_action_keywords("booking")
        available_indicators = {"available", "open", "book", "select", "可预约", "可选", "空闲"}
        unavailable_indicators = {"full", "booked", "unavailable", "已满", "已约", "不可用"}
        
        for element in elements:
            text = element.text
            
            # Check if element looks like a time slot
            time_match = time_regex.search(text)
            if not time_match:
                continue
            
            # Determine availability
            text_lower = text.lower()
            available = True
            
            for indicator in unavailable_indicators:
                if indicator in text_lower:
                    available = False
                    break
            
            # Also check if button is disabled
            if element.disabled:
                available = False
            
            # Only include if element is interactive
            if element.element_type in ("button", "link", "cell", "option"):
                slots.append(BookingSlot(
                    time=time_match.group(),
                    available=available,
                    uid=element.uid,
                    label=text[:50],
                ))
        
        return slots
    
    def find_confirm_button(self, snapshot: str) -> Optional[PageElement]:
        """
        Find confirmation/submit button.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PageElement for confirm button or None
        """
        confirm_keywords = ActionSemantics.get_action_keywords("confirm")
        submit_keywords = ActionSemantics.get_action_keywords("submit")
        
        all_keywords = list(confirm_keywords | submit_keywords)
        
        return self.find_element_by_text(
            snapshot,
            all_keywords,
            element_types=["button"]
        )
    
    def find_quantity_selector(self, snapshot: str) -> Optional[PageElement]:
        """
        Find quantity input field (for ticket/product purchases).
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PageElement for quantity input or None
        """
        quantity_keywords = ["quantity", "qty", "amount", "数量", "购买数量"]
        
        elements = SnapshotParser.parse(snapshot)
        
        for element in elements:
            if element.element_type in ("spinbutton", "textbox", "combobox"):
                text_lower = element.text.lower()
                for keyword in quantity_keywords:
                    if keyword in text_lower:
                        return element
        
        return None
    
    def analyze_flash_sale_page(self, snapshot: str) -> Dict[str, Any]:
        """
        Analyze a flash sale / seckill page to find key elements.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            Dict with key elements: buy_button, quantity, countdown, etc.
        """
        result = {
            "buy_button": None,
            "quantity_input": None,
            "countdown": None,
            "price": None,
            "stock_status": None,
        }
        
        elements = SnapshotParser.parse(snapshot)
        
        # Buy button keywords
        buy_keywords = {
            "buy now", "purchase", "add to cart", "rush", "grab",
            "立即购买", "抢购", "秒杀", "加入购物车", "马上抢",
        }
        
        # Countdown patterns
        countdown_pattern = r'\d{2}:\d{2}:\d{2}|\d+\s*(?:days?|hours?|min|sec|\u5929|\u65f6|\u5206|\u79d2)'
        
        for element in elements:
            text_lower = element.text.lower()
            
            # Find buy button
            if element.element_type in ("button", "link") and not element.disabled:
                for keyword in buy_keywords:
                    if keyword in text_lower:
                        result["buy_button"] = element
                        break
            
            # Find countdown
            if re.search(countdown_pattern, element.text, re.IGNORECASE):
                result["countdown"] = element.text
            
            # Find quantity input
            if element.element_type in ("spinbutton", "textbox"):
                if any(q in text_lower for q in ["quantity", "qty", "数量"]):
                    result["quantity_input"] = element
        
        return result
    
    def prepare_rapid_click_targets(
        self, 
        snapshot: str,
        keywords: List[str] = None,
    ) -> List[str]:
        """
        Prepare list of UIDs for rapid clicking (flash sale scenario).
        
        Args:
            snapshot: Page snapshot text
            keywords: Target button keywords
            
        Returns:
            List of element UIDs to click
        """
        if keywords is None:
            keywords = ["buy", "rush", "grab", "抢购", "立即", "秒杀"]
        
        targets = []
        elements = SnapshotParser.parse(snapshot)
        
        for element in elements:
            if element.element_type not in ("button", "link"):
                continue
            
            text_lower = element.text.lower()
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    targets.append(element.uid)
                    break
        
        return targets
    
    def find_captcha_element(self, snapshot: str) -> Optional[PageElement]:
        """
        Detect if page has CAPTCHA/verification.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PageElement for CAPTCHA area or None
        """
        captcha_keywords = [
            "captcha", "verification", "verify", "robot", "human",
            "验证码", "滑动验证", "拖动", "点击验证",
        ]
        
        elements = SnapshotParser.parse(snapshot)
        
        for element in elements:
            text_lower = element.text.lower()
            for keyword in captcha_keywords:
                if keyword in text_lower:
                    return element
        
        return None
