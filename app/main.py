import base64
import io
import os
from typing import List, Optional

from fastapi import FastAPI
from PIL import Image
from pydantic import BaseModel

from app.predictor import Predictor

app = FastAPI(title="TableFormer Structure Server")

predictor = Predictor(
    mode=os.getenv("MODE", "accurate"),
    device=os.getenv("DEVICE", "cpu"),
    num_threads=int(os.getenv("NUM_THREADS", "4")),
)


class Token(BaseModel):
    id: int
    text: str
    bbox: List[float]  # [l, t, r, b]


class TableStructureRequest(BaseModel):
    images: List[str]  # base64 인코딩된 페이지 이미지 목록
    tables: List[List[List[float]]]  # 이미지별 테이블 bbox 목록, 각 bbox = [l, t, r, b]
    tokens: Optional[List[Optional[List[Token]]]] = None  # (optional) 이미지별 단어 단위 토큰


class TableCell(BaseModel):
    class Config:
        extra = "allow"


class TableStructureResult(BaseModel):
    num_rows: int
    num_cols: int
    otsl_seq: List[str]
    cells: List[TableCell]


class TableStructureResponse(BaseModel):
    results: List[List[TableStructureResult]]  # 이미지별 테이블별 구조 결과


def _decode_image(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64)))


@app.get("/healthcheck")
async def healthcheck():
    return {"status": "ok"}


@app.post("/structure", response_model=TableStructureResponse)
async def structure(request: TableStructureRequest):
    images = [_decode_image(b64) for b64 in request.images]
    tokens = None
    if request.tokens is not None:
        tokens = [
            [t.model_dump() for t in page_tokens] if page_tokens is not None else None
            for page_tokens in request.tokens
        ]
    results = predictor.predict_batch(images, request.tables, tokens)
    return {"results": results}
