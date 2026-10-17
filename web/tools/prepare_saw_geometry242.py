"""Create a private solid-geometry plan for full-mesh review before native assembly."""

import importlib.util
import itertools
import json
import math
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon, mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/saw-circulation242"
spec = importlib.util.spec_from_file_location(
    "planner242", ROOT / "web/tools/plan_saw_upper242.py"
)
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


class Mesh:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.indices = {}

    def face(self, points):
        indices = []
        for point in points:
            key = tuple(round(float(v), 7) for v in point)
            if key not in self.indices:
                self.indices[key] = len(self.vertices)
                self.vertices.append(key)
            indices.append(self.indices[key])
        if len(set(indices)) >= 3:
            self.faces.append(indices)

    def tube(self, a, b, radius):
        a, b = np.array(a), np.array(b)
        axis = b - a
        axis /= np.linalg.norm(axis)
        u = np.cross(axis, [0.0, 0.0, 1.0])
        if np.linalg.norm(u) < 0.01:
            u = np.cross(axis, [1.0, 0.0, 0.0])
        u /= np.linalg.norm(u)
        v = np.cross(axis, u)
        rings = [
            [
                p
                + radius
                * (math.cos(j * math.tau / 8) * u + math.sin(j * math.tau / 8) * v)
                for j in range(8)
            ]
            for p in [a, b]
        ]
        self.face(rings[0][::-1])
        self.face(rings[1])
        for j in range(8):
            self.face(
                [rings[0][j], rings[0][(j + 1) % 8], rings[1][(j + 1) % 8], rings[1][j]]
            )


def mesh_record(name, mesh, source):
    return {
        "name": name,
        "vertices": mesh.vertices,
        "faces": mesh.faces,
        "source": source,
    }


def solid_stair(route):
    mesh = Mesh()
    count = route["count"]
    rise = route["rise"]
    lower = route["lowerDatum"]
    samples = 8
    for step, walk in enumerate(route["surfaces"]):
        coordinates = list(walk["polygon"].exterior.coords)[:-1]
        left = np.array(coordinates[: samples + 1])
        right = np.array(coordinates[samples + 1 :][::-1])
        top = walk["top"]
        previous = lower + step * rise
        for j in range(samples):
            s0 = (step + j / samples) / count
            s1 = (step + (j + 1) / samples) / count
            bottom0 = lower + (route["upperDatum"] - lower) * s0 - 0.18
            bottom1 = lower + (route["upperDatum"] - lower) * s1 - 0.18
            l0, l1, r0, r1 = left[j], left[j + 1], right[j], right[j + 1]
            mesh.face([(*l0, top), (*r0, top), (*r1, top), (*l1, top)])
            mesh.face([(*l0, bottom0), (*l1, bottom1), (*r1, bottom1), (*r0, bottom0)])
            left_wall = [(*l0, bottom0)]
            right_wall = [(*r0, bottom0)]
            if j == 0 and step > 0:
                left_wall.append((*l0, previous))
                right_wall.append((*r0, previous))
            mesh.face(left_wall + [(*l0, top), (*l1, top), (*l1, bottom1)])
            mesh.face((right_wall + [(*r0, top), (*r1, top), (*r1, bottom1)])[::-1])
            if j == 0:
                if step == 0:
                    mesh.face([(*l0, bottom0), (*r0, bottom0), (*r0, top), (*l0, top)])
                else:
                    mesh.face(
                        [(*l0, previous), (*r0, previous), (*r0, top), (*l0, top)]
                    )
            if step == count - 1 and j == samples - 1:
                mesh.face([(*l1, bottom1), (*l1, top), (*r1, top), (*r1, bottom1)])
    return mesh


def retain_current(row, cutoff):
    vertices = np.array(row["vertices"])
    faces = []
    selected = []
    for i, face in enumerate(row["faces"]):
        if max(vertices[face, 2]) < cutoff:
            faces.append(face)
            selected.append(i)
    return {
        "name": "SAW242_Retained_" + row["name"],
        "vertices": row["vertices"],
        "faces": faces,
        "source": row["name"],
        "retainedSourceFaces": selected,
    }


def main():
    study = json.loads((OUT / "best-plan.json").read_text())
    assert study["maximumTestedConnectedWidth"] >= 1.1
    baseline = json.loads((OUT / "current-surfaces.json").read_text())
    source = {r["name"]: r for r in baseline["objects"]}
    tread_source = next(n for n in source if n.endswith("registered_main_treads"))
    nosing_source = next(n for n in source if n.endswith("flat_anti_slip_nosings"))
    rail_source = next(n for n in source if n.endswith("main_stair_rails"))
    landing_source = next(
        n for n in source if n.endswith("coordinated_shared_floor_landings")
    )
    records = [
        retain_current(source[n], 11.1001)
        for n in [tread_source, nosing_source, rail_source]
    ]
    archived = [tread_source, nosing_source, rail_source, landing_source]
    routes = []
    for r in study["routes"]:
        route = planner.rounded_route(
            r["sourceControls"],
            r["width"],
            r["cornerRadius"],
            r["count"],
            r["lowerDatum"],
            r["upperDatum"],
            r["flight"],
        )
        routes.append(route)
        records.append(
            mesh_record(
                f"SAW242_Flight{r['flight']}_continuous_winding_waist",
                solid_stair(route),
                tread_source,
            )
        )
    retained_steps = [
        surface
        for row in baseline["objects"]
        if (
            "continuous_waists" in row["name"]
            or row["name"].endswith("registered_main_treads")
            or row["name"].startswith("SAW223_ST04_continuous_spiral")
        )
        for surface in planner.horizontal_surfaces(row)
        if surface["top"] < 11.1001 or surface["top"] > 18.001
    ]
    all_steps = retained_steps + [row for route in routes for row in route["surfaces"]]
    floor_source = json.loads(
        (ROOT / "result/blender/saw-floors216/surface-plan.json").read_text()
    )["floors"]
    zones = planner.vector_source_zones(floor_source)
    floor_records = []
    for page, datum, floor_name in [
        (29, 11.1, "SAW233_Coordinated_floor_11.1"),
        (28, 14.1, "SAWFLOOR216_registered_floor_14.1"),
        (27, 18.0, "SAWFLOOR216_registered_floor_18.0"),
    ]:
        contour = Polygon(
            next(
                r["outlineWorld"]
                for r in floor_source
                if abs(r["datum"] - datum) < 0.01
            )
        )
        old = unary_union(
            [
                r["polygon"]
                for name in [floor_name, landing_source]
                for r in planner.horizontal_surfaces(
                    source[name], two_sided=name == floor_name
                )
                if abs(r["top"] - datum) < 0.001
            ]
        )
        lifts = unary_union(
            [
                shape(p)
                for p in json.loads(
                    (ROOT / "result/blender/saw-circulation233/plan.json").read_text()
                )["lifts"]
            ]
        )
        new = planner.floor_region(contour, lifts, all_steps, datum)
        # Only the source's local uncoloured stair/circulation area may change.
        edit = zones[page].intersection(
            Polygon(
                planner.source_to_world(
                    [[640, 420], [900, 420], [900, 660], [640, 660]], page
                )
            )
        )
        coordinated = old.difference(edit).union(new.intersection(edit))
        assert (
            coordinated.difference(edit).symmetric_difference(old.difference(edit)).area
            < 1e-7
        )
        mesh = Mesh()
        for triangle in shapely.constrained_delaunay_triangles(coordinated).geoms:
            ring = list(triangle.exterior.coords)[:-1]
            if (
                np.cross(np.subtract(ring[1], ring[0]), np.subtract(ring[2], ring[0]))
                < 0
            ):
                ring.reverse()
            mesh.face([(*p, datum) for p in ring])
        records.append(
            mesh_record(f"SAW242_Coordinated_floor_{datum:g}", mesh, floor_name)
        )
        archived.append(floor_name)
        floor_records.append(
            {
                "datum": datum,
                "name": records[-1]["name"],
                "polygon": mapping(coordinated),
                "editRegion": mapping(edit),
                "outsideEditDifferenceM2": 0,
            }
        )
    for route in routes:
        rails = Mesh()
        nosings = Mesh()
        count = route["count"]
        width = route["width"]
        lower = route["lowerDatum"]
        rise = route["rise"]
        pairs = []
        for index, walk in enumerate(route["surfaces"]):
            points = list(walk["polygon"].exterior.coords)[:-1]
            left = np.array(points[:9])
            right = np.array(points[9:][::-1])
            if index == 0:
                pairs.append((left[0], right[0]))
            pairs.extend(zip(left[1:], right[1:], strict=True))
            # A narrow flat anti-slip strip at the front of each tread.
            left0, right0 = left[0], right[0]
            left1 = left0 + (left[1] - left0) * 0.65
            right1 = right0 + (right[1] - right0) * 0.65
            ring = [left0, right0, right1, left1]
            top = walk["top"] + 0.003
            bottom = walk["top"] + 0.001
            nosings.face([(*p, top) for p in ring])
            nosings.face([(*p, bottom) for p in ring[::-1]])
            for a, b in zip(ring, ring[1:] + ring[:1]):
                nosings.face([(*a, bottom), (*b, bottom), (*b, top), (*a, top)])
        for side in [-1, 1]:
            rail_points = []
            for index, (left, right) in enumerate(pairs):
                fraction = index / (len(pairs) - 1)
                normal = (left - right) / width
                centre = (left + right) / 2
                q = centre + normal * side * (width / 2 + 0.045)
                rail_points.append((*q, lower + rise * count * fraction + 1.02))
            for a, b in itertools.pairwise(rail_points):
                rails.tube(a, b, 0.023)
            for step in range(0, count + 1, 3):
                index = max(1, min(len(pairs) - 2, step * 8))
                left, right = pairs[index]
                normal = (left - right) / width
                centre = (left + right) / 2
                q = centre + normal * side * (width / 2 + 0.045)
                top = lower + rise * count * index / (len(pairs) - 1) + 1.02
                tread_top = lower + rise * math.ceil(index / 8)
                rails.tube((*q, tread_top - 0.08), (*q, top), 0.018)
                anchor = centre + normal * side * (width / 2 - 0.01)
                rails.tube((*anchor, tread_top - 0.09), (*q, tread_top - 0.09), 0.018)
        records.append(
            mesh_record(
                f"SAW242_Flight{route['flight']}_supported_handrails",
                rails,
                rail_source,
            )
        )
        records.append(
            mesh_record(
                f"SAW242_Flight{route['flight']}_flat_anti_slip_nosings",
                nosings,
                nosing_source,
            )
        )
    result = {
        "baselineSha256": baseline["baselineSha256"],
        "objects": records,
        "archivedObjects": archived,
        "floors": floor_records,
        "routes": [planner.serialise_route(route) for route in routes],
        "walkingSurfaces": [
            {
                **{k: v for k, v in row.items() if k != "polygon"},
                "polygon": mapping(row["polygon"]),
            }
            for route in routes
            for row in route["surfaces"]
        ],
        "sourceZones": "vector-source-white-zones.json",
        "status": "Private geometry plan, not a saved native or accepted full-width triangle proof",
    }
    (OUT / "geometry-plan.json").write_text(
        json.dumps(result, separators=(",", ":")) + "\n"
    )
    print(
        "GEOMETRY_PLAN242",
        len(records),
        len(archived),
        sum(len(r["faces"]) for r in records),
        flush=True,
    )


if __name__ == "__main__":
    main()
