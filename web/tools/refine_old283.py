"""Correct two photographed Houghton ground-window grids in a separate component.

Fixed paths for Blender's Text Editor. Original279, every old object, material,
UV and room stay intact. Only six horizontal members are replaced by eight
members copied from their existing profiles. No full-campus save or CLI options.
"""

import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v279.blend"
SHA = "b03a0caec932c50e0c7d8ad2a725a43b80eb38abee716f1d1c2d30cde767982c"
OUT = ROOT / "result/blender/old283"
OWNER = "OLD_EXTERIOR"
SOURCE = "OLD_V112_entry_D5_windows85_casements"
NEW = "OLD283_Houghton_two_outer_ground_five_row_casements"
PRIOR_SOURCE = "346a8ba3b1e258330e4af0862cf9b293f9a160e3ff3997bcb96c0f4d89e32f71"
STAGE = "build"
PHOTO = "data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_01.jpg"


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verifier():
    path = ROOT / "web/tests/verify_old283.py"
    spec = importlib.util.spec_from_file_location("old283_independent", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def capture():
    import bpy

    spec = importlib.util.spec_from_file_location(
        "old283_protection", ROOT / "web/tests/verify_campus241.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BASE_SHA = SHA
    state = module.capture_source()
    state["visibility"] = {
        o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
    }
    state["images"] = sorted(i.name for i in bpy.data.images)
    return state


def protection(before, archived=False):
    after = capture()
    for name, record in before["objects"].items():
        expected = dict(record)
        if archived and name == SOURCE:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
        visibility = list(before["visibility"][name])
        if archived and name == SOURCE:
            visibility[0] = visibility[2] = True
        assert after["visibility"][name] == visibility, name
    assert set(after["objects"]) == set(before["objects"]) | {NEW}
    for key in ("materials", "rooms", "campusRooms", "images"):
        assert after[key] == before[key], key
    assert sha(BASE) == SHA
    return {
        "originalObjects": len(before["objects"]),
        "originalMaterialGraphs": len(before["materials"]),
        "roomMemberships": len(before["rooms"]),
        "sourceGeometryUVNormalsMaterialsAndOwnersExact": True,
        "unlistedVisibilityAndImagesExact": True,
        "wholeNativeSaved": False,
    }


def prepare_evidence():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = [
        PHOTO,
        "data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_06.jpg",
        "data/collections/old-user-reference/houghton-entrance.png",
    ]
    write(
        OUT / "source-review.json",
        {
            "baseline": str(BASE.relative_to(ROOT)),
            "baselineSha256": SHA,
            "priorCasementFingerprint": PRIOR_SOURCE,
            "sourcePage": "https://webbyates.com/projects/the-old-building/",
            "sourcePageVerified": "2026-10-30",
            "photographer": "Damian Griffiths",
            "projectCompletionYear": 2024,
            "photoCaptureDate": None,
            "sourceHashes": {p: sha(ROOT / p) for p in sources},
            "scope": "Only two outer ground-floor windows flanking Houghton main entrance; narrow inner portal windows, all upper windows and Clare frontage excluded.",
            "observations": [
                "Project photograph01 shows three internal blue vertical boundaries, hence four columns in each outer ground window.",
                "Each ground window has four horizontal blue boundaries, hence five rows: two above the broad meeting rail and three below it.",
                "Right ground window upper part has a blue field and a circular fitting. Its material is not inferred from photographs and is retained.",
                "Photograph06 repeats the same project view and is corroborating framing, not independent survey evidence.",
                "The user crop hides most ground windows and is used only to exclude the two inner narrow portal windows from this correction.",
            ],
            "nativeDiscrepancy": "Retained275evaluated snapshot has three horizontal members per outer ground window, four rows and meeting rail at3/4height. The fresh279builder must independently re-establish that geometry before writing a candidate.",
            "correction": "Replace only the two outer ground-window horizontal sets with four rails at estimated1/5,2/5,3/5,4/5fractions, retaining the broad profile at3/5. Keep every vertical member and the twelve other ordinary Houghton entrance-wing windows exactly.",
            "privateEvidenceCrop": "result/blender/old283/houghton-source-01-window-crops.png",
            "sourceBitmapsUsedAsPublicTextures": False,
            "limitations": [
                "The photograph establishes five rows and rail hierarchy; fractions, thicknesses, opening dimensions and setbacks remain visual estimates.",
                "A correct pane count does not establish physical glass optics, measured construction details or whole-building exterior accuracy.",
                "No masonry recolouring, unverified transparent facade, window operation, sculpture change or unseen elevation is introduced.",
            ],
        },
    )


def member_record(obj, group):
    selected = set(group)
    mapping = {old: new for new, old in enumerate(group)}
    faces = [f for f in obj.data.polygons if set(f.vertices) <= selected]
    assert len(group) == 8 and len(faces) == 6
    return {
        "points": [list(obj.data.vertices[i].co) for i in group],
        "faces": [
            {
                "vertices": [mapping[i] for i in face.vertices],
                "materialIndex": face.material_index,
                "smooth": face.use_smooth,
                "uvs": {
                    layer.name: [list(layer.data[i].uv) for i in face.loop_indices]
                    for layer in obj.data.uv_layers
                },
            }
            for face in faces
        ],
    }


def build_candidate(source, independent):
    import bpy

    axes = independent.source_axes()
    parts = independent.describe(source, axes)
    assert len(parts) == 84 and len(source.data.vertices) == 672
    target = independent.ground_parts(parts)
    removed = {
        i for group in target for row in group["horizontal"] for i in row["vertices"]
    }
    assert len(removed) == 48
    records = [
        member_record(source, row["vertices"])
        for row in parts
        if not (set(row["vertices"]) & removed)
    ]
    assert len(records) == 78
    source_members = []
    for window in target:
        horizontal = sorted(window["horizontal"], key=lambda r: r["centre"][2])
        assert len(horizontal) == 3
        z0, height = window["bottom"], window["height"]
        for j in range(1, 5):
            template = horizontal[-1] if j == 3 else horizontal[0]
            record = member_record(source, template["vertices"])
            offset = z0 + height * j / 5 - template["centre"][2]
            # Only vertical translation changes; original finite profile, face
            # ordering, native UVs and materials are reused without stretching.
            for point in record["points"]:
                point[2] += offset
            records.append(record)
            source_members.append(
                {
                    "windowCentreX": window["centreX"],
                    "fraction": j / 5,
                    "heavy": j == 3,
                    "sourceTemplateVertices": template["vertices"],
                }
            )
    assert len(records) == 86
    vertices, faces, details = [], [], []
    for record in records:
        start = len(vertices)
        vertices.extend(record["points"])
        for face in record["faces"]:
            faces.append([start + i for i in face["vertices"]])
            details.append(face)
    mesh = bpy.data.meshes.new(NEW + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    for material in source.data.materials:
        mesh.materials.append(material)
    for face, detail in zip(mesh.polygons, details, strict=True):
        face.material_index = detail["materialIndex"]
        face.use_smooth = detail["smooth"]
    for old_layer in source.data.uv_layers:
        layer = mesh.uv_layers.new(name=old_layer.name)
        for face, detail in zip(mesh.polygons, details, strict=True):
            for loop, uv in zip(
                face.loop_indices, detail["uvs"][layer.name], strict=True
            ):
                layer.data[loop].uv = uv
    mesh.update()
    obj = source.copy()
    obj.data = mesh
    obj.name = NEW
    obj["originalObject"] = SOURCE
    obj["destinationCollection"] = OWNER
    obj["webGeometrySource"] = source.get("webGeometrySource", SOURCE)
    obj["sourcePhoto"] = PHOTO
    obj["dimensionsEstimated"] = True
    obj["sourceScope"] = (
        "Two outer Houghton ground windows:4columns5rows; all other members exact"
    )
    bpy.data.collections[OWNER].objects.link(obj)
    obj.hide_render = False
    return obj, source_members


def apply_component(audit, materials):
    import bpy
    from integrate_exterior_round194 import set_layer_hidden, update_scene

    with bpy.data.libraries.load(str(ROOT / audit["componentPath"]), link=False) as (
        _,
        destination,
    ):
        destination.objects = list(audit["addedObjects"])
    for obj in destination.objects:
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        bpy.data.collections[OWNER].objects.link(obj)
        obj.hide_render = False
        set_layer_hidden(obj, False)
    for material in list(bpy.data.materials):
        if material.name not in materials:
            assert material.users == 0
            bpy.data.materials.remove(material)
    bpy.data.objects[SOURCE].hide_render = True
    set_layer_hidden(bpy.data.objects[SOURCE], True)
    update_scene()


def build():
    import bpy

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene

    prepare_evidence()
    assert sha(BASE) == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    write(OUT / "protected-source-state.json", before)
    source = bpy.data.objects[SOURCE]
    assert object_fingerprint(source) == PRIOR_SOURCE
    assert not source.hide_render and not source.modifiers
    assert sorted(c.name for c in source.users_collection) == [OWNER]
    assert NEW not in bpy.data.objects
    independent = verifier()
    obj, members = build_candidate(source, independent)
    update_scene()
    protection(before)
    component = OUT / "component.blend"
    audit = {
        "version": 283,
        "building": "OLD",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "status": "bounded-two-outer-ground-window-candidate",
        "targetCollection": OWNER,
        "destinationCollection": OWNER,
        "componentPath": str(component.relative_to(ROOT)),
        "addedObjects": [NEW],
        "archivedObjects": [SOURCE],
        "changedObjects": [],
        "addedFingerprints": {NEW: object_fingerprint(obj)},
        "replacementMaterialBindings": {NEW: [m.name for m in obj.data.materials]},
        "reusedMaterialGraphs": {
            m.name: before["materials"][m.name] for m in obj.data.materials
        },
        "newMaterials": 0,
        "addedMaterialFingerprints": {},
        "sourceFingerprint": object_fingerprint(source),
        "sourceHashes": json.loads((OUT / "source-review.json").read_text())[
            "sourceHashes"
        ],
        "sourceEvidence": str((OUT / "source-review.json").relative_to(ROOT)),
        "sourceEvidenceSha256": sha(OUT / "source-review.json"),
        "members": members,
        "scope": "Only horizontal rail sets in two outer Houghton ground windows. Six old rails archived inside the original84member batch; eight copied profiles create5rows.78native members remain exact.",
        "limitations": json.loads((OUT / "source-review.json").read_text())[
            "limitations"
        ],
        "wholeNativeSaved": False,
    }
    bpy.data.libraries.write(str(component), {obj}, fake_user=False)
    audit["componentSha256"] = sha(component)
    bpy.ops.wm.open_mainfile(filepath=str(component))
    assert set(bpy.data.objects.keys()) == {NEW}
    evaluate_component_scene("builder")
    assert object_fingerprint(bpy.data.objects[NEW]) == audit["addedFingerprints"][NEW]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    apply_component(audit, before["materials"])
    audit["protection"] = protection(before, archived=True)
    audit["actualMeshProof"] = independent.geometry_proof(audit)
    audit["authoringScriptSha256"] = sha(Path(__file__))
    audit["verificationScriptSha256"] = sha(ROOT / "web/tests/verify_old283.py")
    write(OUT / "audit.json", audit)
    write(
        OUT / "verification.json",
        {"freshBlenderProcess": False, **audit["actualMeshProof"]},
    )
    print("OLD283_COMPONENT_READY", audit["componentSha256"], flush=True)


def evaluate_component_scene(label):
    """Evaluate stored TRS before reading world matrices from an object library.

    The component intentionally has no saved scene. Linking it to a temporary
    scene restores the same dependency-graph context as the campus. Mesh bytes
    are hashed on both sides and cannot change during this step.
    """
    import array
    import hashlib

    import bpy
    from integrate_exterior_round194 import object_fingerprint

    obj = bpy.data.objects[NEW]

    def mesh_hash():
        digest = hashlib.sha256()
        for rows, field, kind, width in (
            (obj.data.vertices, "co", "f", 3),
            (obj.data.loops, "vertex_index", "i", 1),
            (obj.data.polygons, "material_index", "i", 1),
            (obj.data.polygons, "loop_total", "i", 1),
        ):
            values = array.array(kind, [0]) * (len(rows) * width)
            rows.foreach_get(field, values)
            digest.update(values.tobytes())
        for uv in obj.data.uv_layers:
            values = array.array("f", [0]) * (len(uv.data) * 2)
            uv.data.foreach_get("uv", values)
            digest.update(uv.name.encode() + values.tobytes())
        digest.update(str([m.name for m in obj.data.materials]).encode())
        return digest.hexdigest()

    def snapshot():
        return {
            "fingerprint": object_fingerprint(obj),
            "matrixWorld": [list(r) for r in obj.matrix_world],
            "meshSha256": mesh_hash(),
        }

    raw = snapshot()
    scene = bpy.context.scene
    if scene is None:
        scene = bpy.data.scenes.new("OLD283_temporary_component_evaluation")
        bpy.context.window.scene = scene
    if obj.name not in scene.objects:
        scene.collection.objects.link(obj)
    for layer in scene.view_layers:
        layer.update()
    evaluated = snapshot()
    assert raw["meshSha256"] == evaluated["meshSha256"]
    result = {
        "rawEmptyScene": raw,
        "linkedAndEvaluated": evaluated,
        "meshCoordinatesUVsAndSlotsExact": True,
        "nativeSaved": False,
        "componentSaved": False,
    }
    write(OUT / ("roundtrip-evaluation-" + label + ".json"), result)
    return result


def diagnose_component():
    """Read the existing component and evaluate its transform in an empty scene."""
    import bpy

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint

    path = OUT / "component.blend"
    before_sha = sha(path)
    bpy.ops.wm.open_mainfile(filepath=str(path))
    obj = bpy.data.objects[NEW]
    raw = {
        "fingerprint": object_fingerprint(obj),
        "matrixWorld": [list(r) for r in obj.matrix_world],
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "vertices": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "uvLayers": [uv.name for uv in obj.data.uv_layers],
    }
    scene = bpy.context.scene
    if obj.name not in scene.objects:
        scene.collection.objects.link(obj)
    for layer in scene.view_layers:
        layer.update()
    evaluated = {
        "fingerprint": object_fingerprint(obj),
        "matrixWorld": [list(r) for r in obj.matrix_world],
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale),
    }
    result = {
        "componentSha256": before_sha,
        "rawEmptySceneObject": raw,
        "linkedAndEvaluatedObject": evaluated,
        "nativeSaved": False,
        "componentSaved": False,
    }
    assert sha(path) == before_sha
    write(OUT / "roundtrip-transform-diagnostic.json", result)
    print(
        "OLD283_TRANSFORM_DIAGNOSTIC",
        raw["fingerprint"],
        evaluated["fingerprint"],
        flush=True,
    )


def render():
    import bpy
    from mathutils import Vector

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene

    audit = json.loads((OUT / "audit.json").read_text())
    assert (
        sha(BASE) == SHA
        and sha(ROOT / audit["componentPath"]) == audit["componentSha256"]
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    apply_component(audit, before["materials"])
    independent = verifier()
    source = bpy.data.objects[SOURCE]
    axes = independent.source_axes()
    right = (source.matrix_world.to_3x3() @ axes[1]).normalized()
    normal = (
        source.matrix_world.to_3x3().inverted().transposed() @ axes[2]
    ).normalized()

    def point(x, depth, z):
        return source.matrix_world @ independent.source_point(x, depth, z, axes)

    contextual = [
        o
        for o in bpy.data.collections[OWNER].all_objects
        if o.type in {"MESH", "FONT", "CURVE", "SURFACE"} and not o.hide_render
    ]
    contextual.append(source)
    # Each comparison includes the entire OLD assembly at the same settings.
    # Close-ups do not suppress stone, glass, frame or foreground fixtures.
    views = [
        ("whole-Houghton", point(22, -3, 16), 70, (1600, 1000), 80, 0),
        ("entrance-wing", point(0, 0, 10), 19.6, (1440, 1600), 40, 0),
        ("left-ground-window", point(-6.7, 0.13, 2.6), 2.4, (960, 1200), 12, 0),
    ]
    manifest = {
        "baselineSha256": SHA,
        "componentSha256": audit["componentSha256"],
        "views": [],
    }
    for name, target, scale, size, distance, lateral in views:
        scene = bpy.data.scenes.new("OLD283_private_" + name)
        for obj in contextual:
            scene.collection.objects.link(obj)
        world = bpy.data.worlds.new(scene.name + "_world")
        world.use_nodes = True
        world.node_tree.nodes["Background"].inputs["Color"].default_value = (
            0.8,
            0.85,
            0.95,
            1,
        )
        world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.65
        scene.world = world
        light = bpy.data.lights.new(scene.name + "_sun", "SUN")
        light.energy, light.angle = 1.4, 0.15
        sun = bpy.data.objects.new(light.name, light)
        scene.collection.objects.link(sun)
        sun.rotation_euler = (
            (-normal + Vector((0, 0, -0.7))).to_track_quat("-Z", "Y").to_euler()
        )
        data = bpy.data.cameras.new(scene.name + "_camera")
        camera = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(camera)
        camera.location = target + normal * distance + right * lateral
        camera.rotation_euler = (
            (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        )
        scene.camera = camera
        data.type, data.ortho_scale, data.sensor_fit = "ORTHO", scale, "HORIZONTAL"
        data.clip_end = 500
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = 32
        scene.render.resolution_x, scene.render.resolution_y = size
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.view_settings.view_transform = "AgX"
        outputs = {}
        for phase in ("before", "after"):
            source.hide_render = phase == "after"
            bpy.data.objects[NEW].hide_render = phase == "before"
            for layer in scene.view_layers:
                layer.update()
            path = OUT / f"{phase}-{name}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True, scene=scene.name)
            outputs[phase] = {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}
        manifest["views"].append(
            {
                "id": name,
                "target": list(target),
                "camera": list(camera.location),
                "orthoScale": scale,
                "resolution": size,
                "outputs": outputs,
            }
        )
        bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.objects.remove(sun, do_unlink=True)
        bpy.data.cameras.remove(data)
        bpy.data.lights.remove(light)
        bpy.data.worlds.remove(world)
    source.hide_render = True
    bpy.data.objects[NEW].hide_render = False
    update_scene()
    protection(before, archived=True)
    assert object_fingerprint(bpy.data.objects[NEW]) == audit["addedFingerprints"][NEW]
    manifest.update(
        sameCameraAndLighting=True, wholeNativeSaved=False, publicTexturesCreated=False
    )
    write(OUT / "render-manifest.json", manifest)
    print("OLD283_PRIVATE_COMPARISON_READY", len(views) * 2, flush=True)


def main(stage=STAGE):
    if stage == "evidence":
        prepare_evidence()
    elif stage == "build":
        build()
    elif stage == "render":
        render()
    elif stage == "diagnose":
        diagnose_component()
    else:
        raise ValueError(stage)


if __name__ == "__main__":
    main()
