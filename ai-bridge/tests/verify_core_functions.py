#!/usr/bin/env python3
"""
AI-Bridge 核心功能验证脚本

验证浏览器自动化、安全机制等核心功能是否真正工作。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class CoreFunctionVerifier:
    """核心功能验证器"""
    
    def __init__(self):
        self.results = []
    
    def log(self, name: str, success: bool, message: str):
        """记录结果"""
        status = "✅" if success else "❌"
        self.results.append((name, success, message))
        print(f"   {status} {name}: {message}")
    
    async def verify_chrome_adapter(self):
        """验证 ChromeAdapter"""
        print("\n" + "="*60)
        print("🌐 验证 ChromeAdapter 浏览器自动化")
        print("="*60)
        
        from aibridge.adapters.browser.chrome import ChromeAdapter
        
        adapter = ChromeAdapter({"headless": True})  # 无头模式
        
        # 1. 检查可用性
        print("\n1️⃣  检查 Playwright 可用性...")
        try:
            available = await adapter.is_available()
            self.log("Playwright 可用", available, 
                    "已安装" if available else "未安装，请运行: playwright install chromium")
            if not available:
                return
        except Exception as e:
            self.log("Playwright 可用", False, f"检查异常: {e}")
            return
        
        # 2. 连接浏览器
        print("\n2️⃣  连接浏览器...")
        try:
            await adapter.connect()
            self.log("浏览器连接", adapter._connected, 
                    "成功启动" if adapter._connected else "启动失败")
        except Exception as e:
            self.log("浏览器连接", False, f"连接异常: {e}")
            return
        
        try:
            # 3. 导航测试
            print("\n3️⃣  导航测试 (百度)...")
            result = await adapter.execute("goto", value="https://www.baidu.com")
            self.log("页面导航", result.get("success", False), 
                    f"URL: {result.get('data', {}).get('url', 'N/A')}")
            
            # 4. 获取标题
            print("\n4️⃣  获取页面标题...")
            result = await adapter.execute("get_title")
            title = result.get("title", "")
            self.log("获取标题", bool(title), f"标题: {title[:30]}..." if title else "未获取到")
            
            # 5. 执行安全脚本（白名单机制）
            print("\n5️⃣  安全脚本执行 (白名单测试)...")
            result = await adapter.execute("execute", value="get_title")
            self.log("白名单脚本", result.get("success", False), 
                    f"脚本结果: {result.get('data', 'N/A')}")
            
            # 6. 测试拒绝非白名单脚本
            print("\n6️⃣  安全验证 (拒绝任意JS)...")
            result = await adapter.execute("execute", value="alert('test')")
            # 应该失败
            is_blocked = not result.get("success", True)
            self.log("JS注入防护", is_blocked, 
                    "正确阻止任意JS执行" if is_blocked else "警告：未阻止任意JS")
            
            # 7. A11y 快照
            print("\n7️⃣  A11y 树快照...")
            result = await adapter.execute("take_snapshot")
            if result.get("success"):
                elem_count = result.get("element_count", 0)
                self.log("A11y快照", True, f"获取到 {elem_count} 个元素")
            else:
                self.log("A11y快照", False, result.get("error", "未知错误"))
            
            # 8. 截图测试
            print("\n8️⃣  截图功能...")
            result = await adapter.execute("screenshot")
            has_screenshot = bool(result.get("screenshot"))
            self.log("截图功能", has_screenshot, 
                    f"Base64 大小: {len(result.get('screenshot', ''))//1024}KB" if has_screenshot else "截图失败")
            
            # 9. CSS 选择器验证
            print("\n9️⃣  CSS选择器安全验证...")
            # 测试正常选择器
            valid = adapter._validate_css_selector("#kw")
            self.log("正常选择器", valid, "允许 #kw")
            # 测试危险选择器
            dangerous = adapter._validate_css_selector("div; javascript:alert(1)")
            self.log("危险选择器阻止", not dangerous, 
                    "正确阻止注入" if not dangerous else "警告：未阻止危险选择器")
            
        finally:
            # 断开连接
            print("\n🔌 断开浏览器连接...")
            await adapter.disconnect()
    
    async def verify_security_framework(self):
        """验证安全框架"""
        print("\n" + "="*60)
        print("🔒 验证安全框架")
        print("="*60)
        
        from aibridge.core.security import SecurityPolicy, SecurityManager
        
        # 1. 创建安全策略
        print("\n1️⃣  创建安全策略...")
        policy = SecurityPolicy(
            allowlist=["*.baidu.com", "*.github.com"],
            blocklist=["*.evil.com"],
            blocked_actions=["download"],
            max_page_loads=10
        )
        manager = SecurityManager(policy)
        self.log("策略创建", True, f"白名单: {len(policy.allowlist)}, 黑名单: {len(policy.blocklist)}")
        
        # 2. URL 白名单测试
        print("\n2️⃣  URL 白名单验证...")
        result = manager.check_url_access("https://www.baidu.com")
        self.log("白名单放行", result["allowed"], "baidu.com 正确放行")
        
        # 3. URL 黑名单测试
        print("\n3️⃣  URL 黑名单验证...")
        result = manager.check_url_access("https://www.evil.com")
        self.log("黑名单阻止", not result["allowed"], "evil.com 正确阻止")
        
        # 4. 白名单外 URL 测试
        print("\n4️⃣  白名单外 URL 验证...")
        result = manager.check_url_access("https://www.google.com")
        self.log("白名单外阻止", not result["allowed"], "google.com 正确阻止（不在白名单）")
        
        # 5. 操作权限测试
        print("\n5️⃣  操作权限验证...")
        result = manager.check_action_permission("download")
        self.log("禁止操作阻止", not result["allowed"], "download 操作被正确阻止")
        
        # 6. 敏感操作确认
        print("\n6️⃣  敏感操作确认机制...")
        result = manager.check_action_permission("execute")
        needs_confirm = result.get("requires_confirmation", False)
        self.log("敏感操作确认", needs_confirm, "execute 需要确认")
        
        # 7. 资源限制测试
        print("\n7️⃣  资源限制验证...")
        for i in range(11):
            manager.stats["pages_loaded"] += 1
        result = manager.check_resource_limits()
        is_limited = not result["allowed"]
        self.log("资源限制", is_limited, "页面加载超限被正确阻止")
        
        # 8. 参数脱敏测试
        print("\n8️⃣  敏感参数脱敏...")
        params = {"username": "test", "password": "secret123", "token": "abc"}
        sanitized = manager._sanitize_params(params)
        password_hidden = sanitized.get("password") == "***REDACTED***"
        self.log("密码脱敏", password_hidden, 
                f"password: {sanitized.get('password', 'N/A')}")
    
    async def verify_mcp_server(self):
        """验证 MCP Server"""
        print("\n" + "="*60)
        print("🔌 验证 MCP Server 输入验证")
        print("="*60)
        
        from aibridge.server.mcp_server import AIBridgeMCPServer
        
        server = AIBridgeMCPServer()
        
        # 1. URL 验证
        print("\n1️⃣  URL 验证...")
        valid, _ = server._validate_url("https://www.baidu.com")
        self.log("正常URL", valid, "https://www.baidu.com 通过")
        
        valid, err = server._validate_url("javascript:alert(1)")
        self.log("危险URL阻止", not valid, f"javascript: 协议被阻止")
        
        valid, err = server._validate_url("")
        self.log("空URL阻止", not valid, "空URL被阻止")
        
        # 2. 选择器验证
        print("\n2️⃣  选择器验证...")
        valid, _ = server._validate_selector("#submit-btn")
        self.log("正常选择器", valid, "#submit-btn 通过")
        
        valid, _ = server._validate_selector("div<script>alert(1)</script>")
        self.log("XSS选择器阻止", not valid, "XSS注入被阻止")
        
        # 3. wait_until 验证
        print("\n3️⃣  wait_until 验证...")
        valid, _ = server._validate_wait_until("domcontentloaded")
        self.log("正常值", valid, "domcontentloaded 通过")
        
        valid, _ = server._validate_wait_until("malicious_value")
        self.log("非法值阻止", not valid, "非法值被阻止")
    
    def print_summary(self):
        """打印总结"""
        print("\n" + "="*60)
        print("📊 验证结果总结")
        print("="*60)
        
        passed = sum(1 for _, s, _ in self.results if s)
        failed = sum(1 for _, s, _ in self.results if not s)
        
        print(f"\n   总计: {len(self.results)} 项")
        print(f"   ✅ 通过: {passed} 项")
        print(f"   ❌ 失败: {failed} 项")
        
        if failed > 0:
            print("\n   失败项:")
            for name, success, msg in self.results:
                if not success:
                    print(f"   - {name}: {msg}")
        
        print("\n" + "="*60)
        return failed == 0


async def main():
    """主验证流程"""
    print("\n" + "🚀 " + "="*56 + " 🚀")
    print("    AI-Bridge 核心功能验证")
    print("🚀 " + "="*56 + " 🚀")
    
    verifier = CoreFunctionVerifier()
    
    # 验证安全框架（不需要浏览器）
    await verifier.verify_security_framework()
    
    # 验证 MCP Server 输入验证
    await verifier.verify_mcp_server()
    
    # 验证浏览器适配器（需要 Playwright）
    await verifier.verify_chrome_adapter()
    
    # 打印总结
    all_passed = verifier.print_summary()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
