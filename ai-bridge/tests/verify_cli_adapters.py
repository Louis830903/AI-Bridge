#!/usr/bin/env python3
"""
CLI 适配器功能验证脚本

验证 WPS CLI 和 LibreOffice CLI 适配器是否能真正工作。
这不是单元测试，而是实际功能验证。
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aibridge.adapters.cli.wps import WPSCLIAdapter
from aibridge.adapters.cli.libreoffice import LibreOfficeAdapter


class CLIAdapterVerifier:
    """CLI 适配器功能验证器"""
    
    def __init__(self):
        self.results = []
        self.temp_dir = None
    
    def setup(self):
        """创建临时目录和测试文件"""
        self.temp_dir = tempfile.mkdtemp(prefix="aibridge_verify_")
        print(f"\n📁 临时目录: {self.temp_dir}")
        
        # 创建测试文本文件
        test_txt = Path(self.temp_dir) / "test.txt"
        test_txt.write_text("Hello AI-Bridge!\nThis is a test file for CLI adapter verification.", encoding="utf-8")
        print(f"   创建测试文件: {test_txt}")
        
        # 创建简单的 HTML 文件（可被 LibreOffice 转换）
        test_html = Path(self.temp_dir) / "test.html"
        test_html.write_text("""<!DOCTYPE html>
<html>
<head><title>AI-Bridge Test</title></head>
<body>
<h1>Hello AI-Bridge!</h1>
<p>This is a test HTML file for LibreOffice conversion.</p>
<ul>
<li>Item 1</li>
<li>Item 2</li>
<li>Item 3</li>
</ul>
</body>
</html>""", encoding="utf-8")
        print(f"   创建测试文件: {test_html}")
        
        return self.temp_dir
    
    def cleanup(self):
        """清理临时文件"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print(f"\n🗑️  已清理临时目录: {self.temp_dir}")
    
    def log_result(self, name: str, success: bool, message: str):
        """记录验证结果"""
        status = "✅" if success else "❌"
        self.results.append((name, success, message))
        print(f"   {status} {name}: {message}")
    
    async def verify_wps_adapter(self):
        """验证 WPS CLI 适配器"""
        print("\n" + "="*60)
        print("🔍 验证 WPS CLI 适配器")
        print("="*60)
        
        adapter = WPSCLIAdapter()
        
        # 1. 检查初始化
        print("\n1️⃣  初始化适配器...")
        try:
            init_result = await adapter.initialize()
            self.log_result("WPS 初始化", init_result, 
                          f"已找到 WPS" if init_result else "WPS 未安装或未找到")
        except Exception as e:
            self.log_result("WPS 初始化", False, f"初始化异常: {e}")
            return
        
        if not adapter._connected:
            print("   ⚠️  WPS 未安装，跳过后续验证")
            return
        
        # 2. 检查可用的应用程序
        print("\n2️⃣  检查可用应用...")
        try:
            from aibridge.core.protocol import Action
            result = await adapter.execute(Action(action="list_apps", params={}))
            if result.success:
                apps = result.data.get("available_apps", {})
                self.log_result("WPS 应用列表", True, f"找到 {len(apps)} 个应用: {list(apps.keys())}")
                for app, path in apps.items():
                    print(f"      - {app}: {path}")
            else:
                self.log_result("WPS 应用列表", False, result.error)
        except Exception as e:
            self.log_result("WPS 应用列表", False, f"异常: {e}")
        
        # 3. 尝试打开测试文件（非阻塞验证）
        print("\n3️⃣  验证文件打开功能...")
        test_file = Path(self.temp_dir) / "test.txt"
        try:
            from aibridge.core.protocol import Action
            result = await adapter.execute(Action(
                action="open", 
                params={"value": str(test_file)}
            ))
            if result.success:
                self.log_result("WPS 打开文件", True, "文件打开命令已发送")
            else:
                self.log_result("WPS 打开文件", False, result.error)
        except Exception as e:
            self.log_result("WPS 打开文件", False, f"异常: {e}")
        
        await adapter.cleanup()
    
    async def verify_libreoffice_adapter(self):
        """验证 LibreOffice CLI 适配器"""
        print("\n" + "="*60)
        print("🔍 验证 LibreOffice CLI 适配器")
        print("="*60)
        
        adapter = LibreOfficeAdapter()
        
        # 1. 检查初始化
        print("\n1️⃣  初始化适配器...")
        try:
            init_result = await adapter.initialize()
            self.log_result("LibreOffice 初始化", init_result,
                          f"已找到: {adapter._cli_executable}" if init_result else "LibreOffice 未安装")
        except Exception as e:
            self.log_result("LibreOffice 初始化", False, f"初始化异常: {e}")
            return
        
        if not adapter._connected:
            print("   ⚠️  LibreOffice 未安装，跳过后续验证")
            return
        
        # 2. 获取版本信息
        print("\n2️⃣  获取版本信息...")
        try:
            from aibridge.core.protocol import Action
            result = await adapter.execute(Action(action="version", params={}))
            if result.success:
                version = result.data.get("version", "Unknown")
                self.log_result("LibreOffice 版本", True, version)
            else:
                self.log_result("LibreOffice 版本", False, result.error)
        except Exception as e:
            self.log_result("LibreOffice 版本", False, f"异常: {e}")
        
        # 3. 列出支持的格式
        print("\n3️⃣  列出支持的格式...")
        try:
            from aibridge.core.protocol import Action
            result = await adapter.execute(Action(action="list_formats", params={}))
            if result.success:
                input_formats = result.data.get("input_formats", [])
                output_formats = result.data.get("output_formats", [])
                self.log_result("格式列表", True, 
                              f"输入: {len(input_formats)} 种, 输出: {len(output_formats)} 种")
            else:
                self.log_result("格式列表", False, result.error)
        except Exception as e:
            self.log_result("格式列表", False, f"异常: {e}")
        
        # 4. 实际转换测试: HTML → PDF
        print("\n4️⃣  实际转换测试 (HTML → PDF)...")
        test_html = Path(self.temp_dir) / "test.html"
        output_pdf = Path(self.temp_dir) / "test.pdf"
        
        try:
            from aibridge.core.protocol import Action
            result = await adapter.execute(Action(
                action="convert",
                params={
                    "input": str(test_html),
                    "format": "pdf",
                    "outdir": self.temp_dir
                }
            ))
            
            if result.success:
                # 验证输出文件是否真正生成
                if output_pdf.exists():
                    size = output_pdf.stat().st_size
                    self.log_result("HTML→PDF 转换", True, 
                                  f"成功! 输出文件: {output_pdf.name} ({size} bytes)")
                else:
                    self.log_result("HTML→PDF 转换", False, "命令成功但文件未生成")
            else:
                self.log_result("HTML→PDF 转换", False, result.error)
        except Exception as e:
            self.log_result("HTML→PDF 转换", False, f"异常: {e}")
        
        # 5. 实际转换测试: TXT → DOCX
        print("\n5️⃣  实际转换测试 (TXT → DOCX)...")
        test_txt = Path(self.temp_dir) / "test.txt"
        output_docx = Path(self.temp_dir) / "test.docx"
        
        try:
            from aibridge.core.protocol import Action
            result = await adapter.execute(Action(
                action="to_docx",
                params={
                    "input": str(test_txt),
                    "outdir": self.temp_dir
                }
            ))
            
            if result.success:
                if output_docx.exists():
                    size = output_docx.stat().st_size
                    self.log_result("TXT→DOCX 转换", True,
                                  f"成功! 输出文件: {output_docx.name} ({size} bytes)")
                else:
                    self.log_result("TXT→DOCX 转换", False, "命令成功但文件未生成")
            else:
                self.log_result("TXT→DOCX 转换", False, result.error)
        except Exception as e:
            self.log_result("TXT→DOCX 转换", False, f"异常: {e}")
        
        await adapter.cleanup()
    
    def print_summary(self):
        """打印验证总结"""
        print("\n" + "="*60)
        print("📊 验证结果总结")
        print("="*60)
        
        passed = sum(1 for _, success, _ in self.results if success)
        failed = sum(1 for _, success, _ in self.results if not success)
        total = len(self.results)
        
        print(f"\n   总计: {total} 项")
        print(f"   ✅ 通过: {passed} 项")
        print(f"   ❌ 失败: {failed} 项")
        
        if failed > 0:
            print("\n   失败项:")
            for name, success, message in self.results:
                if not success:
                    print(f"   - {name}: {message}")
        
        print("\n" + "="*60)
        return failed == 0


async def main():
    """主验证流程"""
    print("\n" + "🚀 " + "="*56 + " 🚀")
    print("    AI-Bridge CLI 适配器功能验证")
    print("🚀 " + "="*56 + " 🚀")
    
    verifier = CLIAdapterVerifier()
    
    try:
        # 设置测试环境
        verifier.setup()
        
        # 验证各适配器
        await verifier.verify_wps_adapter()
        await verifier.verify_libreoffice_adapter()
        
        # 打印总结
        all_passed = verifier.print_summary()
        
        return 0 if all_passed else 1
        
    finally:
        # 清理
        verifier.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
