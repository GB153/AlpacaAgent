FROM python:3.12-slim

# no __pycache__
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen

COPY . .

CMD ["uv", "run", "python", "main.py"]
