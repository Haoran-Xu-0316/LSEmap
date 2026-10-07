"""Correct the photographed OLD foyer bench support without changing its seat.

The historical Design Engine built photo shows a solid pale stone plinth beneath
its dark timber bench. Plinth thickness and recess remain modelling estimates.
The original bench, floor and doorway registration are retained exactly.
"""
import bpy
from build_room_samples167 import RoomGeometry
PREFIX='OLD182_foyer_'
COLLECTION='OLD_MAIN_FOYER174'

def apply_old_bench182():
    name=PREFIX+'stone_bench_plinth'
    if bpy.data.objects.get(name):
        return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[]}
    bench=bpy.data.objects['OLD174_foyer_waiting_bench']
    supports=bpy.data.objects['OLD174_foyer_bench_supports']
    floor=bpy.data.objects['OLD174_foyer_lower_limestone_floor']
    assert not bench.hide_render and not supports.hide_render
    corners=[v.co for v in bench.data.vertices]
    lo=[min(v[i] for v in corners)for i in range(3)]
    hi=[max(v[i] for v in corners)for i in range(3)]
    bottom=max(v.co.z for v in floor.data.vertices)
    top=lo[2];assert top>bottom
    # Recesses expose the timber seat edge without moving its accepted position.
    g=RoomGeometry(bpy.data.collections[COLLECTION],PREFIX)
    g.materials['white']=floor.data.materials[0]
    g.box('stone_bench_plinth','white',((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,(bottom+top)/2),(hi[0]-lo[0]-.12,hi[1]-lo[1]-.04,top-bottom))
    objects=g.finish()
    for obj in objects:
        obj.matrix_world=bench.matrix_world.copy()
        obj['referencePeriod']='2011built refurbishment'
        obj['dimensionBasis']='existing registered seat and floor; plinth recess estimated'
    supports.hide_render=True;supports.hide_set(True)
    return {'alreadyApplied':False,'code':'OLD','version':182,'addedObjects':[o.name for o in objects],
      'archivedObjects':[supports.name],'changedObjects':[],
      'source':'https://www.designengine.co.uk/projects/reception-london-school-of-economics/',
      'referenceImage':'result/blender/old_foyer173/reception-main.jpg',
      'scope':'Historical foyer timber bench stone support; no new exterior survey or current room-layout claim',
      'seatRetained':bench.name,'floorRetained':floor.name,'plinthLocalBounds':[[lo[0]+.06,lo[1]+.02,bottom],[hi[0]-.06,hi[1]-.02,top]],'solidProof':g.solid_proof}
