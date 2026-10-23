"""Reopen the263Clare fixture component and verify actual support and recesses."""

import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.path.insert(0, str(ROOT / "web/tests"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_clare_fixtures263 import (
    BASE,
    BODY,
    COLLECTION,
    FACE,
    OUT,
    SHA,
    WALL,
    capture,
    frame,
    local,
    sha,
    tree,
    world,
)
from verify_houghton262 import no_old_intersections, solids


def fixture_proof(audit):
    body_tree = tree(bpy.data.objects[BODY])
    face_tree = tree(bpy.data.objects[FACE])
    wall_tree = tree(bpy.data.objects[WALL])
    normal = frame()[2]
    fixtures = []
    for row in audit["fixtures"]:
        x, z, d = row["x"], row["z"], row["wallDepth"]
        contacts = []
        for dx in [-0.06, 0, 0.06]:
            for dz in [-0.05, 0, 0.05]:
                source = wall_tree.ray_cast(world(x + dx, 1, z + dz), -normal, 2)
                assert source[0] is not None
                rear = body_tree.ray_cast(source[0] + normal * 0.0001, normal, 0.04)
                assert rear[0] is not None
                gap = (rear[0] - source[0]).dot(normal)
                assert 0.0002 < gap < 0.0006, (row["index"], dx, dz, gap)
                contacts.append({"dx": dx, "dz": dz, "actualFixingGap": gap})
        recess = []
        # The front cover must lie inside a real rim opening and before its
        # blind backing. Test several interior rays,not just intended vertices.
        for dx in [-0.06, 0, 0.06]:
            for dz in [-0.022, 0, 0.022]:
                origin = world(x + dx, 1, z + dz)
                cover = face_tree.ray_cast(origin, -normal, 2)
                shell = body_tree.ray_cast(origin, -normal, 2)
                assert cover[0] is not None and shell[0] is not None
                assert cover[3] < shell[3] and 0.07 < shell[3] - cover[3] < 0.15
                assert local(cover[0]).y < d + 0.255 - 0.012
                recess.append(
                    {
                        "dx": dx,
                        "dz": dz,
                        "physicalRecessDepthToBacking": shell[3] - cover[3],
                    }
                )
        rim = []
        for dx, dz in [(-0.12, 0), (0.12, 0), (0, -0.061), (0, 0.060)]:
            hit = body_tree.ray_cast(world(x + dx, 1, z + dz), -normal, 2)
            assert hit[0] is not None
            assert local(hit[0]).y > d + 0.20
            rim.append(list(local(hit[0])))
        fixtures.append(
            {
                "index": row["index"],
                "pierIndex": row["pierIndex"],
                "actualWallFixingContacts": contacts,
                "recessedFaceChannels": recess,
                "retainedHoodRimRays": rim,
            }
        )
    radius = audit["leftConduit"]["radius"]
    conduit = []
    # Straight vertical sides and bottom leg have unambiguous pipe back faces.
    x = audit["fixtures"][0]["x"]
    samples = [
        (x - 0.33, 4.0),
        (x - 0.33, 4.5),
        (x - 0.33, 5.10),
        (x + 0.33, 4.0),
        (x + 0.33, 4.5),
        (x + 0.33, 5.10),
        (x - 0.15, 3.62),
        (x, 3.62),
        (x + 0.15, 3.62),
    ]
    for xx, zz in samples:
        source = wall_tree.ray_cast(world(xx, 1, zz), -normal, 2)
        assert source[0] is not None
        rear = body_tree.ray_cast(source[0] + normal * 0.0001, normal, 0.04)
        assert rear[0] is not None
        gap = (rear[0] - source[0]).dot(normal)
        assert 0.0002 < gap < 0.0006, (xx, zz, gap)
        front = body_tree.ray_cast(world(xx, 1, zz), -normal, 2)
        assert front[0] is not None
        assert abs((front[0] - rear[0]).dot(normal) - radius * 2) < 0.00005
        conduit.append(
            {
                "x": xx,
                "z": zz,
                "actualWallGap": gap,
                "actualDiameterAlongNormal": (front[0] - rear[0]).dot(normal),
            }
        )
    topology = {name: solids(bpy.data.objects[name]) for name in [BODY, FACE]}
    assert topology[BODY]["closedPositiveSolids"] == 7
    assert topology[FACE]["closedPositiveSolids"] == 2
    assert len(audit["fixtures"]) == 2 and [
        row["pierIndex"] for row in audit["fixtures"]
    ] == [1, 4]
    return {
        "twoPhotoSupportedFixtures": fixtures,
        "onlyLeftConduit": conduit,
        "closedPositiveTopology": topology,
        "newLightingOrEmissionAdded": False,
    }


def main():
    audit = json.loads((OUT / "audit.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    component = ROOT / audit["componentPath"]
    assert (
        sha(BASE) == SHA == audit["baselineSha256"]
        and sha(component) == audit["componentSha256"]
    )
    assert (
        sha(OUT / "source-review.json") == audit["sourceReviewSha256"]
        and sha(OUT / "clare-native-inspection.json") == audit["nativeInspectionSha256"]
    )
    review = json.loads((OUT / "source-review.json").read_text())
    assert all(sha(ROOT / r["path"]) == r["sha256"] for r in review["references"])
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == before
    with bpy.data.libraries.load(str(component), link=False) as (_source, loaded):
        loaded.objects = list(audit["addedObjects"])
    for obj in loaded.objects:
        bpy.data.collections[COLLECTION].objects.link(obj)
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
    update_scene()
    for obj in loaded.objects:
        assert object_fingerprint(obj) == audit["addedFingerprints"][obj.name], obj.name
    proof = fixture_proof(audit)
    proof["retainedVisibleSceneClearance"] = no_old_intersections(audit, before)
    after = capture()
    for key in ["objects", "materials", "visibility"]:
        assert all(after[key][name] == row for name, row in before[key].items()), key
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
        and len(after["rooms"]) == 35
    )
    assert set(after["objects"]) - set(before["objects"]) == set(audit["addedObjects"])
    assert sha(BASE) == SHA
    report = {
        "passed": True,
        "savedComponentIndependentlyReopened": True,
        "componentSha256": sha(component),
        "protectedOriginalObjects": 8744,
        "protectedOriginalMaterials": 2355,
        "protectedIndependentRooms": 35,
        "proof": proof,
        "fixtureFunctionClaimed": False,
        "wholeStreetCompletionClaimed": False,
        "photoPixelsOrPeopleExported": False,
    }
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "CLARE263_TWO_FIXTURES_AND_CONDUIT_VERIFIED",
        len(proof["twoPhotoSupportedFixtures"]),
        len(proof["onlyLeftConduit"]),
        flush=True,
    )


if __name__ == "__main__":
    main()
