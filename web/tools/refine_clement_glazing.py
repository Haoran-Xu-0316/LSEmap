"""Reduce the unsupported cyan cast in Clement House exterior glazing.

Run in Blender's Text Editor. The neutral grey tint is a photographic estimate,
not a measured optical property. Existing bronze frames and stone stay intact.
"""
from pathlib import Path
import array,hashlib,json
import bpy
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage39'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v38.blend'))

def geometry_hash(obj):
 h=hashlib.sha256(array.array('f',[v for p in obj.data.vertices for v in p.co]).tobytes())
 h.update(array.array('i',[v.vertex_index for v in obj.data.loops]).tobytes())
 return h.hexdigest()

before={o.name:geometry_hash(o) for o in bpy.data.objects if o.type=='MESH'}
assignments={o.name:[m.name if m else None for m in o.data.materials] for o in bpy.data.objects if o.type=='MESH'}
obj=bpy.data.objects['CLM_D3_window_glass']
assert len(obj.data.materials)==1
old=obj.data.materials[0]
original_colour=list(old.diffuse_color)
new=old.copy();new.name='CLM_V39_neutral_recessed_glass'
new.diffuse_color=(.075,.085,.088,1)
node=new.node_tree.nodes.get('Principled BSDF')
assert node is not None
node.inputs['Base Color'].default_value=new.diffuse_color
# Roughness, opacity and optical treatment remain unchanged: isolate tint only.
obj.data.materials[0]=new
assert all(geometry_hash(o)==before[o.name] for o in bpy.data.objects if o.type=='MESH')
assert all([m.name if m else None for m in o.data.materials]==assignments[o.name]
           for o in bpy.data.objects if o.type=='MESH' and o!=obj)
assert list(old.diffuse_color)==original_colour
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'clement-glazing-candidate.blend'))
(OUT/'glazing-audit.json').write_text(json.dumps({
 'baseline':'result/blender/LSE_campus_detailed_v38.blend','candidate':'result/blender/stage39/clement-glazing-candidate.blend',
 'object':obj.name,'oldColourLinear':original_colour,'newColourLinear':list(new.diffuse_color),
 'unchangedMeshCount':len(before),'unchanged':'Geometry, stone, bronze frames, roofs, interiors, and all other buildings',
 'references':[{'url':'https://historicengland.org.uk/listing/the-list/list-entry/1066494','supports':'Portland stone, bronze frames, slate roof'},
 {'path':'data/collections/exteriors/images/lse_estate_003.jpg','supports':'Muted window appearance in archived daylight portal photograph; not calibrated colour'},
 {'url':'https://www.westminster.gov.uk/media/document/all---18-august-2024','page':111,'application':'24/03808/FULL and 24/03809/LBC','supports':'Rooftop AC and ductwork consent; does not prove completed installation'}],
 'limitations':['Tint is a visual estimate; real reflections vary with light and viewpoint','Roof equipment, rear elevations and sculpture remain incomplete'],
 'publication':'Native candidate only; production-render comparison pending'
},ensure_ascii=False,indent=2)+'\n')
print('CLM_GLAZING_REFINED',len(before),'mesh geometries unchanged; one isolated material copy')
