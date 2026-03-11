#!/usr/bin/env python3
"""
工作流示例：每日报告自动化
Workflow Example: Daily Report Automation

这个工作流演示如何使用 AI-Bridge 自动化完成以下任务：
1. 从浏览器抓取今日数据
2. 在 Excel 中整理数据
3. 生成 Word 报告
4. 通过飞书/钉钉发送报告
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '../../src')

from aibridge.core.manager import AdapterManager
from aibridge.core.protocol import Target


class DailyReportWorkflow:
    """每日报告工作流"""
    
    def __init__(self):
        self.manager = AdapterManager()
        self.data = {}
        self.report_date = datetime.now().strftime("%Y-%m-%d")
        
    async def setup(self):
        """初始化适配器"""
        from aibridge.adapters.browser.chrome import ChromeAdapter, ChromeConfig
        from aibridge.adapters.office.excel import ExcelAdapter, ExcelConfig
        from aibridge.adapters.office.word import WordAdapter, WordConfig
        from aibridge.adapters.im.feishu import FeishuAdapter, FeishuConfig
        
        # 注册所需适配器
        self.manager.register(ChromeAdapter(ChromeConfig(headless=True)))
        self.manager.register(ExcelAdapter(ExcelConfig(visible=False)))
        self.manager.register(WordAdapter(WordConfig(visible=False)))
        
        # 飞书配置 (实际使用时替换为真实凭证)
        feishu_config = FeishuConfig(
            app_id="your_app_id",
            app_secret="your_app_secret"
        )
        self.manager.register(FeishuAdapter(feishu_config))
        
        print(f"✓ 工作流初始化完成，日期: {self.report_date}")
        
    async def step1_collect_data(self):
        """步骤1: 从网页收集数据"""
        print("\n[Step 1] 收集数据...")
        
        chrome = self.manager.get("chrome")
        await chrome.connect()
        
        try:
            # 示例：访问数据源页面
            await chrome.execute(
                action="goto",
                target=None,
                value="https://example.com/daily-stats",
                options={}
            )
            
            # 读取页面数据 (示例)
            # 实际场景中，这里会使用 read 操作提取具体元素
            self.data = {
                "date": self.report_date,
                "visitors": 12580,
                "orders": 856,
                "revenue": 125800.50,
                "conversion_rate": "6.8%"
            }
            
            print(f"  ✓ 数据收集完成: {len(self.data)} 项指标")
            
        finally:
            await chrome.disconnect()
            
    async def step2_process_excel(self):
        """步骤2: 在 Excel 中处理数据"""
        print("\n[Step 2] 处理 Excel 数据...")
        
        excel = self.manager.get("excel")
        await excel.connect()
        
        try:
            # 创建新工作簿
            await excel.execute(
                action="create",
                target=None,
                value=None,
                options={}
            )
            
            # 写入表头
            headers = ["指标", "数值", "说明"]
            for i, header in enumerate(headers):
                await excel.execute(
                    action="write_cell",
                    target=Target(name=f"A1"),
                    value=header,
                    options={"row": 1, "col": i + 1}
                )
            
            # 写入数据行
            rows = [
                ("日期", self.data["date"], "报告日期"),
                ("访客数", self.data["visitors"], "UV"),
                ("订单数", self.data["orders"], "成交订单"),
                ("营收", self.data["revenue"], "元"),
                ("转化率", self.data["conversion_rate"], "订单/访客"),
            ]
            
            for row_idx, (metric, value, note) in enumerate(rows, start=2):
                await excel.execute(
                    action="write_cell",
                    target=None,
                    value=str(metric),
                    options={"row": row_idx, "col": 1}
                )
                await excel.execute(
                    action="write_cell",
                    target=None,
                    value=str(value),
                    options={"row": row_idx, "col": 2}
                )
                await excel.execute(
                    action="write_cell",
                    target=None,
                    value=str(note),
                    options={"row": row_idx, "col": 3}
                )
            
            # 保存 Excel 文件
            excel_path = f"daily_report_{self.report_date}.xlsx"
            await excel.execute(
                action="save",
                target=None,
                value=excel_path,
                options={}
            )
            
            self.data["excel_path"] = excel_path
            print(f"  ✓ Excel 报表已生成: {excel_path}")
            
        finally:
            await excel.disconnect()
            
    async def step3_generate_word_report(self):
        """步骤3: 生成 Word 报告"""
        print("\n[Step 3] 生成 Word 报告...")
        
        word = self.manager.get("word")
        await word.connect()
        
        try:
            # 创建新文档
            await word.execute(
                action="create",
                target=None,
                value=None,
                options={}
            )
            
            # 写入报告内容
            report_content = f"""
每日运营报告

报告日期: {self.data['date']}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

一、核心指标

| 指标 | 数值 |
|------|------|
| 访客数 | {self.data['visitors']:,} |
| 订单数 | {self.data['orders']:,} |
| 营收 | ¥{self.data['revenue']:,.2f} |
| 转化率 | {self.data['conversion_rate']} |

二、数据分析

今日访客数为 {self.data['visitors']:,}，共产生 {self.data['orders']:,} 笔订单，
转化率为 {self.data['conversion_rate']}，总营收 ¥{self.data['revenue']:,.2f}。

三、附件

详细数据请见 Excel 附件: {self.data.get('excel_path', 'N/A')}

---
此报告由 AI-Bridge 自动生成
"""
            
            await word.execute(
                action="write",
                target=None,
                value=report_content,
                options={}
            )
            
            # 保存 Word 文件
            word_path = f"daily_report_{self.report_date}.docx"
            await word.execute(
                action="save",
                target=None,
                value=word_path,
                options={}
            )
            
            self.data["word_path"] = word_path
            print(f"  ✓ Word 报告已生成: {word_path}")
            
        finally:
            await word.disconnect()
            
    async def step4_send_notification(self):
        """步骤4: 发送通知"""
        print("\n[Step 4] 发送通知...")
        
        feishu = self.manager.get("feishu")
        
        try:
            connected = await feishu.connect()
            if not connected:
                print("  ⚠ 飞书连接失败，跳过通知发送")
                return
                
            # 构造消息
            message = f"""📊 每日报告已生成

日期: {self.data['date']}
访客: {self.data['visitors']:,}
订单: {self.data['orders']:,}
营收: ¥{self.data['revenue']:,.2f}
转化率: {self.data['conversion_rate']}

📎 附件:
- {self.data.get('excel_path', 'Excel报表')}
- {self.data.get('word_path', 'Word报告')}"""
            
            # 发送到运营群
            await feishu.execute(
                action="send_message",
                target=Target(name="oc_operations_group"),  # 运营群 chat_id
                value=message,
                options={}
            )
            
            print("  ✓ 飞书通知已发送")
            
        except Exception as e:
            print(f"  ⚠ 发送通知失败: {e}")
        finally:
            await feishu.disconnect()
            
    async def run(self):
        """执行完整工作流"""
        print("=" * 50)
        print("每日报告自动化工作流")
        print("=" * 50)
        
        try:
            await self.setup()
            await self.step1_collect_data()
            await self.step2_process_excel()
            await self.step3_generate_word_report()
            await self.step4_send_notification()
            
            print("\n" + "=" * 50)
            print("✅ 工作流执行完成!")
            print("=" * 50)
            
        except Exception as e:
            print(f"\n❌ 工作流执行失败: {e}")
            raise


async def main():
    """主函数"""
    workflow = DailyReportWorkflow()
    await workflow.run()


if __name__ == "__main__":
    asyncio.run(main())
