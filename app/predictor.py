from pathlib import Path
from typing import List, Optional

import numpy as np
from huggingface_hub import snapshot_download
from PIL import Image

MODES = ("fast", "accurate")


class Predictor:
    _model_repo_folder = "model_artifacts/tableformer"

    def __init__(
        self,
        mode: str = "accurate",
        device: str = "cpu",
        num_threads: int = 4,
    ):
        if mode not in MODES:
            raise ValueError(f"알 수 없는 mode입니다: {mode} (선택지: {list(MODES)})")

        # Third Party
        import docling_ibm_models.tableformer.common as c
        from docling_ibm_models.tableformer.data_management.tf_predictor import (
            TFPredictor,
        )

        artifacts_path = self.download_models(mode) / self._model_repo_folder / mode

        tm_config = c.read_config(f"{artifacts_path}/tm_config.json")
        tm_config["model"]["save_dir"] = artifacts_path

        self._predictor = TFPredictor(tm_config, device, num_threads)

    @staticmethod
    def download_models(
        mode: str, local_dir: Optional[Path] = None, force: bool = False
    ) -> Path:
        # ds4sd/docling-models는 layout/tableformer 등 여러 모델을 한 레포에 묶어둔 저장소라,
        # 실제 서빙에 쓸 mode(fast|accurate)의 가중치만 받아 이미지 용량을 줄인다.
        return Path(
            snapshot_download(
                repo_id="ds4sd/docling-models",
                revision="v2.2.0",
                allow_patterns=[f"{Predictor._model_repo_folder}/{mode}/*"],
                local_dir=local_dir,
                force_download=force,
            )
        )

    def predict(
        self,
        image: Image.Image,
        table_bboxes: List[List[float]],
        tokens: Optional[List[dict]] = None,
    ) -> List[dict]:
        """
        image: 표가 포함된 페이지 전체 이미지 (테이블 bbox와 같은 좌표계/해상도)
        table_bboxes: 이 페이지에서 감지된 테이블 영역 목록, [l, t, r, b] 픽셀 좌표
        tokens: (optional) 텍스트 매칭에 쓸 단어 단위 토큰 [{"id", "text", "bbox": [l,t,r,b]}, ...].
                주어지면 tf_predictor가 PDF/OCR 텍스트를 표 셀에 매칭(do_matching=True),
                없으면 모델이 예측한 구조만 반환(do_matching=False, 텍스트는 클라이언트가 bbox로 채워야 함).
        """
        if not table_bboxes:
            return []

        page_input = {
            "width": image.width,
            "height": image.height,
            "image": np.asarray(image.convert("RGB")),
        }
        do_matching = tokens is not None
        # predict_dummy(do_matching=False) 경로도 iocr_page["tokens"]를 무조건 읽으므로 항상 채워둔다
        page_input["tokens"] = tokens if do_matching else []

        # multi_table_predict가 bbox 리스트를 in-place로 스케일링하므로 복사본을 넘긴다
        bboxes = [list(b) for b in table_bboxes]
        outputs = self._predictor.multi_table_predict(
            page_input, bboxes, do_matching=do_matching
        )

        results = []
        for table_out in outputs:
            details = table_out.get("predict_details", {})
            results.append(
                {
                    "num_rows": details.get("num_rows", 0),
                    "num_cols": details.get("num_cols", 0),
                    "otsl_seq": details.get("prediction", {}).get("rs_seq", []),
                    "cells": table_out.get("tf_responses", []),
                }
            )
        return results

    def predict_batch(
        self,
        images: List[Image.Image],
        tables: List[List[List[float]]],
        tokens: Optional[List[Optional[List[dict]]]] = None,
    ) -> List[List[dict]]:
        toks = tokens or [None] * len(images)
        return [
            self.predict(image, bboxes, tok)
            for image, bboxes, tok in zip(images, tables, toks)
        ]
