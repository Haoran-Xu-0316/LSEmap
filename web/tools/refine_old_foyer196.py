"""Refine the registered historical OLD foyer finishes and entrance mat.

Open in Blender's Text Editor. The2011 Design Engine built photograph supports
stone slab joints, a dark entrance mat and pale suspended disc lamps. Sizes and
optical values are estimates. Existing foyer geometry and all original UVs stay
exact; this does not claim a new current floor plan or adjoining rooms.
"""
from pathlib import Path
import hashlib
import json
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import object_fingerprint
from refine_col_exterior195 import state
from build_room_samples167 import RoomGeometry
BASE = ROOT / 'result/blender/LSE_campus_detailed_v195.blend'
BASE_SHA = '93aab89a4f76c5343ee085c6271046294d6f51a801a42b118c8a4445703a4ac2'
OUT = ROOT / 'result/blender/old-foyer196'
PREFIX = 'OLD196_FOYER_'
SOURCE = 'https://www.designengine.co.uk/projects/reception-london-school-of-economics/'
OWNED = ['OLD174_foyer_lower_limestone_floor', 'OLD174_foyer_disc_light_rims', 'OLD174_foyer_disc_light_diffusers']


def procedural_material(name, first, second, width, height, joint, roughness):
    material = bpy.data.materials.new(PREFIX + name)
    material.use_nodes = True
    material.diffuse_color = (*first, 1)
    nodes = material.node_tree.nodes
    shader = nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*first, 1)
    shader.inputs['Metallic'].default_value = 0
    shader.inputs['Roughness'].default_value = roughness
    uv = nodes.new('ShaderNodeTexCoord')
    brick = nodes.new('ShaderNodeTexBrick')
    brick.offset = 0
    for key, value in [('Scale', 1), ('Mortar Size', joint), ('Mortar Smooth', .02), ('Brick Width', width), ('Row Height', height)]:
        brick.inputs[key].default_value = value
    brick.inputs['Color1'].default_value = (*first, 1)
    brick.inputs['Color2'].default_value = (*second, 1)
    brick.inputs['Mortar'].default_value = (*(tuple(value * .85 for value in first)), 1)
    material.node_tree.links.new(uv.outputs['UV'], brick.inputs['Vector'])
    material.node_tree.links.new(brick.outputs['Color'], shader.inputs['Base Color'])
    return material


def preview(scene, originals, additions, phase):
    for obj in scene.objects:
        if obj.type in {'MESH', 'FONT', 'CURVE'}:
            obj.hide_render = obj.name not in originals | set(additions)
    for name in OWNED:
        bpy.data.objects[name].hide_render = phase == 'after'
    for obj in additions.values():
        obj.hide_render = phase == 'before'
    scene.render.filepath = str(OUT / (phase + '.png'))
    bpy.ops.render.render(write_still=True)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.window.scene = scene
    for layer in scene.view_layers:
        layer.update()
    fingerprints = {obj.name:object_fingerprint(obj) for obj in bpy.data.objects}
    visibility = {obj.name:(obj.hide_render, obj.hide_viewport, obj.hide_get()) for obj in bpy.data.objects}
    source = bpy.data.collections['OLD_MAIN_FOYER174']
    originals = {obj.name for obj in source.all_objects if not obj.hide_render}
    candidate = bpy.data.collections.new(PREFIX + 'COMPONENT')
    scene.collection.children.link(candidate)
    replacements = []
    added = {}
    for name in OWNED:
        original = bpy.data.objects[name]
        assert not original.hide_render
        obj = original.copy()
        obj.data = original.data.copy()
        obj.name = PREFIX + name.removeprefix('OLD174_foyer_')
        obj['originalObject'] = name
        obj['referencePeriod'] = '2011 built refurbishment'
        obj['dimensionBasis'] = 'Existing registered geometry retained; photographic finishes estimated'
        candidate.objects.link(obj)
        obj.data.materials.clear()
        if name.endswith('lower_limestone_floor'):
            material = procedural_material('neutral_limestone_slabs', (.72,.70,.65), (.735,.715,.665), .90, .60, .002, .78)
        else:
            material = original.data.materials[0].copy()
            material.name = PREFIX + ('satin_pale_lamp_rims' if name.endswith('rims') else 'warm_disc_diffusers')
            shader = material.node_tree.nodes.get('Principled BSDF')
            color = (.71,.73,.70,1) if name.endswith('rims') else (.94,.91,.80,1)
            material.diffuse_color = color
            shader.inputs['Base Color'].default_value = color
            shader.inputs['Metallic'].default_value = 0
            shader.inputs['Roughness'].default_value = .48 if name.endswith('rims') else .7
            if name.endswith('diffusers'):
                material['webEmission'] = True
                shader.inputs['Emission Color'].default_value = color
                shader.inputs['Emission Strength'].default_value = 1.2
        obj.data.materials.append(material)
        assert state(obj)['geometry'] == state(original)['geometry']
        assert state(obj)['uv'] == state(original)['uv']
        replacements.append({'object':obj.name,'originalObject':name,'originalState':state(original)})
        added[obj.name] = obj
    floor = bpy.data.objects[OWNED[0]]
    top = max(vertex.co.z for vertex in floor.data.vertices)
    # Door centre is local x0. The mat stays on the broad lower landing,
    # well before the four steps and away from either side reception station.
    width, depth, center_y = 4.2, 2.1, 2.65
    g = RoomGeometry(candidate, PREFIX)
    g.materials['carpet'] = procedural_material('dark_ribbed_entrance_mat', (.026,.031,.033), (.036,.042,.043), .018, 3, .002, .97)
    g.box('entrance_mat','carpet',(0,center_y,top+.0035),(width,depth,.006))
    mat = g.finish()[0]
    mat.matrix_world = floor.matrix_world.copy()
    mat['referencePeriod'] = '2011 built refurbishment'
    mat['dimensionBasis'] = 'Photo-visible mat; width4.2m and depth2.1m are placement estimates inside existing registered lower landing'
    added[mat.name] = mat
    tree = BVHTree.FromPolygons([floor.matrix_world @ vertex.co for vertex in floor.data.vertices], [list(face.vertices) for face in floor.data.polygons])
    floor_samples = []
    for x in [-width/2,0,width/2]:
        for y in [center_y-depth/2,center_y,center_y+depth/2]:
            origin = floor.matrix_world @ Vector((x,y,top+.1))
            hit = tree.ray_cast(origin,Vector((0,0,-1)),.2)
            assert hit[0] is not None
            floor_samples.append(list(hit[0]))
    # Preview the same bounded room before/after with unchanged light and view.
    camera = bpy.data.objects.new(PREFIX+'preview_camera',bpy.data.cameras.new(PREFIX+'preview_camera'))
    scene.collection.objects.link(camera)
    camera.data.type = 'ORTHO';camera.data.ortho_scale = 21
    camera.location = floor.matrix_world @ Vector((8,-15,13))
    target = floor.matrix_world @ Vector((0,3.8,1.6))
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera = camera
    world = bpy.data.worlds.new(PREFIX+'preview_world');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.78,.82,.87,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
    light_data=bpy.data.lights.new(PREFIX+'preview_sun','SUN');light_data.energy=2
    light=bpy.data.objects.new(light_data.name,light_data);scene.collection.objects.link(light)
    light.rotation_euler=Vector((-.6,.5,-1)).to_track_quat('-Z','Y').to_euler()
    scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.resolution_x=1200;scene.render.resolution_y=850;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    preview(scene,originals,added,'before');preview(scene,originals,added,'after')
    for name,values in visibility.items():
        obj=bpy.data.objects[name];obj.hide_render,obj.hide_viewport=values[:2];obj.hide_set(values[2])
    for obj in added.values():obj.hide_render=False;obj.hide_viewport=False;obj.hide_set(False)
    assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in fingerprints.items())
    component=OUT/'old-foyer196-component.blend'
    bpy.data.libraries.write(str(component),set(added.values()),fake_user=True,compress=True)
    report=dict(version=196,baselineSha256=BASE_SHA,componentPath=str(component.relative_to(ROOT)),
                componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),targetCollection='OLD_MAIN_FOYER174',destinationCollection='OLD_MAIN_FOYER174',
                addedObjects=list(added),archivedObjects=OWNED,replacements=replacements,
                fingerprints={name:object_fingerprint(obj) for name,obj in added.items()},floorCoverageSamples=floor_samples,
                matLocalBounds=[[-width/2,center_y-depth/2,top+.0005],[width/2,center_y+depth/2,top+.0065]],
                source=SOURCE,referenceImage='result/blender/old_foyer173/reception-main.jpg',referencePeriod='2011 built refurbishment',
                scope='Registered historical foyer stone joints, dark entrance mat and pale illuminated disc lamps; original stairs, walls, UVs and room registration retained',
                limitations='Photographic finish and mat dimensions are estimates. No current2026condition or complete floor-layout claim.')
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False) as (available,target):target.objects=list(report['addedObjects'])
    for obj in target.objects:
        bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    for obj in target.objects:
        assert object_fingerprint(obj)==report['fingerprints'][obj.name],obj.name
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    (OUT/'verification.json').write_text(json.dumps(dict(componentReopened=True,addedObjectsVerified=len(added),sourceGeometryAndUVPreserved=True,baselineUnchanged=True,floorCoverageSamples=9),indent=2)+'\n')
    print('OLD_FOYER196_VERIFIED',len(added),flush=True)


if __name__ == '__main__':
    build()
