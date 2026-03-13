"""
O-R-A 循环 (Observation-Reasoning-Action Loop)

观察-推理-行动循环，实现复杂任务的自主完成。

工作流程:
1. Observation (观察): 获取当前页面状态
2. Reasoning (推理): 分析状态，决定下一步
3. Action (行动): 执行具体操作
4. 循环直到任务完成或达到最大步数

示例任务:
"在京东搜索 iPhone 15，提取前3个商品的价格和评分"

循环过程:
Step 1: 观察 → 当前空白页
        推理 → 需要先导航到京东
        行动 → goto("https://www.jd.com")

Step 2: 观察 → 京东首页，有搜索框
        推理 → 需要输入搜索词
        行动 → type("#search", "iPhone 15")

Step 3: 观察 → 搜索词已输入
        推理 → 需要点击搜索按钮
        行动 → click("#search-btn")

Step 4: 观察 → 搜索结果页面
        推理 → 需要提取商品信息
        行动 → extract(".goods-item", {"price": "string", "rating": "string"})

Step 5: 任务完成，返回结果
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from aibridge.adapters.browser.chrome import ChromeAdapter
from aibridge.core.intent_engine import IntentEngine, IntentType

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"           # 待执行
    RUNNING = "running"           # 执行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消


@dataclass
class StepRecord:
    """单步执行记录"""
    step_number: int                    # 步数
    timestamp: datetime                 # 时间戳
    
    # Observation
    observation: Dict[str, Any] = field(default_factory=dict)
    
    # Reasoning
    reasoning: str = ""                 # 推理过程
    plan: List[str] = field(default_factory=list)  # 计划
    
    # Action
    action: str = ""                    # 执行的动作
    action_params: Dict = field(default_factory=dict)
    
    # Result
    success: bool = False
    result_data: Any = None
    error: Optional[str] = None
    
    # 截图（可选）
    screenshot_b64: Optional[str] = None


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    goal: str
    status: TaskStatus
    steps: List[StepRecord]
    data: Any = None
    summary: str = ""
    total_steps: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None


class PageObserver:
    """
    页面观察者 - 负责 Observation 阶段
    
    收集当前页面的状态信息，供 Reasoning 阶段使用。
    """
    
    def __init__(self, adapter: ChromeAdapter):
        self.adapter = adapter
    
    async def observe(self, include_screenshot: bool = True) -> Dict[str, Any]:
        """
        观察当前页面状态
        
        Returns:
            页面状态信息，包括:
            - url: 当前URL
            - title: 页面标题
            - elements: 可交互元素
            - forms: 表单信息
            - links: 链接信息
            - screenshot: 截图（可选）
        """
        observation = {
            "timestamp": datetime.now().isoformat(),
        }
        
        try:
            # 1. 基础信息
            observation["url"] = self.adapter._page.url if self.adapter._page else None
            observation["title"] = await self.adapter._page.title() if self.adapter._page else None
            
            # 2. 获取可交互元素
            try:
                elements = await self.adapter._get_interactive_elements()
                observation["elements"] = elements[:20]  # 只取前20个避免过多
                observation["element_count"] = len(elements)
            except Exception as e:
                logger.warning(f"Failed to get interactive elements: {e}")
                observation["elements"] = []
                observation["element_count"] = 0
            
            # 3. 获取A11y快照（结构化视图）
            try:
                snapshot_result = await self.adapter._take_accessibility_snapshot()
                if snapshot_result.get("success"):
                    observation["a11y_snapshot"] = snapshot_result.get("snapshot", "")[:500]  # 截断
                    observation["a11y_element_count"] = snapshot_result.get("element_count", 0)
            except Exception as e:
                logger.warning(f"Failed to get a11y snapshot: {e}")
            
            # 4. 截图
            if include_screenshot:
                try:
                    screenshot = await self.adapter._page.screenshot(full_page=False)
                    import base64
                    observation["screenshot_b64"] = base64.b64encode(screenshot).decode()
                except Exception as e:
                    logger.warning(f"Failed to take screenshot: {e}")
            
            # 5. 页面文本内容（前500字符）
            try:
                body_text = await self.adapter._page.evaluate("() => document.body.innerText.slice(0, 500)")
                observation["body_text_preview"] = body_text
            except Exception as e:
                logger.warning(f"Failed to get body text: {e}")
            
        except Exception as e:
            logger.error(f"Observation failed: {e}")
            observation["error"] = str(e)
        
        return observation


class ReasoningEngine:
    """
    推理引擎 - 负责 Reasoning 阶段
    
    根据观察结果，决定下一步行动。
    支持两种模式:
    1. 规则推理 - 基于预定义规则
    2. LLM推理 - 使用大语言模型（可选）
    """
    
    def __init__(self, adapter: ChromeAdapter, llm_provider=None):
        """
        初始化推理引擎

        Args:
            adapter: ChromeAdapter 实例
            llm_provider: 共享的LLM提供者（可选）
        """
        self.adapter = adapter
        self.llm_provider = llm_provider
        self.use_llm = llm_provider is not None
    
    async def reason(
        self,
        goal: str,
        observation: Dict[str, Any],
        history: List[StepRecord],
        remaining_steps: int
    ) -> Dict[str, Any]:
        """
        推理下一步行动
        
        Args:
            goal: 任务目标
            observation: 当前观察结果
            history: 历史执行记录
            remaining_steps: 剩余步数
        
        Returns:
            推理结果，包含:
            - reasoning: 推理过程说明
            - action: 建议的行动
            - action_params: 行动参数
            - is_complete: 任务是否已完成
        """
        
        # 1. 检查任务是否已完成（基于简单规则）
        completion_check = self._check_completion(goal, observation, history)
        if completion_check["is_complete"]:
            return {
                "reasoning": completion_check["reason"],
                "action": "complete",
                "action_params": {},
                "is_complete": True
            }
        
        # 2. 基于规则的推理
        rule_result = self._rule_based_reasoning(goal, observation, history)
        if rule_result:
            return rule_result
        
        # 3. 使用LLM推理（如果有）
        if self.use_llm:
            return await self._llm_reasoning(goal, observation, history, remaining_steps)
        
        # 4. 默认：无法推理
        return {
            "reasoning": "无法确定下一步行动",
            "action": "unknown",
            "action_params": {},
            "is_complete": False,
            "error": "No matching reasoning rule found"
        }
    
    def _infer_url_from_goal(self, goal: str) -> str:
        """
        从目标推断URL
        
        支持多种方式:
        1. 直接提取 http:// 或 https:// 链接
        2. 根据关键词推断 (百度 -> baidu.com, 京东 -> jd.com 等)
        3. 默认返回百度
        """
        import re
        
        # 1. 直接提取完整URL
        url_match = re.search(r'(https?://[^\s]+)', goal)
        if url_match:
            return url_match.group(1)
        
        # 2. 从目标中提取域名
        domain_match = re.search(r'(?:www\.)?([\w-]+\.(?:com|cn|org|net|io))', goal)
        if domain_match:
            return f"https://{domain_match.group(1)}"
        
        # 3. 根据关键词推断常用网站
        goal_lower = goal.lower()
        url_mapping = {
            # 中文关键词
            "百度": "https://www.baidu.com",
            "baidu": "https://www.baidu.com",
            "京东": "https://www.jd.com",
            "jd": "https://www.jd.com",
            "淘宝": "https://www.taobao.com",
            "taobao": "https://www.taobao.com",
            "天猫": "https://www.tmall.com",
            "tmall": "https://www.tmall.com",
            "知乎": "https://www.zhihu.com",
            "zhihu": "https://www.zhihu.com",
            "微博": "https://weibo.com",
            "weibo": "https://weibo.com",
            "GitHub": "https://github.com",
            "github": "https://github.com",
            "谷歌": "https://www.google.com",
            "google": "https://www.google.com",
            "必应": "https://www.bing.com",
            "bing": "https://www.bing.com",
            "搜狗": "https://www.sogou.com",
            "sogou": "https://www.sogou.com",
            "B站": "https://www.bilibili.com",
            "bilibili": "https://www.bilibili.com",
            "抖音": "https://www.douyin.com",
            "douyin": "https://www.douyin.com",
        }
        
        for keyword, url in url_mapping.items():
            if keyword in goal or keyword in goal_lower:
                return url
        
        # 4. 默认返回百度
        return "https://www.baidu.com"
    
    def _check_completion(
        self,
        goal: str,
        observation: Dict[str, Any],
        history: List[StepRecord]
    ) -> Dict[str, Any]:
        """检查任务是否已完成"""
        
        # 简单规则：如果已经执行过提取操作且有数据，认为任务完成
        for step in reversed(history):
            if step.action == "extract" and step.success and step.result_data:
                return {
                    "is_complete": True,
                    "reason": f"已成功提取数据: {step.result_data}"
                }
        
        # 规则2: 如果目标只是"打开/访问 XXX"，且已经成功导航到目标网站
        if ("打开" in goal or "访问" in goal or "goto" in goal.lower()) and history:
            last_goto = None
            for step in history:
                if step.action == "goto" and step.success:
                    last_goto = step
            
            if last_goto:
                # 检查当前URL是否匹配目标
                current_url = observation.get("url", "")
                expected_url = self._infer_url_from_goal(goal)
                
                # 如果URL匹配或在同一个域名下，认为任务完成
                if expected_url in current_url or (
                    last_goto.action_params.get("url") in current_url
                ):
                    return {
                        "is_complete": True,
                        "reason": f"已成功打开目标网站: {current_url}"
                    }
        
        # 如果目标包含"搜索"且已经导航并输入了搜索词
        if "搜索" in goal or "search" in goal.lower():
            has_navigated = any(s.action == "goto" for s in history)
            has_typed = any(s.action == "type" for s in history)
            has_clicked_search = any(
                s.action == "click" and "搜索" in s.reasoning 
                for s in history
            )
            
            if has_navigated and has_typed and has_clicked_search:
                # 检查是否在搜索结果页面
                url = observation.get("url", "")
                if "search" in url or "query" in url or "result" in observation.get("title", "").lower():
                    return {
                        "is_complete": True,
                        "reason": "搜索任务已完成，已在搜索结果页面"
                    }
        
        return {"is_complete": False, "reason": ""}
    
    def _rule_based_reasoning(
        self,
        goal: str,
        observation: Dict[str, Any],
        history: List[StepRecord]
    ) -> Optional[Dict[str, Any]]:
        """基于规则的推理"""
        
        url = observation.get("url", "")
        title = observation.get("title", "")
        elements = observation.get("elements", [])
        history_actions = [s.action for s in history]
        
        # 规则1: 如果是空白页或about:blank，或者当前页面与目标不匹配，需要导航
        target_url = self._infer_url_from_goal(goal)
        
        # 检查是否需要导航：空白页 或 URL不匹配
        need_navigation = (
            not url or 
            url in ["about:blank", ""] or
            (target_url not in url and url not in target_url)
        )
        
        if need_navigation and "goto" not in history_actions:
            return {
                "reasoning": f"需要导航到目标网站: {target_url}",
                "action": "goto",
                "action_params": {"url": target_url},
                "is_complete": False
            }
        
        # 规则2: 如果目标是搜索，且还没有输入搜索词
        if ("搜索" in goal or "search" in goal.lower()) and "type" not in history_actions:
            # 提取搜索关键词
            import re
            keywords = re.findall(r'搜索\s*["\']?([^"\']+)["\']?', goal)
            if not keywords:
                keywords = re.findall(r'search\s+(?:for\s+)?["\']?([^"\']+)["\']?', goal, re.I)
            
            keyword = keywords[0] if keywords else goal.replace("搜索", "").strip()
            
            return {
                "reasoning": f"需要搜索 '{keyword}'，在搜索框中输入关键词",
                "action": "type",
                "action_params": {
                    "selector": "#kw",  # 百度搜索框
                    "text": keyword,
                    "force": True
                },
                "is_complete": False
            }
        
        # 规则3: 如果已经输入了搜索词，还没有点击搜索
        if ("搜索" in goal or "search" in goal.lower()) and "type" in history_actions and "click" not in history_actions:
            return {
                "reasoning": "已输入搜索词，需要点击搜索按钮",
                "action": "click",
                "action_params": {
                    "selector": "#su",  # 百度搜索按钮
                    "force": True
                },
                "is_complete": False
            }
        
        # 规则4: 如果在搜索结果页面，需要提取数据
        if ("提取" in goal or "extract" in goal.lower() or "获取" in goal) and "extract" not in history_actions:
            # 判断提取什么
            if "价格" in goal or "price" in goal.lower():
                selector = ".price"  # 假设价格选择器
            elif "标题" in goal or "title" in goal.lower():
                selector = "h1, h2, h3"
            else:
                selector = ".result"  # 默认搜索结果
            
            return {
                "reasoning": f"需要提取页面数据，使用选择器: {selector}",
                "action": "extract",
                "action_params": {
                    "selector": selector,
                    "fields": {"text": "string"},
                    "multiple": True
                },
                "is_complete": False
            }
        
        # 规则5: 如果页面加载慢，等待一下
        if observation.get("element_count", 0) == 0:
            return {
                "reasoning": "页面元素较少，可能需要等待加载",
                "action": "wait",
                "action_params": {"timeout": 2000},
                "is_complete": False
            }
        
        return None
    
    async def _llm_reasoning(
        self,
        goal: str,
        observation: Dict[str, Any],
        history: List[StepRecord],
        remaining_steps: int
    ) -> Dict[str, Any]:
        """
        使用LLM进行推理

        通过共享的LLM提供者进行智能推理。
        """
        if not self.llm_provider:
            return {
                "reasoning": "LLM provider not configured",
                "action": "unknown",
                "action_params": {},
                "is_complete": False
            }

        try:
            # 构建提示词
            history_summary = []
            for step in history[-5:]:  # 最近5步
                history_summary.append(f"- Step {step.step_number}: {step.action} - {'success' if step.success else 'failed'}")

            prompt = f"""作为浏览器自动化助手，根据当前状态决定下一步行动。

目标: {goal}

当前页面:
- URL: {observation.get('url', 'unknown')}
- Title: {observation.get('title', 'unknown')}
- 可交互元素: {observation.get('element_count', 0)} 个

最近执行历史:
{chr(10).join(history_summary) if history_summary else '无'}

剩余步数: {remaining_steps}

可用操作: goto, click, type, extract, scroll, wait

请分析并返回JSON格式:
{{
    "reasoning": "为什么执行这个行动",
    "action": "操作名",
    "action_params": {{
        "selector": "CSS选择器或目标",
        "value": "值(如果需要)"
    }},
    "is_complete": true/false
}}

只返回JSON，不要其他解释。"""

            # 调用共享LLM
            response = await self.llm_provider.complete(
                prompt=prompt,
                temperature=0.3,
                max_tokens=400
            )

            # 解析JSON
            import json
            try:
                data = json.loads(response)
                return {
                    "reasoning": data.get("reasoning", "LLM推理"),
                    "action": data.get("action", "unknown"),
                    "action_params": data.get("action_params", {}),
                    "is_complete": data.get("is_complete", False)
                }
            except json.JSONDecodeError:
                logger.error(f"LLM响应JSON解析失败: {response[:200]}")
                return {
                    "reasoning": "LLM响应格式错误",
                    "action": "unknown",
                    "action_params": {},
                    "is_complete": False
                }

        except Exception as e:
            logger.error(f"LLM推理失败: {e}")
            return {
                "reasoning": f"LLM调用失败: {e}",
                "action": "unknown",
                "action_params": {},
                "is_complete": False
            }


class ActionExecutor:
    """
    行动执行器 - 负责 Action 阶段
    
    执行具体的浏览器操作。
    """
    
    def __init__(self, adapter: ChromeAdapter, intent_engine: IntentEngine):
        self.adapter = adapter
        self.intent_engine = intent_engine
    
    async def execute(self, action: str, params: Dict) -> Dict[str, Any]:
        """
        执行行动
        
        Args:
            action: 行动类型
            params: 行动参数
        
        Returns:
            执行结果
        """
        try:
            if action == "complete":
                return {"success": True, "data": None}
            
            elif action == "unknown":
                return {"success": False, "error": "Unknown action"}
            
            elif action == "goto":
                # goto 操作特殊处理 - 支持 url 参数
                url = params.get("url") or params.get("target", {}).get("url")
                if not url:
                    return {"success": False, "error": "goto 操作需要提供 url"}
                result = await self.adapter.execute(
                    "goto",
                    target={"url": url},
                    options=params.get("options", {})
                )
                return result
            
            elif action in ["click", "type", "extract", "scroll", "wait", "screenshot"]:
                # 其他标准操作
                result = await self.adapter.execute(
                    action,
                    target=params.get("target") or ({"css": params["selector"]} if "selector" in params else None),
                    value=params.get("text") or params.get("value"),
                    options=params.get("options", {})
                )
                return result
            
            elif action == "intent":
                # 使用意图引擎执行
                intent_text = params.get("intent")
                result = await self.intent_engine.execute(intent_text, {})
                return result
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return {"success": False, "error": str(e)}


class Orchestrator:
    """
    编排器 - O-R-A 循环的主控制器
    
    协调 Observation、Reasoning、Action 三个阶段，
    完成复杂任务的自主执行。
    """
    
    def __init__(
        self,
        adapter: ChromeAdapter,
        intent_engine: IntentEngine,
        max_steps: int = 10,
        use_llm: bool = False
    ):
        self.adapter = adapter
        self.intent_engine = intent_engine
        self.max_steps = max_steps
        self.use_llm = use_llm
        
        # 初始化各组件
        self.observer = PageObserver(adapter)
        self.reasoning_engine = ReasoningEngine(adapter, use_llm)
        self.action_executor = ActionExecutor(adapter, intent_engine)
        
        # 回调函数
        self.on_step: Optional[Callable[[StepRecord], None]] = None
        self.on_complete: Optional[Callable[[TaskResult], None]] = None
    
    async def execute_task(
        self,
        goal: str,
        max_steps: Optional[int] = None,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行复杂任务
        
        Args:
            goal: 任务目标描述
            max_steps: 最大执行步数
            callback_url: 可选的回调URL
        
        Returns:
            任务执行结果
        """
        import time
        start_time = time.time()
        
        max_steps = max_steps or self.max_steps
        history: List[StepRecord] = []
        
        logger.info(f"Starting O-R-A task: {goal}")
        logger.info(f"Max steps: {max_steps}")
        
        # O-R-A 循环防死循环保护
        visited_states = set()  # 记录已访问状态
        consecutive_same_state = 0  # 连续相同状态计数
        
        for step_num in range(1, max_steps + 1):
            logger.info(f"\n--- Step {step_num}/{max_steps} ---")
            
            # 检查 adapter 是否仍然连接
            if not self.adapter or not self.adapter.is_connected:
                logger.error("Adapter disconnected during task execution")
                return {
                    "success": False,
                    "status": TaskStatus.FAILED,
                    "steps_taken": step_num - 1,
                    "error": "Browser adapter disconnected"
                }
            
            # 检查是否被外部取消
            if hasattr(self, '_cancelled') and self._cancelled:
                logger.info("Task was cancelled")
                return {
                    "success": False,
                    "status": TaskStatus.CANCELLED,
                    "steps_taken": step_num - 1,
                    "error": "Task was cancelled by user"
                }
            
            # ========== Observation ==========
            logger.info("[Observation] Observing current state...")
            observation = await self.observer.observe(include_screenshot=True)
            
            # ========== Reasoning ==========
            logger.info("[Reasoning] Deciding next action...")
            reasoning_result = await self.reasoning_engine.reason(
                goal=goal,
                observation=observation,
                history=history,
                remaining_steps=max_steps - step_num
            )
            
            # 检查是否完成
            if reasoning_result.get("is_complete"):
                logger.info("[Reasoning] Task completed!")
                break
            
            action = reasoning_result.get("action")
            action_params = reasoning_result.get("action_params", {})
            reasoning_text = reasoning_result.get("reasoning", "")
            
            logger.info(f"[Reasoning] Plan: {reasoning_text}")
            logger.info(f"[Reasoning] Action: {action}")
            
            # ========== Action ==========
            logger.info(f"[Action] Executing: {action}")
            action_result = await self.action_executor.execute(action, action_params)
            
            # 记录步骤
            step_record = StepRecord(
                step_number=step_num,
                timestamp=datetime.now(),
                observation=observation,
                reasoning=reasoning_text,
                action=action,
                action_params=action_params,
                success=action_result.get("success", False),
                result_data=action_result.get("data"),
                error=action_result.get("error"),
                screenshot_b64=observation.get("screenshot_b64")
            )
            history.append(step_record)
            
            # 防死循环检测：检查是否重复相同的状态
            state_key = f"{observation.get('url')}:{action}:{hash(str(action_params))}"
            if state_key in visited_states:
                consecutive_same_state += 1
                if consecutive_same_state >= 3:
                    logger.error(f"检测到死循环：连续 {consecutive_same_state} 次相同状态")
                    return {
                        "success": False,
                        "status": TaskStatus.FAILED,
                        "steps_taken": step_num,
                        "error": "Detected infinite loop: repeating same state",
                        "history": history
                    }
            else:
                consecutive_same_state = 0
                visited_states.add(state_key)
            
            # 防死循环：限制状态历史大小
            if len(visited_states) > max_steps * 2:
                visited_states.clear()
            
            # 触发回调
            if self.on_step:
                await self._async_callback(self.on_step, step_record)
            
            logger.info(f"[Action] Result: {action_result.get('success')}")
            
            # 如果行动失败，尝试恢复
            if not action_result.get("success"):
                logger.warning(f"Action failed: {action_result.get('error')}")
                # 简单恢复：等待一下继续
                await asyncio.sleep(1)
        
        # 构建最终结果
        duration = time.time() - start_time
        
        # 判断任务是否成功
        last_step = history[-1] if history else None
        success = last_step is not None and (
            last_step.action == "complete" or 
            (last_step.action == "extract" and last_step.success and last_step.result_data)
        )
        
        result = TaskResult(
            success=success,
            goal=goal,
            status=TaskStatus.COMPLETED if success else TaskStatus.FAILED,
            steps=history,
            data=last_step.result_data if last_step else None,
            summary=f"任务{'完成' if success else '失败'}，共执行{len(history)}步，耗时{duration:.1f}秒",
            total_steps=len(history),
            duration_seconds=duration
        )
        
        # 触发完成回调
        if self.on_complete:
            await self._async_callback(self.on_complete, result)
        
        logger.info(f"\nTask finished: {result.summary}")
        
        return {
            "success": result.success,
            "goal": result.goal,
            "status": result.status.value,
            "steps": [
                {
                    "step": s.step_number,
                    "action": s.action,
                    "reasoning": s.reasoning,
                    "success": s.success,
                    "data": s.result_data
                }
                for s in history
            ],
            "data": result.data,
            "summary": result.summary,
            "total_steps": result.total_steps,
            "duration": result.duration_seconds
        }
    
    async def _async_callback(self, callback: Callable, data: Any):
        """异步执行回调"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as e:
            logger.error(f"Callback error: {e}")


# ============ 使用示例 ============

async def demo():
    """演示 O-R-A 循环"""
    from aibridge.adapters.browser.chrome import ChromeAdapter
    from aibridge.core.intent_engine import IntentEngine
    
    # 创建组件
    adapter = ChromeAdapter()
    await adapter.connect()
    
    intent_engine = IntentEngine(adapter)
    await intent_engine.initialize()
    
    orchestrator = Orchestrator(adapter, intent_engine, max_steps=5)
    
    # 设置回调
    def on_step(step: StepRecord):
        print(f"  Step {step.step_number}: {step.action} - {'✅' if step.success else '❌'}")
    
    def on_complete(result: TaskResult):
        print(f"\n✨ Task {'completed' if result.success else 'failed'}!")
    
    orchestrator.on_step = on_step
    orchestrator.on_complete = on_complete
    
    # 执行任务
    print("\n" + "="*60)
    print("🤖 O-R-A 循环演示")
    print("="*60)
    
    goal = "在百度上搜索 'iPhone 15'"
    print(f"\n📝 Goal: {goal}\n")
    
    result = await orchestrator.execute_task(goal, max_steps=5)
    
    print(f"\n📊 Result: {result['summary']}")
    print(f"📈 Data: {result['data']}")
    
    await adapter.disconnect()


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
