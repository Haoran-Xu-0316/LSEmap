"""Photo-supported Cowdray brick, stone and slate surface review, fixed configuration."""
from pathlib import Path
import hashlib,json,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/cow-exterior217'
BASE=ROOT/'result/blender/LSE_campus_detailed_v216.blend'
SHA='12376d6365bbc57fa9eec97617453dbbfcf9235a8200bb90726f80c2147c1a60'
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints
from refine_portsmouth_exterior207 import material_fingerprint,uv_sha

def load():
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE))
 bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 for scene in bpy.data.scenes:
  for layer in scene.view_layers:layer.update()
 expected=accepted_fingerprints(ROOT/'result/blender/stage216',SHA)
 actual={o.name:object_fingerprint(o)for o in bpy.data.objects}
 assert actual==expected,[n for n in actual if actual[n]!=expected.get(n)][:20]
 return actual

def inspect():
 originals=load();objects=[];materials={}
 for o in bpy.data.collections['COW_EXTERIOR'].all_objects:
  if o.type!='MESH'or o.hide_render:continue
  objects.append(dict(name=o.name,materials=[m.name if m else None for m in o.data.materials],bounds=[[min((o.matrix_world@v.co)[i]for v in o.data.vertices),max((o.matrix_world@v.co)[i]for v in o.data.vertices)]for i in range(3)],uvLayers=[dict(name=u.name,first=[list(d.uv)for d in list(u.data)[:8]])for u in o.data.uv_layers]))
  for m in o.data.materials:
   if not m or m.name in materials:continue
   p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
   materials[m.name]=dict(properties=dict(m.items()),diffuse=list(m.diffuse_color),inputs={s.name:(list(s.default_value)if hasattr(s.default_value,'__len__')else s.default_value)for s in p.inputs if hasattr(s,'default_value')},nodes=[dict(name=n.name,type=n.type)for n in m.node_tree.nodes],links=[(l.from_node.name,l.to_node.name,l.to_socket.name)for l in m.node_tree.links])
 (OUT/'inspection.json').write_text(json.dumps(dict(originalsVerified=len(originals),objects=objects,materials=materials),indent=2)+'\n')
 print('COW217_INSPECT',len(originals),len(objects),len(materials),flush=True)


def render(label):
 scene=bpy.data.scenes.new('COW217_REVIEW_'+label)
 scene.collection.children.link(bpy.data.collections['COW_EXTERIOR']);bpy.context.window.scene=scene
 world=bpy.data.worlds.new('COW217_WORLD_'+label);world.use_nodes=True
 world.node_tree.nodes['Background'].inputs[0].default_value=(.68,.74,.8,1)
 world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
 sun=bpy.data.objects.new('COW217_SUN',bpy.data.lights.new('COW217_SUN','SUN'));scene.collection.objects.link(sun)
 sun.data.energy=2;sun.data.angle=.22;sun.rotation_euler=(.4,-.5,-.1)
 camera=bpy.data.objects.new('COW217_CAMERA',bpy.data.cameras.new('COW217_CAMERA'));scene.collection.objects.link(camera);scene.camera=camera
 camera.data.type='ORTHO';camera.data.clip_end=500
 scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
 scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
 scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
 cameras=[]
 for name,target,position,scale in [('whole',(10,-3,10),(-39,-47,36),46),('entrance',(-5.4,-5,6),(-29,-31,12),15)]:
  camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
  scene.render.filepath=str(OUT/(label+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
  cameras.append(dict(name=name,target=target,position=position,scale=scale))
 bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 for o in [sun,camera]:bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.scenes.remove(scene)
 return cameras

def finish_material(source):
 name=source.name.lower()
 if 'brick'in name:return 'brick'
 if 'slate'in name:return 'slate'
 if 'lead'in name:return 'lead'
 if 'glass'in name:return 'glass'
 if 'frame'in name or 'finish'in name:return 'paint'
 if 'stone'in name:return 'stone'
 if 'trim'in name:return 'trim'
 return None

def make_material(source,role):
 m=source.copy();m.name='COW217_'+source.name
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 colors={'brick':(.34,.155,.096,1),'stone':(.56,.54,.485,1),'trim':(.67,.65,.60,1),'paint':(.79,.79,.745,1),'slate':(.055,.064,.072,1),'lead':(.29,.31,.315,1),'glass':(.09,.12,.13,1)}
 m.diffuse_color=colors[role];p.inputs['Base Color'].default_value=colors[role]
 p.inputs['Roughness'].default_value={'brick':.87,'stone':.83,'trim':.78,'paint':.46,'slate':.86,'lead':.69,'glass':.19}[role]
 if role!='lead':p.inputs['Metallic'].default_value=0
 m['surfacePolicy']='Cowdray photographic material separation; authored estimate, not measured albedo.'
 if role=='brick':
  b=next(n for n in m.node_tree.nodes if n.type=='TEX_BRICK')
  b.inputs['Color1'].default_value=(.39,.20,.135,1);b.inputs['Color2'].default_value=(.29,.118,.073,1)
  b.inputs['Mortar'].default_value=(.30,.27,.22,1)
  # Preserve original metric brick pitch and offset. Only soften chroma and relief.
  bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.0009;bump.inputs['Strength'].default_value=1
  m.node_tree.links.new(b.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
 elif role in ['stone','trim','slate']:
  uv=m.node_tree.nodes.new('ShaderNodeTexCoord');noise=m.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3 if role!='slate'else 2
  ramp=m.node_tree.nodes.new('ShaderNodeValToRGB')
  for element,factor in zip(ramp.color_ramp.elements,[.965,1.035]):element.color=tuple(v*factor for v in colors[role][:3])+(1,)
  m.node_tree.links.new(uv.outputs['UV'],noise.inputs['Vector']);m.node_tree.links.new(noise.outputs['Fac'],ramp.inputs['Fac']);m.node_tree.links.new(ramp.outputs['Color'],p.inputs['Base Color'])
 if role=='glass':m['webSurfaceRole']='glazing'
 return m

def run():
 OUT.mkdir(exist_ok=True);originals=load()
 materials={m.name:material_fingerprint(m)for m in bpy.data.materials}
 visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
 candidates=[o for o in bpy.data.collections['COW_EXTERIOR'].all_objects if o.type=='MESH'and not o.hide_render and any(finish_material(m)for m in o.data.materials if m)]
 cameras=render('before');copies={};owned=[];changes=[]
 for source in candidates:
  o=source.copy();o.data=source.data.copy();o.name='COW217_'+source.name;o.data.name=o.name+'_mesh'
  bpy.data.collections['COW_EXTERIOR'].objects.link(o);o['originalObject']=source.name;o['webGeometrySource']=source.name;o['destinationCollection']='COW_EXTERIOR'
  for i,m in enumerate(source.data.materials):
   role=finish_material(m)if m else None
   if not role:continue
   if m.name not in copies:copies[m.name]=make_material(m,role)
   o.data.materials[i]=copies[m.name]
  source.hide_render=True;source.hide_set(True);o.hide_render=False;o.hide_set(False)
  assert uv_sha(o)==uv_sha(source)
  owned.append(o);changes.append(dict(source=source.name,owned=o.name,uvSha256=uv_sha(o),vertices=len(o.data.vertices),polygons=len(o.data.polygons),materials=[m.name for m in o.data.materials]))
 assert all(object_fingerprint(bpy.data.objects[n])==fp for n,fp in originals.items())
 assert all(material_fingerprint(bpy.data.materials[n])==fp for n,fp in materials.items())
 render('after')
 state={o.name:object_fingerprint(o)for o in owned};component=OUT/'component.blend'
 bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
 source_parameters={}
 for name,m in copies.items():
  old=bpy.data.materials[name];p=next(n for n in old.node_tree.nodes if n.type=='BSDF_PRINCIPLED');q=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  source_parameters[name]=dict(replacement=m.name,role=finish_material(old),oldDiffuse=list(old.diffuse_color),newDiffuse=list(m.diffuse_color),oldRoughness=p.inputs['Roughness'].default_value,newRoughness=q.inputs['Roughness'].default_value)
  if finish_material(old)=='brick':
   b=next(n for n in old.node_tree.nodes if n.type=='TEX_BRICK');c=next(n for n in m.node_tree.nodes if n.type=='TEX_BRICK')
   source_parameters[name]['brick']={s:dict(before=list(b.inputs[s].default_value)if s in ['Color1','Color2','Mortar']else b.inputs[s].default_value,after=list(c.inputs[s].default_value)if s in ['Color1','Color2','Mortar']else c.inputs[s].default_value)for s in ['Scale','Brick Width','Row Height','Mortar Size','Color1','Color2','Mortar']}
 audit=dict(baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),addedObjects=[o.name for o in owned],archivedObjects=[c['source']for c in changes],destinationCollection='COW_EXTERIOR',retainNewMaterials=True,replacementMaterialBindings={o.name:[m.name for m in o.data.materials]for o in owned},changes=changes,materialParameters=source_parameters,cameras=cameras,sourceReferences=[dict(local='data/collections/campus_photos_round2/images/COW/COW_cow_russell_05.jpg',url='https://www.russellcawberry.com/files/projects/Cowdray%2520House/056_cowdray_house_MR.jpg',date='Project2019; image date unknown',evidence='Red-brown brick, pale gray stone, white painted window joinery and blue-gray slate; relative material relationships, not measured color.'),dict(local='data/建筑图片/COW_Cowdray House/01_建筑实拍/exteriors_lse_estate_006.jpg',url='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/Cowdray-web.jpg',date='Undated archival LSE estate photo',evidence='Same brick/stone/paint separation.')],improvement='Reduce orange-red brick chroma, distinguish pale gray limestone from white painted sashes, add shallow mortar relief, soften neutral glass tint and preserve separate slate/lead finishes.',limitations=['Material colors are photographic estimates under unknown illumination, not measured albedo or confirmed2026 refurbishment.','No geometry or UV changes;177 dormer roofs/normals and118 portal retained.','Glass remains opaque; no verified near backing supports making it transparent.','Low-amplitude procedural noise approximates stone/slate finish, not surveyed ageing or tile dimensions.'])
 for ref in audit['sourceReferences']:ref['sha256']=hashlib.sha256((ROOT/ref['local']).read_bytes()).hexdigest()
 (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 bpy.ops.wm.read_factory_settings(use_empty=True)
 with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(state)
 assert {o.name:object_fingerprint(o)for o in dst.objects}==state
 (OUT/'verification.json').write_text(json.dumps(dict(sourceSha256=hashlib.sha256(BASE.read_bytes()).hexdigest(),acceptedOriginalsVerified=len(originals),originalGeometryUvMaterialBindingsPreserved=True,originalMaterialNodesVerified=len(materials),replacementGeometryAndUvRetained=True,reopenedComponentVerified=True,componentSha256=audit['componentSha256'],addedObjects=len(state),addedGeometryTriangles=0,parameters=source_parameters),indent=2)+'\n')
 print('COW217_VERIFIED',len(owned),audit['componentSha256'],flush=True)
if __name__=='__main__':run()
