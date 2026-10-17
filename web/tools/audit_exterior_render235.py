"""Identify the234Portugal-view blue speckles without changing source appearance."""
from pathlib import Path
import json,math,hashlib,sys
ROOT=Path('/Users/haoranxu/Desktop/LSEmap');OUT=ROOT/'result/blender/exterior-render235';DATA=ROOT/'data/collections/exterior-render235'
BASE=ROOT/'result/blender/LSE_campus_detailed_v234.blend';SHA='0c9c4d7d5793ac3693c6ff7b9789e5300ebca32a5de39e0a39b75a910182d0b7'
def write(name,value): (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare():
 from PIL import Image
 im=Image.open(ROOT/'result/blender/street-ground234/after-portugal-duplicate-nonregression.png').convert('RGB');blue=[]
 for y in range(5,350):
  for x in range(670,755):
   r,g,b=im.getpixel((x,y))
   if b>r+42 and b>g+20:blue.append([x,y])
 selected=blue[::max(1,len(blue)//24)][:24];write('blue-pixels.json',dict(count=len(blue),pixels=selected,criterion='B>R+42,B>G+20;upper-right brick ROI x670..754,y5..349',source='result/blender/street-ground234/after-portugal-duplicate-nonregression.png'))
def diagnose():
 import bpy
 from mathutils import Vector
 sys.path.insert(0,str(ROOT/'web/tools'))
 from integrate_exterior_round194 import update_scene,object_fingerprint
 from refine_portsmouth_exterior207 import material_fingerprint
 from refine_ksw_exterior219 import modifier_state
 assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();s=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=s
 state=dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},materials={m.name:material_fingerprint(m)for m in bpy.data.materials},owners={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects},modifiers={o.name:modifier_state(o)for o in bpy.data.objects},props={o.name:repr(sorted(o.items()))for o in bpy.data.objects},visibility={o.name:o.hide_render for o in bpy.data.objects})
 write('baseline-state.json',state);write('baseline-counts.json',dict(objects=len(bpy.data.objects),materials=len(bpy.data.materials),baselineSha256=SHA))
 for o in s.objects:
  if o.hide_render:o.hide_set(True)
 cd=bpy.data.cameras.new('RENDER235_DIAGNOSTIC_CAMERA');c=bpy.data.objects.new(cd.name,cd);s.collection.objects.link(c);s.camera=c;cd.sensor_fit='VERTICAL';cd.clip_end=1400;cd.lens=cd.sensor_height/(2*math.tan(math.radians(62)/2));c.location=(-2,16,9);c.rotation_euler=(Vector((49,37,.1))-c.location).to_track_quat('-Z','Y').to_euler();update_scene()
 corners=c.data.view_frame(scene=s);aspect=1000/750
 # Explicit vertical projection matches234camera independent of inherited render size.
 rotation=c.rotation_euler.to_quaternion();rows=[];deps=bpy.context.evaluated_depsgraph_get()
 pixels=json.loads((OUT/'blue-pixels.json').read_text())['pixels']+[[700,200],[715,200],[730,200],[715,275],[710,325]]
 for x,y in pixels:
  d=rotation@Vector(((2*(x+.5)/1000-1)*aspect*math.tan(math.radians(31)),(1-2*(y+.5)/750)*math.tan(math.radians(31)),-1));d.normalize();origin=c.location.copy();hits=[]
  for _ in range(12):
   ok,point,normal,face,o,m=s.ray_cast(deps,origin,d,distance=300)
   if not ok:break
   slot=o.data.polygons[face].material_index if 0<=face<len(o.data.polygons)else -1
   hits.append(dict(object=o.name,point=list(point),normal=list(normal),face=face,distance=(point-c.location).length,materialSlot=slot,material=o.material_slots[slot].material.name if slot>=0 and slot<len(o.material_slots)and o.material_slots[slot].material else None,owners=[co.name for co in o.users_collection]));origin=point+d*.00001
  rows.append(dict(pixel=[x,y],hits=hits))
 write('native-ray-hits.json',rows)
 names=sorted({r['hits'][0]['object']for r in rows if r['hits']});details=[]
 for n in names:
  o=bpy.data.objects[n]
  materials=[]
  for m in o.data.materials:
   if m:materials.append(dict(name=m.name,diffuse=list(m.diffuse_color),nodes=[dict(name=node.name,type=node.type,inputs={i.name:str(i.default_value)for i in node.inputs if hasattr(i,'default_value')})for node in m.node_tree.nodes]if m.use_nodes else []))
  details.append(dict(name=n,properties={k:str(v)for k,v in o.items()},materials=materials,bounds=[[min((o.matrix_world@v.co)[a]for v in o.data.vertices),max((o.matrix_world@v.co)[a]for v in o.data.vertices)]for a in range(3)],vertices=len(o.data.vertices),polygons=len(o.data.polygons)))
 from mathutils.bvhtree import BVHTree
 art=bpy.data.objects['LRB_NEXT_ENVELOPE_Blue_Rain_static_photo_display'];wall=bpy.data.objects['LRB196_FINISH_LRB_NEXT_ENVELOPE_continuous_artwork_corner_wall']
 tree=BVHTree.FromPolygons([wall.matrix_world@v.co for v in wall.data.vertices],[list(f.vertices)for f in wall.data.polygons]);proof=[];face_keys=[]
 for f in art.data.polygons:
  vs=[art.matrix_world@art.data.vertices[i].co for i in f.vertices];centre=sum(vs,Vector())/len(vs);normal=(vs[1]-vs[0]).cross(vs[2]-vs[0]).normalized();loc,norm,face,dist=tree.find_nearest(centre);face_keys.append(tuple(sorted(tuple(round(x,7)for x in v)for v in vs)))
  proof.append(dict(face=f.index,centre=list(centre),artworkNormal=list(normal),hostNormal=list(norm),nearestHostFace=face,wallGap=dist,normalDotHost=normal.dot(norm),area=f.area))
 write('artwork-surface-proof.json',dict(object=art.name,host=wall.name,faceCount=len(proof),duplicateFaces=len(face_keys)-len(set(face_keys)),minimumGap=min(r['wallGap']for r in proof),maximumGap=max(r['wallGap']for r in proof),minimumNormalDotHost=min(r['normalDotHost']for r in proof),maximumNormalDotHost=max(r['normalDotHost']for r in proof),minimumFaceArea=min(r['area']for r in proof),faces=proof))
 write('hit-object-details.json',details)
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1000;s.render.resolution_y=750;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.filepath=str(OUT/'native-baseline234.png');bpy.ops.render.render(write_still=True)
 bpy.data.objects.remove(c,do_unlink=True);bpy.data.cameras.remove(cd);assert sha(BASE)==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 reopened=dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},materials={m.name:material_fingerprint(m)for m in bpy.data.materials},owners={o.name:sorted(co.name for co in o.users_collection)for o in bpy.data.objects},modifiers={o.name:modifier_state(o)for o in bpy.data.objects},props={o.name:repr(sorted(o.items()))for o in bpy.data.objects},visibility={o.name:o.hide_render for o in bpy.data.objects})
 assert reopened==state
 meta=json.loads((ROOT/'web/tools/building-metadata.json').read_text());rooms={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in meta['spaces']};assert len(rooms)==35 and len(set(n for ns in rooms.values()for n in ns))==1485
 write('protected-rooms.json',rooms);write('verification.json',dict(independentlyReopenedBaseline=True,allSourceFingerprintsMaterialsOwnersModifiersPropertiesVisibilityEqual=True,objects=8582,materials=len(bpy.data.materials),protectedSpaces=35,protectedMembers=1485,baselineSha256=sha(BASE),noNativeFileWritten=True))
def finalize():
 prior=json.loads((ROOT/'result/blender/lrb_envelope_next/audit.json').read_text());proof=json.loads((OUT/'artwork-surface-proof.json').read_text());outward=prior['registeredFacade']['outwardNormal']
 dots=[sum(x*y for x,y in zip(f['artworkNormal'],outward))for f in proof['faces']]
 proof.update(minimumNormalDotRegisteredOutward=min(dots),maximumNormalDotRegisteredOutward=max(dots),normalExplanation='Display normals point outward. Host polygon winding points inward here; opposing host/display normals are not a flipped display.')
 write('artwork-surface-proof.json',proof)
 photo=ROOT/prior['photoSampling']['sourceImage'];assert sha(photo)==prior['photoSampling']['sourceSha256']
 sources=dict(artworkIdentity=prior['artworkIdentity'],existingAudit='result/blender/lrb_envelope_next/audit.json',existingBuilder='web/tools/refine_lrb_envelope.py',photoSampling=prior['photoSampling'],sourceImageSha256=sha(photo),newSourceLookup=False,dateBoundary='Official history article published2018-03-07 and describes2009installation photograph. Archived estate night photograph capture date unknown. This audit does not establish2026daylight/off state, current pattern or live artwork behavior.',limitations=prior['limitations'])
 (DATA/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
 web=json.loads((OUT/'web-reproduction.json').read_text());assert web['sourceModelSha256']==SHA
 webproof=json.loads((OUT/'web-artwork-surface-proof.json').read_text());assert webproof['triangles']==2022 and webproof['duplicateTriangles']==0;assert webproof['minimumNormalDotOutward']>.99999
 assert all('Blue_Rain_photo_blue'in r['hits'][0]['material']for r in webproof['rays']);assert not web['errors']
 renderer={str(p.relative_to(ROOT)):sha(p)for p in [ROOT/'web/src/viewer.js',ROOT/'web/src/surface-materials.js',ROOT/'web/public/models/catalogue.json']}
 catalogue=json.loads((ROOT/'web/public/models/catalogue.json').read_text());asset=next(b for b in catalogue['buildings']if b['code']=='LRB')['detailedExterior']['url'];assetpath=ROOT/'web/public'/asset.split('?')[0].lstrip('/');renderer[str(assetpath.relative_to(ROOT))]=sha(assetpath)
 write('production-source-hashes.json',renderer)
 audit=dict(version=235,status='no-change-diagnostic',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=None,componentSha256=None,addedObjects=[],archivedObjects=[],changedObjects=[],replacementMaterialBindings={},displayOwner='LRB_EXTERIOR',sourceManifest='data/collections/exterior-render235/sources.json',diagnosis='Visible blue speckles are the previously sourced Blue Rain static artwork mesh, not a demonstrated exterior render defect. Reproduced in nativeEEVEE and actual productionCampusViewer with234assets.',nativeRenderer='BLENDER_EEVEE',artworkObject=proof['object'],hostObject=proof['host'],faceCount=proof['faceCount'],duplicateFaces=proof['duplicateFaces'],wallGapMetres=[proof['minimumGap'],proof['maximumGap']],normalDotRegisteredOutward=[min(dots),max(dots)],sourceView=dict(nativeEye=[-2,16,9],nativeTarget=[49,37,.1],webEye=[-2,9,-16],webTarget=[49,.1,-37],verticalFov=62,width=1000,height=750),previews=['native-baseline234.png','web-baseline234.webp'],verification=json.loads((OUT/'verification.json').read_text()),webEvidence='web-reproduction.json',webSurfaceProof='web-artwork-surface-proof.json',webWallGapMetres=[webproof['minimumSignedOutwardDepth'],webproof['maximumSignedOutwardDepth']],webCanvasPixels=web['canvas'],webCssPixels=[1000,750],nativePixelMatch=json.loads((OUT/'native-comparison.json').read_text()),productionSourceHashes=renderer,limitations=['Historic static photographic representation, not current/live Blue Rain content.','Subpixel27×39mmquads can rasterize as sparse dots in daylight wide views. This audit does not calibrate daytime luminous intensity.','No before/after images fabricated: geometry and materials are unchanged; native/web images compare renderers at identical camera.','No glass or facade replacements proposed; no shared viewer/material changes required.'])
 write('audit.json',audit)

if __name__=='__main__':
 try:import bpy
 except ImportError:
  if (OUT/'verification.json').exists()and(OUT/'web-reproduction.json').exists():finalize()
  else:prepare()
 else:diagnose()
