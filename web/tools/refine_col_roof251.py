"""Coordinate COL's source upper facade with a finite closed estimated roof.

Run in the existing MachineLearning Python to prepare the fixed geometry plan,
then in Blender's Text Editor to create an independent component. Never saves a
complete campus. The 2020 Houghton elevation controls the front; rear depth and
slate colour remain inherited estimates, not a current as-built survey.
"""

import hashlib
import importlib.util
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/col-roof251"
BASE = ROOT / "result/blender/LSE_campus_detailed_v250.blend"
SHA = "833c92b1af57b5c60fbf6f7cd85deb35ea506f680beefcbf6ffde502516dc4ee"
OWNER = "COL_EXTERIOR"
COLLECTION = "COL251_COMPLETE_CANDIDATE"
ROOF = "COL251_closed_source_height_roof"
EAVE = "COL251_window_avoiding_eave_line"
SOURCE_ROOF = "COL_D4_estimated_mansard"
RETAINED = {
    "COL_D4_roof_parapet": "COL251_retained_Aldwych_roof_parapet",
    "COL_D4_parapet_coping": "COL251_retained_Aldwych_parapet_coping",
}
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def source_records():
    source = json.loads(
        (ROOT / "result/blender/col-component244/geometry-plan.json").read_text()
    )
    registration = json.loads(
        (ROOT / "result/blender/col-registration249/registration-plan.json").read_text()
    )
    candidate = json.loads(
        (ROOT / "result/blender/col-assembly250/candidate-audit.json").read_text()
    )
    assert candidate["baselineSha256"] == SHA
    assert sha(ROOT / candidate["component"]) == candidate["componentSha256"]
    assert sha(ROOT / source["source"]) == source["sourceSha256"]
    return source, registration, candidate


def prepare_plan():
    from shapely import Polygon, box, constrained_delaunay_triangles, union_all

    OUT.mkdir(parents=True, exist_ok=True)
    source, registration, _candidate = source_records()
    inventory = json.loads((OUT / "native-inventory.json").read_text())
    old_roof = next(o for o in inventory if o["name"] == SOURCE_ROOF)
    scale, (ox, oy) = source["metresPerPoint"], source["sourceOrigin"]
    fit = registration["horizontalFit"]
    eave_z = (oy - source["horizontalBandsYpt"]["roofFaceBase"]) * scale
    roof_z = registration["sourceRoofM"]
    assert abs(eave_z - 24.9660833333) < 1e-7 and abs(roof_z - 30.7869166667) < 1e-7
    outline = Polygon(
        [((x - ox) * scale * fit, (oy - y) * scale) for x, y in source["outline"]]
    )
    cap_line = outline.intersection(box(-100, roof_z - 1e-7, 100, roof_z + 1e-7))
    cap_north, cap_south = cap_line.bounds[0], cap_line.bounds[2]
    bottom, top = [], []
    for face in old_roof["polygons"][:14]:
        a, _b, _c, d = [old_roof["points"][i] for i in face["vertices"]]
        assert abs(a[2] - 26.4) < 1e-5 and abs(d[2] - 29) < 1e-5
        bottom.append([a[0], a[1], 26.2])
        top.append([d[0], d[1], roof_z])
    assert abs(bottom[12][1]) < 1e-5 and abs(bottom[13][1]) < 1e-5
    # Only two front cap points move in XY. All other rear/side coordinates are
    # exactly the inherited roof plan; the basal ring remains parcel-aligned.
    top[12] = [cap_south, 0.30, roof_z]
    top[13] = [cap_north, 0.30, roof_z]

    def cap_triangles(ring, offset, reverse=False):
        poly = Polygon([(p[0], p[1]) for p in ring])
        assert poly.is_valid and poly.area > 0
        points = [(p[0], p[1]) for p in ring]
        triangles = constrained_delaunay_triangles(poly)
        assert abs(sum(t.area for t in triangles.geoms) - poly.area) < 1e-7
        result = []
        for t in triangles.geoms:
            indices = [
                min(
                    range(len(points)),
                    key=lambda i: (points[i][0] - x) ** 2 + (points[i][1] - y) ** 2,
                )
                + offset
                for x, y in list(t.exterior.coords)[:-1]
            ]
            result.append(list(reversed(indices)) if reverse else indices)
        return result

    faces = []
    for i in range(14):
        j = (i + 1) % 14
        faces.extend([[i, j, j + 14], [i, j + 14, i + 14]])
    faces += cap_triangles(bottom, 0, True) + cap_triangles(top, 14)
    holes = []
    upper = []
    for opening in source["openings"]:
        polygon = Polygon(
            [
                ((x - ox) * scale * fit, (oy - y) * scale)
                for x, y in opening["cutPolygonPt"]
            ]
        )
        holes.append(polygon)
        if opening["id"].startswith(("R1-", "R2-")):
            upper.append(
                {
                    "id": opening["id"],
                    "ring": [list(p) for p in list(polygon.exterior.coords)[:-1]],
                }
            )
    assert len(upper) == 16
    eave_shape = outline.intersection(
        box(-100, eave_z - 0.03, 100, eave_z + 0.03)
    ).difference(union_all(holes))
    assert not eave_shape.is_empty and eave_shape.is_valid

    def extrude(geometry, front, back):
        vertices = []
        polygons = []

        def face(coords):
            start = len(vertices)
            vertices.extend(coords)
            polygons.append(list(range(start, start + len(coords))))

        parts = (
            list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
        )
        for poly in parts:
            if poly.area < 1e-10:
                continue
            triangles = constrained_delaunay_triangles(poly)
            assert abs(sum(t.area for t in triangles.geoms) - poly.area) < 1e-6
            for t in triangles.geoms:
                ring = list(t.exterior.coords)[:-1]
                face([[u, front, z] for u, z in ring])
                face([[u, back, z] for u, z in reversed(ring)])
            for ring in [poly.exterior, *poly.interiors]:
                coords = list(ring.coords)
                for a, b in itertools.pairwise(coords):
                    face(
                        [
                            [a[0], front, a[1]],
                            [b[0], front, b[1]],
                            [b[0], back, b[1]],
                            [a[0], back, a[1]],
                        ]
                    )
        return {"vertices": vertices, "faces": polygons}

    cutters = extrude(union_all([Polygon(p["ring"]) for p in upper]), -0.08, 0.85)
    plan = {
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "sourcePdf": source["source"],
        "sourcePdfSha256": source["sourceSha256"],
        "registration": {
            key: registration[key]
            for key in [
                "frontageNorthToSouth",
                "axis",
                "inwardNormal",
                "horizontalFit",
                "nativeLengthM",
                "flatStreetThresholdM",
            ]
        },
        "eaveZ": eave_z,
        "roofZ": roof_z,
        "baseZ": 26.2,
        "roof": {"vertices": bottom + top, "faces": faces},
        "windowCutters": cutters,
        "cutOpenings": upper,
        "eave": extrude(eave_shape, -0.055, 0.025),
        "eavePieces": len(list(eave_shape.geoms))
        if eave_shape.geom_type == "MultiPolygon"
        else 1,
        "retainedObjects": {
            name: {
                "replacement": replacement,
                "removedSourceFaceIndices": list(range(12, 18)),
                "preservedSourceFaceIndices": list(range(12)),
            }
            for name, replacement in RETAINED.items()
        },
        "roofCoordinateChanges": {
            "baseRingXYUnchanged": True,
            "oldBaseZ": 26.4,
            "newBaseZ": 26.2,
            "oldTopZ": 29,
            "newTopZ": roof_z,
            "frontTopIndicesOnly": [12, 13],
            "frontTopDepth": 0.30,
            "sourceFrontCapBounds": [cap_north, cap_south],
        },
        "limitations": [
            "The 2020 source controls Houghton upper openings,eave datum and main top silhouette only.",
            "The basal ring,rear roof depth and rear/side slope distribution inherit the prior parcel model and remain estimates.",
            "The 26.2mclosed basal face joins the existing modeled wall top; it is not a measured roof floor or claimed room ceiling.",
            "Two upper rows are actual holes through the roof mass to at least0.85mbehind the facade,keeping the accepted0.14mpanes and0.60mbacks clear.",
            "The source high rectangle is left in the original shallow facade only; no function or full-depth block is inferred.",
            "Slate colour is inherited without calibration. No unseen wall or lower Aldwych/Garrick face is cut.",
        ],
    }
    write("geometry-plan.json", plan)
    print(
        "COL251_CPU_PLAN_READY",
        len(faces),
        len(cutters["faces"]),
        plan["eavePieces"],
        flush=True,
    )


def capture():
    spec = importlib.util.spec_from_file_location(
        "col251_capture", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def clip_legacy_aperture_skin(source, collection, aperture_objects, axis, inside):
    """Remove every legacy face fragment inside actual new aperture volumes."""
    import bpy
    from mathutils import Vector
    from refine_col_registration249 import split_face

    volumes = []
    for aperture_obj in aperture_objects:
        for face in aperture_obj.data.polygons:
            points = [
                aperture_obj.matrix_world @ aperture_obj.data.vertices[i].co
                for i in face.vertices
            ]
            ring = [(p.dot(axis), p.z) for p in points]
            area = sum(
                a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1])
            )
            sign = 1 if area > 0 else -1
            planes = []
            for a, b in zip(ring, ring[1:] + ring[:1]):
                direction = axis * (-(b[1] - a[1]) * sign) + Vector(
                    (0, 0, (b[0] - a[0]) * sign)
                )
                planes.append(
                    (direction, direction.dot(axis * a[0] + Vector((0, 0, a[1]))))
                )
            depth = points[0].dot(inside)
            planes.extend([(inside, depth - 0.005), (-inside, -depth - 0.47)])
            volumes.append(planes)
    vertices = []
    faces = []
    all_uvs = []
    normal_rows = []
    materials = []
    smooth = []
    source_indices = []
    unchanged = []
    changed = []
    removed = []
    inverse = source.matrix_world.inverted()
    for face in source.data.polygons:
        polygon = [
            (
                source.matrix_world
                @ source.data.vertices[source.data.loops[li].vertex_index].co,
                [layer.data[li].uv.copy() for layer in source.data.uv_layers],
                source.data.corner_normals[li].vector.copy(),
            )
            for li in face.loop_indices
        ]
        pieces = [polygon]
        touched = False
        for planes in volumes:
            next_pieces = []
            for piece in pieces:
                if any(
                    max(direction.dot(p[0]) - offset for p in piece) < -1e-7
                    for direction, offset in planes
                ):
                    next_pieces.append(piece)
                    continue
                inside_piece = piece
                outside_pieces = []
                for direction, offset in planes:
                    if not inside_piece:
                        break
                    inside_piece, outside = split_face(inside_piece, direction, offset)
                    if len(outside) >= 3:
                        outside_pieces.append(outside)
                if len(inside_piece) >= 3:
                    touched = True
                    next_pieces.extend(outside_pieces)
                else:
                    next_pieces.append(piece)
            pieces = next_pieces
        (changed if touched else unchanged).append(face.index)
        if not pieces:
            removed.append(face.index)
        for piece in pieces:
            if len(piece) < 3:
                continue
            start = len(vertices)
            vertices.extend(tuple(inverse @ p[0]) for p in piece)
            faces.append(tuple(range(start, start + len(piece))))
            all_uvs.append([p[1] for p in piece])
            normal_rows.extend(tuple(p[2]) for p in piece)
            materials.append(face.material_index)
            smooth.append(face.use_smooth)
            source_indices.append(face.index)
    assert changed and len(changed) < len(source.data.polygons)
    mesh = bpy.data.meshes.new("COL251_retained_glazing_outside_source_apertures")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for m in source.data.materials:
        mesh.materials.append(m)
    for layer_index, layer in enumerate(source.data.uv_layers):
        target = mesh.uv_layers.new(name=layer.name)
        for face, values in zip(mesh.polygons, all_uvs):
            for li, uvs in zip(face.loop_indices, values):
                target.data[li].uv = uvs[layer_index]
    for face, mi, sm in zip(mesh.polygons, materials, smooth):
        face.material_index = mi
        face.use_smooth = sm
    mesh.normals_split_custom_set(normal_rows)
    obj = source.copy()
    obj.data = mesh
    obj.name = mesh.name
    collection.objects.link(obj)
    obj["originalObject"] = source.name
    obj["destinationCollection"] = OWNER
    obj["scope"] = (
        "Bounded Houghton actual-aperture volumes only;Aldwych/Garrick outside faces and vertex-bound UVs retained"
    )
    return obj, {
        "original": source.name,
        "replacement": obj.name,
        "sourceFaceCount": len(source.data.polygons),
        "untouchedSourcePolygonIndices": unchanged,
        "changedSourcePolygonIndices": changed,
        "fullyRemovedSourcePolygonIndices": removed,
        "newFaceSourceIndices": source_indices,
        "depthRangeBehindFacade": [0.135, 0.61],
        "apertureVolumes": len(volumes),
    }


def build_component():
    import bmesh
    import bpy
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from mathutils import Vector

    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "component.blend").exists(), (
        "Never overwrite a reviewed candidate"
    )
    assert sha(BASE) == SHA
    plan = json.loads((OUT / "geometry-plan.json").read_text())
    _source, registration, candidate = source_records()
    assert plan["baselineSha256"] == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    bpy.context.preferences.filepaths.save_version = 0
    before = capture()
    write("protected-source-state.json", before)
    originals = {n: m for n, m in bpy.data.materials.items()}
    collection = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    with bpy.data.libraries.load(str(ROOT / candidate["component"]), link=False) as (
        _lib,
        loaded,
    ):
        loaded.objects = list(candidate["addedObjects"])
    objects = []
    for obj in loaded.objects:
        for index, name in enumerate(
            candidate["replacementMaterialBindings"][obj.name]
        ):
            if name in originals:
                obj.data.materials[index] = originals[name]
        collection.objects.link(obj)
        assert object_fingerprint(obj) == candidate["addedFingerprints"][obj.name], (
            obj.name
        )
        objects.append(obj)
    archive = list(candidate["archivedObjects"])
    for name in archive:
        bpy.data.objects[name].hide_render = True
        bpy.data.objects[name].hide_set(True)
    origin = Vector((*registration["frontageNorthToSouth"][0], 0))
    axis = Vector((*registration["axis"], 0))
    inside = Vector((*registration["inwardNormal"], 0))

    def world(p):
        return origin + axis * p[0] + inside * p[1] + Vector((0, 0, p[2]))

    def make_mesh(name, geometry, material):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(
            [world(p) for p in geometry["vertices"]], [], geometry["faces"]
        )
        mesh.update()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        mesh.materials.append(material)
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        obj["destinationCollection"] = OWNER
        obj["presentationEstimated"] = True
        return obj

    roof = make_mesh(ROOF, plan["roof"], bpy.data.materials["STREET_D4_slate_roof"])
    cutter = make_mesh(
        "COL251_temporary_window_cutters",
        plan["windowCutters"],
        bpy.data.materials["STREET_D4_slate_roof"],
    )
    bpy.context.view_layer.objects.active = roof
    roof.select_set(True)
    modifier = roof.modifiers.new("Actual16upper_openings", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    cutter_mesh = cutter.data
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.meshes.remove(cutter_mesh)
    roof["scope"] = (
        "Closed estimated parcel roof;2020main height and16real upper-window holes,not a complete roof interior"
    )
    roof["originalObject"] = SOURCE_ROOF
    objects.append(roof)
    archive.append(SOURCE_ROOF)
    eave = make_mesh(
        EAVE, plan["eave"], bpy.data.materials["COL249_estimated_neutral_stone"]
    )
    eave["scope"] = (
        "60mmestimated ledge centered on source eave line,with all source opening polygons removed"
    )
    objects.append(eave)
    retained_faces = {}
    for name, record in plan["retainedObjects"].items():
        source = bpy.data.objects[name]
        mesh = bpy.data.meshes.new(record["replacement"])
        vertices = []
        faces = []
        uvs = []
        mapping = {}
        for fi in record["preservedSourceFaceIndices"]:
            face = source.data.polygons[fi]
            for vertex_index in face.vertices:
                if vertex_index not in mapping:
                    mapping[vertex_index] = len(vertices)
                    vertices.append(tuple(source.data.vertices[vertex_index].co))
            faces.append(tuple(mapping[i] for i in face.vertices))
            uvs.append(
                [
                    [list(layer.data[li].uv) for li in face.loop_indices]
                    for layer in source.data.uv_layers
                ]
            )
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        for m in source.data.materials:
            mesh.materials.append(m)
        for layer_index, layer in enumerate(source.data.uv_layers):
            target = mesh.uv_layers.new(name=layer.name)
            for face, values in zip(mesh.polygons, uvs):
                for li, uv in zip(face.loop_indices, values[layer_index]):
                    target.data[li].uv = uv
        for face, fi in zip(mesh.polygons, record["preservedSourceFaceIndices"]):
            face.material_index = source.data.polygons[fi].material_index
            face.use_smooth = source.data.polygons[fi].use_smooth
        # Original retained prisms have inward winding with positive transforms.
        # Reorient only these new copies; BMesh carries each UV corner with its
        # vertex when it reverses polygon order. Never copy the inward normals.
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        assert bm.calc_volume(signed=True) > 0
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        mesh.normals_split_custom_set([(0, 0, 0)] * len(mesh.loops))
        obj = source.copy()
        obj.data = mesh
        obj.name = record["replacement"]
        collection.objects.link(obj)
        obj["originalObject"] = name
        obj["destinationCollection"] = OWNER
        objects.append(obj)
        archive.append(name)
        retained_faces[name] = {
            **record,
            "normalCorrection": "Original identity-transform prisms are inward; new retained copies reoriented outward. Vertex-bound UV mapping retained independent of polygon direction.",
        }
    legacy_source = bpy.data.objects[
        "COL195_FINISH_GLASS181_COL_V99_retained_D4_recessed_glass"
    ]
    retained_glass, aperture_skin = clip_legacy_aperture_skin(
        legacy_source,
        collection,
        [
            bpy.data.objects["COL249_Houghton_glazing"],
            bpy.data.objects["COL249_Houghton_opaque_ground_infill"],
        ],
        axis,
        inside,
    )
    objects.append(retained_glass)
    archive.append(legacy_source.name)
    # Metric coordinates only on newly built roof/eave surfaces. All original
    # source facade/retained face UVs remain untouched.
    for obj in [roof, eave]:
        uv = obj.data.uv_layers.new(name="UVMap")
        for face in obj.data.polygons:
            for li in face.loop_indices:
                p = (
                    obj.matrix_world
                    @ obj.data.vertices[obj.data.loops[li].vertex_index].co
                )
                if abs(face.normal.z) > 0.5:
                    coord = ((p - origin).dot(axis), (p - origin).dot(inside))
                else:
                    coord = ((p - origin).dot(axis), p.z)
                uv.data[li].uv = coord
    for name in archive:
        bpy.data.objects[name].hide_render = True
        bpy.data.objects[name].hide_set(True)
    update_scene()
    after = capture()
    for name, row in before["objects"].items():
        expected = dict(row)
        if name in archive:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(
        after["materials"][name] == value for name, value in before["materials"].items()
    )
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    fingerprints = {o.name: object_fingerprint(o) for o in objects}
    bindings = {o.name: [m.name for m in o.data.materials] for o in objects}
    component = OUT / "component.blend"
    bpy.data.libraries.write(
        str(component), set(objects), fake_user=True, compress=True
    )
    report = dict(candidate)
    report.update(
        version=251,
        building="COL",
        status="unified_component_saved_awaiting_independent_reopen",
        baseline=str(BASE.relative_to(ROOT)),
        baselineSha256=SHA,
        component=str(component.relative_to(ROOT)),
        componentPath=str(component.relative_to(ROOT)),
        componentSha256=sha(component),
        targetCollection=OWNER,
        destinationCollection=OWNER,
        addedObjects=list(fingerprints),
        archivedObjects=archive,
        changedObjects=[],
        addedFingerprints=fingerprints,
        replacementMaterialBindings=bindings,
        roofPlan="geometry-plan.json",
        retainedRoofEdgeFaces=retained_faces,
        apertureSkinClipping=aperture_skin,
        roofDecision="Closed finite parcel roof with true upper-window cutouts;source silhouette accepted only for Houghton,eave and main top.Rear depth and slate shade remain estimated.",
        sourceFacadeComponent=candidate["component"],
        sourceFacadeSha256=candidate["componentSha256"],
        limitations=plan["limitations"],
    )
    write("audit.json", report)
    assert sha(BASE) == SHA
    print(
        "COL251_UNIFIED_COMPONENT_SAVED",
        sha(component),
        len(objects),
        len(archive),
        flush=True,
    )


if __name__ == "__main__":
    if importlib.util.find_spec("bpy") is None:
        prepare_plan()
    else:
        build_component()
