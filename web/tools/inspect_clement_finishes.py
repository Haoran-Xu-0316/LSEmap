"""Read current Clement House exterior material assignments."""
from pathlib import Path
import json,bpy
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v38.blend'))
rows=[]
for o in bpy.data.collections['CLM_EXTERIOR'].all_objects:
 if o.type!='MESH':continue
 rows.append({'name':o.name,'materials':[{'name':m.name,'colour':list(m.diffuse_color),'roughness':m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value if m.use_nodes else None} for m in o.data.materials if m]})
(ROOT/'result/blender/stage39/material-inventory.json').write_text(json.dumps(rows,indent=2)+'\n')
print('CLM_INVENTORY',len(rows))
