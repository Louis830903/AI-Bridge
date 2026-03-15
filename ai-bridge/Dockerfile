# AI-Bridge v5.0 Docker 镜像
# MCP + A2A 双协议网关
#
# 使用方法:
#   docker build -t aibridge .
#   docker run -p 9090:9090 aibridge
#
# 或使用 docker-compose:
#   docker-compose up -d

FROM python:3.11-slim

LABEL maintainer="AI-Bridge Team"
LABEL version="5.0.0"
LABEL description="MCP + A2A Dual Protocol Gateway for AI Assistants"

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # AI-Bridge 配置
    AIBRIDGE_LOG_LEVEL=INFO \
    AIBRIDGE_METRICS_ENABLED=true \
    AIBRIDGE_METRICS_PORT=9090

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 基础工具
    curl \
    # Playwright 依赖
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件（先复制源码，再安装）
COPY pyproject.toml ./
COPY src/ ./src/
COPY examples/ ./examples/

# 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install -e ".[all]"

# 安装 Playwright 浏览器
RUN playwright install chromium --with-deps

# 创建非 root 用户
RUN useradd -m -u 1000 aibridge && \
    chown -R aibridge:aibridge /app
USER aibridge

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9090/metrics || exit 1

# 暴露端口
# 9090: Prometheus 指标
# 8080: Web Dashboard (可选)
EXPOSE 9090 8080

# 默认命令
CMD ["python", "-m", "aibridge"]
