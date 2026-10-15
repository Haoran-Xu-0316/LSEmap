"""Differentiate OLD portal fixed framing from thin paired-leaf meeting seams.

Fixed authoring configuration. Preserve the accepted opening, four candidate
leaves, hardware, glass optics and archived original meshes/UVs. Photo-guided
profile widths are estimates; this is not a surveyed door or certified net width.
"""
from pathlib import Path
import array
import hashlib
import json
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v217.blend'
SHA='daac71eaf581c94e544fe7098e51f897273223a981bd8f1b4b637d56d4469423'
OUT=ROOT/'result/blender/old-portal218'
PREFIX='OLDPORTAL218_'
SOURCES={'frame':'OLD_NEXT_EXTERIOR154_door_frame','glass':'OLD_ENTRANCE192_single_glass','hardware':'OLD_NEXT_EXTERIOR154_door_steel'}
SEAM_WIDTH=.018
CENTRAL_FIXED_WIDTH=.16
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import accepted_fingerprints,object_fingerprint
from refine_portsmouth_exterior207 import material_fingerprint
import refine_old_glazing217 as comparison


def update():
 for scene in bpy.data.scenes:
  for layer in scene.view_layers:layer.update()


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh_geometry_state(obj):
 digest=hashlib.sha256()
 for data,key,kind,count in [(obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)]:
  values=array.array(kind,[0])*(len(data)*count);data.foreach_get(key,values);digest.update(values.tobytes())
 uvs={}
 for layer in obj.data.uv_layers:
  values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);uvs[layer.name]=hashlib.sha256(values.tobytes()).hexdigest()
 return dict(geometry=digest.hexdigest(),uv=uvs)


def components(obj,right,outward):
 adjacency=[set()for _ in obj.data.vertices]
 for edge in obj.data.edges:
  a,b=edge.vertices;adjacency[a].add(b);adjacency[b].add(a)
 remaining=set(range(len(adjacency)));result=[]
 while remaining:
  seed=remaining.pop();pending=[seed];indices=[seed]
  while pending:
   for neighbour in adjacency[pending.pop()]:
    if neighbour in remaining:remaining.remove(neighbour);pending.append(neighbour);indices.append(neighbour)
  pts=[obj.matrix_world@obj.data.vertices[i].co for i in indices]
  local=[(p.dot(right),p.dot(outward),p.z)for p in pts]
  low=[min(p[i]for p in local)for i in range(3)];high=[max(p[i]for p in local)for i in range(3)]
  result.append(dict(indices=indices,low=low,high=high,dimensions=[high[i]-low[i]for i in range(3)],centre=[(low[i]+high[i])/2 for i in range(3)]))
 return result


def set_width(obj,part,low,high,right):
 inverse=obj.matrix_world.inverted()
 for index in part['indices']:
  point=obj.matrix_world@obj.data.vertices[index].co
  old=point.dot(right);fraction=(old-part['low'][0])/part['dimensions'][0]
  obj.data.vertices[index].co=inverse@(point+right*(low+(high-low)*fraction-old))
 obj.data.update()


def portal_checks(frame,glass,hardware,right,outward):
 vertical=sorted([p for p in components(frame,right,outward)if p['dimensions'][2]>2.5],key=lambda p:p['centre'][0])
 panes=sorted(components(glass,right,outward),key=lambda p:(p['low'][2],p['low'][0]))
 assert len(vertical)==5 and len(panes)==8
 records=[]
 for row in range(2):
  for column in range(4):
   pane=panes[row*4+column];left,right_stile=vertical[column:column+2]
   gap_left=pane['low'][0]-left['high'][0];gap_right=right_stile['low'][0]-pane['high'][0]
   assert -.003<gap_left<.03 and -.003<gap_right<.03,(gap_left,gap_right)
   records.append(dict(row=row,column=column,glassWidth=pane['dimensions'][0],leftClearance=gap_left,rightClearance=gap_right))
 pull_parts=[p for p in components(hardware,right,outward)if p['dimensions'][2]>.5 and p['dimensions'][0]<.1]
 assert len(pull_parts)==4
 for pull in pull_parts:
  assert any(p['low'][0]<pull['centre'][0]<p['high'][0] and p['low'][2]<pull['centre'][2]<p['high'][2]for p in panes[:4])
 # Closed glass is intentionally excluded when checking the openable doorway
 # aperture. Every opaque fixed/leaf frame remains included in these short rays.
 vertices=[];faces=[];owners=[]
 for obj in bpy.data.collections['OLD_EXTERIOR'].all_objects:
  if obj.hide_render or obj.type!='MESH'or obj==glass:continue
  start=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices);faces.extend(tuple(start+i for i in face.vertices)for face in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
 tree=BVHTree.FromPolygons(vertices,faces)
 paths=[]
 for pane in panes[:4]:
  for z in [1.5,2.4]:
   point=right*pane['centre'][0]+outward*pane['centre'][1]+Vector((0,0,z))
   hit=tree.ray_cast(point+outward*.20,-outward,.40)
   assert hit[0]is None,'Opaque frame crosses candidate door-leaf centre'
   paths.append(dict(leafCentre=pane['centre'][0],height=z,opaqueHit=False,depthMetres=.4,closedGlassExcluded=True))
 floor_probes=[]
 for pane in panes[:4]:
  for offset in [-.18,.18]:
   point=right*pane['centre'][0]+outward*(pane['centre'][1]+offset)+Vector((0,0,1.9))
   hit=tree.ray_cast(point,Vector((0,0,-1)),2.0)
   assert hit[0]is not None,'Missing threshold support'
   assert abs(hit[0].z-.69)<.025,('Unexpected threshold height',hit[0].z,owners[hit[2]])
   floor_probes.append(dict(leafCentre=pane['centre'][0],depthOffset=offset,support=owners[hit[2]],height=hit[0].z))
 return dict(thresholdSupportProbes=floor_probes,glassFrameEdges=records,hardwarePullsInsideLeafPanes=len(pull_parts),openableApertureProbes=paths,verticalWidths=[p['dimensions'][0]for p in vertical],panes=panes)


def run():
 OUT.mkdir(parents=True,exist_ok=True)
 assert sha(BASE)==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
 expected=accepted_fingerprints(ROOT/'result/blender/stage217',SHA)
 actual={o.name:object_fingerprint(o)for o in bpy.data.objects}
 mismatches=[name for name in set(expected)|set(actual)if expected.get(name)!=actual.get(name)]
 assert not mismatches,mismatches[:20]
 material_states={m.name:material_fingerprint(m)for m in bpy.data.materials}
 visibility={o.name:o.hide_render for o in bpy.data.objects}
 metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
 protected={o.name for space in metadata['spaces']for o in bpy.data.collections[space['collection']].all_objects}
 assert len(metadata['spaces'])==18 and len(protected)==623
 assert not protected.intersection(SOURCES.values())
 protected_states={name:actual[name]for name in protected}
 # Actual accepted pane plane supplies the registration; no old pre112 frame.
 source_glass=bpy.data.objects[SOURCES['glass']]
 hint=Vector((.890279,-.455415,0))
 face=max(source_glass.data.polygons,key=lambda p:(source_glass.matrix_world.to_3x3().inverted().transposed()@p.normal).normalized().dot(hint))
 outward=(source_glass.matrix_world.to_3x3().inverted().transposed()@face.normal).normalized();outward.z=0;outward.normalize()
 right=Vector((-outward.y,outward.x,0))
 initial_frame=components(bpy.data.objects[SOURCES['frame']],right,outward)
 old_stiles=sorted([part for part in initial_frame if part['dimensions'][2]>2.5],key=lambda p:p['centre'][0]);assert len(old_stiles)==5
 initial_glass=sorted(components(source_glass,right,outward),key=lambda p:(p['low'][2],p['low'][0]));assert len(initial_glass)==8
 comparison.OUT=OUT
 if not(OUT/'before-houghton.png').exists():comparison.render_review('before')
 owned={};states={}
 for role,name in SOURCES.items():
  source=bpy.data.objects[name];assert not source.hide_render
  obj=source.copy();obj.data=source.data.copy();obj.name=PREFIX+role;obj.data.name=obj.name
  obj['originalObject']=name;obj['destinationCollection']='OLD_EXTERIOR'
  obj['scope']='Houghton portal frame/leaf hierarchy only; accepted whole opening and four candidate leaves retained'
  bpy.data.collections['OLD_EXTERIOR'].objects.link(obj);obj.hide_render=False;obj.hide_set(False)
  owned[role]=obj;states[role]=mesh_geometry_state(source)
 frame=owned['frame'];glass=owned['glass'];hardware=owned['hardware']
 new_widths=[old_stiles[0]['dimensions'][0],SEAM_WIDTH,CENTRAL_FIXED_WIDTH,SEAM_WIDTH,old_stiles[4]['dimensions'][0]]
 for part,width in zip(old_stiles,new_widths):
  set_width(frame,part,part['centre'][0]-width/2,part['centre'][0]+width/2,right)
 new_stiles=sorted([p for p in components(frame,right,outward)if p['dimensions'][2]>2.5],key=lambda p:p['centre'][0])
 pane_adjustments=[]
 for index,pane in enumerate(initial_glass):
  column=index%4
  left_gap=pane['low'][0]-old_stiles[column]['high'][0]
  right_gap=old_stiles[column+1]['low'][0]-pane['high'][0]
  low=new_stiles[column]['high'][0]+left_gap;high=new_stiles[column+1]['low'][0]-right_gap
  set_width(glass,pane,low,high,right)
  pane_adjustments.append(dict(pane=index,column=column,beforeWidth=pane['dimensions'][0],afterWidth=high-low,inheritedFrameClearances=[left_gap,right_gap]))
 for name in SOURCES.values():bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
 update()
 assert all(mesh_geometry_state(obj)['uv']==states[role]['uv']for role,obj in owned.items())
 assert mesh_geometry_state(hardware)==states['hardware']
 checks=portal_checks(frame,glass,hardware,right,outward)
 # The external envelope, height, frame depth and datum stay at their accepted
 # coordinates. Only internal stile widths and adjacent pane edges differ.
 original_bounds=[min(v['low'][i]for v in initial_frame)for i in range(3)]+[max(v['high'][i]for v in initial_frame)for i in range(3)]
 current=components(frame,right,outward)
 current_bounds=[min(v['low'][i]for v in current)for i in range(3)]+[max(v['high'][i]for v in current)for i in range(3)]
 assert max(abs(a-b)for a,b in zip(original_bounds,current_bounds))<.00003
 assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in actual.items())
 assert all(material_fingerprint(bpy.data.materials[name])==value for name,value in material_states.items())
 comparison.render_review('after')
 fingerprints={o.name:object_fingerprint(o)for o in owned.values()}
 bindings={o.name:[m.name for m in o.data.materials]for o in owned.values()}
 component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(owned.values()),fake_user=True,compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
 assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in expected.items())
 with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=list(fingerprints)
 for obj in loaded.objects:
  for index,name in enumerate(bindings[obj.name]):obj.data.materials[index]=bpy.data.materials[name]
  bpy.data.collections['OLD_EXTERIOR'].objects.link(obj);obj.hide_render=False;obj.hide_set(False)
 for name in SOURCES.values():bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
 update()
 assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in expected.items())
 assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in fingerprints.items())
 assert all(material_fingerprint(bpy.data.materials[name])==value for name,value in material_states.items())
 assert all(bpy.data.objects[name].hide_render==value for name,value in visibility.items()if name not in SOURCES.values())
 assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in protected_states.items())
 saved_checks=portal_checks(bpy.data.objects[PREFIX+'frame'],bpy.data.objects[PREFIX+'glass'],bpy.data.objects[PREFIX+'hardware'],right,outward)
 for role in SOURCES:
  assert mesh_geometry_state(bpy.data.objects[PREFIX+role])['uv']==states[role]['uv']
 verification=dict(savedComponentReopened=True,acceptedOriginalFingerprintsVerified=len(expected),originalMaterialNodesVerified=len(material_states),originalGeometryUVsAndBindingsPreserved=True,independentSpacesVerified=18,independentRoomObjectsVerified=len(protected),unrelatedVisibilityPreserved=True,glassFrameClearancePairsVerified=len(saved_checks['glassFrameEdges']),openableApertureProbesVerified=len(saved_checks['openableApertureProbes']),thresholdSupportProbesVerified=len(saved_checks['thresholdSupportProbes']),hardwarePullsInsideLeafPanes=saved_checks['hardwarePullsInsideLeafPanes'],glassHardwareOriginalOpticsAndMaterialNodesUnchanged=True,wholePortalBoundsUnchanged=True,sourceFileUnchanged=sha(BASE)==SHA)
 references=[]
 for path in ['data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_01.jpg','data/collections/old-exterior-2026/user-references/houghton-entrance-latest.png']:
  references.append(dict(path=path,sha256=sha(ROOT/path),captureDate='unknown',use='Private visual evidence, never a public texture'))
 report=dict(version=218,baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection='OLD_EXTERIOR',destinationCollection='OLD_EXTERIOR',addedObjects=list(fingerprints),archivedObjects=list(SOURCES.values()),changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,materialBindings=bindings,scope='Differentiate two broad glazed doorway fields with a fixed central spine and thin paired-leaf meeting seams; retain four candidate leaves and existing hardware.',stileWidths=dict(before=[p['dimensions'][0]for p in old_stiles],after=saved_checks['verticalWidths'],estimatedLeafSeamWidth=SEAM_WIDTH,estimatedCentralFixedWidth=CENTRAL_FIXED_WIDTH),paneAdjustments=pane_adjustments,checks={k:v for k,v in saved_checks.items()if k!='panes'},wholePortalBounds=original_bounds,verification=verification,references=references,previews=['before-houghton.png','after-houghton.png'],limitations=['18mm leaf-seam and160mm fixed-spine widths are photographic estimates, not product or surveyed dimensions.','Four candidate leaves remain; exact active/manual/fixed operation is not certified from photographs.','No146cm accessible net-opening value is used to resize the full portal.','No changes to the arch, threshold, steps, artwork, OLDGLASS217 window batches or room collections; no additional glass layer or reference texture.','Openable-aperture probes intentionally exclude the closed door panes and inspect only their local geometric clearance, not full-building egress or accessibility compliance.'])
 (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
 print('OLDPORTAL218_COMPONENT_REOPENED',sha(component),len(expected),len(protected),flush=True)
if __name__=='__main__':run()
