"""
AI-Bridge 环境诊断工具

提供一键式环境检查，帮助用户快速诊断问题。
"""

import sys
import os
import shutil
import asyncio
import platform
from typing import Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum


class CheckStatus(Enum):
    """检查状态"""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    SKIP = "skip"


@dataclass
class CheckResult:
    """检查结果"""
    name: str
    status: CheckStatus
    message: str
    suggestion: Optional[str] = None


class DoctorCommand:
    """环境诊断命令"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[CheckResult] = []
    
    def _print_header(self):
        """打印头部"""
        print()
        print("🔍 AI-Bridge 环境诊断")
        print("=" * 50)
        print()
    
    def _print_result(self, result: CheckResult):
        """打印单条结果"""
        icons = {
            CheckStatus.OK: "✅",
            CheckStatus.WARNING: "⚠️ ",
            CheckStatus.ERROR: "❌",
            CheckStatus.SKIP: "⏭️ ",
        }
        icon = icons.get(result.status, "❓")
        print(f"{icon} {result.name}: {result.message}")
        if result.suggestion and result.status != CheckStatus.OK:
            print(f"   💡 {result.suggestion}")
    
    def _print_summary(self):
        """打印汇总"""
        ok_count = sum(1 for r in self.results if r.status == CheckStatus.OK)
        warn_count = sum(1 for r in self.results if r.status == CheckStatus.WARNING)
        error_count = sum(1 for r in self.results if r.status == CheckStatus.ERROR)
        
        print()
        print("=" * 50)
        print(f"📊 检查汇总: {ok_count} 通过, {warn_count} 警告, {error_count} 错误")
        print()
        
        if error_count > 0:
            print("❌ 存在错误，请根据建议修复后重试")
            return 1
        elif warn_count > 0:
            print("⚠️  存在警告，部分功能可能不可用")
            return 0
        else:
            print("🎉 环境检查全部通过！可以正常使用 AI-Bridge")
            return 0
    
    def check_python_version(self) -> CheckResult:
        """检查 Python 版本"""
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"
        
        if version.major < 3 or (version.major == 3 and version.minor < 9):
            return CheckResult(
                name="Python 版本",
                status=CheckStatus.ERROR,
                message=f"Python {version_str} (需要 >= 3.9)",
                suggestion="请升级 Python: https://python.org/downloads/"
            )
        return CheckResult(
            name="Python 版本",
            status=CheckStatus.OK,
            message=f"Python {version_str}"
        )
    
    def check_aibridge_version(self) -> CheckResult:
        """检查 AI-Bridge 版本"""
        try:
            from aibridge.version import __version__
            return CheckResult(
                name="AI-Bridge 版本",
                status=CheckStatus.OK,
                message=f"v{__version__}"
            )
        except ImportError:
            return CheckResult(
                name="AI-Bridge 版本",
                status=CheckStatus.ERROR,
                message="未安装",
                suggestion="运行: pip install ai-bridge"
            )
    
    def check_playwright(self) -> CheckResult:
        """检查 Playwright"""
        try:
            import playwright
            # 检查浏览器是否已安装
            browsers_path = os.path.expanduser("~/.cache/ms-playwright")
            if platform.system() == "Windows":
                browsers_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
            
            if os.path.exists(browsers_path):
                return CheckResult(
                    name="Playwright",
                    status=CheckStatus.OK,
                    message="已安装，浏览器可用"
                )
            else:
                return CheckResult(
                    name="Playwright",
                    status=CheckStatus.WARNING,
                    message="已安装，但浏览器未下载",
                    suggestion="运行: playwright install chromium"
                )
        except ImportError:
            return CheckResult(
                name="Playwright",
                status=CheckStatus.WARNING,
                message="未安装 (浏览器功能不可用)",
                suggestion="运行: pip install playwright && playwright install"
            )
    
    def check_chrome_browser(self) -> CheckResult:
        """检查 Chrome 浏览器"""
        chrome_paths = []
        
        if platform.system() == "Windows":
            chrome_paths = [
                os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
            ]
        elif platform.system() == "Darwin":
            chrome_paths = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
        else:
            chrome_paths = ["/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/bin/chromium"]
        
        for path in chrome_paths:
            if os.path.exists(path):
                return CheckResult(
                    name="Chrome 浏览器",
                    status=CheckStatus.OK,
                    message="已安装"
                )
        
        # 检查 which/where
        chrome_cmd = shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("chromium")
        if chrome_cmd:
            return CheckResult(
                name="Chrome 浏览器",
                status=CheckStatus.OK,
                message=f"已安装 ({chrome_cmd})"
            )
        
        return CheckResult(
            name="Chrome 浏览器",
            status=CheckStatus.WARNING,
            message="未检测到 (可通过 Playwright 内置浏览器使用)",
            suggestion="下载: https://google.com/chrome"
        )
    
    def check_office(self) -> CheckResult:
        """检查 Office"""
        if platform.system() != "Windows":
            return CheckResult(
                name="Microsoft Office",
                status=CheckStatus.SKIP,
                message="仅 Windows 支持"
            )
        
        try:
            import win32com.client
            # 尝试检测 Word
            try:
                word = win32com.client.Dispatch("Word.Application")
                word.Quit()
                return CheckResult(
                    name="Microsoft Office",
                    status=CheckStatus.OK,
                    message="已安装"
                )
            except Exception:
                pass
            
            # 尝试检测 WPS
            try:
                wps = win32com.client.Dispatch("Kwps.Application")
                wps.Quit()
                return CheckResult(
                    name="WPS Office",
                    status=CheckStatus.OK,
                    message="已安装"
                )
            except Exception:
                pass
            
            return CheckResult(
                name="Office 套件",
                status=CheckStatus.WARNING,
                message="未检测到 Office/WPS",
                suggestion="Office 功能需要安装 Microsoft Office 或 WPS"
            )
        except ImportError:
            return CheckResult(
                name="Office 支持",
                status=CheckStatus.WARNING,
                message="缺少 pywin32",
                suggestion="运行: pip install pywin32"
            )
    
    def check_mcp_sdk(self) -> CheckResult:
        """检查 MCP SDK"""
        try:
            import mcp
            return CheckResult(
                name="MCP SDK",
                status=CheckStatus.OK,
                message="已安装"
            )
        except ImportError:
            return CheckResult(
                name="MCP SDK",
                status=CheckStatus.WARNING,
                message="未安装 (MCP 协议功能受限)",
                suggestion="运行: pip install mcp"
            )
    
    def check_enterprise_deps(self) -> CheckResult:
        """检查企业级依赖"""
        missing = []
        
        try:
            import aiosqlite
        except ImportError:
            missing.append("aiosqlite")
        
        try:
            import prometheus_client
        except ImportError:
            missing.append("prometheus_client")
        
        if not missing:
            return CheckResult(
                name="企业级依赖",
                status=CheckStatus.OK,
                message="Prometheus, SQLite 支持就绪"
            )
        else:
            return CheckResult(
                name="企业级依赖",
                status=CheckStatus.WARNING,
                message=f"缺少: {', '.join(missing)}",
                suggestion=f"运行: pip install {' '.join(missing)}"
            )
    
    def check_network(self) -> CheckResult:
        """检查网络连接"""
        import urllib.request
        try:
            urllib.request.urlopen("https://www.baidu.com", timeout=5)
            return CheckResult(
                name="网络连接",
                status=CheckStatus.OK,
                message="正常"
            )
        except Exception:
            return CheckResult(
                name="网络连接",
                status=CheckStatus.WARNING,
                message="无法访问外网",
                suggestion="部分功能可能需要网络连接"
            )
    
    def check_disk_space(self) -> CheckResult:
        """检查磁盘空间"""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free // (1024 ** 3)
            
            if free_gb < 1:
                return CheckResult(
                    name="磁盘空间",
                    status=CheckStatus.ERROR,
                    message=f"剩余 {free_gb}GB (不足)",
                    suggestion="请清理磁盘空间，至少需要 1GB"
                )
            elif free_gb < 5:
                return CheckResult(
                    name="磁盘空间",
                    status=CheckStatus.WARNING,
                    message=f"剩余 {free_gb}GB (较少)",
                    suggestion="建议保留 5GB 以上空间"
                )
            else:
                return CheckResult(
                    name="磁盘空间",
                    status=CheckStatus.OK,
                    message=f"剩余 {free_gb}GB"
                )
        except Exception:
            return CheckResult(
                name="磁盘空间",
                status=CheckStatus.SKIP,
                message="无法检测"
            )
    
    def run(self) -> int:
        """运行所有检查"""
        self._print_header()
        
        # 基础环境
        print("📦 基础环境")
        print("-" * 30)
        checks = [
            self.check_python_version(),
            self.check_aibridge_version(),
            self.check_disk_space(),
            self.check_network(),
        ]
        for result in checks:
            self.results.append(result)
            self._print_result(result)
        
        # 浏览器自动化
        print()
        print("🌐 浏览器自动化")
        print("-" * 30)
        checks = [
            self.check_playwright(),
            self.check_chrome_browser(),
        ]
        for result in checks:
            self.results.append(result)
            self._print_result(result)
        
        # Office 支持
        print()
        print("📄 Office 支持")
        print("-" * 30)
        result = self.check_office()
        self.results.append(result)
        self._print_result(result)
        
        # 协议与企业级
        print()
        print("🔧 协议与企业级特性")
        print("-" * 30)
        checks = [
            self.check_mcp_sdk(),
            self.check_enterprise_deps(),
        ]
        for result in checks:
            self.results.append(result)
            self._print_result(result)
        
        # 汇总
        return self._print_summary()


def run_doctor(verbose: bool = False) -> int:
    """运行诊断命令"""
    doctor = DoctorCommand(verbose=verbose)
    return doctor.run()


if __name__ == "__main__":
    sys.exit(run_doctor())
