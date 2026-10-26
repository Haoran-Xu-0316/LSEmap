"""Correct only CBG's two upperG4shade/glazing boundaries from built photos.

main('prepare') uses native269readback in MachineLearning. main('build') runs in
Blender and writes a separate component, never the full campus. No CLI, global
fin re-spacing, floor-height change, new coating, texture or shared-file edit.
"""

import hashlib
import importlib.util
import json
import math
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v269.blend"
SHA = "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b"
OUT = ROOT / "result/blender/cbg274"
OWNER = "CBG_EXTERIOR"
STEP = 52.2 / 13
STAGE = "build"
FAMILIES = {
    "gold_solar_blades": ("coloured_blades", 1),
    "pale_solar_blades": ("pale_blades", 1),
    "shade_cantilever_brackets": ("brackets", 2),
    "shade_module_caps": ("caps", 2),
    "shade_fixing_bolt_heads": ("bolts", 4),
    "shade_leading_silver_strips": ("leading_strips", 3),
    "shade_mid_tie_rods": ("tie_rods", 1),
}
GLASS = "CBG274_G4_upper_clear_glass_patches"


def sha(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def f32(point):
    return list(struct.unpack("fff", struct.pack("fff", *point)))


def prepare():
    import numpy as np

    native = json.loads((OUT / "native-inspection.json").read_text())
    assert native["baselineSha256"] == SHA
    objects = native["visibleExterior"]

    def find(suffix):
        matches = [o for o in objects if o["name"].endswith(suffix)]
        assert len(matches) == 1, suffix
        return matches[0]

    brackets = find("shade_cantilever_brackets")
    stations = {
        floor: sorted(
            {
                round(c["localCentre"][0], 4)
                for c in brackets["topFrontComponents"]
                if math.floor(c["localCentre"][2] / STEP) == floor
            }
        )
        for floor in (11, 12)
    }
    assert stations[11] == stations[12]
    removed_stations = [x for x in stations[11] if x > -18]
    assert (
        len(removed_stations) == 4 and max(x for x in stations[11] if x <= -18) == -18.2
    )
    rows = []

    def row(source, selected, replacement, role):
        assert source["owners"] == [OWNER] and not source["modifiers"]
        vertices = sorted({v for c in selected for v in c["vertices"]})
        faces = [
            f for f in source["selectedFaces"] if set(f["vertices"]) <= set(vertices)
        ]
        assert len(vertices) == len(selected) * 8 and len(faces) == len(selected) * 6
        return {
            "sourceObject": source["name"],
            "sourceFingerprint": source["fingerprint"],
            "replacement": replacement,
            "role": role,
            "materials": [m["name"] for m in source["materials"]],
            "sourceComponentCount": source["allComponentCount"],
            "removedComponents": selected,
            "removedVertices": vertices,
            "removedFaces": [f["index"] for f in faces],
        }

    for suffix, (role, count) in FAMILIES.items():
        source = find(suffix)
        selected = []
        groups = {}
        for component in source["topFrontComponents"]:
            floor = math.floor(component["localCentre"][2] / STEP)
            if floor not in stations:
                continue
            station = min(
                stations[floor], key=lambda x: abs(x - component["localCentre"][0])
            )
            assert abs(station - component["localCentre"][0]) < 0.25
            if station <= -18:
                continue
            selected.append(component)
            groups[(floor, station)] = groups.get((floor, station), 0) + 1
        assert set(groups.values()) == {count} and len(groups) == 8
        rows.append(row(source, selected, "CBG274_G4_retained_" + role, role))
    solid, vent, glass = (
        find("metric_office_solid"),
        find("metric_office_vent_transoms"),
        find("metric_office_glass"),
    )
    leaves = [
        c
        for c in solid["topFrontComponents"]
        if -18 < c["localCentre"][0] < -15 and c["localCentre"][2] > 11 * STEP
    ]
    vents = [
        c
        for c in vent["topFrontComponents"]
        if -18 < c["localCentre"][0] < -15 and c["localCentre"][2] > 11 * STEP
    ]
    assert len(leaves) == len(vents) == 2
    rows.append(row(solid, leaves, "CBG274_G4_retained_office_solid", "office_solid"))
    rows.append(row(vent, vents, "CBG274_G4_retained_office_vents", "office_vent"))
    x_axis = np.array([*native["frame"]["x_unit_SW"], 0])
    inverse = np.linalg.inv(np.array(glass["matrixWorld"]))
    patches = []
    lookup = {v["index"]: v for v in glass["selectedVertices"]}
    for leaf in leaves:
        candidates = [
            c
            for c in glass["topFrontComponents"]
            if abs(c["localCentre"][2] - leaf["localCentre"][2]) < 0.00001
            and -18 < c["localCentre"][0] < -15
        ]
        assert len(candidates) == 1
        template = candidates[0]
        assert abs(template["localBounds"][0][2] - leaf["localBounds"][0][2]) < 0.00001
        assert abs(template["localBounds"][1][2] - leaf["localBounds"][1][2]) < 0.00001
        old_width = template["localBounds"][1][0] - template["localBounds"][0][0]
        width = leaf["localBounds"][1][0] - leaf["localBounds"][0][0]
        points = []
        for index in template["vertices"]:
            source = lookup[index]
            shift = (
                leaf["localCentre"][0]
                - template["localCentre"][0]
                + (source["facadeLocal"][0] - template["localCentre"][0])
                * (width / old_width - 1)
            )
            world = np.array(source["world"]) + x_axis * shift
            points.append(f32((inverse @ np.append(world, 1))[:3]))
        indices = {v: i for i, v in enumerate(template["vertices"])}
        faces = [
            dict(f, vertices=[indices[v] for v in f["vertices"]])
            for f in glass["selectedFaces"]
            if set(f["vertices"]) <= set(template["vertices"])
        ]
        assert len(points) == 8 and len(faces) == 6
        patches.append(
            {
                "leafComponent": leaf["component"],
                "templateGlassComponent": template["component"],
                "floor": math.floor(leaf["localCentre"][2] / STEP),
                "targetLocalBounds": [
                    leaf["localBounds"][0][:1] + template["localBounds"][0][1:],
                    leaf["localBounds"][1][:1] + template["localBounds"][1][1:],
                ],
                "points": points,
                "faces": faces,
            }
        )
    sources = [
        "result/blender/cbg274/native-inspection.json",
        "result/blender/cbg274/native-preflight.json",
        "result/blender/cbg274/exterior-audit.json",
        "data/collections/exteriors/images/cbg_rshp_020.jpg",
        "data/collections/cbg_facade_contractor/photo-2.jpg",
        "result/blender/cbg-georegistration202/rebuild-mapping.json",
        "web/tests/inspect_cbg274.py",
        "web/tools/refine_cbg274.py",
        "web/tests/verify_cbg274.py",
        "web/tools/review_cbg274.py",
    ]
    plan = {
        "baselineSha256": SHA,
        "frame": native["frame"],
        "G4LocalX": -18,
        "floorIndices": [11, 12],
        "assemblyStationsRemoved": removed_stations,
        "replacements": rows,
        "glassSource": glass["name"],
        "glassSourceFingerprint": glass["fingerprint"],
        "glassMaterials": [m["name"] for m in glass["materials"]],
        "glassProperties": glass["materials"],
        "glassPatches": patches,
        "newGlassObject": GLASS,
        "removedShadeParts": 112,
        "removedOpaqueLeaves": 2,
        "removedObsoleteVentBars": 2,
        "newGlassPatches": 2,
        "sourceHashes": {p: sha(ROOT / p) for p in sources},
    }
    assert sum(len(r["removedComponents"]) for r in rows) == 116
    write(OUT / "plan.json", plan)
    print("CBG274_PLAN_READY", len(rows), len(patches), flush=True)


def capture():
    from refine_houghton262 import capture as original_capture

    result = original_capture()
    result["baselineSha256"] = SHA
    return result


def protection(before, added=(), archived=()):
    after = capture()
    for name, value in before["objects"].items():
        expected = dict(value)
        if name in archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
        visible = (
            [True, before["visibility"][name][1], True]
            if name in archived
            else before["visibility"][name]
        )
        assert after["visibility"][name] == visible, name
    assert set(after["objects"]) == set(before["objects"]) | set(added)
    assert after["materials"] == before["materials"]
    assert after["rooms"] == before["rooms"] and len(after["rooms"]) == 35
    assert after["campusRooms"] == before["campusRooms"]
    assert sha(BASE) == SHA


def mesh_object(source, name, points, faces):
    import bpy

    assert not source.data.has_custom_normals and not any(
        p.use_smooth for p in source.data.polygons
    )
    assert not any(e.use_edge_sharp for e in source.data.edges)
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(points, [], [f["vertices"] for f in faces])
    for material in source.data.materials:
        mesh.materials.append(material)
    for polygon, record in zip(mesh.polygons, faces, strict=True):
        polygon.material_index = record["materialIndex"]
        polygon.use_smooth = record["smooth"]
    for uv_name in (uv.name for uv in source.data.uv_layers):
        uv = mesh.uv_layers.new(name=uv_name)
        for polygon, record in zip(mesh.polygons, faces, strict=True):
            for index, value in zip(
                polygon.loop_indices, record["uvs"][uv_name], strict=True
            ):
                uv.data[index].uv = value
    mesh.update()
    obj = source.copy()
    obj.data = mesh
    obj.name = name
    obj.use_fake_user = True
    obj["originalObject"] = source.name
    obj["destinationCollection"] = OWNER
    obj["sourceScope"] = (
        "Built-photo upper two-storeyG4boundary only; no global fin grid or complete facade acceptance"
    )
    bpy.data.collections[OWNER].objects.link(obj)
    return obj


def retain(source, row):
    removed = set(row["removedVertices"])
    keep = [v for v in source.data.vertices if v.index not in removed]
    mapping = {v.index: i for i, v in enumerate(keep)}
    faces = []
    for face in source.data.polygons:
        if set(face.vertices) & removed:
            assert set(face.vertices) <= removed
            continue
        faces.append(
            {
                "vertices": [mapping[v] for v in face.vertices],
                "materialIndex": face.material_index,
                "smooth": face.use_smooth,
                "uvs": {
                    uv.name: [list(uv.data[i].uv) for i in face.loop_indices]
                    for uv in source.data.uv_layers
                },
            }
        )
    assert len(source.data.polygons) - len(faces) == len(row["removedFaces"])
    return mesh_object(source, row["replacement"], [list(v.co) for v in keep], faces)


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
    assert len(before["objects"]) == 8752 and len(before["materials"]) == 2355
    images = sorted(i.name for i in bpy.data.images)
    write(OUT / "protected-source-state.json", before)
    objects = []
    for row in plan["replacements"]:
        source = bpy.data.objects[row["sourceObject"]]
        assert (
            object_fingerprint(source) == row["sourceFingerprint"]
            and not source.hide_render
        )
        objects.append(retain(source, row))
    template = bpy.data.objects[plan["glassSource"]]
    assert object_fingerprint(template) == plan["glassSourceFingerprint"]
    points, faces = [], []
    for patch in plan["glassPatches"]:
        start = len(points)
        points.extend(patch["points"])
        faces.extend(
            dict(f, vertices=[start + i for i in f["vertices"]]) for f in patch["faces"]
        )
    objects.append(mesh_object(template, GLASS, points, faces))
    update_scene()
    protection(before, [o.name for o in objects])
    component = OUT / "component.blend"
    audit = {
        "version": 274,
        "building": "CBG",
        "status": "bounded-upper-G4-candidate",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "destinationCollection": OWNER,
        "targetCollection": OWNER,
        "addedObjects": [o.name for o in objects],
        "archivedObjects": [r["sourceObject"] for r in plan["replacements"]],
        "changedObjects": [],
        "objectOwners": {o.name: OWNER for o in objects},
        "addedFingerprints": {o.name: object_fingerprint(o) for o in objects},
        "replacementMaterialBindings": {
            o.name: [m.name for m in o.data.materials] for o in objects
        },
        "reusedMaterialGraphs": {
            m.name: material_fingerprint(m) for o in objects for m in o.data.materials
        },
        "newMaterials": 0,
        "newMaterialGraphs": {},
        "addedMaterialFingerprints": {},
        "sourcePlan": "result/blender/cbg274/plan.json",
        "sourcePlanSha256": sha(OUT / "plan.json"),
        "sourceEvidence": "result/blender/cbg274/exterior-audit.json",
        "sourceHashes": plan["sourceHashes"],
        "scope": "Top two front storeys only: remove8complete shade assemblies crossingG4,2misplaced office leaves and their2vent bars; fill only those leaves with existing coplanar neutral glass. All other surfaces and red/orange coats preserved.",
        "limitations": [
            "Built photos have unknown capture date; not a2026survey.",
            "Inherited floor heights, frame layout, global fin phase and all other void boundaries remain estimates.",
        ],
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
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        bpy.data.collections[OWNER].objects.link(obj)
        obj.hide_render = False
        set_layer_hidden(obj, False)
    for material in list(bpy.data.materials):
        if material.name not in before["materials"]:
            assert material.users == 0
            bpy.data.materials.remove(material)
    for name in audit["archivedObjects"]:
        bpy.data.objects[name].hide_render = True
        set_layer_hidden(bpy.data.objects[name], True)
    update_scene()
    protection(before, audit["addedObjects"], audit["archivedObjects"])
    assert sorted(i.name for i in bpy.data.images) == images
    path = ROOT / "web/tests/verify_cbg274.py"
    spec = importlib.util.spec_from_file_location("cbg274_independent", path)
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    proof = verifier.geometry_proof(audit)
    audit["verification"] = proof
    audit["authoringScriptSha256"] = sha(Path(__file__))
    audit["verificationScriptSha256"] = sha(path)
    write(OUT / "audit.json", audit)
    write(
        OUT / "verification.json",
        {
            "status": "passed-builder-roundtrip",
            "freshBlenderProcess": False,
            "baselineSha256": SHA,
            "componentSha256": audit["componentSha256"],
            "actualMeshProof": proof,
            "originalObjectsProtected": 8752,
            "originalMaterialGraphsProtected": 2355,
            "roomMembershipsProtected": 35,
            "noFullNativeSaved": True,
        },
    )
    print("CBG274_COMPONENT_READY", audit["componentSha256"], flush=True)


def main(stage=STAGE):
    if stage == "prepare":
        prepare()
    elif stage == "build":
        build()
    else:
        raise ValueError(stage)


if __name__ == "__main__":
    main()
