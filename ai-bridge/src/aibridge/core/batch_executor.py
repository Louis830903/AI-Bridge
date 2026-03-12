"""
Batch Executor - 批量并行操作执行器

支持批量执行多个操作，可选择串行或并行模式。

使用示例:
```python
# 串行执行
results = await adapter.execute_batch([
    {"action": "goto", "target": {"url": "https://www.baidu.com"}},
    {"action": "type", "target": {"css": "#kw"}, "value": "Python"},
    {"action": "click", "target": {"css": "#su"}}
])

# 并行执行多个提取任务
results = await adapter.execute_batch([
    {"action": "extract", "target": {"css": ".price"}},
    {"action": "extract", "target": {"css": ".title"}},
    {"action": "extract", "target": {"css": ".rating"}}
], parallel=True, max_workers=3)
```
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

logger = logging.getLogger(__name__)


class BatchMode(str, Enum):
    """批量执行模式"""
    SEQUENTIAL = "sequential"  # 串行
    PARALLEL = "parallel"      # 并行


@dataclass
class BatchAction:
    """批量操作定义"""
    action: str
    target: Optional[Dict] = None
    value: Optional[Any] = None
    options: Optional[Dict] = field(default_factory=dict)
    id: Optional[str] = None  # 操作标识，用于结果匹配


@dataclass
class BatchResult:
    """批量操作结果"""
    action_id: Optional[str]
    action: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    index: int = 0


class BatchExecutor:
    """
    批量执行器
    
    支持串行和并行执行多个操作。
    """
    
    def __init__(self, adapter):
        """
        初始化批量执行器
        
        Args:
            adapter: ChromeAdapter 实例
        """
        self.adapter = adapter
    
    async def execute_batch(
        self,
        actions: List[Dict],
        mode: BatchMode = BatchMode.SEQUENTIAL,
        max_workers: int = 3,
        stop_on_error: bool = False,
        on_progress: Optional[Callable[[int, int, BatchResult], None]] = None
    ) -> Dict[str, Any]:
        """
        批量执行操作
        
        Args:
            actions: 操作列表，每个操作是包含 action/target/value/options 的字典
            mode: 执行模式（串行/并行）
            max_workers: 并行模式下的最大并发数
            stop_on_error: 遇到错误是否停止
            on_progress: 进度回调函数 (current, total, result)
        
        Returns:
            批量执行结果
        """
        import time
        
        start_time = time.time()
        total = len(actions)
        
        logger.info(f"开始批量执行: {total} 个操作, 模式: {mode.value}")
        
        if mode == BatchMode.SEQUENTIAL:
            results = await self._execute_sequential(
                actions, stop_on_error, on_progress
            )
        else:
            results = await self._execute_parallel(
                actions, max_workers, stop_on_error, on_progress
            )
        
        duration = (time.time() - start_time) * 1000
        
        # 统计结果
        success_count = sum(1 for r in results if r.success)
        failure_count = len(results) - success_count
        
        logger.info(f"批量执行完成: {success_count}/{total} 成功, 耗时 {duration:.0f}ms")
        
        return {
            "success": failure_count == 0,
            "mode": mode.value,
            "total": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "duration_ms": duration,
            "results": [
                {
                    "index": r.index,
                    "id": r.action_id,
                    "action": r.action,
                    "success": r.success,
                    "data": r.data,
                    "error": r.error,
                    "duration_ms": r.duration_ms
                }
                for r in results
            ]
        }
    
    async def _execute_sequential(
        self,
        actions: List[Dict],
        stop_on_error: bool,
        on_progress: Optional[Callable]
    ) -> List[BatchResult]:
        """串行执行"""
        results = []
        
        for i, action_def in enumerate(actions):
            result = await self._execute_single(i, action_def)
            results.append(result)
            
            if on_progress:
                on_progress(i + 1, len(actions), result)
            
            if not result.success and stop_on_error:
                logger.warning(f"操作 {i} 失败，停止后续执行")
                break
        
        return results
    
    async def _execute_parallel(
        self,
        actions: List[Dict],
        max_workers: int,
        stop_on_error: bool,
        on_progress: Optional[Callable]
    ) -> List[BatchResult]:
        """并行执行"""
        # 注意：浏览器操作通常需要在同一个页面上串行执行
        # 这里的并行主要是针对可以独立执行的操作
        # 实际实现中需要小心处理并发问题
        
        results = [None] * len(actions)
        completed = 0
        
        # 使用信号量限制并发
        semaphore = asyncio.Semaphore(max_workers)
        
        async def execute_with_semaphore(index: int, action_def: Dict):
            nonlocal completed
            
            async with semaphore:
                result = await self._execute_single(index, action_def)
                results[index] = result
                completed += 1
                
                if on_progress:
                    on_progress(completed, len(actions), result)
                
                return result
        
        # 创建所有任务
        tasks = [
            execute_with_semaphore(i, action_def)
            for i, action_def in enumerate(actions)
        ]
        
        if stop_on_error:
            # 遇到错误停止：逐个执行
            for task in tasks:
                result = await task
                if not result.success:
                    # 取消剩余任务
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    break
        else:
            # 继续执行所有
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def _execute_single(self, index: int, action_def: Dict) -> BatchResult:
        """执行单个操作"""
        import time
        
        start_time = time.time()
        
        action = action_def.get("action")
        target = action_def.get("target")
        value = action_def.get("value")
        options = action_def.get("options", {})
        action_id = action_def.get("id")
        
        try:
            result = await self.adapter.execute(
                action=action,
                target=target,
                value=value,
                options=options
            )
            
            duration = (time.time() - start_time) * 1000
            
            return BatchResult(
                action_id=action_id,
                action=action,
                success=result.get("success", False),
                data=result.get("data"),
                error=result.get("error"),
                duration_ms=duration,
                index=index
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"批量操作 {index} 异常: {e}")
            
            return BatchResult(
                action_id=action_id,
                action=action,
                success=False,
                error=str(e),
                duration_ms=duration,
                index=index
            )
    
    async def execute_chain(
        self,
        actions: List[Dict],
        on_step: Optional[Callable[[int, Dict, Dict], None]] = None
    ) -> Dict[str, Any]:
        """
        执行操作链（前一步的结果传给后一步）
        
        Args:
            actions: 操作列表
            on_step: 每步完成的回调 (index, input, output)
        
        Returns:
            最终结果
        """
        logger.info(f"开始执行操作链: {len(actions)} 步")
        
        context = {}  # 上下文数据，可以在步骤间传递
        last_result = None
        
        for i, action_def in enumerate(actions):
            logger.info(f"链式执行步骤 {i + 1}/{len(actions)}: {action_def.get('action')}")
            
            # 允许使用上一步的结果
            if last_result and action_def.get("use_previous_result"):
                # 将上一步结果注入到 target 或 value
                if "target" in action_def and isinstance(action_def["target"], dict):
                    for key, val in action_def["target"].items():
                        if isinstance(val, str) and "{{previous}}" in val:
                            action_def["target"][key] = val.replace("{{previous}}", str(last_result.get("data", "")))
            
            # 执行操作
            result = await self.adapter.execute(
                action=action_def.get("action"),
                target=action_def.get("target"),
                value=action_def.get("value"),
                options=action_def.get("options", {})
            )
            
            if on_step:
                on_step(i, action_def, result)
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": f"步骤 {i} 失败: {result.get('error')}",
                    "failed_step": i,
                    "context": context,
                    "last_result": result
                }
            
            # 更新上下文
            context[f"step_{i}"] = result
            last_result = result
        
        return {
            "success": True,
            "steps": len(actions),
            "context": context,
            "final_result": last_result
        }


# ============ 便捷函数 ============

async def demo():
    """演示批量执行"""
    from aibridge.adapters.browser.chrome import ChromeAdapter
    
    adapter = ChromeAdapter()
    await adapter.connect()
    
    executor = BatchExecutor(adapter)
    
    # 演示串行执行
    print("\n=== 串行执行 ===")
    results = await executor.execute_batch([
        {"action": "goto", "target": {"url": "https://www.baidu.com"}, "id": "navigate"},
        {"action": "type", "target": {"css": "#kw"}, "value": "Python", "id": "type_search"},
    ], mode=BatchMode.SEQUENTIAL)
    
    print(f"结果: {results['success_count']}/{results['total']} 成功")
    
    await adapter.disconnect()


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
