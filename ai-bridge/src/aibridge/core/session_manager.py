"""
Session Manager - 会话持久化管理

支持保存和恢复浏览器会话，包括:
- Cookies
- LocalStorage
- SessionStorage
- 页面状态

使用示例:
```python
# 保存会话
await adapter.save_session(
    name="jd_account",
    include_cookies=True,
    include_storage=True
)

# 恢复会话
await adapter.load_session("jd_account")
```
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SessionData:
    """会话数据结构"""
    name: str
    created_at: str
    updated_at: str
    url: str
    title: str
    cookies: List[Dict] = field(default_factory=list)
    local_storage: Dict[str, Any] = field(default_factory=dict)
    session_storage: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """
    会话管理器
    
    负责保存和恢复浏览器会话状态。
    """
    
    DEFAULT_SESSIONS_DIR = Path.home() / ".aibridge" / "sessions"
    
    def __init__(self, adapter, sessions_dir: Optional[str] = None):
        """
        初始化会话管理器
        
        Args:
            adapter: ChromeAdapter 实例
            sessions_dir: 会话存储目录，默认 ~/.aibridge/sessions
        """
        self.adapter = adapter
        self.sessions_dir = Path(sessions_dir) if sessions_dir else self.DEFAULT_SESSIONS_DIR
        self._ensure_sessions_dir()
    
    def _ensure_sessions_dir(self):
        """确保会话目录存在"""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_session_file(self, name: str) -> Path:
        """获取会话文件路径"""
        # 清理名称，只保留字母数字和下划线
        safe_name = "".join(c for c in name if c.isalnum() or c in "_-").lower()
        return self.sessions_dir / f"{safe_name}.json"
    
    async def save_session(
        self,
        name: str,
        include_cookies: bool = True,
        include_storage: bool = True,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        保存当前会话
        
        Args:
            name: 会话名称
            include_cookies: 是否保存 cookies
            include_storage: 是否保存 storage
            metadata: 额外元数据
        
        Returns:
            保存结果
        """
        try:
            if not self.adapter._page:
                return {"success": False, "error": "页面未初始化"}
            
            page = self.adapter._page
            
            # 获取当前页面信息
            url = page.url
            title = await page.title()
            
            # 获取 cookies
            cookies = []
            if include_cookies:
                try:
                    cookies = await page.context.cookies()
                except Exception as e:
                    logger.warning(f"获取 cookies 失败: {e}")
            
            # 获取 storage
            local_storage = {}
            session_storage = {}
            if include_storage:
                try:
                    local_storage = await page.evaluate("() => Object.assign({}, localStorage)")
                    session_storage = await page.evaluate("() => Object.assign({}, sessionStorage)")
                except Exception as e:
                    logger.warning(f"获取 storage 失败: {e}")
            
            # 构建会话数据
            now = datetime.now().isoformat()
            session_data = SessionData(
                name=name,
                created_at=now,
                updated_at=now,
                url=url,
                title=title,
                cookies=cookies,
                local_storage=local_storage,
                session_storage=session_storage,
                metadata=metadata or {}
            )
            
            # 保存到文件
            session_file = self._get_session_file(name)
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(session_data), f, ensure_ascii=False, indent=2)
            
            logger.info(f"会话已保存: {name} -> {session_file}")
            
            return {
                "success": True,
                "name": name,
                "file": str(session_file),
                "url": url,
                "title": title,
                "cookies_count": len(cookies),
                "local_storage_keys": len(local_storage),
                "session_storage_keys": len(session_storage)
            }
            
        except Exception as e:
            logger.error(f"保存会话失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def load_session(self, name: str) -> Dict[str, Any]:
        """
        加载会话
        
        Args:
            name: 会话名称
        
        Returns:
            加载结果
        """
        try:
            session_file = self._get_session_file(name)
            
            if not session_file.exists():
                return {
                    "success": False,
                    "error": f"会话不存在: {name}"
                }
            
            # 读取会话数据
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            session_data = SessionData(**data)
            
            if not self.adapter._page:
                return {"success": False, "error": "页面未初始化"}
            
            page = self.adapter._page
            context = page.context
            
            # 导航到保存的 URL
            await page.goto(session_data.url)
            
            # 恢复 cookies
            if session_data.cookies:
                try:
                    await context.add_cookies(session_data.cookies)
                    logger.info(f"已恢复 {len(session_data.cookies)} 个 cookies")
                except Exception as e:
                    logger.warning(f"恢复 cookies 失败: {e}")
            
            # 恢复 localStorage
            if session_data.local_storage:
                try:
                    for key, value in session_data.local_storage.items():
                        await page.evaluate(f'localStorage.setItem("{key}", JSON.stringify({json.dumps(value)}))')
                    logger.info(f"已恢复 {len(session_data.local_storage)} 个 localStorage 项")
                except Exception as e:
                    logger.warning(f"恢复 localStorage 失败: {e}")
            
            # 恢复 sessionStorage
            if session_data.session_storage:
                try:
                    for key, value in session_data.session_storage.items():
                        await page.evaluate(f'sessionStorage.setItem("{key}", JSON.stringify({json.dumps(value)}))')
                    logger.info(f"已恢复 {len(session_data.session_storage)} 个 sessionStorage 项")
                except Exception as e:
                    logger.warning(f"恢复 sessionStorage 失败: {e}")
            
            logger.info(f"会话已加载: {name}")
            
            return {
                "success": True,
                "name": name,
                "url": session_data.url,
                "title": session_data.title,
                "cookies_count": len(session_data.cookies),
                "local_storage_keys": len(session_data.local_storage),
                "session_storage_keys": len(session_data.session_storage),
                "metadata": session_data.metadata
            }
            
        except Exception as e:
            logger.error(f"加载会话失败: {e}")
            return {"success": False, "error": str(e)}
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有保存的会话"""
        sessions = []
        
        try:
            for session_file in self.sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    sessions.append({
                        "name": data.get("name"),
                        "url": data.get("url"),
                        "title": data.get("title"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "file": str(session_file)
                    })
                except Exception as e:
                    logger.warning(f"读取会话文件失败 {session_file}: {e}")
            
            # 按更新时间排序
            sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            
        except Exception as e:
            logger.error(f"列出会话失败: {e}")
        
        return sessions
    
    def delete_session(self, name: str) -> Dict[str, Any]:
        """删除会话"""
        try:
            session_file = self._get_session_file(name)
            
            if not session_file.exists():
                return {
                    "success": False,
                    "error": f"会话不存在: {name}"
                }
            
            session_file.unlink()
            logger.info(f"会话已删除: {name}")
            
            return {"success": True, "name": name}
            
        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            return {"success": False, "error": str(e)}


# ============ 便捷函数 ============

async def demo():
    """演示会话管理"""
    from aibridge.adapters.browser.chrome import ChromeAdapter
    
    adapter = ChromeAdapter()
    await adapter.connect()
    
    # 创建会话管理器
    session_mgr = SessionManager(adapter)
    
    # 导航到百度并登录（模拟）
    await adapter.execute("goto", target={"url": "https://www.baidu.com"})
    
    # 保存会话
    print("\n保存会话...")
    result = await session_mgr.save_session(
        name="baidu_demo",
        metadata={"description": "百度演示会话"}
    )
    print(f"保存结果: {result}")
    
    # 列出会话
    print("\n列出所有会话:")
    sessions = session_mgr.list_sessions()
    for s in sessions:
        print(f"  - {s['name']}: {s['title']}")
    
    await adapter.disconnect()


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
