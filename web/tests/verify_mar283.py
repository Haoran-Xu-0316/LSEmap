"""Independent actual-mesh proof for MAR283's boundedGround lift correction.

Fresh Blender run; reads the immutable279campus and private component, checks
all original geometry, materials, visibility and35room memberships. Verifies
actual floor apertures, door airspace, support contact and retained native UVs.
"""

import collections
import importlib.util
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
import refine_mar283 as builder
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_portsmouth_exterior207 import material_fingerprint


def load_helper(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helpers = load_helper("mar283_geometry_helpers", "web/tests/verify_mar269.py")
prior = load_helper("mar283_contact_helpers", "web/tests/verify_mar273.py")


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
        bpy.data.collections[audit["objectOwners"][obj.name]].objects.link(obj)
        obj.hide_render = False
        set_layer_hidden(obj, False)
    for material in list(bpy.data.materials):
        if material.name not in before["materials"]:
            assert material.users == 0, material.name
            bpy.data.materials.remove(material)
    for name in audit["archivedObjects"]:
        bpy.data.objects[name].hide_render = True
        set_layer_hidden(bpy.data.objects[name], True)
    update_scene()
    builder.protection(before, audit["addedObjects"], audit["archivedObjects"])
    return before


def top_area(obj, height):
    return sum(
        abs((t[1] - t[0]).cross(t[2] - t[0]).z) / 2
        for t in helpers.rows(obj)
        if all(abs(p.z - height) < 1e-6 for p in t)
    )


def source_thickness_proof(tree, plan, height):
    """Locate both actual surfaces at the independent PDFnormal intersections."""
    widths = []
    discrepancies = []
    tolerance = plan["sourceThicknessNumericToleranceM"]
    assert tolerance == 0.0005
    for probe in plan["sourceThicknessProbes"]:
        origin = Vector((*probe["originXY"], height))
        normal = Vector((*probe["outwardXY"], 0))
        hit = tree.ray_cast(origin, normal, 0.05)
        assert hit[0] is not None, ("missing-source-inner-wall", probe)
        assert abs(hit[3] - probe["sourceEntryDistanceM"]) < tolerance, (
            "wrong-source-inner-wall",
            probe,
            hit[3],
        )
        # The search end follows the independently calculated source exit. This
        # supports the0.88mGround wall without accepting a thinner wall.
        exit_hit = tree.ray_cast(
            hit[0] + normal * 0.00005, normal, probe["sourceThicknessM"] + 0.002
        )
        assert exit_hit[0] is not None, ("missing-source-outer-wall", probe)
        expected_exit = origin + normal * probe["sourceExitDistanceM"]
        error = (exit_hit[0] - expected_exit).length
        assert error < tolerance, ("wrong-source-outer-wall", probe, error)
        width = exit_hit[3] + 0.00005
        assert width > 0.2 and abs(width - probe["sourceThicknessM"]) < tolerance, (
            "incorrect-source-thickness",
            probe,
            width,
        )
        widths.append(width)
        discrepancies.append(error)
    assert len(widths) > 30
    return {
        "samples": len(widths),
        "height": height,
        "minimumActualRayThicknessM": min(widths),
        "maximumActualRayThicknessM": max(widths),
        "minimumSourceThicknessM": min(
            p["sourceThicknessM"] for p in plan["sourceThicknessProbes"]
        ),
        "maximumSourceThicknessM": max(
            p["sourceThicknessM"] for p in plan["sourceThicknessProbes"]
        ),
        "maximumOuterSurfaceDeviationFromIndependentSourceM": max(discrepancies),
        "numericToleranceM": tolerance,
        "minimumThicknessRequirementM": 0.2,
        "expectedExitFromPaintedSource": True,
    }


def geometry_proof(audit):
    plan = builder.read(audit["sourcePlan"])
    assert plan["baselineSha256"] == builder.SHA and len(plan["holes"]) == 4
    checks = []
    for row in plan["objects"]:
        obj = bpy.data.objects[row["replacement"]]
        assert (
            not obj.hide_render
            and object_fingerprint(obj) == audit["addedFingerprints"][obj.name]
        )
        assert sorted(c.name for c in obj.users_collection) == [
            audit["objectOwners"][obj.name]
        ]
        assert [m.name for m in obj.data.materials] == row["materials"]
        volume = prior.solid_proof(obj)
        retained = 0
        original_volume = None
        if row["sourceObject"]:
            original = bpy.data.objects[row["sourceObject"]]
            assert (
                original.hide_render
                and object_fingerprint(original) == row["sourceFingerprint"]
            )
            if "legacyClosedSourceVolumeM3" in row:
                original_volume = row["legacyClosedSourceVolumeM3"]
                assert row["legacyAddedPerimeterFaces"] == 197
            else:
                original_volume = prior.solid_proof(original)
            assert (
                abs((original_volume - volume) - row["expectedRemovedVolumeM3"]) < 0.004
            ), (
                obj.name,
                "removed-volume",
                original_volume - volume,
                row["expectedRemovedVolumeM3"],
            )
            removed_top = top_area(original, row["sourceZ"][1]) - top_area(
                obj, row["sourceZ"][1]
            )
            assert abs(removed_top - row["expectedTopAreaRemovedM2"]) < 0.0006, (
                obj.name,
                "removed-top",
                removed_top,
                row["expectedTopAreaRemovedM2"],
            )
            signatures = collections.Counter(
                helpers.signature(obj, f) for f in obj.data.polygons
            )
            for record in row["faceRecords"]:
                if record["role"] != "retained-native-face":
                    continue
                signature = helpers.signature(
                    original, original.data.polygons[record["sourceFace"]]
                )
                assert signatures[signature] > 0, (
                    obj.name,
                    record["sourceFace"],
                    "retained-native-face-and-UV",
                )
                signatures[signature] -= 1
                retained += 1
        assert all(uv.name for uv in obj.data.uv_layers)
        checks.append(
            {
                "object": obj.name,
                "closedManifoldPositiveVolumeM3": volume,
                "nativeFacesAndUVsRetainedExactly": retained,
                "addedLegacySoffitOuterEdgeFaces": row.get(
                    "legacyAddedPerimeterFaces", 0
                ),
            }
        )
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
    ceiling_rows = [
        r for r in plan["objects"] if r["componentRole"] == "ground-ceiling-aperture"
    ]
    old_ceiling = helpers.tree(
        [
            t
            for r in ceiling_rows
            for t in helpers.rows(bpy.data.objects[r["sourceObject"]])
        ]
    )
    air = old_fill = 0
    for ring in plan["holes"]:
        for xy in helpers.samples(ring):
            start = Vector((*xy, 0.2))
            assert context.ray_cast(start, Vector((0, 0, 1)), 7.06)[0] is None, (
                "retainedMARshaftObstruction",
                xy,
            )
            assert (
                old_ceiling.ray_cast(start, Vector((0, 0, 1)), 7.06)[0] is not None
            ), ("ceilingWasNotFilled", xy)
            air += 1
            old_fill += 1
    wall = bpy.data.objects["MAR283_ground_source_lift_core_walls"]
    walltree = helpers.tree(helpers.rows(wall))
    ceiling = bpy.data.objects[
        next(
            r["replacement"]
            for r in ceiling_rows
            if r["sourceObject"] == "MAR217_coordinated_acoustic_soffit"
        )
    ]
    floor = bpy.data.objects["MAR_MAR_public_floor"]
    contacts = prior.wall_contact_proof(
        wall,
        plan["groundLow"],
        plan["groundTop"],
        helpers.tree(helpers.rows(floor)),
        helpers.tree(helpers.rows(ceiling)),
    )
    doors = prior.door_proof(
        walltree, plan["doors"], plan["groundLow"], plan["doorHead"]
    )
    thickness = source_thickness_proof(walltree, plan, 3.2)
    # Doorways must also be clear of every retained MAR context mesh.
    context_doors = prior.door_proof(
        context, plan["doors"], plan["groundLow"], plan["doorHead"]
    )
    for name, graph in audit["reusedMaterialGraphs"].items():
        assert material_fingerprint(bpy.data.materials[name]) == graph
    assert (
        object_fingerprint(bpy.data.objects[plan["unmodifiedHigherPlate"]])
        == audit["retainedHigherPlateFingerprint"]
    )
    glass = builder.read("result/blender/mar283/native-inspection.json")["entryGlass"]
    assert all(
        object_fingerprint(bpy.data.objects[r["name"]]) == r["fingerprint"]
        for r in glass
    )
    return {
        "status": "passed-ground-only-four-lift-walls-and-ceiling-apertures",
        "shaftCount": 4,
        "objects": checks,
        "actualMARContextAirRays": air,
        "originalFilledCeilingRays": old_fill,
        "airTestZ": [0.2, 7.26],
        "groundWallContacts": contacts,
        "sourceDoorways": doors,
        "fullMARContextDoorways": context_doors,
        "actualWallThickness": thickness,
        "entryGlassGeometryAndExistingDielectricGraphsRetained": True,
        "fullHeightShaftAcceptance": False,
        "higher21_9mPlateUnmodified": True,
        "limits": "Ground-wall height and door head are display estimates. NoFirst-floor wall/door layout,basement shaft or full-height lift is accepted.",
    }


def main():
    audit = builder.read("result/blender/mar283/audit.json")
    assert builder.sha(builder.BASE) == builder.SHA
    assert builder.sha(ROOT / audit["componentPath"]) == audit["componentSha256"]
    assert all(builder.sha(ROOT / p) == h for p, h in audit["sourceHashes"].items())
    bpy.ops.wm.open_mainfile(filepath=str(builder.BASE))
    update_scene()
    before = apply_component(audit)
    proof = geometry_proof(audit)
    result = {
        "status": "passed-fresh-ground-only-MAR283-component",
        "baselineSha256": builder.SHA,
        "componentSha256": audit["componentSha256"],
        "freshBlenderProcess": True,
        "originalObjectsProtected": len(before["objects"]),
        "originalMaterialGraphsProtected": len(before["materials"]),
        "roomMembershipsProtected": len(before["rooms"]),
        "actualMeshProof": proof,
        "verificationScriptSha256": builder.sha(Path(__file__)),
        "authoringScriptSha256": builder.sha(ROOT / "web/tools/refine_mar283.py"),
        "fullHeightShaftAcceptance": False,
        "wholeNativeSaved": False,
    }
    builder.write(builder.OUT / "fresh-process-verification.json", result)
    print("MAR283_FRESH_VERIFIED", audit["componentSha256"], flush=True)


if __name__ == "__main__":
    main()
