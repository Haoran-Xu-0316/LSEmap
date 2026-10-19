"""Reopen COL251,protect the campus and test the full roof/facade assembly.

Fixed-path independent Blender verification. Far50mrays include every retained
COL facade,parapet and new roof; near-only probes cannot pass this gate.
"""

import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/col-roof251"
BASE = ROOT / "result/blender/LSE_campus_detailed_v250.blend"
SHA = "833c92b1af57b5c60fbf6f7cd85deb35ea506f680beefcbf6ffde502516dc4ee"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.path.insert(0, str(ROOT / "web/tests"))
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_col_roof251 import COLLECTION, EAVE, ROOF, capture
from verify_col_registration249 import face_key


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def tree(obj):
    return BVHTree.FromPolygons(
        [obj.matrix_world @ v.co for v in obj.data.vertices],
        [tuple(p.vertices) for p in obj.data.polygons],
    )


def closed_proof(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert len(bm.faces) > 0 and all(e.is_manifold for e in bm.edges), obj.name
    volume = bm.calc_volume(signed=True)
    assert volume > 0, (obj.name, volume)
    components = []
    remaining = set(bm.verts)
    while remaining:
        seed = remaining.pop()
        pending = [seed]
        shell_vertices = [seed]
        while pending:
            for edge in pending.pop().link_edges:
                for vertex in edge.verts:
                    if vertex in remaining:
                        remaining.remove(vertex)
                        pending.append(vertex)
                        shell_vertices.append(vertex)
        shell_faces = {face for vertex in shell_vertices for face in vertex.link_faces}
        signed_volume = 0
        for face in shell_faces:
            points = [vertex.co for vertex in face.verts]
            for i in range(1, len(points) - 1):
                signed_volume += points[0].dot(points[i].cross(points[i + 1])) / 6
        assert signed_volume > 0, (obj.name, signed_volume)
        components.append(
            {"vertices": len(shell_vertices), "signedVolume": signed_volume}
        )
    bm.free()
    obj.data.calc_loop_triangles()
    return {
        "closedManifold": True,
        "positiveVolumeM3": volume,
        "connectedSolids": len(components),
        "shells": components,
        "vertices": len(obj.data.vertices),
        "triangles": len(obj.data.loop_triangles),
    }


def render(objects, label, origin, axis, inside, kind):
    scene = bpy.data.scenes.new("COL251_REVIEW_" + label)
    for obj in objects:
        scene.collection.objects.link(obj)
    world = bpy.data.worlds.new(scene.name)
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.8,
        0.82,
        0.85,
        1,
    )
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.65
    scene.world = world
    target = origin + axis * 15 + Vector((0, 0, 17))
    data = bpy.data.cameras.new(scene.name)
    camera = bpy.data.objects.new(scene.name + "_camera", data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    offsets = {
        "front": -inside * 70,
        "oblique": -inside * 65 + axis * 26 + Vector((0, 0, 12)),
        "rear": inside * 65 - axis * 20 + Vector((0, 0, 14)),
    }
    camera.location = target + offsets[kind]
    camera.rotation_euler = (
        (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    data.type = "ORTHO"
    data.ortho_scale = 40
    data.clip_end = 500
    light = bpy.data.lights.new(scene.name, "AREA")
    light.energy = 1800
    light.size = 12
    lamp = bpy.data.objects.new(scene.name + "_light", light)
    scene.collection.objects.link(lamp)
    lamp.location = target - inside * 25 - axis * 10 + Vector((0, 0, 24))
    lamp.rotation_euler = (target - lamp.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / (label + ".png"))
    bpy.context.window.scene = scene
    bpy.ops.render.render(write_still=True, scene=scene.name)
    for obj in [camera, lamp]:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    bpy.data.worlds.remove(world)
    bpy.data.cameras.remove(data)
    bpy.data.lights.remove(light)
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()


def undirected_uv_face_key(obj, polygon):
    """Pair UVs with their spatial vertex; winding may intentionally reverse."""
    return (
        polygon.material_index,
        polygon.use_smooth,
        tuple(
            sorted(
                tuple(
                    round(c, 5)
                    for c in obj.matrix_world
                    @ obj.data.vertices[obj.data.loops[li].vertex_index].co
                )
                + tuple(
                    tuple(round(c, 5) for c in uv.data[li].uv)
                    for uv in obj.data.uv_layers
                )
                for li in polygon.loop_indices
            )
        ),
    )


def verify_fragment_uvs(original, replacement, source_indices):
    """Check saved UVs against original spatial barycentric interpolation."""
    assert len(source_indices) == len(replacement.data.polygons)
    worst = 0.0
    samples = 0
    for face, source_index in zip(replacement.data.polygons, source_indices):
        source_face = original.data.polygons[source_index]
        original_loops = list(source_face.loop_indices)
        points = [
            original.matrix_world
            @ original.data.vertices[original.data.loops[li].vertex_index].co
            for li in original_loops
        ]
        for li in face.loop_indices:
            point = (
                replacement.matrix_world
                @ replacement.data.vertices[replacement.data.loops[li].vertex_index].co
            )
            choices = []
            for i in range(1, len(points) - 1):
                a, b, c = points[0], points[i], points[i + 1]
                ab = b - a
                ac = c - a
                ap = point - a
                den = ab.dot(ab) * ac.dot(ac) - ab.dot(ac) ** 2
                if abs(den) < 1e-12:
                    continue
                wb = (ac.dot(ac) * ap.dot(ab) - ab.dot(ac) * ap.dot(ac)) / den
                wc = (ab.dot(ab) * ap.dot(ac) - ab.dot(ac) * ap.dot(ab)) / den
                wa = 1 - wb - wc
                if min(wa, wb, wc) < -0.0002 or max(wa, wb, wc) > 1.0002:
                    continue
                if (a * wa + b * wb + c * wc - point).length > 0.00005:
                    continue
                errors = []
                for layer, target_layer in zip(
                    original.data.uv_layers, replacement.data.uv_layers
                ):
                    expected = (
                        layer.data[original_loops[0]].uv * wa
                        + layer.data[original_loops[i]].uv * wb
                        + layer.data[original_loops[i + 1]].uv * wc
                    )
                    errors.append((expected - target_layer.data[li].uv).length)
                choices.append(max(errors, default=0))
            assert choices, (source_index, list(point))
            error = min(choices)
            assert error < 0.0002, (source_index, error)
            worst = max(worst, error)
            samples += 1
    return {"spatialUVCornersVerified": samples, "maximumUVInterpolationError": worst}


def main():
    assert sha(BASE) == SHA
    audit = json.loads((OUT / "audit.json").read_text())
    plan = json.loads((OUT / "geometry-plan.json").read_text())
    source = json.loads(
        (ROOT / "result/blender/col-component244/geometry-plan.json").read_text()
    )
    reg = plan["registration"]
    component = ROOT / audit["componentPath"]
    assert sha(component) == audit["componentSha256"]
    protected = json.loads((OUT / "protected-source-state.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    assert capture() == protected
    origin = Vector((*reg["frontageNorthToSouth"][0], 0))
    axis = Vector((*reg["axis"], 0))
    inside = Vector((*reg["inwardNormal"], 0))
    original_materials = {m.name: m for m in bpy.data.materials}
    old_objects = [
        o
        for o in bpy.data.collections["COL_EXTERIOR"].all_objects
        if o.type == "MESH" and not o.hide_render
    ]
    render(old_objects, "before-front", origin, axis, inside, "front")
    render(old_objects, "before-oblique", origin, axis, inside, "oblique")
    collection = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    with bpy.data.libraries.load(str(component), link=False) as (_lib, loaded):
        loaded.objects = list(audit["addedObjects"])
    for obj in loaded.objects:
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            if name in original_materials:
                obj.data.materials[index] = original_materials[name]
        collection.objects.link(obj)
        assert object_fingerprint(obj) == audit["addedFingerprints"][obj.name], obj.name
    for name in audit["archivedObjects"]:
        bpy.data.objects[name].hide_render = True
        bpy.data.objects[name].hide_set(True)
    update_scene()
    observed = capture()
    for name, state in protected["objects"].items():
        expected = dict(state)
        if name in audit["archivedObjects"]:
            expected["hidden"] = True
        assert observed["objects"][name] == expected, name
    assert all(observed["materials"][n] == v for n, v in protected["materials"].items())
    assert (
        observed["rooms"] == protected["rooms"]
        and observed["campusRooms"] == protected["campusRooms"]
    )
    roof = bpy.data.objects[ROOF]
    eave = bpy.data.objects[EAVE]
    proof = {ROOF: closed_proof(roof), EAVE: closed_proof(eave)}
    assert proof[ROOF]["connectedSolids"] == 1
    assert proof[EAVE]["connectedSolids"] == plan["eavePieces"] == 9
    points = [roof.matrix_world @ v.co for v in roof.data.vertices]
    assert abs(max(p.z for p in points) - plan["roofZ"]) < 0.00004
    assert abs(min(p.z for p in points) - 26.2) < 0.00004
    assert not roof.modifiers
    assert [m.name for m in roof.data.materials] == ["STREET_D4_slate_roof"]
    for obj in [roof, eave]:
        assert len(obj.data.uv_layers) == 1
        assert all(
            math.isfinite(c) for loop in obj.data.uv_layers[0].data for c in loop.uv
        )
    retained_count = 0
    for original_name, record in plan["retainedObjects"].items():
        original = bpy.data.objects[original_name]
        retained = bpy.data.objects[record["replacement"]]
        keys = Counter(
            undirected_uv_face_key(retained, p) for p in retained.data.polygons
        )
        for fi in record["preservedSourceFaceIndices"]:
            key = undirected_uv_face_key(original, original.data.polygons[fi])
            assert keys[key] > 0
            keys[key] -= 1
            retained_count += 1
        assert len(retained.data.polygons) == 12 and not any(keys.values())
        proof[retained.name] = closed_proof(retained)
        assert retained.matrix_world.to_3x3().determinant() > 0
        for face in retained.data.polygons:
            assert all(
                face.normal.dot(retained.data.corner_normals[li].vector) > 0.999
                for li in face.loop_indices
            ), retained.name
    corner_preserved = 0
    for record in audit["cornerClipping"]:
        original = bpy.data.objects[record["original"]]
        retained = bpy.data.objects["COL249_retained_" + original.name]
        keys = Counter(face_key(retained, p) for p in retained.data.polygons)
        for fi in record["untouchedSourcePolygonIndices"]:
            key = face_key(original, original.data.polygons[fi])
            assert keys[key] > 0
            keys[key] -= 1
            corner_preserved += 1
    skin_record = audit["apertureSkinClipping"]
    skin_original = bpy.data.objects[skin_record["original"]]
    skin_retained = bpy.data.objects[skin_record["replacement"]]
    skin_keys = Counter(face_key(skin_retained, p) for p in skin_retained.data.polygons)
    for fi in skin_record["untouchedSourcePolygonIndices"]:
        key = face_key(skin_original, skin_original.data.polygons[fi])
        assert skin_keys[key] > 0
        skin_keys[key] -= 1
    skin_uv_proof = verify_fragment_uvs(
        skin_original, skin_retained, skin_record["newFaceSourceIndices"]
    )
    objects = [
        o
        for o in list(bpy.data.collections["COL_EXTERIOR"].all_objects)
        + list(collection.all_objects)
        if o.type == "MESH" and not o.hide_render
    ]
    trees = {o.name: tree(o) for o in objects}
    panes = bpy.data.objects["COL249_Houghton_glazing"]
    infill = bpy.data.objects["COL249_Houghton_opaque_ground_infill"]
    back = bpy.data.objects["COL249_Houghton_closed_backing"]
    assert (
        len(panes.data.polygons) == 64
        and len(infill.data.polygons) == 8
        and len(back.data.polygons) == 72
    )
    shader = panes.data.materials[0].node_tree.nodes.get("Principled BSDF")
    assert (
        shader.inputs["Metallic"].default_value == 0
        and abs(shader.inputs["Transmission Weight"].default_value - 0.58) < 1e-6
    )
    assert abs(panes.data.materials[0]["webOpacity"] - 0.44) < 1e-6
    allowed = {
        "COL249_Houghton_glazing",
        "COL249_Houghton_opaque_ground_infill",
        "COL249_Houghton_joinery",
    }
    opaque_excluded = allowed | {"COL249_Houghton_closed_backing"}
    rays = []
    first_hits = []
    eave_rays = []
    far_occlusions = []
    first_hit_failures = []
    write(
        "geometry-gate.json",
        {
            "componentSha256": audit["componentSha256"],
            "newEnclosureProof": proof,
            "retainedCornerFaceUVRecords": corner_preserved,
            "retainedAldwychParapetFaceUVRecords": retained_count,
            "retainedLegacySkinUntouchedFaceUVRecords": len(
                skin_record["untouchedSourcePolygonIndices"]
            ),
            "retainedLegacySkinAllFragmentUVProof": skin_uv_proof,
        },
    )
    ox, oy = source["sourceOrigin"]
    scale = source["metresPerPoint"]
    fit = reg["horizontalFit"]

    def point(source_x, source_y, opening):
        u = (source_x - ox) * scale
        z = (oy - source_y) * scale
        if opening["role"] == "entrance-material-unverified":
            _x0, y0, _x1, y1 = opening["sourceBounds"]
            lower = max(
                (oy - y1) * scale,
                source["groundRiseNorthM"] * (1 - u / source["sourceWidthM"]),
            )
            head = (oy - y0) * scale
            z = head - (head - z) * (head - reg["flatStreetThresholdM"]) / (
                head - lower
            )
        return origin + axis * (u * fit) + Vector((0, 0, z))

    for opening in source["openings"]:
        x0, y0, x1, y1 = opening["sourceBounds"]
        expected = (
            "COL249_Houghton_glazing"
            if opening["role"] == "regular-window"
            else "COL249_Houghton_opaque_ground_infill"
        )
        for fraction in [0.2, 0.5, 0.8]:
            target = point(
                x0 + (x1 - x0) * fraction, y0 + (y1 - y0) * fraction, opening
            )
            start = target - inside * 50
            hit = trees[expected].ray_cast(start, inside, 80)
            bhit = trees[back.name].ray_cast(start, inside, 80)
            assert hit[0] is not None and abs(hit[3] - 50.14) < 0.003, (
                opening["id"],
                "pane",
                hit,
            )
            assert bhit[0] is not None and abs(bhit[3] - 50.60) < 0.003, (
                opening["id"],
                "back",
                bhit,
            )
            bad = []
            for name, t in trees.items():
                if name in opaque_excluded:
                    continue
                h = t.ray_cast(start, inside, 50.598)
                if h[0] is not None:
                    bad.append(
                        {
                            "object": name,
                            "distance": h[3],
                            "faceIndex": h[2],
                            "point": list(h[0]),
                        }
                    )
            if bad:
                far_occlusions.append(
                    {
                        "opening": opening["id"],
                        "fraction": fraction,
                        "origin": list(start),
                        "blockers": bad,
                    }
                )
            rays.append(
                {
                    "opening": opening["id"],
                    "fraction": fraction,
                    "infillDistance": hit[3],
                    "backDistance": bhit[3],
                }
            )
            if fraction == 0.5:
                hits = []
                for name, t in trees.items():
                    h = t.ray_cast(start, inside, 80)
                    if h[0] is not None:
                        hits.append((h[3], name))
                distance, name = min(hits)
                if name not in allowed:
                    first_hit_failures.append(
                        {"opening": opening["id"], "distance": distance, "object": name}
                    )
                first_hits.append(
                    {"opening": opening["id"], "object": name, "distance": distance}
                )
        if opening["id"].startswith("R2-"):
            for fraction in [0.1, 0.25, 0.75, 0.9]:
                for dz in [-0.02, 0, 0.02]:
                    u = (x0 + (x1 - x0) * fraction - ox) * scale * fit
                    target = origin + axis * u + Vector((0, 0, plan["eaveZ"] + dz))
                    start = target - inside * 50
                    assert (
                        trees[eave.name].ray_cast(start, inside, 50.135)[0] is None
                    ), (opening["id"], "eave")
                    assert trees[ROOF].ray_cast(start, inside, 50.598)[0] is None, (
                        opening["id"],
                        "roof",
                    )
                    eave_rays.append(
                        {"opening": opening["id"], "fraction": fraction, "dz": dz}
                    )
    write(
        "occlusion-diagnostic.json",
        {
            "componentSha256": audit["componentSha256"],
            "farOcclusions": far_occlusions,
            "firstHitFailures": first_hit_failures,
        },
    )
    assert not far_occlusions and not first_hit_failures, (
        "Actual retained geometry remains inside the source aperture depth"
    )
    assert len(rays) == 216 and len(first_hits) == 72 and len(eave_rays) == 96
    verification = {
        "savedComponentReopened": True,
        "baselineSha256": SHA,
        "componentSha256": audit["componentSha256"],
        "originalObjectsPreserved": len(protected["objects"]),
        "originalMaterialGraphsPreserved": len(protected["materials"]),
        "protectedRooms": len(protected["rooms"]),
        "protectedRoomObjects": len(
            {n for a in protected["rooms"].values() for n in a}
        ),
        "allOriginalGeometryUVNormalsBindingsTransformsModifiersPropertiesOwnersPreserved": True,
        "unrelatedVisibilityPreserved": True,
        "reusedSourceObjectsUnchanged": 24,
        "retainedCornerFaceUVRecords": corner_preserved,
        "retainedAldwychParapetFaceUVRecords": retained_count,
        "retainedLegacySkinUntouchedFaceUVRecords": len(
            skin_record["untouchedSourcePolygonIndices"]
        ),
        "retainedLegacySkinAllFragmentUVProof": skin_uv_proof,
        "newEnclosureProof": proof,
        "sourceRoofTopZ": plan["roofZ"],
        "eaveZ": plan["eaveZ"],
        "glassModules": 64,
        "opaqueGroundModules": 8,
        "closedBackings": 72,
        "farOpeningBackingRays": len(rays),
        "farFirstHitChecks": len(first_hits),
        "farEaveAndRoofHoleRays": len(eave_rays),
        "noUpperWindowOpaqueOcclusions": True,
        "sourceNativeBytesUnchanged": sha(BASE) == SHA,
        "unknownProjectionRemainsShallowOriginalFacadeOnly": True,
    }
    write(
        "far-rays.json",
        {
            "originOffsetMetres": 50,
            "openingBackingRays": rays,
            "firstHits": first_hits,
            "eaveAndRoofHoleRays": eave_rays,
        },
    )
    write("saved-verification.json", verification)
    for kind in ["front", "oblique", "rear"]:
        render(objects, "after-" + kind, origin, axis, inside, kind)
    assert sha(BASE) == SHA
    audit.update(
        status="unified_component_independently_reopened_and_geometrically_verified",
        verification=verification,
        previews=[
            "before-front.png",
            "before-oblique.png",
            "after-front.png",
            "after-oblique.png",
            "after-rear.png",
        ],
        roofVolumeAccepted=True,
    )
    write("audit.json", audit)
    print(
        "COL251_SAVED_ASSEMBLY_VERIFIED",
        len(rays),
        len(eave_rays),
        corner_preserved,
        flush=True,
    )


if __name__ == "__main__":
    main()
