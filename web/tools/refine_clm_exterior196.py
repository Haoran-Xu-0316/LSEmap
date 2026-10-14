"""Unify Clement House street stone and painted joinery from official photographs.

Run in Blender's Text Editor. Existing geometry, UV layers, glass alpha and
interior collections are retained. One already packed original stone tone map
is reused; it is a material study, not copied photography or measured staining.
"""
from pathlib import Path
import array
import hashlib
import json

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v195.blend'
BASE_SHA = '93aab89a4f76c5343ee085c6271046294d6f51a801a42b118c8a4445703a4ac2'
OUT = ROOT / 'result/blender/clm-exterior196'
PREFIX = 'CLM196_FINISH_'
UV_NAME = 'CLMStoneFinish196'
STONE = {'CLM_D3_Portland_stone', 'V16_CLM_finish', 'V17_CLM_finish'}
REFERENCES = [
    {'path':'result/blender/clm_exterior175/official-page18-image7.png',
     'url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf',
     'scope':'Official handbook p18, printed16; street colonnade, gray warm-white stone, dark brown window frames and lower windows; tree-obscured upper facade'},
    {'path':'data/建筑图片/CLM_Clement House/01_建筑实拍/exteriors_lse_estate_003.jpg',
     'url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate',
     'scope':'Official estate side portal, neutral warm-gray stone and stained timber; photograph capture date unknown'},
]


def state(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    for data, field, kind, count in ((obj.data.vertices,'co','f',3),
                                    (obj.data.loops,'vertex_index','i',1),
                                    (obj.data.polygons,'material_index','i',1)):
        values = array.array(kind,[0]) * (len(data)*count)
        data.foreach_get(field,values)
        digest.update(values.tobytes())
    uv = {}
    for layer in obj.data.uv_layers:
        values = array.array('f',[0])*(len(layer.data)*2)
        layer.data.foreach_get('uv',values)
        uv[layer.name] = hashlib.sha256(values.tobytes()).hexdigest()
    return {'geometry':digest.hexdigest(),'uv':uv}


def family(material):
    if material.name in STONE:
        return 'stone'
    if 'bronze_or_dark_painted_metal' in material.name:
        return 'joinery'
    if material.name == 'CLM_D3_door_timber':
        return 'timber'
    if 'glass' in material.name.lower():
        return 'glass'
    return None


def finish(source,image):
    material = source.copy()
    material.name = PREFIX+source.name
    p = next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    kind = family(source)
    if kind=='stone':
        tint=(.94,.955,.975,1)
        p.inputs['Base Color'].default_value=(1,1,1,1)
        p.inputs['Metallic'].default_value=0
        p.inputs['Roughness'].default_value=.86
        uv=material.node_tree.nodes.new('ShaderNodeUVMap');uv.uv_map=UV_NAME
        texture=material.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image;texture.extension='REPEAT'
        multiply=material.node_tree.nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY'
        multiply.inputs[0].default_value=1;multiply.inputs[2].default_value=tint
        material.node_tree.links.new(uv.outputs['UV'],texture.inputs['Vector'])
        material.node_tree.links.new(texture.outputs['Color'],multiply.inputs[1])
        material.node_tree.links.new(multiply.outputs[0],p.inputs['Base Color'])
        material.diffuse_color=(.604,.611,.574,1)
        material['webBaseColorMap']=True;material['webBaseColorUV']=UV_NAME;material['webBaseColorTint']=list(tint)
    elif kind=='joinery':
        p.inputs['Base Color'].default_value=(.043,.036,.028,1)
        p.inputs['Metallic'].default_value=.04;p.inputs['Roughness'].default_value=.38
        material.diffuse_color=(.043,.036,.028,1)
    elif kind=='timber':
        p.inputs['Base Color'].default_value=(.21,.115,.063,1)
        p.inputs['Metallic'].default_value=0;p.inputs['Roughness'].default_value=.38
        material.diffuse_color=(.21,.115,.063,1)
    elif kind=='glass':
        # Registered glazing and retained alpha preserve real enclosure limits;
        # polish the dielectric response without exposing invented empty rooms.
        p.inputs['Metallic'].default_value=0;p.inputs['Roughness'].default_value=.18
    return material


def stone_uv(obj):
    layer=obj.data.uv_layers.new(name=UV_NAME)
    layer.active_render=True
    for polygon in obj.data.polygons:
        normal=obj.matrix_world.to_3x3()@polygon.normal
        if abs(normal.z)>.8:
            a,b=Vector((1,0,0)),Vector((0,1,0))
        else:
            a=Vector((-normal.y,normal.x,0)).normalized();b=Vector((0,0,1))
        for index in polygon.loop_indices:
            point=obj.matrix_world@obj.data.vertices[obj.data.loops[index].vertex_index].co
            layer.data[index].uv=(point.dot(a)/5,point.dot(b)/5)


def preview(phase):
    scene=bpy.data.scenes.new('CLM196_preview_'+phase)
    collection=bpy.data.collections.new(scene.name+'_objects');scene.collection.children.link(collection)
    for obj in bpy.data.collections['CLM_EXTERIOR'].all_objects:
        if obj.type in {'MESH','FONT','CURVE'} and not obj.hide_render:collection.objects.link(obj)
    world=bpy.data.worlds.new(scene.name+'_world');world.use_nodes=True;scene.world=world
    background=world.node_tree.nodes['Background'];background.inputs[1].default_value=.65
    env=world.node_tree.nodes.new('ShaderNodeTexEnvironment')
    env.image=bpy.data.images.load(str(ROOT/'web/public/environment/kloppenheim-sky-1k.hdr'),check_existing=True)
    world.node_tree.links.new(env.outputs['Color'],background.inputs[0])
    data=bpy.data.lights.new(scene.name+'_sun','SUN');data.energy=1.8;data.angle=.12
    sun=bpy.data.objects.new(data.name,data);collection.objects.link(sun)
    sun.rotation_euler=Vector((-.6,.5,-1)).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new(scene.name+'_camera');camera=bpy.data.objects.new(data.name,data)
    collection.objects.link(camera);scene.camera=camera;data.type='ORTHO'
    scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    views={'whole':((114.5,-151.9,14),(100,-198,24),40),
           'portal':((103,-150.5,4.3),(96,-172,8),13.5)}
    for name,(target,position,scale) in views.items():
        camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
        data.ortho_scale=scale;scene.render.filepath=str(OUT/(phase+'-'+name+'.png'))
        bpy.ops.render.render(write_still=True,scene=scene.name)
    bpy.data.scenes.remove(scene);bpy.data.collections.remove(collection)


def build_component():
    OUT.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:layer.update()
    original={o.name:state(o) for o in bpy.data.objects if o.type=='MESH'}
    image=bpy.data.images['COL195_Portland_stone_original_tone_study']
    assert image.packed_file
    image_record={'nativeImage':image.name,'sha256':hashlib.sha256(image.packed_file.data).hexdigest(),
                  'bytes':len(image.packed_file.data),'reusedExistingPackedMap':True,
                  'scope':'Original broad material tone study reused with CLM gray tint; not photographic weathering'}
    preview('before')
    materials,replacements,bindings={},[],[]
    target=bpy.data.collections['CLM_EXTERIOR']
    for source in list(target.all_objects):
        if source.type!='MESH' or source.hide_render or any(s in source.name.lower() for s in ('unobserved','rear_','roof73_chimney')):continue
        slots=[(i,m) for i,m in enumerate(source.data.materials) if m and family(m)]
        if not slots:continue
        obj=source.copy();obj.data=source.data.copy();obj.name=PREFIX+source.name
        obj['originalObject']=source.name;obj['finishScope']='CLM street stone and joinery; original geometry, original UV and glass alpha retained'
        target.objects.link(obj)
        if any(family(m)=='stone' for _,m in slots):stone_uv(obj)
        for index,source_material in slots:
            if source_material.name not in materials:materials[source_material.name]=finish(source_material,image)
            replacement=materials[source_material.name];obj.data.materials[index]=replacement
            bindings.append({'object':obj.name,'slot':index,'originalMaterial':source_material.name,'material':replacement.name,'family':family(source_material)})
        source.hide_render=True;source.hide_set(True);obj.hide_render=False;obj.hide_set(False)
        replacements.append({'originalObject':source.name,'original':source.name,'replacement':obj.name,'targetCollection':'CLM_EXTERIOR'})
        actual=state(obj);assert actual['geometry']==original[source.name]['geometry']
        assert all(actual['uv'][name]==value for name,value in original[source.name]['uv'].items())
    assert len(replacements)>25
    assert all(state(bpy.data.objects[name])==value for name,value in original.items())
    preview('after')
    path=OUT/'clm-exterior196-component.blend'
    bpy.data.libraries.write(str(path),{bpy.data.objects[r['replacement']] for r in replacements}|set(materials.values())|{image},fake_user=True)
    report={'version':196,'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':BASE_SHA,
            'componentPath':str(path.relative_to(ROOT)),'componentSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'targetCollection':'CLM_EXTERIOR','addedObjects':[r['replacement'] for r in replacements],
            'archivedObjects':[r['originalObject'] for r in replacements],'changedObjects':[],'replacements':replacements,
            'bindings':bindings,'texture':image_record,'geometryAndOriginalUVPreserved':True,
            'originalStates':{r['originalObject']:original[r['originalObject']] for r in replacements},
            'references':[dict(r,sha256=hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest(),photographCaptureDate='Unknown') for r in REFERENCES],
            'improvements':['Unify tan-yellow street stone and ochre reveal trim to photograph-guided neutral warm-gray Portland stone.',
                            'Dark brown painted window frames lose incorrect 0.55 bare-metal response.',
                            'Refine warm timber door finish from the official close portal photograph.',
                            'Reduce dielectric glass roughness to0.18 while retaining every original glass colour, alpha, transmission, face and room.'],
            'previews':['before-whole.png','after-whole.png','before-portal.png','after-portal.png'],
            'previewLighting':'Identical HDR sky, sun1.8, background0.65, AgX,24 Cycles samples',
            'limitations':['Photograph-guided estimated colours, not calibrated surface measurements or a2026 condition survey.',
                           'Official whole-front image is tree-obscured above lower storeys; upper street stone finish is extended consistently, not a new geometric claim.',
                           'Unobserved rear envelope, rear attic, roof/chimney stone and all interior collections remain unchanged.',
                           'Seven tall bays, opaque cross-storey spandrels, existing window divisions, sculptural silhouette approximations and roof geometry retain inherited estimates.',
                           'Reused tone map is original artwork, not evidence of actual CLM stains, joints or surveyed block dimensions.']}
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(path))
    checks=[]
    for r in replacements:
        obj=bpy.data.objects[r['replacement']];actual=state(obj);expected=original[r['originalObject']]
        assert actual['geometry']==expected['geometry']
        assert all(actual['uv'][name]==value for name,value in expected['uv'].items())
        assert obj['originalObject']==r['originalObject']
        checks.append({'object':obj.name,'geometryPreserved':True,'originalUVPreserved':True})
    report['verification']={'savedComponentReopened':True,'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA,'objects':checks}
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('CLM196_COMPONENT_READY',len(replacements),len(materials),flush=True)


if __name__=='__main__':
    build_component()
