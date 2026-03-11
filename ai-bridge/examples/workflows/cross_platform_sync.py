#!/usr/bin/env python3
"""
工作流示例：跨平台信息同步
Workflow Example: Cross-Platform Information Sync

这个工作流演示如何使用 AI-Bridge 在多个 IM 平台间同步消息：
- 从一个平台读取消息
- 格式化后发送到其他平台
- 记录同步日志
"""

import asyncio
import sys
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, '../../src')

from aibridge.core.manager import AdapterManager
from aibridge.core.protocol import Target


class CrossPlatformSyncWorkflow:
    """跨平台同步工作流"""
    
    def __init__(self):
        self.manager = AdapterManager()
        self.sync_log: List[Dict] = []
        
    async def setup(self, platforms: List[str]):
        """初始化指定平台的适配器"""
        
        if "feishu" in platforms:
            from aibridge.adapters.im.feishu import FeishuAdapter, FeishuConfig
            config = FeishuConfig(
                app_id="your_feishu_app_id",
                app_secret="your_feishu_app_secret"
            )
            self.manager.register(FeishuAdapter(config))
            
        if "dingtalk" in platforms:
            from aibridge.adapters.im.dingtalk import DingtalkAdapter, DingtalkConfig
            config = DingtalkConfig(
                app_key="your_dingtalk_app_key",
                app_secret="your_dingtalk_app_secret"
            )
            self.manager.register(DingtalkAdapter(config))
            
        if "wecom" in platforms:
            from aibridge.adapters.im.wecom import WecomAdapter, WecomConfig
            config = WecomConfig(
                corp_id="your_wecom_corp_id",
                corp_secret="your_wecom_corp_secret",
                agent_id="your_wecom_agent_id"
            )
            self.manager.register(WecomAdapter(config))
            
        print(f"✓ 已初始化平台: {platforms}")
        
    async def broadcast_message(
        self,
        message: str,
        targets: Dict[str, str],
        message_type: str = "text"
    ):
        """
        广播消息到多个平台
        
        Args:
            message: 消息内容
            targets: {平台名: 目标ID} 映射
            message_type: 消息类型 (text/markdown/card)
        """
        print(f"\n📢 广播消息到 {len(targets)} 个平台...")
        
        results = {}
        
        for platform, target_id in targets.items():
            adapter = self.manager.get(platform)
            if not adapter:
                print(f"  ⚠ 平台 {platform} 未注册")
                continue
                
            try:
                # 连接平台
                connected = await adapter.connect()
                if not connected:
                    print(f"  ✗ {platform}: 连接失败")
                    continue
                    
                # 根据平台格式化消息
                formatted_message = self._format_message(
                    message, platform, message_type
                )
                
                # 发送消息
                result = await adapter.execute(
                    action="send_message",
                    target=Target(name=target_id),
                    value=formatted_message,
                    options={"msg_type": message_type}
                )
                
                results[platform] = "success"
                print(f"  ✓ {platform}: 发送成功")
                
                # 记录日志
                self.sync_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "platform": platform,
                    "target": target_id,
                    "status": "success"
                })
                
            except Exception as e:
                results[platform] = f"error: {e}"
                print(f"  ✗ {platform}: {e}")
                
                self.sync_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "platform": platform,
                    "target": target_id,
                    "status": "failed",
                    "error": str(e)
                })
                
            finally:
                await adapter.disconnect()
                
        return results
        
    def _format_message(
        self,
        message: str,
        platform: str,
        message_type: str
    ) -> str:
        """根据平台格式化消息"""
        
        if message_type == "text":
            return message
            
        if message_type == "markdown":
            # 不同平台的 markdown 语法可能有差异
            if platform == "feishu":
                # 飞书使用自己的富文本格式
                return message
            elif platform == "dingtalk":
                # 钉钉支持标准 markdown
                return message
            elif platform == "wecom":
                # 企业微信 markdown 有限制
                return message
                
        return message
        
    async def sync_announcement(
        self,
        title: str,
        content: str,
        platforms: Dict[str, str]
    ):
        """
        同步公告到多个平台
        
        Args:
            title: 公告标题
            content: 公告内容
            platforms: {平台名: 群聊ID} 映射
        """
        print("\n" + "=" * 50)
        print(f"📣 同步公告: {title}")
        print("=" * 50)
        
        # 构造通用格式消息
        message = f"""📢 {title}

{content}

---
发布时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
        results = await self.broadcast_message(
            message=message,
            targets=platforms,
            message_type="text"
        )
        
        # 统计结果
        success_count = sum(1 for v in results.values() if v == "success")
        print(f"\n✓ 同步完成: {success_count}/{len(platforms)} 个平台成功")
        
        return results
        
    def get_sync_log(self) -> List[Dict]:
        """获取同步日志"""
        return self.sync_log


async def demo():
    """演示跨平台同步"""
    
    workflow = CrossPlatformSyncWorkflow()
    
    # 初始化平台 (实际使用时需要真实凭证)
    await workflow.setup(["feishu", "dingtalk", "wecom"])
    
    # 定义同步目标
    targets = {
        "feishu": "oc_feishu_group_id",      # 飞书群聊ID
        "dingtalk": "dingtalk_group_id",      # 钉钉群聊ID
        "wecom": "wecom_group_id",            # 企微群聊ID
    }
    
    # 发送公告
    await workflow.sync_announcement(
        title="系统维护通知",
        content="""
各位同事：

系统将于今晚 22:00-24:00 进行例行维护升级，届时以下服务将暂停：
- 工单系统
- 报表系统
- 审批流程

请提前做好相关工作安排，如有紧急事项请联系 IT 支持。

感谢配合！
""",
        platforms=targets
    )
    
    # 打印同步日志
    print("\n📋 同步日志:")
    for log in workflow.get_sync_log():
        status = "✓" if log["status"] == "success" else "✗"
        print(f"  {status} [{log['timestamp']}] {log['platform']} -> {log['target']}")


if __name__ == "__main__":
    asyncio.run(demo())
