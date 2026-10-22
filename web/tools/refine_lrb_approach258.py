"""Calibrate the library's visible southwest frontage to its2025AsExisting drawing.

The original source meshes are archived, never rewritten. This component
corrects the historic/modern bay rhythm, wide Library portal and the visible
roof edge. Connections behind the traced frontage are bounded estimates.
Run this fixed-path script in Blender through the project's serial scheduler.
"""

import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v257.blend"
SHA = "5f73b29480de08425d4d8ab3c39aa1e2b9231656f81f1f763ee1ffa200568db9"
OUT = ROOT / "result/blender/lrb258"
DEST = "LRB_EXTERIOR"
ROOF = "LRB_EXTERIOR210_LRB_V117_current_perimeter_roof"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
import itertools

from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_ocs_exterior257 import parts


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def capture():
    spec = importlib.util.spec_from_file_location(
        "lrb258_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


class Frame:
    """Keep the source's unfolded stations on the actual three GIS faces."""

    def __init__(self, plan):
        self.plan = plan
        self.chain = [Vector(p) for p in plan["gisPolyline"]]
        self.prefix = plan["gisStations"]
        self.scale = plan["estimatedHorizontalScale"]
        self.zscale = plan["verticalMapping"]["scale"]

    def s(self, x):
        return (x - 46.56) * self.scale

    def z(self, y):
        return 0.3319997787475586 + (1235.559 - y) * self.zscale

    def i(self, s):
        return next((i for i in range(3) if s <= self.prefix[i + 1] + 1e-7), 2)

    def basis(self, i):
        u = (self.chain[i + 1] - self.chain[i]).normalized()
        return u, Vector((u.y, -u.x, 0))

    def point(self, s, d, z, i=None):
        i = self.i(s) if i is None else i
        u, n = self.basis(i)
        return self.chain[i] + u * (s - self.prefix[i]) + n * d + Vector((0, 0, z))

    def local(self, p):
        rows = []
        for i, (a, b) in enumerate(zip(self.chain, self.chain[1:])):
            u, n = self.basis(i)
            along = max(0.0, min((p - a).dot(u), (b - a).length))
            q = a + u * along
            rows.append(((p.xy - q.xy).length, self.prefix[i] + along, (p - q).dot(n)))
        _, s, d = min(rows)
        return Vector((s, d, p.z))

    def cuts(self, a, b):
        return [a] + [s for s in self.prefix[1:-1] if a + 1e-6 < s < b - 1e-6] + [b]


class Batch:
    def __init__(self, name, material):
        self.name = name
        self.material = material
        self.vertices = []
        self.faces = []
        self.probes = []

    def face(self, points):
        first = len(self.vertices)
        self.vertices.extend(tuple(p) for p in points)
        self.faces.append(tuple(range(first, len(self.vertices))))

    def box(self, F, a, b, d0, d1, z0, z1):
        if min(b - a, d1 - d0, z1 - z0) < 1e-6:
            return
        cuts = F.cuts(a, b)
        for lo, hi in itertools.pairwise(cuts):
            i = F.i((lo + hi) / 2)
            p = [
                F.point(s, d, z, i)
                for z in [z0, z1]
                for d in [d0, d1]
                for s in [lo, hi]
            ]
            for indices in [
                (0, 1, 3, 2),
                (4, 6, 7, 5),
                (0, 4, 5, 1),
                (2, 3, 7, 6),
                (0, 2, 6, 4),
                (1, 5, 7, 3),
            ]:
                self.face([p[j] for j in indices])

    def build(self):
        if not self.faces:
            return None
        mesh = bpy.data.meshes.new(self.name + "_mesh")
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        mesh.materials.append(bpy.data.materials[self.material])
        uv = mesh.uv_layers.new(name="MetricUV")
        for face in mesh.polygons:
            normal = face.normal
            axes = (0, 2) if abs(normal.y) > abs(normal.x) else (1, 2)
            if abs(normal.z) > 0.9:
                axes = (0, 1)
            for li in face.loop_indices:
                p = mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv = (p[axes[0]], p[axes[1]])
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.data.collections[DEST].objects.link(obj)
        obj["destinationCollection"] = DEST
        obj["sourceDrawing"] = "4556-FBR-LR-ZZ-DR-A-111 P01 As Existing"
        obj["webGeometrySource"] = self.name
        if self.name.endswith("_roof"):
            obj["sharedInteriorRoof"] = True
        return obj


def apertures(F):
    """Explicit outer controls read from original PDF vector edges."""
    rows = []

    def add(name, l, r, t, b, cols, lines, kind="modern", xs=None, ys=None):
        rows.append(
            {
                "name": name,
                "a": F.s(l),
                "b": F.s(r),
                "bottom": F.z(b),
                "top": F.z(t),
                "columns": cols,
                "rows": lines,
                "kind": kind,
                "pageBounds": [l, r, t, b],
                "columnFractions": xs,
                "rowFractions": ys,
            }
        )

    add("historic_ground_left", 84.719, 234.84, 1115.199, 1225.48, 3, 3, "historic")
    # Five divisions are evidenced; actual door operation remains unassigned.
    add(
        "Library_lower_glazed_divisions",
        294.48,
        444.359,
        1146.879,
        1235.559,
        5,
        1,
        "entry",
    )
    add(
        "Library_upper_three_by_two",
        294.48,
        444.359,
        1114.359,
        1144.0,
        3,
        2,
        "entry",
        xs=[0.4, 0.6],
    )
    historic_inner = [
        [
            [(92.52, 134.52), (138.719, 180.719), (184.922, 226.801)],
            [(92.879, 133.68), (139.559, 180.359), (185.762, 226.68)],
            [(92.879, 133.68), (139.559, 179.879), (185.762, 226.441)],
        ],
        [
            [(302.039, 344.039), (348.238, 390.238), (394.441, 436.32)],
            [(302.398, 343.199), (349.199, 390.0), (395.398, 436.199)],
            [(302.398, 343.199), (349.199, 389.398), (395.398, 436.078)],
        ],
    ]
    for col, levels in enumerate(historic_inner):
        for level, panes in enumerate(levels):
            t, b = [(986.32, 1068.762), (881.32, 942.281), (779.559, 838.0)][level]
            for part, (l, r) in enumerate(panes):
                add(
                    f"historic_{col + 1}_upper_{level + 1}_part_{part + 1}",
                    l,
                    r,
                    t,
                    b,
                    4,
                    6 if level == 0 else 4,
                    "historic_upper",
                )
    modern = [
        (503.52, 648.961),
        (691.441, 836.879),
        (879.359, 1024.922),
        (1067.52, 1213.199),
        (1255.68, 1403.281),
    ]
    for col, (l, r) in enumerate(modern):
        for level, (t, b) in enumerate(
            [
                (984.762, 1074.281),
                (882.16, 943.359),
                (778.719, 839.922),
                (674.68, 735.879),
            ]
        ):
            if col == 4 and level == 3:
                continue
            add(
                f"modern_{col + 1}_upper_{level + 1}",
                l,
                r,
                t,
                b,
                3,
                3 if level == 0 else 2,
            )
    # The fifth modern top bay differs from the first four; no repeated proxy.
    add("modern_5_top_left", 1253.641, 1301.039, 674.68, 708.398, 1, 1)
    add("modern_5_top_right", 1354.801, 1402.32, 674.68, 708.398, 1, 1)
    add("modern_5_top_low_strip", 1255.68, 1403.281, 721.48, 735.879, 3, 1)
    for row in F.plan["groundBays"]:
        if row["name"] in ["historic_left_ground_window", "Library_main_entry"]:
            continue
        l, r, t, b = row["sourceBounds"]
        add(
            row["name"],
            l,
            r,
            t,
            b,
            3 if "window" in row["name"] else 4,
            3 if "window" in row["name"] else 1,
        )
    add("service_upper_1", 1439.281, 1559.281, 984.762, 1074.281, 2, 3)
    add("service_upper_2", 1439.281, 1559.281, 882.16, 943.359, 2, 2)
    add("service_upper_strip", 1439.281, 1559.281, 819.039, 841.602, 2, 1)
    add("modern_6_upper_1", 1585.32, 1744.32, 984.762, 1074.281, 3, 3)
    add("modern_6_upper_2", 1585.32, 1744.32, 891.52, 943.359, 3, 2)
    add("low_wing_left_upper", 1770.359, 1823.762, 919.84, 943.359, 1, 1)
    add("low_wing_right_upper", 1849.801, 1927.68, 919.84, 943.359, 2, 1)
    add("low_wing_cladding_window_left", 1686.0, 1720.441, 729.16, 743.078, 1, 1)
    add("low_wing_cladding_window_right", 1729.199, 1763.641, 729.16, 743.078, 1, 1)
    # Four dormers remain at source positions, with bounded estimated depth.
    for i, (l, r) in enumerate(
        [(89.641, 137.641), (181.801, 229.68), (299.52, 347.398), (391.32, 439.199)]
    ):
        add(f"historic_dormer_{i + 1}", l, r, 670.719, 746.68, 4, 5, "dormer")
    return rows


def wall_rectangle(F, batch, a, b, bottom, top, holes):
    xs = sorted(
        {a, b}
        | {
            max(a, min(b, h[k]))
            for h in holes
            for k in ["a", "b"]
            if h["a"] < b and h["b"] > a
        }
    )
    zs = sorted(
        {bottom, top}
        | {
            max(bottom, min(top, h[k]))
            for h in holes
            for k in ["bottom", "top"]
            if h["bottom"] < top and h["top"] > bottom
        }
    )
    for x0, x1 in itertools.pairwise(xs):
        for z0, z1 in itertools.pairwise(zs):
            x = (x0 + x1) / 2
            z = (z0 + z1) / 2
            if any(
                h["a"] - 1e-6 < x < h["b"] + 1e-6
                and h["bottom"] - 1e-6 < z < h["top"] + 1e-6
                for h in holes
            ):
                continue
            batch.box(F, x0, x1, -0.26, 0.1, z0, z1)


def make_windows(F, rows, batches):
    for row in rows:
        a, b, z0, z1 = (row[k] for k in ["a", "b", "bottom", "top"])
        dormer = row["kind"] == "dormer"
        historic_upper = row["kind"] == "historic_upper"
        glass = (
            batches["entry_glass"]
            if row["kind"] == "entry"
            else batches["historic_glass"]
            if row["kind"] in ["historic", "historic_upper", "dormer"]
            else batches["glass"]
        )
        pane_d = 0.24 if historic_upper else -0.025 if dormer else 0.12
        row["glassDepth"] = pane_d
        xf = row["columnFractions"] or [
            i / row["columns"] for i in range(1, row["columns"])
        ]
        yf = row["rowFractions"] or [i / row["rows"] for i in range(1, row["rows"])]
        per_column_rows = [yf for _ in range(row["columns"])]
        if row["name"].startswith("modern_") and row["name"].endswith("_upper_1"):
            upper = (row["pageBounds"][3] - 1014.4) / (
                row["pageBounds"][3] - row["pageBounds"][2]
            )
            lower = (row["pageBounds"][3] - 1042.7) / (
                row["pageBounds"][3] - row["pageBounds"][2]
            )
            per_column_rows = [[upper], [lower, upper], [upper]]
            row["perColumnRowFractions"] = per_column_rows
        xcuts = [a] + [a + (b - a) * v for v in xf] + [b]
        row["glassObject"] = glass.name
        row["glassFaceIndices"] = []
        for col, (left, right) in enumerate(itertools.pairwise(xcuts)):
            zcuts = [z0] + [z0 + (z1 - z0) * v for v in per_column_rows[col]] + [z1]
            for low, high in itertools.pairwise(zcuts):
                x0, x1 = left + 0.025, right - 0.025
                bottom, top = low + 0.022, high - 0.022
                for lo, hi in itertools.pairwise(F.cuts(x0, x1)):
                    i = F.i((lo + hi) / 2)
                    row["glassFaceIndices"].append(len(glass.faces))
                    glass.face(
                        [
                            F.point(lo, pane_d, bottom, i),
                            F.point(hi, pane_d, bottom, i),
                            F.point(hi, pane_d, top, i),
                            F.point(lo, pane_d, top, i),
                        ]
                    )
        frame = batches["frames"]
        frame_start = len(frame.faces)
        edge = 0.045 if row["kind"] != "entry" else 0.055
        d0, d1 = (
            (0.29, 0.41)
            if historic_upper
            else (0.025, 0.15)
            if dormer
            else (0.17, 0.29)
        )
        for lo, hi in [(a - edge, a), (b, b + edge)]:
            frame.box(F, lo, hi, d0, d1, z0 - edge, z1 + edge)
        for low, high in [(z0 - edge, z0), (z1, z1 + edge)]:
            frame.box(F, a, b, d0, d1, low, high)
        for f in xf:
            x = a + (b - a) * f
            frame.box(F, x - 0.015, x + 0.015, d0, d1, z0, z1)
        for col, (left, right) in enumerate(itertools.pairwise(xcuts)):
            for f in per_column_rows[col]:
                z = z0 + (z1 - z0) * f
                frame.box(F, left, right, d0, d1, z - 0.014, z + 0.014)
        row["frameFaceIndices"] = list(range(frame_start, len(frame.faces)))
        if not dormer:
            batches["stone"].box(
                F,
                a - 0.06,
                b + 0.06,
                0.06,
                0.48 if historic_upper else 0.38,
                z0 - 0.095,
                z0 - 0.025,
            )


def remove_front_components(F, inventory):
    added = []
    archived = []
    proof = []
    explicit = {
        "SITE232_EST_LRB_three_low_steps_and_entry_landing",
        "SITE232_EST_LRB_short_local_landing_handrails",
    }
    for row in inventory["frontageComponentClassification"]:
        source = bpy.data.objects[row["name"]]
        if (
            "Blue_Rain" in source.name
            or source.name.endswith("facade_wall_0_10")
            or "artwork_corner_wall" in source.name
        ):
            continue
        chosen = []
        planes = []
        for ids in parts(source.data):
            world_points = [
                source.matrix_world @ source.data.vertices[i].co for i in ids
            ]
            accepted = None
            for segment, (start, end) in enumerate(itertools.pairwise(F.prefix)):
                tangent, normal = F.basis(segment)
                origin = F.chain[segment]
                along = [(p - origin).dot(tangent) for p in world_points]
                depths = [(p - origin).dot(normal) for p in world_points]
                # Signed, unclamped halfspaces: endpoint projections cannot
                # collapse a Portugal/Serle return into a false SW component.
                if (
                    min(along) >= -0.011
                    and max(along) <= end - start + 0.011
                    and max(along) - min(along) > 1e-5
                    and min(depths) > -0.701
                    and max(depths) < 0.701
                ):
                    accepted = {
                        "segment": segment,
                        "signedAlongBounds": [min(along), max(along)],
                        "signedDepthBounds": [min(depths), max(depths)],
                    }
                    break
            if (
                source.name in explicit
                or "_entry_" in source.name
                or accepted is not None
            ):
                chosen.extend(ids)
                planes.append(
                    {
                        "vertexIndices": ids,
                        "halfspaceProof": accepted,
                        "explicitRetiredLocalApproach": source.name in explicit
                        or "_entry_" in source.name,
                    }
                )
        if not chosen:
            continue
        source.hide_render = True
        set_layer_hidden(source, True)
        archived.append(source.name)
        retained = sorted(set(range(len(source.data.vertices))) - set(chosen))
        clone = None
        if retained:
            clone = source.copy()
            clone.data = source.data.copy()
            clone.name = "LRB258_retained_" + source.name
            clone.hide_render = False
            bpy.data.collections[DEST].objects.link(clone)
            set_layer_hidden(clone, False)
            bm = bmesh.new()
            bm.from_mesh(clone.data)
            bm.verts.ensure_lookup_table()
            bmesh.ops.delete(bm, geom=[bm.verts[i] for i in chosen], context="VERTS")
            bm.to_mesh(clone.data)
            bm.free()
            clone.data.update()
            clone["originalObject"] = source.name
            clone["webGeometrySource"] = source.get("webGeometrySource", source.name)
            clone["destinationCollection"] = DEST
            added.append(clone)
        proof.append(
            {
                "source": source.name,
                "sourceFingerprint": object_fingerprint(source),
                "removedSourceVertexIndices": sorted(chosen),
                "actualSWComponentHalfspaces": planes,
                "retainedSourceVertexIndices": retained,
                "replacement": clone.name if clone else None,
            }
        )
    return added, archived, proof


def clip_polygon(poly, axis, value, keep_greater):
    """Clip position/UV records, preserving interpolated UV at each new cut."""
    if not poly:
        return []
    result = []

    def f(v):
        return (v[0][axis] - value) * (1 if keep_greater else -1)

    for a, b in zip(poly, poly[1:] + poly[:1]):
        da, db = f(a), f(b)
        ina, inb = da >= -1e-8, db >= -1e-8
        if ina:
            result.append(a)
        if ina != inb:
            t = da / (da - db)
            result.append(
                (a[0].lerp(b[0], t), [x.lerp(y, t) for x, y in zip(a[1], b[1])])
            )
    return result


def clip_roof_strip(F, source, depth):
    """Only subtract the proven lower20.24m plane's narrow SW return strip."""
    # Work in each segment's local linear coordinates, not nearest/clamped
    # stations, so clipping remains accurate at parcel corners.
    mesh = source.data
    uvs = list(mesh.uv_layers)
    out = []
    degenerate = []
    cut = []
    upper = []
    for face in mesh.polygons:
        poly = [
            (
                source.matrix_world @ mesh.vertices[mesh.loops[j].vertex_index].co,
                [layer.data[j].uv.copy() for layer in uvs],
            )
            for j in face.loop_indices
        ]
        if all(abs(v[0].z - 23.99) < 0.002 for v in poly):
            upper.append([[list(v[0]), [list(q) for q in v[1]]] for v in poly])
        if not all(abs(v[0].z - 20.24) < 0.002 for v in poly):
            out.append((poly, face.material_index))
            continue
        pieces = [poly]
        for i, (start, end) in enumerate(zip(F.prefix, F.prefix[1:])):
            u, n = F.basis(i)
            origin = F.chain[i]
            next_pieces = []
            for piece in pieces:
                local = [
                    (Vector(((p - origin).dot(u), (p - origin).dot(n), p.z)), uv)
                    for p, uv in piece
                ]
                inside = local
                for axis, value, greater in [
                    (0, 0, True),
                    (0, end - start, False),
                    (1, -depth, True),
                    (1, 0, False),
                ]:
                    outside = clip_polygon(inside, axis, value, not greater)
                    if len(outside) >= 3:
                        world = [
                            (origin + u * p.x + n * p.y + Vector((0, 0, p.z)), uv)
                            for p, uv in outside
                        ]
                        next_pieces.append(world)
                    inside = clip_polygon(inside, axis, value, greater)
                    if len(inside) < 3:
                        break
                if len(inside) >= 3:
                    cut.append(
                        {
                            "segment": i,
                            "points": [
                                list(origin + u * p.x + n * p.y + Vector((0, 0, p.z)))
                                for p, uv in inside
                            ],
                        }
                    )
            pieces = next_pieces
        for piece in pieces:
            p0 = piece[0][0]
            actual_area = sum(
                (piece[i][0] - p0).cross(piece[i + 1][0] - p0).length / 2
                for i in range(1, len(piece) - 1)
            )
            if actual_area > 1e-4:
                out.append((piece, face.material_index))
            else:
                degenerate.append(
                    {
                        "sourceFace": face.index,
                        "area": actual_area,
                        "points": [list(p) for p, uv in piece],
                    }
                )
    clone = source.copy()
    clone.name = "LRB258_retained_lower_roof_with_source_frontage_returns"
    vertices = []
    faces = []
    for poly, mat in out:
        offset = len(vertices)
        vertices.extend(tuple(p) for p, uv in poly)
        faces.append(tuple(range(offset, len(vertices))))
    new = bpy.data.meshes.new(clone.name + "_mesh")
    new.from_pydata(vertices, [], faces)
    new.update()
    for mat in mesh.materials:
        new.materials.append(mat)
    for layer in uvs:
        new.uv_layers.new(name=layer.name)
    for face, (poly, mat) in zip(new.polygons, out):
        face.material_index = mat
        for li, record in zip(face.loop_indices, poly):
            for k, layer in enumerate(new.uv_layers):
                layer.data[li].uv = record[1][k]
    # Coordinates above are world positions; explicitly use identity transform.
    clone.data = new
    clone.matrix_world = Matrix.Identity(4)
    clone.hide_render = False
    bpy.data.collections[DEST].objects.link(clone)
    set_layer_hidden(clone, False)
    clone["originalObject"] = source.name
    clone["sharedInteriorRoof"] = True
    clone["webGeometrySource"] = source.get("webGeometrySource", source.name)
    clone["destinationCollection"] = DEST
    source.hide_render = True
    set_layer_hidden(source, True)
    write(
        "roof-clipping-quality.json",
        {
            "discardedNumericalSlivers": degenerate,
            "totalDiscardedArea": sum(r["area"] for r in degenerate),
            "thresholdAreaM2": 1e-4,
        },
    )
    return clone, cut, upper


def make_low_wing_rooflights(F, batches, depth):
    """Trace three source parallelograms as real openings in the slope."""
    controls = [
        [(1613.398, 672.52), (1653.0, 672.52), (1664.039, 702.52), (1624.32, 702.52)],
        [
            (1714.199, 672.52),
            (1753.801, 672.52),
            (1764.719, 702.52),
            (1725.121, 702.52),
        ],
        [(1793.281, 672.52), (1833.0, 672.52), (1843.922, 702.52), (1804.199, 702.52)],
    ]
    front_z = F.z(715.0)

    def point(x, y, index=None):
        z = F.z(y)
        d = -(depth - 0.25) * (z - front_z) / (F.z(659.801) - front_z)
        return F.point(F.s(x), d, z, index)

    def page_face(polygon, batch):
        # Split real source polygons at each GIS corner before mapping them.
        for index in range(3):
            a = 46.56 + F.prefix[index] / F.scale
            b = 46.56 + F.prefix[index + 1] / F.scale
            poly = [(Vector((x, y, 0)), []) for x, y in polygon]
            poly = clip_polygon(poly, 0, a, True)
            poly = clip_polygon(poly, 0, b, False)
            if len(poly) < 3:
                continue
            points = [point(p.x, p.y, index) for p, uv in poly]
            if (points[1] - points[0]).cross(points[2] - points[0]).z < 0:
                points.reverse()
            batch.face(points)

    # Cut the actual glass outlines from the continuous slope by partitioning
    # the drawing at their top and bottom; no opaque pane lies underneath.
    for y0, y1 in itertools.pairwise([659.801, 672.52, 702.52, 715.0]):

        def intervals(y, midpoint=(y0 + y1) / 2):
            cuts = [1570.8]
            if 672.52 - 1e-7 <= y <= 702.52 + 1e-7 and 672.52 < midpoint < 702.52:
                f = (y - 672.52) / 30.0
                for poly in controls:
                    cuts.extend(
                        [
                            poly[0][0] + (poly[3][0] - poly[0][0]) * f,
                            poly[1][0] + (poly[2][0] - poly[1][0]) * f,
                        ]
                    )
            cuts.append(1896.36)
            return [(cuts[i], cuts[i + 1]) for i in range(0, len(cuts) - 1, 2)]

        top, bottom = intervals(y0), intervals(y1)
        assert len(top) == len(bottom)
        for (a, b), (c, d) in zip(top, bottom):
            page_face([(a, y0), (b, y0), (d, y1), (c, y1)], batches["roof"])
    for lo, hi in itertools.pairwise(F.cuts(F.s(1570.8), F.s(1896.36))):
        index = F.i((lo + hi) / 2)
        batches["roof"].face(
            [
                F.point(lo, -(depth - 0.25), F.z(659.801), index),
                F.point(hi, -(depth - 0.25), F.z(659.801), index),
                F.point(hi, -depth, 20.24, index),
                F.point(lo, -depth, 20.24, index),
            ]
        )
    records = []
    for number, control in enumerate(controls, 1):
        points = [point(x, y) for x, y in control]
        normal = (points[1] - points[0]).cross(points[2] - points[0]).normalized()
        if normal.z < 0:
            normal = -normal
        glass = batches["glass"]
        index = len(glass.faces)
        # The source order is top-left/right/bottom-right/left; reverse if
        # necessary so the exposed surface normal faces out and up.
        if (points[1] - points[0]).cross(points[2] - points[0]).dot(normal) < 0:
            points.reverse()
        glass.face([p + normal * 0.006 for p in points])
        center = sum(points, Vector()) / 4
        outside = [center + (p - center) * 1.065 for p in points]
        frame_start = len(batches["frames"].faces)
        for i in range(4):
            j = (i + 1) % 4
            batches["frames"].face(
                [
                    outside[i] + normal * 0.018,
                    outside[j] + normal * 0.018,
                    points[j] + normal * 0.018,
                    points[i] + normal * 0.018,
                ]
            )
        records.append(
            {
                "name": f"low_wing_rooflight_{number}",
                "kind": "rooflight",
                "sourcePageCorners": control,
                "sourceSlopePageYBounds": [659.801, 715.0],
                "estimatedVisibleSlopeDepth": depth - 0.25,
                "estimatedHiddenReturnDepth": 0.25,
                "glassObject": glass.name,
                "glassFaceIndices": [index],
                "frameFaceIndices": list(
                    range(frame_start, len(batches["frames"].faces))
                ),
                "normal": list(normal),
                "estimatedGlassOffset": 0.006,
            }
        )
    return records


def make_source_roof(F, batches, rows, depth):
    # Historic projected silhouette and four dormers, plus modern/low-wing
    # source top profile. The hidden2.5mreturn is an explicit bounded estimate.
    boundary = [(46.56, 749.922), (483.0, 749.922)]
    a, b = F.s(46.56), F.s(483)
    bottom = F.z(749.922)
    top = 20.24
    holes = [r for r in rows if r["kind"] == "dormer"]
    xs = sorted({a, b} | {r[k] for r in holes for k in ["a", "b"]})
    zs = sorted({bottom, top} | {r[k] for r in holes for k in ["bottom", "top"]})

    def slope_d(z):
        return -depth * (z - bottom) / (top - bottom)

    for s0, s1 in itertools.pairwise(xs):
        for z0, z1 in itertools.pairwise(zs):
            if any(
                r["a"] < (s0 + s1) / 2 < r["b"]
                and r["bottom"] < (z0 + z1) / 2 < r["top"]
                for r in holes
            ):
                continue
            batches["roof"].face(
                [
                    F.point(s0, slope_d(z0), z0),
                    F.point(s1, slope_d(z0), z0),
                    F.point(s1, slope_d(z1), z1),
                    F.point(s0, slope_d(z1), z1),
                ]
            )
    for r in holes:
        stone_start = len(batches["stone"].faces)
        # Dormer fronts remain at the facade line; side cheeks join the slope
        # exactly at both sill and head rather than floating in front of it.
        for s in [r["a"], r["b"]]:
            batches["stone"].face(
                [
                    F.point(s, 0.0, r["bottom"]),
                    F.point(s, slope_d(r["bottom"]), r["bottom"]),
                    F.point(s, slope_d(r["top"]), r["top"]),
                    F.point(s, 0.0, r["top"]),
                ]
            )
        batches["stone"].face(
            [
                F.point(r["a"], 0, r["top"]),
                F.point(r["b"], 0, r["top"]),
                F.point(r["b"], slope_d(r["top"]), r["top"]),
                F.point(r["a"], slope_d(r["top"]), r["top"]),
            ]
        )
        r["stoneFaceIndices"] = list(range(stone_start, len(batches["stone"].faces)))
    # Each source-visible top control is joined to actual retained20.24mroof.
    profile = [
        (483, 650.68),
        (1416.238, 650.68),
        (1416.238, 804.879),
        (1570.8, 804.879),
        (1570.8, 715.0),
        (1896.36, 715.0),
        (1896.36, 816.398),
        (1954.199, 816.398),
    ]
    rooflights = []
    for (x0, y0), (x1, y1) in itertools.pairwise(profile):
        if x0 == 1570.8 and x1 == 1896.36:
            rooflights = make_low_wing_rooflights(F, batches, depth)
            continue
        if x1 <= x0:
            continue
        s0, s1 = F.s(x0), F.s(x1)
        cuts = F.cuts(s0, s1)
        for lo, hi in itertools.pairwise(cuts):
            z0 = F.z(y0) + (F.z(y1) - F.z(y0)) * (lo - s0) / (s1 - s0)
            z1 = F.z(y0) + (F.z(y1) - F.z(y0)) * (hi - s0) / (s1 - s0)
            i = F.i((lo + hi) / 2)
            batches["roof"].face(
                [
                    F.point(lo, 0, z0, i),
                    F.point(hi, 0, z1, i),
                    F.point(hi, -depth, 20.24, i),
                    F.point(lo, -depth, 20.24, i),
                ]
            )
    # Close only the local return ends and source height steps. These triangles
    # join the same back edge as the slope, not a separate floating roof cap.
    sections = [(0.0, bottom, 20.24), (F.s(483), bottom, 20.24)]
    for (x0, y0), (x1, y1) in itertools.pairwise(profile):
        if abs(x1 - x0) < 1e-7 and abs(y1 - y0) > 1e-7:
            sections.append((F.s(x0), F.z(y0), F.z(y1)))
    sections.append((F.s(1954.199), F.z(816.398), 20.24))
    for station, z0, z1 in sections:
        if abs(z1 - z0) < 1e-6:
            continue
        batches["roof"].face(
            [
                F.point(station, 0, z0),
                F.point(station, 0, z1),
                F.point(station, -depth, 20.24),
            ]
        )
    return boundary, profile, rooflights


def face_multiset(objects):
    result = Counter()
    for obj in objects:
        for face in obj.data.polygons:
            points = [
                list(obj.matrix_world @ obj.data.vertices[i].co) for i in face.vertices
            ]
            uvs = [
                {
                    "name": layer.name,
                    "uv": [list(layer.data[i].uv) for i in face.loop_indices],
                }
                for layer in obj.data.uv_layers
            ]
            material = obj.data.materials[face.material_index].name
            value = [points, uvs, material, list(face.normal)]
            result[
                hashlib.sha256(
                    json.dumps(value, separators=(",", ":")).encode()
                ).hexdigest()
            ] += 1
    return result


def split_shared_roof_batches(rows, rooflights):
    reference = json.loads((OUT / "batch-split-reference.json").read_text())
    originals = [bpy.data.objects[n] for n in reference["exactPreSplitFingerprints"]]
    for obj in originals:
        assert (
            object_fingerprint(obj) == reference["exactPreSplitFingerprints"][obj.name]
        ), ("Geometry changed before a bookkeeping-only split", obj.name)
    before = face_multiset(originals)
    groups = {
        "LRB258_shared_rooflight_glass": (
            "LRB258_source_SW_glass",
            {i for r in rooflights for i in r["glassFaceIndices"]},
        ),
        "LRB258_shared_rooflight_frames": (
            "LRB258_source_SW_frames",
            {i for r in rooflights for i in r["frameFaceIndices"]},
        ),
        "LRB258_shared_dormer_glass": (
            "LRB258_source_SW_historic_glass",
            {i for r in rows if r["kind"] == "dormer" for i in r["glassFaceIndices"]},
        ),
        "LRB258_shared_dormer_frames": (
            "LRB258_source_SW_frames",
            {i for r in rows if r["kind"] == "dormer" for i in r["frameFaceIndices"]},
        ),
        "LRB258_shared_dormer_cheeks": (
            "LRB258_source_SW_stone",
            {i for r in rows if r["kind"] == "dormer" for i in r["stoneFaceIndices"]},
        ),
    }

    def subset(source, indices, name):
        selected = [source.data.polygons[i] for i in sorted(indices)]
        vertices = sorted({v for face in selected for v in face.vertices})
        mapping = {old: new for new, old in enumerate(vertices)}
        mesh = bpy.data.meshes.new(name + "_mesh")
        mesh.from_pydata(
            [source.data.vertices[i].co.copy() for i in vertices],
            [],
            [tuple(mapping[i] for i in face.vertices) for face in selected],
        )
        mesh.update()
        for material in source.data.materials:
            mesh.materials.append(material)
        for layer in source.data.uv_layers:
            mesh.uv_layers.new(name=layer.name)
        for new, old in zip(mesh.polygons, selected):
            new.material_index = old.material_index
            for source_layer, new_layer in zip(source.data.uv_layers, mesh.uv_layers):
                for a, b in zip(old.loop_indices, new.loop_indices):
                    new_layer.data[b].uv = source_layer.data[a].uv
        return mesh, {old.index: new.index for old, new in zip(selected, mesh.polygons)}

    added = []
    taken = {obj.name: set() for obj in originals}
    face_targets = {}
    for name, (source_name, indices) in groups.items():
        assert indices and not (taken[source_name] & indices)
        source = bpy.data.objects[source_name]
        mesh, mapping = subset(source, indices, name)
        obj = bpy.data.objects.new(name, mesh)
        obj.matrix_world = source.matrix_world.copy()
        bpy.data.collections[DEST].objects.link(obj)
        obj["destinationCollection"] = DEST
        obj["webGeometrySource"] = name
        obj["sharedInteriorRoof"] = True
        added.append(obj)
        taken[source_name].update(indices)
        for old, new in mapping.items():
            face_targets[(source_name, old)] = (name, new)
    for source in originals:
        remaining = set(range(len(source.data.polygons))) - taken[source.name]
        assert remaining
        mesh, mapping = subset(
            source, remaining, source.name + "_retained_ordinary_facade"
        )
        oldmesh = source.data
        source.data = mesh
        for old, new in mapping.items():
            face_targets[(source.name, old)] = (source.name, new)
        assert oldmesh.users == 0
        bpy.data.meshes.remove(oldmesh)
    for row in rows + rooflights:
        original = row["glassObject"]
        # The entry-glass batch is not split; preserve its original face IDs.
        if original not in taken:
            continue
        targets = [face_targets[(original, i)] for i in row["glassFaceIndices"]]
        assert len({name for name, index in targets}) == 1
        row["glassObject"] = targets[0][0]
        row["glassFaceIndices"] = [index for name, index in targets]
    update_scene()
    after = face_multiset(originals + added)
    assert before == after, (
        "A position, UV, material, winding or normal changed during roof-only rebatching"
    )
    return added, {
        "verifiedPreSplitComponentSha256": reference["verifiedPreSplitComponentSha256"],
        "preSplitFingerprints": reference["exactPreSplitFingerprints"],
        "sourceObjects": [obj.name for obj in originals],
        "sharedObjects": [obj.name for obj in added],
        "actualFaceMultiset": dict(before),
        "faceCount": sum(before.values()),
        "unchangedFacePositionsUVMaterialsWindingNormals": True,
    }


def main():
    assert sha(BASE) == SHA and not (OUT / "component.blend").exists()
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    bpy.context.preferences.filepaths.save_version = 0
    before = capture()
    write("protected-source-state.json", before)
    plan = json.loads((OUT / "source-native-registration-plan.json").read_text())
    F = Frame(plan)
    diagnosis = json.loads((OUT / "wide-approach-diagnostic.json").read_text())
    assert all(
        not r["intersectsEntryLanding"]
        for o in diagnosis["protectedSurroundings"]
        for r in o["nearbyParts"]
    )
    rows = apertures(F)
    materials = {
        "stone": "LRB_V35_light_stone_bands",
        "brick": "LRB196_FINISH_LRB_V35_warm_brown_brick",
        "frames": "LRB196_FINISH_LRB_NEXT_LRB_V35_graphite_frames",
        "glass": "LRB233_limited_transmission_2",
        "historic_glass": "LRB233_limited_transmission_0",
        "entry_glass": "LRB233_entry_dielectric_4",
        "roof": "LRB196_FINISH_LRB_V109_cladding.001",
        "paving": "SITE172_SITE_V47_slab_2_Watkins.001",
    }
    batches = {
        key: Batch("LRB258_source_SW_" + key, mat) for key, mat in materials.items()
    }
    added, archived, retained = remove_front_components(F, diagnosis)
    # Historic masonry is lower than the modern brick wall, as drawn.
    stone_end = F.s(483)
    historic_top = F.z(749.922)
    wall_rectangle(F, batches["stone"], 0, stone_end, 0, F.z(1089.641), rows)
    wall_rectangle(F, batches["brick"], 0, stone_end, F.z(1089.641), historic_top, rows)
    for l, r in [(84.84, 234.48), (294.719, 443.762)]:
        for t, b in [(1076.922, 1089.641), (950.801, 974.199), (846.762, 860.922)]:
            batches["stone"].box(
                F, F.s(l) - 0.12, F.s(r) + 0.12, 0.1, 0.50, F.z(b), F.z(t)
            )
        for x in [l, r]:
            batches["stone"].box(
                F, F.s(x) - 0.13, F.s(x) + 0.13, 0.08, 0.44, F.z(1076.922), F.z(756.398)
            )
        for x in (
            [(134.52 + 138.719) / 2, (180.719 + 184.922) / 2]
            if l < 100
            else [(344.039 + 348.238) / 2, (390.238 + 394.441) / 2]
        ):
            batches["stone"].box(
                F,
                F.s(x) - 0.075,
                F.s(x) + 0.075,
                0.12,
                0.46,
                F.z(1076.922),
                F.z(756.398),
            )
    for t, b in [(1089.641, 1101.762), (749.922, 764.32)]:
        batches["stone"].box(F, 0, stone_end, 0.08, 0.53, F.z(b), F.z(t))
    wall_rectangle(F, batches["brick"], stone_end, F.s(1416.238), 0, 20.24, rows)
    # Upper service column and eastern wing contain cladding, not extra
    # repetitive brick windows. These zones follow the visible source outline.
    wall_rectangle(
        F, batches["brick"], F.s(1416.238), F.s(1570.8), 0, F.z(804.879), rows
    )
    wall_rectangle(
        F, batches["brick"], F.s(1570.8), F.s(1896.36), 0, F.z(816.398), rows
    )
    wall_rectangle(
        F, batches["roof"], F.s(1570.8), F.s(1896.36), F.z(816.398), F.z(715.0), rows
    )
    wall_rectangle(
        F, batches["brick"], F.s(1896.36), F.s(1954.199), 0, F.z(816.398), rows
    )
    make_windows(F, rows, batches)
    # Source Library label and shallow canopy; exact projection is estimated.
    entry = next(r for r in rows if r["name"] == "Library_lower_glazed_divisions")
    a, b = entry["a"], entry["b"]
    batches["frames"].box(F, a - 0.07, b + 0.07, 0.12, 0.48, F.z(1146.879), F.z(1144.0))
    batches["stone"].box(F, a, b, 0.11, 0.18, F.z(1113.8), F.z(1102.2))
    # Only the already established .282mthreshold difference is bridged. No
    # broad plaza, tree container, public bridge or accessible ramp is moved.
    bottom = 0.05
    ffl = 0.3319997787475586
    for step, front in [(1, 2.4), (2, 2.0), (3, 1.6)]:
        batches["paving"].box(
            F,
            a - 0.12,
            b + 0.12,
            -0.03,
            front,
            bottom - 0.01,
            bottom + (ffl - bottom) * step / 3,
        )
    supports = []
    floor_trees = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        if (
            "LRB" in obj.name
            and any(t in obj.name for t in ["floor_slabs", "gallery_carpet"])
        ) or obj.name == "SITE194_SITE_V47_John_Watkins_Plaza":
            floor_trees.append(
                (
                    obj.name,
                    BVHTree.FromPolygons(
                        [obj.matrix_world @ v.co for v in obj.data.vertices],
                        [tuple(face.vertices) for face in obj.data.polygons],
                        all_triangles=False,
                    ),
                )
            )
    for station in [a + 0.08, a + 0.6, (a + b) / 2, b - 0.6, b - 0.08]:
        for depth_probe, expected in [(-0.1, 0.332), (0.6, 0.05), (2.4, 0.05)]:
            hits = []
            for name, tree in floor_trees:
                hit = tree.ray_cast(
                    F.point(station, depth_probe, 0.8), Vector((0, 0, -1)), 1
                )
                if hit[0] is not None:
                    hits.append({"name": name, "z": hit[0].z})
            assert any(abs(hit["z"] - expected) < 0.002 for hit in hits), (
                "registered doorway support",
                station,
                depth_probe,
                hits,
            )
            supports.append(
                {
                    "station": station,
                    "depth": depth_probe,
                    "hits": hits,
                    "expectedSupportZ": expected,
                }
            )
    depth = 2.5
    roof_source = bpy.data.objects[ROOF]
    tree = BVHTree.FromPolygons(
        [roof_source.matrix_world @ v.co for v in roof_source.data.vertices],
        [tuple(f.vertices) for f in roof_source.data.polygons],
        all_triangles=False,
    )
    joins = []
    for s in [0.15, 3, 7, 11, 15, 20, 30, 40, 50, 55, 60, 65, 67.5]:
        hit = tree.ray_cast(F.point(s, -depth, 20.245), Vector((0, 0, -1)), 0.02)
        assert hit[0] is not None and abs(hit[0].z - 20.24) < 0.002, (
            "roof return support",
            s,
            hit,
        )
        joins.append({"station": s, "point": list(hit[0]), "normal": list(hit[1])})
    newroof, cuts, upper = clip_roof_strip(F, roof_source, depth)
    added.append(newroof)
    archived.append(ROOF)
    boundary, profile, rooflights = make_source_roof(F, batches, rows, depth)
    for batch in batches.values():
        obj = batch.build()
        if obj:
            added.append(obj)
    shared, shared_proof = split_shared_roof_batches(rows, rooflights)
    added.extend(shared)
    # Lettering uses the existing source font datablock when one is available.
    font = bpy.data.curves.new("LRB258_Library_label_curve", "FONT")
    font.body = "Library"
    font.size = 0.28
    font.align_x = "CENTER"
    font.extrude = 0.002
    font.resolution_u = 4
    label = bpy.data.objects.new("LRB258_source_Library_label", font)
    bpy.data.collections[DEST].objects.link(label)
    label.location = F.point((a + b) / 2, 0.195, F.z(1104.0))
    u, n = F.basis(0)
    label.matrix_world = Matrix(
        (
            (u.x, 0, n.x, label.location.x),
            (u.y, 0, n.y, label.location.y),
            (0, 1, 0, label.location.z),
            (0, 0, 0, 1),
        )
    )
    font.materials.append(bpy.data.materials[materials["frames"]])
    label["destinationCollection"] = DEST
    update_scene()
    evaluated = label.to_mesh()
    actual = [label.matrix_world @ v.co for v in evaluated.vertices]
    label.to_mesh_clear()
    low, high = F.z(1113.0) + 0.025, F.z(1102.5) - 0.025
    actual_height = max(p.z for p in actual) - min(p.z for p in actual)
    if actual_height > high - low:
        font.size *= (high - low) / actual_height
        update_scene()
        evaluated = label.to_mesh()
        actual = [label.matrix_world @ v.co for v in evaluated.vertices]
        label.to_mesh_clear()
    label.location.z += (low + high) / 2 - (
        min(p.z for p in actual) + max(p.z for p in actual)
    ) / 2
    update_scene()
    evaluated = label.to_mesh()
    evaluated.calc_loop_triangles()
    label_points = [label.matrix_world @ v.co for v in evaluated.vertices]
    normal = F.basis(0)[1]
    triangles = [
        t
        for t in evaluated.loop_triangles
        if (label.matrix_world.to_3x3() @ t.normal).normalized().dot(normal) > 0.99
    ]
    assert triangles
    sorted_triangles = sorted(
        triangles,
        key=lambda t: sum(label_points[i].dot(F.basis(0)[0]) for i in t.vertices) / 3,
    )
    label_probes = []
    for ordinal in [
        0,
        len(sorted_triangles) // 3,
        2 * len(sorted_triangles) // 3,
        len(sorted_triangles) - 1,
    ]:
        t = sorted_triangles[ordinal]
        p = sum((label_points[i] for i in t.vertices), Vector()) / 3
        label_probes.append(
            {
                "triangle": list(t.vertices),
                "point": list(p),
                "normal": list(normal),
                "origin": list(p + normal * 0.15),
            }
        )
    label_bounds = [
        [min(p[i] for p in label_points), max(p[i] for p in label_points)]
        for i in range(3)
    ]
    assert low - 1e-5 <= label_bounds[2][0] <= label_bounds[2][1] <= high + 1e-5
    label.to_mesh_clear()
    label_proof = {
        "object": label.name,
        "actualWorldBounds": label_bounds,
        "allowedZBounds": [low, high],
        "probes": label_probes,
        "sourcePageYBounds": [1102.5, 1113.0],
    }
    added.append(label)
    update_scene()
    after = capture()
    for name, row in before["objects"].items():
        expected = dict(row)
        if name in archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
        and len(before["rooms"]) == 35
    )
    assert all(after["materials"][n] == v for n, v in before["materials"].items())
    probes = []
    for row in rows + rooflights:
        obj = bpy.data.objects[row["glassObject"]]
        obj.data.calc_loop_triangles()
        triangles = [
            t
            for t in obj.data.loop_triangles
            if t.polygon_index == row["glassFaceIndices"][0]
        ]
        t = max(triangles, key=lambda t: t.area)
        point = obj.matrix_world @ (
            sum((obj.data.vertices[i].co for i in t.vertices), Vector()) / 3
        )
        normal = (obj.matrix_world.to_3x3() @ t.normal).normalized()
        probes.append(
            {
                "window": row["name"],
                "object": obj.name,
                "face": t.polygon_index,
                "triangle": list(t.vertices),
                "point": list(point),
                "normal": list(normal),
                "origin": list(point + normal * 0.08),
                "expectedMaterial": obj.data.materials[0].name,
                "expectedDistance": 0.08,
            }
        )
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), set(added), fake_user=True, compress=True)
    audit = {
        "version": 258,
        "code": "LRB",
        "baselineSha256": SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": sha(component),
        "destinationCollection": DEST,
        "targetCollection": DEST,
        "addedObjects": [o.name for o in added],
        "archivedObjects": archived,
        "changedObjects": [],
        "addedFingerprints": {o.name: object_fingerprint(o) for o in added},
        "replacementMaterialBindings": {
            o.name: [m.name for m in o.data.materials] for o in added
        },
        "replacementFontBindings": {
            label.name: {
                k: getattr(font, k).name
                for k in ["font", "font_bold", "font_italic", "font_bold_italic"]
            }
        },
        "sourceRegistration": plan,
        "windows": rows,
        "sourceRooflights": rooflights,
        "labelProof": label_proof,
        "sharedRoofBatchSplit": shared_proof,
        "glassTriangleProbes": probes,
        "retainedFacadeParts": retained,
        "lowerRoof": {
            "source": ROOF,
            "replacement": newroof.name,
            "estimatedReturnDepth": depth,
            "sourceVisibleRoof": {
                "historicPageYBounds": [650.68, 749.922],
                "lowWingPageYBounds": [659.801, 715.0],
                "lowWingRooflightPageYBounds": [672.52, 702.52],
            },
            "hiddenRoofReturn": {
                "lowWingDepth": 0.25,
                "frontSlopeDepthEstimate": 2.25,
                "retainedRoofZ": 20.24,
                "sourceMeasured": False,
            },
            "sourceCutPolygons": cuts,
            "protectedUpperFaces": upper,
            "actualSupportedJoins": joins,
            "frontSourceProfile": profile,
            "historicSourceProfile": boundary,
        },
        "geometryBudget": {
            "newMaterials": 0,
            "newObjects": len(added),
            "newMeshVertices": sum(
                len(o.data.vertices) for o in added if o.type == "MESH"
            ),
        },
        "mainEntryWorldCenter": list(F.point((a + b) / 2, 0.12, 0.332)),
        "registeredMainEntrySupportProbes": supports,
        "limitations": [
            "Source2025main-building elevation and GIS footprint differ by1.19percent; source-derived outer bay registration remains an estimate.",
            "The concealed2.5mroof-return depth is estimated and joins the actual retained20.24mplane;23.99mupper roof and dome are protected.",
            "Five lower glazed divisions and three by two upper lights are evidenced; door operating modes are not assigned.",
            "The0.282mthreshold bridge follows actual retainedFFL/paving levels; its width/tread depth remain a local model estimate, not a surveyed accessible route.",
        ],
    }
    write("audit.json", audit)
    assert sha(BASE) == SHA
    print("LRB258_COMPONENT_READY", sha(component), len(added), "objects", flush=True)


if __name__ == "__main__":
    main()
