"""Fresh verification of the complete275 campus and each declared component.

Reopens269and275 independently; all original geometry, normals, UVs, material
graphs, owners, properties, modifiers and35room memberships are protected.
Every configured component reruns its own independent actual-mesh proof.
"""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/stage275"


def tools_module():
    sys.path.insert(0, str(ROOT / "web/tools"))
    import integrate_campus275

    return integrate_campus275


def capture_source(config):
    helper = config.load_module(
        "campus275_original_state", "web/tests/verify_campus241.py"
    )
    helper.BASE_SHA = config.BASE_SHA
    state = helper.capture_source()
    state["visibility"] = {
        o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
    }
    return state


def surface_probes(config, audits):
    probes = []
    for spec in config.COMPONENTS:
        for name in audits[spec.folder]["addedObjects"]:
            obj = bpy.data.objects[name]
            if obj.type != "MESH":
                continue
            obj.data.calc_loop_triangles()
            points = [obj.matrix_world @ v.co for v in obj.data.vertices]
            tree = BVHTree.FromPolygons(
                points,
                [tuple(t.vertices) for t in obj.data.loop_triangles],
                all_triangles=True,
                epsilon=0,
            )
            samples = []
            for face in list(obj.data.polygons)[
                :: max(1, len(obj.data.polygons) // 24)
            ]:
                centre = sum((points[i] for i in face.vertices), Vector()) / len(
                    face.vertices
                )
                normal = (
                    obj.matrix_world.to_3x3().inverted().transposed() @ face.normal
                ).normalized()
                origin = centre + normal * 0.03
                hit = tree.ray_cast(origin, -normal, 0.061)
                if hit[0] is not None and abs(hit[3] - 0.03) < 0.0001:
                    samples.append(
                        {
                            "code": spec.code,
                            "object": name,
                            "origin": list(origin),
                            "direction": list(-normal),
                            "distance": hit[3],
                            "materials": [m.name for m in obj.data.materials],
                        }
                    )
            assert samples, name
            probes.extend(samples)
    return probes


def main():
    config = tools_module()
    from integrate_exterior_round194 import object_fingerprint, update_scene

    assert config.sha(config.BASE) == config.BASE_SHA
    record = json.loads((OUT / "building-refinement.json").read_text())
    manifest = json.loads((OUT / "accepted-components.json").read_text())
    current_sha = config.sha(config.DESTINATION)
    assert record["baselineSha256"] == manifest["baselineSha256"] == config.BASE_SHA
    assert current_sha == record["sourceModelSha256"] == manifest["sourceModelSha256"]
    assert manifest["components"] == [vars(s) for s in config.COMPONENTS]
    assert manifest["authoringScriptSha256"] == config.sha(
        ROOT / "web/tools/integrate_campus275.py"
    )
    assert manifest["verificationScriptSha256"] == config.sha(Path(__file__))
    audits = config.accepted_components()
    added = set().union(*(set(a["addedObjects"]) for a in audits.values()))
    archived = set().union(*(set(a["archivedObjects"]) for a in audits.values()))
    assert (
        set(record["addedObjects"]) == added
        and set(record["archivedObjects"]) == archived
    )
    assert record["changedObjects"] == []
    previous = json.loads(
        (ROOT / "result/blender/stage269/building-refinement.json").read_text()
    )
    for key in ("libraryNativeViewRouting", "librarySourceArchiveScene"):
        assert record[key] == previous[key]
    bpy.ops.wm.open_mainfile(filepath=str(config.BASE))
    update_scene()
    before = capture_source(config)
    assert len(before["objects"]) == 8752 and len(before["materials"]) == 2355
    images = sorted(i.name for i in bpy.data.images)
    bpy.ops.wm.open_mainfile(filepath=str(config.DESTINATION))
    update_scene()
    after = capture_source(config)
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
    assert set(after["objects"]) == set(before["objects"]) | added
    declared_new_materials = {
        n: value
        for a in audits.values()
        for n, value in a.get("newMaterialGraphs", {}).items()
    }
    assert not set(declared_new_materials) & set(before["materials"])
    assert after["materials"] == before["materials"] | declared_new_materials
    assert after["rooms"] == before["rooms"] and len(after["rooms"]) == 35
    assert after["campusRooms"] == before["campusRooms"]
    assert sorted(i.name for i in bpy.data.images) == images
    proofs = {}
    for spec in config.COMPONENTS:
        audit = audits[spec.folder]
        for name in audit["addedObjects"]:
            obj = bpy.data.objects[name]
            assert (
                not obj.hide_render
                and object_fingerprint(obj)
                == audit["addedFingerprints"][name]
                == record["addedFingerprints"][name]
            )
            assert [m.name for m in obj.data.materials] == audit[
                "replacementMaterialBindings"
            ][name]
        verifier = config.load_module(
            "campus275_geometry_" + spec.folder, spec.verifier
        )
        proofs[spec.folder] = verifier.geometry_proof(audit)
    probes = surface_probes(config, audits)
    assert capture_source(config) == after
    assert (
        config.sha(config.BASE) == config.BASE_SHA
        and config.sha(config.DESTINATION) == current_sha
    )
    (OUT / "production-probes.json").write_text(json.dumps(probes, indent=2) + "\n")
    result = {
        "status": "passed-bounded-integration",
        "freshBlenderProcess": True,
        "baselineSha256": config.BASE_SHA,
        "sourceModelSha256": current_sha,
        "originalObjectsProtected": len(before["objects"]),
        "originalMaterialsProtected": len(before["materials"]),
        "roomMembershipsProtected": len(before["rooms"]),
        "allOriginalGeometryNormalsUVsOwnersPropertiesModifiersPreserved": True,
        "onlyDeclaredVisibilityChanges": sorted(archived),
        "actualGeometryProofs": proofs,
        "productionProbes": len(probes),
        "completeCampusSavedAndReopened": True,
        "unlistedComponentsExcluded": True,
        "wholeBuildingCompletionClaimed": False,
    }
    (OUT / "independent-verification.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("CAMPUS275_INDEPENDENTLY_VERIFIED", current_sha, flush=True)


if __name__ == "__main__":
    main()
