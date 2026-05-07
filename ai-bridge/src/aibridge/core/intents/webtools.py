"""
WebTools 领域意图模式 — 4 个模式
覆盖网页抓取、表格提取、搜索、Markdown转换
"""

from aibridge.core.intent_pattern import IntentPattern, Slot, SlotType

WEBTOOLS_PATTERNS = [
    IntentPattern(
        id="webtools.scrape", domain="webtools",
        patterns=["抓取{网址:url}", "爬{网址:url}的内容"],
        description="抓取网页内容",
        slots=[Slot("网址", SlotType.URL, description="目标网址")],
        examples=["抓取https://example.com", "爬github.com/trending的内容"],
    ),
    IntentPattern(
        id="webtools.extract_table", domain="webtools",
        patterns=["提取{网址:url}的表格", "从{网址:url}导出表格数据"],
        description="从网页中提取表格数据",
        slots=[Slot("网址", SlotType.URL, description="目标网址")],
        examples=["提取wikipedia.org的表格", "从stats.gov导出表格数据"],
    ),
    IntentPattern(
        id="webtools.search", domain="webtools",
        patterns=["搜索{关键词:string}", "在{平台:string}搜{关键词:string}"],
        description="执行网络搜索",
        slots=[
            Slot("关键词", SlotType.STRING, description="搜索关键词"),
            Slot("平台", SlotType.STRING, required=False, description="搜索平台"),
        ],
        examples=["搜索AI最新进展", "在百度搜Python教程"],
    ),
    IntentPattern(
        id="webtools.markdown", domain="webtools",
        patterns=["把{网址:url}转成Markdown", "{网址:url}转md"],
        description="将网页转换为Markdown格式",
        slots=[Slot("网址", SlotType.URL, description="目标网址")],
        examples=["把https://example.com转成Markdown", "docs.python.org转md"],
    ),
]
