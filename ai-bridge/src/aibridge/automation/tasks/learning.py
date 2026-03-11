"""
Learning Tasks - Learning and Research Automation

Provides tasks for:
- Paper downloads: Find and download research papers
- Course auto-play: Automatically play online course videos
- Auto-pagination: Automatically turn pages for reading
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

from .base import BaseTask, TaskConfig, TaskResult, TaskStatus
from ..engine import SnapshotParser, PageElement
from ..semantics import ActionSemantics


@dataclass
class Paper:
    """Research paper information"""
    title: str
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    doi: Optional[str] = None
    year: Optional[int] = None
    download_uid: Optional[str] = None


@dataclass
class VideoInfo:
    """Video/course information"""
    title: str
    duration: Optional[str] = None
    progress: float = 0.0  # 0-100
    completed: bool = False
    play_uid: Optional[str] = None
    next_uid: Optional[str] = None


@dataclass
class ReadingProgress:
    """Reading/pagination progress"""
    current_page: int = 1
    total_pages: Optional[int] = None
    next_uid: Optional[str] = None
    prev_uid: Optional[str] = None
    progress_percent: float = 0.0


class LearningTask(BaseTask):
    """
    Learning and research automation tasks.
    
    Example:
        task = LearningTask()
        
        # Find papers on page
        papers = task.extract_papers(snapshot)
        
        # Find play button for video
        video = task.find_video_controls(snapshot)
        
        # Find next page button
        next_btn = task.find_next_page_button(snapshot)
    """
    
    def extract_papers(
        self, 
        snapshot: str,
        max_count: int = 20,
    ) -> List[Paper]:
        """
        Extract paper information from search results page.
        
        Works with common academic sites like:
        - Google Scholar
        - arXiv
        - IEEE Xplore
        - ACM Digital Library
        
        Args:
            snapshot: Page snapshot text
            max_count: Maximum papers to extract
            
        Returns:
            List of Paper objects
        """
        elements = SnapshotParser.parse(snapshot)
        papers = []
        
        # PDF/download indicators
        pdf_keywords = {"pdf", "download", "full text", "下载", "全文"}
        
        current_paper = None
        
        for element in elements:
            if len(papers) >= max_count:
                break
            
            # Look for paper titles (usually links with substantial text)
            if element.element_type == "link" and element.text:
                text = element.text.strip()
                
                # Paper titles are typically longer and don't contain common nav words
                if len(text) > 20 and len(text) < 300:
                    skip_patterns = ["login", "sign", "about", "contact", "home"]
                    if not any(p in text.lower() for p in skip_patterns):
                        # Check if this looks like a PDF link
                        if any(kw in text.lower() for kw in pdf_keywords):
                            if current_paper:
                                current_paper.pdf_url = element.url
                                current_paper.download_uid = element.uid
                        else:
                            # New paper entry
                            current_paper = Paper(
                                title=text,
                                url=element.url,
                            )
                            papers.append(current_paper)
            
            # Extract DOI if present
            if current_paper and element.text:
                doi_match = re.search(r'10\.\d{4,}/[^\s]+', element.text)
                if doi_match:
                    current_paper.doi = doi_match.group()
                
                # Extract year
                year_match = re.search(r'\b(19|20)\d{2}\b', element.text)
                if year_match:
                    current_paper.year = int(year_match.group())
        
        return papers
    
    def find_download_button(
        self, 
        snapshot: str,
        paper: Optional[Paper] = None,
    ) -> Optional[PageElement]:
        """
        Find PDF/download button on paper page.
        
        Args:
            snapshot: Page snapshot text
            paper: Optional Paper object for context
            
        Returns:
            PageElement for download button or None
        """
        download_keywords = ActionSemantics.get_action_keywords("download")
        
        extra_keywords = {
            "pdf", "full text", "download pdf", "get pdf",
            "下载PDF", "全文下载", "获取全文",
        }
        
        all_keywords = list(download_keywords | extra_keywords)
        
        return self.find_element_by_text(
            snapshot,
            all_keywords,
            element_types=["button", "link"]
        )
    
    def find_video_controls(self, snapshot: str) -> VideoInfo:
        """
        Find video player controls and status.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            VideoInfo with control elements
        """
        elements = SnapshotParser.parse(snapshot)
        
        video_info = VideoInfo(title="")
        play_keywords = ActionSemantics.get_action_keywords("play")
        
        # Duration pattern
        duration_pattern = re.compile(r'(\d{1,2}:\d{2}(?::\d{2})?)')
        
        for element in elements:
            text_lower = element.text.lower()
            
            # Find play/pause button
            if element.element_type in ("button", "link"):
                for keyword in play_keywords:
                    if keyword.lower() in text_lower:
                        video_info.play_uid = element.uid
                        break
            
            # Find video title (usually heading or prominent text)
            if element.element_type == "heading" and len(element.text) > 5:
                if not video_info.title:
                    video_info.title = element.text
            
            # Find duration
            duration_match = duration_pattern.search(element.text)
            if duration_match and not video_info.duration:
                video_info.duration = duration_match.group(1)
            
            # Find progress
            if "%" in element.text:
                progress_match = re.search(r'(\d+(?:\.\d+)?)\s*%', element.text)
                if progress_match:
                    video_info.progress = float(progress_match.group(1))
            
            # Find next video button
            if element.element_type in ("button", "link"):
                next_keywords = {"next", "下一个", "下一节", "下一课"}
                if any(kw in text_lower for kw in next_keywords):
                    video_info.next_uid = element.uid
        
        # Check if completed
        completed_indicators = {"completed", "finished", "已完成", "已学完"}
        all_text = " ".join(e.text.lower() for e in elements if e.text)
        video_info.completed = any(ind in all_text for ind in completed_indicators)
        
        return video_info
    
    def find_next_page_button(self, snapshot: str) -> Optional[PageElement]:
        """
        Find next page button for reading/pagination.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PageElement for next page button or None
        """
        next_keywords = ActionSemantics.get_action_keywords("next_page")
        
        return self.find_element_by_text(
            snapshot,
            list(next_keywords),
            element_types=["button", "link"]
        )
    
    def find_prev_page_button(self, snapshot: str) -> Optional[PageElement]:
        """
        Find previous page button.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PageElement for prev page button or None
        """
        prev_keywords = {
            "previous", "prev", "back", "last page",
            "上一页", "上一章", "返回",
            "←", "‹", "«",
        }
        
        return self.find_element_by_text(
            snapshot,
            list(prev_keywords),
            element_types=["button", "link"]
        )
    
    def get_reading_progress(self, snapshot: str) -> ReadingProgress:
        """
        Extract current reading/pagination progress.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            ReadingProgress object
        """
        elements = SnapshotParser.parse(snapshot)
        progress = ReadingProgress()
        
        # Page number patterns
        page_patterns = [
            r'page\s*(\d+)\s*(?:of|/)\s*(\d+)',
            r'(\d+)\s*/\s*(\d+)',
            r'第\s*(\d+)\s*页.*?共\s*(\d+)\s*页',
            r'(\d+)\s*页',
        ]
        
        all_text = " ".join(e.text for e in elements if e.text)
        
        for pattern in page_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                progress.current_page = int(groups[0])
                if len(groups) > 1 and groups[1]:
                    progress.total_pages = int(groups[1])
                break
        
        # Calculate progress percentage
        if progress.total_pages and progress.total_pages > 0:
            progress.progress_percent = (progress.current_page / progress.total_pages) * 100
        
        # Find navigation buttons
        next_btn = self.find_next_page_button(snapshot)
        if next_btn:
            progress.next_uid = next_btn.uid
        
        prev_btn = self.find_prev_page_button(snapshot)
        if prev_btn:
            progress.prev_uid = prev_btn.uid
        
        return progress
    
    def find_course_chapters(
        self, 
        snapshot: str,
        max_count: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Extract course chapter/lesson list.
        
        Args:
            snapshot: Page snapshot text
            max_count: Maximum chapters to extract
            
        Returns:
            List of chapter info dicts
        """
        elements = SnapshotParser.parse(snapshot)
        chapters = []
        
        # Chapter/lesson indicators
        chapter_keywords = {
            "chapter", "lesson", "section", "lecture", "unit", "module",
            "章", "节", "课", "单元", "讲",
        }
        
        for element in elements:
            if len(chapters) >= max_count:
                break
            
            text_lower = element.text.lower()
            
            # Check if this looks like a chapter entry
            is_chapter = any(kw in text_lower for kw in chapter_keywords)
            
            # Also check for numbered items
            numbered = re.match(r'^(\d+\.|\d+\s*[)）])', element.text.strip())
            
            if (is_chapter or numbered) and element.element_type in ("link", "button", "listitem"):
                # Check completion status
                completed = any(
                    ind in text_lower 
                    for ind in ["completed", "done", "finished", "已完成", "✓", "✔"]
                )
                
                chapters.append({
                    "title": element.text[:100],
                    "uid": element.uid,
                    "completed": completed,
                    "clickable": element.element_type in ("link", "button"),
                })
        
        return chapters
    
    def detect_video_platform(self, snapshot: str, url: str = "") -> str:
        """
        Detect video/learning platform from page.
        
        Args:
            snapshot: Page snapshot text
            url: Current URL
            
        Returns:
            Platform identifier
        """
        platform_indicators = {
            "youtube": ["youtube", "youtu.be"],
            "bilibili": ["bilibili", "b站"],
            "coursera": ["coursera"],
            "udemy": ["udemy"],
            "mooc": ["mooc", "中国大学"],
            "xuetangx": ["学堂在线", "xuetangx"],
        }
        
        # Check URL first
        url_lower = url.lower()
        for platform, indicators in platform_indicators.items():
            if any(ind in url_lower for ind in indicators):
                return platform
        
        # Fallback to page content
        elements = SnapshotParser.parse(snapshot)
        all_text = " ".join(e.text.lower() for e in elements if e.text)
        
        for platform, indicators in platform_indicators.items():
            if any(ind in all_text for ind in indicators):
                return platform
        
        return "unknown"
    
    def find_fullscreen_button(self, snapshot: str) -> Optional[PageElement]:
        """
        Find fullscreen/theater mode button for video.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PageElement for fullscreen button or None
        """
        fullscreen_keywords = {
            "fullscreen", "full screen", "theater", "expand",
            "全屏", "剧场模式", "放大",
        }
        
        return self.find_element_by_text(
            snapshot,
            list(fullscreen_keywords),
            element_types=["button"]
        )
    
    def find_playback_speed(self, snapshot: str) -> Optional[PageElement]:
        """
        Find playback speed control.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PageElement for speed control or None
        """
        speed_keywords = {
            "speed", "playback speed", "1x", "1.5x", "2x",
            "倍速", "播放速度",
        }
        
        return self.find_element_by_text(
            snapshot,
            list(speed_keywords),
            element_types=["button", "combobox"]
        )
