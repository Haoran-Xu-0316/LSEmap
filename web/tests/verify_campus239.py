"""Verify source238 and independently reopened239 relief assembly.

Before integration, save a compact source snapshot without changing the native.
After integration, allow only the exact reviewed visibility replacements while
protecting geometry, UVs, material nodes, modifiers and existing room ownership.
Fixed project paths keep the verification reproducible in Blender's editor.
"""

from pathlib import Path
import ast
import hashlib
import json
import sys
import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import (
    accepted_fingerprints,
    object_fingerprint,
    update_scene,
)
from refine_portsmouth_exterior207 import material_fingerprint
from refine_ksw_exterior219 import modifier_state
from refine_kgs_surface237 import normal_record

OUT = ROOT / "result/blender/stage239"
PRIOR = ROOT / "result/blender/stage238"
BASE = ROOT / "result/blender/LSE_campus_detailed_v238.blend"
FINAL = ROOT / "result/blender/LSE_campus_detailed_v239.blend"
BASE_SHA = "8f837ee09610a13d31f24fe586737b8f80ddf09a0791e61649047999302995e5"
OUT.mkdir(parents=True, exist_ok=True)


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def stable_modifiers(obj):
    return json.loads(json.dumps(modifier_state(obj)))


expected = accepted_fingerprints(PRIOR, BASE_SHA)
previous = read(PRIOR / "building-refinement.json")
visibility = read(PRIOR / "baseline-state.json")["visibility"]
visibility.update({n: True for n in previous["archivedObjects"]})
visibility.update({n: False for n in previous["addedObjects"]})
snapshot = OUT / "protected-source-state.json"
if not snapshot.exists():
    assert BASE.exists() and hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert {o.name: object_fingerprint(o) for o in bpy.data.objects} == expected
    assert {o.name: o.hide_render for o in bpy.data.objects} == visibility
    metadata = read(OUT / "metadata-before.json")
    campus = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    protected = dict(
        baselineSha256=BASE_SHA,
        materials={m.name: material_fingerprint(m) for m in bpy.data.materials},
        normals={
            o.name: normal_record(o.data) for o in bpy.data.objects if o.type == "MESH"
        },
        properties={o.name: repr(sorted(o.items())) for o in bpy.data.objects},
        modifiers={o.name: stable_modifiers(o) for o in bpy.data.objects},
        ownership={
            o.name: sorted(c.name for c in o.users_collection) for o in bpy.data.objects
        },
        rooms={
            r["collection"]: sorted(
                o.name for o in bpy.data.collections[r["collection"]].all_objects
            )
            for r in metadata["spaces"]
        },
        roomCampusObjects={
            r["collection"]: sorted(
                o.name
                for o in bpy.data.collections[r["collection"]].all_objects
                if o.name in campus.objects
            )
            for r in metadata["spaces"]
        },
    )
    assert len(protected["rooms"]) == 35
    if snapshot.exists():
        assert read(snapshot) == protected
    else:
        write(snapshot, protected)
else:
    protected = read(snapshot)
    assert protected["baselineSha256"] == BASE_SHA
    # The independently captured source snapshot is reusable only for the exact
    # accepted native bytes; the final assembly is still reopened and checked.
    if BASE.exists():
        assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA

if not FINAL.exists():
    print(
        "CAMPUS239_SOURCE_SNAPSHOT",
        len(expected),
        len(protected["materials"]),
        flush=True,
    )
else:
    record = read(OUT / "building-refinement.json")
    assert record["version"] == 239 and record["baselineSha256"] == BASE_SHA
    assert hashlib.sha256(FINAL.read_bytes()).hexdigest() == record["sourceModelSha256"]
    assert read(OUT / "baseline-state.json") == dict(
        fingerprints=expected, visibility=visibility
    )
    assert record["changedObjects"] == []
    added = record["addedObjects"]
    archived = record["archivedObjects"]
    assert len(added) == len(set(added)) and not set(added) & set(expected)
    assert len(archived) == len(set(archived)) and set(archived) <= set(expected)
    assert all(not visibility[n] for n in archived)
    shared_ownership = {}
    for public in record.get("publicInteriors", []):
        for name in public["sharedObjects"]:
            shared_ownership.setdefault(name, set()).add(public["collection"])
    bpy.ops.wm.open_mainfile(filepath=str(FINAL))
    update_scene()
    assert set(bpy.data.objects.keys()) == set(expected) | set(added)
    for name, value in expected.items():
        obj = bpy.data.objects[name]
        assert object_fingerprint(obj) == value, name
        if obj.type == "MESH":
            assert normal_record(obj.data) == protected["normals"][name], name
        assert obj.hide_render == (True if name in archived else visibility[name]), name
        assert stable_modifiers(obj) == protected["modifiers"][name], name
        assert repr(sorted(obj.items())) == protected["properties"][name], name
        assert {c.name for c in obj.users_collection} == set(
            protected["ownership"][name]
        ) | shared_ownership.get(name, set()), name
    assert all(
        material_fingerprint(bpy.data.materials[n]) == v
        for n, v in protected["materials"].items()
    )
    assert all(
        object_fingerprint(bpy.data.objects[n]) == v
        for n, v in record["addedFingerprints"].items()
    )
    assert all(not bpy.data.objects[n].hide_render for n in added)
    relief = read(ROOT / "result/blender/old-clare239/audit.json")
    assert len(relief["addedObjects"]) == 5
    for name, normals in relief["replacementNormals"].items():
        obj = bpy.data.objects[name]
        assert normal_record(obj.data) == normals, name
        assert object_fingerprint(obj) == relief["addedFingerprints"][name], name
        assert not obj.modifiers and len(obj.data.materials) == 1
        assert obj.data.materials[0].name in protected["materials"]
        assert obj.data.uv_layers.get("StoneFinish194")
        assert all(len(f.vertices) >= 3 for f in obj.data.polygons)
    room_count = 0
    for collection, names in protected["rooms"].items():
        assert (
            sorted(o.name for o in bpy.data.collections[collection].all_objects)
            == names
        )
        assert (
            sorted(
                n for n in names if n in bpy.data.scenes["00_CAMPUS_COMPLETE"].objects
            )
            == protected["roomCampusObjects"][collection]
        )
        room_count += len(names)
    for change in record["changes"]:
        audit = read(ROOT / change["report"])
        assert audit["baselineSha256"] == BASE_SHA
        component = ROOT / audit.get("componentPath", audit.get("component", ""))
        assert (
            hashlib.sha256(component.read_bytes()).hexdigest()
            == audit["componentSha256"]
            == change["componentSha256"]
        )
        assert set(audit["addedObjects"]) == set(change["addedObjects"])
        assert set(audit["archivedObjects"]) == set(change["archivedObjects"])
        ownership = audit.get("displayOwnership", {})
        for scene_name in (
            ownership.get("scenes", []) if isinstance(ownership, dict) else []
        ):
            authored_scene = bpy.data.scenes[scene_name]
            assert all(
                name in authored_scene.objects for name in change["addedObjects"]
            ), scene_name
            assert all(
                bpy.data.objects[name].visible_get(
                    view_layer=authored_scene.view_layers[0]
                )
                for name in change["addedObjects"]
            ), scene_name + " hides the current public assembly"
    # Execute only the production selector on the actual reopened native.
    # The overview and exterior must include the same authored public collection
    # that the interior loads, never the superseded hard-coded library set.
    exporter = ast.parse((ROOT / "web/tools/export_scene.py").read_text())
    selector = next(
        n
        for n in exporter.body
        if isinstance(n, ast.FunctionDef) and n.name == "exterior_objects"
    )
    namespace = {"bpy": bpy}
    exec(
        compile(
            ast.Module(body=[selector], type_ignores=[]),
            "production-exterior-selection",
            "exec",
        ),
        namespace,
    )
    metadata = read(ROOT / "web/tools/building-metadata.json")
    library = next(b for b in metadata["buildings"] if b["code"] == "LRB")
    best_public = bpy.data.collections[library["interiorCollection"]]
    selected = {
        o.name for o in namespace["exterior_objects"](library) if not o.hide_render
    }
    current_public = {o.name for o in best_public.all_objects if not o.hide_render}
    old_public = {
        o.name
        for o in bpy.data.collections["LRB_PUBLIC_INTERIOR_study"].all_objects
        if not o.hide_render
    }
    assert current_public <= selected
    assert not (old_public - current_public) & selected
    routes = record.get(
        "libraryNativeViewRouting", previous["libraryNativeViewRouting"]
    )
    assert {row["scene"] for row in routes} == {
        "00_CAMPUS_COMPLETE",
        "04_LRB_DETAIL_REVIEW",
    }
    for row in routes:
        scene = bpy.data.scenes[row["scene"]]
        layer = scene.view_layers[row["viewLayer"]]
        assert best_public.name in scene.collection.children
        assert all(
            o.visible_get(view_layer=layer)
            for o in best_public.all_objects
            if not o.hide_render
        )
        assert all(
            not o.visible_get(view_layer=layer)
            for o in bpy.data.collections[row["excludedArchive"]].all_objects
        )
    for public in record.get("publicInteriors", []):
        collection = bpy.data.collections[public["collection"]]
        assert {o.name for o in collection.all_objects} == set(public["objects"]) | set(
            public["sharedObjects"]
        )
        assert collection.name in bpy.data.scenes[public["scene"]].collection.children
        assert (
            collection.name in bpy.data.scenes["00_CAMPUS_COMPLETE"].collection.children
        )
        assert all(
            n in bpy.data.collections[public["exteriorCollection"]].objects
            for n in public["exteriorObjects"]
        )
        code = public["exteriorCollection"].removesuffix("_EXTERIOR")
        authored = next(b for b in metadata["buildings"] if b["code"] == code)
        assert authored["interiorCollection"] == collection.name
        exterior = {
            o.name for o in namespace["exterior_objects"](authored) if not o.hide_render
        }
        assert {o.name for o in collection.all_objects if not o.hide_render} <= exterior
        assert (
            not {
                o.name
                for o in bpy.data.collections[
                    code + "_PUBLIC_INTERIOR_study"
                ].all_objects
            }
            & exterior
        )
    shared_public_routes = []
    campus = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    for code in ["CBG", "MAR", "SAW"]:
        authored = next(b for b in metadata["buildings"] if b["code"] == code)
        collection = bpy.data.collections[
            authored.get("interiorCollection", code + "_PUBLIC_INTERIOR_study")
        ]
        names = {o.name for o in collection.all_objects if not o.hide_render}
        selected = {
            o.name for o in namespace["exterior_objects"](authored) if not o.hide_render
        }
        assert names <= selected, (
            code + " public assembly missing from geographic exterior"
        )
        assert names <= set(campus.objects.keys()), (
            code + " public assembly missing from native campus"
        )
        assert all(
            bpy.data.objects[n].visible_get(view_layer=campus.view_layers[0])
            for n in names
        ), code
        shared_public_routes.append(
            dict(code=code, collection=collection.name, visibleObjects=len(names))
        )
    # Every new component has a single explicit display owner. Independent
    # rooms remain outside the geographic campus; exterior changes are shared.
    for change in record["changes"]:
        audit = read(ROOT / change["report"])
        collection = bpy.data.collections[audit["destinationCollection"]]
        assert set(change["addedObjects"]) <= {o.name for o in collection.all_objects}
        if audit.get("collectionSpec", {}).get("kind") == "independent-room":
            assert not set(change["addedObjects"]) & set(campus.objects.keys())
            assert any(
                room["collection"] == collection.name for room in metadata["spaces"]
            ) or any(
                b.get("interiorCollection") == collection.name
                for b in metadata["buildings"]
            )
        elif collection.name in {
            "00_SITE",
            "01_CITY_CONTEXT_estimated_heights",
            "03_PUBLIC_REALM",
        }:
            assert set(change["addedObjects"]) <= set(campus.objects.keys())
            assert all(
                bpy.data.objects[n].visible_get(view_layer=campus.view_layers[0])
                for n in change["addedObjects"]
            )
            assert not any(
                set(change["addedObjects"]) & set(names)
                for names in protected["rooms"].values()
            )
        else:
            authored = next(
                b for b in metadata["buildings"] if b["code"] == change["code"]
            )
            selected_names = {o.name for o in namespace["exterior_objects"](authored)}
            assert set(change["addedObjects"]) <= selected_names
            assert set(change["addedObjects"]) <= set(campus.objects.keys())
            assert all(
                bpy.data.objects[n].visible_get(view_layer=campus.view_layers[0])
                for n in change["addedObjects"]
            )
    result = dict(
        sourceModelSha256=record["sourceModelSha256"],
        baselineSha256=BASE_SHA,
        originalObjectsVerified=len(expected),
        originalMeshNormalsVerified=len(protected["normals"]),
        originalMaterialNodesVerified=len(protected["materials"]),
        sourceRoomObjectsVerified=room_count,
        sourceRoomsVerified=35,
        addedObjectsVerified=len(added),
        exactArchiveObjectsVerified=len(archived),
        originalGeometryUVsBindingsModifiersAndExistingOwnershipPreserved=True,
        allOriginalCustomPropertiesPreserved=True,
        explicitlySharedSourceObjects=len(shared_ownership),
        publicInteriorAssemblies=len(record.get("publicInteriors", [])),
        wholeBuildingInteriorsClaimed=False,
        completeModelReopened=True,
        libraryOverviewAndInteriorSharePublicCollection=True,
        nativeCampusAndDetailUseSameCurrentLibrary=True,
        refinedPublicRoutes=shared_public_routes,
        currentLibraryPublicObjects=len(current_public),
    )
    write(OUT / "native-verification.json", result)
    print("CAMPUS239_NATIVE", result, flush=True)


def verify_relief_geometry():
    from mathutils import Vector
    import bpy, bmesh, json
    from pathlib import Path

    ROOT = Path("/Users/haoranxu/Desktop/LSEmap")
    study = json.loads(
        (ROOT / "result/blender/stage89/old-clare-reliefs-audit.json").read_text()
    )
    origin, axis, normal = [
        Vector(study["frame"][k]) for k in ["origin", "right", "outward"]
    ]
    checks = []
    for panel in study["panels"]:
        name = "OLD239_relief_" + str(panel["panel"])
        obj = bpy.data.objects[name]
        mesh = obj.data
        points = [obj.matrix_world @ v.co - origin for v in mesh.vertices]
        coordinates = [
            Vector(
                (
                    (p.dot(axis) - panel["centre"]) / (study["width"] * 0.44),
                    p.dot(normal),
                    (p.z - 5.37) / 0.96,
                )
            )
            for p in points
        ]
        adjacency = [[] for _ in mesh.vertices]
        for edge in mesh.edges:
            a, b = edge.vertices
            adjacency[a].append(b)
            adjacency[b].append(a)
        pending = set(range(len(mesh.vertices)))
        components = []
        while pending:
            seed = pending.pop()
            component = {seed}
            stack = [seed]
            while stack:
                i = stack.pop()
                for j in adjacency[i]:
                    if j in pending:
                        pending.remove(j)
                        component.add(j)
                        stack.append(j)
            components.append(component)
        body = max(components, key=len)
        hx, hz = panel["head"]
        hip = Vector((panel["limbs"][0][0][-1][0], 0.14, panel["limbs"][0][0][-1][1]))
        head = min(
            range(len(coordinates)),
            key=lambda i: (coordinates[i] - Vector((hx, 0.10, hz))).length,
        )
        torso = min(
            range(len(coordinates)), key=lambda i: (coordinates[i] - hip).length
        )
        assert head in body and torso in body, (name, len(body), head, torso)
        assert (coordinates[head] - Vector((hx, 0.10, hz))).length < 0.08
        assert (coordinates[torso] - hip).length < 0.14
        bm = bmesh.new()
        bm.from_mesh(mesh)
        nonmanifold = sum(not e.is_manifold for e in bm.edges)
        loose = sum(not v.link_edges for v in bm.verts)
        bm.free()
        assert not nonmanifold and not loose, (name, nonmanifold, loose)
        depth = [p.y for p in coordinates]
        z = [5.37 + p.z * 0.96 for p in coordinates]
        assert 0.04 < min(depth) < max(depth) < 0.23
        assert 5.30 < min(z) < max(z) < 6.34
        triangles = sum(len(p.vertices) - 2 for p in mesh.polygons)
        assert triangles < 23000
        checks.append(
            dict(
                name=name,
                panel=panel["panel"],
                sourcePose=study["frontageOrder"][panel["panel"] - 1],
                triangles=triangles,
                largestBodyVertices=len(body),
                headAndTorsoInOneConnectedSurface=True,
                nonmanifoldEdges=nonmanifold,
                looseVertices=loose,
                depthRange=[min(depth), max(depth)],
            )
        )
    result = dict(
        savedCompleteModel=True,
        frontageOrder=study["frontageOrder"],
        checks=checks,
        totalReliefTriangles=sum(c["triangles"] for c in checks),
        measuredSculptureClaimed=False,
    )
    (ROOT / "result/blender/stage239/relief-geometry-verification.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("RELIEF239_GEOMETRY_VERIFIED", result["totalReliefTriangles"], flush=True)


if FINAL.exists():
    verify_relief_geometry()
