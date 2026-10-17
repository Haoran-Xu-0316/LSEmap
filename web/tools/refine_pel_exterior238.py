"""Refine PEL's photographed entrance finishes without changing its envelope.

Run in Blender's editor. The undated official entrance photo supports the warm
aggregate wall, silver entrance box and neutral glass. Adjacent ribbon windows
are not assigned to PEL. Unseen elevations and the inherited tower remain estimates.
"""

from pathlib import Path
import array, ast, hashlib, json, sys
import bpy, bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/pel-exterior238"
BASE = ROOT / "result/blender/LSE_campus_detailed_v237.blend"
SHA = "f4ab6cfb3688820d7b6ef3a830def14bf35c9d0f4532099a7fde6005895360f5"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    accepted_fingerprints,
    update_scene,
)
from refine_portsmouth_exterior207 import material_fingerprint
from refine_kgs_surface237 import normal_record

FRONT = [
    "PEL_D5_masonry_piers_concrete",
    "PEL_D5_spandrels_concrete",
    "PEL_D5_heads_concrete",
    "PEL_NEXT_narrow_window_shoulders_concrete",
    "PEL_NEXT_closed_middle_panels_concrete",
]
SILVER = [
    "PEL_D5_entry61_box_cheek_silver",
    "PEL_D5_entry61_box_spandrel_silver",
    "PEL_D5_entry61_canopy_fascia_silver",
]
GLASS = [
    "GLASS181_PEL_D5_entry61_back_glass_glass",
    "GLASS181_PEL_D5_entry61_revolving_glass",
    "GLASS181_PEL_D5_entry61_upper_glass_glass",
    "GLASS181_PEL_NEXT_narrow_glass_glass",
]
MOVES = {
    "GLASS181_PEL_D5_entry61_revolving_glass": 1.72,
    "PEL_D5_entry61_revolving_post_silver": 1.72,
    "PEL_D5_entry61_side_door_handle_silver": -3.4,
}
CENTRAL = "PEL_D5_entry61_entry_mullion_silver"
ORIGIN = Vector((109.09975115798566, -88.88292847380751, 0))
END = Vector((114.7297651367445, -92.83246690353144, 0))
AXIS = (END - ORIGIN).normalized()
NORMAL = Vector((0.5742943523473701, 0.8186488849695666, 0))
WIDTH = (END - ORIGIN).length


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(name, v):
    (OUT / name).write_text(json.dumps(v, indent=2) + "\n")


def geometry_state(o, include_transform=True):
    h = hashlib.sha256(
        str([list(r) for r in o.matrix_world]).encode()
        if include_transform
        else b"local"
    )
    mesh = o.data
    for values, field, kind, width in [
        (mesh.vertices, "co", "f", 3),
        (mesh.loops, "vertex_index", "i", 1),
        (mesh.polygons, "loop_total", "i", 1),
    ]:
        buf = array.array(kind, [0]) * (len(values) * width)
        values.foreach_get(field, buf)
        h.update(buf.tobytes())
    for uv in mesh.uv_layers:
        buf = array.array("f", [0]) * (len(uv.data) * 2)
        uv.data.foreach_get("uv", buf)
        h.update(uv.name.encode() + buf.tobytes())
    return h.hexdigest()


def export_private(label):
    source = (
        (ROOT / "web/tools/export_scene.py")
        .read_text()
        .split("campus_scene = bpy.data.scenes.new('WEB_CAMPUS')")[0]
    )
    # Only definitions are needed: keep the current native loaded and its reviewed
    # component visibility. Do not execute any shared export writes or policy loops.
    tree = ast.parse(source)
    wanted = {
        "source_geometry_name",
        "surface_descriptor",
        "web_material",
        "clip_below_ground",
        "clone_group",
        "export_scene",
    }
    ns = dict(
        bpy=bpy,
        bmesh=bmesh,
        Vector=Vector,
        re=__import__("re"),
        json=json,
        full_detail=True,
        material_cache={},
        OUTPUT=OUT,
        depsgraph=bpy.context.evaluated_depsgraph_get(),
    )
    exec(
        compile(
            ast.Module(
                body=[
                    n
                    for n in tree.body
                    if isinstance(n, ast.FunctionDef) and n.name in wanted
                ],
                type_ignores=[],
            ),
            "current-production-export-functions",
            "exec",
        ),
        ns,
    )
    scene = bpy.data.scenes.new("PEL238_PRIVATE_" + label)
    ns["clone_group"](
        list(bpy.data.collections["PEL_EXTERIOR"].all_objects), "PEL", scene
    )
    ns["export_scene"](scene, label + ".glb")
    for o in list(scene.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.scenes.remove(scene)
    update_scene()


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    assert sha(BASE) == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    originals = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    assert originals == accepted_fingerprints(ROOT / "result/blender/stage237", SHA)
    mats = {m.name: material_fingerprint(m) for m in bpy.data.materials}
    visibility = {o.name: o.hide_render for o in bpy.data.objects}
    names = list(dict.fromkeys(FRONT + SILVER + GLASS + list(MOVES) + [CENTRAL]))
    assert all(not visibility[n] for n in names)
    baseline = {
        n: dict(
            geometry=geometry_state(bpy.data.objects[n]),
            localGeometry=geometry_state(bpy.data.objects[n], False),
            normals=normal_record(bpy.data.objects[n].data),
            properties=repr(sorted(bpy.data.objects[n].items())),
        )
        for n in names
    }
    write("source-target-state.json", baseline)
    export_private("before")
    materials = {}
    owned = []
    changes = []

    def material(source, kind):
        key = (source.name, kind)
        if key in materials:
            return materials[key]
        m = source.copy()
        m.name = "PEL238_" + kind + "_" + source.name
        p = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        before = list(p.inputs["Base Color"].default_value)
        if kind == "aggregate":
            color = (0.55, 0.54, 0.51, 1)
            p.inputs["Roughness"].default_value = 0.84
            p.inputs["Metallic"].default_value = 0
        elif kind == "silver_cladding":
            color = (0.58, 0.58, 0.57, 1)
            p.inputs["Roughness"].default_value = 0.48
            p.inputs["Metallic"].default_value = 0.35
        else:
            # Remove a pigment-like cyan cast at constant authored luminance; reflections
            # and the retained back pane still determine the actual appearance.
            luminance = sum(v * w for v, w in zip(before[:3], [0.2126, 0.7152, 0.0722]))
            ratios = (0.98, 1.005, 1.01)
            scale = luminance / sum(
                v * w for v, w in zip(ratios, [0.2126, 0.7152, 0.0722])
            )
            color = tuple(v * scale for v in ratios) + (before[3],)
            p.inputs["Metallic"].default_value = 0
            m["webSurfaceRole"] = "glazing"
        p.inputs["Base Color"].default_value = color
        m.diffuse_color = color
        if kind == "revolving_glass":
            p.inputs["Alpha"].default_value = 0.68
            p.inputs["Transmission Weight"].default_value = 0.25
            p.inputs["Roughness"].default_value = 0.16
            m["webOpacity"] = 0.68
            m.surface_render_method = "DITHERED"
        m["surfacePolicy"] = (
            "PEL238 photo-guided finish estimate; no surveyed optical coefficients or current whole-building interior claim."
        )
        materials[key] = m
        return m

    for name in names:
        original = bpy.data.objects[name]
        o = original.copy()
        o.data = original.data.copy()
        o.name = "PEL238_" + name
        o.data.name = o.name + "_mesh"
        bpy.data.collections["PEL_EXTERIOR"].objects.link(o)
        o["originalObject"] = name
        o["webGeometrySource"] = original.get("webGeometrySource", name)
        o["destinationCollection"] = "PEL_EXTERIOR"
        count = 0
        if name in FRONT:
            old = o.data.materials[0]
            new = material(old, "aggregate")
            slot = len(o.data.materials)
            o.data.materials.append(new)
            for face in o.data.polygons:
                world = o.matrix_world @ face.center
                delta = world - ORIGIN
                depth = delta.dot(NORMAL)
                x = delta.dot(AXIS)
                facing = (
                    (o.matrix_world.to_3x3() @ face.normal).normalized().dot(NORMAL)
                )
                if -0.025 < x < WIDTH + 0.025 and -0.35 < depth < 0.25 and facing > 0.9:
                    face.material_index = slot
                    count += 1
            assert count > 0, (name, count)
        elif name in SILVER + GLASS:
            kind = (
                "silver_cladding"
                if name in SILVER
                else "revolving_glass"
                if name == "GLASS181_PEL_D5_entry61_revolving_glass"
                else "neutral_glass"
            )
            for i, m in enumerate(original.data.materials):
                o.data.materials[i] = material(m, kind)
            count = len(o.data.polygons)
        moved_vertices = 0
        if name in MOVES:
            o.location += AXIS * MOVES[name]
            assert geometry_state(o, False) == baseline[name]["localGeometry"]
        elif name == CENTRAL:
            inverse = o.matrix_world.inverted().to_3x3()
            delta = inverse @ (AXIS * -0.7)
            for v in o.data.vertices:
                x = (o.matrix_world @ v.co - ORIGIN).dot(AXIS)
                if abs(x - (WIDTH / 2 + 0.35)) < 0.08:
                    v.co += delta
                    moved_vertices += 1
            assert moved_vertices == 8, moved_vertices
            for a, b in zip(original.data.vertices, o.data.vertices):
                expected = (
                    delta
                    if abs(
                        (original.matrix_world @ a.co - ORIGIN).dot(AXIS)
                        - (WIDTH / 2 + 0.35)
                    )
                    < 0.08
                    else Vector()
                )
                assert (b.co - a.co - expected).length < 1e-5
        else:
            assert geometry_state(o) == baseline[name]["geometry"]
        o.data.update()
        normal_error = 0
        if name == CENTRAL:
            for a, b in zip(original.data.corner_normals, o.data.corner_normals):
                normal_error = max(normal_error, (a.vector - b.vector).length)
            assert normal_error < 0.0001, normal_error
        else:
            assert normal_record(o.data) == baseline[name]["normals"], name
        o.hide_render = False
        o.hide_set(False)
        original.hide_render = True
        original.hide_set(True)
        owned.append(o)
        changes.append(
            dict(
                source=name,
                replacement=o.name,
                facesReassigned=count,
                originalLocalGeometryUvExact=name != CENTRAL,
                normalsExact=name != CENTRAL,
                maximumCornerNormalVectorDifference=normal_error,
                axisTranslationMetres=MOVES.get(name, 0),
                centralPostVerticesMoved=moved_vertices,
            )
        )
    update_scene()
    export_private("after")
    assert all(
        object_fingerprint(bpy.data.objects[n]) == fp for n, fp in originals.items()
    )
    assert all(
        material_fingerprint(bpy.data.materials[n]) == fp for n, fp in mats.items()
    )
    assert sha(BASE) == SHA
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), set(owned), fake_user=True, compress=True)
    fingerprints = {o.name: object_fingerprint(o) for o in owned}
    normal_states = {o.name: normal_record(o.data) for o in owned}
    materials_record = {
        m.name: dict(
            fingerprint=material_fingerprint(m),
            role=k[1],
            source=k[0],
            color=list(m.diffuse_color),
        )
        for k, m in materials.items()
    }
    audit = dict(
        version=238,
        code="PEL",
        baselineSha256=SHA,
        componentPath=str(component.relative_to(ROOT)),
        componentSha256=sha(component),
        destinationCollection="PEL_EXTERIOR",
        addedObjects=list(fingerprints),
        archivedObjects=names,
        addedFingerprints=fingerprints,
        retainNewMaterials=True,
        replacementMaterialBindings={
            o.name: [m.name for m in o.data.materials] for o in owned
        },
        changes=changes,
        newMaterials=materials_record,
        replacementNormals=normal_states,
        scope="Correct the reversed revolving-door side relative to the photographed LSE sign: translate the existing curved glass and posts1.72m along the facade axis; move the side-door pull to the opposite field and shift only8central-post vertices0.7m. Refine photographed front wall, entrance cladding and four glass batches. Keep22narrow windows, topology/UV/normals, opaque rear pane and every room.",
        sourcePhoto="data/建筑图片/PEL_Pethick-Lawrence House/01_建筑实拍/exteriors_lse_estate_023.jpg",
        sourcePhotoSha256=sha(
            ROOT
            / "data/建筑图片/PEL_Pethick-Lawrence House/01_建筑实拍/exteriors_lse_estate_023.jpg"
        ),
        sourceUrl="https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/Pethick-Lawrence-web.jpg",
        captureDate=None,
        limitations=[
            "Finish colours and roughness are estimates from undated photographs, not measured reflectance.",
            "Upper continuation and inherited44m tower, roof and unseen elevations remain unverified.",
            "Adjacent ribbon-window building is not assigned to PEL.",
            "Only the curved revolving front becomes partly transparent; its existing opaque rear glazing proxy remains. No complete lobby or new room is inferred.",
        ],
    )
    write("audit.json", audit)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component), link=False) as (_, target):
        target.objects = list(fingerprints)
    for o in target.objects:
        bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    assert {o.name: object_fingerprint(o) for o in target.objects} == fingerprints
    assert {o.name: normal_record(o.data) for o in target.objects} == normal_states
    assert all(
        material_fingerprint(bpy.data.materials[n]) == v["fingerprint"]
        for n, v in materials_record.items()
    )
    write(
        "independent-component-verification.json",
        dict(
            sourceObjectsPreserved=len(originals),
            sourceMaterialsPreserved=len(mats),
            savedComponentReopened=True,
            sourceGeometryPreserved=True,
            replacementTopologyAndUvPreserved=True,
            centralPostNormalRoundingTolerance=0.0001,
            componentSha256=audit["componentSha256"],
            newObjects=len(owned),
        ),
    )
    print("PEL238_COMPONENT_READY", len(owned), flush=True)


if __name__ == "__main__":
    run()
