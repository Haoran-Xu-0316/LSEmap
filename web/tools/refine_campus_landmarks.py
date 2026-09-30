"""Refine the inverted globe and model the user-photographed MAR letters.
Run in Blender's Text Editor. Reference photos remain private local evidence.
"""
from pathlib import Path
import bpy, json, math, hashlib, array
from mathutils import Matrix, Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage48';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v47.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
old=list(bpy.data.objects)
def fingerprint(obj):
 h=hashlib.sha256(str([list(r)for r in obj.matrix_world]).encode())
 if obj.type=='MESH':h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
 return h.hexdigest()
before={o.name:fingerprint(o)for o in old}
globe=bpy.data.objects['SITE_V45_The_World_Turned_Upside_Down']
material=globe.data.materials[0]
node=next(n for n in material.node_tree.nodes if n.type=='TEX_IMAGE')
node.image=bpy.data.images.load(str(OUT/'globe-map.png'),check_existing=False);node.image.pack()
shader=material.node_tree.nodes['Principled BSDF'];shader.inputs['Roughness'].default_value=.47
shader.inputs['Coat Weight'].default_value=.10;shader.inputs['Coat Roughness'].default_value=.42
material['globeMap']=True
# The photograph establishes red faces and deep white sides. Dimensions and
# the north-forecourt registration are estimates, not a surveyed position.
center=json.loads((ROOT/'result/blender/stage02/detail_geometry.json').read_text())['mar_center']
a=math.radians(22);right=Vector((math.cos(a),math.sin(a),0));outward=Vector((-math.sin(a),math.cos(a),0))
origin=Vector((center[0],center[1],.05))+right*(-24.0)+outward*24.8
rotation=Matrix((right,Vector((0,0,1)),outward)).transposed().to_euler()
collection=bpy.data.collections['MAR_EXTERIOR']
def mat(name,color):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=.55
 return m
white=mat('MAR_V48_LSE_white_sides',(.86,.86,.83));red=mat('MAR_V48_LSE_red_face',(.47,.008,.016))
added=[]
profiles=json.loads((ROOT/'web/tools/lse-letter-profiles.json').read_text())['letters']
for letter,outline in profiles.items():
 for face,lo,hi,finish in [('body',-.19,.19,white),('face',.191,.201,red)]:
  points=[origin-right*x+Vector((0,0,z))+outward*d for d in [lo,hi] for x,z in outline]
  n=len(outline);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)]
  name=f'MAR_V48_LSE_{letter}_{face}';mesh=bpy.data.meshes.new(name);mesh.from_pydata(points,[],[tuple(reversed(f))for f in faces]);mesh.materials.append(finish);mesh.update()
  obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
  obj['scope']='LSE brand outline with photographed sculpture LS connection; dimensions and placement estimated';added.append(name)
# Five fine concentric inlays are visible in the supplied Sheffield Street view.
inlay=mat('SITE_V48_globe_paving_inlay',(.19,.205,.20))
vertices=[];faces=[];segments=192
for radius in [3.02,3.12,3.22,3.32,3.42]:
 offset=len(vertices)
 for r in [radius-.012,radius+.012]:
  vertices.extend((globe.location.x+r*math.cos(i*math.tau/segments),globe.location.y+r*math.sin(i*math.tau/segments),.052)for i in range(segments))
 faces.extend((offset+i+segments,offset+(i+1)%segments+segments,offset+(i+1)%segments,offset+i)for i in range(segments))
mesh=bpy.data.meshes.new('SITE_V48_globe_concentric_inlays');mesh.from_pydata(vertices,[],faces);mesh.materials.append(inlay);mesh.update()
obj=bpy.data.objects.new(mesh.name,mesh);bpy.data.collections['00_SITE'].objects.link(obj);added.append(obj.name)
for layer in bpy.context.scene.view_layers:layer.update()
changed=[o.name for o in old if fingerprint(o)!=before[o.name]];assert changed==[],changed
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v48.blend'))
for name in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/name).write_bytes((ROOT/'result/blender/stage47'/name).read_bytes())
payload={'version':48,'baseline':47,'addedObjects':added,'changedExistingGeometry':changed,'globeTextureSha256':hashlib.sha256((OUT/'globe-map.png').read_bytes()).hexdigest(),'signOrigin':list(origin),'signOutward':list(outward),'limitations':['MAR letter depth and proportions and north forecourt placement estimated from the supplied close-up','Country labels compensate globe inversion; map colors and boundaries remain reconstructed cartography']}
(OUT/'landmark-audit.json').write_text(json.dumps(payload,indent=2)+'\n')
print('LANDMARKS_SAVED',list(origin))
