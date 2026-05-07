"""
DevOps 领域意图模式 — 9 个模式
覆盖 Docker 容器管理和 Git 版本控制
"""

from aibridge.core.intent_pattern import IntentPattern, Slot, SlotType

DEVOPS_PATTERNS = [
    # Docker
    IntentPattern(
        id="devops.docker_list", domain="devops",
        patterns=["列出容器", "查看所有容器", "显示{状态:string}的容器"],
        description="列出Docker容器",
        slots=[Slot("状态", SlotType.STRING, required=False,
                   description="容器状态",
                   enum_values=["运行中", "已停止", "全部"])],
        examples=["列出容器", "显示运行中的容器"],
    ),
    IntentPattern(
        id="devops.docker_start", domain="devops",
        patterns=["启动容器{名称:string}", "运行{名称:string}"],
        description="启动Docker容器",
        slots=[Slot("名称", SlotType.STRING, description="容器名称")],
        examples=["启动容器nginx", "运行mysql"],
    ),
    IntentPattern(
        id="devops.docker_stop", domain="devops",
        patterns=["停止{名称:string}", "关闭容器{名称:string}"],
        description="停止Docker容器",
        slots=[Slot("名称", SlotType.STRING, description="容器名称")],
        examples=["停止nginx", "关闭容器mysql"],
    ),
    IntentPattern(
        id="devops.docker_logs", domain="devops",
        patterns=["查看{名称:string}日志", "{名称:string}的日志"],
        description="查看容器日志",
        slots=[Slot("名称", SlotType.STRING, description="容器名称")],
        examples=["查看nginx日志", "mysql的日志"],
    ),
    IntentPattern(
        id="devops.docker_compose", domain="devops",
        patterns=["启动{文件:path}的docker-compose", "用{文件:path}编排容器"],
        description="启动docker-compose编排",
        slots=[Slot("文件", SlotType.PATH, description="docker-compose.yml路径")],
        examples=["启动docker-compose.yml的docker-compose", "用prod.yml编排容器"],
    ),
    # Git
    IntentPattern(
        id="devops.git_status", domain="devops",
        patterns=["查看git状态", "git状态"],
        description="查看Git仓库状态",
        examples=["查看git状态", "git状态"],
    ),
    IntentPattern(
        id="devops.git_commit", domain="devops",
        patterns=["提交代码", "git commit -m {信息:string}"],
        description="提交代码变更",
        slots=[Slot("信息", SlotType.STRING, description="提交信息")],
        examples=["提交代码", "git commit -m fix bug"],
    ),
    IntentPattern(
        id="devops.git_push", domain="devops",
        patterns=["推送代码", "git push"],
        description="推送代码到远程仓库",
        examples=["推送代码", "git push"],
    ),
    IntentPattern(
        id="devops.git_branch", domain="devops",
        patterns=["创建分支{名称:string}", "切换到{名称:string}分支"],
        description="管理Git分支",
        slots=[Slot("名称", SlotType.STRING, description="分支名称")],
        examples=["创建分支feature-login", "切换到main分支"],
    ),
]
