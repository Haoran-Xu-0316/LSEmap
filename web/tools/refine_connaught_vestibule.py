"""Restore the photographed open CON portal and recessed warm vestibule.
Run in Blender Text Editor. Hall depth and fixture dimensions are estimates.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/stage68'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v67.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
record=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='CON')
ring=record['rings'][0]
p,q=Vector((*ring[4],0)),Vector((*ring[5],0))
u=(q-p).normalized()
signed=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))
n=Vector((u.y,-u.x,0))*(1 if signed>0 else -1)
origin=p+u*((q-p).length/5*2.5)
angle=math.atan2(u.y,u.x)
def point(x,d,z):return origin+u*x+n*d+Vector((0,0,z))
def digest(obj):
 h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[loop.vertex_index for loop in obj.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
 return h.hexdigest()
before={o.name:digest(o) for o in bpy.data.objects}
hidden=['CON_D4_entrance_pocket','CON_D4_portal_piers','CON_D4_vestibule_glass',
        'CON_D4_vestibule_door_frames','CON_D4_door_pull_handles','CON_D4_entrance_steps',
        'CON_V19_HIST_vestibule_light_backplate_bronze','CON_V19_HIST_vestibule_light_diffuser_cream']
for name in hidden:
 obj=bpy.data.objects[name];obj.hide_render=True;obj.hide_set(True)
materials.clear()
for key,color,rough,metal in [
 ('granite',(.43,.425,.40),.74,0),('stone',(.62,.595,.53),.82,0),
 ('wall',(.62,.565,.39),.81,0),('floor',(.25,.255,.24),.80,0),
 ('bronze',(.105,.078,.050),.39,.45),('glass',(.13,.18,.18),.20,.10),
 ('light',(.87,.77,.50),.50,0),('tactile',(.57,.57,.54),.84,0)]:
 mat=bpy.data.materials.new('CON_V68_'+key);mat.use_nodes=True;mat.diffuse_color=(*color,1)
 shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color
 shader.inputs['Roughness'].default_value=rough;shader.inputs['Metallic'].default_value=metal
 if key=='glass':shader.inputs['Transmission Weight'].default_value=.20;mat['webOpacity']=.18
 if key=='light':shader.inputs['Emission Color'].default_value=(*color,1);shader.inputs['Emission Strength'].default_value=.65
 if key=='granite':
  nodes,links=mat.node_tree.nodes,mat.node_tree.links
  coord=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=85
  ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.37,.365,.34,1);ramp.color_ramp.elements[1].color=(.47,.465,.43,1)
  links.new(coord.outputs['UV'],noise.inputs['Vector']);links.new(noise.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs['Color'],shader.inputs['Base Color'])
 materials[key]=mat
batches={}
def batch(key):
 if key not in batches:batches[key]=Geometry('CON','vestibule68_'+key,key)
 return batches[key]
def box(key,x,d,z,w,t,h):batch(key).box(point(x,d,z),(w,t,h),angle)
# Match the photographed two-part casing; retain the existing upper cornice.
for side in [-1,1]:
 box('granite',side*1.225,-.01,1.56,.50,1.02,3.12)
 box('stone',side*1.225,-.01,3.68,.50,1.02,1.12)
# The street portal remains open. The inner door is beyond a short lit passage.
for side in [-1,1]:box('wall',side*1.045,-1.59,1.56,.14,2.60,2.92)
box('floor',0,-1.48,.04,2.10,3.46,.12)
box('wall',0,-1.58,3.03,2.10,2.65,.12)
# Inner door glazing and framing at the estimated 2.75m setback.
for side in [-1,1]:
 box('glass',side*.455,-2.78,1.48,.85,.045,2.67)
for x in [-.95,0,.95]:box('bronze',x,-2.71,1.48,.055,.10,2.78)
for z in [.10,2.87]:box('bronze',0,-2.71,z,1.95,.10,.065)
for x in [-.115,.115]:box('bronze',x,-2.61,1.38,.025,.07,.43)
# A shallow interior backing gives translucent glazing a restrained warm depth.
box('wall',0,-3.11,1.49,2.05,.09,2.80)
box('floor',0,-2.98,.11,2.02,.28,.04)
# The single visible left wall light; no invented furniture or route behind it.
box('bronze',.952,-.98,1.90,.09,.21,.48)
box('light',.897,-.98,1.90,.025,.15,.35)
# Fine threshold and the tactile paving visible in the archive photograph.
box('floor',0,.27,.065,1.98,.22,.13)
box('tactile',0,.69,.012,1.54,.46,.024)
for i in range(15):box('tactile',-.70+i*.10,.69,.028,.020,.36,.018)
# Bronze belongs to the fanlight frame too; only this dedicated slot changes.
fanlight=bpy.data.objects['CON_D4_bronze_fanlight']
fanlight.data.materials[0]=materials['bronze']
added=[]
for geometry in batches.values():
 obj=geometry.finish();added.append(obj.name)
 for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
changed=[name for name,prior in before.items() if digest(bpy.data.objects[name])!=prior]
assert changed==['CON_D4_bronze_fanlight'],changed
for filename in ['room-studies.json','room-spaces.json','building-review.json']:
 (OUT/filename).write_bytes((ROOT/'result/blender/stage67'/filename).read_bytes())
a={'version':68,'baseline':67,'changedExistingObjects':changed,'changedOtherObjects':[],
   'hiddenPreviousObjects':hidden,'addedObjects':added,'origin':list(origin),'right':list(u),'outward':list(n),
   'innerDoorDepth':-2.78,'clearHallWidth':1.95,'reference':'data/建筑图片/CON_Connaught House/01_建筑实拍/exteriors_lse_estate_005.jpg',
   'limitations':['Undated estate photo; not a 2026 site survey','Hall depth, heights, materials and lighting are photo-guided estimates',
                  'Crest retained as a simplified reserve; upper elevations, roof and complete interior unverified']}
(OUT/'connaught-vestibule-audit.json').write_text(json.dumps(a,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v68.blend'))
print('CONNAUGHT_VESTIBULE_SAVED',len(added))
