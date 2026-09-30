"""Read-only verification of the saved chamfered Aldwych pavilion."""
from pathlib import Path
import bpy,json
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v63.blend'));p=ROOT/'result/blender/stage63/aldwych-pavilion-audit.json';a=json.loads(p.read_text())
roof=bpy.data.objects['61A_D5_pavilion63_hip_roof'];pts=[roof.matrix_world@v.co for v in roof.data.vertices];assert len(roof.data.polygons)==8 and all(f.normal.z>0 for f in roof.data.polygons)
assert abs(min(v.z for v in pts)-35.35)<.0001 and abs(max(v.z for v in pts)-37.7)<.0001
lower=bpy.data.objects['61A_D5_pavilion63_lower_glass_glass'];upper=bpy.data.objects['61A_D5_pavilion63_clerestory_glass_glass'];assert len(lower.data.vertices)//8==8 and len(upper.data.vertices)//8==8
assert all(bpy.data.objects[n].hide_render for n in a['hiddenObjects']);assert a['changedExistingGeometry']==[]
a['savedMeasurements']={'roofFaces':8,'upwardRoofFaces':8,'eave':min(v.z for v in pts),'peak':max(v.z for v in pts),'lowerWindows':len(lower.data.vertices)//8,'clerestoryFaces':len(upper.data.vertices)//8};p.write_text(json.dumps(a,indent=2)+'\n');print('SAVED_ALDWYCH_PAVILION_VERIFIED')
