FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

# 安装依赖
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# 复制源码
COPY . .

# 启动
CMD ["uv", "run", "main.py"]
