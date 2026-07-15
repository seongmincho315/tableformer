# syntax=docker/dockerfile:1.7

########################################
# 0) 공통 ARG
########################################
ARG PY_VER=3.11
ARG DEBIAN_DIST=bookworm
ARG APP_DIR=/app
# 빌드 시점에 미리 받아서 이미지에 구워둘 TableFormer 모드
ARG MODE=accurate

########################################
# 1) Base (OS + uv + supervisor)
########################################
FROM python:${PY_VER}-slim-${DEBIAN_DIST} AS base

ARG APP_DIR
ENV APP_DIR=${APP_DIR}

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        tini \
        supervisor \
        curl \
        ca-certificates \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN mkdir -p ${APP_DIR}
WORKDIR ${APP_DIR}

########################################
# 2) deps (pyproject/uv.lock → venv)
########################################
FROM base AS deps

ARG APP_DIR
WORKDIR ${APP_DIR}

COPY pyproject.toml uv.lock README.md ${APP_DIR}/

RUN uv venv ${APP_DIR}/.venv
ENV VIRTUAL_ENV=${APP_DIR}/.venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --python ${VIRTUAL_ENV}/bin/python

########################################
# 3) models (TableFormer 가중치를 이미지에 구워둠)
########################################
FROM deps AS models

ARG APP_DIR
ARG MODE
ENV HF_HOME=/models/hf-cache
ENV MODE=${MODE}

COPY app ${APP_DIR}/app

# 런타임엔 HF_HUB_OFFLINE=1이라 여기서 실패하면 폐쇄망에서 그대로 못 뜨므로, 실패를 삼키지 않고 빌드를 깨뜨림
RUN mkdir -p ${HF_HOME} && \
    ${APP_DIR}/.venv/bin/python -c "\
from app.predictor import Predictor; \
import os; \
Predictor.download_models(os.environ['MODE'])"

########################################
# 4) runtime (최종)
########################################
FROM base AS runtime

ARG APP_DIR
ARG MODE
ENV VIRTUAL_ENV=${APP_DIR}/.venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ENV HF_HOME=/models/hf-cache
ENV MODE=${MODE}
ENV DEVICE=cpu
ENV NUM_THREADS=4
# 모델은 빌드 단계(models stage)에서 이미 이미지에 구워둠 — 런타임엔 HF Hub 접속 자체를 막아서
# 폐쇄망에서도 동작하게 함 (안 걸면 캐시가 있어도 매번 Hub에 접속을 시도함)
ENV HF_HUB_OFFLINE=1

WORKDIR ${APP_DIR}

COPY --from=deps ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --from=models /models /models
COPY app ${APP_DIR}/app
COPY config ${APP_DIR}/config
COPY docker ${APP_DIR}/docker
COPY etc ${APP_DIR}/etc

RUN ln -sf ${APP_DIR}/config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf && \
    chmod +x ${APP_DIR}/etc/*.sh

EXPOSE 8080

CMD ["supervisord", "-n"]
