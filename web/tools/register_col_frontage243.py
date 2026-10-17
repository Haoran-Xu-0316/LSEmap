"""Diagnose COL frontage orientation without modifying native geometry.

Uses archived ENU footprints and historical 2D sources. No Blender import,
parcel edits, or normalization are performed. Run main() with fixed paths.
"""

import hashlib
import json
import math
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/col-frontage243"
SITE = ROOT / "result/blender/site_geometry.json"
PDF = ROOT / "data/collections/aldwych-boundary243/con_site_plan.pdf"
SCALE = 250 * 0.0254 / 72


def diagnostic():
    site = json.loads(SITE.read_text())
    buildings = {
        b["code"]: b for b in site["buildings"] if b.get("code") in ("COL", "CON")
    }
    ring = buildings["COL"]["rings"][0]
    south, north = ring[12], ring[13]
    length = math.dist(south, north)
    axis = [(north[i] - south[i]) / length for i in range(2)]
    printed = (569.12 - 273.32) * SCALE
    drop = (445.84 - 441.16) * SCALE
    con = json.loads(
        (ROOT / "result/blender/con-frontage243/geometry-plan.json").read_text()
    )
    con_reg = json.loads(
        (
            ROOT / "result/blender/con-frontage243/native-registration-diagnostic.json"
        ).read_text()
    )
    segments = []
    for index, name in [
        (10, "Aldwych main frontage"),
        (11, "Garrick corner chamfer"),
        (12, "Houghton main frontage"),
        (13, "north turn to New Inn Passage"),
    ]:
        a, b = ring[index], ring[(index + 1) % len(ring)]
        segments.append(
            {
                "index": index,
                "role": name,
                "start": a,
                "end": b,
                "lengthM": math.dist(a, b),
            }
        )
    return (
        site,
        buildings,
        {
            "status": "read-only diagnostic; orientation identified, metric/vertical registration not accepted",
            "nativeChanged": False,
            "sources": {
                "nativeFootprint": str(SITE.relative_to(ROOT)),
                "nativeFootprintSha256": hashlib.sha256(SITE.read_bytes()).hexdigest(),
                "nativeCoordinateSystem": site["coordinate_system"],
                "nativeVerticalDatum": site["vertical_datum"],
                "locationPlan": str(PDF.relative_to(ROOT)),
                "locationPlanSha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
                "locationPlanPageSizePt": [842, 595],
                "colElevationReview": "result/blender/col-frontage243/col-frontage243-review.json",
                "authoringEvidence": [
                    "web/tools/refine_col_exterior175.py:FRAME_POINTS",
                    "web/tools/refine_col_envelope.py:frames",
                ],
                "sourceEpoch": "2020 historical application drawings; not a current2026 survey",
            },
            "segments": segments,
            "houghtonRegistration": {
                "buildingId": buildings["COL"]["id"],
                "ringIndex": 0,
                "segmentIndex": 12,
                "nativeOrder": "south to north",
                "southVertexIndex": 12,
                "northVertexIndex": 13,
                "southEndpointENU": south,
                "northEndpointENU": north,
                "nativeLengthM": length,
                "nativeUnitAxisSouthToNorth": axis,
                "outwardUnitNormal": [-axis[1], axis[0]],
                "northBearingDeg": math.degrees(math.atan2(axis[0], axis[1])) % 360,
                "elevationLeft": "north endpoint / vertex13",
                "elevationRight": "south endpoint / vertex12",
                "sourceXLeftPt": 273.32,
                "sourceXRightPt": 569.12,
                "mappingDirection": "source x increases north-to-south, opposite to native segment12",
                "confidence": "high for side/topology from ENU street and historical location plan; endpoint coordinates exact only within archived footprint",
            },
            "lengthComparison": {
                "sourcePrintedScaleLengthM": printed,
                "nativeLengthM": length,
                "sourceMinusNativeM": printed - length,
                "differenceAsPercentOfSource": 100 * (printed - length) / printed,
                "compressionIfBothEndpointsForced": length / printed,
                "centredUnscaledOverhangEachEndM": (printed - length) / 2,
                "mainPlusSouthChamferM": length + math.dist(ring[11], ring[12]),
                "decision": "Do not silently compress or borrow the Garrick chamfer. Keep the0.134m discrepancy visible until a registration tolerance or survey is established.",
            },
            "locationPlanUse": {
                "role": "topological check of CON west of Houghton and COL east of Houghton, plus COL main edge and Garrick corner",
                "coordinateOrigin": "PDF top-left, y down",
                "colRedStrokeIndices": list(range(5243, 5255)),
                "approximateColMainRedMidlinePt": [[387.8, 301.12], [390.68, 325.18]],
                "approximateConMainRedMidlinePt": [[376.04, 298.48], [379.1, 326.5]],
                "boundaryStatus": "red application boundary/outline, not surveyed ownership or facade dimensions",
                "printedScaleText": "Scale :1/30 at A4",
                "scaleStatus": "not used metrically; printed ratio is inconsistent with the depicted multi-block extent",
                "existingBoundaryTransform": "stage243 boundary-registration-diagnostic.json belongs to a different2025 site_plan.pdf and is not transferred to this PDF",
                "northOrientation": "native plan north is +Y; historical plan topology agrees. No surveyed bearing is recovered from its red strokes.",
            },
            "streetGrades": {
                "COL": {
                    "sourceGroundlinePt": [[273.32, 441.16], [569.12, 445.84]],
                    "orientation": "left=north, right=south",
                    "northAboveSouthM": drop,
                    "nominalAlongFrontageRiseTowardNorth": drop / printed,
                    "nominalPercent": 100 * drop / printed,
                    "lowerOpeningDatumAodM": 18.07,
                    "lowerOpeningDatumYpt": 438.52,
                    "warning": "18.07 is an opening-bottom datum. Native world Z has no established AOD offset.",
                },
                "CON": {
                    "sourceGroundlinePt": con["groundline"],
                    "orientation": "left=south, right=north",
                    "northAboveSouthM": con["groundRiseM"],
                    "nominalAlongFrontageRiseTowardNorth": con["groundRiseM"]
                    / con["sourceWidthM"],
                    "nominalPercent": 100 * con["groundRiseM"] / con["sourceWidthM"],
                    "sourceFrontageLengthM": con["sourceWidthM"],
                    "nativeFrontageLengthM": con_reg["nativeFrontageLengthM"],
                },
                "nativeState": "relative flat ground; no surveyed road profile or common AOD anchor in site_geometry.json",
                "coordinationFinding": "Geographic slope signs agree: both sides rise northward. Their nominal gradients differ, so a single constant street grade is not established. Local curvature, crossfall, drawing simplification and endpoint scope remain possible.",
                "acceptedSharedGrade": False,
                "requiredEvidence": [
                    "A common surveyed road/threshold datum tied to native Z.",
                    "Actual frontage endpoint and street centreline elevations.",
                    "A decision on source-to-footprint length discrepancies before geometry replacement.",
                ],
            },
            "constraints": [
                "Keep all archived COL and CON parcel vertices unchanged.",
                "Restrict the straight COL elevation to segment12; segment11 and segment13 are separate returns.",
                "Do not mirror COL by copying the CON source-x direction.",
                "Do not infer ownership transfer from red outlines or the separate61A boundary diagnostic.",
                "Retain source-scale widths and ground slopes as diagnostics until horizontal and vertical registration is accepted.",
            ],
        },
    )


def plan_image(site, buildings, review):
    canvas = Image.new("RGB", (2100, 1740), "#f7f6f2")
    d = ImageDraw.Draw(canvas)
    path = "/System/Library/Fonts/Supplemental/Arial.ttf"

    def font(s):
        return ImageFont.truetype(path, s)

    def point(p):
        return (60 + (p[0] + 40) * 14, 1070 - (p[1] + 144) * 14)

    d.text(
        (35, 23),
        "COL frontage: side, endpoints and street-grade diagnostic",
        font=font(39),
        fill="#17232a",
    )
    d.text(
        (35, 80),
        "Native ENU plan: X east, Y north. Archived footprints retained. Historical source geometry is not accepted registration.",
        font=font(24),
        fill="#4c5960",
    )
    d.rectangle((30, 135, 1120, 1130), fill="white", outline="#bac1c2", width=2)
    for b in site["buildings"]:
        pts = b["rings"][0]
        if (
            not pts
            or min(p[0] for p in pts) < -41
            or max(p[0] for p in pts) > 35
            or min(p[1] for p in pts) < -145
            or max(p[1] for p in pts) > -86
        ):
            continue
        d.polygon([point(p) for p in pts], fill="#dde2e1", outline="#9ca7aa", width=2)
    for code, fill in [("CON", "#dcd8cb"), ("COL", "#d6e3eb")]:
        b = buildings[code]
        d.polygon(
            [point(p) for p in b["rings"][0]], fill=fill, outline="#334650", width=3
        )
        d.text(point(b["center"]), code, font=font(30), fill="#17232a")
    for road in site["roads"]:
        if road.get("properties", {}).get("name") == "Houghton Street":
            pts = road["geometry"]["coordinates"]
            d.line(
                [point(p) for p in pts if -145 < p[1] < -89], fill="#a3b4a3", width=4
            )
    d.text(
        (point((-0.7, -111))[0] - 13, point((0, -111))[1] - 43),
        "Houghton",
        font=font(20),
        fill="#53665b",
    )
    ring = buildings["COL"]["rings"][0]
    for index, color, width in [
        (10, "#8d969d", 5),
        (11, "#cf8d3d", 8),
        (12, "#1d65ad", 9),
        (13, "#8c5ca5", 7),
    ]:
        a, b = ring[index], ring[(index + 1) % len(ring)]
        d.line([point(a), point(b)], fill=color, width=width)
    for idx, tag, offset in [
        (13, "N / vertex13", (-24, -50)),
        (12, "S / vertex12", (3, 20)),
        (11, "vertex11", (20, 10)),
        (0, "vertex0", (22, -10)),
    ]:
        x, y = point(ring[idx])
        d.ellipse((x - 7, y - 7, x + 7, y + 7), fill="#1d65ad")
        d.text((x + offset[0], y + offset[1]), tag, font=font(20), fill="#194e7b")
    for a, b in zip([1, 2], [2, 3]):
        d.line(
            [
                point(buildings["CON"]["rings"][0][a]),
                point(buildings["CON"]["rings"][0][b]),
            ],
            fill="#9b5252",
            width=5,
        )
    for x, y0, y1 in [(1, -102, -123), (-12, -102, -123)]:
        a = point((x, y0))
        b = point((x, y1))
        d.line([a, b], fill="#a72c38", width=4)
        d.polygon([b, (b[0] - 8, b[1] - 15), (b[0] + 8, b[1] - 15)], fill="#a72c38")
    d.text(
        (70, 1015),
        "Red arrows: geographic downhill is south on both historical elevations.",
        font=font(23),
        fill="#a72c38",
    )
    d.text(
        (70, 1060),
        "Blue: COL segment12. Orange: Garrick chamfer11. Purple: north return13.",
        font=font(23),
        fill="#354e5c",
    )
    d.line([(1055, 280), (1055, 185)], fill="#17232a", width=4)
    d.polygon([(1055, 179), (1044, 201), (1066, 201)], fill="#17232a")
    d.text((1044, 144), "N", font=font(27), fill="#17232a")
    d.line([(90, 1175), (230, 1175)], fill="#17232a", width=4)
    d.text((90, 1190), "10m", font=font(22), fill="#17232a")
    d.text(
        (300, 1175),
        "Metric drawing uses archived ENU coordinates; no parcel changes.",
        font=font(23),
        fill="#4c5960",
    )
    x = 1170
    y = 140
    paras = [
        ("Exact archived endpoints", "#17232a", 30),
        (
            "Segment12: S(5.831283,-125.399003) to N(3.464042,-99.553750)m. Native length25.953438m. Outward face points west.",
            "#1d65ad",
            26,
        ),
        (
            "Elevation LEFT=NORTH; RIGHT=SOUTH. Source x runs opposite to the native segment12 order.",
            "#1d65ad",
            27,
        ),
        ("Width discrepancy stays explicit", "#17232a", 30),
        (
            "Printed-scale frontage26.087917m is0.134479m longer than the native straight edge, a0.5155% difference. No compression is applied.",
            "#4c5960",
            26,
        ),
        (
            "Adding the2.883573m Garrick chamfer produces28.837010m and changes frontage scope. Do not borrow it.",
            "#4c5960",
            26,
        ),
        ("Grades agree in direction, not calibration", "#17232a", 30),
        (
            "COL rises0.412750m toward north, nominal1.5822%. CON rises0.635000m toward north, nominal2.1368%. Native street ground remains flat.",
            "#a72c38",
            26,
        ),
        (
            "No common AOD-to-native-Z anchor or surveyed crossfall exists here.18.07 remains COL opening-bottom datum. A shared street grade is unaccepted.",
            "#a72c38",
            26,
        ),
    ]
    for msg, color, size in paras:
        for line in textwrap.wrap(msg, width=53 if size < 29 else 45):
            d.text((x, y), line, font=font(size), fill=color)
            y += size + 8
        y += 20
    assert y < 1090, y
    crop = Image.open(OUT / "location-plan-crop.png").convert("RGB").resize((800, 600))
    canvas.paste(crop, (1170, 1120))
    # Keep this source inset separate from the metric ENU plan above.
    d.rectangle((1168, 1118, 1972, 1722), outline="#889598", width=2)
    d.rectangle((1170, 1120, 1970, 1195), fill="#f7f6f2")
    d.text(
        (1180, 1130),
        "2020 location-plan crop: topology only",
        font=font(27),
        fill="#17232a",
    )
    d.text(
        (1180, 1166),
        "Red outline is not surveyed ownership; printed1/30 unused.",
        font=font(20),
        fill="#4c5960",
    )
    d.text(
        (60, 1290),
        "Source image positions agree: CON west of Houghton; COL east.",
        font=font(25),
        fill="#17232a",
    )
    d.text(
        (60, 1330),
        "COL north turn joins New Inn Passage; south chamfer joins Aldwych.",
        font=font(25),
        fill="#17232a",
    )
    d.text(
        (60, 1400),
        "Native plan coordinates identify the retained edge exactly.",
        font=font(24),
        fill="#4c5960",
    )
    d.text(
        (60, 1440),
        "They do not establish survey accuracy or current2026 condition.",
        font=font(24),
        fill="#4c5960",
    )
    canvas.save(OUT / "col-native-registration-plan.png")


def main():
    site, buildings, review = diagnostic()
    (OUT / "col-native-registration-diagnostic.json").write_text(
        json.dumps(review, indent=2) + "\n"
    )
    subprocess.run(
        [
            "pdftoppm",
            "-r",
            "600",
            "-x",
            "2833",
            "-y",
            "2400",
            "-W",
            "800",
            "-H",
            "600",
            "-png",
            "-singlefile",
            str(PDF),
            str(OUT / "location-plan-crop"),
        ],
        check=True,
    )
    plan_image(site, buildings, review)
    (OUT / "location-plan-crop.png").unlink()
    print("COL native frontage diagnostic complete:", review["lengthComparison"])


if __name__ == "__main__":
    main()
