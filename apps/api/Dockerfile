FROM python:3.12-slim

RUN useradd --create-home --uid 10001 synapse && mkdir -p /workspace /home/synapse && chown -R 10001:10001 /workspace /home/synapse
WORKDIR /workspace

ENV HOME=/home/synapse \
    UV_CACHE_DIR=/tmp/uv-cache \
    PATH="/workspace/.venv/bin:$PATH"

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY packages ./packages
COPY apps/api ./apps/api
COPY apps/worker ./apps/worker
COPY schemas ./schemas

RUN uv sync --locked --no-dev && chown -R 10001:10001 /workspace /home/synapse
USER 10001:10001

EXPOSE 8000
CMD ["/workspace/.venv/bin/python", "-m", "synapse_api.cli"]
