"""Recover a five-U cycle stand bank at Sheffield's retained mapped anchor.

Fixed Blender authoring configuration. No native save, renderer or CLI options.
The old mixed furniture batch is retained intact for archive; its other faces,
UVs and material indices are copied exactly into an independent retained batch.
"""

import collections
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET
from importlib import import_module
from itertools import pairwise
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/sheffield263"
BASE = ROOT / "result/blender/LSE_campus_detailed_v262.blend"
SHA = "35547bb32309adcd934df8845c71e672e3dc7b3ca519ad5154ec9a65f143cb75"
ORIGINAL = "SITE231_Mapped_furniture_without_Watkins_flat_grates"
RETAINED = "SHEFFIELD263_Mapped_furniture_retained_without_single_cycle_stand"
BANK = "SHEFFIELD263_Five_U_cycle_stands"
sys.path.insert(0, str(ROOT / "web/tools"))
# Blender needs the repository helper path before these runtime imports.
campus_helpers = import_module("integrate_exterior_round194")
object_fingerprint = campus_helpers.object_fingerprint
update_scene = campus_helpers.update_scene
material_fingerprint = import_module(
    "refine_portsmouth_exterior207"
).material_fingerprint
modifier_state = import_module("refine_ksw_exterior219").modifier_state


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, r):
    p.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")


def faces_signature(obj, omit=frozenset()):
    records = []
    for face in obj.data.polygons:
        if set(face.vertices) & omit:
            continue
        corners = []
        for loop_index in face.loop_indices:
            index = obj.data.loops[loop_index].vertex_index
            corners.append(
                (
                    tuple(obj.data.vertices[index].co),
                    tuple(
                        (layer.name, tuple(layer.data[loop_index].uv))
                        for layer in obj.data.uv_layers
                    ),
                )
            )
        rotations = [tuple(corners[i:] + corners[:i]) for i in range(len(corners))]
        records.append((face.material_index, min(rotations)))
    return collections.Counter(records)


def snapshot():
    meta = json.loads((ROOT / "web/tools/building-metadata.json").read_text())
    return {
        "objects": {o.name: object_fingerprint(o) for o in bpy.data.objects},
        "materials": {m.name: material_fingerprint(m) for m in bpy.data.materials},
        "owners": {
            o.name: sorted(c.name for c in o.users_collection) for o in bpy.data.objects
        },
        "visibility": {o.name: o.hide_render for o in bpy.data.objects},
        "props": {o.name: repr(sorted(o.items())) for o in bpy.data.objects},
        "modifiers": {o.name: modifier_state(o) for o in bpy.data.objects},
        "rooms": {
            r["collection"]: sorted(
                o.name for o in bpy.data.collections[r["collection"]].all_objects
            )
            for r in meta["spaces"]
        },
    }


def preserve(state):
    assert all(
        object_fingerprint(bpy.data.objects[n]) == v
        for n, v in state["objects"].items()
    )
    assert all(
        material_fingerprint(bpy.data.materials[n]) == v
        for n, v in state["materials"].items()
    )
    assert all(
        sorted(c.name for c in bpy.data.objects[n].users_collection) == v
        for n, v in state["owners"].items()
    )
    assert all(
        bpy.data.objects[n].hide_render == v for n, v in state["visibility"].items()
    )
    assert all(
        repr(sorted(bpy.data.objects[n].items())) == v
        for n, v in state["props"].items()
    )
    assert all(
        modifier_state(bpy.data.objects[n]) == v for n, v in state["modifiers"].items()
    )
    assert all(
        sorted(o.name for o in bpy.data.collections[n].all_objects) == v
        for n, v in state["rooms"].items()
    )
    assert sha(BASE) == SHA


def build():
    assert sha(BASE) == SHA and not (OUT / "component.blend").exists()
    inspection = json.loads((OUT / "native-inspection.json").read_text())
    assert inspection["baselineSha256"] == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = snapshot()
    assert (
        len(before["objects"]) == 8744
        and len(before["materials"]) == 2355
        and len(before["rooms"]) == 35
    )
    source = bpy.data.objects[ORIGINAL]
    assert not source.hide_render
    assert object_fingerprint(source) == inspection["sourceFingerprint"]
    assert len(inspection["originalCycleParts"]) == 3 and [
        len(p["indices"]) for p in inspection["originalCycleParts"]
    ] == [32, 32, 136]
    removed = {
        index for part in inspection["originalCycleParts"] for index in part["indices"]
    }
    assert len(removed) == 200
    expected = faces_signature(source, removed)
    retained = source.copy()
    retained.data = source.data.copy()
    retained.name = RETAINED
    retained.data.name = RETAINED + "_mesh"
    bpy.data.collections["03_PUBLIC_REALM"].objects.link(retained)
    bm = bmesh.new()
    bm.from_mesh(retained.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in sorted(removed)], context="VERTS")
    bm.to_mesh(retained.data)
    bm.free()
    retained.data.update()
    assert faces_signature(retained) == expected, (
        "Retained native face/UV/material records changed"
    )
    retained["destinationCollection"] = "03_PUBLIC_REALM"
    retained["originalObject"] = ORIGINAL
    retained["scope"] = (
        "Exact other-furniture subset; only the three connected pieces of one old mapped cycle stand omitted. Full old object archived intact."
    )
    paving = bpy.data.objects["SITE194_SITE_V47_Sheffield_Street"]
    paving.data.calc_loop_triangles()
    floor = BVHTree.FromPolygons(
        [paving.matrix_world @ v.co for v in paving.data.vertices],
        [tuple(t.vertices) for t in paving.data.loop_triangles],
        all_triangles=True,
    )
    vertices = []
    faces = []
    slots = []
    stand_rows = []
    radius = 0.028
    sides = 12
    anchor = Vector(inspection["mappedCycleAnchor"])
    centres = [
        list(anchor + Vector((0, offset, 0)))
        for offset in [-2.10, -1.05, 0, 1.05, 2.10]
    ]
    for number, centre in enumerate(centres):
        x, y, _ = centre
        ground = []
        for dx in [-0.34, 0.34]:
            hit = floor.ray_cast(Vector((x + dx, y, 0.25)), Vector((0, 0, -1)), 0.4)
            assert hit[0] is not None and 0.049 <= hit[0].z <= 0.051
            ground.append(hit[0].z - 0.0005)
        datum = max(ground)
        path = []
        for z in [ground[0], datum + 0.50, datum + 0.58, datum + 0.66, datum + 0.68]:
            path.append(Vector((x - 0.34, y, z)))
        for i in range(1, 7):
            a = math.pi - i * math.pi / 12
            path.append(
                Vector(
                    (
                        x - 0.22 + 0.12 * math.cos(a),
                        y,
                        datum + 0.68 + 0.12 * math.sin(a),
                    )
                )
            )
        path.append(Vector((x + 0.22, y, datum + 0.80)))
        for i in range(1, 7):
            a = math.pi / 2 - i * math.pi / 12
            path.append(
                Vector(
                    (
                        x + 0.22 + 0.12 * math.cos(a),
                        y,
                        datum + 0.68 + 0.12 * math.sin(a),
                    )
                )
            )
        for z in [datum + 0.66, datum + 0.58, datum + 0.50, ground[1]]:
            path.append(Vector((x + 0.34, y, z)))
        first = len(vertices)
        lengths = [0]
        for a, b in pairwise(path):
            lengths.append(lengths[-1] + (b - a).length)
        for index, point in enumerate(path):
            tangent = (
                path[min(index + 1, len(path) - 1)] - path[max(0, index - 1)]
            ).normalized()
            n = Vector((0, 1, 0))
            b = tangent.cross(n).normalized()
            for j in range(sides):
                a = j * math.tau / sides
                vertices.append(
                    point + n * (radius * math.cos(a)) + b * (radius * math.sin(a))
                )
        faces.append(tuple(first + j for j in reversed(range(sides))))
        slots.append(0)
        for index in range(len(path) - 1):
            slot = 0
            for j in range(sides):
                faces.append(
                    (
                        first + index * sides + j,
                        first + index * sides + (j + 1) % sides,
                        first + (index + 1) * sides + (j + 1) % sides,
                        first + (index + 1) * sides + j,
                    )
                )
                slots.append(slot)
        faces.append(tuple(first + (len(path) - 1) * sides + j for j in range(sides)))
        slots.append(0)
        stand_rows.append(
            {
                "index": number,
                "centre": centre,
                "footCentres": [[x - 0.34, y, ground[0]], [x + 0.34, y, ground[1]]],
                "pitchM": 1.05,
                "widthCentrelineM": 0.68,
                "topCentrelineZ": datum + 0.80,
                "tubeRadiusM": radius,
                "groundDatum": datum,
            }
        )
    mesh = bpy.data.meshes.new(BANK + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for name in ["SITE_V47_iron"]:
        mesh.materials.append(bpy.data.materials[name])
    uv = mesh.uv_layers.new(name="MetricUV")
    for polygon, slot in zip(mesh.polygons, slots):
        polygon.material_index = slot
        polygon.use_smooth = len(polygon.vertices) == 4
        for index in polygon.loop_indices:
            uv.data[index].uv = mesh.vertices[mesh.loops[index].vertex_index].co.xz
    bm = bmesh.new()
    bm.from_mesh(mesh)
    assert all(e.is_manifold for e in bm.edges)
    assert bm.calc_volume(signed=True) > 0
    bm.free()
    bank = bpy.data.objects.new(BANK, mesh)
    bpy.data.collections["03_PUBLIC_REALM"].objects.link(bank)
    bank["destinationCollection"] = "03_PUBLIC_REALM"
    bank["scope"] = (
        "Five double-sided Ucycle stands inferred from the archived10-bicycle capacity at the existing mapped group anchor. Existing hoop axis retained; pitch, exact individual centres and section estimated. Photographs establish same-street form only, not this exact group."
    )
    bank["sourceOsm"] = "node/6510702755"
    bank["sourceDate"] = (
        "OSMnode2023-06-22;2021same-street photograph published2022; not an October2026survey"
    )
    added = [retained, bank]
    update_scene()
    preserve(before)
    assert set(bpy.data.objects.keys()) - set(before["objects"]) == {RETAINED, BANK}
    assert set(bpy.data.materials.keys()) == set(before["materials"])
    fingerprints = {o.name: object_fingerprint(o) for o in added}
    bindings = {o.name: [m.name for m in o.data.materials] for o in added}
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), set(added), fake_user=True, compress=True)
    photo = ROOT / "data/collections/streets/derived/review_public_realm_pdf_page71.png"
    pdf = ROOT / "data/collections/streets/raw/public_realm_strategy_2022.pdf"
    osm = ROOT / "data/collections/streets/raw/osm_map.osm"
    node = next(
        n
        for n in ET.parse(osm).getroot().findall("node")
        if n.get("id") == "6510702755"
    )
    tags = {t.get("k"): t.get("v") for t in node.findall("tag")}
    assert (
        tags["amenity"] == "bicycle_parking"
        and tags["bicycle_parking"] == "stands"
        and tags["capacity"] == "10"
        and tags["covered"] == "no"
    )
    node_file = OUT / "source-osm-node.xml"
    node_file.write_text(ET.tostring(node, encoding="unicode") + "\n")
    source_review = {
        "version": 263,
        "sources": [
            {
                "path": str(osm.relative_to(ROOT)),
                "sha256": sha(osm),
                "role": "Exact archived OSMnode6510702755, version2,2023-06-22: bicycle parking stands, capacity10, uncovered, free",
            },
            {
                "path": str(node_file.relative_to(ROOT)),
                "sha256": sha(node_file),
                "role": "Exact node element retained with all attributes and tags",
            },
            {
                "path": str(photo.relative_to(ROOT)),
                "sha256": sha(photo),
                "role": "Official2021site photo in2022strategy appendix; same-street Ustand form only. This close group is not claimed to be the mapped group.",
                "captureDate": "2021",
                "publicationYear": 2022,
                "url": "https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/2022-LSE-Public-Realm-Strategy.pdf",
            },
            {
                "path": str(pdf.relative_to(ROOT)),
                "sha256": sha(pdf),
                "role": "Official source document; existing-condition photographs distinguished from enhancement recommendations",
            },
        ],
        "osmNode": {"attributes": dict(node.attrib), "tags": tags},
        "registration": "Original native/OSMnode6510702755 is the group centre. Original single-hoopXaxis retained; five positions spaced1.05m along the perpendicularYaxis are an explicit modeling estimate, not a photographed surveyed layout.",
        "capacityInterpretation": "OSMcapacity10counts bicycles. Five double-sided Ustands are a transparent modeling inference with two bicycles per stand; the source does not independently enumerate five physical hoops.",
        "limits": "Exact individual centres, pitch, section and height are estimates. Same-street photographs support Ustand form only and are not asserted to show this exact mapped bank. No uniform yellow bands, new bicycles or angular lights. No October2026as-built or inventory claim.",
    }
    write(OUT / "source-review.json", source_review)
    audit = {
        "version": 263,
        "status": "component-authored-pending-independent-geometry-test",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": sha(component),
        "targetCollection": "03_PUBLIC_REALM",
        "destinationCollection": "03_PUBLIC_REALM",
        "objectOwners": {RETAINED: "03_PUBLIC_REALM", BANK: "03_PUBLIC_REALM"},
        "addedObjects": [RETAINED, BANK],
        "archivedObjects": [ORIGINAL],
        "changedObjects": [],
        "addedFingerprints": fingerprints,
        "replacementMaterialBindings": bindings,
        "retainNewMaterials": [],
        "removedVertexIndices": sorted(removed),
        "originalObject": ORIGINAL,
        "retainedFaceRecords": sum(expected.values()),
        "originalMaterialBindings": [m.name for m in source.data.materials],
        "stands": stand_rows,
        "sourceManifest": "result/blender/sheffield263/source-review.json",
        "sourceHashes": {r["path"]: r["sha256"] for r in source_review["sources"]},
        "verification": {
            "originalObjectsPreserved": 8744,
            "originalMaterialsPreserved": 2355,
            "independentRoomsPreserved": 35,
            "retainedFacesUVsMaterialIndicesExact": True,
            "protected262Planters": inspection["protected262Planters"],
            "baselineUnchanged": True,
            "noFullNativeSaved": True,
        },
        "budget": {
            "objects": 2,
            "newMaterials": 0,
            "bankVertices": len(vertices),
            "bankFaces": len(faces),
            "sourceCyclePartsReplaced": 3,
            "cycleStandsAfter": 5,
        },
        "limitations": source_review["limits"],
    }
    write(OUT / "audit.json", audit)
    bpy.ops.wm.open_mainfile(filepath=str(component))
    assert all(
        object_fingerprint(bpy.data.objects[n]) == fp for n, fp in fingerprints.items()
    )
    assert sha(BASE) == SHA
    write(
        OUT / "component-reopen.json",
        {
            "status": "passed",
            "componentSha256": sha(component),
            "objectsVerified": 2,
            "originalBaselineUnchanged": True,
        },
    )
    print("SHEFFIELD263_COMPONENT", audit["componentSha256"], flush=True)


if __name__ == "__main__":
    build()
