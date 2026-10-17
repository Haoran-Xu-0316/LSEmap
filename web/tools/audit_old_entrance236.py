"""Read-only Houghton entrance review; do not manufacture a change for236."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path('/Users/haoranxu/Desktop/LSEmap');BASE=ROOT/'result/blender/LSE_campus_detailed_v234.blend';OUT=ROOT/'result/blender/old-entrance236';DATA=ROOT/'data/collections/old-entrance236'
SHA='0c9c4d7d5793ac3693c6ff7b9789e5300ebca32a5de39e0a39b75a910182d0b7'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def sources():
 paths=['data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_01.jpg','data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_06.jpg','data/collections/old-user-reference/houghton-user-entrance-additional-20261002.png','data/collections/old-user-reference/houghton-entrance.png','data/collections/old-user-reference/houghton-entrance-user-20261002.png','data/collections/old-exterior-2026/user-references/houghton-entrance-latest.png','data/collections/old-exterior-2026/user-references/houghton-arch-masonry.png','data/collections/old-roof-2024/existing-south.pdf']
 refs=[dict(path=p,sha256=sha(ROOT/p))for p in paths];groups={}
 for r in refs:groups.setdefault(r['sha256'],[]).append(r['path'])
 write(DATA/'sources.json',dict(references=refs,duplicateReferenceGroups=[p for p in groups.values()if len(p)>1],sourceManifest='data/collections/old-roof-2024/source-documents.json',officialPhotoPage='https://webbyates.com/projects/the-old-building/',dateBoundary='South existing/strip-out drawing dated2022-12-07,P1,LSEOLD-HBA-V1-XX-DR-A-080201. The folder name2024does not date that existing drawing. Engineer project completed2024; photograph capture dates unknown. User file names20261001/02 are receipt labels, not photographic capture evidence. No2026site survey inferred.',sourcePhotographsPrivateOnly=True,newLookup=False,observations=['Four visible external rises and chamfered widening tread ends in unobstructed built photograph01.','Right raised route with continuous silver handrail is visible, but its complete far endpoint and measured slope are not supplied by the front crop.','Broad concave arch and radial joints, blue four-column casements and paired LSE signs already present in current viewer.','Photographic stone looks varied and pale; uncalibrated exposure does not justify recolouring.','The translucent lattice Final Sale artwork is already a sourced218representation; this review does not replace it with invented solid figures.']))
def inspect_native():
 import bpy
 from mathutils import Vector
 sys.path.insert(0,str(ROOT/'web/tools'))
 from integrate_exterior_round194 import object_fingerprint,update_scene
 from refine_portsmouth_exterior207 import material_fingerprint
 from refine_ksw_exterior219 import modifier_state
 from refine_old_portal218 import components
 assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 def state():return dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},materials={m.name:material_fingerprint(m)for m in bpy.data.materials},owners={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects},modifiers={o.name:modifier_state(o)for o in bpy.data.objects},props={o.name:repr(sorted(o.items()))for o in bpy.data.objects},visibility={o.name:o.hide_render for o in bpy.data.objects})
 before=state();prior=json.loads((ROOT/'result/blender/exterior-render235/baseline-state.json').read_text());canonical=json.loads(json.dumps(before));differences={key:[name for name in set(canonical[key])|set(prior[key])if canonical[key].get(name)!=prior[key].get(name)]for key in before};write(OUT/'prior-state-comparison.json',differences);assert not any(differences.values()),{k:v[:3]for k,v in differences.items()if v}
 frame=json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text());right=Vector(frame['right']);normal=Vector(frame['outward']);rows=[]
 for o in bpy.data.collections['OLD_EXTERIOR'].all_objects:
  if o.hide_render or o.type!='MESH':continue
  pts=[o.matrix_world@v.co for v in o.data.vertices];rows.append(dict(name=o.name,vertices=len(o.data.vertices),faces=len(o.data.polygons),materials=[m.name if m else None for m in o.data.materials],bounds=[[min(p.dot(right)for p in pts),max(p.dot(right)for p in pts)],[min(p.dot(normal)for p in pts),max(p.dot(normal)for p in pts)],[min(p.z for p in pts),max(p.z for p in pts)]]))
 write(OUT/'current-old-inventory.json',rows)
 steps=bpy.data.objects['OLD_NEXT_ACCESS_external_four_steps'];parts=components(steps,right,normal);tops=sorted(round(p['high'][2],6)for p in parts);assert len(parts)==4 and tops==[.21,.37,.53,.69]
 portal={}
 for role in ['frame','glass','hardware']:
  o=bpy.data.objects['OLDPORTAL218_'+role];assert not o.hide_render;portal[role]=dict(object=o.name,parts=[dict(low=p['low'],high=p['high'],dimensions=p['dimensions'])for p in components(o,right,normal)])
 ramp=bpy.data.objects['OLD_NEXT_APPROACH_continuous_ramp_surface'];assert not ramp.hide_render
 write(OUT/'current-houghton-geometry.json',dict(externalSteps=dict(object=steps.name,count=len(parts),topHeights=tops,riseMetres=.16,dimensionsEstimated=True),portal=portal,rightRaisedRoute=ramp.name,checkedOwners='OLD_EXTERIOR',scope='Houghton only; Clare Market entrance is owned by another236reviewer'))
 import refine_old_glazing217 as review
 review.OUT=OUT;review.render_review('current')
 assert state()==before and sha(BASE)==SHA
 meta=json.loads((ROOT/'web/tools/building-metadata.json').read_text());rooms={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in meta['spaces']};assert len(rooms)==35 and len(set(n for ns in rooms.values()for n in ns))==1485
 write(OUT/'verification.json',dict(independentlyOpenedBaseline=True,baselineSha256=sha(BASE),objects=len(before['objects']),materials=len(before['materials']),protectedSpaces=len(rooms),protectedMembers=1485,allOriginalGeometryUVTransformsNodesBindingsModifiersPropertiesOwnershipVisibilityEqual=True,baselineStateMatchesIndependent235Audit=True,noFullNativeOrComponentSaved=True))
def finalize():
 web=json.loads((OUT/'web-review.json').read_text());assert web['sourceModelSha256']==SHA and not web['errors']
 hashes={str(p.relative_to(ROOT)):sha(p)for p in [ROOT/'web/src/viewer.js',ROOT/'web/src/surface-materials.js',ROOT/'web/public/models/catalogue.json']};write(OUT/'production-source-hashes.json',hashes)
 findings=[dict(part='Arch and wall layers',status='No safely located new correction',evidence='Existing broad concave arch, radial joints, inner rim and shallow rustication are present. Current silhouette broadly follows both user and engineer photos; exact radius/recession are unmeasured.'),dict(part='Exterior approach',status='Previously corrected four rises retained',evidence='Saved current native mesh has four connected tread solids with tops.21,.37,.53,.69m, not the six-riser obsolete137diagnostic. Photo01supports four visible rises and chamfered ends. Rise,run,width and ramp slope remain estimates.'),dict(part='Blue casements',status='Previously corrected hierarchy retained',evidence='Four-column casements and heavier top-quarter transom already originate in85; neutral pane colour217and portal218are active. No new survey supports relocating openings or recolouring the blue joinery.'),dict(part='Sculpture and upper work',status='Excluded from new modelling',evidence='218lattice artwork and233upper grilles are accepted separate work. No new carving, bodies or attic revisions made.')]
 write(OUT/'audit.json',dict(version=236,building='OLD',scope='Houghton principal entrance only',status='no-change-source-review',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=None,componentSha256=None,displayOwner='OLD_EXTERIOR',addedObjects=[],archivedObjects=[],changedObjects=[],replacementMaterialBindings={},sourceManifest=str((DATA/'sources.json').relative_to(ROOT)),findings=findings,verification=json.loads((OUT/'verification.json').read_text()),previews=['current-houghton.png','web-current-houghton.webp','web-current-houghton-context.webp'],webEvidence='web-review.json',productionSourceHashes=hashes,limitations=['No claim that the whole OLD Building is now exact: façade dimensions, stone section, route width/gradient and artwork depth remain estimates.','Existing2022drawing and unknown-date completed-project photos are not a2026survey. Multiple user filenames contain the identical photograph.','No fabricated before/after pair: no scene change was justified, so current native/production/context views are recorded.','The production gallery camera is partially occluded by adjacent buildings with context enabled. Context image records this actual obstruction; it is not an unoccluded whole-frontage photo match.'],nextUsefulAction='A dated front entrance photograph with unoccluded landing plus ground plan/section or spot heights would support calibrating arch recession and the long raised route/curb connection; existing front crops cannot determine these dimensions.'))
if __name__=='__main__':
 try:import bpy
 except ImportError:
  sources()
  if (OUT/'web-review.json').exists()and(OUT/'verification.json').exists():finalize()
 else:inspect_native()
