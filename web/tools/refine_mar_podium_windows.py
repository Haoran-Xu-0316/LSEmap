"""Correct MAR's three north podium windows from Nick Kane built photographs.
Run in Blender Text Editor. Dimensions retained; optical finish is an estimate.
"""
from pathlib import Path
import array, hashlib, json, math, shutil, sys
import bpy, bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'result/blender/stage104'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v103.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
collection=bpy.data.collections['MAR_EXTERIOR']
surface=next(s for s in json.loads((ROOT/'result/blender/stage02/detail_geometry.json').read_text())['surfaces'] if s['name']=='MAR_north_podium')
p,q=[Vector((*surface[k],0)) for k in ['p','q']]; u=(q-p).normalized(); n=Vector((-u.y,u.x,0))
assert n.y>0
windows=[w for w in surface['openings'] if w[2]-w[0]<4]
assert len(windows)==3

def fingerprint(obj):
 h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
 return h.hexdigest()
before={o.name:fingerprint(o) for o in bpy.data.objects}
copies=[]
def owned_copy(name,target_collection=None):
 source=bpy.data.objects[name]; assert not source.hide_render
 copy=source.copy();copy.data=source.data.copy();copy.name='MAR_V104_'+name.removeprefix('MAR_')
 (target_collection or collection).objects.link(copy);source.hide_render=True;source.hide_set(True)
 copies.append({'source':name,'copy':copy.name});return source,copy

def local(point):
 d=point-p;return (d.dot(u),d.dot(n),point.z)
def inside(points):
 coords=[local(point) for point in points]
 return any(all(a-.13<=x<=c+.13 and b-.13<=z<=d+.13 and -.4<=depth<=-.05 for x,depth,z in coords) for a,b,c,d in windows)
source,copy=owned_copy('MAR_window_frames')
bm=bmesh.new();bm.from_mesh(copy.data);seen=set();removed=[];indices=[]
for vertex in bm.verts:
 if vertex in seen:continue
 stack=[vertex];seen.add(vertex);component=[]
 while stack:
  v=stack.pop();component.append(v)
  for edge in v.link_edges:
   other=edge.other_vert(v)
   if other not in seen:seen.add(other);stack.append(other)
 if inside([copy.matrix_world@v.co for v in component]):
  indices.extend(v.index for v in component);removed.append(component)
assert len(removed)==sum(round((c-a)/1.2)+4 for a,b,c,d in windows),len(removed)
bmesh.ops.delete(bm,geom=[v for component in removed for v in component],context='VERTS')
bm.to_mesh(copy.data);bm.free();copy.data.update()
copies[-1]['removedVertexIndices']=indices
source,glass=owned_copy('MAR_recessed_window_glass')
material=source.data.materials[0].copy();material.name='MAR_V104_podium_glass'
material.diffuse_color=(.13,.19,.23,1)
shader=next(node for node in material.node_tree.nodes if node.type=='BSDF_PRINCIPLED')
shader.inputs['Base Color'].default_value=material.diffuse_color
shader.inputs['Roughness'].default_value=.15
shader.inputs['Metallic'].default_value=.18
shader.inputs['Transmission Weight'].default_value=0
material['webOpacity']=1.0
glass.data.materials.append(material);pane_indices=[]
for poly in glass.data.polygons:
 if inside([glass.matrix_world@glass.data.vertices[i].co for i in poly.vertices]):
  poly.material_index=len(glass.data.materials)-1;pane_indices.append(poly.index)
assert len(pane_indices)==3,pane_indices
materials.clear();materials['frame']=bpy.data.objects['MAR_window_frames'].data.materials[0]
geometry=Geometry('MAR','podium104_joinery','frame')
angle=math.atan2(u.y,u.x)
def point(x,z):return p+u*x+n*(-.18)+Vector((0,0,z))
for a,b,c,d in windows:
 # The photographed tall windows have one clear glass column and two panes.
 for x in [a,c]:geometry.box(point(x,(b+d)/2),(.052,.09,d-b),angle)
 for z in [b,(b+d)/2,d]:geometry.box(point((a+c)/2,z),(c-a+.10,.10,.065 if z in [b,d] else .09),angle)
joinery=geometry.finish()
for modifier in list(joinery.modifiers):joinery.modifiers.remove(modifier)
# Remove obsolete rear-wing sill and trim pieces that cross the north openings.
# Boolean cutters follow the retained apertures and leave closed construction edges.
overlap_names=['MAR_window_sills','MAR_D5_V16_metal_sill_channel','MAR_D5_V17_sill_front_fascia','MAR_D3_mezzanine_slab_with_stair_aperture']
cutters=[]
for a,b,c,d in windows:
 bpy.ops.mesh.primitive_cube_add(size=1)
 cutter=bpy.context.object;cutter.name='MAR_TEMP_aperture_cutter'
 cutter.rotation_euler.z=angle
 cutter.location=p+u*((a+c)/2)+n*(-.1)+Vector((0,0,(b+d)/2))
 cutter.scale=(c-a-.04,1.6,d-b-.08)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 cutters.append(cutter)
overlap_records=[]
for name in overlap_names:
 source,trim=owned_copy(name,bpy.data.collections['MAR_PUBLIC_INTERIOR_study'] if 'mezzanine_slab' in name else collection)
 original_vertices=len(trim.data.vertices)
 for modifier in list(trim.modifiers):trim.modifiers.remove(modifier)
 for cutter in cutters:
  bpy.context.view_layer.objects.active=trim
  modifier=trim.modifiers.new('Retained podium aperture','BOOLEAN')
  modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=cutter
  bpy.ops.object.modifier_apply(modifier=modifier.name)
 if 'mezzanine_slab' in name:
  # The same legacy slab also projected through solid facade panels.
  bpy.ops.mesh.primitive_cube_add(size=1)
  front=bpy.context.object;front.rotation_euler.z=angle
  front.location=p+u*27+n*.25+Vector((0,0,7.1))
  front.scale=(54.4,1.1,1.0)
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  bpy.context.view_layer.objects.active=trim
  modifier=trim.modifiers.new('Slab edge behind north facade','BOOLEAN')
  modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=front
  bpy.ops.object.modifier_apply(modifier=modifier.name)
  bpy.data.objects.remove(front,do_unlink=True)
 overlap_records.append({'object':trim.name,'previousVertices':original_vertices,'retainedVertices':len(trim.data.vertices)})
for cutter in cutters:bpy.data.objects.remove(cutter,do_unlink=True)
assert all(fingerprint(bpy.data.objects[name])==digest for name,digest in before.items())
for filename in ['room-studies.json','room-spaces.json','building-review.json']:
 shutil.copyfile(ROOT/'result/blender/stage103'/filename,OUT/filename)
if not (OUT/'catalogue-before.json').exists():shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
assert json.loads((OUT/'catalogue-before.json').read_text())['version']=='103'
audit={'version':104,'baseline':103,'originalFingerprints':before,'copies':copies,'addedObjects':[joinery.name],
 'overlapCorrections':overlap_records,'surface':surface,'windows':windows,'removedFrames':len(removed),'newRails':15,'paneIndices':pane_indices,
 'referenceUrl':'https://nickkane.co.uk/portfolio_page/marshall-building-lse-london-grafton-architects/',
 'referenceImages':['architecture_round5_MAR_mar_kane_02.jpg','architecture_round5_MAR_mar_kane_03.jpg'],
 'limits':['Photo upload paths date to 2022; exact capture date unknown','Existing openings and heights retained; fine dimensions and glass finish estimated','Academic wings, upper screens, whole roof and full interior structure still require further review']}
(OUT/'mar-podium-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v104.blend'))
print('MAR_PODIUM_SAVED',len(removed),len(pane_indices),flush=True)
