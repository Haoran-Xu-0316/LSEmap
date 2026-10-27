"""Independent CPU and fresh-Blender proofs of the bounded Lindsey facade.

No authoring helpers are imported. Actual closed solids, parcel containment,
true openings, pane first surfaces, joinery contacts and original roof support
are checked. Native geometry/material/room protection is repeated after reopen.
"""

import collections
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/street277"
BASE = ROOT / "result/blender/LSE_campus_detailed_v275.blend"
SHA = "18a60235fd7c71c6c2864690c574f97b66a9d05577e0c584c626dee41829a4f9"
OWNER = "01_CITY_CONTEXT_estimated_heights"
ML_PYTHON = Path("/opt/anaconda3/envs/MachineLearning/bin/python")
CPU_RUNNER = ROOT / "web/tests/verify_lindsey277_cpu.py"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ray(triangles, origin, direction, distance=1):
    import numpy as np

    a = triangles[:, 0]
    e1, e2 = triangles[:, 1] - a, triangles[:, 2] - a
    h = np.cross(np.broadcast_to(direction, e2.shape), e2)
    determinant = np.einsum("ij,ij->i", e1, h)
    valid = abs(determinant) > 1e-12
    inverse = np.zeros_like(determinant)
    inverse[valid] = 1 / determinant[valid]
    s = origin - a
    u = np.einsum("ij,ij->i", s, h) * inverse
    q = np.cross(s, e1)
    v = q @ direction * inverse
    t = np.einsum("ij,ij->i", e2, q) * inverse
    valid &= (
        (u >= -1e-7)
        & (v >= -1e-7)
        & (u + v <= 1 + 1e-7)
        & (t >= 1e-7)
        & (t <= distance)
    )
    if not valid.any():
        return None
    indices = np.flatnonzero(valid)
    index = int(indices[np.argmin(t[indices])])
    return index, float(t[index])


def cpu_proof(plan, write_preview=True):
    import numpy as np
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union

    native = json.loads((OUT / "native-inspection.json").read_text())
    assert native["baselineSha256"] == plan["baselineSha256"] == SHA
    byname = {r["name"]: r for r in native["targetOriginalObjects"]}
    assert len(byname) == 7 and all(
        r["renderEligibleInCompleteCampus"] and not r["hideRender"]
        for r in byname.values()
    )
    assert all(
        len(byname[f"Context_way/181939019_wall_0_{i}"]["faces"]) == 1
        and len(byname[f"Context_way/181939019_wall_0_{i}"]["verticesWorld"]) == 4
        for i in range(6)
    )
    ring = [
        byname[f"Context_way/181939019_wall_0_{i}"]["verticesWorld"][0][:2]
        for i in range(6)
    ]
    parcel = Polygon(ring)
    ends = np.array(plan["frontPolyline"])
    lengths = np.array([np.linalg.norm(ends[i + 1] - ends[i]) for i in (0, 1)])
    assert abs(lengths.sum() - plan["lengthM"]) < 1e-8
    tangents = (ends[1:] - ends[:-1]) / lengths[:, None]
    normals = np.array([[t[1], -t[0]] for t in tangents])

    def source_point(s, z):
        index = 0 if s <= lengths[0] else 1
        start = 0 if index == 0 else lengths[0]
        return np.array([*(ends[index] + tangents[index] * (s - start)), z]), np.array(
            [*normals[index], 0]
        )

    arrays, labels, batch_arrays = [], [], {}
    volumes, triangles, solids = [], 0, 0
    for batch in plan["batches"]:
        mesh_triangles = []
        for part in batch["solids"]:
            points = np.array([v["world"] for v in part["vertices"]])
            assert len(set(map(tuple, points))) == len(points), (
                "collapsed-vertex",
                part["role"],
                part["tag"],
            )
            edges = collections.Counter()
            directed = collections.Counter()
            centre = points.mean(axis=0)
            volume = 0.0
            for face in part["faces"]:
                assert len(face) == 3 and len(set(face)) == 3
                tri = points[face]
                assert np.linalg.norm(np.cross(tri[1] - tri[0], tri[2] - tri[0])) > 1e-9
                volume += (
                    float(
                        (tri[0] - centre) @ np.cross(tri[1] - centre, tri[2] - centre)
                    )
                    / 6
                )
                for a, b in zip(face, face[1:] + face[:1], strict=True):
                    edges[tuple(sorted((a, b)))] += 1
                    directed[(a, b)] += 1
                mesh_triangles.append(tri)
                labels.append((batch["name"], part["role"], part["tag"], part["slot"]))
                arrays.append(tri)
            assert set(edges.values()) == {2}, (
                "non-manifold",
                part["role"],
                collections.Counter(edges.values()),
            )
            assert all(n == directed[(b, a)] for (a, b), n in directed.items()), (
                "winding",
                part["role"],
            )
            assert volume > 1e-9, ("negative-volume", part["role"], volume)
            assert all(parcel.buffer(0.00002).covers(Point(p[:2])) for p in points), (
                "outside-existing-parcel",
                part["role"],
            )
            assert points[:, 2].min() >= 0 and points[:, 2].max() <= 17.00001
            triangles += len(part["faces"])
            solids += 1
            volumes.append(volume)
        batch_arrays[batch["name"]] = np.array(mesh_triangles)
    assert len(plan["batches"]) == 4 and triangles <= 4500
    all_triangles = np.array(arrays)
    core = batch_arrays["LINDSEY277_closed_front_wall"]
    old = []
    for name in plan["sourceObjects"]:
        record = byname[name]
        pts = np.array(record["verticesWorld"])
        for f in record["faces"]:
            vertices = f["vertices"]
            old.extend(
                pts[[vertices[0], vertices[i], vertices[i + 1]]]
                for i in range(1, len(vertices) - 1)
            )
    old = np.array(old)
    masks = [
        Polygon(
            [
                (o["x"] - o["width"] / 2, o["z0"]),
                (o["x"] + o["width"] / 2, o["z0"]),
                (o["x"] + o["width"] / 2, o["z1"]),
                (o["x"] - o["width"] / 2, o["z1"]),
            ]
        )
        for o in plan["openings"]
    ]
    assert (
        len(plan["openings"]) == 16
        and sum(o["kind"] == "window" for o in plan["openings"]) == 14
    )
    assert all(
        a.intersection(b).area < 1e-10
        for i, a in enumerate(masks)
        for b in masks[i + 1 :]
    )
    aperture_rays, glass_rays, door_rays, contacts = 0, 0, 0, 0
    for opening in plan["openings"]:
        x, lo, hi, width = opening["x"], opening["z0"], opening["z1"], opening["width"]
        for u in (0.2, 0.5, 0.8):
            for v in (0.2, 0.5, 0.8):
                point, normal = source_point(x + (u - 0.5) * width, lo + v * (hi - lo))
                start = point + normal * 0.6
                assert ray(old, start, -normal) is not None
                assert ray(core, start, -normal) is None, (
                    "blocked-wall-aperture",
                    opening["id"],
                    u,
                    v,
                )
                aperture_rays += 1
        # Back half of each outside reveal is real core wall, rather than
        # an independently hovering sash. Four finite frame/reveal contacts.
        for s, h in [
            (x - width / 2 - 0.018, (lo + hi) / 2),
            (x + width / 2 + 0.018, (lo + hi) / 2),
            (x, lo - 0.018),
            (x, hi + 0.018),
        ]:
            point, normal = source_point(s, h)
            inside = point - normal * 0.20
            assert ray(core, inside, normal, 0.3) and ray(core, inside, -normal, 0.3), (
                "unsupported-reveal-frame",
                opening["id"],
            )
            contacts += 1
        if opening["kind"] == "window":
            for col in range(opening["columns"]):
                for row in range(opening["rows"]):
                    s = x - width / 2 + width * (col + 0.5) / opening["columns"]
                    h = lo + (hi - lo) * (row + 0.5) / opening["rows"]
                    point, normal = source_point(s, h)
                    hit = ray(all_triangles, point + normal * 0.6, -normal, 1.2)
                    assert (
                        hit
                        and labels[hit[0]][1] == "window-glass"
                        and labels[hit[0]][2] == opening["id"]
                    ), (
                        "wrong-window-first-surface",
                        opening["id"],
                        labels[hit[0]] if hit else None,
                    )
                    glass_rays += 1
        else:
            point, normal = source_point(x, (lo + opening["spring"]) / 2)
            hit = ray(all_triangles, point + normal * 0.6, -normal, 1.2)
            assert hit and labels[hit[0]][1] == "static-door-leaf"
            door_rays += 1
    wall_control = 0
    for s in np.linspace(0.15, plan["lengthM"] - 0.15, 31):
        for h in np.linspace(0.2, 16.8, 29):
            if any(mask.buffer(0.05).covers(Point(s, h)) for mask in masks):
                continue
            point, normal = source_point(s, h)
            hit = ray(core, point + normal * 0.6, -normal)
            assert hit and abs(hit[1] - 0.72) < 0.00003, (
                "missing-retained-wall",
                s,
                h,
                hit,
            )
            wall_control += 1
    roof = np.array(
        [
            t["world"]
            for r in native["completeCampusRenderableRegion"]
            if r["name"] == plan["roofObject"]
            for t in r["triangles"]
        ]
    )
    roof_contacts = 0
    for s in np.linspace(0.3, plan["lengthM"] - 0.3, 25):
        point, normal = source_point(s, 16.8)
        hit = ray(roof, point - normal * 0.25, np.array([0, 0, 1]), 0.6)
        assert hit and abs(hit[1] - 0.2) < 0.00003, ("existing-roof-contact", s, hit)
        roof_contacts += 1
    footprint = unary_union(
        [
            Polygon([v["world"][:2] for v in part["vertices"]]).convex_hull
            for batch in plan["batches"]
            for part in batch["solids"]
        ]
    )
    mapped_surface_checks = []
    for record in native["completeCampusRenderableRegion"]:
        if not record["name"].startswith(
            ("SITE217_mapped_footway_", "STREET227_Asphalt_")
        ):
            continue
        assert not record["flatDisplayDatumOnly"]
        mapped = unary_union(
            [
                Polygon([v[:2] for v in t["world"]]).convex_hull
                for t in record["triangles"]
            ]
        )
        overlap = footprint.intersection(mapped).area
        assert overlap < 1e-10, ("mapped-surface-encroachment", record["name"], overlap)
        mapped_surface_checks.append(
            {"object": record["name"], "exportedRegionProjectedOverlapM2": overlap}
        )
    assert len(mapped_surface_checks) == 3
    result = {
        "status": "passed-cpu-actual-face-plan",
        "triangles": triangles,
        "closedPositiveSolids": solids,
        "minimumSolidVolumeM3": min(volumes),
        "trueWallOpenings": 16,
        "windowOpenings": 14,
        "doorOpenings": 2,
        "oldFilledToNewOpenWallRays": aperture_rays,
        "glassPaneFirstSurfaceRays": glass_rays,
        "staticDoorFirstSurfaceRays": door_rays,
        "finiteRevealFrameContacts": contacts,
        "retainedWallRays": wall_control,
        "unchangedRoofContactRays": roof_contacts,
        "allGeometryInsideExistingParcel": True,
        "GISBendPreserved": True,
        "nativeTargetObjectsRenderedInCompleteScene": 7,
        "originalSixWallQuadFaces": 6,
        "exportedRegionMappedSurfaceChecks": mapped_surface_checks,
        "flatDisplayDatumExcludedFromMappedPathChecks": True,
        "inheritedHeightM": 17,
        "newMaterials": 2,
        "newImages": 0,
        "blenderExecuted": False,
        "wholeBuildingAccepted": False,
    }
    if write_preview:
        preview(plan)
    return result


def preview(plan):
    from PIL import Image, ImageDraw, ImageFont

    width, height, margin = 1400, 1360, 70
    scale = min((width - 2 * margin) / plan["lengthM"], (height - 150) / 17)
    canvas = Image.new("RGB", (width, height), "#f4f3ef")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 23)
    draw.text(
        (margin, 20),
        "Lindsey277 source-relative frontage; native 17m height retained",
        font=font,
        fill="#25313b",
    )

    def pixel(s, z):
        return margin + s * scale, height - 65 - z * scale

    a, b = pixel(0, 17), pixel(plan["lengthM"], 0)
    draw.rectangle((*a, *b), fill="#d4d1c3", outline="#363f43", width=2)
    for o in plan["openings"]:
        a, b = (
            pixel(o["x"] - o["width"] / 2, o["z1"]),
            pixel(o["x"] + o["width"] / 2, o["z0"]),
        )
        draw.rectangle(
            (*a, *b),
            fill="#8ba3b1" if o["kind"] == "window" else "#313b40",
            outline="#f6f2df",
            width=3,
        )
    for s in plan["pierCentres"]:
        a, b = pixel(s - 0.20, 14.4), pixel(s + 0.20, plan["baseBandHeight"])
        draw.rectangle((*a, *b), fill="#ede8d8")
    x, _ = pixel(plan["breakS"], 0)
    draw.line((x, 80, x, height - 65), fill="#a66532", width=2)
    draw.text(
        (margin, height - 40),
        "Orange line: retained GIS bend. Roof/dormers and unseen sides remain proxies.",
        font=font,
        fill="#25313b",
    )
    canvas.save(OUT / "cpu-frontage-layout.png")


def verify_observed(observed_path, expected_sha256):
    """CPU-only physical proof of a hash-bound Blender mesh snapshot."""
    observed_path = Path(observed_path)
    assert sha(observed_path) == expected_sha256
    snapshot = json.loads(observed_path.read_text())
    provenance = snapshot["provenance"]
    assert provenance["capturedFromBlenderMeshDatablocks"] is True
    assert provenance["captureContext"] in {
        "build-roundtrip",
        "fresh",
        "integration-callback",
    }
    assert provenance["blenderProcessID"] != os.getpid()
    assert provenance["baselineSha256"] == SHA == sha(BASE)
    assert provenance["sourcePlanSha256"] == sha(OUT / "plan.json")
    assert provenance["verifierScriptSha256"] == sha(Path(__file__))
    assert provenance["cpuRunnerScriptSha256"] == sha(CPU_RUNNER)
    assert provenance["componentSha256"] == sha(ROOT / provenance["componentPath"])
    assert provenance["freshBlenderProcess"] == (
        provenance["captureContext"] == "fresh"
        and provenance["blenderProcessID"] != provenance["builderProcessID"]
    )
    if provenance["captureContext"] == "fresh":
        assert provenance["freshBlenderProcess"]
    observed = snapshot["actualPlan"]
    assert all(sha(ROOT / path) == h for path, h in observed["sourceHashes"].items())
    assert set(snapshot["actualObjectFingerprints"]) == {
        batch["name"] for batch in observed["batches"]
    }
    assert all(owner == [OWNER] for owner in snapshot["actualObjectOwners"].values())
    assert snapshot["metricUVLoopsChecked"] == sum(
        len(face)
        for batch in observed["batches"]
        for part in batch["solids"]
        for face in part["faces"]
    )
    proof = cpu_proof(observed, write_preview=False)
    proof.update(
        status="passed-bounded-actual-native-facade",
        blenderExecuted=True,
        actualLoadedMeshesUsed=True,
        observedActualPlan=str(observed_path.relative_to(ROOT)),
        observedActualPlanSha256=expected_sha256,
        componentSha256=provenance["componentSha256"],
        sourcePlanSha256=provenance["sourcePlanSha256"],
        captureContext=provenance["captureContext"],
        blenderProcessID=provenance["blenderProcessID"],
        builderProcessID=provenance["builderProcessID"],
        freshBlenderProcess=provenance["freshBlenderProcess"],
        cpuProcessID=os.getpid(),
        cpuExecutable=sys.executable,
        verifierScriptSha256=provenance["verifierScriptSha256"],
        cpuRunnerScriptSha256=provenance["cpuRunnerScriptSha256"],
        actualMetricUVLoopsChecked=snapshot["metricUVLoopsChecked"],
        actualMaterialGraphs=snapshot["actualMaterialGraphs"],
    )
    assert sha(observed_path) == expected_sha256
    return proof


def geometry_proof(audit, context="integration-callback"):
    """Blender capture plus existing MachineLearning CPU verification.

    Blender needs only its bundled Python and bpy. NumPy/Shapely run in the
    existing MachineLearning interpreter against this process's actual meshes.
    The default remains compatible with campus integration callbacks.
    """
    import bpy

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint
    from refine_portsmouth_exterior207 import material_fingerprint

    assert context in {"build-roundtrip", "fresh", "integration-callback"}
    assert sha(BASE) == audit["baselineSha256"] == SHA
    assert sha(ROOT / audit["componentPath"]) == audit["componentSha256"]
    assert sha(OUT / "plan.json") == audit["sourcePlanSha256"]
    plan = json.loads((OUT / "plan.json").read_text())
    assert all(sha(ROOT / path) == h for path, h in plan["sourceHashes"].items())
    assert all(
        bpy.data.objects[n].hide_render
        and object_fingerprint(bpy.data.objects[n]) == fp
        for n, fp in plan["sourceFingerprints"].items()
    )
    assert (
        object_fingerprint(bpy.data.objects[plan["roofObject"]])
        == plan["roofFingerprint"]
    )
    assert bpy.data.materials["RCS224_glass"]["webOpacity"] == 0.25
    material_graphs = {
        name: material_fingerprint(bpy.data.materials[name])
        for name in plan["materials"]
    }
    assert material_graphs == audit["reusedMaterialGraphs"] | audit["newMaterialGraphs"]
    for name in plan["newMaterialNames"]:
        assert not any(
            n.type == "TEX_IMAGE" for n in bpy.data.materials[name].node_tree.nodes
        )
    observed = copy.deepcopy(plan)
    object_fingerprints, object_owners, uv_count = {}, {}, 0
    source_batches = {b["name"]: b for b in plan["batches"]}
    for batch in observed["batches"]:
        obj = bpy.data.objects[batch["name"]]
        assert not obj.hide_render and not obj.modifiers and obj.type == "MESH"
        assert sorted(c.name for c in obj.users_collection) == [OWNER]
        object_owners[obj.name] = sorted(c.name for c in obj.users_collection)
        object_fingerprints[obj.name] = object_fingerprint(obj)
        assert object_fingerprints[obj.name] == audit["addedFingerprints"][obj.name]
        assert [m.name for m in obj.data.materials] == plan["materials"]
        cursor = 0
        for part in batch["solids"]:
            count = len(part["vertices"])
            for index, record in enumerate(part["vertices"]):
                record["world"] = list(
                    obj.matrix_world @ obj.data.vertices[cursor + index].co
                )
            cursor += count
        assert cursor == len(obj.data.vertices)
        # Reconstruct actual polygon connectivity/materials in each solid range.
        vertex_owner = {}
        offset = 0
        for pi, part in enumerate(batch["solids"]):
            for vi in range(len(part["vertices"])):
                vertex_owner[offset + vi] = (pi, vi)
            part["faces"] = []
            offset += len(part["vertices"])
        for face in obj.data.polygons:
            pi = vertex_owner[face.vertices[0]][0]
            assert len(face.vertices) == 3
            assert all(vertex_owner[v][0] == pi for v in face.vertices)
            part = batch["solids"][pi]
            assert face.material_index == part["slot"] and not face.use_smooth
            part["faces"].append([vertex_owner[v][1] for v in face.vertices])
            for loop_index, vertex_index in zip(
                face.loop_indices, face.vertices, strict=True
            ):
                local_index = vertex_owner[vertex_index][1]
                expected_uv = source_batches[obj.name]["solids"][pi]["vertices"][
                    local_index
                ]["uv"]
                actual_uv = list(
                    obj.data.uv_layers["Metric_facade_UV"].data[loop_index].uv
                )
                assert all(
                    abs(a - b) < 0.000002
                    for a, b in zip(actual_uv, expected_uv, strict=True)
                )
                part["vertices"][local_index]["uv"] = actual_uv
                uv_count += 1
    builder_pid = audit["builderProcessID"]
    if context == "fresh":
        assert os.getpid() != builder_pid, "Fresh proof requires a new Blender process"
    snapshot = {
        "provenance": {
            "capturedFromBlenderMeshDatablocks": True,
            "captureContext": context,
            "blenderVersion": bpy.app.version_string,
            "blenderProcessID": os.getpid(),
            "builderProcessID": builder_pid,
            "freshBlenderProcess": context == "fresh" and os.getpid() != builder_pid,
            "baselineSha256": SHA,
            "componentPath": audit["componentPath"],
            "componentSha256": audit["componentSha256"],
            "sourcePlanSha256": audit["sourcePlanSha256"],
            "verifierScriptSha256": sha(Path(__file__)),
            "cpuRunnerScriptSha256": sha(CPU_RUNNER),
        },
        "actualPlan": observed,
        "actualObjectFingerprints": object_fingerprints,
        "actualObjectOwners": object_owners,
        "actualMaterialGraphs": material_graphs,
        "metricUVLoopsChecked": uv_count,
    }
    observed_path = OUT / f"observed-{context}.json"
    proof_path = OUT / f"observed-{context}-cpu-verification.json"
    observed_path.write_text(json.dumps(snapshot, indent=2) + "\n")
    observed_sha = sha(observed_path)
    request = {
        "observedPath": str(observed_path),
        "observedSha256": observed_sha,
        "proofPath": str(proof_path),
    }
    environment = dict(os.environ)
    for key in ("PYTHONHOME", "PYTHONPATH", "PYTHONEXECUTABLE", "__PYVENV_LAUNCHER__"):
        environment.pop(key, None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    assert ML_PYTHON.is_file()
    completed = subprocess.run(
        [str(ML_PYTHON), str(CPU_RUNNER)],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        cwd=str(ROOT),
        env=environment,
        timeout=45,
        check=False,
    )
    assert completed.returncode == 0, (
        "MachineLearning actual-mesh proof failed",
        completed.stdout[-2000:],
        completed.stderr[-5000:],
    )
    proof = json.loads(proof_path.read_text())
    assert proof["status"] == "passed-bounded-actual-native-facade"
    assert proof["observedActualPlanSha256"] == sha(observed_path) == observed_sha
    assert proof["componentSha256"] == audit["componentSha256"]
    assert proof["sourcePlanSha256"] == audit["sourcePlanSha256"]
    assert proof["blenderProcessID"] == os.getpid()
    assert proof["cpuProcessID"] != os.getpid()
    assert proof["captureContext"] == context
    return proof


def main(stage="fresh"):
    if stage == "cpu":
        plan = json.loads((OUT / "plan.json").read_text())
        result = cpu_proof(plan)
        (OUT / "cpu-preflight.json").write_text(json.dumps(result, indent=2) + "\n")
        return
    import bpy

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import (
        object_fingerprint,
        set_layer_hidden,
        update_scene,
    )
    from refine_houghton262 import capture

    assert sha(BASE) == SHA
    audit = json.loads((OUT / "audit.json").read_text())
    assert (
        audit["baselineSha256"] == SHA
        and sha(ROOT / audit["componentPath"]) == audit["componentSha256"]
    )
    assert sha(ROOT / audit["sourcePlan"]) == audit["sourcePlanSha256"]
    assert all(sha(ROOT / p) == h for p, h in audit["sourceHashes"].items())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    images = sorted(i.name for i in bpy.data.images)
    assert len(before["objects"]) == 8770 and len(before["materials"]) == 2355
    with bpy.data.libraries.load(str(ROOT / audit["componentPath"]), link=False) as (
        _,
        destination,
    ):
        destination.objects = list(audit["addedObjects"])
    for obj in destination.objects:
        for i, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[i] = bpy.data.materials[name]
        bpy.data.collections[OWNER].objects.link(obj)
        obj.hide_render = False
        set_layer_hidden(obj, False)
    for material in list(bpy.data.materials):
        if (
            material.name not in before["materials"]
            and material.name not in audit["newMaterialGraphs"]
        ):
            assert material.users == 0
            bpy.data.materials.remove(material)
    for name in audit["archivedObjects"]:
        bpy.data.objects[name].hide_render = True
        set_layer_hidden(bpy.data.objects[name], True)
    update_scene()
    after = capture()
    for name, value in before["objects"].items():
        expected = dict(value)
        if name in audit["archivedObjects"]:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
        assert after["visibility"][name] == (
            [True, before["visibility"][name][1], True]
            if name in audit["archivedObjects"]
            else before["visibility"][name]
        ), name
    assert set(after["objects"]) == set(before["objects"]) | set(audit["addedObjects"])
    assert after["materials"] == before["materials"] | audit["newMaterialGraphs"]
    assert after["rooms"] == before["rooms"] and len(after["rooms"]) == 35
    assert after["campusRooms"] == before["campusRooms"]
    assert sorted(i.name for i in bpy.data.images) == images
    assert all(
        object_fingerprint(bpy.data.objects[n]) == f
        for n, f in audit["addedFingerprints"].items()
    )
    assert os.getpid() != audit["builderProcessID"]
    result = {
        "status": "passed-bounded-candidate",
        "freshBlenderProcess": True,
        "baselineSha256": SHA,
        "componentSha256": audit["componentSha256"],
        "originalObjectsProtected": 8770,
        "originalMaterialGraphsProtected": 2355,
        "roomMembershipsProtected": 35,
        "actualMeshProof": geometry_proof(audit, context="fresh"),
        "allOriginalRoadTerrainRoofAndOtherBuildingsPreserved": True,
        "wholeNativeSaved": False,
    }
    assert sha(BASE) == SHA
    (OUT / "fresh-process-verification.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("LINDSEY277_FRESH_VERIFIED", audit["componentSha256"], flush=True)


if __name__ == "__main__":
    main()
