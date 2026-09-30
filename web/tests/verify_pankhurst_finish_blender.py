"""Read-only inspection of the saved PAN/FAW native window heads."""
from pathlib import Path
import bpy,json
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v58.blend'))
path=ROOT/'result/blender/stage58/pankhurst-finish-audit.json';audit=json.loads(path.read_text());measurements={}
for code in ['PAN','FAW']:
 obj=bpy.data.objects[code+'_D3_window_heads_and_sills'];verts=list(obj.data.vertices)
 heights=[max(v.co.z for v in verts[i:i+8])-min(v.co.z for v in verts[i:i+8]) for i in range(0,len(verts),8)]
 assert heights and all(abs(height-.11)<.00002 for height in heights)
 measurements[code]={'count':len(heights),'minimum':min(heights),'maximum':max(heights)}
audit['savedHeadMeasurements']=measurements;path.write_text(json.dumps(audit,indent=2)+'\n');print('SAVED_HEADS_VERIFIED',measurements)
