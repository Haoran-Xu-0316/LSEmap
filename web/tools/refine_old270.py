"""Replace only OLD's four lower Clare casement grids from retained photographs.

Fixed native269 and separate component. Set STAGE or call main('prepare') in
MachineLearning; main('build') runs in Blender. Counts are source-observed;
proportions and section sizes remain estimates. No full-native save or CLI.
"""

import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
STAGE = "build"
BASE = ROOT / "result/blender/LSE_campus_detailed_v269.blend"
SHA = "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b"
OUT = ROOT / "result/blender/old270"
OWNER = "OLD_EXTERIOR"
SOURCE = "OLD_D5_clare87_casements"
REPLACEMENT = "OLD270_Clare_lower_six_column_eight_row_casements"
VERTICAL_FRACTIONS = (0.135, 0.3175, 0.5, 0.6825, 0.865)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def f32(values):
    return list(struct.unpack("fff", struct.pack("fff", *values)))


def prepare():
    import numpy as np

    native = json.loads((OUT / "native-inspection.json").read_text())
    evidence = json.loads((OUT / "exterior-audit.json").read_text())
    legacy_path = ROOT / "result/blender/stage87/old-clare-casement-audit.json"
    legacy = json.loads(legacy_path.read_text())
    assert native["baselineSha256"] == evidence["baselineSha256"] == SHA
    assert native["sourceObject"] == SOURCE and native["sourceOwners"] == [OWNER]
    assert not native["modifiers"] and len(native["components"]) == 56
    matrix = np.array(native["matrixWorld"])
    inverse = np.linalg.inv(matrix)
    origin, right, outward = [
        np.array(native["frame"][n]) for n in ("origin", "right", "outward")
    ]
    matched = {}
    for index, member in enumerate(legacy["members"]):
        found = [
            c
            for c in native["components"]
            if max(
                abs(a - b)
                for a, b in zip(c["localCentre"], member["centre"], strict=True)
            )
            < 0.00005
            and max(
                abs(a - b) for a, b in zip(c["localSize"], member["size"], strict=True)
            )
            < 0.00005
        ]
        assert len(found) == 1, (index, found)
        matched[index] = found[0]
    assert len({r["component"] for r in matched.values()}) == 56

    def component(index, role, window=None, centre=None, size=None):
        group = matched[index]
        member = legacy["members"][index]
        selected = group["vertices"]
        mapping = {v: i for i, v in enumerate(selected)}
        points = [native["verticesLocal"][i] for i in selected]
        if centre is not None:
            transformed = []
            for world in (np.array(native["verticesWorld"][i]) for i in selected):
                delta = world - origin
                local = np.array([delta @ right, delta @ outward, world[2]])
                # Transform within the inherited facade frame. Round only newly
                # positioned members to Blender's stored Float32 coordinates.
                local = (
                    np.array(centre)
                    + (local - member["centre"]) * np.array(size) / member["size"]
                )
                changed = (
                    origin
                    + right * local[0]
                    + outward * local[1]
                    + np.array([0, 0, local[2]])
                )
                transformed.append(f32((inverse @ np.append(changed, 1))[:3]))
            points = transformed
        return {
            "role": role,
            "window": window,
            "sourceComponent": group["component"],
            "sourceMember": index,
            "centre": centre,
            "size": size,
            "points": points,
            "faces": [
                {
                    "sourceFace": face["index"],
                    "vertices": [mapping[v] for v in face["vertices"]],
                    "materialIndex": face["materialIndex"],
                    "smooth": face["smooth"],
                    "uvs": face["uvs"],
                }
                for face in native["faces"]
                if face["index"] in group["faces"]
            ],
        }

    records = []
    removed = []
    for index, member in enumerate(legacy["members"]):
        window = legacy["windows"][member["window"]]
        if window["family"] == "upper":
            records.append(
                component(index, "retained-upper-native-member", member["window"])
            )
        else:
            removed.append(matched[index]["component"])
    assert len(records) == len(removed) == 28
    for wi, window in enumerate(legacy["windows"]):
        if window["family"] != "lower":
            continue
        horizontal = next(
            i
            for i, m in enumerate(legacy["members"])
            if m["window"] == wi and m["kind"] == "horizontal"
        )
        vertical = next(
            i
            for i, m in enumerate(legacy["members"])
            if m["window"] == wi and m["kind"] == "vertical"
        )
        for j in range(1, 8):
            centre = [
                window["x"],
                -0.10,
                window["z"] - window["h"] / 2 + window["h"] * j / 8,
            ]
            size = [window["w"], 0.15, 0.095 if j % 2 == 0 else 0.045]
            records.append(component(horizontal, "lower-horizontal", wi, centre, size))
        for j, fraction in enumerate(VERTICAL_FRACTIONS, 1):
            centre = [
                window["x"] - window["w"] / 2 + window["w"] * fraction,
                -0.10,
                window["z"],
            ]
            size = [0.052 if j % 2 else 0.028, 0.15, window["h"]]
            records.append(component(vertical, "lower-vertical", wi, centre, size))
    assert len(records) == 76
    sources = [
        "result/blender/old270/exterior-audit.json",
        "result/blender/old270/native-inspection.json",
        "result/blender/old270/native-contact-preflight.json",
        "web/tests/inspect_old270.py",
        "result/blender/stage87/old-clare-casement-audit.json",
        "data/collections/old-clare-reference/front.png",
        "data/collections/public-realm-2026/user-references/reference-08.png",
        "web/tools/refine_old270.py",
        "web/tests/verify_old270.py",
    ]
    plan = {
        "baselineSha256": SHA,
        "sourceObject": SOURCE,
        "sourceFingerprint": native["sourceFingerprint"],
        "replacement": REPLACEMENT,
        "owner": OWNER,
        "materials": native["materials"],
        "sourceMaterialGraphs": native["materialGraphs"],
        "sourceCounts": [native["originalObjects"], native["originalMaterials"]],
        "frame": native["frame"],
        "windows": legacy["windows"],
        "removedLowerComponents": removed,
        "components": records,
        "sourceHashes": {p: sha(ROOT / p) for p in sources},
        "dimensionStatus": "Photo-estimated fractions and profiles within inherited native openings; no surveyed dimensions.",
    }
    write(OUT / "plan.json", plan)
    print("OLD270_PLAN_READY", len(records), flush=True)


def capture():
    from refine_houghton262 import capture as capture_source

    result = capture_source()
    result["baselineSha256"] = SHA
    return result


def protection(before, added=(), archived=()):
    after = capture()
    for name, value in before["objects"].items():
        expected = dict(value)
        if name in archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
        visibility = (
            [True, before["visibility"][name][1], True]
            if name in archived
            else before["visibility"][name]
        )
        assert after["visibility"][name] == visibility, name
    assert set(after["objects"]) == set(before["objects"]) | set(added)
    assert after["materials"] == before["materials"]
    assert after["rooms"] == before["rooms"] and len(after["rooms"]) == 35
    assert after["campusRooms"] == before["campusRooms"]
    assert sha(BASE) == SHA


def build_mesh(plan, source):
    import bpy

    vertices, faces, records = [], [], []
    for part in plan["components"]:
        start = len(vertices)
        vertices.extend(part["points"])
        for face in part["faces"]:
            faces.append([start + i for i in face["vertices"]])
            records.append(face)
    mesh = bpy.data.meshes.new(REPLACEMENT + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    for material in source.data.materials:
        mesh.materials.append(material)
    for face, record in zip(mesh.polygons, records, strict=True):
        face.material_index = record["materialIndex"]
        face.use_smooth = record["smooth"]
    for name in (layer.name for layer in source.data.uv_layers):
        layer = mesh.uv_layers.new(name=name)
        for face, record in zip(mesh.polygons, records, strict=True):
            for index, value in zip(
                face.loop_indices, record["uvs"][name], strict=True
            ):
                layer.data[index].uv = value
    mesh.update()
    obj = source.copy()
    obj.data = mesh
    obj.name = REPLACEMENT
    obj.use_fake_user = True
    obj["originalObject"] = SOURCE
    obj["destinationCollection"] = OWNER
    obj["dimensionsEstimated"] = True
    obj["sourceScope"] = (
        "Undated user Clare photographs: four lower ordinary6column8row casements only; upper5window grids retained exactly"
    )
    bpy.data.collections[OWNER].objects.link(obj)
    return obj


def build():
    import bpy

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import (
        object_fingerprint,
        set_layer_hidden,
        update_scene,
    )
    from refine_portsmouth_exterior207 import material_fingerprint

    assert sha(BASE) == SHA
    plan = json.loads((OUT / "plan.json").read_text())
    assert plan["baselineSha256"] == SHA
    assert all(sha(ROOT / p) == h for p, h in plan["sourceHashes"].items())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    assert [len(before["objects"]), len(before["materials"])] == plan["sourceCounts"]
    assert len(before["rooms"]) == 35
    images = sorted(i.name for i in bpy.data.images)
    write(OUT / "protected-source-state.json", before)
    source = bpy.data.objects[SOURCE]
    assert (
        not source.hide_render
        and object_fingerprint(source) == plan["sourceFingerprint"]
    )
    assert [m.name for m in source.data.materials] == plan["materials"]
    obj = build_mesh(plan, source)
    update_scene()
    protection(before, [obj.name])
    path = OUT / "component.blend"
    audit = {
        "version": 270,
        "building": "OLD",
        "status": "bounded-lower-casement-grid-candidate",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "componentPath": str(path.relative_to(ROOT)),
        "destinationCollection": OWNER,
        "targetCollection": OWNER,
        "addedObjects": [obj.name],
        "archivedObjects": [SOURCE],
        "changedObjects": [],
        "objectOwners": {obj.name: OWNER},
        "addedFingerprints": {obj.name: object_fingerprint(obj)},
        "replacementMaterialBindings": {obj.name: [m.name for m in obj.data.materials]},
        "reusedMaterialGraphs": {
            m.name: material_fingerprint(m) for m in obj.data.materials
        },
        "newMaterials": 0,
        "newMaterialGraphs": {},
        "addedMaterialFingerprints": {},
        "sourcePlan": "result/blender/old270/plan.json",
        "sourcePlanSha256": sha(OUT / "plan.json"),
        "sourceEvidence": "result/blender/old270/exterior-audit.json",
        "sourceHashes": plan["sourceHashes"],
        "scope": "Four ordinary lower Clare casement grids only. All28upper native members and unrelated native state preserved.",
        "limitations": [
            "Undated photos support6columns8rows, not2026whole-building completion.",
            "Opening extents and profiles remain estimates; no door operation or manufacturing joinery claim.",
        ],
        "noFullNativeSaved": True,
    }
    bpy.data.libraries.write(str(path), {obj}, fake_user=False)
    audit["componentSha256"] = sha(path)
    bpy.ops.wm.open_mainfile(filepath=str(path))
    assert set(bpy.data.objects.keys()) == {REPLACEMENT}
    assert (
        object_fingerprint(bpy.data.objects[REPLACEMENT])
        == audit["addedFingerprints"][REPLACEMENT]
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    with bpy.data.libraries.load(str(path), link=False) as (_, destination):
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
    bpy.data.objects[SOURCE].hide_render = True
    set_layer_hidden(bpy.data.objects[SOURCE], True)
    update_scene()
    protection(before, audit["addedObjects"], audit["archivedObjects"])
    assert sorted(i.name for i in bpy.data.images) == images
    verifier_path = ROOT / "web/tests/verify_old270.py"
    spec = importlib.util.spec_from_file_location("old270_independent", verifier_path)
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    proof = verifier.geometry_proof(audit)
    audit["verification"] = proof
    audit["authoringScriptSha256"] = sha(Path(__file__))
    audit["verificationScriptSha256"] = sha(verifier_path)
    write(OUT / "audit.json", audit)
    write(
        OUT / "verification.json",
        {
            "status": "passed-builder-roundtrip",
            "freshBlenderProcess": False,
            "componentSha256": audit["componentSha256"],
            "actualMeshProof": proof,
            "originalObjectsProtected": len(before["objects"]),
            "originalMaterialGraphsProtected": len(before["materials"]),
            "roomMembershipsProtected": 35,
            "noFullNativeSaved": True,
        },
    )
    print("OLD270_COMPONENT_READY", audit["componentSha256"], flush=True)


def main(stage=STAGE):
    if stage == "prepare":
        prepare()
    elif stage == "build":
        build()
    else:
        raise ValueError(stage)


if __name__ == "__main__":
    main()
