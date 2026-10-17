"""Review the historical COL elevation without changing model or web assets.

Coordinates are PDF points measured from the page's top-left. The review
classifies visible frontage modules; it does not infer a current survey.
"""

import hashlib
import json
import textwrap
from collections import defaultdict
from itertools import pairwise
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/collections/aldwych-boundary243/col_existing_elevation.pdf"
CANDIDATES = ROOT / "result/blender/stage243/frontage-source-candidates.json"
RENDER = ROOT / "result/blender/stage243/col-existing-elevation.png"
OUTPUT = ROOT / "result/blender/col-frontage243"
EXPECTED_SHA = "cd369000f7053523e3fd2bbc1a0b343c72ca5f61d96d0c66e9b29f5d0eb1d47f"
METRES_PER_POINT = 250 * 0.0254 / 72


def review_data():
    sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert sha == EXPECTED_SHA, "Source changed: re-review required."
    raw = json.loads(CANDIDATES.read_text())["COL"]
    grouped = defaultdict(list)
    for candidate in raw["candidateOuterRectangles"]:
        bounds = candidate["bounds"]
        grouped[tuple(bounds[1::2])].append(bounds)
    ranges = [
        (109.12, 131.68),
        (145.0, 168.88),
        (186.76, 207.16),
        (219.76, 242.92),
        (256.12, 279.16),
        (292.48, 316.72),
        (328.0, 350.08),
        (367.96, 391.0),
        (405.28, 438.52),
    ]
    labels = [
        "upper roof-face windows",
        "lower roof-face windows",
        "main ribbons, upper row",
        "main ribbons, second row",
        "main ribbons, third row",
        "main ribbons, lower row",
        "separate intermediate row",
        "lower block, upper windows",
        "ground frontage: panels and entrance",
    ]
    rows = []
    for number, ((top, bottom), label) in enumerate(zip(ranges, labels), 1):
        bounds = sorted(grouped[(top, bottom)])
        if number == 5:
            # The candidate finder lost the left pane because the drawn edge
            # drifts from x295.04 to x294.92. Preserve the complete visible frame.
            bounds[0][0] = 294.92
        if number == 9:
            bounds.insert(1, [328.76, 405.28, 348.56, 442.24])
        assert len(bounds) == 8
        rows.append(
            {
                "id": f"R{number}",
                "description": label,
                "nominalYRangePt": [top, bottom],
                "moduleCount": 8,
                "moduleBoundsPt": bounds,
                "classification": "regular window modules"
                if number < 9
                else "7 louvred/panel modules plus1 entrance",
                "confidence": "high for drawn bounds and module grouping; material inference excluded",
            }
        )
    main_centres = [round((b[0] + b[2]) / 2, 3) for b in rows[2]["moduleBoundsPt"]]
    roof_centres = [round((b[0] + b[2]) / 2, 3) for b in rows[0]["moduleBoundsPt"]]
    ground = [[273.32, 441.16], [569.12, 445.84]]
    return {
        "building": "COL / Columbia House",
        "reviewStatus": "historical 2D source classification; not current2026 verification or native model acceptance",
        "source": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": sha,
            "application": raw["sourceApplication"],
            "published": raw["published"],
            "title": "Houghton Street Elevation / Columbia House",
            "page": 1,
            "paperSizePt": [842, 595],
            "printedScale": "1:250 at A4",
        },
        "coordinateSystem": {
            "unit": "PDF point",
            "origin": "page top-left",
            "x": "right positive",
            "y": "down positive",
            "metresPerPointAtPrintedScale": METRES_PER_POINT,
            "metricStatus": "nominal scale-derived dimensions, not surveyed dimensions",
        },
        "counts": {
            "regularWindowRows": 8,
            "regularWindowModules": 64,
            "groundModules": 8,
            "groundEntranceModules": 1,
            "groundLouvredOrPanelModules": 7,
            "totalFrontageModules": 72,
            "warning": "Do not call72 a window count; pane rectangles and spandrels are not openings.",
        },
        "rows": rows,
        "horizontalStructure": {
            "bayCount": 8,
            "numbering": "left to right in source",
            "mainBayCentresPt": main_centres,
            "roofBayCentresPt": roof_centres,
            "mainBayPitchPt": [round(b - a, 3) for a, b in pairwise(main_centres)],
            "facadeEdgesPt": [273.32, 569.12],
            "facadeWidthMAtPrintedScale": round(
                (569.12 - 273.32) * METRES_PER_POINT, 3
            ),
            "notes": [
                "Main rows use3 vertical lights per bay; roof rows use2, with different transom patterns.",
                "Roof and main axes differ slightly; retain measured row bounds rather than enforcing one perfect grid.",
                "R3-R6 are separated by opaque-looking spandrel bands inside continuous vertical ribbons; these bands are not additional window rows.",
                "R8-R9 share vertical framing in most bays; bay2 contains the lower entrance.",
            ],
        },
        "roofProfile": {
            "confidence": "high for source silhouette; 3D interpretation remains estimated",
            "outerPolylinePt": [
                [278.96, 162.76],
                [290.24, 96.76],
                [558.92, 96.76],
                [563.96, 140.32],
            ],
            "parallelCapLinePt": [[289.76, 99.04], [559.16, 99.04]],
            "roofTopDatum": {"yPt": 96.76, "printedAodM": 48.21},
            "rooftopRectangularProjectionPt": [
                [447.2, 96.76],
                [447.2, 52.12],
                [482.96, 52.12],
                [482.96, 96.76],
            ],
            "rightUpstand": {
                "upperLeftPt": [548.72, 140.32],
                "rightEdgeXPt": 569.12,
                "description": "drawn right-side upstand/return, function not identified",
            },
            "interpretation": "Two rows on a steep sloping-sided roof-face projection. Do not invent dormer boxes, rear roof, roof depth, chimney function or roof pitch from this view alone.",
        },
        "horizontalBandsYpt": {
            "roofFaceBase": 162.76,
            "upperCorniceLines": [171.28, 178.24],
            "lowerMainCorniceLines": [316.72, 322.36],
            "lowerBlockBandLines": [350.08, 355.72],
        },
        "groundline": {
            "polylinePt": ground,
            "classification": "drawn sloping base/groundline in source, not surveyed terrain",
            "confidence": "high for drawn line; real-world ground interpretation unverified",
            "dropRightMAtPrintedScale": round(4.68 * METRES_PER_POINT, 3),
            "lowerOpeningDatum": {"yPt": 438.52, "printedAodM": 18.07},
            "gapBelowOpeningDatumPt": [2.64, 7.32],
            "warning": "18.07 labels lower panel/opening bottoms at y438.52. It is not a flat ground datum. Do not snap the facade base to it.",
        },
        "printedLevelInterpretation": {
            "status": "visually transcribed from source; opening-edge levels, not floor slab or terrain levels",
            "levels": [
                {"aodM": 48.21, "yPt": 96.76, "role": "main roof top"},
                {
                    "aodM": 46.96,
                    "yPt": 111.04,
                    "role": "R1 inner window head; outer surround starts109.12",
                },
                {
                    "aodM": 43.80,
                    "yPt": 146.8,
                    "role": "R2 inner window head; outer surround starts145.0",
                },
                {"aodM": 42.30, "yPt": 168.88, "role": "R2 sill"},
                {"aodM": 40.28, "yPt": 186.76, "role": "R3 head"},
                {"aodM": 38.48, "yPt": 207.16, "role": "R3 sill"},
                {"aodM": 37.37, "yPt": 219.76, "role": "R4 head"},
                {"aodM": 35.33, "yPt": 242.92, "role": "R4 sill"},
                {"aodM": 34.16, "yPt": 256.12, "role": "R5 head"},
                {"aodM": 32.13, "yPt": 279.16, "role": "R5 sill"},
                {"aodM": 30.95, "yPt": 292.48, "role": "R6 head"},
                {"aodM": 28.82, "yPt": 316.72, "role": "R6 sill"},
                {"aodM": 27.82, "yPt": 328.0, "role": "R7 head"},
                {"aodM": 25.87, "yPt": 350.08, "role": "R7 sill"},
                {"aodM": 24.30, "yPt": 367.96, "role": "R8 head"},
                {"aodM": 22.27, "yPt": 391.0, "role": "R8 sill"},
                {"aodM": 21.01, "yPt": 405.28, "role": "ground module head"},
                {
                    "aodM": 18.07,
                    "yPt": 438.52,
                    "role": "ground panel bottoms; not ground",
                },
            ],
        },
        "groundEntrance": {
            "bay": 2,
            "fullModuleBoundsPt": [328.76, 405.28, 348.56, 442.24],
            "upperPanelBoundsPt": [328.76, 405.28, 348.56, 417.76],
            "doorBoundsPt": [328.76, 417.76, 348.56, 442.24],
            "confidence": "high for two-leaf gridded entrance depiction; operation and glazing/material unknown",
        },
        "candidateCorrections": [
            "Discard spandrel and nested-pane rectangles as extra openings.",
            "R5 bay1 bounds restored to x294.92..315.20, y256.12..279.16 after visual/vector review.",
            "Ground bay2 is one entrance assembly, not its6 lower leaf panes plus top panel as separate openings.",
        ],
        "nextModelConstraints": [
            "Register source x to the existing COL Houghton Street frontage only after checking frontage orientation and endpoints.",
            "Use the source groundline for relative vertical placement; any native-world height or horizontal scaling remains a separate registration assumption.",
            "Keep8 bays and row-specific bounds; preserve64 regular windows plus7 ambiguous ground panels and1 entrance.",
            "Use opaque material for spandrel zones; do not turn candidate rectangles into transparency by default.",
            "Preserve the two roof-window rows and roof silhouette; depth, setback, wall thickness and rear roof require other sources.",
            "Do not present this2020 drawing as a current2026 survey. No native model, export, website or deployment was changed.",
        ],
        "unresolved": [
            "Current alterations since2020.",
            "Ground-panel material and exact louvre construction.",
            "Building depth, true roof slope/setbacks, roof projection function and side/rear elevations.",
            "Registration to native frontage and current terrain.",
        ],
    }


def annotated_image(review):
    source = Image.open(RENDER).convert("RGB")
    crop = [255, 42, 590, 456]
    factor = 3.7
    sx, sy = source.width / 842, source.height / 595
    source = source.crop(
        tuple(round(v * (sx if i % 2 == 0 else sy)) for i, v in enumerate(crop))
    )
    source = source.resize(
        (round((crop[2] - crop[0]) * factor), round((crop[3] - crop[1]) * factor))
    )
    canvas = Image.new("RGB", (2200, 1770), "#f7f6f2")
    canvas.paste(source, (35, 150))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"

    def font(size):
        return ImageFont.truetype(font_path, size)

    def point(pt):
        return (35 + (pt[0] - crop[0]) * factor, 150 + (pt[1] - crop[1]) * factor)

    draw.text(
        (35, 28),
        "COL / Columbia House: historical frontage classification",
        font=font(39),
        fill="#171e26",
    )
    draw.text(
        (35, 81),
        "Westminster20/04703/FULL | published2020-08-28 |1:250 at A4 | PDF point coordinates",
        font=font(25),
        fill="#49535c",
    )
    blue = "#1f61ac"
    red = "#b02d35"
    green = "#258060"
    for row in review["rows"]:
        for bounds in row["moduleBoundsPt"]:
            draw.rectangle(
                (*point(bounds[:2]), *point(bounds[2:])), outline=blue, width=3
            )
        center = sum(row["nominalYRangePt"]) / 2
        draw.text((39, point((0, center))[1] - 14), row["id"], font=font(23), fill=blue)
    for key in ["outerPolylinePt", "rooftopRectangularProjectionPt"]:
        draw.line([point(p) for p in review["roofProfile"][key]], fill=green, width=5)
    ground = review["groundline"]["polylinePt"]
    draw.line([point(p) for p in ground], fill=red, width=7)
    for i, x in enumerate(review["horizontalStructure"]["mainBayCentresPt"], 1):
        draw.text(
            (point((x, 0))[0] - 7, point((0, 454))[1]), str(i), font=font(23), fill=blue
        )
    x = 1330
    y = 155
    entries = [
        ("Confirmed from the drawing", "#171e26", 30),
        (
            "8 bays,9 opening bands. R1-R8 contain64 regular window modules. R9 contains7 louvred/panel modules and1 entrance in bay2.",
            blue,
            27,
        ),
        (
            "R1 109.12-131.68pt; R2 145.00-168.88pt. Both roof rows have2 vertical lights per bay.",
            blue,
            25,
        ),
        (
            "R3-R6 186.76-316.72pt: four rows within8 continuous vertical ribbons. The gaps are spandrels.",
            blue,
            25,
        ),
        (
            "R7 328.00-350.08pt; R8 367.96-391.00pt. Main rows have3 vertical lights per bay.",
            blue,
            25,
        ),
        (
            "R9 405.28-438.52pt. Bay2 entrance extends to442.24pt. Panel material is unresolved.",
            blue,
            25,
        ),
        ("Roof silhouette", green, 30),
        (
            "Main top y96.76pt. Left shoulder(278.96,162.76); left top(290.24,96.76); right top(558.92,96.76); right shoulder(563.96,140.32).",
            green,
            25,
        ),
        (
            "Rectangular roof projection x447.20-482.96pt, top y52.12pt. Its function and depth are unknown.",
            green,
            25,
        ),
        ("Groundline: do not use18.07 as ground", red, 29),
        (
            "The red line is(273.32,441.16) to(569.12,445.84)pt. It slopes down to the right by0.413m at the printed scale.",
            red,
            25,
        ),
        (
            "18.07 is the printed opening-bottom datum at y438.52pt. The drawn groundline lies2.64-7.32pt below it.",
            red,
            25,
        ),
        ("Limits for next modeling", "#171e26", 30),
        (
            "Source-projected bounds are trustworthy. Metric dimensions are nominal scale conversions. Current2026 condition, true roof slope, depth, setbacks, wall thickness and native registration remain unresolved.",
            "#49535c",
            25,
        ),
        (
            "Source crop: x255-590pt,y42-456pt. Blue: opening modules. Green: roof. Red: drawn groundline. Full coordinates and constraints are in the review JSON.",
            "#49535c",
            23,
        ),
    ]
    for message, color, size in entries:
        for line in textwrap.wrap(message, width=54 if size < 28 else 46):
            draw.text((x, y), line, font=font(size), fill=color)
            y += size + 9
        y += 21
    assert y < 1720, y
    canvas.save(OUTPUT / "col-frontage243-annotated.png")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    review = review_data()
    (OUTPUT / "col-frontage243-review.json").write_text(
        json.dumps(review, indent=2) + "\n"
    )
    annotated_image(review)
    print("Created review JSON and annotated PNG under", OUTPUT)


if __name__ == "__main__":
    main()
