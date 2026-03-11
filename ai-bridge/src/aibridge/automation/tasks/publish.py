"""
Publish Tasks - Content Distribution

Provides tasks for:
- Multi-platform publishing: Post content to multiple platforms
- Comment management: Batch reply, moderate comments
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

from .base import BaseTask, TaskConfig, TaskResult, TaskStatus
from ..engine import SnapshotParser, PageElement
from ..semantics import ActionSemantics, identify_platform


@dataclass
class PublishTarget:
    """Target platform for publishing"""
    platform: str
    url: str
    authenticated: bool = False
    character_limit: Optional[int] = None
    supports_images: bool = True
    supports_markdown: bool = False


@dataclass
class Comment:
    """Comment/reply extracted from page"""
    uid: str
    author: str
    content: str
    timestamp: Optional[str] = None
    likes: int = 0
    reply_uid: Optional[str] = None  # UID for reply button


@dataclass
class PublishResult:
    """Result of publishing operation"""
    success: bool
    platform: str
    post_url: Optional[str] = None
    message: str = ""


# Platform configurations
PUBLISH_PLATFORMS = {
    "twitter": PublishTarget(
        platform="twitter",
        url="https://twitter.com/compose/tweet",
        character_limit=280,
        supports_images=True,
    ),
    "linkedin": PublishTarget(
        platform="linkedin",
        url="https://www.linkedin.com/feed/",
        character_limit=3000,
        supports_images=True,
    ),
    "weibo": PublishTarget(
        platform="weibo",
        url="https://weibo.com/",
        character_limit=2000,
        supports_images=True,
    ),
    "zhihu": PublishTarget(
        platform="zhihu",
        url="https://www.zhihu.com/",
        character_limit=None,
        supports_markdown=True,
    ),
    "devto": PublishTarget(
        platform="devto",
        url="https://dev.to/new",
        character_limit=None,
        supports_markdown=True,
    ),
    "medium": PublishTarget(
        platform="medium",
        url="https://medium.com/new-story",
        character_limit=None,
        supports_markdown=True,
    ),
}


class PublishTask(BaseTask):
    """
    Content publishing and comment management tasks.
    
    Example:
        task = PublishTask()
        
        # Find compose box
        box = task.find_compose_box(snapshot)
        
        # Extract comments
        comments = task.extract_comments(snapshot)
    """
    
    def find_compose_box(self, snapshot: str) -> Optional[PageElement]:
        """
        Find the main content composition input area.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PageElement for compose box or None
        """
        elements = SnapshotParser.parse(snapshot)
        
        # Compose box keywords
        compose_keywords = {
            "compose", "write", "post", "share", "what's happening",
            "what's on your mind", "start a post", "write something",
            "发布", "写点什么", "分享新鲜事", "说点什么",
        }
        
        # Look for textbox/textarea elements
        for element in elements:
            if element.element_type in ("textbox", "textarea"):
                text_lower = element.text.lower()
                for keyword in compose_keywords:
                    if keyword in text_lower:
                        return element
        
        # Fallback: find any large text input
        for element in elements:
            if element.element_type in ("textbox", "textarea"):
                return element
        
        return None
    
    def find_publish_button(self, snapshot: str) -> Optional[PageElement]:
        """
        Find the publish/post button.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PageElement for publish button or None
        """
        publish_keywords = {
            "post", "publish", "send", "tweet", "share", "submit",
            "发布", "发送", "分享", "提交", "发表",
        }
        
        return self.find_element_by_text(
            snapshot,
            list(publish_keywords),
            element_types=["button"]
        )
    
    def find_image_upload(self, snapshot: str) -> Optional[PageElement]:
        """
        Find image/media upload button.
        
        Args:
            snapshot: Page snapshot text
            
        Returns:
            PageElement for upload button or None
        """
        upload_keywords = {
            "image", "photo", "media", "upload", "attach", "gallery",
            "图片", "照片", "媒体", "上传", "添加图片",
            "📷", "🖼️",
        }
        
        elements = SnapshotParser.parse(snapshot)
        
        for element in elements:
            if element.element_type in ("button", "link"):
                text_lower = element.text.lower()
                for keyword in upload_keywords:
                    if keyword in text_lower or keyword in element.text:
                        return element
        
        return None
    
    def extract_comments(
        self, 
        snapshot: str,
        max_count: int = 50,
    ) -> List[Comment]:
        """
        Extract comments from a page.
        
        Args:
            snapshot: Page snapshot text
            max_count: Maximum comments to extract
            
        Returns:
            List of Comment objects
        """
        elements = SnapshotParser.parse(snapshot)
        comments = []
        
        # Comment indicators
        comment_types = {"comment", "article", "listitem"}
        reply_keywords = {"reply", "respond", "回复", "评论"}
        
        current_comment = None
        
        for element in elements:
            # Look for reply buttons to identify comment boundaries
            if element.element_type in ("button", "link"):
                text_lower = element.text.lower()
                for keyword in reply_keywords:
                    if keyword in text_lower:
                        if current_comment:
                            current_comment.reply_uid = element.uid
                        break
            
            # Look for content that looks like comments
            if element.text and len(element.text) > 10:
                # Simple heuristic: substantial text that's not a heading
                if element.element_type not in ("heading", "button", "link"):
                    # Extract author from nearby elements (simplified)
                    comments.append(Comment(
                        uid=element.uid,
                        author="",
                        content=element.text[:500],
                    ))
                    current_comment = comments[-1]
                    
                    if len(comments) >= max_count:
                        break
        
        return comments
    
    def find_reply_input(
        self, 
        snapshot: str,
        comment: Comment,
    ) -> Optional[PageElement]:
        """
        Find reply input for a specific comment.
        
        Args:
            snapshot: Page snapshot text
            comment: Comment to reply to
            
        Returns:
            PageElement for reply input or None
        """
        # If comment has reply_uid, look for nearby textbox
        elements = SnapshotParser.parse(snapshot)
        
        for element in elements:
            if element.element_type in ("textbox", "textarea"):
                return element
        
        return None
    
    def adapt_content_for_platform(
        self, 
        content: str, 
        platform: str,
    ) -> str:
        """
        Adapt content for specific platform requirements.
        
        Args:
            content: Original content
            platform: Target platform name
            
        Returns:
            Adapted content string
        """
        config = PUBLISH_PLATFORMS.get(platform)
        
        if not config:
            return content
        
        result = content
        
        # Apply character limit
        if config.character_limit and len(result) > config.character_limit:
            # Truncate with ellipsis
            result = result[:config.character_limit - 3] + "..."
        
        # Platform-specific adaptations
        if platform == "twitter":
            # 确保 hashtags 格式正确：将“#tag”格式化
            result = self._format_twitter_content(result)
        elif platform == "linkedin":
            # 为可读性添加换行
            result = self._format_linkedin_content(result)
        elif platform == "weibo":
            # 处理中文特殊格式
            result = self._format_weibo_content(result)
        
        return result
    
    def _format_twitter_content(self, content: str) -> str:
        """
        Format content for Twitter.
        
        - Ensure hashtags are properly formatted
        - Convert mentions to @username format
        """
        import re
        # 确保 hashtag 前有空格（除非在开头）
        content = re.sub(r'([^\s])#', r'\1 #', content)
        return content
    
    def _format_linkedin_content(self, content: str) -> str:
        """
        Format content for LinkedIn.
        
        - Add line breaks for readability
        - Format lists properly
        """
        # 在句子结束处添加换行以提高可读性
        lines = content.split('\n')
        formatted_lines = []
        for line in lines:
            if line.strip():
                formatted_lines.append(line)
                # 在段落后添加空行
                if len(line) > 100:
                    formatted_lines.append('')
        return '\n'.join(formatted_lines)
    
    def _format_weibo_content(self, content: str) -> str:
        """
        Format content for Weibo.
        
        - Handle Chinese-specific formatting
        - Ensure proper spacing around hashtags
        """
        import re
        # 微博的 hashtag 格式是 #话题#
        content = re.sub(r'#(\S+?)(?:\s|$)', r'#\1# ', content)
        return content.strip()
    
    def detect_platform(self, snapshot: str, url: str = "") -> str:
        """
        Detect which platform the current page belongs to.
        
        Args:
            snapshot: Page snapshot text
            url: Current page URL
            
        Returns:
            Platform identifier string
        """
        if url:
            platform = identify_platform(url)
            if platform:
                return platform
        
        # Fallback: detect from page content
        elements = SnapshotParser.parse(snapshot)
        all_text = " ".join(e.text for e in elements if e.text).lower()
        
        platform_indicators = {
            "twitter": ["tweet", "retweet", "twitter"],
            "linkedin": ["linkedin", "connection"],
            "weibo": ["微博", "weibo"],
            "zhihu": ["知乎", "zhihu"],
        }
        
        for platform, indicators in platform_indicators.items():
            if any(ind in all_text for ind in indicators):
                return platform
        
        return "unknown"
    
    def find_delete_button(
        self, 
        snapshot: str,
        comment: Comment,
    ) -> Optional[PageElement]:
        """
        Find delete button for a comment (for moderation).
        
        Args:
            snapshot: Page snapshot text
            comment: Comment to delete
            
        Returns:
            PageElement for delete button or None
        """
        delete_keywords = {"delete", "remove", "hide", "删除", "移除", "隐藏"}
        
        return self.find_element_by_text(
            snapshot,
            list(delete_keywords),
            element_types=["button", "link"]
        )
    
    def get_platform_config(self, platform: str) -> Optional[PublishTarget]:
        """
        Get configuration for a platform.
        
        Args:
            platform: Platform identifier
            
        Returns:
            PublishTarget config or None
        """
        return PUBLISH_PLATFORMS.get(platform.lower())
