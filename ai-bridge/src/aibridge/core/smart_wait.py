"""
Smart Wait - 智能等待和重试机制

提供更智能的元素等待和操作重试策略。

使用示例:
```python
# 智能等待网络空闲
await adapter.execute(
    "click",
    target={"css": "#submit"},
    options={
        "smart_wait": True,
        "wait_for": "network_idle",  # 等待网络空闲
        "retry_count": 3,             # 失败重试3次
        "retry_delay": 1000           # 重试间隔1秒
    }
)

# 等待元素稳定
await adapter.execute(
    "click",
    target={"css": "#btn"},
    options={
        "wait_for": "element_stable",  # 等待元素位置稳定
        "stable_duration": 500         # 稳定500ms
    }
)
```
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class WaitCondition(str, Enum):
    """等待条件类型"""
    NETWORK_IDLE = "network_idle"           # 网络空闲
    ELEMENT_STABLE = "element_stable"       # 元素位置稳定
    ELEMENT_VISIBLE = "element_visible"     # 元素可见
    ELEMENT_CLICKABLE = "element_clickable" # 元素可点击
    PAGE_LOAD = "page_load"                 # 页面加载完成
    CUSTOM = "custom"                       # 自定义条件


class SmartWait:
    """
    智能等待器
    
    提供多种等待策略和自动重试机制。
    """
    
    def __init__(self, page):
        self.page = page
    
    async def wait(
        self,
        condition: WaitCondition,
        target: Optional[Dict] = None,
        timeout: int = 10000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行智能等待
        
        Args:
            condition: 等待条件
            target: 目标元素（某些条件需要）
            timeout: 超时时间（毫秒）
            **kwargs: 额外参数
        
        Returns:
            等待结果
        """
        try:
            if condition == WaitCondition.NETWORK_IDLE:
                return await self._wait_for_network_idle(timeout)
            
            elif condition == WaitCondition.ELEMENT_STABLE:
                selector = target.get("css") if target else None
                duration = kwargs.get("stable_duration", 500)
                return await self._wait_for_element_stable(selector, duration, timeout)
            
            elif condition == WaitCondition.ELEMENT_VISIBLE:
                selector = target.get("css") if target else None
                return await self._wait_for_element_visible(selector, timeout)
            
            elif condition == WaitCondition.ELEMENT_CLICKABLE:
                selector = target.get("css") if target else None
                return await self._wait_for_element_clickable(selector, timeout)
            
            elif condition == WaitCondition.PAGE_LOAD:
                wait_until = kwargs.get("wait_until", "networkidle")
                return await self._wait_for_page_load(wait_until, timeout)
            
            elif condition == WaitCondition.CUSTOM:
                check_fn = kwargs.get("check_fn")
                if not check_fn:
                    return {"success": False, "error": "CUSTOM 条件需要提供 check_fn"}
                return await self._wait_for_custom(check_fn, timeout)
            
            else:
                return {"success": False, "error": f"未知的等待条件: {condition}"}
                
        except Exception as e:
            logger.error(f"智能等待失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _wait_for_network_idle(self, timeout: int) -> Dict[str, Any]:
        """等待网络空闲"""
        try:
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
            return {
                "success": True,
                "condition": "network_idle",
                "message": "网络已空闲"
            }
        except Exception as e:
            return {
                "success": False,
                "condition": "network_idle",
                "error": str(e)
            }
    
    async def _wait_for_element_stable(
        self,
        selector: Optional[str],
        duration: int,
        timeout: int
    ) -> Dict[str, Any]:
        """等待元素位置稳定"""
        if not selector:
            return {"success": False, "error": "等待元素稳定需要提供 selector"}
        
        try:
            # 获取初始位置
            element = self.page.locator(selector)
            
            start_time = asyncio.get_event_loop().time()
            stable_start = None
            last_box = None
            
            while (asyncio.get_event_loop().time() - start_time) * 1000 < timeout:
                try:
                    box = await element.bounding_box()
                    
                    if box and last_box:
                        # 检查位置是否变化
                        if (abs(box["x"] - last_box["x"]) < 1 and
                            abs(box["y"] - last_box["y"]) < 1 and
                            abs(box["width"] - last_box["width"]) < 1 and
                            abs(box["height"] - last_box["height"]) < 1):
                            
                            if stable_start is None:
                                stable_start = asyncio.get_event_loop().time()
                            elif (asyncio.get_event_loop().time() - stable_start) * 1000 >= duration:
                                return {
                                    "success": True,
                                    "condition": "element_stable",
                                    "message": f"元素已稳定 {duration}ms"
                                }
                        else:
                            stable_start = None
                    
                    last_box = box
                    
                except Exception:
                    stable_start = None
                
                await asyncio.sleep(0.05)  # 50ms 检查一次
            
            return {
                "success": False,
                "condition": "element_stable",
                "error": f"等待超时，元素未在 {timeout}ms 内稳定"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _wait_for_element_visible(self, selector: Optional[str], timeout: int) -> Dict[str, Any]:
        """等待元素可见"""
        if not selector:
            return {"success": False, "error": "需要提供 selector"}
        
        try:
            await self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            return {
                "success": True,
                "condition": "element_visible",
                "message": "元素已可见"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _wait_for_element_clickable(self, selector: Optional[str], timeout: int) -> Dict[str, Any]:
        """等待元素可点击"""
        if not selector:
            return {"success": False, "error": "需要提供 selector"}
        
        try:
            element = self.page.locator(selector)
            
            # 等待可见和启用
            await element.wait_for(state="visible", timeout=timeout)
            
            # 检查是否启用
            is_enabled = await element.is_enabled()
            if not is_enabled:
                return {"success": False, "error": "元素已禁用"}
            
            return {
                "success": True,
                "condition": "element_clickable",
                "message": "元素可点击"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _wait_for_page_load(self, wait_until: str, timeout: int) -> Dict[str, Any]:
        """等待页面加载"""
        try:
            await self.page.wait_for_load_state(wait_until, timeout=timeout)
            return {
                "success": True,
                "condition": "page_load",
                "message": f"页面已加载 ({wait_until})"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _wait_for_custom(
        self,
        check_fn: Callable[[], bool],
        timeout: int
    ) -> Dict[str, Any]:
        """自定义等待条件"""
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) * 1000 < timeout:
            try:
                if check_fn():
                    return {
                        "success": True,
                        "condition": "custom",
                        "message": "自定义条件已满足"
                    }
            except Exception as e:
                logger.warning(f"自定义检查函数异常: {e}")
            
            await asyncio.sleep(0.1)
        
        return {
            "success": False,
            "condition": "custom",
            "error": "等待超时"
        }


class RetryHandler:
    """
    重试处理器
    
    处理操作失败后的自动重试。
    """
    
    @staticmethod
    async def execute_with_retry(
        operation: Callable,
        retry_count: int = 3,
        retry_delay: int = 1000,
        on_retry: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        执行带重试的操作
        
        Args:
            operation: 要执行的操作函数
            retry_count: 最大重试次数
            retry_delay: 重试间隔（毫秒）
            on_retry: 重试时的回调函数
        
        Returns:
            操作结果
        """
        last_error = None
        
        for attempt in range(retry_count + 1):
            try:
                result = await operation()
                
                if result.get("success"):
                    if attempt > 0:
                        logger.info(f"操作在尝试 {attempt + 1} 后成功")
                    return result
                
                last_error = result.get("error", "Unknown error")
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"操作失败 (尝试 {attempt + 1}/{retry_count + 1}): {e}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < retry_count:
                if on_retry:
                    on_retry(attempt + 1, retry_count + 1, last_error)
                
                logger.info(f"等待 {retry_delay}ms 后重试...")
                await asyncio.sleep(retry_delay / 1000)
        
        # 所有尝试都失败
        return {
            "success": False,
            "error": f"操作在 {retry_count + 1} 次尝试后仍然失败: {last_error}",
            "retry_count": retry_count,
            "last_error": last_error
        }


# ============ 集成到 ChromeAdapter 的辅助函数 ============

async def execute_with_smart_wait(
    adapter,
    action: str,
    target: Optional[Dict],
    value: Optional[Any],
    options: Dict
) -> Dict[str, Any]:
    """
    使用智能等待执行操作
    
    这个函数会被集成到 ChromeAdapter.execute 中。
    """
    # 检查是否需要智能等待
    smart_wait = options.get("smart_wait", False)
    wait_for = options.get("wait_for")
    retry_count = options.get("retry_count", 0)
    retry_delay = options.get("retry_delay", 1000)
    
    if not smart_wait and not wait_for and retry_count == 0:
        # 不需要智能等待和重试，直接返回
        return None  # 让调用者执行原始操作
    
    # 如果需要等待条件
    if wait_for and adapter._page:
        smart_waiter = SmartWait(adapter._page)
        
        condition = WaitCondition(wait_for) if isinstance(wait_for, str) else wait_for
        
        wait_result = await smart_waiter.wait(
            condition=condition,
            target=target,
            timeout=options.get("timeout", 10000),
            stable_duration=options.get("stable_duration", 500),
            wait_until=options.get("wait_until", "networkidle")
        )
        
        if not wait_result.get("success"):
            return wait_result  # 等待失败，直接返回
    
    # 执行操作（带重试）
    async def do_execute():
        return await adapter._execute_original(action, target, value, options)
    
    if retry_count > 0:
        return await RetryHandler.execute_with_retry(
            do_execute,
            retry_count=retry_count,
            retry_delay=retry_delay
        )
    else:
        return await do_execute()


# ============ 使用示例 ============

async def demo():
    """演示智能等待"""
    from aibridge.adapters.browser.chrome import ChromeAdapter
    
    adapter = ChromeAdapter()
    await adapter.connect()
    
    # 导航到页面
    await adapter.execute("goto", target={"url": "https://www.baidu.com"})
    
    # 使用智能等待点击
    print("\n使用智能等待点击...")
    result = await adapter.execute(
        "click",
        target={"css": "#su"},
        options={
            "smart_wait": True,
            "wait_for": "element_clickable",
            "retry_count": 2
        }
    )
    print(f"结果: {result}")
    
    await adapter.disconnect()


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
