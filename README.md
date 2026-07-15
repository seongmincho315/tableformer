# TableFormer Structure Server

docling이 사용하는 TableFormer 표 구조 인식 모델([docling-ibm-models](https://github.com/docling-project/docling-ibm-models))을
FastAPI로 감싼 서빙 앱입니다. 페이지 이미지 + 그 안에서 감지된 테이블 영역(bbox)을 보내면,
각 테이블의 행/열 구조와 셀(bbox/병합 범위/헤더 여부)을 반환합니다.

레이아웃(detr)이 "여기가 테이블이다"까지만 잡아주면, 그 영역 안의 실제 표 구조(몇 행/몇 열,
셀 병합, 헤더)를 복원하는 건 이 서버의 역할입니다.

## Quick start

```shell
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080
```

첫 요청(또는 서버 기동) 시 HuggingFace(`ds4sd/docling-models`)에서 TableFormer 가중치를
내려받습니다. 네트워크가 막힌 환경이라면 아래로 미리 캐시해두세요.

```python
from app.predictor import Predictor
Predictor.download_models(mode="accurate")  # 또는 "fast"
```

## Environment variables

| Name | Default | Description |
|---|---|---|
| `MODE` | `accurate` | `fast` / `accurate` — 정확도-속도 트레이드오프. `accurate`가 느리지만 정확. |
| `DEVICE` | `cpu` | `cpu` / `cuda`. |
| `NUM_THREADS` | `4` | `DEVICE=cpu`일 때 torch 스레드 수. |

## API

### `GET /healthcheck`

```json
{"status": "ok"}
```

### `POST /structure`

페이지 이미지(base64)와, 그 안에서 레이아웃 모델(detr 등)이 감지한 테이블 bbox 목록을 보내면
테이블별 구조를 반환합니다. `tokens`(선택)를 함께 주면 PDF/OCR에서 뽑은 단어 단위 텍스트를
표 셀에 매칭해서 텍스트까지 채워 돌려주고, 생략하면 구조(행/열/셀 bbox)만 예측합니다.

좌표계는 모두 `[l, t, r, b]` = 보낸 이미지 좌상단 기준 픽셀 좌표입니다 (요청에 보낸 이미지
해상도 그대로 — 서버가 임의로 스케일을 바꾸지 않으니, 호출 측에서 detr에 보낸 것과 같은
이미지/좌표계를 그대로 재사용하면 됩니다).

**Request**
```json
{
  "images": ["<base64 png>"],
  "tables": [
    [[40.0, 40.0, 400.0, 200.0]]
  ],
  "tokens": [
    [{"id": 0, "text": "Name", "bbox": [50.0, 50.0, 100.0, 65.0]}]
  ]
}
```

**Response**
```json
{
  "results": [
    [
      {
        "num_rows": 2,
        "num_cols": 2,
        "otsl_seq": ["fcel", "fcel", "nl", "fcel", "fcel"],
        "cells": [
          {"bbox": {"l": 50.0, "t": 50.0, "r": 100.0, "b": 65.0}, "text": "Name", "column_header": true, "...": "..."}
        ]
      }
    ]
  ]
}
```

### 호출 예시 (PyMuPDF로 페이지 렌더링 + 임의 테이블 bbox → 요청)

```python
import base64
import fitz
import httpx

doc = fitz.open("sample.pdf")
page = doc[0]
png_bytes = page.get_pixmap(dpi=150).tobytes("png")

resp = httpx.post(
    "http://localhost:8080/structure",
    json={
        "images": [base64.b64encode(png_bytes).decode("ascii")],
        "tables": [[[40, 40, 400, 200]]],  # 실제로는 detr가 감지한 테이블 bbox를 사용
    },
)
print(resp.json())
```

## Build & deploy

- `build-script/tableformer-build.sh` (+ `.config`): 도커 이미지 빌드/푸시. `MODE`(fast|accurate)
  빌드 시점에 해당 가중치만 이미지에 구워둠 (`ds4sd/docling-models`는 여러 모델을 한 레포에
  묶어둔 저장소라 `allow_patterns`로 필요한 것만 받음).
- `k8s-manifest/`: `llmops` 네임스페이스용 Deployment/Service (`doc-parser-tableformer-*`,
  기본은 ClusterIP, `-node-port` 버전은 NodePort `30882`).
- `docker/Dockerfile`: base → deps(uv sync) → models(HF 가중치 다운로드) → runtime 멀티스테이지.
  `supervisord`가 `uvicorn`을 실행하고, `etc/health_checker.sh`가 60초마다 `/healthcheck`를
  확인해 실패 시 자동 재시작합니다.
- `etc/smoke_test.sh`: 컨테이너 내부에서 `health` → `inference` 순으로 검증 (합성 표 이미지로
  in-process 추론).

레퍼런스: 레이아웃 서빙 레포([`detr`](../detr))와 동일한 구조. 실제 TableFormer 호출 로직은
`genonai/doc_parser` 레포의 `docling/models/table_structure_model.py`를 참고해 이식.
