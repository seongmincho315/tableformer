"""컨테이너 안에서 실행하는 in-process 추론 스모크 테스트.
합성 표 이미지(격자 + 셀 텍스트)를 만들어 Predictor로 직접 추론하고,
장비(device)/구조 예측 결과를 JSON으로 저장한다.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.environ.get("APP_DIR", "/app"))

from PIL import Image, ImageDraw  # noqa: E402

from app.predictor import Predictor  # noqa: E402


def _make_sample_table_page() -> Image.Image:
    img = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(img)
    # 2행 x 2열 표 하나
    table_box = (40, 40, 400, 200)
    x0, y0, x1, y1 = table_box
    mid_x = (x0 + x1) // 2
    mid_y = (y0 + y1) // 2
    draw.rectangle(table_box, outline="black")
    draw.line([(mid_x, y0), (mid_x, y1)], fill="black")
    draw.line([(x0, mid_y), (x1, mid_y)], fill="black")
    draw.text((x0 + 10, y0 + 10), "Name", fill="black")
    draw.text((mid_x + 10, y0 + 10), "Score", fill="black")
    draw.text((x0 + 10, mid_y + 10), "Alice", fill="black")
    draw.text((mid_x + 10, mid_y + 10), "90", fill="black")
    return img, [list(table_box)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    mode = os.environ.get("MODE", "accurate")
    device = os.environ.get("DEVICE", "cpu")
    num_threads = int(os.environ.get("NUM_THREADS", "4"))

    predictor = Predictor(mode=mode, device=device, num_threads=num_threads)
    image, table_bboxes = _make_sample_table_page()
    tables = predictor.predict(image, table_bboxes)

    result = {
        "mode": mode,
        "device": device,
        "num_tables": len(tables),
        "tables": tables,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[smoke] mode={mode} device={device} tables={len(tables)}")


if __name__ == "__main__":
    main()
