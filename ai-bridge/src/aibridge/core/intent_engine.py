"""
意图识别引擎 (Intent Engine)

将自然语言意图转换为结构化操作。
支持两种模式:
1. 规则匹配模式 - 基于关键词和模式匹配（无需LLM）
2. LLM模式 - 使用大语言模型理解复杂意图（可选）

示例:
- "搜索iPhone 15" → goto("https://search.xxx") + type("#search", "iPhone 15") + click("#submit")
- "点击提交按钮" → click({"text": "提交"})
- "提取所有商品价格" → extract({"css": ".price"}, {"price": "number"}, multiple=True)
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

from aibridge.adapters.browser.chrome import ChromeAdapter

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """意图类型枚举"""
    NAVIGATE = "navigate"          # 导航到URL
    SEARCH = "search"              # 搜索内容
    CLICK = "click"                # 点击元素
    TYPE = "type"                  # 输入文本
    EXTRACT = "extract"            # 提取数据
    SCROLL = "scroll"              # 滚动页面
    WAIT = "wait"                  # 等待
    COMPOSITE = "composite"        # 复合操作（多个步骤）
    UNKNOWN = "unknown"            # 未知意图


@dataclass
class ActionStep:
    """单个操作步骤"""
    action: str                     # 操作类型: goto, click, type, extract等
    target: Optional[Dict] = None   # 目标选择器
    value: Optional[Any] = None     # 输入值
    options: Optional[Dict] = field(default_factory=dict)  # 额外选项
    description: str = ""           # 人类可读的描述


@dataclass
class IntentResult:
    """意图解析结果"""
    success: bool                   # 是否成功解析
    intent_type: IntentType         # 意图类型
    original_intent: str            # 原始意图文本
    steps: List[ActionStep]         # 操作步骤列表
    summary: str                    # 执行摘要
    data: Optional[Dict] = None     # 额外数据
    error: Optional[str] = None     # 错误信息


# ============ 规则模式定义 ============

class IntentPattern:
    """意图模式 - 用于规则匹配"""
    
    def __init__(
        self,
        intent_type: IntentType,
        patterns: List[str],
        handler: Callable[[re.Match, 'ChromeAdapter'], List[ActionStep]]
    ):
        self.intent_type = intent_type
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.handler = handler
    
    def match(self, text: str) -> Optional[re.Match]:
        """尝试匹配文本"""
        for pattern in self.patterns:
            match = pattern.match(text.strip())
            if match:
                return match
        return None


# ============ 意图处理器 ============

def handle_navigate(match: re.Match, adapter: ChromeAdapter) -> List[ActionStep]:
    """处理导航意图"""
    url = match.group(1)
    # 自动补全协议
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return [ActionStep(
        action="goto",
        target={"url": url},
        description=f"导航到 {url}"
    )]


def handle_search(match: re.Match, adapter: ChromeAdapter) -> List[ActionStep]:
    """处理搜索意图"""
    keyword = match.group(1)
    
    # 尝试在常见搜索框输入
    return [
        ActionStep(
            action="type",
            target={"css": "#kw"},  # 百度搜索框
            value=keyword,
            options={"force": True},
            description=f"在搜索框输入: {keyword}"
        ),
        ActionStep(
            action="click",
            target={"css": "#su"},  # 百度搜索按钮
            options={"force": True},
            description="点击搜索按钮"
        )
    ]


def handle_click(match: re.Match, adapter: ChromeAdapter) -> List[ActionStep]:
    """处理点击意图"""
    target_text = match.group(1)
    
    return [ActionStep(
        action="click",
        target={"text": target_text},
        options={"force": True},
        description=f"点击包含文本的元素: {target_text}"
    )]


def handle_type(match: re.Match, adapter: ChromeAdapter) -> List[ActionStep]:
    """处理输入意图"""
    field_hint = match.group(1)  # 字段提示（如"搜索框"、"用户名"）
    text = match.group(2)
    
    # 根据字段提示推断选择器
    selector_map = {
        "搜索框": "#kw",
        "search": "#kw",
        "用户名": "input[name='username'], input[type='text']",
        "密码": "input[type='password']",
        "邮箱": "input[type='email'], input[name='email']",
    }
    
    selector = selector_map.get(field_hint, "input")
    
    return [ActionStep(
        action="type",
        target={"css": selector},
        value=text,
        options={"force": True},
        description=f"在{field_hint}输入: {text}"
    )]


def handle_extract(match: re.Match, adapter: ChromeAdapter) -> List[ActionStep]:
    """处理提取意图"""
    field_name = match.group(1)
    
    # 常见字段映射
    field_map = {
        "标题": {"css": "h1, h2, h3", "field": "title"},
        "链接": {"css": "a", "field": "href"},
        "价格": {"css": ".price", "field": "price"},
        "商品": {"css": ".product", "field": "name"},
        "结果": {"css": ".result", "field": "content"},
    }
    
    config = field_map.get(field_name, {"css": "body", "field": "text"})
    
    return [ActionStep(
        action="extract",
        target={"css": config["css"]},
        value={config["field"]: "string"},
        options={"multiple": True},
        description=f"提取页面中的{field_name}"
    )]


def handle_scroll(match: re.Match, adapter: ChromeAdapter) -> List[ActionStep]:
    """处理滚动意图"""
    direction = match.group(1).lower() if match.group(1) else "down"
    
    return [ActionStep(
        action="scroll",
        value=direction,
        description=f"向{direction}滚动页面"
    )]


# ============ 意图引擎 ============

class IntentEngine:
    """
    意图识别引擎
    
    将自然语言转换为可执行的操作序列。
    """
    
    # 预定义的规则模式
    PATTERNS = [
        # 导航意图
        IntentPattern(
            IntentType.NAVIGATE,
            [
                r"^(?:打开|访问|导航到|goto|navigate to)\s+(.+)$",
                r"^https?://.+",
                r"^(?:www\.)?[\w-]+\.(com|cn|org|net|io)$",
            ],
            handle_navigate
        ),
        
        # 搜索意图
        IntentPattern(
            IntentType.SEARCH,
            [
                r"^(?:搜索|查找|search for|search)\s+(.+)$",
                r"^(.+?)\s*(?:的)?\s*(?:搜索|查找)$",
            ],
            handle_search
        ),
        
        # 点击意图
        IntentPattern(
            IntentType.CLICK,
            [
                r"^(?:点击|点|click)\s*(?:按钮|链接|元素)?\s*(?:叫|为)?[\"']?(.+?)[\"']?$",
                r"^(?:点|click)\s+(.+)$",
            ],
            handle_click
        ),
        
        # 输入意图
        IntentPattern(
            IntentType.TYPE,
            [
                r"^(?:在|in)\s*(.+?)\s*(?:输入|填写|type|enter)\s*[\"']?(.+?)[\"']?$",
                r"^(?:输入|填写)\s*[\"']?(.+?)[\"']?\s*(?:到|in)\s*(.+)$",
            ],
            handle_type
        ),
        
        # 提取意图
        IntentPattern(
            IntentType.EXTRACT,
            [
                r"^(?:提取|获取|抓取|extract|get)\s*(?:所有|全部)?\s*(.+?)(?:数据|信息|内容)?$",
                r"^(?:获取|得到)\s*(?:所有|全部)?\s*(.+)$",
            ],
            handle_extract
        ),
        
        # 滚动意图
        IntentPattern(
            IntentType.SCROLL,
            [
                r"^(?:滚动|scroll)\s*(?:页面|向下|向上|往下|往上)?\s*(向下|向上|down|up)?$",
                r"^(?:向下|向上|往下|往上)\s*滚动$",
            ],
            handle_scroll
        ),
    ]
    
    def __init__(self, adapter: ChromeAdapter, llm_provider=None):
        self.adapter = adapter
        self.llm_provider = llm_provider
        self.use_llm = llm_provider is not None
    
    async def initialize(self):
        """初始化意图引擎"""
        logger.info("Initializing Intent Engine...")
        
        if self.llm_provider:
            logger.info("LLM provider configured")
            self.use_llm = True
        else:
            logger.info("LLM not available, using rule-based mode only")
        
        logger.info("Intent Engine initialized")
    
    async def parse(self, intent_text: str) -> IntentResult:
        """
        解析意图文本
        
        Args:
            intent_text: 自然语言意图，例如 "搜索iPhone 15"
        
        Returns:
            IntentResult: 解析结果，包含操作步骤
        """
        intent_text = intent_text.strip()
        logger.info(f"Parsing intent: {intent_text}")
        
        # 1. 先尝试规则匹配
        for pattern in self.PATTERNS:
            match = pattern.match(intent_text)
            if match:
                try:
                    steps = pattern.handler(match, self.adapter)
                    return IntentResult(
                        success=True,
                        intent_type=pattern.intent_type,
                        original_intent=intent_text,
                        steps=steps,
                        summary=f"识别为{pattern.intent_type.value}意图，包含{len(steps)}个步骤"
                    )
                except Exception as e:
                    logger.error(f"Error handling intent pattern: {e}")
                    continue
        
        # 2. 规则匹配失败，尝试LLM（如果有）
        if self.use_llm and self.llm_provider:
            return await self._parse_with_llm(intent_text)
        
        # 3. 都失败了
        return IntentResult(
            success=False,
            intent_type=IntentType.UNKNOWN,
            original_intent=intent_text,
            steps=[],
            summary="无法识别意图",
            error="No matching pattern found and LLM not available"
        )
    
    async def _parse_with_llm(self, intent_text: str) -> IntentResult:
        """
        使用LLM解析意图
        
        通过共享的LLM提供者理解复杂意图。
        """
        if not self.llm_provider:
            return IntentResult(
                success=False,
                intent_type=IntentType.UNKNOWN,
                original_intent=intent_text,
                steps=[],
                error="LLM provider not configured"
            )
        
        try:
            # 构建提示词
            prompt = f"""将以下用户意图转换为浏览器操作序列。

用户意图: {intent_text}

可用操作:
- goto: 导航到指定URL
- click: 点击元素
- type: 输入文本
- extract: 提取数据
- scroll: 滚动页面

请分析用户意图，返回JSON格式:
{{
    "intent_type": "navigate|search|click|type|extract|composite",
    "steps": [
        {{
            "action": "操作名",
            "target": {{"css": "选择器"}},
            "value": "值(可选)",
            "description": "操作描述"
        }}
    ],
    "summary": "执行摘要"
}}

只返回JSON，不要其他解释。"""
            
            # 调用共享的LLM，添加超时保护（默认30秒）
            import asyncio
            try:
                response = await asyncio.wait_for(
                    self.llm_provider.complete(
                        prompt=prompt,
                        temperature=0.2,
                        max_tokens=500
                    ),
                    timeout=30.0  # 30秒超时
                )
            except asyncio.TimeoutError:
                logger.error("LLM调用超时（30秒）")
                return IntentResult(
                    success=False,
                    intent_type=IntentType.UNKNOWN,
                    original_intent=intent_text,
                    steps=[],
                    summary="LLM调用超时",
                    error="LLM request timeout after 30 seconds"
                )
            
            # 解析JSON响应
            import json
            try:
                data = json.loads(response)
                steps_data = data.get("steps", [])
                
                steps = []
                for step_data in steps_data:
                    steps.append(ActionStep(
                        action=step_data.get("action", ""),
                        target=step_data.get("target"),
                        value=step_data.get("value"),
                        description=step_data.get("description", "")
                    ))
                
                return IntentResult(
                    success=True,
                    intent_type=IntentType.COMPOSITE,
                    original_intent=intent_text,
                    steps=steps,
                    summary=data.get("summary", f"LLM解析: {intent_text}")
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"LLM响应JSON解析失败: {e}")
                return IntentResult(
                    success=False,
                    intent_type=IntentType.UNKNOWN,
                    original_intent=intent_text,
                    steps=[],
                    error=f"LLM响应格式错误: {e}"
                )
                
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return IntentResult(
                success=False,
                intent_type=IntentType.UNKNOWN,
                original_intent=intent_text,
                steps=[],
                error=f"LLM调用失败: {e}"
            )
    
    async def execute(self, intent_text: str, context: Optional[Dict] = None) -> Dict:
        """
        解析并执行意图
        
        Args:
            intent_text: 自然语言意图
            context: 上下文信息
        
        Returns:
            执行结果
        """
        # 解析意图
        intent_result = await self.parse(intent_text)
        
        if not intent_result.success:
            return {
                "success": False,
                "error": intent_result.error,
                "intent": intent_text
            }
        
        # 执行步骤
        executed_actions = []
        last_data = None
        
        for step in intent_result.steps:
            try:
                result = await self.adapter.execute(
                    step.action,
                    target=step.target,
                    value=step.value,
                    options=step.options
                )
                
                executed_actions.append({
                    "action": step.action,
                    "description": step.description,
                    "success": result.get("success", False)
                })
                
                if result.get("success"):
                    last_data = result.get("data")
                
            except Exception as e:
                logger.error(f"Error executing step {step.action}: {e}")
                executed_actions.append({
                    "action": step.action,
                    "description": step.description,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": all(a["success"] for a in executed_actions),
            "intent": intent_text,
            "intent_type": intent_result.intent_type.value,
            "actions": executed_actions,
            "data": last_data,
            "summary": intent_result.summary
        }
    
    def add_pattern(self, pattern: IntentPattern):
        """添加自定义规则模式"""
        self.PATTERNS.append(pattern)
    
    def list_supported_intents(self) -> List[str]:
        """列出支持的意图类型"""
        return list(set(p.intent_type.value for p in self.PATTERNS))


# ============ 使用示例 ============

async def demo():
    """演示意图引擎"""
    from aibridge.adapters.browser.chrome import ChromeAdapter
    
    # 创建适配器
    adapter = ChromeAdapter()
    await adapter.connect()
    
    # 创建意图引擎
    engine = IntentEngine(adapter)
    await engine.initialize()
    
    # 测试意图
    test_intents = [
        "打开 https://www.baidu.com",
        "搜索 iPhone 15",
        "点击 搜索按钮",
        "提取 所有结果",
        "向下滚动",
    ]
    
    print("\n" + "="*60)
    print("🧪 意图识别引擎测试")
    print("="*60 + "\n")
    
    for intent in test_intents:
        result = await engine.parse(intent)
        print(f"📝 意图: {intent}")
        print(f"   类型: {result.intent_type.value}")
        print(f"   步骤: {len(result.steps)}")
        for i, step in enumerate(result.steps, 1):
            print(f"      {i}. {step.description}")
        print()
    
    await adapter.disconnect()


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
