"""
Browser 领域意图模式 — 6 个模式
覆盖导航、点击、填写、截图、滚动、数据提取
"""

from aibridge.core.intent_pattern import IntentPattern, Slot, SlotType

BROWSER_PATTERNS = [
    IntentPattern(
        id="browser.navigate", domain="browser",
        patterns=["打开{网址:url}", "访问{网址:url}", "去{网址:url}"],
        description="导航到指定网址",
        slots=[Slot("网址", SlotType.URL, description="目标网址")],
        confidence_threshold=0.8,
        examples=["打开百度", "访问 github.com"],
    ),
    IntentPattern(
        id="browser.click", domain="browser",
        patterns=["点击{元素:string}", "按下{按钮:string}"],
        description="点击页面元素或按钮",
        slots=[Slot("元素", SlotType.STRING, description="要点击的元素文本或选择器")],
        confidence_threshold=0.6,
        examples=["点击登录按钮", "按下提交"],
    ),
    IntentPattern(
        id="browser.fill", domain="browser",
        patterns=["在{字段:string}输入{内容:string}", "填写{字段:string}为{内容:string}"],
        description="在表单字段中输入内容",
        slots=[
            Slot("字段", SlotType.STRING, description="字段名称或选择器"),
            Slot("内容", SlotType.STRING, description="要输入的内容"),
        ],
        examples=["在搜索框输入iPhone", "填写用户名为admin"],
    ),
    IntentPattern(
        id="browser.screenshot", domain="browser",
        patterns=["截屏", "截图保存到{路径:path}", "给当前页面截图"],
        description="截取当前页面截图",
        slots=[Slot("路径", SlotType.PATH, required=False, description="保存路径")],
        confidence_threshold=0.5,
        examples=["截屏", "截图保存到screenshot.png"],
    ),
    IntentPattern(
        id="browser.scroll", domain="browser",
        patterns=["向下滚动", "滚动到{位置:string}", "翻到{方向:string}"],
        description="滚动页面",
        slots=[
            Slot("位置", SlotType.STRING, required=False, description="滚动到的位置"),
            Slot("方向", SlotType.STRING, required=False, description="滚动方向"),
        ],
        confidence_threshold=0.5,
        examples=["向下滚动", "滚动到底部"],
    ),
    IntentPattern(
        id="browser.extract", domain="browser",
        patterns=["提取{页面:string}中的{数据:string}", "从{页面:string}抓取{数据:string}"],
        description="从页面中提取或抓取数据",
        slots=[
            Slot("页面", SlotType.URL, description="目标页面URL"),
            Slot("数据", SlotType.STRING, description="要提取的数据类型"),
        ],
        examples=["提取淘宝页面中的商品价格", "从github.com抓取代码"],
    ),
]
