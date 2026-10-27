"""Author a bounded Lindsey House street facade inside the retained275shell.

main('prepare') creates and CPU-checks a fixed face plan in MachineLearning.
main('build') writes a separate Blender component. Two mapped front quads only
are replaced; all other walls, roof, roads, datum and native materials survive.
"""

import hashlib
import importlib.util
import json
import math
import os
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/street277"
BASE = ROOT / "result/blender/LSE_campus_detailed_v275.blend"
SHA = "18a60235fd7c71c6c2864690c574f97b66a9d05577e0c584c626dee41829a4f9"
OWNER = "01_CITY_CONTEXT_estimated_heights"
PREFIX = "LINDSEY277_"
STAGE = "build"
SOURCE_NAMES = ["Context_way/181939019_wall_0_3", "Context_way/181939019_wall_0_4"]
MATERIALS = [
    PREFIX + "stucco_field",
    PREFIX + "scored_stucco_base",
    "RCS224_trim",
    "RCS224_glass",
    "RCS224_back",
    "RCS224_dark",
]


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def f32(point):
    return list(struct.unpack("fff", struct.pack("fff", *point)))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def prepare():
    import numpy as np
    from shapely import constrained_delaunay_triangles
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union

    native = json.loads((OUT / "native-inspection.json").read_text())
    assert native["baselineSha256"] == SHA
    sources = {r["name"]: r for r in native["targetOriginalObjects"]}
    assert all(sources[n]["renderEligibleInCompleteCampus"] for n in SOURCE_NAMES)
    south = np.array(sources[SOURCE_NAMES[1]]["verticesWorld"][1][:2])
    joint = np.array(sources[SOURCE_NAMES[1]]["verticesWorld"][0][:2])
    north = np.array(sources[SOURCE_NAMES[0]]["verticesWorld"][0][:2])
    endpoints = [south, joint, north]
    lengths = [
        float(np.linalg.norm(b - a))
        for a, b in zip(endpoints, endpoints[1:], strict=False)
    ]
    split, length = lengths[0], sum(lengths)
    tangents = [
        (b - a) / size
        for a, b, size in zip(endpoints, endpoints[1:], lengths, strict=False)
    ]
    normals = [np.array([t[1], -t[0]]) for t in tangents]
    middle = (normals[0] + normals[1]) / (1 + normals[0] @ normals[1])
    # End faces follow the retained party-wall planes. A perpendicular offset
    # at the mapped south corner would leave a1mm wedge outside its footprint.
    south_side = (
        np.array(sources["Context_way/181939019_wall_0_0"]["verticesWorld"][0][:2])
        - south
    )
    north_side = (
        np.array(sources["Context_way/181939019_wall_0_2"]["verticesWorld"][0][:2])
        - north
    )
    offsets = [
        south_side / (south_side @ normals[0]),
        middle,
        north_side / (north_side @ normals[1]),
    ]
    height = sources[SOURCE_NAMES[0]]["worldBounds"][1][2]
    assert height == 17 and sources[SOURCE_NAMES[1]]["worldBounds"][1][2] == height

    def point(s, depth, z):
        segment = 0 if s <= split else 1
        start = 0 if segment == 0 else split
        t = (s - start) / lengths[segment]
        xy = (
            endpoints[segment] * (1 - t)
            + endpoints[segment + 1] * t
            + depth * (offsets[segment] * (1 - t) + offsets[segment + 1] * t)
        )
        return f32((*xy, z))

    # SourcePhotoA: facade limits714/1393px; source feature coordinates are
    # proportions only. The native17mheight is inherited, not photographed metres.
    def x(pixel):
        return (pixel - 714) / (1393 - 714) * length

    def z(pixel):
        return (703 - pixel) / (703 - 148) * height

    centres = [x(v) for v in [795, 921, 1047, 1176, 1299]]
    openings = []
    for row, top, bottom, width in [
        ("ground", 565, 651, 53),
        ("principal", 399, 523, 65),
        ("upper", 263, 339, 62),
    ]:
        for column, centre in enumerate(centres):
            if row == "ground" and column == 2:
                continue
            w = x(714 + width)
            low, high = z(bottom), z(top)
            if row == "upper" and column == 2:
                w, low, high = x(714 + 50), z(329), z(270)
            openings.append(
                {
                    "id": f"{row}-{column}",
                    "kind": "window",
                    "row": row,
                    "column": column,
                    "x": centre,
                    "width": w,
                    "z0": low,
                    "z1": high,
                    "columns": 2 if row == "upper" and column == 2 else 3,
                    "rows": 2 if row == "upper" and column == 2 else 4,
                }
            )
    for i, pixel in enumerate([1022, 1071]):
        openings.append(
            {
                "id": f"door-{i}",
                "kind": "door",
                "row": "ground",
                "column": 2,
                "x": x(pixel),
                "width": x(714 + 39),
                "z0": 0.08,
                "z1": z(571),
                "spring": z(601),
            }
        )
    masks = [
        box(o["x"] - o["width"] / 2, o["z0"], o["x"] + o["width"] / 2, o["z1"])
        for o in openings
    ]
    cut = unary_union(masks)
    domain = box(0, 0, length, height).difference(cut)
    assert (
        domain.geom_type == "Polygon"
        and len(domain.interiors) == 16
        and len(openings) == 16
    )
    batches = {
        name: {"name": PREFIX + name, "solids": []}
        for name in [
            "closed_front_wall",
            "orders_and_sash",
            "glazing",
            "opaque_recesses",
        ]
    }

    def boundary_split(ring):
        result = []
        for a, b in zip(ring, ring[1:] + ring[:1], strict=True):
            result.append(a)
            if (a[0] - split) * (b[0] - split) < -1e-12:
                t = (split - a[0]) / (b[0] - a[0])
                result.append((split, a[1] + t * (b[1] - a[1])))
        return result

    def solid(batch, shape, back, front, slot, role, tag=None):
        if shape.is_empty:
            return
        assert shape.geom_type == "Polygon" and shape.area > 1e-8
        vertices, faces, lookup = [], [], {}

        def index(s, d, h):
            key = (round(s, 9), round(d, 9), round(h, 9))
            if key not in lookup:
                lookup[key] = len(vertices)
                vertices.append(
                    {"world": point(s, d, h), "uv": [s, h], "facade": [s, d, h]}
                )
            return lookup[key]

        # Hard split at the existingGISbend. No triangle spans an invented
        # straight facade plane; inner corners use the exact parallel miter.
        for bounds in [(0, split), (split, length)]:
            part = shape.intersection(box(bounds[0], -1, bounds[1], height + 1))
            if part.is_empty:
                continue
            for tri in constrained_delaunay_triangles(part).geoms:
                ring = list(tri.exterior.coords)[:3]
                if Polygon(ring).area < 1e-10:
                    continue
                signed = sum(
                    a[0] * b[1] - b[0] * a[1]
                    for a, b in zip(ring, ring[1:] + ring[:1], strict=True)
                )
                if signed < 0:
                    ring.reverse()
                faces.append([index(s, front, h) for s, h in ring])
                faces.append([index(s, back, h) for s, h in reversed(ring)])
        for ring_index, ring in enumerate([shape.exterior, *shape.interiors]):
            points = list(ring.coords)[:-1]
            signed = sum(
                a[0] * b[1] - b[0] * a[1]
                for a, b in zip(points, points[1:] + points[:1], strict=True)
            )
            if (signed > 0) != (ring_index == 0):
                points.reverse()
            boundary = boundary_split(points)
            for a, b in zip(boundary, boundary[1:] + boundary[:1], strict=True):
                faces.extend(
                    [
                        [
                            index(b[0], front, b[1]),
                            index(a[0], front, a[1]),
                            index(a[0], back, a[1]),
                        ],
                        [
                            index(b[0], front, b[1]),
                            index(a[0], back, a[1]),
                            index(b[0], back, b[1]),
                        ],
                    ]
                )
        # Orient the complete closed solid from its actual rounded world mesh.
        centre = np.mean([v["world"] for v in vertices], axis=0)
        volume = sum(
            float(
                (np.array(vertices[f[0]]["world"]) - centre)
                @ np.cross(
                    np.array(vertices[f[1]]["world"]) - centre,
                    np.array(vertices[f[2]]["world"]) - centre,
                )
            )
            / 6
            for f in faces
        )
        if volume < 0:
            faces = [list(reversed(f)) for f in faces]
        batches[batch]["solids"].append(
            {
                "role": role,
                "tag": tag,
                "slot": slot,
                "vertices": vertices,
                "faces": faces,
            }
        )

    # Splitting at the base-band height keeps procedural scored-stucco UVs
    # independent from the upper field, with no added image texture or brickwork.
    base_height = z(549)
    for shape, slot in [
        (domain.intersection(box(0, 0, length, base_height)), 1),
        (domain.intersection(box(0, base_height, length, height)), 0),
    ]:
        if shape.geom_type == "Polygon":
            solid("closed_front_wall", shape, -0.36, -0.12, slot, "wall-core")
        else:
            for part in shape.geoms:
                solid("closed_front_wall", part, -0.36, -0.12, slot, "wall-core")

    def rect(batch, s0, s1, h0, h1, back, front, slot, role, tag=None):
        assert s1 > s0 and h1 > h0
        solid(batch, box(s0, h0, s1, h1), back, front, slot, role, tag)

    def bar(a, b, width, back, front, role, tag=None):
        a, b = np.array(a), np.array(b)
        normal = np.array([-(b - a)[1], (b - a)[0]])
        normal = normal / np.linalg.norm(normal) * width / 2
        shape = Polygon([a + normal, b + normal, b - normal, a - normal])
        solid("orders_and_sash", shape, back, front, 2, role, tag)

    # Main horizontal articulation; all relief is sunk inside the old envelope.
    for lo, hi, front in [
        (0.08, 0.34, -0.015),
        (base_height - 0.18, base_height + 0.08, 0),
        (z(540), z(531), -0.025),
        (z(240), z(225), -0.035),
        (z(224), z(205), -0.015),
        (z(204), z(190), 0),
        (z(185), z(177), -0.025),
    ]:
        rect(
            "orders_and_sash",
            0.02,
            length - 0.02,
            lo,
            hi,
            -0.15,
            front,
            2,
            "horizontal-order",
        )
    piers = [
        0.34,
        *[(a + b) / 2 for a, b in zip(centres, centres[1:], strict=False)],
        length - 0.34,
    ]
    for centre in piers:
        rect(
            "orders_and_sash",
            centre - 0.20,
            centre + 0.20,
            base_height + 0.14,
            z(247),
            -0.16,
            -0.025,
            2,
            "upper-pilaster",
        )
        for bottom, top, width in [
            (base_height + 0.08, base_height + 0.25, 0.57),
            (z(255), z(242), 0.62),
        ]:
            rect(
                "orders_and_sash",
                centre - width / 2,
                centre + width / 2,
                bottom,
                top,
                -0.17,
                -0.005,
                2,
                "pilaster-base-cap",
            )
    glazing_records = []
    for opening in openings:
        cx, width, low, high, tag = (
            opening["x"],
            opening["width"],
            opening["z0"],
            opening["z1"],
            opening["id"],
        )
        rect(
            "opaque_recesses",
            cx - width / 2 - 0.055,
            cx + width / 2 + 0.055,
            low - 0.035,
            high + 0.035,
            -0.435,
            -0.355,
            4,
            "opaque-recess-backing",
            tag,
        )
        for side in (-1, 1):
            rect(
                "orders_and_sash",
                cx + side * (width / 2 - 0.02) - 0.06,
                cx + side * (width / 2 - 0.02) + 0.06,
                low,
                high,
                -0.30,
                -0.07,
                2,
                "opening-side-frame",
                tag,
            )
        for centre in (low + 0.02, high - 0.02):
            rect(
                "orders_and_sash",
                cx - width / 2,
                cx + width / 2,
                centre - 0.055,
                centre + 0.055,
                -0.30,
                -0.07,
                2,
                "opening-head-sill",
                tag,
            )
        if opening["kind"] == "window":
            rect(
                "glazing",
                cx - width / 2 + 0.05,
                cx + width / 2 - 0.05,
                low + 0.05,
                high - 0.05,
                -0.29,
                -0.255,
                3,
                "window-glass",
                tag,
            )
            glazing_records.append(
                {
                    "id": tag,
                    "shape": list(
                        box(
                            cx - width / 2 + 0.05,
                            low + 0.05,
                            cx + width / 2 - 0.05,
                            high - 0.05,
                        ).exterior.coords
                    )[:-1],
                    "frontDepth": -0.255,
                }
            )
            for j in range(1, opening["columns"]):
                s = cx - width / 2 + width * j / opening["columns"]
                rect(
                    "orders_and_sash",
                    s - 0.014,
                    s + 0.014,
                    low + 0.03,
                    high - 0.03,
                    -0.27,
                    -0.23,
                    2,
                    "sash-muntin",
                    tag,
                )
            for j in range(1, opening["rows"]):
                h = low + (high - low) * j / opening["rows"]
                rail = 0.045 if j * 2 == opening["rows"] else 0.025
                rect(
                    "orders_and_sash",
                    cx - width / 2 + 0.03,
                    cx + width / 2 - 0.03,
                    h - rail / 2,
                    h + rail / 2,
                    -0.27,
                    -0.23,
                    2,
                    "sash-meeting-rail",
                    tag,
                )
            if opening["row"] == "principal":
                base, top = high + 0.14, high + 0.63
                rect(
                    "orders_and_sash",
                    cx - width / 2 - 0.14,
                    cx + width / 2 + 0.14,
                    base - 0.08,
                    base + 0.05,
                    -0.16,
                    -0.005,
                    2,
                    "window-pediment-base",
                    tag,
                )
                if opening["column"] == 2:
                    points = [
                        (
                            cx + (width / 2 + 0.12) * math.cos(t),
                            base + 0.46 * math.sin(t),
                        )
                        for t in np.linspace(0, math.pi, 9)
                    ]
                    for a, b in zip(points, points[1:], strict=False):
                        bar(a, b, 0.09, -0.16, -0.005, "central-curved-pediment", tag)
                else:
                    bar(
                        (cx - width / 2 - 0.12, base),
                        (cx, top),
                        0.085,
                        -0.16,
                        -0.005,
                        "triangular-pediment",
                        tag,
                    )
                    bar(
                        (cx, top),
                        (cx + width / 2 + 0.12, base),
                        0.085,
                        -0.16,
                        -0.005,
                        "triangular-pediment",
                        tag,
                    )
        else:
            spring = opening["spring"]
            rect(
                "opaque_recesses",
                cx - width / 2 + 0.035,
                cx + width / 2 - 0.035,
                low + 0.04,
                spring - 0.035,
                -0.31,
                -0.25,
                5,
                "static-door-leaf",
                tag,
            )
            radius = width / 2 - 0.06
            arc = [
                (cx + radius * math.cos(t), spring + radius * math.sin(t))
                for t in np.linspace(0, math.pi, 13)
            ]
            shape = Polygon(arc)
            solid("glazing", shape, -0.29, -0.255, 3, "door-fanlight", tag)
            glazing_records.append(
                {
                    "id": tag,
                    "shape": list(shape.exterior.coords)[:-1],
                    "frontDepth": -0.255,
                }
            )
            for a, b in zip(arc, arc[1:], strict=False):
                bar(a, b, 0.025, -0.275, -0.23, "fanlight-arc", tag)
            for theta in [
                math.pi / 5,
                2 * math.pi / 5,
                3 * math.pi / 5,
                4 * math.pi / 5,
            ]:
                bar(
                    (cx, spring),
                    (cx + radius * math.cos(theta), spring + radius * math.sin(theta)),
                    0.018,
                    -0.275,
                    -0.23,
                    "fanlight-spoke",
                    tag,
                )
    sources_to_hash = [
        "result/blender/street277/native-inspection.json",
        "result/blender/street277/scope-audit.json",
        "result/blender/street277/sources/garden-court-owner-factsheet.pdf",
        "result/blender/street277/sources/owner-photo-A-000.jpg",
        "web/tools/refine_lindsey277.py",
        "web/tests/verify_lindsey277.py",
        "web/tests/verify_lindsey277_cpu.py",
        "web/tools/review_lindsey277.py",
    ]
    plan = {
        "baselineSha256": SHA,
        "owner": OWNER,
        "sourceObjects": SOURCE_NAMES,
        "sourceFingerprints": {n: sources[n]["fingerprint"] for n in SOURCE_NAMES},
        "roofObject": "Context_way/181939019_roof",
        "roofFingerprint": sources["Context_way/181939019_roof"]["fingerprint"],
        "frontPolyline": [list(p) for p in endpoints],
        "segmentLengths": lengths,
        "breakS": split,
        "lengthM": length,
        "inheritedHeightM": height,
        "openings": openings,
        "glazingRecords": glazing_records,
        "pierCentres": piers,
        "batches": list(batches.values()),
        "materials": MATERIALS,
        "newMaterialNames": MATERIALS[:2],
        "baseBandHeight": base_height,
        "sourcePixelControls": {
            "photoFacadeX": [714, 1393],
            "photoNativeBaseAndParapetY": [703, 148],
            "axesX": [795, 921, 1047, 1176, 1299],
        },
        "sourceHashes": {p: sha(ROOT / p) for p in sources_to_hash},
        "limits": [
            "Five axes/three main facade zones and finish from ownerPhotoA; dimensions retain native17mproxy height.",
            "Fine sash grids and moulding sections are estimates, not surveyed joinery.",
            "Roof/attic/dormers/railings and unseen rear are retained as proxies, not reconstructed.",
            "Dark finite recess backings are contextual enclosure proxies, not rooms or an operating entrance.",
        ],
    }
    write(OUT / "plan.json", plan)
    verifier = load_module("lindsey277_cpu", "web/tests/verify_lindsey277.py")
    cpu = verifier.cpu_proof(plan)
    write(OUT / "cpu-preflight.json", cpu)
    print("LINDSEY277_PLAN_READY", cpu["triangles"], len(plan["openings"]), flush=True)


def capture():
    from refine_houghton262 import capture as original_capture

    value = original_capture()
    value["baselineSha256"] = SHA
    return value


def protect(before, added=(), archived=(), new_materials=None):
    after = capture()
    for name, value in before["objects"].items():
        expected = dict(value)
        if name in archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
        assert after["visibility"][name] == (
            [True, before["visibility"][name][1], True]
            if name in archived
            else before["visibility"][name]
        ), name
    assert set(after["objects"]) == set(before["objects"]) | set(added)
    assert after["materials"] == before["materials"] | (new_materials or {})
    assert after["rooms"] == before["rooms"] and len(after["rooms"]) == 35
    assert after["campusRooms"] == before["campusRooms"] and sha(BASE) == SHA


def new_materials():
    import bpy

    for index, name in enumerate(MATERIALS[:2]):
        assert name not in bpy.data.materials
        material = bpy.data.materials["RCS224_stone"].copy()
        material.name = name
        material["finishSource"] = (
            "Owner2021factsheet: brick with painted stucco; currentPhotoAcream presentation, not historic pinkPhotoB"
        )
        material["presentationEstimated"] = True
        material.diffuse_color = (0.69, 0.68, 0.63, 1)
        shader = material.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = material.diffuse_color
        shader.inputs["Roughness"].default_value = 0.84
        shader.inputs["Metallic"].default_value = 0
        nodes, links = material.node_tree.nodes, material.node_tree.links
        uv = nodes.new("ShaderNodeTexCoord")
        bump = nodes.new("ShaderNodeBump")
        if index == 0:
            texture = nodes.new("ShaderNodeTexNoise")
            texture.inputs["Scale"].default_value = 24
            texture.inputs["Detail"].default_value = 1
            bump.inputs["Distance"].default_value = 0.002
            bump.inputs["Strength"].default_value = 0.18
            links.new(texture.outputs["Fac"], bump.inputs["Height"])
        else:
            texture = nodes.new("ShaderNodeTexBrick")
            texture.inputs["Scale"].default_value = 1
            texture.inputs["Brick Width"].default_value = 1.35
            texture.inputs["Row Height"].default_value = 0.48
            texture.inputs["Mortar Size"].default_value = 0.018
            texture.inputs["Color1"].default_value = (0.69, 0.68, 0.63, 1)
            texture.inputs["Color2"].default_value = (0.68, 0.67, 0.62, 1)
            texture.inputs["Mortar"].default_value = (0.52, 0.51, 0.47, 1)
            bump.inputs["Distance"].default_value = 0.025
            bump.inputs["Strength"].default_value = 0.30
            links.new(texture.outputs["Fac"], bump.inputs["Height"])
            links.new(texture.outputs["Color"], shader.inputs["Base Color"])
        links.new(uv.outputs["UV"], texture.inputs["Vector"])
        links.new(bump.outputs["Normal"], shader.inputs["Normal"])


def build():
    import bpy

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import (
        object_fingerprint,
        set_layer_hidden,
        update_scene,
    )
    from refine_portsmouth_exterior207 import material_fingerprint

    plan = json.loads((OUT / "plan.json").read_text())
    assert sha(BASE) == plan["baselineSha256"] == SHA
    assert all(sha(ROOT / p) == h for p, h in plan["sourceHashes"].items())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    assert len(before["objects"]) == 8770 and len(before["materials"]) == 2355
    images = sorted(i.name for i in bpy.data.images)
    write(OUT / "protected-source-state.json", before)
    new_materials()
    graphs = {n: material_fingerprint(bpy.data.materials[n]) for n in MATERIALS[:2]}
    objects = []
    for batch in plan["batches"]:
        points, faces, records, slots = [], [], [], []
        for solid in batch["solids"]:
            start = len(points)
            points.extend(v["world"] for v in solid["vertices"])
            for face in solid["faces"]:
                faces.append([start + i for i in face])
                records.append([solid["vertices"][i]["uv"] for i in face])
                slots.append(solid["slot"])
        mesh = bpy.data.meshes.new(batch["name"] + "_mesh")
        mesh.from_pydata(points, [], faces)
        for name in MATERIALS:
            mesh.materials.append(bpy.data.materials[name])
        uv = mesh.uv_layers.new(name="Metric_facade_UV")
        for polygon, record, slot in zip(mesh.polygons, records, slots, strict=True):
            polygon.material_index = slot
            for index, value in zip(polygon.loop_indices, record, strict=True):
                uv.data[index].uv = value
        mesh.update()
        obj = bpy.data.objects.new(batch["name"], mesh)
        obj.use_fake_user = True
        obj["destinationCollection"] = OWNER
        obj["sourceBuildingOSM"] = "way/181939019"
        obj["sourceScope"] = (
            "59-60park-facing main facade only; native17mheight, roof, terrain and all other sides retained"
        )
        bpy.data.collections[OWNER].objects.link(obj)
        objects.append(obj)
    update_scene()
    protect(before, [o.name for o in objects], new_materials=graphs)
    component = OUT / "component.blend"
    audit = {
        "version": 277,
        "status": "bounded-street-facade-candidate",
        "builderProcessID": os.getpid(),
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "targetCollection": OWNER,
        "destinationCollection": OWNER,
        "addedObjects": [o.name for o in objects],
        "archivedObjects": SOURCE_NAMES,
        "changedObjects": [],
        "objectOwners": {o.name: OWNER for o in objects},
        "addedFingerprints": {o.name: object_fingerprint(o) for o in objects},
        "replacementMaterialBindings": {o.name: MATERIALS for o in objects},
        "newMaterials": 2,
        "newMaterialGraphs": graphs,
        "addedMaterialFingerprints": graphs,
        "reusedMaterialGraphs": {
            n: material_fingerprint(bpy.data.materials[n]) for n in MATERIALS[2:]
        },
        "sourcePlan": "result/blender/street277/plan.json",
        "sourcePlanSha256": sha(OUT / "plan.json"),
        "sourceEvidence": "result/blender/street277/scope-audit.json",
        "sourceHashes": plan["sourceHashes"],
        "scope": "Two existing park-facing context quads only:five facade axes,three main levels,16backed real window/door openings and simplified stucco orders. Original roof and all other sides preserved.",
        "limitations": plan["limits"],
        "noFullNativeSaved": True,
    }
    bpy.data.libraries.write(str(component), set(objects), fake_user=False)
    audit["componentSha256"] = sha(component)
    bpy.ops.wm.open_mainfile(filepath=str(component))
    assert set(bpy.data.objects.keys()) == set(audit["addedObjects"])
    assert all(
        object_fingerprint(bpy.data.objects[n]) == f
        for n, f in audit["addedFingerprints"].items()
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    with bpy.data.libraries.load(str(component), link=False) as (_, destination):
        destination.objects = list(audit["addedObjects"])
    for obj in destination.objects:
        for i, name in enumerate(MATERIALS):
            obj.data.materials[i] = bpy.data.materials[name]
        bpy.data.collections[OWNER].objects.link(obj)
        obj.hide_render = False
        set_layer_hidden(obj, False)
    for material in list(bpy.data.materials):
        if material.name not in before["materials"] and material.name not in graphs:
            assert material.users == 0
            bpy.data.materials.remove(material)
    for name in SOURCE_NAMES:
        bpy.data.objects[name].hide_render = True
        set_layer_hidden(bpy.data.objects[name], True)
    update_scene()
    protect(before, audit["addedObjects"], SOURCE_NAMES, graphs)
    assert sorted(i.name for i in bpy.data.images) == images
    verifier = load_module("lindsey277_independent", "web/tests/verify_lindsey277.py")
    audit["verification"] = verifier.geometry_proof(audit, context="build-roundtrip")
    audit["authoringScriptSha256"] = sha(Path(__file__))
    audit["verificationScriptSha256"] = sha(ROOT / "web/tests/verify_lindsey277.py")
    write(OUT / "audit.json", audit)
    write(
        OUT / "verification.json",
        {
            "status": "passed-builder-roundtrip",
            "freshBlenderProcess": False,
            "componentSha256": audit["componentSha256"],
            "actualMeshProof": audit["verification"],
            "noFullNativeSaved": True,
        },
    )
    print("LINDSEY277_COMPONENT_READY", audit["componentSha256"], flush=True)


def main(stage=STAGE):
    if stage == "prepare":
        prepare()
    elif stage == "build":
        build()
    else:
        raise ValueError(stage)


if __name__ == "__main__":
    main()
