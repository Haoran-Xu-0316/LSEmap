"""Change PAN's existing round fascia apertures to horizontal expanded-mesh diamonds.

The official historic campus-tour photograph shows horizontally long diamond
openings. Existing centres, nominal90mmcell spacing, full outer silhouette, material and UVs
are preserved. Nominal64x22mmapertures are display estimates, not a mesh survey.
No backing, glass, shader, texture, hidden elevation or room is changed.
"""

import importlib.util
import json
import math
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v255.blend"
SHA = "bcb85b059475971cc0e684597d2cc8e5081d47302e669e17d48a923ea44fb3ad"
OUT = ROOT / "result/blender/pan256"
SOURCE = "PAN_D3_perforated_entrance_fascia"
REPLACEMENT = "PAN256_horizontal_diamond_entrance_mesh"
COLLECTION = "PAN_EXTERIOR"
LONG_DIAGONAL = 0.064
SHORT_DIAGONAL = 0.022
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_col_finish252 import mesh_record, sha


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def capture():
    spec = importlib.util.spec_from_file_location(
        "pan256_protection", ROOT / "web/tests/verify_campus241.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BASE_SHA = SHA
    return module.capture_source()


def aperture_cells(obj):
    mesh = obj.data
    neighbors = defaultdict(set)
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbors[a].add(b)
        neighbors[b].add(a)
    components, visited = [], set()
    for seed in range(len(mesh.vertices)):
        if seed in visited:
            continue
        part, pending = set(), [seed]
        visited.add(seed)
        while pending:
            current = pending.pop()
            part.add(current)
            for adjacent in neighbors[current]:
                if adjacent not in visited:
                    visited.add(adjacent)
                    pending.append(adjacent)
        components.append(part)
    cells = []
    for part in components:
        assert len(part) == 16
        faces = [p for p in mesh.polygons if p.vertices[0] in part]
        assert len(faces) == 8 and all(
            all(i in part for i in p.vertices) for p in faces
        )
        counts = Counter()
        for face in faces:
            indices = list(face.vertices)
            for a, b in zip(indices, indices[1:] + indices[:1]):
                counts[tuple(sorted((a, b)))] += 1
        boundary = defaultdict(set)
        for (a, b), count in counts.items():
            if count == 1:
                boundary[a].add(b)
                boundary[b].add(a)
        assert len(boundary) == 16 and all(
            len(adjacent) == 2 for adjacent in boundary.values()
        )
        loops, seen = [], set()
        for first in sorted(boundary):
            if first in seen:
                continue
            pending, loop = [first], set()
            seen.add(first)
            while pending:
                current = pending.pop()
                loop.add(current)
                for adjacent in boundary[current]:
                    if adjacent not in seen:
                        seen.add(adjacent)
                        pending.append(adjacent)
            loops.append(sorted(loop))
        assert len(loops) == 2 and all(len(loop) == 8 for loop in loops)
        loops.sort(
            key=lambda loop: (
                max(mesh.vertices[i].co.z for i in loop)
                - min(mesh.vertices[i].co.z for i in loop)
            ),
            reverse=True,
        )
        outer, inner = loops
        outer_points = [list(obj.matrix_world @ mesh.vertices[i].co) for i in outer]
        inner_points = [list(obj.matrix_world @ mesh.vertices[i].co) for i in inner]
        outer_exact = [
            math.fsum(point[d] for point in outer_points) / 8 for d in range(3)
        ]
        inner_exact = [
            math.fsum(point[d] for point in inner_points) / 8 for d in range(3)
        ]
        actual_offset = math.sqrt(
            math.fsum((a - b) ** 2 for a, b in zip(outer_exact, inner_exact))
        )
        assert actual_offset < 1e-5
        # Fit the horizontal plane direction from all outer points rather than
        # assuming the first index is a horizontal edge midpoint.
        xx = math.fsum((point[0] - outer_exact[0]) ** 2 for point in outer_points)
        yy = math.fsum((point[1] - outer_exact[1]) ** 2 for point in outer_points)
        xy = math.fsum(
            (point[0] - outer_exact[0]) * (point[1] - outer_exact[1])
            for point in outer_points
        )
        theta = 0.5 * math.atan2(2 * xy, xx - yy)
        axis = Vector((math.cos(theta), math.sin(theta), 0))
        if axis.x < 0:
            axis = -axis
        normal = axis.cross(Vector((0, 0, 1))).normalized()
        along = [
            math.fsum((point[d] - outer_exact[d]) * axis[d] for d in range(3))
            for point in outer_points
        ]
        assert abs(max(abs(value) for value in along) - 0.044) < 1e-5
        assert (
            abs(max(abs(point[2] - outer_exact[2]) for point in outer_points) - 0.044)
            < 1e-5
        )
        assert (
            max(
                abs(
                    math.fsum((point[d] - outer_exact[d]) * normal[d] for d in range(3))
                )
                for point in outer_points
            )
            < 1e-5
        )
        phased = {}
        for index, point in zip(inner, inner_points):
            x = math.fsum((point[d] - inner_exact[d]) * axis[d] for d in range(3))
            z = point[2] - inner_exact[2]
            phase = round(math.atan2(z, x) / (math.tau / 8)) % 8
            assert phase not in phased
            phased[phase] = index
        assert set(phased) == set(range(8))
        inner = [phased[phase] for phase in range(8)]
        center = Vector(inner_exact)
        cells.append(
            {
                "outer": outer,
                "inner": inner,
                "center": center,
                "innerCenterExact": inner_exact,
                "outerCenterExact": outer_exact,
                "inheritedCenterOffsetMetres": actual_offset,
                "axis": axis,
                "normal": normal,
                "faces": [p.index for p in faces],
            }
        )
    assert len(cells) == 910
    return cells


def next_float32(value, direction):
    """One representable storage step; all fascia coordinates are nonzero."""
    assert math.isfinite(value) and value != 0
    bits = struct.unpack("I", struct.pack("f", value))[0]
    bits += 1 if (value > 0) == (direction > 0) else -1
    return struct.unpack("f", struct.pack("I", bits))[0]


def preserve_inner_center(source, obj, cell):
    """Distribute final float32 rounding steps without moving the original centre."""
    for coordinate in range(3):
        target = math.fsum(
            source.data.vertices[i].co[coordinate] for i in cell["inner"]
        )
        steps = 0
        while True:
            total = math.fsum(
                obj.data.vertices[i].co[coordinate] for i in cell["inner"]
            )
            if total == target:
                break
            direction = 1 if target > total else -1
            candidates = []
            for vertex_index in cell["inner"]:
                point = list(obj.data.vertices[vertex_index].co)
                old = point[coordinate]
                point[coordinate] = next_float32(old, direction)
                if abs(target - total - (point[coordinate] - old)) >= abs(
                    target - total
                ):
                    continue
                plane_error = abs(
                    math.fsum(
                        (point[d] - cell["center"][d]) * cell["normal"][d]
                        for d in range(3)
                    )
                )
                candidates.append((plane_error, vertex_index, point))
            assert candidates, "Original stored centre is not representable"
            _, vertex_index, point = min(candidates, key=lambda row: row[0])
            obj.data.vertices[vertex_index].co = point
            steps += 1
            assert steps < 64


def fascia_joint_layout(source, cells):
    """Infer adjacency from the actual original cells; never author a new grid."""
    centers = [cell["outerCenterExact"] for cell in cells]
    mean = [math.fsum(point[d] for point in centers) / len(centers) for d in range(3)]
    xx = math.fsum((point[0] - mean[0]) ** 2 for point in centers)
    yy = math.fsum((point[1] - mean[1]) ** 2 for point in centers)
    xy = math.fsum((point[0] - mean[0]) * (point[1] - mean[1]) for point in centers)
    theta = 0.5 * math.atan2(2 * xy, xx - yy)
    axis = (math.cos(theta), math.sin(theta), 0)
    rows = []
    for index in sorted(range(len(cells)), key=lambda i: centers[i][2]):
        if not rows or abs(centers[index][2] - centers[rows[-1][0]][2]) > 1e-5:
            rows.append([])
        rows[-1].append(index)
    assert len(rows) == 7 and all(len(row) == 130 for row in rows)
    for row in rows:
        row.sort(key=lambda i: math.fsum(centers[i][d] * axis[d] for d in range(3)))
    nodes = defaultdict(list)
    horizontal_steps, vertical_steps = [], []
    for row_index, row in enumerate(rows):
        for column, index in enumerate(row):
            center = centers[index]
            if column:
                horizontal_steps.append(
                    math.fsum(
                        (center[d] - centers[row[column - 1]][d]) * axis[d]
                        for d in range(3)
                    )
                )
            if row_index:
                vertical_steps.append(
                    center[2] - centers[rows[row_index - 1][column]][2]
                )
            for vertex_index in cells[index]["outer"]:
                point = source.data.vertices[vertex_index].co
                x = math.fsum((point[d] - center[d]) * axis[d] for d in range(3))
                z = point.z - center[2]
                sx, sz = round(x / 0.044), round(z / 0.044)
                assert sx in [-1, 0, 1] and sz in [-1, 0, 1] and (sx or sz)
                assert abs(x - sx * 0.044) < 1e-5 and abs(z - sz * 0.044) < 1e-5
                nodes[(2 * column + sx, 2 * row_index + sz)].append(vertex_index)
    assert all(abs(step - 0.09) < 1e-5 for step in horizontal_steps + vertical_steps)
    targets = {
        key: tuple(
            math.fsum(source.data.vertices[i].co[d] for i in indices) / len(indices)
            for d in range(3)
        )
        for key, indices in nodes.items()
    }
    return {
        "rows": rows,
        "axis": axis,
        "nodes": nodes,
        "targets": targets,
        "horizontalSpacingRange": [min(horizontal_steps), max(horizontal_steps)],
        "verticalSpacingRange": [min(vertical_steps), max(vertical_steps)],
    }


def close_internal_cell_joints(source, obj, cells):
    layout = fascia_joint_layout(source, cells)
    for key, indices in layout["nodes"].items():
        # This is the mean of actual opposing endpoints. At a four-cell joint
        # all four original corners meet; no extra plate or regular-grid point.
        for index in indices:
            obj.data.vertices[index].co = layout["targets"][key]
    obj.data.update()


def joint_geometry_proof(source, obj, cells):
    layout = fascia_joint_layout(source, cells)
    displaced = []
    internal_nodes = boundary_nodes = 0
    for key, indices in layout["nodes"].items():
        expected = Vector(layout["targets"][key])
        assert all(obj.data.vertices[i].co == expected for i in indices)
        boundary_x = key[0] in [-1, 259]
        boundary_z = key[1] in [-1, 13]
        if len(indices) > 1:
            if boundary_x or boundary_z:
                boundary_nodes += 1
            else:
                internal_nodes += 1
        if boundary_z:
            assert all(
                obj.data.vertices[i].co.z == source.data.vertices[i].co.z
                for i in indices
            )
        if boundary_x:
            assert all(
                tuple(obj.data.vertices[i].co.xy)
                == tuple(source.data.vertices[i].co.xy)
                for i in indices
            )
        if boundary_x and boundary_z:
            assert all(
                obj.data.vertices[i].co == source.data.vertices[i].co for i in indices
            )
        displaced.extend(
            (obj.data.vertices[i].co - source.data.vertices[i].co).length
            for i in indices
        )
    # Prove that outer rectangles touch but do not overlap. Adjacent intervals
    # share exact vertices; ordering then separates every nonadjacent cell too.
    bounds = {}
    axis = layout["axis"]
    for index, cell in enumerate(cells):
        points = [obj.data.vertices[i].co for i in cell["outer"]]
        along = [math.fsum(point[d] * axis[d] for d in range(3)) for point in points]
        bounds[index] = (
            min(along),
            max(along),
            min(point.z for point in points),
            max(point.z for point in points),
        )
    shared_interfaces = 0
    for row_index, row in enumerate(layout["rows"]):
        for column, index in enumerate(row):
            if column:
                assert bounds[row[column - 1]][1] <= bounds[index][0] + 1e-10
                shared_interfaces += 1
            if row_index:
                assert (
                    bounds[layout["rows"][row_index - 1][column]][3]
                    <= bounds[index][2] + 1e-10
                )
                shared_interfaces += 1
    original_outer = [
        source.data.vertices[i].co for cell in cells for i in cell["outer"]
    ]
    current_outer = [obj.data.vertices[i].co for cell in cells for i in cell["outer"]]
    assert [
        [min(p[d] for p in original_outer), max(p[d] for p in original_outer)]
        for d in range(3)
    ] == [
        [min(p[d] for p in current_outer), max(p[d] for p in current_outer)]
        for d in range(3)
    ]
    assert max(displaced) < 0.00143
    return {
        "rows": 7,
        "columns": 130,
        "actualHorizontalCenterSpacingRangeMetres": layout["horizontalSpacingRange"],
        "actualVerticalCenterSpacingRangeMetres": layout["verticalSpacingRange"],
        "sharedInternalNodes": internal_nodes,
        "perimeterTangentialJointNodes": boundary_nodes,
        "verifiedNonoverlappingInterfaces": shared_interfaces,
        "maximumOuterVertexDisplacementMetres": max(displaced),
        "fullOuterBoundsAndFourCornersExact": True,
        "sharedVertexCoordinatesBitEqual": True,
        "noNewFacesVerticesOrCornerPlates": True,
    }


def retain_checks(source, obj, cells):
    original, replacement = mesh_record(source), mesh_record(obj)
    assert all(
        original[key] == value
        for key, value in replacement.items()
        if key != "vertices"
    )
    outer = {index for cell in cells for index in cell["outer"]}
    changed = [
        v.index for v in obj.data.vertices if v.co != source.data.vertices[v.index].co
    ]
    inner = {index for cell in cells for index in cell["inner"]}
    assert inner.issubset(set(changed)) and not inner.intersection(outer)
    assert set(changed).issubset(inner | outer)
    joints = joint_geometry_proof(source, obj, cells)
    assert [m.name for m in source.data.materials] == [
        m.name for m in obj.data.materials
    ]
    center_errors = []
    for cell in cells:
        original_sum = [
            math.fsum(source.data.vertices[i].co[d] for i in cell["inner"])
            for d in range(3)
        ]
        replacement_sum = [
            math.fsum(obj.data.vertices[i].co[d] for i in cell["inner"])
            for d in range(3)
        ]
        assert replacement_sum == original_sum, "Original aperture centre changed"
        center_errors.append(
            max(abs(a - b) for a, b in zip(original_sum, replacement_sum)) / 8
        )
    assert not source.modifiers and not obj.modifiers
    return {
        "outerVertices": len(outer),
        "unchangedOuterVertices": sum(
            obj.data.vertices[i].co == source.data.vertices[i].co for i in outer
        ),
        "cellJoints": joints,
        "changedInnerVertices": len(inner),
        "changedOuterVertices": len(set(changed) & outer),
        "originalVertices": len(source.data.vertices),
        "originalPolygons": len(source.data.polygons),
        "allUVTopologyFaceMaterialsAndTransformExact": True,
        "maximumInnerCenterChangeMetres": max(center_errors),
        "maximumInheritedInnerOuterCenterOffsetMetres": max(
            cell["inheritedCenterOffsetMetres"] for cell in cells
        ),
    }


def aperture_geometry_proof(obj, cells):
    """Check the mesh itself, never the original opaque backing behind it."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    vertices = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
    for cell in cells:
        center, axis, normal = [cell[key] for key in ["center", "axis", "normal"]]
        positions = [vertices[index] for index in cell["inner"]]
        assert max(abs((p - center).dot(normal)) for p in positions) < 1e-5
        # A convex horizontal diamond with four collinear edge midpoints.
        cross_products = []
        points = [((p - center).dot(axis), p.z - center.z) for p in positions]
        for index in range(8):
            a, b, c = [points[(index + offset) % 8] for offset in [0, 1, 2]]
            cross_products.append(
                (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            )
        assert min(cross_products) > -1e-6
        for x, z in points:
            assert (
                abs(abs(x) / (LONG_DIAGONAL / 2) + abs(z) / (SHORT_DIAGONAL / 2) - 1)
                < 0.001
            )
        hit, _, _, _ = tree.ray_cast(center - normal * 0.03, normal, 0.06)
        assert hit is None, "Hole centre blocked by fascia itself"
    # No degenerate or inverted ring triangles are allowed.
    for triangle in mesh.loop_triangles:
        a, b, c = [vertices[index] for index in triangle.vertices]
        cross = (b - a).cross(c - a)
        assert cross.length > 1e-7
        cell = cells[triangle.polygon_index // 8]
        assert cross.normalized().dot(cell["normal"]) > 0.999, (
            "Inverted or folded ring triangle"
        )
    representatives = []
    for cell_index in [0, 65, 130, 260, 455, 650, 845, 909]:
        cell = cells[cell_index]
        center, normal = cell["center"], cell["normal"]
        triangle = next(
            t for t in mesh.loop_triangles if t.polygon_index == cell["faces"][0]
        )
        metal_center = (
            sum((vertices[index] for index in triangle.vertices), Vector()) / 3
        )
        metal_origin = metal_center - normal * 0.03
        hit, _, _, distance = tree.ray_cast(metal_origin, normal, 0.06)
        assert hit is not None and 0.0299 < distance < 0.0301
        representatives.append(
            {
                "cellIndex": cell_index,
                "planeNormal": list(normal),
                "outwardNormal": list(-normal),
                "holeCenter": list(center),
                "holeRayOrigin": list(center - normal * 0.03),
                "direction": list(normal),
                "rayLimitMetres": 0.06,
                "expectedFasciaPlaneDistanceMetres": 0.03,
                "metalTriangleCenter": list(metal_center),
                "metalRayOrigin": list(metal_origin),
                "metalHitDistanceMetres": distance,
                "scope": "Fascia-only mesh rays; later backing is not counted as fascia closure",
            }
        )
    assert len(mesh.loop_triangles) == 14560
    return {
        "aperturesVerified": len(cells),
        "holeCentersClearOfFascia": True,
        "meshTriangles": len(mesh.loop_triangles),
        "representatives": representatives,
    }


def check_protection(before, after):
    for name, row in before["objects"].items():
        expected = dict(row)
        if name == SOURCE:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(
        after["materials"][name] == value for name, value in before["materials"].items()
    )
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert len(before["rooms"]) == 35


def main():
    assert sha(BASE) == SHA
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "component.blend").exists()
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.preferences.filepaths.save_version = 0
    update_scene()
    protected = capture()
    write("protected-source-state.json", protected)
    source = bpy.data.objects[SOURCE]
    assert not source.hide_render and len(source.data.materials) == 1
    cells = aperture_cells(source)
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = REPLACEMENT
    obj.data.name = REPLACEMENT + "_mesh"
    obj["originalObject"] = SOURCE
    obj["webGeometrySource"] = source.get("webGeometrySource", SOURCE)
    obj["destinationCollection"] = COLLECTION
    obj["sourceScope"] = (
        "Horizontal expanded-mesh hole type from historical official photo; dimensions estimated"
    )
    bpy.data.collections[COLLECTION].objects.link(obj)
    assert obj.matrix_world == Matrix.Identity(4)
    for cell in cells:
        for index, vertex_index in enumerate(cell["inner"]):
            angle = index * math.tau / 8
            cosine, sine = math.cos(angle), math.sin(angle)
            divisor = abs(cosine) + abs(sine)
            horizontal = LONG_DIAGONAL / 2 * cosine / divisor
            vertical = SHORT_DIAGONAL / 2 * sine / divisor
            # Python float arithmetic avoids large-coordinate float32 Vector
            # accumulation. Preserve each inherited inner centre, not outer mean.
            obj.data.vertices[vertex_index].co = tuple(
                cell["innerCenterExact"][d]
                + cell["axis"][d] * horizontal
                + (vertical if d == 2 else 0)
                for d in range(3)
            )
        preserve_inner_center(source, obj, cell)
    close_internal_cell_joints(source, obj, cells)
    obj.data.update()
    obj.hide_render = False
    set_layer_hidden(obj, False)
    source.hide_render = True
    set_layer_hidden(source, True)
    update_scene()
    retained = retain_checks(source, obj, cells)
    geometry = aperture_geometry_proof(obj, cells)
    check_protection(protected, capture())
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), {obj}, fake_user=True, compress=True)
    photo = ROOT / "data/collections/tower_photos_round4/images/PAN/tour_p16_0.png"
    write(
        "audit.json",
        {
            "version": 256,
            "building": "PAN",
            "baseline": str(BASE.relative_to(ROOT)),
            "baselineSha256": SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": sha(component),
            "destinationCollection": COLLECTION,
            "addedObjects": [REPLACEMENT],
            "archivedObjects": [SOURCE],
            "changedObjects": [],
            "addedFingerprints": {REPLACEMENT: object_fingerprint(obj)},
            "replacementMaterialBindings": {
                REPLACEMENT: [m.name for m in obj.data.materials]
            },
            "newMaterials": [],
            "newMaterialGraphs": {},
            "retainNewMaterials": True,
            "geometryPreservation": retained,
            "apertureGeometry": geometry,
            "longDiagonalEstimateMetres": LONG_DIAGONAL,
            "shortDiagonalEstimateMetres": SHORT_DIAGONAL,
            "longAxis": "horizontal within fascia plane; diamond edges diagonal",
            "inheritedCellSizeMetres": 0.088,
            "sourceRefs": [
                {
                    "path": str(photo.relative_to(ROOT)),
                    "sha256": sha(photo),
                    "url": "https://info.lse.ac.uk/current-students/your-first-weeks/assets/documents/self-guided-campus-tour.pdf",
                    "date": "undated photograph and guide; no2026current-condition claim",
                    "supports": "Horizontally elongated diamond/open expanded-mesh silver fascia, rather than round punctures",
                    "crop": "result/blender/pan256/fascia-source-crop.png",
                    "sourceCropBox": [480, 176, 680, 219],
                }
            ],
            "limitations": [
                "Hole shape and measured2mmcell gaps are corrected; source88mmring cells at90mmcentres join at opposing endpoint midlines. Overall silhouette stays exact; no surveyed mesh pitch is claimed.",
                "64x22mmhole dimensions are display estimates; no exact architectural product or gauge is claimed.",
                "All original materials/UVs remain; no black decals, shader, texture, backing or optical change.",
                "Physical apertures are proved through the ring mesh itself; original ground_head remains behind the fascia. Internal cell edges meet exactly with no new plates or overlapping outer polygons.",
            ],
        },
    )
    assert sha(BASE) == SHA
    print("PAN256_COMPONENT_SAVED", sha(component), flush=True)


if __name__ == "__main__":
    main()
