"""Restore the photograph-supported OLD upper parapet, fixed Blender editor run.

The112planning rebuild replaced77's four arched grilles/central stone panel
with five ordinary windows and four small balconies. The completed-project
photograph supports the former composition. Envelope and unseen roof stay put.
"""
from pathlib import Path
import sys,json,hashlib,math
sys.dont_write_bytecode=True
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/old-exterior233';DATA=ROOT/'data/collections/old-exterior233'
BASE=ROOT/'result/blender/LSE_campus_detailed_v232.blend';SHA='1f6ed3da66011e057233697fe8753374a55918d8c4278d56670cbd81192ae2a8'
SOURCES=['OLD194_STONE_OLD_D5_houghton112_entry-attic_stone','OLD_D5_houghton112_entry-attic_blue','GLASS181_OLD_D5_houghton112_entry-attic_glass','OLD_D5_houghton112_balcony_iron']
NAMES=['OLD233_upper_parapet_stone','OLD233_four_arched_parapet_grilles']
ORIGIN=Vector((6.868992805480957,-66.35987854003906,0));U=Vector((.45541495084762573,.8902792930603027,0));N=Vector((.8902792930603027,-.45541495084762573,0))
LEFT=-34.5;RIGHT=-18.295483;CENTER=(LEFT+RIGHT)/2
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,update_scene,set_layer_hidden
from refine_plaza_environment231 import state
from refine_lrb_glazing233 import preserve

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def world(x,d,z):return ORIGIN+U*x+N*d+Vector((0,0,z))
class Batch:
 def __init__(self,name,mat,original):self.name=name;self.mat=mat;self.original=original;self.vertices=[];self.faces=[]
 def box(self,x,d,z,w,t,h):
  start=len(self.vertices);self.vertices.extend(world(x+sx*w/2,d+sd*t/2,z+sz*h/2)for sz in [-1,1]for sd in [-1,1]for sx in [-1,1]);self.faces.extend(tuple(start+i for i in f)for f in [(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)])
 def tube(self,points,r):
  points=[world(*p)for p in points];start=len(self.vertices);sides=8
  for i,p in enumerate(points):
   tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized();side=tangent.cross(N).normalized()
   self.vertices.extend(p+r*(side*math.cos(k*math.tau/sides)+N*math.sin(k*math.tau/sides))for k in range(sides))
  self.faces.extend([tuple(start+k for k in range(sides-1,-1,-1)),tuple(start+(len(points)-1)*sides+k for k in range(sides))])
  for i in range(len(points)-1):
   for k in range(sides):j=(k+1)%sides;self.faces.append((start+i*sides+k,start+i*sides+j,start+(i+1)*sides+j,start+(i+1)*sides+k))
 def finish(self):
  mesh=bpy.data.meshes.new(self.name);mesh.from_pydata(self.vertices,[],self.faces);mesh.materials.append(self.mat);mesh.update()
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);assert bm.calc_volume(signed=True)>0;bm.to_mesh(mesh);bm.free();mesh.update()
  for name in ['MetricUV','StoneFinish194']:
   uv=mesh.uv_layers.new(name=name)
   for p in mesh.polygons:
    for li in p.loop_indices:
     v=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(v.dot(U)/4.5,v.z/4.5)if name=='StoneFinish194'else(v.dot(U),v.z)
  o=bpy.data.objects.new(self.name,mesh);bpy.data.collections['OLD_EXTERIOR'].objects.link(o);o['originalObject']=self.original;o['destinationCollection']='OLD_EXTERIOR';o['buildingCode']='OLD';o['scope']='Four photo-supported arched parapet grilles and broad central stone panel; envelope and all lower exterior retained';o['estimatedDimensions']=True
  return o

def source_refs():
 refs=[dict(path='data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_06.jpg',url='https://webbyates.com/projects/the-old-building/',date='2024completion;photograph capture date unknown',scope='Completed Houghton facade:four low arched grille openings and broad central stone panel above main cornice,below lower dormers.'),dict(path='data/collections/old-exterior233/210224_N88295_website-scaled.jpg',url='https://i0.wp.com/www.hawkinsbrown.com/wp-content/uploads/2025/06/210224_N88295_website-scaled.jpg?fit=1200%2C1800&ssl=1',parentUrl='https://www.hawkinsbrown.com/projects/lse-old-building/',date='2024completed project,asset URL2025/06;capture date not asserted',scope='Architect official publication of the same project photograph corroborates provenance;not an independent dated survey or2026condition proof.'),dict(path='data/collections/old-roof-2024/existing-south.pdf',url='https://idoxpa.westminster.gov.uk/online-applications/files/97633D2FC04D7E918333D7F9B365101F/pdf/22_08664_FULL-EXISTING___STRIP_OUT_SOUTH_ELEVATION-7612991.pdf',date='07December2022,P1,LSEOLD-HBA-V1-XX-DR-A-080201',scope='Planning existing drawing retains six dormer columns;left column hidden in photograph cannot be deleted. Ordinary attic-window/balcony depiction is not adopted over built photograph.')]
 for r in refs:r['sha256']=sha(ROOT/r['path'])
 write(DATA/'sources.json',dict(references=refs,reviewDate='2026-10-17',boundedOfficialLookup=dict(searchBatches=1,officialPage='https://www.hawkinsbrown.com/projects/lse-old-building/',projectStatus='Complete2024',assetsDownloaded=2,assetsRetained=1,interiorLeadUnused='Downloaded interior thumbnail removed after irrelevance check;not a model source'),current2026ConditionConfirmed=False,sourcePhotosNotUsedAsTextures=True))
 return refs

def render(sources,added):
 s=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=s;c=bpy.data.objects.new('OLD233_REVIEW_CAMERA',bpy.data.cameras.new('OLD233_REVIEW_CAMERA'));s.collection.objects.link(c);s.camera=c;c.data.clip_end=1500;c.data.sensor_fit='VERTICAL'
 old_world=s.world;w=old_world.copy();w.name='OLD233_REVIEW_WORLD';s.world=w;bg=next(n for n in w.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[1].default_value=.65;env=w.node_tree.nodes.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(ROOT/'web/public/environment/kloppenheim-daylight-1k.hdr'),check_existing=True);w.node_tree.links.new(env.outputs['Color'],bg.inputs[0])
 s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True;s.render.resolution_x=1100;s.render.resolution_y=825;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
 focus=world(CENTER,0,14);eye=focus+N*14+U*.15
 gallery=json.loads((ROOT/'web/tools/gallery-views.json').read_text());upper_focus=world(CENTER,0,20.8);upper_eye=upper_focus+N*13+Vector((0,0,2.0));upper=dict(position=[upper_eye.x,upper_eye.z,-upper_eye.y],target=[upper_focus.x,upper_focus.z,-upper_focus.y],fov=65)
 views=[dict(name='whole-Houghton',position=[eye.x,eye.z,-eye.y],target=[focus.x,focus.z,-focus.y],fov=98),dict(name='upper-parapet',**upper)]
 active=sorted(o.name for o in s.objects if not o.hide_render and o not in sources+added+[c])
 for v in views:
  eye=Vector((v['position'][0],-v['position'][2],v['position'][1]));target=Vector((v['target'][0],-v['target'][2],v['target'][1]));c.location=eye;c.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler();c.data.lens=c.data.sensor_height/(2*math.tan(math.radians(v['fov'])/2))
  for phase in ['before','after']:
   for o in sources:o.hide_render=phase=='after';set_layer_hidden(o,phase=='after')
   for o in added:o.hide_render=phase=='before';set_layer_hidden(o,phase=='before')
   update_scene();s.render.filepath=str(OUT/(phase+'-'+v['name']+'.png'))
   if phase=='after' or not Path(s.render.filepath).exists():bpy.ops.render.render(write_still=True)
 for o in sources:o.hide_render=False;set_layer_hidden(o,False)
 for o in added:o.hide_render=False;set_layer_hidden(o,False)
 s.world=old_world;bpy.data.objects.remove(c,do_unlink=True);bpy.data.cameras.remove(bpy.data.cameras['OLD233_REVIEW_CAMERA']);bpy.data.worlds.remove(w)
 return views,dict(allNativeBuildingsCrownsAndExistingPublicSpacesRetained=True,activeContextObjects=len(active),activeContextNamesSha256=hashlib.sha256('\n'.join(active).encode()).hexdigest(),lighting='Same full native context,HDR0.65,native lights,AgX,Cycles12samples,1100x825')

def build():
 OUT.mkdir(parents=True,exist_ok=True);DATA.mkdir(parents=True,exist_ok=True);assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();before=state();assert len(before['materials'])==2299
 sources=[bpy.data.objects[n]for n in SOURCES];assert all(not o.hide_render for o in sources)
 stone=Batch(NAMES[0],sources[0].data.materials[0],SOURCES[0]);blue=Batch(NAMES[1],sources[1].data.materials[0],SOURCES[1])
 width=RIGHT-LEFT;scale=width/17.9;grille_bottom=18.98;grille_top=19.66
 # Preserve the accepted complete upper-band width/top/bottom and front plane.
 # Four shallow low grilles replace the ordinary5-window visual rhythm.
 a,b=16.895,20.225;depth=-.46;thickness=.30
 stone.box(CENTER,depth,(a+grille_bottom)/2,width,thickness,grille_bottom-a)
 stone.box(CENTER,depth,(grille_top+b)/2,width,thickness,b-grille_top)
 piers=[(-8.65,.60),(-5.20,.44),(0,3.90),(5.20,.44),(8.65,.60)]
 for x,w in piers:stone.box(CENTER+x*scale,depth,(grille_bottom+grille_top)/2,w*scale,thickness,grille_top-grille_bottom)
 openings=[(-8.35,-5.42),(-4.98,-1.95),(1.95,4.98),(5.42,8.35)];records=[]
 for left,right in openings:
  lo=CENTER+left*scale;hi=CENTER+right*scale;pitch=(hi-lo)/4;d=depth+thickness/2+.012
  for z in [grille_bottom+.025,grille_top-.025]:blue.box((lo+hi)/2,d,z,hi-lo,.035,.032)
  for x in [lo+.016,hi-.016]:blue.box(x,d,(grille_bottom+grille_top)/2,.032,.035,grille_top-grille_bottom)
  for i in range(4):
   x=lo+(i+.5)*pitch
   blue.tube([(x+pitch*.49*math.cos(k*math.pi/20),d,grille_bottom+.045+(grille_top-grille_bottom-.09)*math.sin(k*math.pi/20))for k in range(21)],.015)
   for sign in [-1,1]:blue.tube([(x-sign*pitch*.41,d+.008,grille_bottom+.045),(x+sign*pitch*.32,d+.008,grille_top-.10)],.011)
  records.append(dict(x=[lo,hi],z=[grille_bottom,grille_top],archRepeats=4,dimensionsEstimated=True))
 added=[stone.finish(),blue.finish()];bindings={o.name:[m.name for m in o.data.materials]for o in added}
 views=[];context={};verification=preserve(before,NAMES,[])
 component=OUT/'component.blend';fingerprints={o.name:object_fingerprint(o)for o in added};bpy.data.libraries.write(str(component),set(added),fake_user=True)
 report=dict(version=233,building='OLD',status='bounded-photo-guided-upper-parapet-candidate',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,sourceModelSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection='OLD_EXTERIOR',destinationCollection='OLD_EXTERIOR',displayOwner='OLD_EXTERIOR',addedObjects=NAMES,ownedObjects=NAMES,archivedObjects=SOURCES,changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,verification=verification,sourceManifest=str((DATA/'sources.json').relative_to(ROOT)),references=source_refs(),diagnosis='112planning rebuild archived77photo-based four arched screens/central panel and introduced five ordinary attic windows/four small balconies;2024built-project photographs support restoring the grille composition.',registration=dict(retainedWidth=width,retainedZ=[a,b],frontPlane=depth+thickness/2,openings=records,centralStonePanelWidth=3.90*scale,allDimensionsInheritedOrEstimated=True),retained=['218portal leaves,seams,glass,hardware and four-step approach','217Houghton blue window optics and divisions','218Final Sale sculpture','12mansard openings,including obscured leftmost column supported by2022drawing','209continuous mansard brick,168bluejambs,156blue horizontal caps','All main cornice,lower wall apertures,street wings,roof mass,public interiors and independent spaces'],productionVisibility=context,views=views,previews=[phase+'-'+v['name']+'.png'for v in views for phase in ['before','after']],limitations=['Low grille heights,stone band thicknesses,4arch repeats,bar radii and panel widths are photographic estimates,not measured fabrication.','Existing upper-band envelope and main cornice height/setback remain inherited2024planning estimates;this candidate does not certify their complete as-built registration.','The2024completed-project photograph has unknown capture date;2025asset upload and2026review do not establish current2026condition.','No new room,backboard,hidden roof/elevation or missing sixth dormer is fabricated;only this visible upper-band composition is replaced.'])
 write(OUT/'audit.json',report)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(NAMES)
 for o in dst.objects:
  bpy.data.collections['OLD_EXTERIOR'].objects.link(o)
  for i,name in enumerate(bindings[o.name]):o.data.materials[i]=bpy.data.materials[name]
  assert object_fingerprint(o)==fingerprints[o.name],o.name
 for m in list(bpy.data.materials):
  if m.name not in before['materials']:assert m.users<=int(m.use_fake_user);bpy.data.materials.remove(m)
 report['verification'].update(preserve(before,NAMES,[]));report['verification']['componentIndependentlyAppendedAndVerified']=True
 views,context=render([bpy.data.objects[n]for n in SOURCES],list(dst.objects));report['views']=views;report['productionVisibility']=context;report['previews']=[phase+'-'+v['name']+'.png'for v in views for phase in ['before','after']];report['verification'].update(preserve(before,NAMES,[]));report['verification']['comparisonRenderedAfterSavedComponentReappend']=True;report['verification']['originalMaterialsVerified']=2299;report['verification']['addedMaterials']=0;report['verification']['replacementMeshesClosedManifoldAtBuild']=True;report['verification']['replacementMeshNormalsRecalculatedAndPositiveAggregateVolumeAtBuild']=True
 write(OUT/'audit.json',report);write(OUT/'verification.json',report['verification'])
 for p in OUT.glob('*.blend1'):p.unlink()
 print('OLD233_COMPONENT_READY',sha(component),flush=True)
if __name__=='__main__':build()
