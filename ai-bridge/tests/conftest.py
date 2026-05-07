"""AI-Bridge test configuration."""

import pytest
import asyncio


# ═══════════════════════════════════════════════════════════════════
# CLI Options — 可选测试层级开关
# ═══════════════════════════════════════════════════════════════════

def pytest_addoption(parser):
    parser.addoption(
        "--integration", action="store_true", default=False,
        help="运行集成测试（需要 Docker/FFmpeg/Git 等外部依赖）",
    )
    parser.addoption(
        "--e2e", action="store_true", default=False,
        help="运行端到端测试（需要完整 AI-Bridge 环境）",
    )
    parser.addoption(
        "--perf", action="store_true", default=False,
        help="运行性能基准测试",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: 集成测试（需要外部依赖如 Docker/FFmpeg/Git）")
    config.addinivalue_line("markers", "docker: 需要 Docker 守护进程的集成测试")
    config.addinivalue_line("markers", "e2e: 端到端全链路测试")
    config.addinivalue_line("markers", "perf: 性能基准测试")


def pytest_collection_modifyitems(config, items):
    skip_integration = pytest.mark.skip(reason="需要 --integration 标志")
    skip_e2e = pytest.mark.skip(reason="需要 --e2e 标志")
    skip_perf = pytest.mark.skip(reason="需要 --perf 标志")

    for item in items:
        if "integration" in item.keywords and not config.getoption("--integration"):
            item.add_marker(skip_integration)
        if "e2e" in item.keywords and not config.getoption("--e2e"):
            item.add_marker(skip_e2e)
        if "perf" in item.keywords and not config.getoption("--perf"):
            item.add_marker(skip_perf)


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_config():
    """Sample configuration for tests."""
    return {
        "chrome": {
            "enabled": True,
            "cdp_url": "http://localhost:9222",
        },
        "feishu": {
            "enabled": True,
            "app_id": "test_app_id",
            "app_secret": "test_secret",
        },
    }
