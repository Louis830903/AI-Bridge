"""
意图识别引擎 (Intent Engine) - v2.0

三级意图解析流水线:
L1: 精确模式匹配 → L2: 语义搜索 → L3: LLM 理解回退

将自然语言意图转换为结构化操作。
支持两种模式:
1. 规则匹配模式 - 基于关键词和模式匹配（无需LLM）
2. LLM模式 - 使用大语言模型理解复杂意图（可选）

Phase II — 意图引擎通用化 (v0.10.0)

示例:
- "搜索iPhone 15" → goto("https://search.xxx") + type("#search", "iPhone 15") + click("#submit")
- "点击提交按钮" → click({"text": "提交"})
- "提取所有商品价格" → extract({"css": ".price"}, {"price": "number"}, multiple=True)
- "把video.mp4转成gif" → L1命中 ffmpeg.convert 模式
"""

from __future__ import annotations

import re
import json
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional, Callable, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from aibridge.adapters.browser.chrome import ChromeAdapter
    from aibridge.core.llm_provider import LLMProvider

from aibridge.adapters.base import BaseAdapter
from aibridge.core.domain_registry import DomainIntentRegistry
from aibridge.core.intent_pattern import (
    IntentMatch,
    CompositeIntent,
    IntentPattern as ProtocolIntentPattern,
)

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
        handler: Callable[[re.Match, BaseAdapter], List[ActionStep]]
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

# 模块级搜索引擎配置
SEARCH_ENGINES = {
    "baidu": {"search_box": "#kw", "search_btn": "#su"},
    "google": {"search_box": "input[name='q']", "search_btn": "input[name='btnK']"},
    "bing": {"search_box": "#sb_form_q", "search_btn": "#sb_form_go"},
}


def handle_navigate(match: re.Match, adapter: BaseAdapter) -> List[ActionStep]:
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


def handle_search(match: re.Match, adapter: BaseAdapter) -> List[ActionStep]:
    """处理搜索意图 — 支持多搜索引擎配置"""
    keyword = match.group(1)
    # 从 adapter 获取搜索引擎配置（如果可用），否则默认百度
    engine = getattr(adapter, '_search_engine', None) or 'baidu'
    config = SEARCH_ENGINES.get(engine, SEARCH_ENGINES["baidu"])
    
    return [
        ActionStep(
            action="type",
            target={"css": config["search_box"]},
            value=keyword,
            options={"force": True},
            description=f"在搜索框输入: {keyword}"
        ),
        ActionStep(
            action="click",
            target={"css": config["search_btn"]},
            options={"force": True},
            description="点击搜索按钮"
        )
    ]


def handle_click(match: re.Match, adapter: BaseAdapter) -> List[ActionStep]:
    """处理点击意图"""
    target_text = match.group(1)
    
    return [ActionStep(
        action="click",
        target={"text": target_text},
        options={"force": True},
        description=f"点击包含文本的元素: {target_text}"
    )]


def handle_type(match: re.Match, adapter: BaseAdapter) -> List[ActionStep]:
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


def handle_extract(match: re.Match, adapter: BaseAdapter) -> List[ActionStep]:
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


def handle_scroll(match: re.Match, adapter: BaseAdapter) -> List[ActionStep]:
    """处理滚动意图"""
    direction = match.group(1).lower() if match.group(1) else "down"
    
    return [ActionStep(
        action="scroll",
        value=direction,
        description=f"向{direction}滚动页面"
    )]


# ============ 意图引擎 v2.0 流水线配置 ============

@dataclass
class IntentPipelineConfig:
    """三级流水线配置"""
    l1_timeout_ms: int = 50         # L1 精确匹配超时
    l2_timeout_ms: int = 500        # L2 语义搜索超时
    l3_timeout_ms: int = 5000       # L3 LLM 超时
    l2_top_k: int = 5               # 语义搜索返回数量
    l2_min_confidence: float = 0.5  # L2 最低置信度
    l3_auto_register: bool = False  # 是否自动注册新模式
    l3_register_threshold: float = 0.8  # 自动注册置信阈值


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
    
    # 默认超时配置（秒），可被实例属性覆盖
    DEFAULT_EXECUTE_TIMEOUT = 120.0  # 意图解析+执行总超时
    DEFAULT_STEP_TIMEOUT = 30.0      # 单步操作超时

    def __init__(self, adapter: BaseAdapter, llm_provider=None):
        self.adapter = adapter
        self.llm_provider = llm_provider
        self.use_llm = llm_provider is not None
        self._execute_timeout = self.DEFAULT_EXECUTE_TIMEOUT
        self._stats = {"l1_hits": 0, "l2_hits": 0, "l3_hits": 0, "misses": 0}
        self._registry: DomainIntentRegistry | None = None
    
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
        patterns = getattr(self, '_patterns', self.PATTERNS)
        for pattern in patterns:
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
    
    async def execute(self, intent_text: str, context: Optional[Dict] = None,
                      timeout: Optional[float] = None) -> Dict:
        """
        解析并执行意图，带全局超时保护
        
        Args:
            intent_text: 自然语言意图
            context: 上下文信息
            timeout: 单次调用超时（秒），None 则使用实例默认值
        
        Returns:
            执行结果
        """
        effective_timeout = timeout if timeout is not None else self._execute_timeout
        try:
            return await asyncio.wait_for(
                self._execute_internal(intent_text, context),
                timeout=effective_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"意图执行超时（{effective_timeout}秒）: {intent_text}")
            return {
                "success": False,
                "error": f"意图执行超时（{effective_timeout}秒）",
                "intent": intent_text
            }

    async def _execute_internal(self, intent_text: str, context: Optional[Dict] = None) -> Dict:
        """内部执行逻辑（实际执行意图步骤）"""
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

    def set_timeout(self, seconds: float):
        """动态调整超时时间
        
        Args:
            seconds: 超时秒数
        """
        self._execute_timeout = seconds
    
    # ========== v2.0 三级意图解析流水线 ==========

    async def resolve(
        self,
        user_input: str,
        domain: str | None = None,
        registry: DomainIntentRegistry | None = None,
        config: IntentPipelineConfig | None = None,
    ) -> IntentMatch | CompositeIntent | None:
        """三级流水线解析用户意图。

        Args:
            user_input: 自然语言输入
            domain: 限定的领域 (可选)
            registry: 外部注册中心（为 None 则使用内部注册中心）
            config: 流水线配置（为 None 则使用默认配置）

        Returns:
            IntentMatch (单意图), CompositeIntent (复合意图), 或 None

        Raises:
            IntentRouteError: 所有级别都失败时
        """
        cfg = config or IntentPipelineConfig()
        reg = registry or getattr(self, '_registry', None)
        if reg is None:
            logger.debug("No registry configured, falling back to rule-based parse")
            return None

        # L1: 精确模式匹配
        result = await self._resolve_l1(user_input, domain, reg, cfg)
        if result:
            self._stats["l1_hits"] = self._stats.get("l1_hits", 0) + 1
            return result

        # L2: 语义搜索
        result = await self._resolve_l2(user_input, reg, cfg)
        if result:
            self._stats["l2_hits"] = self._stats.get("l2_hits", 0) + 1
            return result

        # L3: LLM 回退
        if self.llm_provider:
            result = await self._resolve_l3(user_input, reg, cfg)
            if result:
                self._stats["l3_hits"] = self._stats.get("l3_hits", 0) + 1
                return result

        self._stats["misses"] = self._stats.get("misses", 0) + 1
        return None

    async def _resolve_l1(
        self,
        user_input: str,
        domain: str | None,
        registry: DomainIntentRegistry,
        config: IntentPipelineConfig,
    ) -> IntentMatch | None:
        """L1: 精确模式匹配——基于注册的模板"""
        try:
            matches = await asyncio.wait_for(
                asyncio.to_thread(registry.match, user_input, domain),
                timeout=config.l1_timeout_ms / 1000,
            )
            if matches and matches[0].confidence >= matches[0].pattern.confidence_threshold:
                logger.debug(
                    f"L1 hit: {matches[0].pattern.id} "
                    f"(conf={matches[0].confidence:.2f})"
                )
                return matches[0]
            if matches:
                logger.debug(
                    f"L1 low confidence: {matches[0].pattern.id} "
                    f"(conf={matches[0].confidence:.2f} < "
                    f"threshold={matches[0].pattern.confidence_threshold})"
                )
        except asyncio.TimeoutError:
            logger.warning("L1 match timeout")
        return None

    async def _resolve_l2(
        self,
        user_input: str,
        registry: DomainIntentRegistry,
        config: IntentPipelineConfig,
    ) -> IntentMatch | CompositeIntent | None:
        """L2: 语义搜索 + 组合意图检测"""
        try:
            matches = await asyncio.wait_for(
                asyncio.to_thread(
                    registry.semantic_search, user_input, config.l2_top_k
                ),
                timeout=config.l2_timeout_ms / 1000,
            )
            if not matches or matches[0].confidence < config.l2_min_confidence:
                return None

            # 检测是否为复合意图（多个高置信度匹配）
            high_conf = [m for m in matches if m.confidence > 0.6]
            if len(high_conf) >= 2:
                logger.info(
                    f"L2 composite intent detected: "
                    f"{[m.pattern.id for m in high_conf]}"
                )
                return CompositeIntent(
                    sub_intents=high_conf,
                    dag={m.pattern.id: [] for m in high_conf},
                    original_text=user_input,
                )

            logger.debug(
                f"L2 hit: {matches[0].pattern.id} "
                f"(conf={matches[0].confidence:.2f})"
            )
            return matches[0]
        except asyncio.TimeoutError:
            logger.warning("L2 semantic search timeout")
        return None

    async def _resolve_l3(
        self,
        user_input: str,
        registry: DomainIntentRegistry,
        config: IntentPipelineConfig,
    ) -> IntentMatch | None:
        """L3: LLM 理解 + 自动注册候选"""
        try:
            context = registry.to_prompt_context()
            result = await asyncio.wait_for(
                self.llm_provider.parse_intent(user_input, context),
                timeout=config.l3_timeout_ms / 1000,
            )
            if result and result.confidence >= 0.5:
                logger.info(f"L3 LLM resolved: {result.pattern.id}")

                # 自动注册候选
                if (
                    config.l3_auto_register
                    and result.confidence >= config.l3_register_threshold
                ):
                    logger.info(
                        f"Auto-registering new pattern: {result.pattern.id}"
                    )
                    registry.register(result.pattern.adapter_id, [result.pattern])

                return result
        except asyncio.TimeoutError:
            logger.error("L3 LLM timeout")
        except Exception as e:
            logger.error(f"L3 LLM error: {e}")
        return None

    def get_stats(self) -> dict:
        """获取三级流水线统计"""
        stats = {
            "l1_hits": 0, "l2_hits": 0, "l3_hits": 0, "misses": 0
        }
        stats.update(self._stats)
        total = max(sum(stats.values()), 1)
        return {
            **stats,
            "total": total,
            "l1_rate": stats["l1_hits"] / total,
            "l2_rate": stats["l2_hits"] / total,
            "l3_rate": stats["l3_hits"] / total,
            "miss_rate": stats["misses"] / total,
        }

    def set_registry(self, registry: DomainIntentRegistry):
        """设置意图注册中心"""
        self._registry = registry

    def add_pattern(self, pattern: IntentPattern):
        """添加自定义规则模式"""
        # 安全：复制类变量到实例变量，避免修改类本身
        if not hasattr(self, '_patterns'):
            self._patterns = list(self.PATTERNS)
        self._patterns.append(pattern)
    
    def list_supported_intents(self) -> List[str]:
        """列出支持的意图类型"""
        patterns = getattr(self, '_patterns', self.PATTERNS)
        return list(set(p.intent_type.value for p in patterns))


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
