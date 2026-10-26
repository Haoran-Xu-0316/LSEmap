"""Read-only SAW exterior/floor registration inspection of native263.

Open this fixed script in Blender or let the parent run it in background mode.
It never saves a .blend, edits an object, changes visibility, or applies a modifier.
Only result/blender/saw269/native-inspection.json is written.
Coordinates in this report are saved-model world metres, Z-up. glTF uses X,Z,-Y.
"""
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v263.blend"
EXPECTED_SHA256 = "f55f5975ea5e4d755f0c883bc64965b928a3d03add666c598a9b7e987bb70c2d"
OUT = ROOT / "result/blender/saw269/native-inspection.json"
LEVELS = (8.1, 11.1, 14.1, 18.0)
TOP_TOLERANCE = 0.035
SECTION_OFFSET = 0.004


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def point(value):
    return [round(float(component), 7) for component in value]


def bounds(points):
    if not points:
        return None
    return {"min": [min(p[i] for p in points) for i in range(3)],
            "max": [max(p[i] for p in points) for i in range(3)]}


def safe_property(value, depth=0):
    if depth > 3:
        return str(value)[:200]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "items"):
        return {str(k): safe_property(v, depth + 1) for k, v in value.items()}
    try:
        return [safe_property(v, depth + 1) for v in value]
    except TypeError:
        return str(value)


def plane_section(vertices, height):
    """Return a triangle/Z-plane segment; discard point contacts and coplanar faces."""
    hits = []
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        da, db = a.z - height, b.z - height
        if abs(da) < 1e-8:
            hits.append(a.copy())
        if da * db < -1e-16:
            hits.append(a + (b - a) * (da / (da - db)))
    unique = {tuple(round(c, 7) for c in p): p for p in hits}
    hits = list(unique.values())
    if len(hits) != 2 or (hits[1] - hits[0]).length < 1e-7:
        return None
    return [point(p) for p in hits]


def authoring_family(name):
    families = (("SAW242_", "upper-circulation242"), ("SAW233_", "lower-circulation233"),
                ("SAW223_", "circulation223"), ("SAWFLOOR216_", "floor-registration216"),
                ("SAW173_", "historical-public-structure173"), ("SAW206_", "glazing206"),
                ("SAW_EXTERIOR166_", "single-pane166"), ("SAW_D5_curtain82_", "timber-curtain82"))
    return next((family for prefix, family in families if name.startswith(prefix)),
                "legacy-envelope" if name.startswith("SAW_") else "unclassified")


assert BASE.is_file(), BASE
assert file_sha256(BASE) == EXPECTED_SHA256, "Unexpected native baseline; do not inspect a substituted edition"
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
scene = bpy.context.scene
for layer in scene.view_layers:
    layer.update()

# A scene may link one object through multiple collections. Record every path;
# a hidden archive path must not suppress a second visible production path.
scene_paths = defaultdict(list)

def collect_paths(collection, path=(), hidden=False):
    current = path + (collection.name,)
    hidden = hidden or collection.hide_render
    for obj in collection.objects:
        scene_paths[obj.name].append({"collections": list(current), "renderPathHidden": hidden})
    for child in collection.children:
        collect_paths(child, current, hidden)

collect_paths(scene.collection)
collections = [bpy.data.collections.get(name) for name in ("SAW_EXTERIOR", "SAW_PUBLIC_INTERIOR_study")]
assert all(collections), "Expected SAW exterior and public-interior collections"
candidates = {obj.name: obj for collection in collections for obj in collection.all_objects}

public_export_names = set()
public_selection_error = None
try:
    sys.path.insert(0, str(ROOT / "web/tools"))
    from public_interior_objects import public_interior_objects
    metadata = json.loads((ROOT / "web/tools/building-metadata.json").read_text())
    building = next(record for record in metadata["buildings"] if record["code"] == "SAW")
    public_export_names = {obj.name for obj in public_interior_objects(building)}
except (AssertionError, ImportError, KeyError, OSError, RuntimeError, StopIteration, TypeError, ValueError) as error:
    public_selection_error = repr(error)

report = {
    "version": 269, "readOnly": True, "baseline": str(BASE.relative_to(ROOT)),
    "baselineSha256": EXPECTED_SHA256, "scene": scene.name,
    "blenderVersion": bpy.app.version_string,
    "coordinates": {"native": "world metres X,Y,Z-up", "gltf": "native X,native Z,-native Y"},
    "floorTopToleranceMetres": TOP_TOLERANCE,
    "sectionsAt": {str(level): level + SECTION_OFFSET for level in LEVELS},
    "objects": [], "visibleObjects": [], "floorTopSurfaces": {str(level): [] for level in LEVELS},
    "brickSections": {str(level): [] for level in LEVELS},
    "glazingSections": {str(level): [] for level in LEVELS},
    "publicExportSelection": sorted(public_export_names), "publicSelectionError": public_selection_error,
    "limitations": ["Visibility, material names and slices are observations, not acceptance of either historic registration.",
                    "Native exterior and floor plans were authored in different stages; an existing shell is not a clipping authority.",
                    "Evaluated modifier coordinates are inspected without applying or saving modifiers.",
                    "A Z-plane slice is offset4mm above the named floor to avoid shared-edge degeneracy."]}

for name, obj in sorted(candidates.items()):
    paths = scene_paths.get(name, [])
    render_visible = not obj.hide_render and any(not p["renderPathHidden"] for p in paths)
    try:
        viewport_visible = obj.visible_get(view_layer=bpy.context.view_layer)
    except (TypeError, RuntimeError):
        viewport_visible = None
    material_names = [material.name if material else None for material in getattr(obj.data, "materials", [])]
    row = {"name": name, "type": obj.type, "authoringFamily": authoring_family(name),
           "ownerCollections": sorted(collection.name for collection in obj.users_collection),
           "sceneCollectionPaths": paths, "renderVisible": render_visible, "viewportVisible": viewport_visible,
           "hideRender": obj.hide_render, "hideViewport": obj.hide_viewport,
           "inProductionPublicInteriorSelection": name in public_export_names,
           "materials": material_names, "worldMatrix": [list(r) for r in obj.matrix_world],
           "worldBounds": bounds([obj.matrix_world @ Vector(p) for p in obj.bound_box]) if obj.type == "MESH" else None,
           "modifiers": [{"name": m.name, "type": m.type, "renderEnabled": m.show_render,
                          "viewportEnabled": m.show_viewport} for m in obj.modifiers],
           "properties": {key: safe_property(obj[key]) for key in obj.keys()  # noqa: SIM118 - Blender ID custom-property keys, not object iteration.
                          if any(token in key.lower() for token in ("owner", "source", "component", "scope", "reference", "collection", "stage", "registered", "evidence"))}}
    if obj.type == "MESH":
        row["savedMesh"] = {"vertices": len(obj.data.vertices), "polygons": len(obj.data.polygons),
                            "materialFaceCounts": dict(Counter(material_names[p.material_index] if p.material_index < len(material_names) else None for p in obj.data.polygons))}
    report["objects"].append(row)
    if not render_visible or obj.type != "MESH":
        continue
    report["visibleObjects"].append(name)
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=bpy.context.evaluated_depsgraph_get())
    try:
        mesh.calc_loop_triangles()
        world = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        row["evaluatedMesh"] = {"vertices": len(mesh.vertices), "triangles": len(mesh.loop_triangles), "worldBounds": bounds(world)}
        for triangle in mesh.loop_triangles:
            vertices = [world[i] for i in triangle.vertices]
            cross = (vertices[1] - vertices[0]).cross(vertices[2] - vertices[0])
            if cross.length < 1e-12:
                continue
            normal = cross.normalized()
            material_index = triangle.material_index
            material = material_names[material_index] if material_index < len(material_names) else None
            is_concrete = material and any(token in material.lower() for token in ("concrete", "floor", "slab"))
            is_floor = bool(re.search(r"floor|slab|landing", name, re.IGNORECASE)) or is_concrete
            is_brick = material and "brick" in material.lower()
            is_glazing = material and any(token in material.lower() for token in ("glass", "glazing"))
            low, high = min(p.z for p in vertices), max(p.z for p in vertices)
            for level in LEVELS:
                key = str(level)
                if is_floor and normal.z > .98 and max(abs(p.z - level) for p in vertices) <= TOP_TOLERANCE:
                    report["floorTopSurfaces"][key].append({"object": name, "ownerCollections": row["ownerCollections"],
                        "authoringFamily": row["authoringFamily"], "triangle": triangle.index,
                        "polygon": triangle.polygon_index, "vertexIndices": list(triangle.vertices),
                        "material": material, "area": cross.length / 2, "normal": point(normal),
                        "vertices": [point(p) for p in vertices]})
                cut = level + SECTION_OFFSET
                if low <= cut <= high and abs(normal.z) < .85 and (is_brick or is_glazing):
                    segment = plane_section(vertices, cut)
                    if segment:
                        report["brickSections" if is_brick else "glazingSections"][key].append({
                            "object": name, "ownerCollections": row["ownerCollections"], "authoringFamily": row["authoringFamily"],
                            "triangle": triangle.index, "polygon": triangle.polygon_index,
                            "material": material, "normal": point(normal), "segment": segment})
    finally:
        evaluated.to_mesh_clear()

for filename, field in (("result/blender/stage02/detail_geometry.json", "historicalEnvelope"),
                        ("result/blender/saw-floors216/registration.json", "historicalFloorRegistration"),
                        ("result/blender/saw-floors216/surface-plan.json", "historicalFloorContours")):
    path = ROOT / filename
    if not path.is_file():
        continue
    data = json.loads(path.read_text())
    if field == "historicalEnvelope":
        data = {"saw_center": data.get("saw_center"), "surfaces": [s for s in data.get("surfaces", []) if s.get("code") == "SAW"]}
    elif field == "historicalFloorContours":
        data = {"sourcePdfSha256": data.get("sourcePdfSha256"), "floors": [
            {k: value for k, value in floor.items() if k in {"level", "datum", "sourceObject", "floorObject", "outlineWorld", "floorArea", "landingArea"}}
            for floor in data.get("floors", [])]}
    report[field] = {"path": filename, "sha256": file_sha256(path), "data": data}

report["summary"] = {"candidateObjects": len(report["objects"]), "visibleMeshObjects": len(report["visibleObjects"]),
    "floorTopTriangles": {level: len(rows) for level, rows in report["floorTopSurfaces"].items()},
    "brickSectionSegments": {level: len(rows) for level, rows in report["brickSections"].items()},
    "glazingSectionSegments": {level: len(rows) for level, rows in report["glazingSections"].items()},
    "visibleFloorOwners": sorted({r["object"] for rows in report["floorTopSurfaces"].values() for r in rows})}
assert file_sha256(BASE) == EXPECTED_SHA256, "Read-only baseline changed during inspection"
report["nativeFileUnchanged"] = True
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print("SAW269_READ_ONLY_NATIVE_INSPECTION", json.dumps(report["summary"]), flush=True)
