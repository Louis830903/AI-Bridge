"""
Monitor Tasks - Information Monitoring Automation

Provides tasks for:
- Price tracking: Track product prices, alert on changes
- Stock monitoring: Check inventory status, notify on restock
- News aggregation: Collect headlines from multiple sources
- Content change detection: Compare page content over time
"""

import re
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from datetime import datetime

from .base import BaseTask, TaskConfig, TaskResult, TaskStatus
from ..engine import SnapshotParser, PageElement
from ..semantics import ActionSemantics


@dataclass
class PriceInfo:
    """Price information extracted from page"""
    value: float
    currency: str = ""
    original_price: Optional[float] = None
    discount: Optional[str] = None
    
    @property
    def has_discount(self) -> bool:
        return self.original_price is not None and self.original_price > self.value


@dataclass
class StockStatus:
    """Stock status information"""
    in_stock: bool
    quantity: Optional[int] = None
    message: str = ""


@dataclass
class NewsItem:
    """News/article item"""
    title: str
    url: Optional[str] = None
    source: str = ""
    timestamp: Optional[datetime] = None
    score: Optional[int] = None


@dataclass
class MonitorResult:
    """Result of monitoring operation"""
    success: bool
    data: Any = None
    changed: bool = False
    previous_value: Any = None
    current_value: Any = None
    message: str = ""


class MonitorTask(BaseTask):
    """
    Monitor task for tracking prices, stock, news, and content changes.
    
    Example:
        task = MonitorTask()
        
        # Extract price from page snapshot
        price = task.extract_price(snapshot)
        
        # Check stock status
        status = task.detect_stock(snapshot)
        
        # Extract news headlines
        news = task.extract_headlines(snapshot)
    """
    
    # 默认货币，可通过构造函数配置
    DEFAULT_CURRENCY = "CNY"
    
    # Currency patterns
    CURRENCY_PATTERNS = {
        "CNY": [r"[\u00a5\uffe5]", r"\u5143", r"RMB"],
        "USD": [r"\$", r"USD"],
        "EUR": [r"\u20ac", r"EUR"],
        "GBP": [r"\u00a3", r"GBP"],
    }
    
    # Price extraction pattern
    PRICE_PATTERN = re.compile(
        r'(?:[\u00a5\uffe5$\u20ac\u00a3]|RMB|USD|EUR|GBP)?\s*'
        r'([\d,]+\.?\d*)'
        r'\s*(?:\u5143|\u8d77)?',
        re.IGNORECASE
    )
    
    def extract_price(self, snapshot: str) -> Optional[PriceInfo]:
        """
        Extract price information from page snapshot.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PriceInfo object or None if no price found
        """
        elements = SnapshotParser.parse(snapshot)
        price_keywords = ActionSemantics.get_action_keywords("price")
        
        prices = []
        
        for element in elements:
            text = element.text
            
            # Check if element contains price-related keywords
            is_price_context = any(
                kw.lower() in text.lower() for kw in price_keywords
            )
            
            # Extract numbers that look like prices
            matches = self.PRICE_PATTERN.findall(text)
            for match in matches:
                try:
                    value = float(match.replace(',', ''))
                    if value > 0:
                        prices.append((value, is_price_context, text))
                except ValueError:
                    continue
        
        if not prices:
            return None
        
        # Prefer prices in price context
        prices_in_context = [p for p in prices if p[1]]
        if prices_in_context:
            best_price = min(prices_in_context, key=lambda x: x[0])
        else:
            best_price = min(prices, key=lambda x: x[0])
        
        # Detect currency
        currency = self._detect_currency(best_price[2])
        
        return PriceInfo(value=best_price[0], currency=currency)
    
    def _detect_currency(self, text: str, default: Optional[str] = None) -> str:
        """
        Detect currency from text.
        
        Args:
            text: Text containing currency symbol
            default: Default currency if not detected
            
        Returns:
            Currency code (CNY, USD, EUR, GBP)
        """
        for currency, patterns in self.CURRENCY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return currency
        return default or self.DEFAULT_CURRENCY
    
    def detect_stock(self, snapshot: str) -> StockStatus:
        """
        Detect stock/inventory status from page snapshot.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            StockStatus object
        """
        elements = SnapshotParser.parse(snapshot)
        stock_keywords = ActionSemantics.get_action_keywords("stock")
        
        # Positive indicators (in stock)
        positive = {"in stock", "available", "buy now", "add to cart",
                    "有货", "现货", "立即购买", "加入购物车", "库存充足"}
        
        # Negative indicators (out of stock)
        negative = {"out of stock", "sold out", "unavailable", "notify me",
                    "无货", "缺货", "售罄", "已售罄", "到货通知", "补货中"}
        
        for element in elements:
            text_lower = element.text.lower()
            
            # Check for negative indicators first
            for indicator in negative:
                if indicator in text_lower:
                    return StockStatus(in_stock=False, message=element.text)
            
            # Check for positive indicators
            for indicator in positive:
                if indicator in text_lower:
                    return StockStatus(in_stock=True, message=element.text)
        
        # Check for clickable buy button
        buy_buttons = self.find_elements_by_text(
            snapshot, 
            ["buy", "purchase", "add to cart", "购买", "立即购买", "加入购物车"],
            element_types=["button", "link"]
        )
        
        if buy_buttons:
            # Check if button is disabled
            for btn in buy_buttons:
                if not btn.disabled:
                    return StockStatus(in_stock=True, message="Buy button available")
        
        return StockStatus(in_stock=False, message="Unable to determine stock status")
    
    def extract_headlines(
        self, 
        snapshot: str, 
        max_count: int = 20
    ) -> List[NewsItem]:
        """
        Extract news headlines from page snapshot.
        
        Works with common news sites, aggregators like HN, Reddit, etc.
        
        Args:
            snapshot: Page snapshot text
            max_count: Maximum number of headlines to extract
            
        Returns:
            List of NewsItem objects
        """
        elements = SnapshotParser.parse(snapshot)
        headlines = []
        
        # Look for links with substantial text (likely headlines)
        for element in elements:
            if len(headlines) >= max_count:
                break
            
            # Headlines are typically links with decent length
            if element.element_type == "link" and element.text:
                text = element.text.strip()
                
                # Filter out navigation, short text, and common non-headline patterns
                if len(text) < 10 or len(text) > 300:
                    continue
                
                skip_patterns = [
                    "login", "sign in", "register", "subscribe",
                    "登录", "注册", "订阅", "更多", "查看更多",
                    "next", "previous", "page", "comment",
                ]
                
                if any(p in text.lower() for p in skip_patterns):
                    continue
                
                # Extract score if present (HN, Reddit style)
                score = self._extract_score(elements, element)
                
                headlines.append(NewsItem(
                    title=text,
                    url=element.url,
                    score=score,
                ))
        
        return headlines
    
    def _extract_score(
        self, 
        elements: List[PageElement], 
        headline_element: PageElement
    ) -> Optional[int]:
        """Try to extract score/points for a headline"""
        # Look for nearby elements with numbers followed by "points", "votes", etc.
        score_pattern = re.compile(r'(\d+)\s*(?:points?|votes?|upvotes?|\u8d5e|\u70b9)')
        
        for element in elements:
            match = score_pattern.search(element.text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def compare_content(
        self, 
        old_snapshot: str, 
        new_snapshot: str
    ) -> List[str]:
        """
        Compare two snapshots and return list of changes.
        
        Args:
            old_snapshot: Previous snapshot
            new_snapshot: Current snapshot
            
        Returns:
            List of change descriptions
        """
        old_elements = SnapshotParser.parse(old_snapshot)
        new_elements = SnapshotParser.parse(new_snapshot)
        
        old_texts = {e.text for e in old_elements if e.text}
        new_texts = {e.text for e in new_elements if e.text}
        
        changes = []
        
        # Find added content
        added = new_texts - old_texts
        for text in list(added)[:5]:  # Limit to 5 changes
            if len(text) > 10:
                changes.append(f"Added: {text[:100]}...")
        
        # Find removed content
        removed = old_texts - new_texts
        for text in list(removed)[:5]:
            if len(text) > 10:
                changes.append(f"Removed: {text[:100]}...")
        
        return changes
    
    def content_hash(self, snapshot: str, algorithm: str = "md5") -> str:
        """
        Generate hash of page content for quick comparison.
        
        Args:
            snapshot: Page snapshot text
            algorithm: Hash algorithm ('md5' or 'sha256')
            
        Returns:
            Hash string
            
        Note:
            MD5 is used for quick comparison only, not for security purposes.
            Use sha256 if cryptographic security is required.
        """
        elements = SnapshotParser.parse(snapshot)
        content = "".join(e.text for e in elements if e.text)
        
        if algorithm == "sha256":
            return hashlib.sha256(content.encode()).hexdigest()
        return hashlib.md5(content.encode()).hexdigest()
    
    def track_price(
        self,
        snapshot: str,
        target_price: Optional[float] = None,
        previous_price: Optional[float] = None,
    ) -> MonitorResult:
        """
        Track price and check for changes or target match.
        
        Args:
            snapshot: Page snapshot
            target_price: Alert if price drops to/below this
            previous_price: Previous price for comparison
            
        Returns:
            MonitorResult with price info
        """
        price_info = self.extract_price(snapshot)
        
        if not price_info:
            return MonitorResult(
                success=False,
                message="Could not extract price from page"
            )
        
        result = MonitorResult(
            success=True,
            data=price_info,
            current_value=price_info.value,
            previous_value=previous_price,
        )
        
        # Check for price change
        if previous_price is not None:
            result.changed = abs(price_info.value - previous_price) > 0.01
            if result.changed:
                diff = price_info.value - previous_price
                result.message = f"Price changed: {previous_price} -> {price_info.value} ({diff:+.2f})"
        
        # Check target price
        if target_price is not None and price_info.value <= target_price:
            result.message = f"Target price reached! Current: {price_info.value}, Target: {target_price}"
        
        return result
    
    def monitor_stock(
        self,
        snapshot: str,
        previous_status: Optional[bool] = None,
    ) -> MonitorResult:
        """
        Monitor stock status and detect changes.
        
        Args:
            snapshot: Page snapshot
            previous_status: Previous in_stock status
            
        Returns:
            MonitorResult with stock info
        """
        status = self.detect_stock(snapshot)
        
        result = MonitorResult(
            success=True,
            data=status,
            current_value=status.in_stock,
            previous_value=previous_status,
        )
        
        if previous_status is not None:
            result.changed = status.in_stock != previous_status
            if result.changed:
                if status.in_stock:
                    result.message = "Item is now IN STOCK!"
                else:
                    result.message = "Item is now OUT OF STOCK"
        else:
            result.message = "In stock" if status.in_stock else "Out of stock"
        
        return result
