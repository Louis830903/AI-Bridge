"""
Collab 领域意图模式 — 4 个模式
覆盖 Slack、Notion、GitHub Issues、Email 协作工具
"""

from aibridge.core.intent_pattern import IntentPattern, Slot, SlotType

COLLAB_PATTERNS = [
    IntentPattern(
        id="collab.slack_send", domain="collab",
        patterns=["发Slack消息到{频道:string}", "在Slack{频道:string}发{消息:string}"],
        description="发送Slack消息",
        slots=[
            Slot("频道", SlotType.STRING, description="Slack频道名"),
            Slot("消息", SlotType.STRING, description="消息内容"),
        ],
        examples=["发Slack消息到general", "在Slack#dev发部署完成"],
    ),
    IntentPattern(
        id="collab.notion_sync", domain="collab",
        patterns=["同步到Notion", "把{内容:string}存到Notion{页面:string}"],
        description="同步内容到Notion页面",
        slots=[
            Slot("内容", SlotType.STRING, description="要同步的内容"),
            Slot("页面", SlotType.STRING, description="Notion页面名"),
        ],
        examples=["同步到Notion", "把会议纪要存到Notion周报页面"],
    ),
    IntentPattern(
        id="collab.github_issue", domain="collab",
        patterns=["在{仓库:string}创建Issue", "给{仓库:string}提Bug"],
        description="在GitHub仓库创建Issue",
        slots=[Slot("仓库", SlotType.STRING, description="GitHub仓库名")],
        examples=["在ai-bridge创建Issue", "给project/repo提Bug"],
    ),
    IntentPattern(
        id="collab.email_send", domain="collab",
        patterns=["发邮件给{收件人:string}", "发送{主题:string}到{收件人:string}"],
        description="发送邮件",
        slots=[
            Slot("收件人", SlotType.STRING, description="收件人邮箱"),
            Slot("主题", SlotType.STRING, description="邮件主题"),
        ],
        examples=["发邮件给admin@example.com", "发送会议邀请到team@company.com"],
    ),
]
