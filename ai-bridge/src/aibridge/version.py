"""AI-Bridge version information.

Changelog:
    v1.0.0     - Phase IV: 铸盾·生产就绪 (分层测试体系 + 铁幕CI + 性能基准)
    v0.9.0-rc1 - Phase I: 版本校准、统一异常体系、代码规范
    v0.1.0     - Initial development
"""

__version__ = "1.0.0"
__version_info__ = tuple(
    int(x) if x.isdigit() else x
    for x in __version__.replace("-", ".").split(".")
)
