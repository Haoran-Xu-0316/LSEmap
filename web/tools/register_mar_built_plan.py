"""Register the published MAR third-floor outline against the retained site outline.

Read-only evidence workflow. Coordinates picked from the published plan are
approximate; a coarse footprint fit must not authorize high-wing mesh edits.
"""

from pathlib import Path
import hashlib
import json
import math
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/mar_built_plan_registration"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = (
    ROOT
    / "data/collections/mar-built-registration-2026/grafton-marshall-built-plans-2022.pdf"
)
# Verify the downloaded archive manifest rather than accepting an arbitrary PDF.
manifest = json.loads((SOURCE.parent / "sources.json").read_text())
source_sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
assert source_sha == manifest["sha256"]
site = json.loads((ROOT / "result/blender/site_geometry.json").read_text())
mar = next(b for b in site["buildings"] if b.get("code") == "MAR")
origin = np.array(mar["center"])
angle = math.radians(22)
u, n = np.array([math.cos(angle), math.sin(angle)]), np.array(
    [-math.sin(angle), math.cos(angle)]
)
ring = np.array(mar["rings"][0])
local = np.column_stack(((ring - origin) @ u, (ring - origin) @ n))
# Source PDF point units; the three orthogonal outer corners fit the transform.
# Two independently picked ends of the diagonal are held out for validation.
anchors = [
    {"role": "northwest", "pdf": [491.0, 377.4], "siteVertex": 13, "fit": True},
    {"role": "northeast", "pdf": [491.0, 554.7], "siteVertex": 0, "fit": True},
    {"role": "southeast", "pdf": [338.7, 554.7], "siteVertex": 2, "fit": True},
    {
        "role": "south_diagonal_end",
        "pdf": [338.7, 474.0],
        "siteVertex": 6,
        "fit": False,
    },
    {"role": "west_diagonal_end", "pdf": [434.0, 377.4], "siteVertex": 8, "fit": False},
]
source = np.array([[a["pdf"][0], -a["pdf"][1]] for a in anchors])
target = np.array([local[a["siteVertex"]] for a in anchors])
a, b = source[:3], target[:3]
ac, bc = a.mean(axis=0), b.mean(axis=0)
x, y = a - ac, b - bc
left, singular, right = np.linalg.svd(x.T @ y)
rotation = left @ right
assert np.linalg.det(rotation) > 0.999
scale = singular.sum() / np.square(x).sum()
translation = bc - scale * ac @ rotation
registered = scale * source @ rotation + translation
for i, anchor in enumerate(anchors):
    anchor["nativeLocal"] = target[i].tolist()
    anchor["registeredLocal"] = registered[i].tolist()
    anchor["residualMetres"] = float(np.linalg.norm(target[i] - registered[i]))
fit_residual = max(a["residualMetres"] for a in anchors if a["fit"])
validation_residual = max(a["residualMetres"] for a in anchors if not a["fit"])
# A match of outer corners is not a mapping of office-floor or blank-wall faces.
report = {
    "source": manifest,
    "sourceSha256": source_sha,
    "pdfPage": 1,
    "sourceCoordinates": "Approximate PDF point coordinates read from the published third-floor raster. Not vector survey picks.",
    "siteSource": mar["id"],
    "nativeBasisDegrees": 22,
    "nativeOrigin": origin.tolist(),
    "anchors": anchors,
    "metresPerPdfPoint": float(scale),
    "rotation": rotation.tolist(),
    "translation": translation.tolist(),
    "fitMaxResidualMetres": fit_residual,
    "independentDiagonalMaxResidualMetres": validation_residual,
    "axisFinding": "Published-plan right vertical edge corresponds to the retained north frontage; its bottom horizontal edge corresponds to the east street edge. Source plan must be rotated before interpreting left/right wings.",
    "highWingRegistrationAccepted": False,
    "nativeGeometryChanged": False,
    "limitations": [
        "Only three outer corners fit; two diagonal ends independently reveal footprint/pick differences.",
        "Third-floor plan is not the roof plan. It cannot uniquely register the higher office wings or photo05 blank wall.",
        "Native retained OSM footprint and published wall outline need distinct treatment; no anisotropic warp is used to force a fit.",
        "No complete floor or room geometry is claimed.",
    ],
}
(OUT / "registration.json").write_text(json.dumps(report, indent=2) + "\n")


def svg_points(points):
    return " ".join(f"{140+7*p[0]:.2f},{190-7*p[1]:.2f}" for p in points)


# Display model coordinates at both outlines; dashed blue uses independently
# picked third-floor corners, not a traced construction drawing.
boundary = [registered[i] for i in [0, 1, 2, 3, 4]]
svg = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600" viewBox="-140 -50 900 600">',
    '<rect x="-140" y="-50" width="900" height="600" fill="white"/>',
    '<text x="-110" y="-15" font-family="sans-serif" font-size="20">MAR published third-floor outline: coarse registration</text>',
    f'<polygon points="{svg_points(local)}" fill="none" stroke="#383838" stroke-width="2"/>',
    f'<polygon points="{svg_points(boundary)}" fill="none" stroke="#246090" stroke-width="2" stroke-dasharray="7 5"/>',
]
for i, anchor in enumerate(anchors):
    p, q = target[i], registered[i]
    svg.append(f'<polyline points="{svg_points([p,q])}" fill="none" stroke="#ae4339"/>')
    svg.append(
        f'<circle cx="{140+7*p[0]:.2f}" cy="{190-7*p[1]:.2f}" r="4" fill="#383838"/>'
    )
    svg.append(
        f'<text x="{150+7*p[0]:.2f}" y="{185-7*p[1]:.2f}" font-family="sans-serif" font-size="11">{anchor["role"]} {anchor["residualMetres"]:.2f}m</text>'
    )
svg += [
    f'<text x="-110" y="480" font-family="sans-serif" font-size="14">Black: retained site outline. Dashed blue: source third-floor corner picks.</text>',
    f'<text x="-110" y="508" font-family="sans-serif" font-size="14">Fit max {fit_residual:.2f}m; independent diagonal max {validation_residual:.2f}m. High wings unregistered.</text>',
    "</svg>",
]
(OUT / "outline-registration.svg").write_text("".join(svg))
print(
    "MAR_COARSE_OUTLINE_REGISTERED",
    round(fit_residual, 3),
    round(validation_residual, 3),
)
