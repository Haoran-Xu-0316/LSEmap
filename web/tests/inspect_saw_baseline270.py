"""Verify frozen SAW263 against native269 using pure JSON fingerprints.

The parent runs this fixed script in the serial Blender window. It hashes every
saved SAW mesh, UV/attribute layer, material node input, transform, modifier,
owner and visibility state before using269. It never saves either complete
native. This script creates no scene, component or material.
"""
import array
import hashlib
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/saw270"
BASELINES = (
    (ROOT / "result/blender/LSE_campus_detailed_v263.blend", "f55f5975ea5e4d755f0c883bc64965b928a3d03add666c598a9b7e987bb70c2d"),
    (ROOT / "result/blender/LSE_campus_detailed_v269.blend", "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b"),
)
COLLECTIONS = ("SAW_EXTERIOR", "SAW_PUBLIC_INTERIOR_study")


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def serial(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, bpy.types.ID):
        return {"idType": value.bl_rna.identifier, "name": value.name_full}
    if hasattr(value, "items"):
        return {str(key): serial(item) for key, item in value.items()}
    try:
        return [serial(item) for item in value]
    except TypeError:
        return value.bl_rna.identifier


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def rna_scalars(item):
    result = {}
    for prop in item.bl_rna.properties:
        if prop.identifier in {"rna_type", "users", "session_uid", "is_updated", "is_updated_data", "is_evaluated", "is_runtime_data"} or prop.type not in {"BOOLEAN", "INT", "FLOAT", "STRING", "ENUM", "POINTER"}:
            continue
        value = getattr(item, prop.identifier)
        if prop.type == "POINTER" and value is not None and not isinstance(value, bpy.types.ID):
            continue
        result[prop.identifier] = serial(value)
    return result


def collection_bytes(sequence, field, kind, width=1):
    values = array.array(kind, [0]) * (len(sequence) * width)
    sequence.foreach_get(field, values)
    return values.tobytes()


def mesh_fingerprint(mesh):
    digest = hashlib.sha256()
    for sequence, field, kind, width in (
        (mesh.vertices, "co", "f", 3), (mesh.edges, "vertices", "i", 2),
        (mesh.loops, "vertex_index", "i", 1), (mesh.polygons, "loop_start", "i", 1),
        (mesh.polygons, "loop_total", "i", 1), (mesh.polygons, "material_index", "i", 1),
        (mesh.polygons, "use_smooth", "b", 1),
    ):
        digest.update(field.encode())
        digest.update(collection_bytes(sequence, field, kind, width))
    layers = []
    for layer in mesh.uv_layers:
        values = collection_bytes(layer.data, "uv", "f", 2)
        layers.append({"name": layer.name, "sha256": hashlib.sha256(values).hexdigest()})
    attributes = []
    for attribute in mesh.attributes:
        if attribute.name.startswith(".select_") or attribute.name == "position":
            continue
        attributes.append({"name": attribute.name, "domain": attribute.domain,
            "type": attribute.data_type,
            "sha256": digest_json([rna_scalars(value) for value in attribute.data])})
    return {"topologyCoordinatesAndFaceMaterialSha256": digest.hexdigest(), "uv": layers,
        "attributes": attributes, "vertices": len(mesh.vertices), "polygons": len(mesh.polygons),
        "shapeKeys": None if mesh.shape_keys is None else digest_json([
            {"name": key.name, "coordinatesSha256": hashlib.sha256(collection_bytes(key.data, "co", "f", 3)).hexdigest()}
            for key in mesh.shape_keys.key_blocks])}


def material_fingerprint(material):
    record = {"properties": rna_scalars(material), "custom": serial(dict(material.items()))}
    if material.use_nodes:
        tree = material.node_tree
        nodes = []
        for node in tree.nodes:
            value = {"name": node.name, "type": node.bl_idname, "properties": rna_scalars(node),
                "inputs": {socket.identifier: serial(socket.default_value) for socket in node.inputs if hasattr(socket, "default_value")},
                "outputs": {socket.identifier: serial(socket.default_value) for socket in node.outputs if hasattr(socket, "default_value")}}
            if hasattr(node, "color_ramp"):
                value["ramp"] = [(element.position, list(element.color)) for element in node.color_ramp.elements]
            nodes.append(value)
        record["nodes"] = nodes
        record["links"] = [(link.from_node.name, link.from_socket.identifier,
                            link.to_node.name, link.to_socket.identifier) for link in tree.links]
    return digest_json(record)


def inventory(inspection):
    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    bpy.context.window.scene = scene
    for layer in scene.view_layers:
        layer.update()
    objects = {obj.name: obj for name in COLLECTIONS for obj in bpy.data.collections[name].all_objects}
    expected = {row["name"]: row for row in inspection["objects"]}
    assert set(objects) == set(expected), "SAW membership differs from frozen263 inventory"
    materials = {material.name: material for obj in objects.values() if obj.type == "MESH"
                 for material in obj.data.materials if material}
    material_hashes = {name: material_fingerprint(material) for name, material in materials.items()}
    records = {}
    for name, obj in sorted(objects.items()):
        assert obj.type == expected[name]["type"] == "MESH", name
        mesh = mesh_fingerprint(obj.data)
        assert mesh["vertices"] == expected[name]["savedMesh"]["vertices"], name
        assert mesh["polygons"] == expected[name]["savedMesh"]["polygons"], name
        records[name] = {"mesh": mesh, "matrix": [list(row) for row in obj.matrix_world],
            "parent": None if obj.parent is None else obj.parent.name,
            "owners": sorted(collection.name for collection in obj.users_collection),
            "visibility": [obj.hide_render, obj.hide_viewport, obj.hide_get()],
            "properties": serial(dict(obj.items())),
            "modifiers": [rna_scalars(modifier) for modifier in obj.modifiers],
            "materials": [(None, None) if material is None else (material.name, material_hashes[material.name])
                          for material in obj.data.materials]}
    return records


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inspection = json.loads((ROOT / "result/blender/saw269/native-inspection.json").read_text())
    assert inspection["baselineSha256"] == BASELINES[0][1]
    records = []
    for path, expected in BASELINES:
        assert sha(path) == expected, str(path)
        bpy.ops.wm.open_mainfile(filepath=str(path))
        # A JSON round trip guarantees that no RNA/ID/socket wrapper survives
        # the next file load. Only Python dict/list/str/numeric values remain.
        records.append(json.loads(json.dumps(inventory(inspection))))
    differences = [name for name in records[0] if records[0][name] != records[1][name]]
    report = {"status": "preflight-failed" if differences else "baseline-comparison-passed",
        "baselines": [{"path": str(path.relative_to(ROOT)), "sha256": expected} for path, expected in BASELINES],
        "comparedObjects": len(records[0]), "differences": differences,
        "fingerprints263": {name: digest_json(value) for name, value in records[0].items()},
        "fingerprints269": {name: digest_json(value) for name, value in records[1].items()},
        "fields": "Coordinates/edges/loop topology/face materials/smoothing, all UV and nonselection attributes, shape keys, node material inputs, transforms, parents, owners, modifiers, visibility, custom properties",
        "formalNativesSaved": False, "assemblyTransformApplied": False,
        "dimensionalAcceptance": "No assembly transform applied; no width/headroom/support acceptance claimed."}
    (OUT / "baseline-preservation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    assert not differences, f"SAW263->269 mismatch; stop before component creation: {differences}"
    for path, expected in BASELINES:
        assert sha(path) == expected
    print("SAW270_BASELINE_COMPARISON", len(records[0]), len(differences), flush=True)


if __name__ == "__main__":
    main()
