"""Diagnose Aldwych frontage registration against newly archived council vectors.

A signage application boundary and an upper-floor office perimeter are distinct
observations. This diagnostic never authorizes parcel transfer or native edits.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pdfplumber
from PIL import Image, ImageDraw
from shapely.geometry import Point, Polygon

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/stage243"
SOURCE = ROOT / "data/collections/aldwych-boundary243/site_plan.pdf"
SOURCE_SHA = "cd3c47d6ac56407fcfbbfe91e5bf28c9215027bb494048785f305ef5b3afd46d"
CONTROLS = [
    {
        "id": "KSW-south-street-party-wall",
        "pdf": [298.47, 230.39],
        "world": [-76.5901484669, -60.25681352],
    },
    {
        "id": "KSW-south-rear-party-wall",
        "pdf": [464.07, 155.6],
        "world": [-49.787304128, -48.986701019],
    },
    {
        "id": "CON-Houghton-north-wall-turn",
        "pdf": [685.74, 430.64],
        "world": [-8.962077131, -97.017058643],
    },
    {
        "id": "CON-Houghton-south-wall-turn",
        "pdf": [704.64, 598.31],
        "world": [-5.206503106, -125.488009895],
    },
    {
        "id": "CON-Aldwych-east-wall-turn",
        "pdf": [691.14, 611.0],
        "world": [-8.254048436, -128.881377614],
    },
]


def similarity(source, target):
    ac = source.mean(0)
    bc = target.mean(0)
    left, singular, right = np.linalg.svd((source - ac).T @ (target - bc))
    rotation = left @ right
    assert np.linalg.det(rotation) > 0.9999
    scale = singular.sum() / np.square(source - ac).sum()
    return scale, rotation, bc - scale * ac @ rotation


def main():
    OUT.mkdir(exist_ok=True)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    with pdfplumber.open(SOURCE) as doc:
        page = doc.pages[0]
        assert "The site boundary" in page.extract_text()
        red = [
            {"index": i, "points": c["pts"]}
            for i, c in enumerate(page.curves)
            if isinstance(c["stroking_color"], (list, tuple))
            and len(c["stroking_color"]) == 3
            and c["stroking_color"][0] > 0.9
            and max(c["stroking_color"][1:]) < 0.2
        ]
        assert [r["index"] for r in red] == list(range(306, 320))
        creation = doc.metadata["CreationDate"]
    # Midlines of the published finite-width red strokes, not claimed survey corners.
    red_points = [
        [527.835, 324.125],
        [584.13, 455.03],
        [613.11, 628.37],
        [559.65, 638.72],
        [464.34, 594.71],
        [430.68, 519.56],
        [373.35, 394.91],
    ]
    source = np.array([c["pdf"] for c in CONTROLS]) * [1, -1]
    target = np.array([c["world"] for c in CONTROLS])
    scale, rotation, translation = similarity(source, target)
    transform = lambda points: (
        scale * (np.array(points) * [1, -1]) @ rotation + translation
    )
    residuals = np.linalg.norm(transform([c["pdf"] for c in CONTROLS]) - target, axis=1)
    polygon = Polygon(transform(red_points))
    shared = Point(transform([[613.11, 628.37]])[0])
    historic = json.loads(
        (
            ROOT / "result/blender/61a-registration218/registration-hypothesis.json"
        ).read_text()
    )
    historic_tip = Point(historic["diagnostic"]["sourceFrontTipWorld"])
    result = {
        "source": str(SOURCE.relative_to(ROOT)),
        "sourceSha256": SOURCE_SHA,
        "drawing": "7341-WMA-XX-XX-DR-A-1002 P01",
        "creationDate": creation,
        "published": "2025-09-18",
        "transform": {
            "scale": float(scale),
            "rotation": rotation.tolist(),
            "translation": translation.tolist(),
        },
        "controls": [
            dict(c, residualM=float(residuals[i])) for i, c in enumerate(CONTROLS)
        ],
        "rmsResidualM": float(np.sqrt(np.mean(residuals**2))),
        "maximumControlResidualM": float(max(residuals)),
        "sourceRedStrokes": red,
        "redBoundaryWorld": list(polygon.exterior.coords),
        "sourceSharedFrontPointWorld": next(iter(shared.coords)),
        "historic2021TipWorld": next(iter(historic_tip.coords)),
        "twoSourceFrontPointDifferenceM": historic_tip.distance(shared),
        "legacyTipDistanceToMappedRoofParcelM": historic["diagnostic"][
            "frontTipDistanceToMappedBoundaryM"
        ],
        "status": "diagnostic-only-not-accepted-for-native-edit",
        "nativeChanged": False,
        "limits": [
            "The2025red line is the signage application site boundary,not a surveyed upper-floor ownership map.",
            "Candidate neighbouring wall correspondences mix ground projection and archivedOSMroof footprints;1.65m residual prevents a measured common-wall claim.",
            "The2021office underlay and2025application boundary cover different extents. Do not stretch either to force agreement.",
            "Existing elevation drawings contain visibility-limited upper openings. Survey/photograph dates and2026completion state are not established by the2025upload date.",
        ],
        "nextEvidenceGate": "Register the existing Kingsway and Aldwych elevation openings to the actual saved native frontage before replacing geometry; preserve both building footprints meanwhile.",
    }
    (OUT / "boundary-registration-diagnostic.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    site = json.loads((ROOT / "result/blender/site_geometry.json").read_text())
    image = Image.new("RGB", (1200, 1100), "#f7f6f2")
    draw = ImageDraw.Draw(image)

    def screen(points):
        return [(100 + (x + 85) * 11, 1000 - (y + 140) * 10) for x, y in points]

    for b in site["buildings"]:
        shape = Polygon(b["rings"][0])
        bounds = shape.bounds
        if bounds[0] < -90 or bounds[2] > 10 or bounds[1] < -145 or bounds[3] > -25:
            continue
        draw.polygon(
            screen(shape.exterior.coords),
            fill="#dce0dd" if b["id"] != "way/23613978" else "#e7d8c8",
            outline="#7f8889",
            width=2,
        )
    draw.line(screen(historic["sourceFloorFillBoundaryWorld"]), fill="#4b7d61", width=3)
    draw.line(screen(polygon.exterior.coords), fill="#b83f39", width=4)
    for c in CONTROLS:
        x, y = screen([c["world"]])[0]
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill="#294d77")
    draw.text(
        (35, 25),
        "61 Aldwych: independent source diagnostic, no native changes",
        fill="#26333a",
    )
    draw.text(
        (35, 49),
        "Red:2025 signage-site boundary. Green:2021 upper-office outline. Grey/tan:archived roof parcels.",
        fill="#49545a",
    )
    draw.text(
        (35, 73),
        f"Five candidate neighbouring controls; RMS{result['rmsResidualM']:.2f}m, max{max(residuals):.2f}m. Not a surveyed ownership fit.",
        fill="#49545a",
    )
    image.save(OUT / "boundary-source-comparison.png")
    print(
        "ALDWYCH243_BOUNDARY_DIAGNOSTIC",
        result["rmsResidualM"],
        result["maximumControlResidualM"],
        result["twoSourceFrontPointDifferenceM"],
        flush=True,
    )


if __name__ == "__main__":
    main()
