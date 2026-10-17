"""Explore separate inner/outer SAW upper stair paths from historical plans.

Run with the existing MachineLearning environment. This is a private planning
study, not permission to replace the native. A candidate must keep the fixed
lift voids, full-width headroom and a source-constrained fourth-floor passage.
All dimensions, step schedules and curve radii remain authoring estimates.
"""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point, Polygon, box, mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/saw-circulation242"
NATIVE_SHA = "3b49385387b8e5c53223a1151762b80b9b3e1e4c2bbfbd474dfa820af4e424b4"
SOURCE_ZONES = {
    28: [(655, 479), (779, 426), (878, 478), (827, 622), (805, 557), (681, 584)],
    27: [
        (655, 474),
        (823, 447),
        (976, 514),
        (951, 650),
        (823, 650),
        (805, 548),
        (680, 576),
    ],
}
REGISTRATION = json.loads(
    (ROOT / "result/blender/saw-floors216/registration.json").read_text()
)
A, B, C = np.array(
    [[-65.223399, -15.905616], [-84.252182, 28.425], [-55.301, 36.609104]]
)
WORLD_MATRIX = np.column_stack(((B - A) / 1200, (C - B) / 785))
PIXEL_FACTOR = 1501 / 595.276


def source_to_world(points, page):
    registration = REGISTRATION[str(page)]
    ground = (
        np.array(points) @ np.array(registration["matrix"])
        + np.array(registration["offset"]) * PIXEL_FACTOR
    )
    return A + (ground - [145, 400]) @ WORLD_MATRIX.T


def world_to_source(points, page):
    registration = REGISTRATION[str(page)]
    ground = (np.array(points) - A) @ np.linalg.inv(WORLD_MATRIX).T + [145, 400]
    return (ground - np.array(registration["offset"]) * PIXEL_FACTOR) @ np.linalg.inv(
        registration["matrix"]
    )


def horizontal_surfaces(row, two_sided=False):
    vertices = np.array(row["vertices"])
    surfaces = []
    for index, face in enumerate(row["faces"]):
        points = vertices[face]
        if len(points) < 3 or np.ptp(points[:, 2]) > 1e-5:
            continue
        if (
            not two_sided
            and np.cross(points[1] - points[0], points[2] - points[0])[2] <= 1e-8
        ):
            continue
        polygon = Polygon(points[:, :2])
        if polygon.area > 1e-8:
            surfaces.append(
                {
                    "object": row["name"],
                    "face": index,
                    "top": float(points[0, 2]),
                    "polygon": polygon,
                }
            )
    return surfaces


def rounded_route(source_controls, width, radius, count, lower, upper, flight):
    """A metric circular corner prevents a zero-width inner winder edge."""
    start, corner, end = source_to_world(source_controls, 28)
    incoming, outgoing = corner - start, end - corner
    first_length, last_length = np.linalg.norm(incoming), np.linalg.norm(outgoing)
    incoming /= first_length
    outgoing /= last_length
    angle = math.acos(float(np.clip(incoming @ outgoing, -1, 1)))
    sign = 1 if incoming[0] * outgoing[1] - incoming[1] * outgoing[0] > 0 else -1
    trim = radius * math.tan(angle / 2)
    if trim >= min(first_length, last_length) or radius <= width / 2 + 0.08:
        return None
    entry = corner - incoming * trim
    exit_point = corner + outgoing * trim
    normal = np.array([-incoming[1], incoming[0]])
    centre = entry + normal * radius * sign
    initial_angle = math.atan2(*(entry - centre)[::-1])
    straight_first = first_length - trim
    arc_length = radius * angle
    straight_last = last_length - trim
    length = straight_first + arc_length + straight_last

    def sample(distance):
        if distance <= straight_first:
            point = start + incoming * distance
            tangent = incoming
        elif distance < straight_first + arc_length:
            theta = initial_angle + sign * (distance - straight_first) / radius
            radial = np.array([math.cos(theta), math.sin(theta)])
            point = centre + radial * radius
            tangent = sign * np.array([-radial[1], radial[0]])
        else:
            point = exit_point + outgoing * (distance - straight_first - arc_length)
            tangent = outgoing
        normal = np.array([-tangent[1], tangent[0]])
        return point, normal

    surfaces = []
    for index in range(count):
        distances = np.linspace(length * index / count, length * (index + 1) / count, 9)
        pairs = [sample(distance) for distance in distances]
        left = [point + normal * width / 2 for point, normal in pairs]
        right = [point - normal * width / 2 for point, normal in pairs]
        polygon = Polygon(left + right[::-1])
        if not polygon.is_valid:
            return None
        top = lower + (upper - lower) * (index + 1) / count
        surfaces.append(
            {
                "flight": flight,
                "index": index + 1,
                "top": top,
                "bottom": top - (upper - lower) / count - 0.18,
                "polygon": polygon,
            }
        )
    route = {
        "flight": flight,
        "lowerDatum": lower,
        "upperDatum": upper,
        "sourceControls": source_controls,
        "sourceReferencePage": 28,
        "width": width,
        "cornerRadius": radius,
        "count": count,
        "rise": (upper - lower) / count,
        "centreGoing": length / count,
        "length": length,
        "start": start.tolist(),
        "end": end.tolist(),
        "startDirection": incoming.tolist(),
        "endDirection": outgoing.tolist(),
        "centreline": LineString([sample(s)[0] for s in np.linspace(0, length, 120)]),
        "surfaces": surfaces,
    }
    return route


def full_height_pair_conflicts(surfaces):
    conflicts = []
    for i, first in enumerate(surfaces):
        for second in surfaces[i + 1 :]:
            lower, upper = (
                (first, second) if first["top"] < second["top"] else (second, first)
            )
            if abs(lower["top"] - upper["top"]) < 0.001:
                continue
            area = lower["polygon"].intersection(upper["polygon"]).area
            if area > 1e-5 and upper["bottom"] - lower["top"] < 2.1:
                conflicts.append(
                    {
                        "lowerFlight": lower["flight"],
                        "lowerIndex": lower["index"],
                        "upperFlight": upper["flight"],
                        "upperIndex": upper["index"],
                        "area": area,
                        "clearance": upper["bottom"] - lower["top"],
                    }
                )
    return conflicts


def floor_region(contour, lifts, all_steps, datum):
    overhead_opening = unary_union(
        [
            row["polygon"]
            for row in all_steps
            if datum - 2.3 < row["top"] < datum - 0.001
        ]
    ).buffer(0.06, join_style=2)
    arrivals = unary_union(
        [row["polygon"] for row in all_steps if abs(row["top"] - datum) < 0.001]
    )
    return (
        contour.difference(lifts.buffer(0.03, join_style=2))
        .difference(overhead_opening)
        .union(arrivals)
    )


def connection_at_fourth(routes, contour, lifts, zone):
    surfaces = [surface for route in routes for surface in route["surfaces"]]
    support = floor_region(contour, lifts, surfaces, 14.1).intersection(zone)
    blocked = unary_union(
        [
            row["polygon"]
            for row in surfaces
            if 14.1001 < row["top"] and row["bottom"] < 16.2
        ]
    ).buffer(0.02)
    clear = support.difference(blocked)
    # Arrival reaches a level floor beyond the final riser; departure approaches
    # the first riser from behind, rather than from the stair body itself.
    first, second = routes
    arrival = np.array(first["end"]) + np.array(first["endDirection"]) * 0.65
    departure = np.array(second["start"]) - np.array(second["startDirection"]) * 0.65
    checks = []
    for width in [1.1, 0.8, 0.6, 0.4]:
        eroded = clear.buffer(-width / 2, join_style=2)
        components = list(eroded.geoms) if hasattr(eroded, "geoms") else [eroded]
        shared = [
            i
            for i, p in enumerate(components)
            if p.distance(Point(arrival)) < 0.08 and p.distance(Point(departure)) < 0.08
        ]
        checks.append({"width": width, "connected": bool(shared)})
    return {
        "anchors": [arrival.tolist(), departure.tolist()],
        "checks": checks,
        "clear": clear,
    }


def serialise_route(route):
    return {
        key: (mapping(value) if hasattr(value, "geom_type") else value)
        for key, value in route.items()
        if key not in ["surfaces"]
    }


def vector_source_zones(floors):
    """Retain the source's exact coloured-room outlines, not a guessed raster trace."""
    import pdfplumber

    zones, records = {}, []
    pdf_path = ROOT / "data/documents/saw_occupants_guide_2014.pdf"
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, datum in [(29, 11.1), (28, 14.1), (27, 18.0)]:
            page = pdf.pages[page_number - 1]
            regions = []
            source_indices = []
            for index, curve in enumerate(page.curves):
                colour = curve.get("non_stroking_color")
                if (
                    not curve.get("fill")
                    or not isinstance(colour, (list, tuple))
                    or len(colour) != 3
                    or max(colour) - min(colour) < 0.08
                ):
                    continue
                if len(curve["pts"]) < 3:
                    continue
                region = Polygon(np.array(curve["pts"]) * PIXEL_FACTOR)
                if not region.is_valid:
                    region = region.buffer(0)
                if region.area > 1e-8:
                    regions.append(region)
                    source_indices.append(index)
            coloured = unary_union(regions)
            local = box(0, 0, 1501, 1501).difference(coloured)
            from shapely.ops import transform

            def to_world(x, y, z=None, source_page=page_number):
                points = source_to_world(np.column_stack((x, y)), source_page)
                return points[:, 0], points[:, 1]

            local_world = transform(to_world, local)
            contour = Polygon(
                next(
                    f["outlineWorld"] for f in floors if abs(f["datum"] - datum) < 0.01
                )
            )
            zone = local_world.intersection(contour)
            zones[page_number] = zone
            records.append(
                {
                    "page": page_number,
                    "sourceColouredCurves": source_indices,
                    "sourceColouredAreaPixels2": coloured.intersection(
                        box(640, 420, 900, 660)
                    ).area,
                    "worldWhiteRegion": mapping(zone),
                    "whiteRegionM2": zone.area,
                    "localStairWhiteRegionM2": zone.intersection(
                        Polygon(
                            source_to_world(
                                [[640, 420], [900, 420], [900, 660], [640, 660]],
                                page_number,
                            )
                        )
                    ).area,
                    "historicalRasterTraceAreaM2": (
                        Polygon(
                            source_to_world(SOURCE_ZONES[page_number], page_number)
                        ).area
                        if page_number in SOURCE_ZONES
                        else None
                    ),
                }
            )
    (OUT / "vector-source-white-zones.json").write_text(
        json.dumps(
            {
                "sourcePdfSha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
                "records": records,
                "scope": "Complete uncoloured area within inherited source floor outline; coloured room fills excluded exactly. White fill is not proof of2026public access or a measured wall/shaft model.",
            },
            indent=2,
        )
        + "\n"
    )
    return zones


def main():
    native = json.loads((OUT / "current-surfaces.json").read_text())
    assert native["baselineSha256"] == NATIVE_SHA
    assert (
        hashlib.sha256(
            (ROOT / "result/blender/LSE_campus_detailed_v241.blend").read_bytes()
        ).hexdigest()
        == NATIVE_SHA
    )
    prior = json.loads(
        (ROOT / "result/blender/saw-circulation233/plan.json").read_text()
    )
    lifts = unary_union([shape(poly) for poly in prior["lifts"]])
    floors = json.loads(
        (ROOT / "result/blender/saw-floors216/surface-plan.json").read_text()
    )["floors"]
    contour = Polygon(
        next(f["outlineWorld"] for f in floors if abs(f["datum"] - 14.1) < 0.01)
    )
    zones = vector_source_zones(floors)
    source_zone, source_zone5 = zones[28], zones[27]
    old = [
        surface
        for row in native["objects"]
        if row["name"].endswith("registered_main_treads")
        for surface in horizontal_surfaces(row)
    ]
    lift_conflicts = [
        {
            "face": row["face"],
            "top": row["top"],
            "overlapM2": row["polygon"].intersection(lifts).area,
        }
        for row in old
        if row["polygon"].intersection(lifts).area > 1e-5
    ]
    assert len(lift_conflicts) == 11
    records = []
    best = None
    tested = 0
    for outer_start in [[825, 550], [830, 540]]:
        for outer_turn in [[780, 450], [785, 460]]:
            for outer_end in [[700, 515], [710, 525]]:
                for inner_start in [[710, 550], [715, 555], [720, 555]]:
                    for inner_turn in [[775, 510], [780, 515], [785, 515]]:
                        for inner_end in [[825, 550], [830, 555], [835, 550]]:
                            for width in [1.1, 1.2]:
                                for radius in [0.75, 0.9]:
                                    tested += 1
                                    lower = rounded_route(
                                        [outer_start, outer_turn, outer_end],
                                        width,
                                        radius,
                                        20,
                                        11.1,
                                        14.1,
                                        3,
                                    )
                                    upper = rounded_route(
                                        [inner_start, inner_turn, inner_end],
                                        width,
                                        radius,
                                        21,
                                        14.1,
                                        18.0,
                                        4,
                                    )
                                    if lower is None or upper is None:
                                        continue
                                    surfaces = lower["surfaces"] + upper["surfaces"]
                                    footprint = unary_union(
                                        [row["polygon"] for row in surfaces]
                                    )
                                    outside = footprint.difference(source_zone).area
                                    outside5 = (
                                        unary_union(
                                            [
                                                row["polygon"]
                                                for row in upper["surfaces"]
                                            ]
                                        )
                                        .difference(source_zone5)
                                        .area
                                    )
                                    lift_area = footprint.intersection(
                                        lifts.buffer(0.03)
                                    ).area
                                    if (
                                        outside > 0.0001
                                        or outside5 > 0.0001
                                        or lift_area > 0.0001
                                    ):
                                        continue
                                    conflicts = full_height_pair_conflicts(surfaces)
                                    if conflicts:
                                        continue
                                    connection = connection_at_fourth(
                                        [lower, upper], contour, lifts, source_zone
                                    )
                                    score = next(
                                        (
                                            c["width"]
                                            for c in connection["checks"]
                                            if c["connected"]
                                        ),
                                        0,
                                    )
                                    record = {
                                        "routes": [
                                            serialise_route(lower),
                                            serialise_route(upper),
                                        ],
                                        "sourceOutsideArea": outside,
                                        "liftOverlapArea": lift_area,
                                        "pairConflicts": len(conflicts),
                                        "fourthFloorConnection": {
                                            k: v
                                            for k, v in connection.items()
                                            if k != "clear"
                                        },
                                        "maximumTestedConnectedWidth": score,
                                    }
                                    records.append(record)
                                    if best is None or score > best[0]:
                                        best = (
                                            score,
                                            record,
                                            [lower, upper],
                                            connection,
                                        )
    result = {
        "baselineSha256": NATIVE_SHA,
        "readOnlyNative": True,
        "currentRetainedLiftConflicts": lift_conflicts,
        "tested": tested,
        "planarClearCandidates": records,
        "scope": "Opposed inner/outer estimated winding paths, source white zones and fixed cabin holes; actual saved-mesh triangle headroom and native authoring remain required",
        "nativeChanged": False,
    }
    (OUT / "opposed-route-feasibility.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(
        "SAW242_PLAN_FEASIBILITY",
        tested,
        len(records),
        "bestWidth",
        None if best is None else best[0],
        flush=True,
    )
    if best:
        score, record, routes, connection = best
        (OUT / "best-plan.json").write_text(
            json.dumps(
                {
                    **record,
                    "surfaces": [
                        {
                            **{k: v for k, v in row.items() if k != "polygon"},
                            "polygon": mapping(row["polygon"]),
                        }
                        for route in routes
                        for row in route["surfaces"]
                    ],
                    "clearFourthFloor": mapping(connection["clear"]),
                },
                indent=2,
            )
            + "\n"
        )
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(9, 9))
        for region in (
            list(source_zone.geoms) if hasattr(source_zone, "geoms") else [source_zone]
        ):
            ax.fill(*np.array(region.exterior.coords).T, color="#eeeeee", ec="black")
        for poly in lifts.geoms:
            ax.fill(*np.array(poly.exterior.coords).T, color="#993333", alpha=0.6)
        for route, colour in zip(routes, ["#286e9f", "#ba782a"], strict=True):
            for row in route["surfaces"]:
                ax.fill(
                    *np.array(row["polygon"].exterior.coords).T,
                    color=colour,
                    alpha=0.55,
                    ec="white",
                    lw=0.3,
                )
        for point in connection["anchors"]:
            ax.plot(*point, "ko")
        ax.set_aspect("equal")
        ax.grid(alpha=0.2)
        ax.set_title(
            f"Private242 opposed-path study; source-constrained passage tested{score:g}m"
        )
        fig.tight_layout()
        fig.savefig(OUT / "opposed-path-plan.png", dpi=150)
        plt.close(fig)


if __name__ == "__main__":
    main()
