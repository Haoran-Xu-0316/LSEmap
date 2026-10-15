"""Inspect and refine only photograph-supported CKK exterior finish estimates.

The complete218 native remains read-only. Configuration is fixed for Blender's
Text Editor; geometry and existing materials are never edited in place.
"""
from pathlib import Path
import hashlib,json,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v218.blend'
SHA='d57142ea7dce27ea052bbd508f63dcd8c15136faccc132ac4f5915dff64fe27d'
OUT=ROOT/'result/blender/ckk-exterior219'
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints
from refine_portsmouth_exterior207 import material_fingerprint

def update():
 for scene in bpy.data.scenes:
  for layer in scene.view_layers:layer.update()

def metrics(material):
 shader=next((n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)if material.node_tree else None
 return dict(name=material.name,color=list(shader.inputs['Base Color'].default_value)if shader else None,linked=shader.inputs['Base Color'].is_linked if shader else None,roughness=shader.inputs['Roughness'].default_value if shader else None,metallic=shader.inputs['Metallic'].default_value if shader else None,alpha=shader.inputs['Alpha'].default_value if shader else None,transmission=shader.inputs['Transmission Weight'].default_value if shader else None,properties=dict(material.items()))

def inspect():
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
 expected=accepted_fingerprints(ROOT/'result/blender/stage218',SHA)
 actual={o.name:object_fingerprint(o)for o in bpy.data.objects}
 assert actual==expected
 rows=[]
 for obj in bpy.data.collections['CKK_EXTERIOR'].all_objects:
  if obj.type!='MESH'or obj.hide_render:continue
  bounds=[obj.matrix_world@Vector(v)for v in obj.bound_box]
  rows.append(dict(name=obj.name,materials=[metrics(m)for m in obj.data.materials if m],vertices=len(obj.data.vertices),faces=len(obj.data.polygons),low=[min(p[i]for p in bounds)for i in range(3)],high=[max(p[i]for p in bounds)for i in range(3)]))
 (OUT/'inspection.json').write_text(json.dumps(dict(baselineSha256=SHA,acceptedObjectCount=len(actual),originalMaterialCount=len(bpy.data.materials),visibleObjects=rows),indent=2)+'\n')
 print('CKK219_INSPECTED',len(actual),len(rows),len(bpy.data.materials),flush=True)


GLASS_SOURCES=[
 'GLASS181_CKK_NEXT_ENVELOPE_recessed_glass',
 'CKK_NEXT_FRONTAGE154_semicircular_glass',
 'GLASS181_CKK_V32_dormer_glazing',
]
FRAME_SOURCES=[
 'CKK_NEXT_ENVELOPE_window_frames',
 'CKK_NEXT_ENVELOPE_centre_mullions',
 'CKK_NEXT_FRONTAGE154_lowered_arch_frame',
]
NORMAL=Vector((.9271838665008545,.37460657954216003,0))
AXIS=Vector((-NORMAL.y,NORMAL.x,0))
ORIGIN=Vector((-110.49102020263672,77.56015014648438,0))

def geometry_state(obj):
 import array
 digest=hashlib.sha256()
 for data,key,kind,count in [(obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)]:
  values=array.array(kind,[0])*(len(data)*count);data.foreach_get(key,values);digest.update(values.tobytes())
 uvs={}
 for layer in obj.data.uv_layers:
  values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);uvs[layer.name]=hashlib.sha256(values.tobytes()).hexdigest()
 return dict(geometry=digest.hexdigest(),uv=uvs,transform=[list(row)for row in obj.matrix_world])

def modifiers(obj):
 rows=[]
 for modifier in obj.modifiers:
  values={}
  for prop in modifier.bl_rna.properties:
   if prop.identifier=='rna_type':continue
   value=getattr(modifier,prop.identifier,None)
   if isinstance(value,(str,int,float,bool))or value is None:values[prop.identifier]=value
   elif isinstance(value,bpy.types.ID):values[prop.identifier]=value.name
   else:
    try:values[prop.identifier]=list(value)
    except TypeError:pass
  rows.append(dict(name=modifier.name,type=modifier.type,values=values))
 return hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()

def backings():
 from mathutils.bvhtree import BVHTree
 vertices=[];faces=[];owners=[]
 for obj in bpy.data.collections['CKK_EXTERIOR'].all_objects:
  if obj.hide_render or obj.type!='MESH':continue
  if any(k in obj.name.lower()for k in ['frame','mullion','sill','reveal']):continue
  if any(any(k in m.name.lower()for k in ['glass','glazing'])for m in obj.data.materials if m):continue
  start=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
  faces.extend(tuple(start+i for i in face.vertices)for face in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
 tree=BVHTree.FromPolygons(vertices,faces);rows=[]
 for name in GLASS_SOURCES:
  obj=bpy.data.objects[name]
  for face in obj.data.polygons:
   normal=(obj.matrix_world.to_3x3().inverted().transposed()@face.normal).normalized()
   if normal.dot(NORMAL)<.98:continue
   points=[obj.matrix_world@obj.data.vertices[i].co for i in face.vertices]
   centre=sum(points,Vector())/len(points)
   span=max(p.dot(AXIS)for p in points)-min(p.dot(AXIS)for p in points)
   # Rectangular two-light windows are sampled inside the lights, away from
   # their central mullion; triangular fanlight facets keep their centroids.
   offsets=[-.23*span,.23*span]if len(points)==4 and span>.4 else[0]
   for offset in offsets:
    point=centre+AXIS*offset
    hit=tree.ray_cast(point-normal*.015,-normal,45)
    distance=hit[3]+.015 if hit[2]is not None else None
    rows.append(dict(object=name,face=face.index,centre=list(point),lateralOffset=offset,opaqueObject=owners[hit[2]]if hit[2]is not None else None,distanceMetres=distance,nearBacking=distance is not None and distance<=1.5))
 assert rows
 return dict(samples=len(rows),nearBackingSamples=sum(row['nearBacking']for row in rows),rows=rows,method='Front-facing rectangular panes sampled inside each light, away from central mullions; fanlight facets use centroids. All glazing and frame/mullion/sill/reveal batches excluded from opaque ray tree. Near backing <=1.5m is not proof of a complete room.',decision='Retain original alpha1/transmission0 proxies on all reviewed historic frontage and dormers. Existing rooftop and atrium optics remain unchanged.')

def render_views(label):
 scene=bpy.data.scenes.new('CKK219_REVIEW_'+label);scene.collection.children.link(bpy.data.collections['CKK_EXTERIOR'])
 bpy.context.window.scene=scene
 world=bpy.data.worlds.new(scene.name);world.use_nodes=True
 world.node_tree.nodes['Background'].inputs['Color'].default_value=(.82,.85,.88,1)
 world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7;scene.world=world
 light=bpy.data.lights.new(scene.name+'_sun','SUN');light.energy=2;light.angle=.13
 sun=bpy.data.objects.new(light.name,light);scene.collection.objects.link(sun)
 sun.rotation_euler=(-NORMAL+AXIS*.45+Vector((0,0,-1.1))).to_track_quat('-Z','Y').to_euler()
 data=bpy.data.cameras.new(scene.name+'_camera');camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera);scene.camera=camera
 data.type='ORTHO';data.clip_end=500
 scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=32
 scene.render.resolution_x=1000;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
 scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
 target=ORIGIN+NORMAL*21+Vector((0,0,15.8));cameras=[]
 for name,position,scale in [('front',target+NORMAL*80+Vector((0,0,1.5)),37),('oblique',target+NORMAL*75+AXIS*26+Vector((0,0,10)),40)]:
  camera.location=position;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
  scene.render.filepath=str(OUT/(label+'-'+name+'.png'));bpy.ops.render.render(write_still=True,scene=scene.name)
  cameras.append(dict(view=name,target=list(target),position=list(position),orthoScale=scale))
 bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 for obj in [camera,sun]:bpy.data.objects.remove(obj,do_unlink=True)
 bpy.data.scenes.remove(scene);bpy.data.worlds.remove(world);bpy.data.cameras.remove(data);bpy.data.lights.remove(light);update()
 return cameras

def run():
 OUT.mkdir(parents=True,exist_ok=True);inspect()
 originals={o.name:object_fingerprint(o)for o in bpy.data.objects}
 original_modifiers={o.name:modifiers(o)for o in bpy.data.objects}
 material_states={m.name:material_fingerprint(m)for m in bpy.data.materials}
 membership={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects}
 visibility={o.name:o.hide_render for o in bpy.data.objects}
 metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
 spaces={s['collection']:sorted(o.name for o in bpy.data.collections[s['collection']].all_objects)for s in metadata['spaces']}
 protected={name for names in spaces.values()for name in names}
 assert len(spaces)==18 and len(protected)==623 and not protected.intersection(GLASS_SOURCES+FRAME_SOURCES)
 before_geometry={name:geometry_state(bpy.data.objects[name])for name in GLASS_SOURCES+FRAME_SOURCES}
 rays=backings();(OUT/'backing-rays.json').write_text(json.dumps(rays,indent=2)+'\n')
 cameras=render_views('before')
 owned=[];bindings={};materials={};records=[]
 for source_name in GLASS_SOURCES+FRAME_SOURCES:
  source=bpy.data.objects[source_name];assert not source.hide_render
  clone=source.copy();clone.data=source.data.copy();clone.name='CKK219_'+source_name;clone.data.name=clone.name
  clone['originalObject']=source_name;clone['destinationCollection']='CKK_EXTERIOR';clone['webGeometrySource']=source.get('webGeometrySource',source.name)
  clone['scope']='Only photo-supported principal-elevation pane hue and graphite frame finish; exact original geometry and optical policy'
  for index,original in enumerate(source.data.materials):
   if original is None:continue
   role='glass'if source_name in GLASS_SOURCES else'frame'
   key=(original.name,role)
   if key not in materials:
    material=original.copy();material.name='CKK219_'+role+'_'+original.name
    shader=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED');assert not shader.inputs['Base Color'].is_linked
    before=metrics(original);luminance=sum(c*w for c,w in zip(before['color'],[.2126,.7152,.0722]))
    if role=='glass':
     tint=(.97,1.0,1.02);normalizer=sum(c*w for c,w in zip(tint,[.2126,.7152,.0722]));color=tuple(luminance*c/normalizer for c in tint)+(before['color'][3],)
    else:color=(.058,.061,.062,before['color'][3])
    shader.inputs['Base Color'].default_value=color;material.diffuse_color=color
    material['colourBasis']='Grimshaw principal elevation and Willebrand frontage detail built photographs; undated and uncalibrated visual estimate'
    material['finishScope']='Neutral smoke-grey reflective pane, original luminance and optics retained'if role=='glass'else'Graphite-grey historic window frame estimate; original PBR parameters retained'
    after=metrics(material)
    for field in ['roughness','metallic','alpha','transmission']:assert before[field]==after[field]
    for field in ['webOpacity','webClosedGlazing']:assert original.get(field)==material.get(field)
    if role=='glass':assert abs(sum(c*w for c,w in zip(after['color'],[.2126,.7152,.0722]))-luminance)<1e-7
    records.append(dict(source=original.name,replacement=material.name,role=role,before=before,after=after));materials[key]=material
   clone.data.materials[index]=materials[key]
  bpy.data.collections['CKK_EXTERIOR'].objects.link(clone);clone.hide_render=False;clone.hide_set(False);source.hide_render=True;source.hide_set(True)
  owned.append(clone);bindings[clone.name]=[m.name if m else None for m in clone.data.materials]
  assert geometry_state(clone)==before_geometry[source_name]
 update()
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
 assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in material_states.items())
 render_views('after')
 fingerprints={o.name:object_fingerprint(o)for o in owned}
 component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
 expected=accepted_fingerprints(ROOT/'result/blender/stage218',SHA)
 assert {o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
 with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=list(fingerprints)
 for obj in loaded.objects:
  for index,name in enumerate(bindings[obj.name]):obj.data.materials[index]=bpy.data.materials[name]if name else None
  bpy.data.collections['CKK_EXTERIOR'].objects.link(obj);obj.hide_render=False;obj.hide_set(False)
  assert geometry_state(obj)==before_geometry[obj['originalObject']]
 for name in GLASS_SOURCES+FRAME_SOURCES:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
 update()
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items())
 assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in material_states.items())
 assert all(modifiers(bpy.data.objects[n])==v for n,v in original_modifiers.items())
 assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in membership.items())
 assert all(sorted(o.name for o in bpy.data.collections[c].all_objects)==names for c,names in spaces.items())
 assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items()if n not in GLASS_SOURCES+FRAME_SOURCES)
 references=[]
 for path,url in [('data/collections/exteriors/images/ckk_grimshaw_010.jpg','https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/'),('data/collections/library_round5/photos/CKK_8f06506667f1.jpg','https://www.willebrand.com/en/projects/lse-london-school-of-economics-grimshaw-architects.398'),('data/collections/library_round5/photos/CKK_4303d768d356.jpg','https://www.willebrand.com/en/projects/lse-london-school-of-economics-grimshaw-architects.398')]:
  references.append(dict(path=path,sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),sourceUrl=url,evidence='built photograph',projectYear=2008,photographDate='unknown',publicationDate='unknown'))
 verification=dict(savedComponentReopened=True,acceptedOriginalObjectsVerified=len(originals),originalMaterialsVerified=len(material_states),protectedSpaceCollections=len(spaces),protectedSpaceObjects=len(protected),allOriginalFingerprintsUnchanged=True,allOriginalMaterialsUnchanged=True,allOriginalModifiersUnchanged=True,allOriginalCollectionMembershipUnchanged=True,protectedSpaceMembershipAndFingerprintsUnchanged=True,exactReplacementGeometryTransformUVVerified=True,unrelatedVisibilityPreserved=True,baselineNativeUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA)
 audit=dict(version=219,baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),targetCollection='CKK_EXTERIOR',destinationCollection='CKK_EXTERIOR',addedObjects=list(fingerprints),archivedObjects=GLASS_SOURCES+FRAME_SOURCES,addedFingerprints=fingerprints,replacementMaterialBindings=bindings,changedObjects=[],materials=records,references=references,verification=verification,backingEvidence=dict(path=str((OUT/'backing-rays.json').relative_to(ROOT)),samples=rays['samples'],nearBackingSamples=rays['nearBackingSamples']),previews=['before-front.png','after-front.png','before-oblique.png','after-oblique.png'],cameras=cameras,lighting='Identical EEVEE32sample neutral sky0.7/sun2/AgX1000x1100; same cameras, no photo pixels',scope='Neutralise hue on three photographed historic frontage glass batches without changing luminance, opacity or geometry. Darken three principal window-frame batches to graphite grey. No geometry additions.',limitations=['Material values are visual estimates from undated and uncalibrated built photographs, not a measured2026 condition survey.','Historic frontage and dormers retain opaque reflective proxies: no complete near room backing established. No invented interior transparency.','Retained all roof-pavilion limited transparency, public atrium, classroom samples, stonework, dormer zinc, unphotographed rear/side glass and geometry.','Warm ground-floor light in photographs is interior illumination; it is not applied as a yellow glass base colour.'])
 (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
 (OUT/'inspection.json').unlink(missing_ok=True)
 print('CKK219_COMPONENT_REOPENED',len(fingerprints),len(originals),len(material_states),rays['nearBackingSamples'],'/',rays['samples'],flush=True)

if __name__=='__main__':run()
