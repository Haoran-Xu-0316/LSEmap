"""Read-only verification of saved Lakatos sash bars and material ownership."""
from pathlib import Path
import bpy,json
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v59.blend'))
path=ROOT/'result/blender/stage59/lakatos-sash-audit.json';audit=json.loads(path.read_text())
profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text())if p['code']=='LAK')
obj=bpy.data.objects['LAK_D5_sash59_vertical_bar_frame'];verts=list(obj.data.vertices);centres=[sum((obj.matrix_world@v.co for v in verts[i:i+8]),Vector())/8 for i in range(0,len(verts),8)]
horizontal=bpy.data.objects['LAK_D5_sash59_horizontal_bar_frame'];hverts=list(horizontal.data.vertices);hcentres=[sum((horizontal.matrix_world@v.co for v in hverts[i:i+8]),Vector())/8 for i in range(0,len(hverts),8)];measured=[]
for window in audit['sashWindows']:
 wall=profile['walls'][window['wall']];p=Vector((*wall['p'],0));u=Vector(((wall['q'][0]-wall['p'][0])/wall['length'],(wall['q'][1]-wall['p'][1])/wall['length'],0));n=Vector((*wall['outward'],0));z=(window['low']+window['high'])/2
 bars=[((c-p).dot(u)-window['x'])/window['width'] for c in centres if abs(c.z-z)<.001 and abs((c-p).dot(n)-.035)<.001 and abs((c-p).dot(u)-window['x'])<window['width']/2]
 assert len(bars)==2,(window,bars)
 assert all(abs(a-b)<.0001 for a,b in zip(sorted(bars),[-1/6,1/6]))
 rails=[(c.z-window['low'])/(window['high']-window['low']) for c in hcentres if abs((c-p).dot(u)-window['x'])<.001 and abs((c-p).dot(n)-.037)<.001 and window['low']<c.z<window['high']]
 expected=[1/6,2/6,4/6,5/6] if window['rows']==6 else [.25,.75]
 assert len(rails)==len(expected) and all(abs(a-b)<.0001 for a,b in zip(sorted(rails),expected))
 measured.append({'wall':window['wall'],'height':z,'fractions':sorted(bars),'horizontalFractions':sorted(rails),'rows':window['rows']})
assert len(measured)==30 and bpy.data.objects[audit['hiddenOldMesh']].hide_render
for family in audit['palette'].values():
 material=bpy.data.materials[family['material']]
 assert all(obj.name.startswith('LAK_')for obj in bpy.data.objects if obj.type=='MESH' and material in obj.data.materials[:])
audit['savedWindowMeasurements']=measured;path.write_text(json.dumps(audit,indent=2)+'\n');print('SAVED_LAKATOS_SASHES_VERIFIED',len(measured))
