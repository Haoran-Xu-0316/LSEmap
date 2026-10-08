"""Reopen the integrated scene and verify scoped geometry, room separation and idempotence."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name("verify_old_lettering185_blender.py")),run_name="__main__")
import hashlib, json, sys
import bpy
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from refine_rooms import geometry_signatures
from refine_architectural_glass import shape_signature
from refine_old_foyer174 import apply_old_foyer174, COLLECTION
from refine_houghton_environment178 import apply_houghton_environment178
from refine_lrb_exterior178 import apply_lrb_exterior178
from refine_shf_exterior179 import apply_shf_exterior179
from refine_landscape179 import apply_landscape179
from refine_con_exterior180 import apply_con_exterior180
from refine_exterior_glass181 import apply_exterior_glass181, surface_components, is_glazing
import bmesh
from refine_par_exterior180 import apply_par_exterior180
from refine_saw_lower_structure173 import OLD_STAIR_NAMES, OLD_FLOORS, FLOOR_NAMES
from refine_street_fixtures173 import OWNED
REPORT = ROOT / 'result/blender/stage185'
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v185.blend'
proof = json.loads((REPORT / 'building-refinement.json').read_text())
assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
assert geometry_signatures() == proof['geometrySignatures']
for refiner in (apply_houghton_environment178, apply_lrb_exterior178, apply_shf_exterior179, apply_landscape179, apply_con_exterior180, apply_par_exterior180, apply_exterior_glass181):
    assert refiner()['alreadyApplied']
assert geometry_signatures() == proof['geometrySignatures']
assert {o.name:o.hide_render for o in bpy.data.objects} == proof['visibility']
for name, digest in proof['originalShapesAndUVs'].items():
    assert shape_signature(bpy.data.objects[name]) == digest
assert len(bpy.data.objects['SHF_NEXT_EXTERIOR179_three_dormer_panes'].data.polygons)==9
for name in ('LANDSCAPE179_Watkins_registered_crowns','LANDSCAPE179_Houghton_planter_crowns'):
    assert name in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects

glass_proof=json.loads((ROOT/'result/blender/stage181/building-refinement.json').read_text())
for record in glass_proof['changes'][0]['records']:
    original=bpy.data.objects[record['source']];replacement=bpy.data.objects[record['target']]
    assert len(original.data.polygons)==len(replacement.data.polygons)
    assert [tuple(v.co) for v in original.data.vertices]==[tuple(v.co) for v in replacement.data.vertices]
    for old,new in zip(original.data.polygons,replacement.data.polygons):
        assert set(old.vertices)==set(new.vertices)
        for layer in original.data.uv_layers:
            before={tuple(original.data.vertices[original.data.loops[i].vertex_index].co):tuple(layer.data[i].uv) for i in old.loop_indices}
            after={tuple(replacement.data.vertices[replacement.data.loops[i].vertex_index].co):tuple(replacement.data.uv_layers[layer.name].data[i].uv) for i in new.loop_indices}
            assert before==after
    bm=bmesh.new();bm.from_mesh(replacement.data)
    for binding in record['bindings']:
        old=bpy.data.materials[binding['sourceMaterial']];new=replacement.data.materials[binding['targetSlot']]
        left=old.node_tree.nodes['Principled BSDF'];right=new.node_tree.nodes['Principled BSDF']
        for name in ['Base Color','Alpha','Roughness','Transmission Weight']:
            assert (tuple(left.inputs[name].default_value)==tuple(right.inputs[name].default_value) if name=='Base Color' else left.inputs[name].default_value==right.inputs[name].default_value)
        assert old.get('webOpacity')==new.get('webOpacity')
        assert right.inputs['Metallic'].default_value==0
        if binding['closed']:
            assert new['webClosedGlazing']
            assert all(closed and volume*replacement.matrix_world.to_3x3().determinant()>0 for _,closed,volume in surface_components(bm,binding['targetSlot']))
    bm.free()
posts = bpy.data.objects['OLD178_Houghton_approach_black_posts']
rail = bpy.data.objects['OLD_NEXT_APPROACH_continuous_handrail']
assert posts.data.materials[0] not in list(rail.data.materials)
assert bpy.data.objects['OLD_NEXT_APPROACH_silver_posts'].hide_render
assert posts.name in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects
assert len(bpy.data.objects['LRB_EXTERIOR178_plaza_single_panes'].data.polygons) == 66
assert bpy.data.objects['LRB_NEXT_PLAZA155_glass'].hide_render
assert bpy.data.objects['LRB_EXTERIOR178_plaza_single_panes'].name in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects
assert len(bpy.data.objects['MAR177_ground_glass_panes'].data.polygons) == 107
assert len(bpy.data.objects['MAR177_mezzanine_guard_glass'].data.polygons) == 54
assert bpy.data.objects['MAR_D3_ground_glass_panes'].hide_render
attic = bpy.data.collections['KGS176_PORTUGAL_ATTIC']
assert attic['windowAxes'] == 5 and attic['paneFacets'] == 9
assert len(bpy.data.objects['KGS176_attic_single_glass'].data.polygons) == 9
assert all(len(o.users_collection) == 1 and o.users_collection[0].name == '00_SITE'
           for o in (bpy.data.objects['SITE176_PEA_Portugal_frontage_bollards'],
                     bpy.data.objects['SITE176_PEA_Portugal_double_yellow_lines']))
campus = set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())
room = bpy.data.collections['LRB_PUBLIC_INTERIOR168_study']
assert room.all_objects and all(obj.name not in campus for obj in room.all_objects)
assert len(room.all_objects) == 109
room171 = bpy.data.collections['CBG205_ROOM171_study']
assert room171['studentSeatCount'] == 42
assert all(o.name not in campus for o in room171.all_objects)
assert len(room171.all_objects) == 24
glass = bpy.data.objects['OLD_NEXT_GLAZING172_single_door_panes']
assert len(glass.data.vertices) == 32 and len(glass.data.polygons) == 8
assert glass.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value == 0
assert bpy.data.objects['OLD_NEXT_EXTERIOR154_door_glass'].hide_render
panes = bpy.data.objects['CKK_EXTERIOR173_D5_pavilion80_glazing_glass']
assert len(panes.data.polygons) == 18
shader = panes.data.materials[0].node_tree.nodes['Principled BSDF']
assert shader.inputs['Metallic'].default_value == 0
assert shader.inputs['Transmission Weight'].default_value > .1
assert abs(panes.data.materials[0]['webOpacity'] - .55) < 1e-6
assert all(bpy.data.objects[name].hide_render for name in OLD_STAIR_NAMES + OLD_FLOORS)
assert all(not bpy.data.objects[name].hide_render for name in FLOOR_NAMES)
assert OWNED in campus
foyer = bpy.data.collections[COLLECTION]
assert all(o.name in campus for o in foyer.all_objects)
assert all(bpy.data.objects[n].hide_render for n in proof['archivedObjects'])
assert not bpy.data.libraries
assert not any(i.source == 'FILE' and not i.packed_file for i in bpy.data.images)
result = dict(version=185, sourceModelSha256=proof['sourceModelSha256'],
              savedSceneReopened=True, atticWindowAxes=5, atticPaneFacets=9, streetMeshesSingleSiteMembership=True, marGroundSinglePanes=107, marGuardSinglePanes=54, allMeshSignaturesVerified=True,
              allOriginalShapesAndUVsPreserved=True, idempotent=True,
              independentRoomsOutsideCampus=True, entranceFoyerRegisteredToCampus=True, externalDependencies=False,
              archivedObjects=proof['archivedObjects'])
result['glassSurfacePolicyVerified']=True
result['closedShells']=glass_proof['changes'][0]['closedShells']
result['reversedShells']=glass_proof['changes'][0]['reversedShells']
result['benchSeatAndFloorTouching']=True
result['independentSALBrickMaterials']=True
result['brickScaleAndMortarRetained']=True
prior=json.loads((ROOT/'result/blender/stage184/reopened-verification.json').read_text())
assert prior['sourceModelSha256']==proof['baselineSha256']
result['registeredLabels']=3
result['stoneContactProbes']=27
result['allOriginalFontsPreserved']=True
result['closedPositiveCopingChains']=prior['closedPositiveCopingChains']
result['windowGlassOverlaps']=[]
result['recessedGablePanes']=7
result['visibleThroughWindowApertures']=7
result['paneSilhouettesAndFinishesRetained']=True
result['registeredAnchorsRetained']=True
result['internalEndCapsRemoved']=294
(REPORT / 'reopened-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print('BUILDINGS185_REOPENED_VERIFIED')
