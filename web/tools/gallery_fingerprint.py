"""Fingerprint actual render inputs, allowing unchanged views to be reused safely.

Only evaluated geometry, transforms, shader inputs, visibility and render settings
matter. Filenames and the edition number do not change how a scene is rendered.
"""
from array import array
import hashlib
import json
import bpy
import numpy as np


def values(value):
    if isinstance(value, (str, bool, int, float)) or value is None:
        return value
    if hasattr(value, 'to_list'):
        return value.to_list()
    try:
        return [values(item) for item in value]
    except TypeError:
        return getattr(value, 'name', type(value).__name__)


def node_tree_state(tree):
    if tree is None:
        return None
    nodes = []
    for node in tree.nodes:
        properties = {}
        for prop in node.bl_rna.properties:
            if prop.identifier == 'rna_type' or prop.type not in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}:
                continue
            try:
                properties[prop.identifier] = values(getattr(node, prop.identifier))
            except (AttributeError, TypeError):
                continue
        record = {'name': node.name, 'type': node.bl_idname, 'properties': properties,
                  'inputs': [(socket.identifier, values(socket.default_value)) for socket in node.inputs if hasattr(socket, 'default_value')]}
        if hasattr(node, 'color_ramp'):
            ramp = node.color_ramp
            record['ramp'] = {'interpolation': ramp.interpolation, 'mode': ramp.color_mode,
                              'elements': [(item.position, list(item.color)) for item in ramp.elements]}
        if node.type == 'GROUP':
            record['group'] = node_tree_state(node.node_tree)
        if node.type == 'TEX_IMAGE':
            raise AssertionError('Archive images must be removed before public rendering')
        nodes.append(record)
    links = [(link.from_node.name, link.from_socket.identifier, link.to_node.name, link.to_socket.identifier) for link in tree.links]
    return {'nodes': sorted(nodes, key=lambda item: item['name']), 'links': sorted(links)}


class RenderFingerprint:
    def __init__(self):
        self.geometry_cache = {}
        self.material_cache = {}

    def material(self, material):
        if material is None:
            return None
        if material.name not in self.material_cache:
            self.material_cache[material.name] = {'color': list(material.diffuse_color),
                'nodes': node_tree_state(material.node_tree), 'use_nodes': material.use_nodes}
        return self.material_cache[material.name]

    def geometry(self, obj, depsgraph):
        if obj.name not in self.geometry_cache:
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)
            try:
                digest = hashlib.sha256()
                for elements, attribute, width, kind in [
                    (mesh.vertices, 'co', 3, 'f'), (mesh.loops, 'vertex_index', 1, 'i'),
                    (mesh.polygons, 'loop_start', 1, 'i'), (mesh.polygons, 'loop_total', 1, 'i'),
                    (mesh.polygons, 'material_index', 1, 'i'), (mesh.polygons, 'use_smooth', 1, 'b'),
                    (mesh.corner_normals, 'vector', 3, 'f'),
                ]:
                    buffer = array(kind, [0]) * (len(elements) * width)
                    elements.foreach_get(attribute, buffer)
                    digest.update(buffer.tobytes())
                for layer in mesh.uv_layers:
                    buffer = array('f', [0]) * (len(layer.data) * 2)
                    layer.data.foreach_get('uv', buffer)
                    digest.update(layer.name.encode())
                    # Saved float UVs can differ at sub-nanometre scale after
                    # Blender reloads. Compare UVs at one-millionth-unit precision;
                    # positions, normals and topology remain byte-exact.
                    uv = np.round(np.asarray(buffer), decimals=6).astype('<f4')
                    uv[uv == 0] = 0
                    digest.update(uv.tobytes())
                self.geometry_cache[obj.name] = {'geometry': digest.hexdigest(),
                    'materials': [self.material(material) for material in mesh.materials]}
            finally:
                bpy.data.meshes.remove(mesh)
        return self.geometry_cache[obj.name]

    def scene(self, scene):
        bpy.context.window.scene = scene
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        objects = []
        for obj in scene.objects:
            if obj.hide_render or obj.type not in {'MESH', 'CURVE', 'FONT', 'SURFACE', 'LIGHT'}:
                continue
            record = {'transform': [list(row) for row in obj.matrix_world], 'type': obj.type}
            if obj.type == 'LIGHT':
                record['light'] = {key: values(getattr(obj.data, key, None)) for key in
                    ['type', 'energy', 'color', 'shape', 'size', 'size_y', 'angle', 'shadow_soft_size', 'use_nodes']}
                record['nodes'] = node_tree_state(obj.data.node_tree)
            else:
                record.update(self.geometry(obj, depsgraph))
                record['visibility'] = {key: getattr(obj, key, None) for key in
                    ['visible_camera', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_shadow']}
            objects.append(record)
        camera = scene.camera
        state = {'fingerprintVersion': 2, 'uvPrecision': 1e-6, 'objects': sorted(objects, key=lambda item: json.dumps(item, sort_keys=True)),
                 'camera': {'transform': [list(row) for row in camera.matrix_world],
                            **{key: getattr(camera.data, key) for key in ['type', 'lens', 'sensor_width', 'sensor_height', 'sensor_fit', 'ortho_scale', 'shift_x', 'shift_y', 'clip_start', 'clip_end']}},
                 'world': node_tree_state(scene.world.node_tree),
                 'render': {key: getattr(scene.render, key) for key in ['engine', 'resolution_x', 'resolution_y', 'resolution_percentage', 'film_transparent']},
                 'cycles': {key: getattr(scene.cycles, key) for key in ['samples', 'seed', 'use_denoising', 'max_bounces', 'device']},
                 'view': {key: getattr(scene.view_settings, key) for key in ['view_transform', 'look', 'exposure', 'gamma']}}
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
