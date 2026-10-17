"""Build a registered CON facade and bounded roof closure as a private candidate.

Preserve the accepted campus intact. Only the explicitly listed old frontage
skin is replaced in the candidate; ambiguous corners are clipped face by face.
"""

import hashlib
import json
import sys
from itertools import pairwise
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/con-registration244"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene


def main():
    registration = json.loads((OUT / "registration-plan.json").read_text())
    source = json.loads((ROOT / registration["sourcePlan"]).read_text())
    baseline = ROOT / registration["baseline"]
    assert (
        hashlib.sha256(baseline.read_bytes()).hexdigest()
        == registration["baselineSha256"]
    )
    assert (
        hashlib.sha256((ROOT / registration["sourcePlan"]).read_bytes()).hexdigest()
        == registration["sourcePlanSha256"]
    )
    bpy.ops.wm.open_mainfile(filepath=str(baseline))
    update_scene()
    protection = json.loads(
        (ROOT / "result/blender/stage244/protected-source-state.json").read_text()
    )
    original_fingerprints = {
        name: row["fingerprint"] for name, row in protection["objects"].items()
    }
    assert all(
        object_fingerprint(bpy.data.objects[n]) == fp
        for n, fp in original_fingerprints.items()
    )
    original_materials = {m.name: m for m in bpy.data.materials}
    mask = json.loads(
        (
            ROOT / "result/blender/con-frontage243/skin-mask-review/polygon-mask.json"
        ).read_text()
    )
    summary = json.loads(
        (
            ROOT / "result/blender/con-frontage243/skin-mask-review/review-summary.json"
        ).read_text()
    )
    source_record = json.loads(
        (ROOT / "result/blender/con-frontage243/component-record.json").read_text()
    )
    source_path = ROOT / source_record["component"]
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == source_record["componentSha256"]
    )
    collection = bpy.data.collections.new("CON244_REGISTERED_CANDIDATE")
    bpy.context.scene.collection.children.link(collection)
    with bpy.data.libraries.load(str(source_path), link=False) as (_library, imported):
        imported.objects = source_record["ownedObjects"]
    source_objects = list(imported.objects)
    points = [Vector(p) for p in registration["frontage"]]
    lengths = registration["segmentLengthsM"]
    axes = [(points[i + 1] - points[i]).normalized() for i in range(2)]
    normals = [Vector((-axis.y, axis.x)) for axis in axes]
    middle = (normals[0] + normals[1]).normalized()
    middle /= middle.dot(normals[0])
    fit = registration["horizontalFit"]
    source_scale = source["metresPerPoint"]
    ox, oy = source["sourceOrigin"]
    ground_slope = (473.20 - 466.00) / (566.12 - 229.16)
    door_bounds = []
    for opening in source["openings"]:
        if opening["role"] != "door":
            continue
        x0, y0, x1, y1 = opening["sourceBounds"]
        door_bounds.append(
            (
                (x0 - ox) * source_scale,
                (x1 - ox) * source_scale,
                (oy - y1) * source_scale,
                (oy - y0) * source_scale,
            )
        )

    def native_point(co):
        local_x, depth, z = co
        if abs(z - local_x * ground_slope) < 1e-5:
            z = 0.0
        else:
            for left, right, bottom, head in door_bounds:
                if (
                    left - 0.012 <= local_x <= right + 0.012
                    and bottom - 0.012 <= z <= head + 0.012
                ):
                    z = head - (head - z) * (head - registration["doorThresholdM"]) / (
                        head - bottom
                    )
        station = local_x * fit
        if station <= lengths[0]:
            fraction = station / lengths[0]
            normal = normals[0].lerp(middle, fraction)
            xy = points[0] + axes[0] * station + normal * depth
        else:
            fraction = (station - lengths[0]) / lengths[1]
            normal = middle.lerp(normals[1], fraction)
            xy = points[1] + axes[1] * (station - lengths[0]) + normal * depth
        return (xy.x, xy.y, z)

    owned = []
    bindings = {}
    for obj in source_objects:
        old_name = obj.name
        # Appending into a full campus suffixes shared material datablocks.
        # Restore their exact identities before checking the source fingerprint.
        if not old_name.endswith("closed_backing"):
            identity = (
                "Dark bronze frames"
                if old_name.endswith("joinery")
                else "DIELECTRIC166_CON_V41_neutral_glass_1"
                if old_name.endswith("glazing")
                else "Portland limestone warm"
            )
            obj.data.materials[0] = original_materials[identity]
        assert (
            object_fingerprint(obj) == source_record["objectFingerprints"][old_name]
        ), old_name
        obj.name = old_name.replace("CON243_", "CON244_")
        collection.objects.link(obj)
        if old_name.endswith("glazing"):
            # The source distinguishes80 windows from9 door/unknown modules.
            # Set source face roles before the frontage-bend cut, whose child
            # faces inherit these indices. Unknown infill stays opaque.
            assert len(obj.data.polygons) == len(source["openings"]) == 89
            for polygon, opening in zip(obj.data.polygons, source["openings"]):
                polygon.material_index = int(opening["role"] != "window")
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        # All source triangles crossing the slight native frontage bend are cut
        # before mapping. Their depths meet at one shared miter, without a seam.
        bmesh.ops.bisect_plane(
            bm,
            geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
            dist=1e-7,
            plane_co=(lengths[0] / fit, 0, 0),
            plane_no=(1, 0, 0),
        )
        for vertex in bm.verts:
            vertex.co = native_point(vertex.co)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(obj.data)
        bm.free()
        if old_name.endswith("closed_backing"):
            material = obj.data.materials[0]
        else:
            material_name = (
                "Dark bronze frames"
                if old_name.endswith("joinery")
                else "DIELECTRIC166_CON_V41_neutral_glass_1"
                if old_name.endswith("glazing")
                else "Portland limestone warm"
            )
            material = original_materials[material_name]
            obj.data.materials[0] = material
        if old_name.endswith("glazing"):
            # These80 known windows have verified opaque backing0.60m behind the
            # facade. Give only this new assembly finite transmission; retain
            # every legacy proxy and original material graph unchanged.
            material = original_materials[
                "DIELECTRIC166_CON_V41_neutral_glass_1"
            ].copy()
            material.name = "CON244_backed_window_glass"
            material.diffuse_color = (0.24, 0.29, 0.31, 1)
            node = material.node_tree.nodes.get("Principled BSDF")
            node.inputs["Base Color"].default_value = material.diffuse_color
            node.inputs["Metallic"].default_value = 0
            node.inputs["Roughness"].default_value = 0.22
            node.inputs["Transmission Weight"].default_value = 0.58
            node.inputs["IOR"].default_value = 1.5
            material["webOpacity"] = 0.44
            material["webClosedGlazing"] = False
            material["scope"] = (
                "Estimated finite glazing for80 source-backed windows; not measured optics or a complete interior"
            )
            obj.data.materials[0] = material
            infill = original_materials["Dark bronze frames"].copy()
            infill.name = "CON244_unverified_ground_infill"
            infill.diffuse_color = (0.15, 0.16, 0.16, 1)
            node = infill.node_tree.nodes.get("Principled BSDF")
            node.inputs["Base Color"].default_value = infill.diffuse_color
            node.inputs["Metallic"].default_value = 0
            node.inputs["Roughness"].default_value = 0.55
            node.inputs["Transmission Weight"].default_value = 0
            infill["scope"] = (
                "Opaque placeholder for9 source doors or material-unknown modules; not certified glass"
            )
            obj.data.materials.append(infill)
        bindings[obj.name] = [m.name for m in obj.data.materials]
        obj["scope"] = (
            "Registered2020 Houghton elevation; width fit and flat thresholds are estimated, street and Aldwych entrance retained"
        )
        obj["destinationCollection"] = "CON_EXTERIOR"
        owned.append(obj)

    # Split only listed ambiguous corner faces against the two bounded front
    # strips; carry all other face coordinates, material slots and UVs through.
    ambiguous = {}
    for case in summary["ambiguousCases"]:
        ambiguous.setdefault(case["object"], set()).update(
            case["requiresFaceClippingPolygonIndices"]
        )
    clip_records = []

    def split_face(polygon, normal, offset):
        distances = [normal.dot(v[0]) - offset for v in polygon]
        if min(distances) >= -1e-8:
            return polygon, []
        if max(distances) <= 1e-8:
            return [], polygon
        positive, negative = [], []
        for i, a in enumerate(polygon):
            b = polygon[(i + 1) % len(polygon)]
            da, db = distances[i], distances[(i + 1) % len(polygon)]
            (positive if da >= 0 else negative).append(a)
            if (da < 0 < db) or (db < 0 < da):
                fraction = da / (da - db)
                point = (a[0].lerp(b[0], fraction), a[1].lerp(b[1], fraction))
                positive.append(point)
                negative.append(point)
        return positive, negative

    def outside_strip(polygon, segment):
        start = points[segment]
        axis, normal = axes[segment], normals[segment]
        t = Vector((axis.x, axis.y, 0))
        n = Vector((normal.x, normal.y, 0))
        a = Vector((start.x, start.y, 0))
        planes = [
            (t, t.dot(a)),
            (-t, -t.dot(a) - lengths[segment]),
            (n, n.dot(a) - 0.4),
            (-n, -n.dot(a) - 0.4),
        ]
        inside, kept = polygon, []
        for direction, offset in planes:
            if not inside:
                break
            inside, outside = split_face(inside, direction, offset)
            if len(outside) >= 3:
                kept.append(outside)
        return kept

    archived = []
    for entry in mask["objects"]:
        if not entry["removeCount"]:
            continue
        original = bpy.data.objects[entry["name"]]
        assert object_fingerprint(original) == entry["sourceFingerprint"]
        archived.append(original.name)
        remove = set(entry["removePolygonIndices"])
        if len(remove) == len(original.data.polygons):
            continue
        vertices, faces, uv_faces, materials, smooth = [], [], [], [], []
        clipped = 0
        source_uv = original.data.uv_layers.active
        for polygon in original.data.polygons:
            if polygon.index in remove:
                continue
            face = [
                (
                    original.matrix_world
                    @ original.data.vertices[original.data.loops[li].vertex_index].co,
                    source_uv.data[li].uv.copy() if source_uv else Vector((0, 0)),
                )
                for li in polygon.loop_indices
            ]
            pieces = [face]
            if polygon.index in ambiguous.get(original.name, set()):
                for segment in range(2):
                    pieces = [
                        part for item in pieces for part in outside_strip(item, segment)
                    ]
                clipped += 1
            for piece in pieces:
                if len(piece) < 3:
                    continue
                area_vector = sum(
                    (
                        piece[i][0].cross(piece[(i + 1) % len(piece)][0])
                        for i in range(len(piece))
                    ),
                    Vector(),
                )
                if area_vector.length < 1e-10:
                    continue
                start = len(vertices)
                vertices.extend(tuple(v[0]) for v in piece)
                faces.append(tuple(range(start, start + len(piece))))
                uv_faces.append([tuple(v[1]) for v in piece])
                materials.append(polygon.material_index)
                smooth.append(polygon.use_smooth)
        name = "CON244_retained_" + original.name
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        for material in original.data.materials:
            mesh.materials.append(material)
        uv = mesh.uv_layers.new(name=source_uv.name if source_uv else "UVMap")
        for polygon, values, material, shaded in zip(
            mesh.polygons, uv_faces, materials, smooth
        ):
            polygon.material_index = material
            polygon.use_smooth = shaded
            for li, value in zip(polygon.loop_indices, values):
                uv.data[li].uv = value
        obj = bpy.data.objects.new(name, mesh)
        obj["originalObject"] = original.name
        obj["destinationCollection"] = "CON_EXTERIOR"
        collection.objects.link(obj)
        owned.append(obj)
        bindings[name] = [m.name for m in original.data.materials]
        clip_records.append(
            {
                "original": original.name,
                "removedWholeFaces": len(remove),
                "boundedCornerFacesClipped": clipped,
                "retainedResultFaces": len(faces),
            }
        )

    profile = registration["roofProfileStationHeightM"]
    axis = Vector(registration["roofProjectionAxis"])

    def height(xy):
        station = (Vector(xy) - points[0]).dot(axis)
        for (a, za), (b, zb) in pairwise(profile):
            if station <= b:
                return za + (zb - za) * max(0, station - a) / (b - a)
        return profile[-1][1]

    def make_mesh(name, polygons, material):
        verts, faces = [], []
        for polygon in polygons:
            start = len(verts)
            verts.extend(polygon)
            faces.append(tuple(range(start, start + len(polygon))))
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        mesh.materials.append(material)
        obj = bpy.data.objects.new(name, mesh)
        obj["destinationCollection"] = "CON_EXTERIOR"
        obj["scope"] = (
            "Estimated unseen closure over retained CON parcel; source front height profile retained"
        )
        collection.objects.link(obj)
        bindings[name] = [material.name]
        owned.append(obj)
        return obj

    thickness = registration["roofSlabThicknessM"]
    roof_faces, rear_faces = [], []
    for tri in registration["roofTriangles"]:
        roof_faces.append([(x, y, height((x, y))) for x, y in tri])
        roof_faces.append(
            [(x, y, height((x, y)) - thickness) for x, y in reversed(tri)]
        )
    for a, b in registration["roofBoundarySegments"]:
        ha, hb = height(a), height(b)
        roof_faces.append(
            [(*a, ha), (*a, ha - thickness), (*b, hb - thickness), (*b, hb)]
        )
        # Houghton is already a perforated wall, not an opaque duplicate shell.
        midpoint = (Vector(a) + Vector(b)) * 0.5
        on_front = any(
            abs((midpoint - points[i]).dot(normals[i])) < 1e-5
            and -1e-5 <= (midpoint - points[i]).dot(axes[i]) <= lengths[i] + 1e-5
            for i in range(2)
        )
        if not on_front:
            rear_faces.append(
                [
                    (*a, registration["upperRearWallBaseM"]),
                    (*b, registration["upperRearWallBaseM"]),
                    (*b, hb - thickness),
                    (*a, ha - thickness),
                ]
            )
    make_mesh(
        "CON244_closed_roof_slab", roof_faces, original_materials["Lead and slate"]
    )
    make_mesh(
        "CON244_estimated_upper_rear_closure",
        rear_faces,
        original_materials["Portland limestone warm"],
    )
    archived.append("CON_roof")
    update_scene()
    assert all(
        object_fingerprint(bpy.data.objects[n]) == fp
        for n, fp in original_fingerprints.items()
    )
    component = OUT / "component.blend"
    bpy.data.libraries.write(
        str(component), {collection}, fake_user=True, compress=True
    )
    record = {
        "baselineSha256": registration["baselineSha256"],
        "component": str(component.relative_to(ROOT)),
        "componentSha256": hashlib.sha256(component.read_bytes()).hexdigest(),
        "addedObjects": [o.name for o in owned],
        "addedFingerprints": {o.name: object_fingerprint(o) for o in owned},
        "archivedObjects": archived,
        "replacementMaterialBindings": bindings,
        "destinationCollection": "CON_EXTERIOR",
        "cornerClipping": clip_records,
        "registrationPlanSha256": hashlib.sha256(
            (OUT / "registration-plan.json").read_bytes()
        ).hexdigest(),
        "sourceComponentSha256": source_record["componentSha256"],
        "originalObjectsPreserved": len(original_fingerprints),
        "scope": "Register CON historical89-opening Houghton facade, clip only bounded old skin, and close its roof over the retained parcel",
        "status": "private_candidate_awaiting_saved_and_visual_verification",
        "limitations": registration["limitations"],
    }
    (OUT / "audit.json").write_text(json.dumps(record, indent=2) + "\n")
    assert (
        hashlib.sha256(baseline.read_bytes()).hexdigest()
        == registration["baselineSha256"]
    )
    print("CON244_PRIVATE_REGISTERED_COMPONENT", len(owned), len(archived), flush=True)


if __name__ == "__main__":
    main()
