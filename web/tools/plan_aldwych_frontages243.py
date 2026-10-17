"""Extract candidate opening rectangles from the two published existing elevations.

Source vectors are kept distinct from native geometry. Nested panes and stone
surrounds require visual classification before any window or wall replacement.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

import pdfplumber
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/stage243"
SOURCES = {
    "CON": (
        "con_existing_elevation.pdf",
        [228, 90, 571, 475],
        "f49c9ee992fcf28615002474d79733c0035ef29e9021a1e130d96c10e96222f6",
    ),
    "COL": (
        "col_existing_elevation.pdf",
        [270, 90, 573, 446],
        "cd369000f7053523e3fd2bbc1a0b343c72ca5f61d96d0c66e9b29f5d0eb1d47f",
    ),
}


def covers(segments, start, end):
    position = start
    for lo, hi in sorted(segments):
        if hi < position - 0.03:
            continue
        if lo > position + 0.03:
            return False
        position = max(position, hi)
        if position >= end - 0.03:
            return True
    return False


def rectangles(page, bounds):
    segments = [
        (line["x0"], line["top"], line["x1"], line["bottom"]) for line in page.lines
    ]
    for curve in page.curves:
        segments.extend((*a, *b) for a, b in zip(curve["pts"], curve["pts"][1:]))
    horizontal = {}
    vertical = {}
    for x0, y0, x1, y1 in segments:
        if abs(y0 - y1) < 0.02:
            horizontal.setdefault(round((y0 + y1) / 2, 2), []).append(sorted([x0, x1]))
        if abs(x0 - x1) < 0.02:
            vertical.setdefault(round((x0 + x1) / 2, 2), []).append(sorted([y0, y1]))

    def edge(table, key, lo, hi):
        values = [s for k, rows in table.items() if abs(k - key) < 0.03 for s in rows]
        return covers(values, lo, hi)

    found = {}
    candidates = []
    for index, curve in enumerate(page.curves):
        pts = curve["pts"]
        xs = sorted({round(p[0], 2) for p in pts})
        ys = sorted({round(p[1], 2) for p in pts})
        if len(xs) == len(ys) == 2:
            candidates.append((index, xs, ys, "polyline"))
    # AutoCAD often splits the four sides over independent line entities.
    by_height = {}
    for x0, y0, x1, y1 in segments:
        if abs(x0 - x1) < 0.02 and 6 <= abs(y1 - y0) <= 50:
            key = tuple(round(y, 2) for y in sorted([y0, y1]))
            by_height.setdefault(key, set()).add(round((x0 + x1) / 2, 2))
    for ys, positions in by_height.items():
        xs = sorted(positions)
        for i, left in enumerate(xs):
            for right in xs[i + 1 :]:
                if 3 <= right - left <= 43:
                    candidates.append((None, [left, right], ys, "independent-lines"))
    for index, xs, ys, representation in candidates:
        x0, x1 = xs
        y0, y1 = ys
        width = x1 - x0
        height = y1 - y0
        if not (
            bounds[0] <= x0 < x1 <= bounds[2]
            and bounds[1] <= y0 < y1 <= bounds[3]
            and 3 <= width <= 43
            and 6 <= height <= 50
        ):
            continue
        if not (
            all(edge(horizontal, y, x0, x1) for y in [y0, y1])
            and all(edge(vertical, x, y0, y1) for x in [x0, x1])
        ):
            continue
        key = (x0, y0, x1, y1)
        found[key] = {
            "sourceCurve": index,
            "bounds": list(key),
            "widthMAtPrintedScale": width * 25.4 / 72 / 1000 * 250,
            "heightMAtPrintedScale": height * 25.4 / 72 / 1000 * 250,
            "sourceRepresentation": representation,
        }
    return sorted(found.values(), key=lambda r: (r["bounds"][1], r["bounds"][0]))


def main():
    result = {}
    for code, (filename, bounds, expected) in SOURCES.items():
        path = ROOT / "data/collections/aldwych-boundary243" / filename
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        with pdfplumber.open(path) as doc:
            page = doc.pages[0]
            rows = rectangles(page, bounds)
            result[code] = {
                "source": str(path.relative_to(ROOT)),
                "sourceSha256": expected,
                "sourceApplication": "20/04703/FULL",
                "published": "2020-08-28",
                "printedScale": "1:250 at A4",
                "paperSizePoints": [page.width, page.height],
                "candidateRectangles": rows,
                "status": "unclassified-source-rectangles-not-native-openings",
                "limits": "Nested panes, door leaves and stone surrounds may share bounds; visual classification and native-frontage registration remain required.",
            }
            outer = [
                a
                for a in rows
                if not any(
                    b is not a
                    and b["bounds"][0] <= a["bounds"][0] + 0.02
                    and b["bounds"][1] <= a["bounds"][1] + 0.02
                    and b["bounds"][2] >= a["bounds"][2] - 0.02
                    and b["bounds"][3] >= a["bounds"][3] - 0.02
                    and sum(abs(x - y) for x, y in zip(a["bounds"], b["bounds"])) > 0.1
                    for b in rows
                )
            ]
            result[code]["candidateOuterRectangles"] = outer
            scale = 2400 / page.width
            image = Image.open(
                OUT / (code.lower() + "-existing-elevation.png")
            ).convert("RGB")
            draw = ImageDraw.Draw(image)
            for row in outer:
                x0, y0, x1, y1 = [v * scale for v in row["bounds"]]
                draw.rectangle((x0, y0, x1, y1), outline="#cf4e43", width=2)
            image.save(OUT / (code.lower() + "-opening-candidates.png"))
            print(
                "SOURCE_OPENING_CANDIDATES",
                code,
                len(rows),
                Counter(round((r["bounds"][1] + r["bounds"][3]) / 2) for r in rows),
                flush=True,
            )
    (OUT / "frontage-source-candidates.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
