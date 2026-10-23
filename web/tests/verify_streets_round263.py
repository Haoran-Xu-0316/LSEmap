"""Verify the saved complete campus and actual street furniture geometry."""

import importlib.util
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from integrate_streets_round263 import BASE_SHA, accepted_components, sha
from refine_houghton262 import capture


def main():
    folder = ROOT / "result/blender/stage263"
    record = json.loads((folder / "building-refinement.json").read_text())
    baseline = ROOT / "result/blender/LSE_campus_detailed_v262.blend"
    current = ROOT / "result/blender/LSE_campus_detailed_v263.blend"
    assert sha(baseline) == record["baselineSha256"] == BASE_SHA
    current_sha = sha(current)
    assert current_sha == record["sourceModelSha256"]
    audits = accepted_components()
    expected_added = set().union(*(set(a["addedObjects"]) for a in audits.values()))
    assert set(record["addedObjects"]) == expected_added
    expected_archived = set().union(
        *(set(a["archivedObjects"]) for a in audits.values())
    )
    assert set(record["archivedObjects"]) == expected_archived
    assert record["changedObjects"] == []
    bpy.ops.wm.open_mainfile(filepath=str(baseline))
    update_scene()
    before = capture()
    assert len(before["objects"]) == 8744 and len(before["materials"]) == 2355
    bpy.ops.wm.open_mainfile(filepath=str(current))
    update_scene()
    after = capture()
    for name, state in before["objects"].items():
        expected = dict(state)
        if name in expected_archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    for name, state in before["visibility"].items():
        expected = [True, state[1], True] if name in expected_archived else state
        assert after["visibility"][name] == expected, name
    assert all(
        after["materials"][n] == value for n, value in before["materials"].items()
    )
    expected_materials = {
        n: value
        for a in audits.values()
        for n, value in a.get("newMaterialGraphs", {}).items()
    }
    for name, value in expected_materials.items():
        assert after["materials"][name] == value, name
    assert set(after["materials"]) - set(before["materials"]) == set(expected_materials)
    assert after["rooms"] == before["rooms"] and len(after["rooms"]) == 35
    assert after["campusRooms"] == before["campusRooms"]
    assert set(after["objects"]) - set(before["objects"]) == expected_added
    for audit in audits.values():
        for name in audit["addedObjects"]:
            obj = bpy.data.objects[name]
            assert not obj.hide_render
            assert (
                object_fingerprint(obj)
                == audit["addedFingerprints"][name]
                == record["addedFingerprints"][name]
            )
            assert [m.name for m in obj.data.materials] == audit[
                "replacementMaterialBindings"
            ][name]
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    modules = {}
    for name in ["houghton263", "sheffield263"]:
        path = (
            ROOT
            / "web/tests"
            / (
                "verify_clare_fixtures263.py"
                if name == "houghton263"
                else "verify_sheffield263.py"
            )
        )
        spec = importlib.util.spec_from_file_location(name + "_proof", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules[name] = module
    houghton = modules["houghton263"]
    proofs = {
        "houghton263": houghton.fixture_proof(audits["houghton263"]),
        "sheffield263": modules["sheffield263"].geometry_proof(audits["sheffield263"]),
    }
    proofs["houghton263"]["retainedSceneSurfaceClearance"] = (
        houghton.no_old_intersections(audits["houghton263"], before)
    )
    probes = []
    for code, folder_name in [("OLD", "houghton263"), ("LANDSCAPE", "sheffield263")]:
        audit = audits[folder_name]
        owner_trees = []
        for member in bpy.data.collections[audit["destinationCollection"]].all_objects:
            if member.type != "MESH" or member.hide_render:
                continue
            member.data.calc_loop_triangles()
            owner_trees.append(
                (
                    member.name,
                    BVHTree.FromPolygons(
                        [member.matrix_world @ v.co for v in member.data.vertices],
                        [tuple(t.vertices) for t in member.data.loop_triangles],
                        all_triangles=True,
                    ),
                )
            )
        for name in audit["addedObjects"]:
            # The retained furniture subset is verified face-for-face by the
            # native proof; only the new cycle bank belongs to the SAW crop.
            if (
                name
                == "SHEFFIELD263_Mapped_furniture_retained_without_single_cycle_stand"
            ):
                continue
            obj = bpy.data.objects[name]
            mesh = obj.data
            mesh.calc_loop_triangles()
            points = [obj.matrix_world @ v.co for v in mesh.vertices]
            tree = BVHTree.FromPolygons(
                points,
                [tuple(t.vertices) for t in mesh.loop_triangles],
                all_triangles=True,
            )
            samples = []
            step = max(1, len(mesh.polygons) // 12)
            for face in list(mesh.polygons)[::step]:
                center = sum((points[i] for i in face.vertices), Vector()) / len(
                    face.vertices
                )
                normal = (
                    obj.matrix_world.to_3x3().inverted().transposed() @ face.normal
                ).normalized()
                origin = center + normal * 0.03
                hit = tree.ray_cast(origin, -normal, 0.061)
                if hit[0] is None or abs(hit[3] - 0.03) > 0.0001:
                    continue
                nearest = []
                for other_name, other_tree in owner_trees:
                    other_hit = other_tree.ray_cast(origin, -normal, 0.061)
                    if other_hit[0] is not None:
                        nearest.append((other_hit[3], other_name))
                nearest.sort()
                # Shared load-bearing interfaces legitimately have two coincident
                # surfaces. Compare visible, unambiguous faces across Draco assets;
                # component checks separately prove those structural contacts.
                if nearest and any(
                    other_name != nearest[0][1]
                    and abs(distance - nearest[0][0]) < 0.0001
                    for distance, other_name in nearest
                ):
                    continue
                if (
                    not nearest
                    or nearest[0][1] != name
                    or abs(nearest[0][0] - 0.03) > 0.0001
                ):
                    continue
                samples.append(
                    {
                        "code": code,
                        "object": name,
                        "kind": "new-fixture-surface",
                        "origin": list(origin),
                        "direction": list(-normal),
                        "distance": hit[3],
                        "materials": [m.name for m in obj.data.materials],
                    }
                )
            assert samples, name
            probes.extend(samples)
    (folder / "production-probes.json").write_text(json.dumps(probes, indent=2) + "\n")
    assert capture() == after
    assert sha(baseline) == BASE_SHA and sha(current) == current_sha
    result = {
        "completeModelReopened": True,
        "sourceModelSha256": current_sha,
        "baselineSha256": BASE_SHA,
        "originalObjectsProtected": len(before["objects"]),
        "originalMaterialGraphsProtected": len(before["materials"]),
        "roomStudiesProtected": len(after["rooms"]),
        "roomMembersProtected": sum(len(m) for m in after["rooms"].values()),
        "roomMembershipUnchanged": True,
        "campusRoomMembershipUnchanged": True,
        "addedObjects": record["addedObjects"],
        "archivedObjects": record["archivedObjects"],
        "componentProofsInReopenedCompleteScene": proofs,
    }
    (folder / "complete-protection.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("STREETS263_COMPLETE_PROTECTED", len(before["objects"]), flush=True)


if __name__ == "__main__":
    main()
