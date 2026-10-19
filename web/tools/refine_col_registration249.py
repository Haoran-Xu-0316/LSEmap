"""Build a private COL frontage on the retained Houghton segment.

No whole-campus native is saved. Roof coordination remains an explicit gate;
only finite listed skin polygons can be excluded for candidate comparisons.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/col-registration249"
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import object_fingerprint, update_scene


def split_face(polygon, normal, offset):
    distances = [normal.dot(p[0]) - offset for p in polygon]
    if min(distances) >= -1e-8:
        return polygon, []
    if max(distances) <= 1e-8:
        return [], polygon
    positive, negative = [], []
    for index, a in enumerate(polygon):
        b = polygon[(index + 1) % len(polygon)]
        da = distances[index]
        db = distances[(index + 1) % len(polygon)]
        (positive if da >= 0 else negative).append(a)
        if da < 0 < db or db < 0 < da:
            factor = da / (da - db)
            # Carry every UV layer and the original corner normal to new edges.
            point = (
                a[0].lerp(b[0], factor),
                [x.lerp(y, factor) for x, y in zip(a[1], b[1])],
                a[2].lerp(b[2], factor).normalized(),
            )
            positive.append(point)
            negative.append(point)
    return positive, negative


def outside_strip(polygon, plan):
    origin = Vector((*plan["frontageNorthToSouth"][0], 0))
    axis = Vector((*plan["axis"], 0))
    normal = Vector((*plan["inwardNormal"], 0))
    planes = [
        (axis, axis.dot(origin)),
        (-axis, -axis.dot(origin) - plan["nativeLengthM"]),
        (normal, normal.dot(origin) - plan["clipNormalLimitM"]),
        (-normal, -normal.dot(origin) - plan["clipNormalLimitM"]),
    ]
    kept = []
    inside = polygon
    for direction, offset in planes:
        if not inside:
            break
        inside, outside = split_face(inside, direction, offset)
        if len(outside) >= 3:
            kept.append(outside)
    return kept


def main():
    plan = json.loads((OUT / "registration-plan.json").read_text())
    source = json.loads((ROOT / plan["sourcePlan"]).read_text())
    component_record = json.loads(
        (ROOT / "result/blender/col-component244/component-record.json").read_text()
    )
    baseline = ROOT / plan["baseline"]
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == plan["baselineSha256"]
    assert (
        hashlib.sha256((ROOT / plan["sourcePlan"]).read_bytes()).hexdigest()
        == plan["sourcePlanSha256"]
    )
    assert (
        hashlib.sha256((ROOT / plan["sourceMask"]).read_bytes()).hexdigest()
        == plan["sourceMaskSha256"]
    )
    assert not (OUT / "component.blend").exists(), (
        "Never overwrite a reviewed component"
    )
    bpy.ops.wm.open_mainfile(filepath=str(baseline))
    update_scene()
    spec = importlib.util.spec_from_file_location(
        "native_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = plan["baselineSha256"]
    protection = helper.capture_source()
    (OUT / "protected-source-state.json").write_text(
        json.dumps(protection, indent=2) + "\n"
    )
    original_materials = {m.name for m in bpy.data.materials}
    original_fingerprints = {
        name: row["fingerprint"] for name, row in protection["objects"].items()
    }
    collection = bpy.data.collections.new("COL249_REGISTERED_CANDIDATE")
    bpy.context.scene.collection.children.link(collection)
    component = ROOT / component_record["component"]
    assert (
        hashlib.sha256(component.read_bytes()).hexdigest()
        == component_record["componentSha256"]
    )
    with bpy.data.libraries.load(str(component), link=False) as (_library, loaded):
        loaded.objects = list(component_record["ownedObjects"])
    north = Vector(plan["frontageNorthToSouth"][0])
    axis = Vector(plan["axis"])
    inward = Vector(plan["inwardNormal"])
    source_scale = source["metresPerPoint"]
    width = source["sourceWidthM"]
    rise = source["groundRiseNorthM"]
    door = next(
        o for o in source["openings"] if o["role"] == "entrance-material-unverified"
    )
    left, top, right, bottom = door["sourceBounds"]
    ox, oy = source["sourceOrigin"]
    door_bounds = (
        (left - ox) * source_scale,
        (right - ox) * source_scale,
        (oy - bottom) * source_scale,
        (oy - top) * source_scale,
    )

    def native_point(point):
        x, depth, z = point
        ground = rise * (1 - x / width)
        dl, dr, db, dh = door_bounds
        in_door = dl - 0.012 <= x <= dr + 0.012 and z <= dh + 0.012
        if abs(z - ground) < 0.00001:
            z = plan["flatStreetThresholdM"] if in_door else 0
        elif in_door and z >= max(ground, db) - 0.012:
            lower = max(ground, db)
            z = dh - (dh - z) * (dh - plan["flatStreetThresholdM"]) / (dh - lower)
        xy = north + axis * (x * plan["horizontalFit"]) + inward * depth
        return Vector((xy.x, xy.y, z))

    for obj in loaded.objects:
        assert (
            object_fingerprint(obj) == component_record["objectFingerprints"][obj.name]
        ), obj.name
    added = []
    bindings = {}
    for obj in loaded.objects:
        identity = obj.name
        obj.name = identity.replace("COL244_", "COL249_")
        obj.data = obj.data.copy()
        for vertex in obj.data.vertices:
            vertex.co = native_point(vertex.co)
        for material in obj.data.materials:
            assert material.name not in original_materials
            if material.name.startswith("COL244_"):
                material.name = material.name.replace("COL244_", "COL249_")
        if identity.endswith("_glazing"):
            material = obj.data.materials[0]
            material.diffuse_color = (0.24, 0.29, 0.31, 1)
            node = material.node_tree.nodes.get("Principled BSDF")
            node.inputs["Base Color"].default_value = material.diffuse_color
            node.inputs["Metallic"].default_value = 0
            node.inputs["Transmission Weight"].default_value = 0.58
            node.inputs["Roughness"].default_value = 0.22
            material["webOpacity"] = 0.44
            material["webClosedGlazing"] = False
            material["scope"] = (
                "Estimated finite transmission for64 explicitly backed source window modules only"
            )
        obj["destinationCollection"] = "COL_EXTERIOR"
        obj["scope"] = (
            "Private2020 Houghton registration; width and native flat entrance are estimated; roof volume not accepted"
        )
        collection.objects.link(obj)
        added.append(obj)
        bindings[obj.name] = [m.name for m in obj.data.materials]
    archived = []
    clipping = []
    for entry in plan["objects"]:
        original = bpy.data.objects[entry["name"]]
        assert object_fingerprint(original) == entry["sourceFingerprint"], original.name
        remove = set(entry["removePolygonIndices"])
        clip = set(entry["clipPolygonIndices"])
        vertices = []
        faces = []
        all_uvs = []
        normals = []
        materials = []
        smooth = []
        unchanged = []
        clipped = 0
        inverse = original.matrix_world.inverted()
        for polygon in original.data.polygons:
            if polygon.index in remove:
                continue
            loop_indices = list(polygon.loop_indices)
            face = [
                (
                    original.matrix_world
                    @ original.data.vertices[original.data.loops[li].vertex_index].co,
                    [layer.data[li].uv.copy() for layer in original.data.uv_layers],
                    original.data.corner_normals[li].vector.copy(),
                )
                for li in loop_indices
            ]
            pieces = outside_strip(face, plan) if polygon.index in clip else [face]
            if polygon.index in clip:
                clipped += 1
            else:
                unchanged.append(polygon.index)
            for piece in pieces:
                area = sum(
                    (
                        piece[i][0].cross(piece[(i + 1) % len(piece)][0])
                        for i in range(len(piece))
                    ),
                    Vector(),
                ).length
                if polygon.index in clip and area < 1e-10:
                    continue
                start = len(vertices)
                if polygon.index not in clip:
                    # Preserve untouched local coordinates bit-for-bit. A world
                    # transform/inverse round trip can change distant returns.
                    vertices.extend(
                        tuple(
                            original.data.vertices[
                                original.data.loops[li].vertex_index
                            ].co
                        )
                        for li in loop_indices
                    )
                else:
                    vertices.extend(tuple(inverse @ p[0]) for p in piece)
                faces.append(tuple(range(start, start + len(piece))))
                all_uvs.append([[tuple(uv) for uv in p[1]] for p in piece])
                normals.extend(tuple(p[2]) for p in piece)
                materials.append(polygon.material_index)
                smooth.append(polygon.use_smooth)
        mesh = bpy.data.meshes.new("COL249_retained_" + original.data.name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        for material in original.data.materials:
            mesh.materials.append(material)
        for layer_index, old_layer in enumerate(original.data.uv_layers):
            layer = mesh.uv_layers.new(name=old_layer.name)
            for polygon, values in zip(mesh.polygons, all_uvs):
                for li, uvs in zip(polygon.loop_indices, values):
                    layer.data[li].uv = uvs[layer_index]
        for polygon, material, shade in zip(mesh.polygons, materials, smooth):
            polygon.material_index = material
            polygon.use_smooth = shade
        mesh.normals_split_custom_set(normals)
        obj = original.copy()
        obj.data = mesh
        obj.name = "COL249_retained_" + original.name
        obj["originalObject"] = original.name
        obj["destinationCollection"] = "COL_EXTERIOR"
        collection.objects.link(obj)
        added.append(obj)
        archived.append(original.name)
        bindings[obj.name] = [m.name for m in obj.data.materials]
        clipping.append(
            {
                "original": original.name,
                "removeWholeFaces": len(remove),
                "boundedFacesClipped": clipped,
                "retainedFaces": len(faces),
                "untouchedSourcePolygonIndices": unchanged,
                "uvLayers": len(original.data.uv_layers),
            }
        )
    update_scene()
    for name, expected in original_fingerprints.items():
        assert object_fingerprint(bpy.data.objects[name]) == expected, name
    current = helper.capture_source()
    assert (
        current["rooms"] == protection["rooms"]
        and current["campusRooms"] == protection["campusRooms"]
    )
    for name, value in protection["materials"].items():
        assert current["materials"][name] == value, name
    path = OUT / "component.blend"
    bpy.data.libraries.write(str(path), {collection}, fake_user=True, compress=True)
    audit = {
        "baselineSha256": plan["baselineSha256"],
        "component": str(path.relative_to(ROOT)),
        "componentSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "destinationCollection": "COL_EXTERIOR",
        "addedObjects": [o.name for o in added],
        "addedFingerprints": {o.name: object_fingerprint(o) for o in added},
        "archivedObjects": archived,
        "replacementMaterialBindings": bindings,
        "cornerClipping": clipping,
        "originalObjectsPreserved": len(original_fingerprints),
        "protectedRooms": len(protection["rooms"]),
        "sourceComponentSha256": component_record["componentSha256"],
        "status": "private_registered_candidate_roof_not_accepted",
        "limitations": plan["limitations"],
        "roofDecision": plan["roofDecision"],
    }
    (OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == plan["baselineSha256"]
    print("COL249_REGISTERED_PRIVATE", len(added), len(archived), flush=True)


if __name__ == "__main__":
    main()
