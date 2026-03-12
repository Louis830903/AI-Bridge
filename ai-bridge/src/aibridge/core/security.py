"""
Security Policy - 安全沙箱和权限控制

提供企业级的安全控制，包括:
- 域名白名单/黑名单
- 操作权限控制
- 敏感操作确认
- 资源使用限制

使用示例:
```python
# 创建带安全策略的适配器
adapter = ChromeAdapter(
    security_policy={
        "allowlist": ["*.baidu.com", "*.github.com"],
        "blocked_actions": ["download", "upload"],
        "require_confirmation_for": ["click", "type"]
    }
)
```
"""

import asyncio

# 敏感操作需要确认
await adapter.execute("click", target={"css": "#submit"}, options={"require_confirmation": True})
```
"""

import fnmatch
import logging
from typing import Any, Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class PermissionLevel(str, Enum):
    """权限级别"""
    ALLOW = "allow"           # 允许
    DENY = "deny"             # 拒绝
    CONFIRM = "confirm"       # 需要确认
    LOG = "log"               # 仅记录


@dataclass
class SecurityPolicy:
    """安全策略配置"""
    # 域名控制
    allowlist: List[str] = field(default_factory=list)      # 允许的域名
    blocklist: List[str] = field(default_factory=list)      # 禁止的域名
    
    # 操作控制
    allowed_actions: Optional[List[str]] = None              # 允许的操作列表，None表示全部
    blocked_actions: List[str] = field(default_factory=list) # 禁止的操作列表
    
    # 敏感操作确认
    require_confirmation_for: List[str] = field(default_factory=list)
    
    # 资源限制
    max_page_loads: int = 100                               # 最大页面加载次数
    max_storage_mb: float = 100.0                          # 最大存储使用(MB)
    max_execution_time_ms: int = 300000                    # 最大执行时间(5分钟)
    
    # 日志和审计
    audit_log: bool = True                                  # 是否记录审计日志
    audit_actions: List[str] = field(default_factory=lambda: ["goto", "click", "type"])


class SecurityManager:
    """
    安全管理器
    
    负责执行安全策略和权限控制。
    """
    
    # 敏感操作列表
    SENSITIVE_ACTIONS = {
        "download": "下载文件",
        "upload": "上传文件",
        "execute": "执行脚本",
        "eval": "执行代码",
        "set_cookie": "设置 Cookie",
        "clear_storage": "清除存储",
    }
    
    def __init__(self, policy: Optional[SecurityPolicy] = None):
        """
        初始化安全管理器
        
        Args:
            policy: 安全策略配置
        """
        self.policy = policy or SecurityPolicy()
        self.stats = {
            "actions_checked": 0,
            "actions_blocked": 0,
            "actions_confirmed": 0,
            "pages_loaded": 0,
        }
        self.confirmation_callback: Optional[Callable] = None
        self.audit_logs: List[Dict] = []
    
    def set_confirmation_callback(self, callback: Callable[[str, Dict], bool]):
        """
        设置确认回调函数
        
        Args:
            callback: 接收 (action, params) 返回 bool 的函数
        """
        self.confirmation_callback = callback
    
    def check_url_access(self, url: str) -> Dict[str, Any]:
        """
        检查 URL 访问权限
        
        Args:
            url: 目标 URL
        
        Returns:
            检查结果
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            
            # 检查黑名单
            for pattern in self.policy.blocklist:
                if self._match_pattern(hostname, pattern):
                    return {
                        "allowed": False,
                        "reason": f"域名 {hostname} 在黑名单中 (匹配: {pattern})",
                        "level": PermissionLevel.DENY
                    }
            
            # 检查白名单
            if self.policy.allowlist:
                allowed = False
                for pattern in self.policy.allowlist:
                    if self._match_pattern(hostname, pattern):
                        allowed = True
                        break
                
                if not allowed:
                    return {
                        "allowed": False,
                        "reason": f"域名 {hostname} 不在白名单中",
                        "level": PermissionLevel.DENY
                    }
            
            return {
                "allowed": True,
                "reason": "域名检查通过",
                "level": PermissionLevel.ALLOW
            }
            
        except Exception as e:
            logger.error(f"URL 检查失败: {e}")
            return {
                "allowed": False,
                "reason": f"检查异常: {e}",
                "level": PermissionLevel.DENY
            }
    
    def check_action_permission(
        self,
        action: str,
        params: Optional[Dict] = None,
        require_explicit_confirm: bool = False
    ) -> Dict[str, Any]:
        """
        检查操作权限
        
        Args:
            action: 操作名称
            params: 操作参数
            require_explicit_confirm: 是否需要显式确认
        
        Returns:
            检查结果
        """
        self.stats["actions_checked"] += 1
        
        # 检查是否在禁止列表
        if action in self.policy.blocked_actions:
            self.stats["actions_blocked"] += 1
            return {
                "allowed": False,
                "reason": f"操作 '{action}' 被安全策略禁止",
                "level": PermissionLevel.DENY
            }
        
        # 检查是否在允许列表（如果配置了允许列表）
        if self.policy.allowed_actions is not None:
            if action not in self.policy.allowed_actions:
                self.stats["actions_blocked"] += 1
                return {
                    "allowed": False,
                    "reason": f"操作 '{action}' 不在允许列表中",
                    "level": PermissionLevel.DENY
                }
        
        # 检查是否需要确认
        needs_confirm = (
            require_explicit_confirm or
            action in self.policy.require_confirmation_for or
            action in self.SENSITIVE_ACTIONS
        )
        
        if needs_confirm:
            return {
                "allowed": True,
                "requires_confirmation": True,
                "reason": f"操作 '{action}' 需要确认",
                "level": PermissionLevel.CONFIRM
            }
        
        return {
            "allowed": True,
            "requires_confirmation": False,
            "reason": "操作检查通过",
            "level": PermissionLevel.ALLOW
        }
    
    async def confirm_action(self, action: str, params: Dict) -> bool:
        """
        请求操作确认
        
        Args:
            action: 操作名称
            params: 操作参数
        
        Returns:
            是否确认执行
        """
        self.stats["actions_confirmed"] += 1
        
        # 如果有回调函数，使用回调
        if self.confirmation_callback:
            try:
                result = self.confirmation_callback(action, params)
                if asyncio.iscoroutine(result):
                    return await result
                return result
            except Exception as e:
                logger.error(f"确认回调异常: {e}")
                return False
        
        # 默认行为：记录日志并允许（生产环境应该拒绝）
        logger.warning(f"需要确认但没有设置回调: {action}")
        return True
    
    def log_action(self, action: str, params: Dict, result: Dict):
        """
        记录操作审计日志
        
        Args:
            action: 操作名称
            params: 操作参数
            result: 执行结果
        """
        if not self.policy.audit_log:
            return
        
        if action not in self.policy.audit_actions:
            return
        
        from datetime import datetime
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "params": self._sanitize_params(params),
            "success": result.get("success", False),
            "error": result.get("error")
        }
        
        self.audit_logs.append(log_entry)
        
        # 同时输出到日志
        logger.info(f"[AUDIT] {action}: success={log_entry['success']}")
    
    def check_resource_limits(self) -> Dict[str, Any]:
        """检查资源限制"""
        violations = []
        
        # 检查页面加载次数
        if self.stats["pages_loaded"] >= self.policy.max_page_loads:
            violations.append(f"页面加载次数超过限制 ({self.policy.max_page_loads})")
        
        if violations:
            return {
                "allowed": False,
                "violations": violations
            }
        
        return {
            "allowed": True
        }
    
    def _match_pattern(self, text: str, pattern: str) -> bool:
        """
        匹配模式（支持通配符）
        
        Args:
            text: 要匹配的文本
            pattern: 模式（如 *.baidu.com）
        
        Returns:
            是否匹配
        """
        # 处理 *.example.com 匹配 sub.example.com
        if pattern.startswith("*."):
            domain_suffix = pattern[2:]
            return text == domain_suffix or text.endswith("." + domain_suffix)
        
        return fnmatch.fnmatch(text, pattern)
    
    def _sanitize_params(self, params: Dict) -> Dict:
        """
        清理敏感参数
        
        移除密码、token 等敏感信息。
        """
        if not params:
            return params
        
        sensitive_keys = ['password', 'token', 'secret', 'key', 'auth', 'credential']
        sanitized = {}
        
        for k, v in params.items():
            if any(sk in k.lower() for sk in sensitive_keys):
                sanitized[k] = "***REDACTED***"
            elif isinstance(v, dict):
                sanitized[k] = self._sanitize_params(v)
            else:
                sanitized[k] = v
        
        return sanitized

    def get_stats(self) -> Dict:
        """获取安全统计"""
        return self.stats.copy()
    
    def get_audit_logs(self) -> List[Dict]:
        """获取审计日志"""
        return self.audit_logs.copy()


class SecureAdapterWrapper:
    """
    安全适配器包装器
    
    包装现有适配器，添加安全控制。
    """
    
    def __init__(self, adapter, security_policy: Optional[SecurityPolicy] = None):
        """
        初始化安全包装器
        
        Args:
            adapter: 原始适配器
            security_policy: 安全策略
        """
        self.adapter = adapter
        self.security = SecurityManager(security_policy)
    
    async def execute(self, action: str, target=None, value=None, options=None):
        """
        安全执行操作
        
        在执行前进行权限检查。
        """
        options = options or {}
        
        # 1. 检查资源限制
        limit_check = self.security.check_resource_limits()
        if not limit_check["allowed"]:
            return {
                "success": False,
                "error": f"资源限制 exceeded: {limit_check['violations']}"
            }
        
        # 2. 如果是导航操作，检查 URL
        if action == "goto" and target:
            url = target.get("url") if isinstance(target, dict) else target
            if url:
                url_check = self.security.check_url_access(url)
                if not url_check["allowed"]:
                    return {
                        "success": False,
                        "error": url_check["reason"]
                    }
                
                self.security.stats["pages_loaded"] += 1
        
        # 3. 检查操作权限
        permission = self.security.check_action_permission(
            action,
            {"target": target, "value": value},
            options.get("require_confirmation", False)
        )
        
        if not permission["allowed"]:
            return {
                "success": False,
                "error": permission["reason"]
            }
        
        # 4. 如果需要确认
        if permission.get("requires_confirmation"):
            confirmed = await self.security.confirm_action(
                action,
                {"target": target, "value": value}
            )
            if not confirmed:
                return {
                    "success": False,
                    "error": "操作被用户取消"
                }
        
        # 5. 执行操作
        result = await self.adapter.execute(action, target, value, options)
        
        # 6. 记录审计日志
        self.security.log_action(action, {"target": target, "value": value}, result)
        
        return result
    
    def __getattr__(self, name):
        """代理其他属性访问到原始适配器"""
        return getattr(self.adapter, name)


# ============ 便捷函数 ============

def create_secure_adapter(adapter, **policy_kwargs):
    """
    创建安全适配器
    
    Args:
        adapter: 原始适配器
        **policy_kwargs: 安全策略参数
    
    Returns:
        安全包装后的适配器
    """
    policy = SecurityPolicy(**policy_kwargs)
    return SecureAdapterWrapper(adapter, policy)


async def demo():
    """演示安全功能"""
    from aibridge.adapters.browser.chrome import ChromeAdapter
    
    # 创建安全策略
    policy = SecurityPolicy(
        allowlist=["*.baidu.com", "*.github.com"],
        blocked_actions=["download"],
        require_confirmation_for=["click"],
        audit_log=True
    )
    
    # 创建适配器
    adapter = ChromeAdapter()
    await adapter.connect()
    
    # 包装为安全适配器
    secure = SecureAdapterWrapper(adapter, policy)
    
    # 测试允许的 URL
    print("\n测试允许的 URL...")
    result = await secure.execute("goto", target={"url": "https://www.baidu.com"})
    print(f"结果: {result['success']}")
    
    # 测试禁止的 URL
    print("\n测试禁止的 URL...")
    result = await secure.execute("goto", target={"url": "https://www.example.com"})
    print(f"结果: {result.get('error')}")
    
    # 查看审计日志
    print("\n审计日志:")
    for log in secure.security.get_audit_logs():
        print(f"  {log['timestamp']}: {log['action']} - {log['success']}")
    
    await adapter.disconnect()


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
