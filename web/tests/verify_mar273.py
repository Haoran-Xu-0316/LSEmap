"""Fresh Blender verification of MAR273's bounded two-floor coordination."""

import collections
import importlib.util
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
import refine_mar273 as builder
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_portsmouth_exterior207 import (
    material_fingerprint,
)

spec = importlib.util.spec_from_file_location(
    "mar269_geometry_helpers", ROOT / "web/tests/verify_mar269.py"
)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def apply_component(audit):
    before = builder.capture()
    with bpy.data.libraries.load(str(ROOT / audit["componentPath"]), link=False) as (
        _,
        destination,
    ):
        destination.objects = list(audit["addedObjects"])
    for obj in destination.objects:
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        bpy.data.collections[builder.OWNER].objects.link(obj)
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
    builder.protection(before, audit["addedObjects"], audit["archivedObjects"])
    return before


def door_proof(tree, doors, low, head):
    openings = heads = 0
    for door in doors:
        polygon = door.get("world")
        if isinstance(polygon, list) and polygon and isinstance(polygon[0], dict):
            polygon = polygon[0]["outer"]
        if polygon[0] == polygon[-1]:
            polygon = polygon[:-1]
        centre = door.get("centre") or helpers.polygon_centroid(polygon)
        if "normal" in door:
            normal = Vector((*door["normal"], 0))
            normal.normalize()
            tangent = Vector((normal.y, -normal.x, 0))
        else:
            a, b = polygon[0], polygon[-1]
            tangent = Vector((b[0] - a[0], b[1] - a[1], 0))
            tangent.normalize()
            normal = Vector((-tangent.y, tangent.x, 0))
        for offset in [-0.3, 0, 0.3]:
            for height in [0.2, 1.0, 2.0]:
                point = (
                    Vector((*centre, low + height)) + tangent * offset - normal * 0.45
                )
                assert tree.ray_cast(point, normal, 0.9)[0] is None, (
                    door["id"],
                    offset,
                    height,
                )
                openings += 1
            point = Vector((*centre, head + 0.1)) + tangent * offset - normal * 0.45
            assert tree.ray_cast(point, normal, 0.9)[0] is not None, (
                door["id"],
                "missing-head",
            )
            heads += 1
    return {
        "openingRays": openings,
        "headRays": heads,
        "doorClearHeightEstimateM": head - low,
    }


def thickness_proof(tree, holes, height):
    widths = []
    for ring in holes:
        signed = sum(
            a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1])
        )
        for a, b in zip(ring, ring[1:] + ring[:1]):
            tangent = Vector((b[0] - a[0], b[1] - a[1], 0))
            if tangent.length < 0.05:
                continue
            tangent.normalize()
            outward = Vector((tangent.y, -tangent.x, 0)) * (1 if signed > 0 else -1)
            for t in [0.1, 0.5, 0.9]:
                point = (
                    Vector((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), height))
                    - outward * 0.01
                )
                hit = tree.ray_cast(point, outward, 0.05)
                assert hit[0] is not None, ("missing-inner-wall", list(point))
                exit_hit = tree.ray_cast(hit[0] + outward * 0.00005, outward, 0.6)
                assert exit_hit[0] is not None
                width = exit_hit[3] + 0.00005
                assert width > 0.20, ("thin-wall", width, list(point))
                widths.append(width)
    assert len(widths) > 30
    return {
        "samples": len(widths),
        "minimumActualRayThicknessM": min(widths),
        "height": height,
    }


def solid_proof(obj):
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(e.is_manifold for e in bm.edges), obj.name
    directed = collections.Counter(
        (a, b)
        for face in obj.data.polygons
        for a, b in zip(
            list(face.vertices), list(face.vertices)[1:] + list(face.vertices)[:1]
        )
    )
    assert all(n == directed[(b, a)] for (a, b), n in directed.items()), obj.name
    volume = bm.calc_volume(signed=True)
    assert volume > 0
    bm.free()
    return volume


def wall_contact_proof(obj, low, top, bottom_tree, top_tree):
    contacts = {"feet": 0, "heads": 0}
    for triangle in helpers.rows(obj):
        is_low = all(abs(point.z - low) < 1e-6 for point in triangle)
        is_top = all(abs(point.z - top) < 1e-6 for point in triangle)
        if not (is_low or is_top):
            continue
        for weights in [
            (1 / 3, 1 / 3, 1 / 3),
            (0.6, 0.2, 0.2),
            (0.2, 0.6, 0.2),
            (0.2, 0.2, 0.6),
        ]:
            point = sum(
                (corner * weight for corner, weight in zip(triangle, weights)), Vector()
            )
            if is_low:
                hit = bottom_tree.ray_cast(
                    point + Vector((0, 0, 0.01)), Vector((0, 0, -1)), 0.02
                )
                key = "feet"
            else:
                hit = top_tree.ray_cast(
                    point - Vector((0, 0, 0.01)), Vector((0, 0, 1)), 0.02
                )
                key = "heads"
            assert hit[0] is not None and abs(hit[0].z - point.z) < 0.00001, (
                obj.name,
                "unsupported-wall",
                key,
                list(point),
            )
            contacts[key] += 1
    assert min(contacts.values()) >= 20
    return contacts


def core_seam_proof(retained_tree, extension_tree, probes, tolerance):
    distances = []
    for probe in probes:
        point = Vector((*probe["pointXY"], probe["height"]))
        outward = Vector((*probe["outwardXY"], 0))
        old_hit = retained_tree.ray_cast(point - outward * 0.02, outward, 0.04)
        new_hit = extension_tree.ray_cast(point + outward * 0.02, -outward, 0.04)
        assert old_hit[0] is not None and new_hit[0] is not None, (
            "missing-core-joint",
            probe,
        )
        gap = (old_hit[0] - new_hit[0]).length
        assert gap <= tolerance, ("core-joint-gap", gap, probe)
        distances.append(gap)
    assert len(distances) >= 2
    return {
        "samples": len(distances),
        "maximumActualSeamDistanceM": max(distances),
        "toleranceM": tolerance,
    }


def fourth_original_fill_proof(plan):
    fourth = next(
        row
        for row in plan["registration"]["shafts"]
        if row["id"] == "east-lower-transverse"
    )
    checked = 0
    for name, ring, height, depth in [
        (
            "MAR269_second_floor_finish_with_source_shafts",
            fourth["secondInner"],
            12.800000190734863,
            0.025001,
        ),
        ("MAR258_third_south_deck_solid", fourth["thirdInner"], 17.5, 0.320001),
    ]:
        old_tree = helpers.tree(helpers.rows(bpy.data.objects[name]))
        for xy in helpers.samples(ring):
            hit = old_tree.ray_cast(
                Vector((*xy, height + 0.02)), Vector((0, 0, -1)), depth + 0.04
            )
            assert hit[0] is not None, ("fourth-was-not-filled", name, xy)
            checked += 1
    assert checked > 60
    return {"originalFilledSamples": checked, "newOpeningNotPreviouslyPresent": True}


def geometry_proof(audit):
    plan = builder.read(audit["sourcePlan"])
    update_scene()
    assert plan["baselineSha256"] == builder.SHA
    holes = [r["outer"] for r in plan["envelopes"]]
    assert plan["shaftCount"] == 4 and len(holes) == 4
    fourth_fill = fourth_original_fill_proof(plan)
    checks = []
    all_rows = []
    for row in plan["objects"]:
        obj = bpy.data.objects[row["replacement"]]
        assert (
            not obj.hide_render
            and object_fingerprint(obj) == audit["addedFingerprints"][obj.name]
        )
        assert sorted(c.name for c in obj.users_collection) == [builder.OWNER]
        assert [m.name for m in obj.data.materials] == row["materials"]
        volume = solid_proof(obj)
        triangles = helpers.rows(obj)
        all_rows.extend(triangles)
        retained = 0
        if row["sourceObject"]:
            source = bpy.data.objects[row["sourceObject"]]
            assert (
                source.hide_render
                and object_fingerprint(source) == row["sourceFingerprint"]
            )
            original_volume = solid_proof(source)
            assert (
                abs((original_volume - volume) - row["expectedRemovedVolumeM3"]) < 0.003
            ), (obj.name, "removed-volume")

            def top_area(mesh_object, height=row["sourceZ"][1]):
                return sum(
                    abs((triangle[1] - triangle[0]).cross(triangle[2] - triangle[0]).z)
                    / 2
                    for triangle in helpers.rows(mesh_object)
                    if all(abs(point.z - height) < 1e-6 for point in triangle)
                )

            assert (
                abs(
                    (top_area(source) - top_area(obj)) - row["expectedTopAreaRemovedM2"]
                )
                < 0.0005
            ), (obj.name, "removed-top-area")
            actual = collections.Counter(
                helpers.signature(obj, f) for f in obj.data.polygons
            )
            for face in row["faceRecords"]:
                if face["role"] != "retained-native-face":
                    continue
                signature = helpers.signature(
                    source, source.data.polygons[face["sourceFace"]]
                )
                assert actual[signature] > 0, (
                    obj.name,
                    face["sourceFace"],
                    "retained-face-UV",
                )
                actual[signature] -= 1
                retained += 1
        else:
            assert (
                obj["sourceScope"]
                == "Second-to-Third bounded lift-core coordination;inherited height and estimated2.1mdoor heads"
            )
        checks.append(
            {
                "object": obj.name,
                "closedManifoldPositiveVolumeM3": volume,
                "triangles": len(triangles),
                "exactRetainedNativeFacesAndUVs": retained,
            }
        )
    new = helpers.tree(all_rows)
    # Include every visible MAR mesh so unrelated retained context cannot silently
    # obstruct an aperture. Stop below the deliberately retained21.9mplate.
    visible = set(bpy.data.collections["MAR_PUBLIC_INTERIOR_study"].all_objects) | set(
        bpy.data.collections["MAR_EXTERIOR"].all_objects
    )
    context = helpers.tree(
        [
            t
            for obj in visible
            if obj.type == "MESH" and not obj.hide_render
            for t in helpers.rows(obj)
        ]
    )
    continuous = 0
    for ring in holes:
        for p in helpers.samples(ring):
            origin = Vector((*p, 21.85))
            assert new.ray_cast(origin, Vector((0, 0, -1)), 9.45)[0] is None, (
                "new-core-obstruction",
                p,
            )
            assert context.ray_cast(origin, Vector((0, 0, -1)), 9.45)[0] is None, (
                "retained-context-obstruction",
                p,
            )
            continuous += 1
    deck = bpy.data.objects[
        next(
            r["replacement"]
            for r in plan["objects"]
            if r["sourceObject"] == "MAR258_third_south_deck_solid"
        )
    ]
    walls3 = bpy.data.objects[
        next(
            r["replacement"]
            for r in plan["objects"]
            if r["sourceObject"] == "MAR251_third_south_lift_core_walls"
        )
    ]
    walls2 = bpy.data.objects["MAR273_second_south_lift_core_walls"]
    extension = bpy.data.objects[plan["thirdExtension"]["object"]]
    projected = {}
    for obj, z in [
        (deck, 17.5),
        (walls3, 17.5),
        (extension, 17.5),
        (walls2, plan["secondWall"]["low"]),
    ]:
        triangles = [
            t for t in helpers.rows(obj) if all(abs(p.z - z) < 0.00001 for p in t)
        ]
        area = sum(helpers.clipped_area(ring, t) for ring in holes for t in triangles)
        assert area < 0.00015, (obj.name, "projected-cap", area)
        projected[obj.name] = area
    finish = bpy.data.objects[
        next(
            r["replacement"]
            for r in plan["objects"]
            if r["sourceObject"] == "MAR269_second_floor_finish_with_source_shafts"
        )
    ]
    finish_tree = helpers.tree(helpers.rows(finish))
    deck_tree = helpers.tree(helpers.rows(deck))
    contacts = wall_contact_proof(
        walls2,
        plan["secondWall"]["low"],
        plan["secondWall"]["top"],
        finish_tree,
        deck_tree,
    )
    assert min(contacts.values()) > 100
    ceiling_tree = helpers.tree(
        helpers.rows(bpy.data.objects[plan["unmodifiedHigherPlate"]])
    )
    extension_contacts = wall_contact_proof(
        extension,
        plan["thirdExtension"]["low"],
        plan["thirdExtension"]["top"],
        deck_tree,
        ceiling_tree,
    )
    wall2tree = helpers.tree(helpers.rows(walls2))
    retained3tree = helpers.tree(helpers.rows(walls3))
    extension_tree = helpers.tree(helpers.rows(extension))
    wall3tree = helpers.tree(helpers.rows(walls3) + helpers.rows(extension))
    seams = core_seam_proof(
        retained3tree,
        extension_tree,
        plan["thirdExtension"]["seamProbes"],
        plan["thirdExtension"]["seamToleranceM"],
    )
    upper_z = plan["thirdExtension"]["top"]
    old_tops = [
        triangle
        for triangle in helpers.rows(walls3)
        if all(abs(point.z - upper_z) < 1e-6 for point in triangle)
    ]
    new_tops = [
        triangle
        for triangle in helpers.rows(extension)
        if all(abs(point.z - upper_z) < 1e-6 for point in triangle)
    ]
    overlap = sum(
        helpers.clipped_area(triangle, old) for triangle in new_tops for old in old_tops
    )
    assert overlap < 0.00015, ("new-third-wall-overlap", overlap)
    doors2 = door_proof(
        wall2tree,
        plan["secondWall"]["doors"],
        plan["secondWall"]["low"],
        plan["secondWall"]["doorHead"],
    )
    doors3 = door_proof(
        wall3tree,
        plan["thirdExtension"]["doors"],
        plan["thirdExtension"]["low"],
        plan["thirdExtension"]["doorHead"],
    )
    thickness = [
        thickness_proof(wall2tree, holes, 15.2),
        thickness_proof(wall3tree, holes, 20.0),
    ]
    for name, value in audit["reusedMaterialGraphs"].items():
        assert material_fingerprint(bpy.data.materials[name]) == value
    assert (
        object_fingerprint(bpy.data.objects[plan["unmodifiedHigherPlate"]])
        == audit["retainedHigherPlateFingerprint"]
    )
    return {
        "status": "passed-bounded-four-shaft-second-to-third",
        "shaftCount": 4,
        "fourthOriginalFill": fourth_fill,
        "objects": checks,
        "actualMARContextContinuousAirRays": continuous,
        "testedAirZ": [12.4, 21.85],
        "actualHorizontalProjectedIntrusionM2": projected,
        "newSecondWallContacts": contacts,
        "newThirdExtensionContacts": extension_contacts,
        "actualCoreSeams": seams,
        "actualThirdWallBatchProjectedOverlapM2": overlap,
        "secondDoors": doors2,
        "thirdDoors": doors3,
        "actualWallThickness": thickness,
        "secondSourceAndThirdMeshEnvelopeOnly": True,
        "fullHeightShaftAcceptance": False,
        "higher21_9mPlateRetained": True,
        "limits": "Zdatums and2.1mheads are display estimates. Drawing-boundary deviations are consistent with held-out registration residuals;their cause is not proved. The21.9mplate remains uncut.",
    }


def main():
    audit = builder.read("result/blender/mar273/audit.json")
    assert (
        builder.sha(builder.BASE) == builder.SHA
        and builder.sha(ROOT / audit["componentPath"]) == audit["componentSha256"]
    )
    assert all(builder.sha(ROOT / p) == h for p, h in audit["sourceHashes"].items())
    bpy.ops.wm.open_mainfile(filepath=str(builder.BASE))
    update_scene()
    apply_component(audit)
    proof = geometry_proof(audit)
    result = {
        "status": "passed-bounded-four-shaft-two-floor-component",
        "shaftCount": 4,
        "baselineSha256": builder.SHA,
        "componentSha256": audit["componentSha256"],
        "freshBlenderProcess": True,
        "verificationScriptSha256": builder.sha(Path(__file__)),
        "authoringScriptSha256": builder.sha(ROOT / "web/tools/refine_mar273.py"),
        "actualMeshProof": proof,
        "originalObjectsProtected": 8752,
        "originalMaterialGraphsProtected": 2355,
        "roomMembershipsProtected": 35,
        "fullHeightShaftAcceptance": False,
        "wholeNativeSaved": False,
    }
    builder.write(builder.OUT / "fresh-process-verification.json", result)
    print("MAR273_FRESH_VERIFIED", audit["componentSha256"], flush=True)


if __name__ == "__main__":
    main()
