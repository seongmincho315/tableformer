# 표 구조 인식(TableFormer) 서빙

레거시 `doc_parser`는 TableFormer(`docling_ibm_models.tableformer`)를 docling 파이프라인
프로세스 안에 인라인으로 돌렸지만, 이 프로젝트는 detr(레이아웃)/paddle-ocr(OCR)과 동일하게
모델 하나당 독립 FastAPI 파드로 분리하는 걸 원칙으로 한다 — preprocessor는 얇은 HTTP 클라이언트만
가진다.

## 구조

- `docling-ibm-models==3.10.3` (레거시 doc_parser에서 검증된 버전으로 고정, floating 버전(예: detr의
  `>=3.0`)을 쓰면 tm_config.json/safetensors가 특정 모델 코드 버전에 묶여 있어 깨질 위험이 있음)
- 모델 가중치는 `ds4sd/docling-models`(HF) 레포의 `model_artifacts/tableformer/{fast,accurate}/`
  — 레이아웃/기타 모델도 같이 묶여 있는 레포라 `allow_patterns`로 필요한 mode만 받음.
- API는 detr(`/detect`)와 대칭되는 `/structure`: 페이지 이미지 + 테이블 bbox(레이아웃 모델이
  감지한 영역) → 행/열 구조 + 셀(bbox/병합/헤더). `tokens`를 같이 주면 PDF/OCR 텍스트를 셀에
  매칭(do_matching=True), 생략하면 구조만 예측(do_matching=False).

## TODO
- fast api로 테스트 (로컬 CPU 검증 필요 — 아직 안 함)
- Genos에서 사용 가능하게 스크립트 작성 (detr 구조 이식 완료, 실제 GPU 노드 빌드/smoke_test는 미검증)
- `my_preprocessor/preprocessor`의 `facade/resource/tableformer.yaml` + `facade/util/tableformer_client.py`
  로 배선 (detr_layout.py/paddle_ocr.py와 동일 패턴) — 아직 preprocessor 쪽엔 안 만듦
