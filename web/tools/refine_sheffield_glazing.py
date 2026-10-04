"""Inspect and refine attributed Sheffield glazing without invented interior geometry.
Constant Blender configuration; independent component output only.
"""
from pathlib import Path
import array,hashlib,json,math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/shf_glazing149';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v148.blend';PREFIX='SHF_NEXT_GLAZING149_'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
def open_source():
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 old=json.loads((OUT/'audit.json').read_text())if(OUT/'audit.json').exists()else None
 for o in list(bpy.data.objects):
  if o.name.startswith(PREFIX):bpy.data.objects.remove(o,do_unlink=True)
 if old:
  for name in old['archivedObjects']:
   o=bpy.data.objects[name];o.hide_render,o.hide_viewport=old['originalVisibility'][name][:2];o.hide_set(old['originalVisibility'][name][2])
 return bpy.context.scene,bpy.data.collections['SHF_EXTERIOR']
scene,col=open_source();sha=hashlib.sha256(BASE.read_bytes()).hexdigest()
if BASE.stem.endswith('v148'):assert sha=='536b63660f8542ecae569523ef8beb2c45013068487f2aaa160820225e7076f2'
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,width in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   values=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in o.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()

original={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
if BASE.stem.endswith('v148'):assert len(original)==5843
frame=json.loads((ROOT/'result/blender/shf_exterior148/audit.json').read_text())['registration'];O,U,N=[Vector(frame[k])for k in ['origin','right','outward']]
def point(x,d,z):return O+U*x+N*d+Vector((0,0,z))
def local(p):q=p-O;return q.dot(U),q.dot(N),p.z
SOURCES=['SHF_V50_window_glass_glass','SHF_NEXT_entry_glass_glass','SHF_V50_door_transom_glass_glass','SHF_V50_dormer_glass_glass']
def parts(o):
 adj={v.index:set()for v in o.data.vertices}
 for e in o.data.edges:
  a,b=e.vertices;adj[a].add(b);adj[b].add(a)
 seen=set();result=[]
 for seed in adj:
  if seed in seen:continue
  stack=[seed];seen.add(seed);group=[]
  while stack:
   k=stack.pop();group.append(k)
   for q in adj[k]:
    if q not in seen:seen.add(q);stack.append(q)
  result.append(group)
 return result

samples=[];glass_materials={}
for name in SOURCES:
 o=bpy.data.objects[name];assert not o.hide_render
 for k,part in enumerate(parts(o)):
  pts=[o.matrix_world@o.data.vertices[i].co for i in part];c=sum(pts,Vector())/len(pts);x,d,z=local(c)
  for dx,dz in ([(-.11,.04),(.11,.08)]if name=='SHF_V50_door_transom_glass_glass'else[(-.11,.08),(.11,-.08)]):samples.append({'source':name,'pane':k,'point':list(c+U*dx+Vector((0,0,dz))),'localCentre':[x,d,z]})
 node=o.data.materials[0].node_tree.nodes['Principled BSDF'];glass_materials[name]={'material':o.data.materials[0].name,'baseColor':list(node.inputs['Base Color'].default_value),'alpha':float(node.inputs['Alpha'].default_value),'transmission':float(node.inputs['Transmission Weight'].default_value),'roughness':float(node.inputs['Roughness'].default_value)}
def trees():
 allowed=set()
 def walk(c,hidden=False):
  hidden=hidden or c.hide_render
  if not hidden:allowed.update(o.name for o in c.objects)
  for child in c.children:walk(child,hidden)
 walk(scene.collection)
 return[(o.name,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons]))for o in scene.objects if o.type=='MESH'and not o.hide_render and o.name in allowed and len(o.data.polygons)]
def hit(start,direction,maximum,excluded=None):
 hits=[]
 for name,t in ACTIVE_TREES:
  if name in(excluded or []):continue
  r=t.ray_cast(start,direction,maximum)
  if r[0]is not None:hits.append((r[3],name,list(r[0])))
 return min(hits)if hits else None
ACTIVE_TREES=trees();before=[]
for s in samples:
 p=Vector(s['point']);front=hit(p+N*.9,-N,1.2);back=hit(p-N*.002,-N,3,[s['source']]);assert front and front[1]==s['source'],(s,front)
 before.append({**s,'firstSurface':front[1],'behind':back})
(OUT/'nearfield-before.json').write_text(json.dumps({'glassMaterials':glass_materials,'checks':before},indent=2))
owned=[];archives=[];changes=[];mapping={};optics=[]
# Photo-defined street panes receive restrained transparency, retaining source tint.
for name in SOURCES:
 source=bpy.data.objects[name];copy=source.copy();copy.data=source.data.copy();copy.name=PREFIX+name.removeprefix('SHF_');copy.data.name=copy.name;col.objects.link(copy);old=source.data.materials[0];mat=old.copy();mat.name=PREFIX+name.removeprefix('SHF_')+'_material';node=mat.node_tree.nodes['Principled BSDF'];node.inputs['Transmission Weight'].default_value=.32;node.inputs['Alpha'].default_value=.84;node.inputs['Roughness'].default_value=.18;node.inputs['IOR'].default_value=1.45;node.inputs['Metallic'].default_value=0;mat['webOpacity']=.84
 if name==SOURCES[-1]:
  # Leftmost scaffold-obscured dormer retains its existing opaque material.
  copy.data.materials.append(mat)
  for polygon in copy.data.polygons:
   coords=[local(copy.matrix_world@copy.data.vertices[k].co)for k in polygon.vertices];x=sum(q[0]for q in coords)/len(coords);bay=min(range(4),key=lambda i:abs(frame['centres'][i]-x));polygon.material_index=0 if bay==0 else 1
 else:copy.data.materials[0]=mat
 source.hide_render=True;source.hide_set(True);owned.append(copy);archives.append(name);mapping[name]=copy.name;changes.append({'source':name,'owned':copy.name,'action':'Retain source pane geometry, UV and base colour; measured appearance not claimed. Apply estimated reflection/transmission only to attributed panes; dormerbay0 remainsopaque.'})
 optics.append({'source':name,'owned':copy.name,'sourceMaterial':old.name,'newMaterial':mat.name,'original':glass_materials[name],'new':{'transmission':.32,'alpha':.84,'roughness':.18,'ior':1.45,'metallic':0,'webOpacity':.84},'opaqueExcludedDormerBay':0 if name==SOURCES[-1]else None})
# The three photographed dormers have actual glazed openings. The inherited
# continuous mansard crosses their existing cheek volume, sealing the apertures.
# Subtract only each pane's projection within those existing cheek depth limits.
roof_source=bpy.data.objects['SHF_V50_mansard_roof'];roof=roof_source.copy();roof.name=PREFIX+'mansard_registered_dormer_apertures';col.objects.link(roof)
ROOF_HOLES=[{'bay':i,'x':[frame['centres'][i]-1.075,frame['centres'][i]+1.075],'z':[17.13,18.17],'depth':[-1.07,.05]}for i in [1,2,3]]
old_uv=roof_source.data.uv_layers.active;output=[];removed_areas=[]
def clip(poly,axis,value,greater):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  av=local(a[0])[axis];bv=local(b[0])[axis];ia=av>=value-1e-9 if greater else av<=value+1e-9;ib=bv>=value-1e-9 if greater else bv<=value+1e-9
  if ia:result.append(a)
  if ia!=ib:
   f=(value-av)/(bv-av);result.append((a[0].lerp(b[0],f),a[1].lerp(b[1],f)))
 return result
for f in roof_source.data.polygons:
 polygon=[(roof_source.matrix_world@roof_source.data.vertices[roof_source.data.loops[k].vertex_index].co,Vector(old_uv.data[k].uv))for k in f.loop_indices];pieces=[polygon]
 for h in ROOF_HOLES:
  updated=[]
  planes=[(0,h['x'][0],True),(0,h['x'][1],False),(2,h['z'][0],True),(2,h['z'][1],False),(1,h['depth'][0],True),(1,h['depth'][1],False)]
  for piece in pieces:
   inside=piece
   for axis,value,greater in planes:
    inside=clip(inside,axis,value,greater)
    if len(inside)<3:break
   if len(inside)<3:
    updated.append(piece);continue
   current=piece
   for axis,value,greater in planes:
    outside=clip(current,axis,value,not greater)
    if len(outside)>=3:updated.append(outside)
    current=clip(current,axis,value,greater)
   removed_areas.append({'sourcePolygon':f.index,'bay':h['bay'],'projectedWorldVertices':[list(p[0])for p in current]})
  pieces=updated
 output.extend((piece,f.material_index)for piece in pieces)
assert {p['bay']for p in removed_areas}=={1,2,3}
vs=[];fs=[];uvs=[];slots=[]
for poly,slot in output:
 if len(poly)<3:continue
 s=len(vs);vs.extend(roof_source.matrix_world.inverted()@p[0]for p in poly);fs.append(tuple(s+k for k in range(len(poly))));uvs.append([p[1]for p in poly]);slots.append(slot)
me=bpy.data.meshes.new(roof.name);me.from_pydata(vs,[],fs);me.update()
for mat in roof_source.data.materials:me.materials.append(mat)
uv=me.uv_layers.new(name=old_uv.name)
for f,coords,slot in zip(me.polygons,uvs,slots):
 f.material_index=slot
 for k,v in zip(f.loop_indices,coords):uv.data[k].uv=v
roof.data=me;roof_source.hide_render=True;roof_source.hide_set(True);owned.append(roof);archives.append(roof_source.name);changes.append({'source':roof_source.name,'owned':roof.name,'action':'Only subtract3attributedpaneprismsfromcontinuousmansard withinexistingdormercheekdepth; retainotherroofandleftdormerbacksurface withsourceUVinterpolation.'})
OWNED=[o.name for o in owned]
def geometry_uv_digest(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 for data,field,kind,width in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1)]:
  v=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,v);h.update(v.tobytes())
 for uv in o.data.uv_layers:
  v=array.array('f',[0])*(len(uv.data)*2);uv.data.foreach_get('uv',v);h.update(v.tobytes())
 return h.hexdigest()
def check():
 global ACTIVE_TREES
 ACTIVE_TREES=trees();rows=[]
 for s in samples:
  p=Vector(s['point']);expected=mapping[s['source']];first=hit(p+N*.9,-N,1.2);back=hit(p-N*.002,-N,3,[expected]);assert first and first[1]==expected,(s,first,expected)
  unknown=s['source']==SOURCES[-1]and s['pane']==0
  if unknown:assert back and back[1]==PREFIX+'mansard_registered_dormer_apertures'
  else:assert back is None,(s,back)
  rows.append({**s,'kind':'unknown-left-dormer-retained'if unknown else'glass','firstSurface':first[1],'firstObject':first[1],'expected':expected,'behind':back,'opaqueCapRemoved':s['source']==SOURCES[-1]and not unknown,'noOpaqueNearfieldCap':not back})
 # Probe all six light columns above and below the retained148transom in each
 # registered dormer, so central-points alone cannot mask remaining roof caps.
 for bay in [1,2,3]:
  x=frame['centres'][bay]
  for light in range(6):
   for dz in [-.27,.27]:
    p=point(x-1.125+2.25*(light+.5)/6,-.125,17.65+dz);first=hit(p+N*.9,-N,1.2);back=hit(p-N*.002,-N,3,[mapping[SOURCES[-1]]]);assert first and first[1]==mapping[SOURCES[-1]],(bay,light,dz,first)
    assert back is None or(back[1]==PREFIX+'mansard_registered_dormer_apertures'and local(Vector(back[2]))[1]<-1.08),(bay,light,dz,back)
    rows.append({'kind':'registered-dormer-light','bay':bay,'light':light,'point':list(p),'firstSurface':first[1],'firstObject':first[1],'expected':mapping[SOURCES[-1]],'behind':back,'noOpaqueNearfieldCap':True,'clearanceScope':'existingdormercheekvolume; anyroofhitdeeperthan1.08mbehindfacaderetained'})
  start=point(x+(-1.45 if bay==3 else 1.45),1,17.65);first=hit(start,-N,2);assert first and first[1]==PREFIX+'mansard_registered_dormer_apertures',(bay,first)
  rows.append({'kind':'roof-outside-aperture-preserved','bay':bay,'point':list(start),'firstSurface':first[1],'firstObject':first[1],'expected':PREFIX+'mansard_registered_dormer_apertures'})
 return rows
checks=check();assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items())
for n in SOURCES:assert geometry_uv_digest(bpy.data.objects[n])==geometry_uv_digest(bpy.data.objects[mapping[n]])
component=OUT/'sheffield-glazing-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
audit={'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':sha,'originalObjectCount':len(original),'originalFingerprints':original,'originalVisibility':visibility,'ownedObjects':OWNED,'archivedObjects':archives,'changes':changes,'sources':[{'path':'data/建筑图片/SHF_Sheffield Street/01_建筑实拍/exteriors_lse_estate_027.jpg','url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate','captureDate':'unknown','supports':'Mainfrontageclearwindowglassshowssky/treesandinterior;3rightdormersare2row6lightactualglasswindows withwhitesides,notpaintedroofpanels.'},{'path':'data/建筑图片/SHF_Sheffield Street/01_建筑实拍/small_round5_SHF_handbook-000.png','url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf','publicationEdition':'2025/26','captureDate':'unknown','supports':'Actualstreet-levelglazedtimberentry,doortransomandpairedwhiteframedwindows. Roofnotpictured.'}],'glazingOptics':optics,'roofRegistration':{'frame':frame,'holes':ROOF_HOLES,'removedIntersections':removed_areas,'scope':'Only3known glassopeningprisms intersectingexistingdormercheekextent. Allunseenleftdormerandroofoutsideprisms retained. Holedepth/width derivefromnative50dormercheekandglassdimensions,notnewsite measurement.'},'beforeFirstSurfaceChecks':before,'firstSurfaceChecks':checks,'glassPaneCount':25,'unknownDormerPanePreserved':1,'scope':'22main/entryglasspanes and3fullypicturedroofglasspanes; unseenleftdormerandsecondary/rearfacadeglassremainopaque. SourceglassUV/matrix/basecolours unchanged. No inventedinteriororopaque backing plate.','limitations':['Transmission.32,alpha/webOpacity.84,roughness.18andIOR1.45arevisualestimates,notmeasuredopticalspecifications.','Photographdateunknownandhandbookeditiondoesnotdatephotography.','Fullinsidevolumesunregistered;3mrayclearanceisgeometryverification,notclaimofcompleteinterior.','Retainedroofdimensions18.6mheight,mansarddepth/dormerpositionareestimates. Onlyphoto-supported3windowclearancecorrected.','Doortransomlowerprobeat2.84mhitsexistingentryglazingframe; actualtransomchecksusehigherclear2.96/3.00mpositionsinstead ofdeletingcorrectjoinery.']}
(OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
scene,col=open_source()
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(OWNED)
for o in dst.objects:
 col.objects.link(o)
 for slot in o.material_slots:
  m=slot.material
  if m and'.'in m.name and m.name.rsplit('.',1)[1].isdigit():
   canonical=bpy.data.materials.get(m.name.rsplit('.',1)[0])
   if canonical:slot.material=canonical
for n in archives:bpy.data.objects[n].hide_render=True;bpy.data.objects[n].hide_set(True)
reopened=check();assert reopened==checks;assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all([bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==v for n,v in visibility.items()if n not in archives)
for n in SOURCES:assert geometry_uv_digest(bpy.data.objects[n])==geometry_uv_digest(bpy.data.objects[mapping[n]])
optical_checks=[]
for n in SOURCES:
 obj=bpy.data.objects[mapping[n]];mat=obj.data.materials[-1]if n==SOURCES[-1]else obj.data.materials[0];node=mat.node_tree.nodes['Principled BSDF'];assert abs(node.inputs['Transmission Weight'].default_value-.32)<1e-6 and abs(node.inputs['Alpha'].default_value-.84)<1e-6 and abs(mat['webOpacity']-.84)<1e-6;assert list(node.inputs['Base Color'].default_value)==glass_materials[n]['baseColor'];optical_checks.append({'object':obj.name,'material':mat.name,'webOpacity':mat['webOpacity']})
left=bpy.data.objects[mapping[SOURCES[-1]]];assert sum(p.material_index==0 for p in left.data.polygons)==6;node=left.data.materials[0].node_tree.nodes['Principled BSDF'];assert node.inputs['Alpha'].default_value==1 and node.inputs['Transmission Weight'].default_value==0
proof={'baselineSha256':sha,'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'originalObjectCount':len(original),'unrelatedVisibilityPreserved':True,'fullModelSaved':False,'checkCount':len(reopened),'firstSurfaceChecks':reopened,'glazingGeometryUVAndSourceColorsPreserved':True,'opaqueLeftDormerRetained':True,'opticalChecks':optical_checks,'registeredRoofWindows':3}
visible={o.name for o in col.all_objects}
for o in scene.objects:
 if o.type in ['MESH','FONT','CURVE']and o.name not in visible:o.hide_render=True
focus=point(frame['frontLength']/2,0,9.5);position=focus+N*44+U*7+Vector((0,0,9));cd=bpy.data.cameras.new(PREFIX+'review');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cam.location=position;cam.rotation_euler=(focus-position).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=25;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=1300;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-glazing-envelope.png');bpy.ops.render.render(write_still=True)
proof['camera']={'position':list(position),'target':list(focus),'orthoScale':25};proof['nativePreview']=str(OUT/'reloaded-glazing-envelope.png');(OUT/'verification.json').write_text(json.dumps(proof,indent=2));print('SHF149_VERIFIED',len(original),len(owned),len(reopened));bpy.ops.wm.quit_blender()
