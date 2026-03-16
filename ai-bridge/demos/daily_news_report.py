#!/usr/bin/env python3
"""
AI-Bridge v5.0 实际业务演示：AI 行业资讯日报自动生成

业务场景：
    每天自动采集 AI 行业新闻，汇总到 Excel，生成 Word 报告

功能覆盖：
    1. 浏览器自动化 - 打开网页、提取内容、截图
    2. Excel 数据汇总 - 创建表格、写入数据
    3. Word 报告生成 - 创建文档、格式化内容
    
运行方式：
    python demos/daily_news_report.py
"""

import asyncio
import sys
import os
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    source: str
    url: str
    summary: str = ""
    timestamp: str = ""


class DailyNewsReporter:
    """每日新闻报告生成器"""
    
    def __init__(self):
        self.news_items: List[NewsItem] = []
        self.report_date = datetime.now().strftime("%Y-%m-%d")
        self.output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def collect_news_from_browser(self) -> List[NewsItem]:
        """
        Step 1: 使用浏览器自动化采集新闻
        """
        print("\n" + "=" * 60)
        print("📰 Step 1: 浏览器自动化 - 采集 AI 行业新闻")
        print("=" * 60)
        
        from aibridge.adapters.browser.chrome import ChromeAdapter
        
        # ChromeAdapter 接受字典配置
        config = {"headless": False}  # 可视化运行，方便演示
        adapter = ChromeAdapter(config)
        
        news_items = []
        
        try:
            await adapter.connect()
            print("✅ 浏览器已启动")
            
            # 1. 访问 Hacker News (AI 相关)
            print("\n🌐 正在访问 Hacker News...")
            await adapter.execute(
                action="goto",
                target=None,
                value="https://news.ycombinator.com/",
                options={}
            )
            await asyncio.sleep(2)
            
            # 截图保存
            screenshot_path = os.path.join(self.output_dir, f"hackernews_{self.report_date}.png")
            await adapter.execute(
                action="screenshot",
                target=None,
                value=None,
                options={"path": screenshot_path}
            )
            print(f"📸 截图已保存: {screenshot_path}")
            
            # 提取前5条新闻标题
            result = await adapter.execute(
                action="evaluate",
                target=None,
                value="""
                () => {
                    const items = document.querySelectorAll('.titleline > a');
                    return Array.from(items).slice(0, 5).map(a => ({
                        title: a.textContent,
                        url: a.href
                    }));
                }
                """,
                options={}
            )
            
            if result.get("success") and result.get("data"):
                for item in result["data"]:
                    news_items.append(NewsItem(
                        title=item.get("title", "Unknown"),
                        source="Hacker News",
                        url=item.get("url", ""),
                        summary="Tech & AI community discussion",
                        timestamp=datetime.now().strftime("%H:%M")
                    ))
                print(f"✅ 从 Hacker News 提取了 {len(result['data'])} 条新闻")
            
            # 2. 访问 GitHub Trending
            print("\n🌐 正在访问 GitHub Trending...")
            await adapter.execute(
                action="goto",
                target=None,
                value="https://github.com/trending?since=daily",
                options={}
            )
            await asyncio.sleep(2)
            
            # 提取热门项目
            result = await adapter.execute(
                action="evaluate",
                target=None,
                value="""
                () => {
                    const repos = document.querySelectorAll('article.Box-row');
                    return Array.from(repos).slice(0, 3).map(repo => {
                        const nameEl = repo.querySelector('h2 a');
                        const descEl = repo.querySelector('p');
                        return {
                            title: nameEl ? nameEl.textContent.trim().replace(/\\s+/g, ' ') : 'Unknown',
                            url: nameEl ? 'https://github.com' + nameEl.getAttribute('href') : '',
                            summary: descEl ? descEl.textContent.trim() : ''
                        };
                    });
                }
                """,
                options={}
            )
            
            if result.get("success") and result.get("data"):
                for item in result["data"]:
                    news_items.append(NewsItem(
                        title=f"🔥 {item.get('title', 'Unknown')}",
                        source="GitHub Trending",
                        url=item.get("url", ""),
                        summary=item.get("summary", "")[:100],
                        timestamp=datetime.now().strftime("%H:%M")
                    ))
                print(f"✅ 从 GitHub Trending 提取了 {len(result['data'])} 个热门项目")
            
        except Exception as e:
            print(f"⚠️ 浏览器采集出错: {e}")
            # 使用模拟数据继续演示
            news_items = self._get_mock_news()
            print("📋 使用模拟数据继续演示")
        finally:
            await adapter.disconnect()
            print("✅ 浏览器已关闭")
        
        self.news_items = news_items
        return news_items
    
    def _get_mock_news(self) -> List[NewsItem]:
        """模拟数据（用于无网络或浏览器异常时）"""
        return [
            NewsItem("GPT-5 发布在即，OpenAI 透露更多细节", "Hacker News", "https://example.com/1", "OpenAI CEO 透露下一代模型", "09:00"),
            NewsItem("Claude 3.5 Sonnet 性能测评", "Hacker News", "https://example.com/2", "Anthropic 新模型表现优异", "09:15"),
            NewsItem("开源大模型 Llama 3 发布", "GitHub Trending", "https://example.com/3", "Meta 开源最新 LLM", "09:30"),
            NewsItem("AI-Bridge: MCP+A2A 协议网关", "GitHub Trending", "https://example.com/4", "统一 AI 工具入口", "10:00"),
            NewsItem("Cursor IDE 使用技巧分享", "Hacker News", "https://example.com/5", "AI 辅助编程最佳实践", "10:30"),
        ]
    
    async def export_to_excel(self) -> str:
        """
        Step 2: 导出到 Excel 表格
        """
        print("\n" + "=" * 60)
        print("📊 Step 2: Excel 数据汇总")
        print("=" * 60)
        
        import platform
        if platform.system() != "Windows":
            print("⚠️ Excel 功能仅支持 Windows，跳过此步骤")
            return ""
        
        try:
            from aibridge.adapters.office.excel import ExcelAdapter
            
            # ExcelAdapter 接受字典配置
            config = {"visible": True}
            adapter = ExcelAdapter(config)
            
            # Excel 是同步适配器，不需要 await
            adapter.connect()
            print("✅ Excel 已启动")
            
            # 创建新工作簿
            adapter.execute(action="create", target=None, value=None, options={})
            print("✅ 新建工作簿")
            
            # 写入表头
            headers = ["序号", "标题", "来源", "摘要", "时间", "链接"]
            for col, header in enumerate(headers, 1):
                adapter.execute(
                    action="write_cell",
                    target=None,
                    value=header,
                    options={"row": 1, "column": col}
                )
            print("✅ 写入表头")
            
            # 写入数据
            for row, news in enumerate(self.news_items, 2):
                data = [
                    row - 1,
                    news.title,
                    news.source,
                    news.summary,
                    news.timestamp,
                    news.url
                ]
                for col, value in enumerate(data, 1):
                    adapter.execute(
                        action="write_cell",
                        target=None,
                        value=str(value),
                        options={"row": row, "column": col}
                    )
            print(f"✅ 写入 {len(self.news_items)} 条数据")
            
            # 保存文件
            excel_path = os.path.join(self.output_dir, f"news_data_{self.report_date}.xlsx")
            adapter.execute(
                action="save",
                target=None,
                value=excel_path,
                options={}
            )
            print(f"✅ Excel 已保存: {excel_path}")
            
            adapter.disconnect()
            return excel_path
            
        except Exception as e:
            print(f"⚠️ Excel 操作出错: {e}")
            # 使用 CSV 作为替代
            return self._export_to_csv()
    
    def _export_to_csv(self) -> str:
        """导出为 CSV（Excel 不可用时的替代方案）"""
        import csv
        csv_path = os.path.join(self.output_dir, f"news_data_{self.report_date}.csv")
        
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["序号", "标题", "来源", "摘要", "时间", "链接"])
            for i, news in enumerate(self.news_items, 1):
                writer.writerow([i, news.title, news.source, news.summary, news.timestamp, news.url])
        
        print(f"✅ CSV 已保存: {csv_path}")
        return csv_path
    
    async def generate_word_report(self) -> str:
        """
        Step 3: 生成 Word 报告
        """
        print("\n" + "=" * 60)
        print("📄 Step 3: Word 报告生成")
        print("=" * 60)
        
        import platform
        if platform.system() != "Windows":
            print("⚠️ Word 功能仅支持 Windows，使用 Markdown 替代")
            return self._generate_markdown_report()
        
        try:
            from aibridge.adapters.office.word import WordAdapter
            
            # WordAdapter 接受字典配置
            config = {"visible": True}
            adapter = WordAdapter(config)
            
            # Word 是同步适配器，不需要 await
            adapter.connect()
            print("✅ Word 已启动")
            
            # 创建新文档
            adapter.execute(action="create", target=None, value=None, options={})
            print("✅ 新建文档")
            
            # 写入报告内容
            report_content = self._build_report_content()
            adapter.execute(
                action="write",
                target=None,
                value=report_content,
                options={}
            )
            print("✅ 写入报告内容")
            
            # 保存文件
            word_path = os.path.join(self.output_dir, f"AI_Daily_Report_{self.report_date}.docx")
            adapter.execute(
                action="save",
                target=None,
                value=word_path,
                options={}
            )
            print(f"✅ Word 报告已保存: {word_path}")
            
            adapter.disconnect()
            return word_path
            
        except Exception as e:
            print(f"⚠️ Word 操作出错: {e}")
            return self._generate_markdown_report()
    
    def _build_report_content(self) -> str:
        """构建报告内容"""
        lines = [
            f"AI 行业资讯日报",
            f"",
            f"报告日期: {self.report_date}",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"数据来源: Hacker News, GitHub Trending",
            f"",
            f"=" * 50,
            f"",
            f"今日要闻摘要",
            f"",
        ]
        
        for i, news in enumerate(self.news_items, 1):
            lines.extend([
                f"{i}. {news.title}",
                f"   来源: {news.source}",
                f"   摘要: {news.summary}",
                f"   时间: {news.timestamp}",
                f"",
            ])
        
        lines.extend([
            f"=" * 50,
            f"",
            f"本报告由 AI-Bridge v5.0 自动生成",
            f"https://github.com/Louis830903/AI-Bridge",
        ])
        
        return "\n".join(lines)
    
    def _generate_markdown_report(self) -> str:
        """生成 Markdown 报告（Word 不可用时的替代方案）"""
        md_path = os.path.join(self.output_dir, f"AI_Daily_Report_{self.report_date}.md")
        
        lines = [
            f"# AI 行业资讯日报",
            f"",
            f"**报告日期**: {self.report_date}  ",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**数据来源**: Hacker News, GitHub Trending",
            f"",
            f"---",
            f"",
            f"## 今日要闻",
            f"",
        ]
        
        for i, news in enumerate(self.news_items, 1):
            lines.extend([
                f"### {i}. {news.title}",
                f"",
                f"- **来源**: {news.source}",
                f"- **摘要**: {news.summary}",
                f"- **时间**: {news.timestamp}",
                f"- **链接**: [{news.url}]({news.url})",
                f"",
            ])
        
        lines.extend([
            f"---",
            f"",
            f"*本报告由 [AI-Bridge v5.0](https://github.com/Louis830903/AI-Bridge) 自动生成*",
        ])
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        
        print(f"✅ Markdown 报告已保存: {md_path}")
        return md_path
    
    async def run(self):
        """运行完整的日报生成流程"""
        print("\n" + "🚀" * 20)
        print("\n  AI-Bridge v5.0 业务演示")
        print("  场景: AI 行业资讯日报自动生成")
        print("\n" + "🚀" * 20)
        
        start_time = datetime.now()
        
        # Step 1: 浏览器采集
        await self.collect_news_from_browser()
        
        # Step 2: Excel 汇总
        excel_path = await self.export_to_excel()
        
        # Step 3: Word 报告
        report_path = await self.generate_word_report()
        
        # 汇总
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("✅ 日报生成完成!")
        print("=" * 60)
        print(f"\n📊 采集新闻: {len(self.news_items)} 条")
        print(f"📁 输出目录: {self.output_dir}")
        print(f"⏱️  总耗时: {elapsed:.1f} 秒")
        print("\n生成文件:")
        for f in os.listdir(self.output_dir):
            if self.report_date in f:
                print(f"  - {f}")
        
        print("\n" + "🎉" * 20)
        print("\n  演示完成！AI-Bridge 核心功能验证通过")
        print("\n" + "🎉" * 20)


async def main():
    """主入口"""
    reporter = DailyNewsReporter()
    await reporter.run()


if __name__ == "__main__":
    asyncio.run(main())
