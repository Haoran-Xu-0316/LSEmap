"""Review surrounding-building finishes against archived mapped attributes.

Run in Blender's Text Editor. Only explicitly attributed context materials
may change; LSE buildings and unsourced facade detail remain untouched.
"""
from pathlib import Path
import json
import hashlib
import bpy
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v198.blend'
OUT=ROOT/'result/blender/context-palette199'
SHA='b45a6a433f350226beecfd201457420d86b2d253796098f86ff5417d5752b27e'


def review_context():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    collection=bpy.data.collections['01_CITY_CONTEXT_estimated_heights']
    rows=[]
    for obj in collection.all_objects:
        if obj.type!='MESH' or obj.hide_render:continue
        materials=[]
        for mat in obj.data.materials:
            node=mat.node_tree.nodes.get('Principled BSDF') if mat and mat.use_nodes else None
            materials.append(dict(name=mat.name,color=list(node.inputs['Base Color'].default_value)if node else list(mat.diffuse_color)))
        rows.append(dict(name=obj.name,properties={key:obj[key]for key in obj.keys()if isinstance(obj[key],(str,int,float,bool))},materials=materials,vertices=len(obj.data.vertices),faces=len(obj.data.polygons)))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'native-context-audit.json').write_text(json.dumps(dict(baselineSha256=SHA,objects=rows),indent=2)+'\n')
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
    print('CONTEXT199_AUDITED',len(rows),flush=True)


# Linear RGB presentation estimates for explicit mapped material/colour roles.
# Multi-valued labels are deliberately skipped: their facade split is unknown.
NAMED={'white':(.72,.73,.71),'grey':(.27,.29,.30),'lightgrey':(.52,.54,.52),
       'silver':(.46,.49,.50),'brown':(.25,.14,.09),'red':(.40,.095,.05),
       'black':(.035,.04,.045),'darkgrey':(.12,.14,.15)}
MATERIALS={'brick':(.285,.125,.075),'stone':(.50,.49,.46),
           'sandstone':(.55,.485,.365),'concrete':(.48,.49,.47)}


def mapped_finish(properties,role):
    import re
    colour=properties.get('building:colour' if role=='wall' else 'roof:colour')
    material=properties.get('building:material' if role=='wall' else 'roof:material','')
    if colour and ';' in colour:return None
    if colour in NAMED:label=colour;rgb=NAMED[colour]
    elif colour and re.fullmatch(r'#[0-9a-fA-F]{6}',colour):
        label=colour[1:].lower()
        srgb=[int(colour[i:i+2],16)/255 for i in (1,3,5)]
        rgb=tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in srgb)
    elif role=='wall' and material in MATERIALS:label=material;rgb=MATERIALS[material]
    else:return None
    brick=role=='wall' and material=='brick'
    return dict(key=role+'_'+label+('_brick' if brick else ''),colour=rgb,brick=brick,role=role)


def create_finish(spec):
    colour=spec['colour'];mat=bpy.data.materials.new('CONTEXT199_'+spec['key']+('_slate' if spec['role']=='roof' else ''))
    mat.use_nodes=True;mat.diffuse_color=(*colour,1)
    node=mat.node_tree.nodes['Principled BSDF'];node.inputs['Base Color'].default_value=(*colour,1)
    node.inputs['Metallic'].default_value=0;node.inputs['Roughness'].default_value=.84 if spec['role']=='roof' else .94
    if spec['brick']:
        tex=mat.node_tree.nodes.new('ShaderNodeTexBrick');uv=mat.node_tree.nodes.new('ShaderNodeTexCoord')
        tex.inputs['Scale'].default_value=1;tex.inputs['Brick Width'].default_value=.225;tex.inputs['Row Height'].default_value=.078
        tex.inputs['Mortar Size'].default_value=.006;tex.inputs['Mortar Smooth'].default_value=.001
        tex.inputs['Color1'].default_value=(*(c*.98 for c in colour),1)
        tex.inputs['Color2'].default_value=(*(c*1.04 for c in colour),1)
        tex.inputs['Mortar'].default_value=(.115,.105,.09,1)
        mat.node_tree.links.new(uv.outputs['UV'],tex.inputs['Vector']);mat.node_tree.links.new(tex.outputs['Color'],node.inputs['Base Color'])
    mat['presentationEstimated']=True
    mat['sourceScope']='Archived mapped material/colour category; optical values and brick courses are estimates, not a current facade survey.'
    return mat


def render_context(scene,path):
    from mathutils import Vector
    camera_data=bpy.data.cameras.new('CONTEXT199_PRIVATE_CAMERA');camera=bpy.data.objects.new(camera_data.name,camera_data)
    scene.collection.objects.link(camera);scene.camera=camera
    camera.location=(260,-300,220);target=Vector((0,-25,15));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.type='ORTHO';camera_data.ortho_scale=440
    scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1100;scene.render.resolution_y=850
    scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera,do_unlink=True);bpy.data.cameras.remove(camera_data)


def build_component():
    import re,sys
    from collections import Counter
    from mathutils import Vector
    sys.path.insert(0,str(ROOT/'web/tools'))
    from integrate_exterior_round194 import object_fingerprint
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    before={obj.name:object_fingerprint(obj)for obj in bpy.data.objects}
    data=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
    records={row['id']:row for row in data['buildings'] if row['code'] is None}
    owner=bpy.data.collections['01_CITY_CONTEXT_estimated_heights'];batches={};sources=[];bindings=[]
    for obj in list(owner.all_objects):
        if obj.type!='MESH' or obj.hide_render:continue
        match=re.fullmatch(r'Context_((?:way|relation)/\d+)_(wall_\d+_\d+|roof)',obj.name)
        if not match:continue
        identifier=match[1];role='wall' if match[2].startswith('wall') else 'roof'
        assert identifier in records and not obj.modifiers and obj.matrix_world.to_3x3().determinant()>0
        record=records[identifier];spec=mapped_finish(record['properties'],role)
        if not spec:continue
        batch=batches.setdefault(spec['key'],dict(spec=spec,vertices=[],faces=[],uv=[],sources=[]))
        points=[obj.matrix_world@v.co for v in obj.data.vertices];offset=len(batch['vertices']);batch['vertices'].extend(points)
        for face in obj.data.polygons:
            batch['faces'].append(tuple(offset+i for i in face.vertices))
            normal=(obj.matrix_world.inverted().transposed().to_3x3()@face.normal).normalized()
            axis=Vector((-normal.y,normal.x,0))
            if axis.length<.001:axis=Vector((1,0,0))
            else:axis.normalize()
            for loop in face.loop_indices:
                point=points[obj.data.loops[loop].vertex_index]
                batch['uv'].append((point.dot(axis),point.z)if role=='wall'else(point.x,point.y))
        batch['sources'].append(obj.name);sources.append(obj.name)
        bindings.append(dict(source=obj.name,sourceId=identifier,sourceAttributes={k:v for k,v in record['properties'].items()if k in ['building:material','building:colour','roof:material','roof:colour']},profile=spec['key']))
    assert batches and len(batches)<=18
    # A small private scene provides matching before/after views without saving
    # another campus model or changing the original world and camera.
    review=bpy.data.scenes.new('CONTEXT199_PRIVATE_REVIEW');review.collection.children.link(owner);bpy.context.window.scene=review
    world=bpy.data.worlds.new(review.name+'_world');world.use_nodes=True;review.world=world
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
    env=world.node_tree.nodes.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(ROOT/'web/public/environment/kloppenheim-daylight-1k.hdr'),check_existing=True)
    world.node_tree.links.new(env.outputs['Color'],world.node_tree.nodes['Background'].inputs['Color'])
    sun_data=bpy.data.lights.new('CONTEXT199_PRIVATE_SUN','SUN');sun_data.energy=1.8;sun_data.angle=.1
    sun=bpy.data.objects.new(sun_data.name,sun_data);review.collection.objects.link(sun);sun.rotation_euler=Vector((-.6,.5,-1)).to_track_quat('-Z','Y').to_euler()
    render_context(review,OUT/'before-whole-context.png')
    added=[]
    for key,batch in batches.items():
        name='CONTEXT199_'+key
        mesh=bpy.data.meshes.new(name+'_mesh');mesh.from_pydata(batch['vertices'],[],batch['faces']);mesh.materials.append(create_finish(batch['spec']));mesh.update()
        uv=mesh.uv_layers.new(name='MetricUV')
        for corner,coordinate in zip(uv.data,batch['uv']):corner.uv=coordinate
        obj=bpy.data.objects.new(name,mesh);owner.objects.link(obj);obj['presentationEstimated']=True;obj['sourceObjectCount']=len(batch['sources']);added.append(name)
    for name in sources:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
    assert all(object_fingerprint(bpy.data.objects[name])==signature for name,signature in before.items())
    render_context(review,OUT/'after-whole-context.png')
    bpy.data.objects.remove(sun,do_unlink=True);bpy.data.lights.remove(sun_data);bpy.data.scenes.remove(review);bpy.data.worlds.remove(world)
    bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    component=OUT/'context-palette199-component.blend';bpy.data.libraries.write(str(component),{bpy.data.objects[name]for name in added},fake_user=True,compress=True)
    report=dict(version=199,baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),
                targetCollection=owner.name,addedObjects=added,archivedObjects=sources,changedObjects=[],bindings=bindings,buildings=len({row['sourceId']for row in bindings}),profiles=len(batches),
                sourceGeometrySha256=hashlib.sha256((ROOT/'result/blender/site_geometry.json').read_bytes()).hexdigest(),originalsVerified=len(before),
                scope='Only existing non-LSE context faces with singular mapped material/colour attributes; world geometry retained and like finishes batched. No facade openings or details invented.',
                limitations='Mapped attributes were archived2026-09-12, not current photographs. Numeric colours, reflectance and standard brick coursing are presentation estimates. Mixed labels, untagged faces and unconfirmed copper/tile colours retained.')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(added)
    for obj in dst.objects:
        bpy.context.scene.collection.objects.link(obj);assert obj.data.uv_layers and len(obj.data.materials)==1
    expected=Counter(tuple(tuple(round(v,6)for v in point)for point in (batch['vertices'][i]for i in face))for batch in batches.values()for face in batch['faces'])
    actual=Counter(tuple(tuple(round(v,6)for v in obj.data.vertices[i].co)for i in face.vertices)for obj in dst.objects for face in obj.data.polygons)
    assert actual==expected,'Reopened context geometry changed'
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
    report['verification']=dict(componentReopened=True,sourceWorldFacesPreserved=True,originalGeometryUVsAndBindingsPreserved=True,baselineSha256Unchanged=True)
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('CONTEXT199_COMPONENT',len(sources),len(added),report['buildings'],flush=True)


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    build_component()
