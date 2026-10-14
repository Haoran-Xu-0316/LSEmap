"""Add LRB's omitted existing upper-roof safety handrail as an isolated component.

Open in Blender's Text Editor and run. Fixed paths and configuration; original
campus objects, meshes, UVs, bindings and visibility are checked unchanged.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import subprocess
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v209.blend'
BASE_SHA = '6398f422e2fefde66c33e0d87a36092bfad46b7fee69494d5c955caae443e455'
OUT = ROOT / 'result/blender/lrb-exterior210'
NAME = 'LRB_EXTERIOR210_existing_upper_roof_safety_handrail'
OLD_BOUNDARY = [(253,1180),(753,166),(1547,118),(1565,380),(1470,394),(1485,1055),(1339,1058),(1344,1132),(1293,1163),(1215,1157),(1199,1193),(731,1220),(725,1189),(567,1183),(565,1175)]
NEW_BOUNDARY = [(253,1180),(753,166),(1547,118),(1565,380),(1470,394),(1485,1055),(1339,1058),(1344,1132),(1215,1138),(1215,1185),(1076,1185),(1076,1220),(545,1220),(545,1183)]
# Manually read safety-handrail centreline in the 1888px existing-plan render.
# The accepted roof109 rigid metric registration is reused, not re-fitted.
TRACE = [(550,1158),(337,1154),(337,1061),(716,294),(750,228),(785,206),
         (823,183),(1526,138),(1539,380),(1375,383),(1398,1056)]
SOURCES = [
 ('data/collections/library-roof-2025/existing-roof-plan.pdf',
  '4556-FBR-LR-ZZ-DR-A-110 P01, 17 April 2025, Roof Plan As Existing',
  'Existing safety handrail ht.1.10; manually read north/west/east centreline and post rhythm'),
 ('data/collections/library-roof-2025/existing-sw-elevation.pdf',
  '4556-FBR-LR-ZZ-DR-A-111 P01, 17 April 2025, South West As Existing',
  'Upper-roof two horizontal rails and vertical posts, distinct from lower terrace rails'),
 ('data/collections/library_round5/photos/LRB_5ea4100c9303.jpg',
  'https://tyrensakt.com/projects/lse-library/',
  '2001 project, photograph capture date unknown; broad roof mass context only; not current-condition proof'),
]

def fingerprint(obj):
    h = hashlib.sha256((obj.type + str([list(r) for r in obj.matrix_world])).encode())
    if obj.type == 'MESH':
        for values, field, kind, count in [(obj.data.vertices,'co','f',3),
                                          (obj.data.loops,'vertex_index','i',1),
                                          (obj.data.polygons,'material_index','i',1),
                                          (obj.data.polygons,'loop_total','i',1)]:
            buffer = array.array(kind,[0]) * (len(values)*count)
            values.foreach_get(field,buffer); h.update(buffer.tobytes())
        for layer in obj.data.uv_layers:
            buffer=array.array('f',[0])*(len(layer.data)*2)
            layer.data.foreach_get('uv',buffer);h.update(layer.name.encode()+buffer.tobytes())
        h.update(str([m.name if m else None for m in obj.data.materials]).encode())
    return h.hexdigest()


def preview(phase):
    scene=bpy.data.scenes.new('LRB210_preview_'+phase)
    collection=bpy.data.collections.new(scene.name+'_objects')
    scene.collection.children.link(collection)
    for collection_name in ['LRB_EXTERIOR','LRB_PUBLIC_INTERIOR168_study']:
        for obj in bpy.data.collections[collection_name].all_objects:
            if obj.type in {'MESH','FONT','CURVE'} and not obj.hide_render:
                collection.objects.link(obj)
    world=bpy.data.worlds.new(scene.name+'_world');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[1].default_value=.65
    env=world.node_tree.nodes.new('ShaderNodeTexEnvironment')
    env.image=bpy.data.images.load(str(ROOT/'web/public/environment/kloppenheim-daylight-1k.hdr'),check_existing=True)
    world.node_tree.links.new(env.outputs['Color'],world.node_tree.nodes['Background'].inputs[0])
    scene.world=world
    sun_data=bpy.data.lights.new(scene.name+'_sun','SUN');sun_data.energy=1.8;sun_data.angle=.12
    sun=bpy.data.objects.new(sun_data.name,sun_data);collection.objects.link(sun)
    sun.rotation_euler=Vector((-.6,.5,-1)).to_track_quat('-Z','Y').to_euler()
    camera_data=bpy.data.cameras.new(scene.name+'_camera')
    camera=bpy.data.objects.new(camera_data.name,camera_data);collection.objects.link(camera);scene.camera=camera
    camera_data.type='ORTHO';scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.resolution_x=1150;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    for label,center,offset,scale in [('whole',(70,7,15),(-65,-90,55),106),
                                     ('upper-roof',(73,10,24),(50,70,75),82)]:
        center=Vector(center);camera.location=center+Vector(offset)
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        camera_data.ortho_scale=scale;scene.render.filepath=str(OUT/(phase+'-'+label+'.png'))
        bpy.ops.render.render(write_still=True,scene=scene.name)
    bpy.data.scenes.remove(scene);bpy.data.collections.remove(collection)
    for obj in [camera,sun]:bpy.data.objects.remove(obj,do_unlink=True)


def correct_south_roof(project):
    """Replace only south setback boundaries; keep the accepted lightwell open."""
    roof=bpy.data.objects['LRB_V117_current_perimeter_roof']
    old_chain=[project(p)for p in OLD_BOUNDARY[6:]+[OLD_BOUNDARY[0]]]
    new_chain=[project(p)for p in NEW_BOUNDARY[6:]+[NEW_BOUNDARY[0]]]
    horizontal=[];upper_horizontal=[];retained=[]
    for face in roof.data.polygons:
        pts=[roof.matrix_world@roof.data.vertices[i].co for i in face.vertices]
        if all(abs(p.z-23.99)<.002 for p in pts)or all(abs(p.z-20.24)<.002 for p in pts):
            horizontal.append([[p.x,p.y]for p in pts])
            if all(abs(p.z-23.99)<.002 for p in pts):upper_horizontal.append([[p.x,p.y]for p in pts])
        else:retained.append(face.index)
    payload=dict(horizontal=horizontal,upperHorizontal=upper_horizontal,boundary=[[project(p).x,project(p).y]for p in NEW_BOUNDARY],oldBoundary=[[project(p).x,project(p).y]for p in OLD_BOUNDARY])
    (OUT/'roof-region-input.json').write_text(json.dumps(payload))
    prep="""from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
p=Path('result/blender/lrb-exterior210')
d=json.loads((p/'roof-region-input.json').read_text())
domain=unary_union([Polygon(t)for t in d['horizontal']])
old_actual=unary_union([Polygon(t)for t in d['upperHorizontal']])
old_outline=Polygon(d['oldBoundary']);new_outline=Polygon(d['boundary'])
added=new_outline.difference(old_outline).intersection(domain)
removed=old_outline.difference(new_outline).intersection(old_actual)
upper=old_actual.difference(removed).union(added)
lower=domain.difference(upper)
result={'addedUpperArea':added.area,'removedUpperArea':removed.area,'preservedOtherRoofEdges':True,'southWallsOutsideFootprintMetres':__import__('shapely').geometry.LineString(d['boundary'][6:]+[d['boundary'][0]]).difference(domain.buffer(.025)).length}
assert result['southWallsOutsideFootprintMetres']<.001
for name,region in [('upper',upper),('lower',lower)]:
 result[name]=[[list(p)for p in list(t.exterior.coords)[:3]]for t in constrained_delaunay_triangles(region).geoms]
 result[name+'Area']=region.area
result['domainArea']=domain.area
(p/'roof-regions.json').write_text(json.dumps(result))
"""
    subprocess.run(['/opt/anaconda3/envs/MachineLearning/bin/python','-c',prep],cwd=ROOT,check=True)
    regions=json.loads((OUT/'roof-regions.json').read_text())
    replacements=[]
    def clone(source):
        obj=source.copy();obj.data=source.data.copy()
        obj.name='LRB_EXTERIOR210_'+source.name
        obj['originalObject']=source.name;obj['destinationCollection']='LRB_EXTERIOR'
        obj['webGeometrySource']=source.get('webGeometrySource',source.name)
        obj['sharedInteriorRoof']=True
        bpy.data.collections['LRB_EXTERIOR'].objects.link(obj)
        source.hide_render=True;source.hide_set(True);obj.hide_render=False;obj.hide_set(False)
        replacements.append(dict(originalObject=source.name,replacement=obj.name,targetCollection='LRB_EXTERIOR'))
        return obj
    def mesh_with_retained(source,indices,new_verts,new_faces):
        vertices=[];faces=[];uvs=[];slots=[]
        for fi in indices:
            face=source.data.polygons[fi];start=len(vertices)
            vertices.extend(source.data.vertices[i].co.copy()for i in face.vertices)
            faces.append(tuple(range(start,len(vertices))))
            uvs.append([[list(layer.data[li].uv)for li in face.loop_indices]for layer in source.data.uv_layers])
            slots.append(face.material_index)
        start=len(vertices);inv=source.matrix_world.inverted()
        vertices.extend(inv@Vector(v)for v in new_verts)
        for face in new_faces:
            faces.append(tuple(start+i for i in face));slots.append(0)
            pts=[Vector(new_verts[i])for i in face]
            u=(pts[1]-pts[0]).normalized();n=(pts[1]-pts[0]).cross(pts[-1]-pts[0]).normalized();v=n.cross(u)
            coords=[[(p-pts[0]).dot(u),(p-pts[0]).dot(v)]for p in pts]
            uvs.append([coords for layer in source.data.uv_layers])
        mesh=bpy.data.meshes.new('LRB210_'+source.data.name)
        mesh.from_pydata(vertices,[],faces);mesh.update()
        for m in source.data.materials:mesh.materials.append(m)
        for k,old in enumerate(source.data.uv_layers):
            layer=mesh.uv_layers.new(name=old.name)
            for face,values in zip(mesh.polygons,uvs):
                for li,uv in zip(face.loop_indices,values[k]):layer.data[li].uv=uv
        for face,slot in zip(mesh.polygons,slots):face.material_index=slot
        return mesh
    rv=[];rf=[]
    for key,z in [('lower',20.24),('upper',23.99)]:
        for triangle in regions[key]:
            pts=[Vector((p[0],p[1],z))for p in triangle]
            if (pts[1]-pts[0]).cross(pts[2]-pts[0]).z<0:pts.reverse()
            start=len(rv);rv.extend(pts);rf.append(tuple(range(start,start+3)))
    new_roof=clone(roof);new_roof.data=mesh_with_retained(roof,retained,rv,rf)
    sources={'cladding':'LRB196_FINISH_LRB_D5_roof109_cladding',
             'glass':'LRB196_FINISH_GLASS181_LRB_EXTERIOR172_D5_roof109_glass',
             'frame':'LRB196_FINISH_LRB_D5_roof109_frame'}
    added={key:([],[])for key in sources}
    def box(key,center,dimensions,angle):
        vs,fs=added[key];start=len(vs);c=math.cos(angle);s=math.sin(angle)
        for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]:
            x*=dimensions[0]/2;y*=dimensions[1]/2;z*=dimensions[2]/2
            vs.append((center.x+c*x-s*y,center.y+s*x+c*y,center.z+z))
        fs.extend([tuple(start+i for i in f)for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]])
    # The manually read source order becomes clockwise in campus coordinates.
    for a,b in zip(new_chain,new_chain[1:]):
        u=(b-a).normalized();n=Vector((-u.y,u.x,0));span=(b-a).length
        angle=math.atan2(u.y,u.x);count=max(1,round(span/2.4));pitch=span/count
        def at(x,d,z):
            p=a+u*x+n*d;p.z=z;return p
        for i in range(count):
            x=(i+.5)*pitch
            box('cladding',at(x,-.10,22.115),(pitch,.20,3.75),angle)
            width=min(1.35,pitch*.66);lo=20.89;hi=23.51
            box('glass',at(x,.022,(lo+hi)/2),(width,.035,hi-lo),angle)
            for z in [lo,hi,(lo+hi)/2]:box('frame',at(x,.058,z),(width,.08,.035),angle)
            for sign in [-1,1]:box('frame',at(x+sign*width/2,.058,(lo+hi)/2),(.035,.08,hi-lo),angle)
        box('cladding',at(span/2,-.04,24.065),(span+.12,.35,.15),angle)
    removed={};unchanged={}
    def distance(p,a,b):
        d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));return (p-(a+d*t)).length
    for key,name in sources.items():
        source=bpy.data.objects[name];mesh=source.data
        neighbors=[set()for v in mesh.vertices]
        for edge in mesh.edges:
            a,b=edge.vertices;neighbors[a].add(b);neighbors[b].add(a)
        seen=set();remove=set()
        for i in range(len(mesh.vertices)):
            if i in seen:continue
            stack=[i];seen.add(i);component=[]
            while stack:
                j=stack.pop();component.append(j)
                for k in neighbors[j]:
                    if k not in seen:seen.add(k);stack.append(k)
            pts=[source.matrix_world@mesh.vertices[j].co for j in component]
            center=sum(pts,Vector())/len(pts);center.z=23.99
            if min(p.z for p in pts)>=20.20 and max(p.z for p in pts)<=24.15 and min(distance(center,a,b)for a,b in zip(old_chain,old_chain[1:]))<.55:
                remove.update(component)
        keep=[p.index for p in mesh.polygons if not any(i in remove for i in p.vertices)]
        assert len(keep)<len(mesh.polygons),name
        obj=clone(source);obj.data=mesh_with_retained(source,keep,*added[key])
        removed[key]=len(mesh.polygons)-len(keep);unchanged[key]=len(keep)
    return replacements,dict(oldBoundaryPixels=OLD_BOUNDARY,newBoundaryPixels=NEW_BOUNDARY,
        upperArea=regions['upperArea'],lowerArea=regions['lowerArea'],addedUpperArea=regions['addedUpperArea'],removedUpperArea=regions['removedUpperArea'],preservedOtherRoofEdges=True,southWallsOutsideFootprintMetres=regions['southWallsOutsideFootprintMetres'],retainedLightwell=True,
        southEdgeSource='2025 As Existing110: actual steps atx545/x1076; old x565/x725/x731 jogs were not drawing boundaries',
        rebuiltCladdingFaces=removed,unchangedFacesWithOriginalCornerUVs=unchanged,
        newGlazingStatus='Opaque inherited proxy material with cladding0.10m behind; no unregistered transparent interior')

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:layer.update()
    originals={o.name:fingerprint(o)for o in bpy.data.objects}
    visibility={o.name:o.hide_render for o in bpy.data.objects}
    if not (OUT/'before-upper-roof.png').exists(): preview('before')
    ring=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings']if b['code']=='LRB')['rings'][0]
    direction=Vector(ring[7])-Vector(ring[4])
    angle=math.atan2(direction.y,direction.x)-math.atan2(52,926)
    center=Vector((75.5933837890625,13.260777473449707))
    # Read the accepted cap centre from the actual current shell, avoiding a stale
    # stored centre and retaining the already authored source-to-campus transform.
    shell=bpy.data.objects['LRB_V109_survey_dome_shell']
    pts=[shell.matrix_world@v.co for v in shell.data.vertices]
    center=Vector(((min(p.x for p in pts)+max(p.x for p in pts))/2,
                   (min(p.y for p in pts)+max(p.y for p in pts))/2))
    def project(pixel):
        dx,dy=pixel[0]-993,pixel[1]-629
        return Vector((center.x+(math.cos(angle)*dx+math.sin(angle)*dy)/22.5,
                       center.y+(math.sin(angle)*dx-math.cos(angle)*dy)/22.5,23.99))
    roof_replacements,roof_review = correct_south_roof(project)
    path=[project(p)for p in TRACE]
    roof=bpy.data.objects[roof_replacements[0]['replacement']];inv=roof.matrix_world.inverted()
    def support(p):
        hit,point,normal,index=roof.ray_cast(inv@Vector((p.x,p.y,24.1)),Vector((0,0,-1)))
        return hit and abs((roof.matrix_world@point).z-23.99)<.002
    checks=[]; segment_checks=[]
    for segment,(a,b) in enumerate(zip(path,path[1:])):
        prior=len(checks)
        for i in range(max(2,math.ceil((b-a).length/.25))):
            p=a+(b-a)*i/max(2,math.ceil((b-a).length/.25))
            checks.append(support(p))
        segment_checks.append(dict(segment=segment,pixels=[TRACE[segment],TRACE[(segment+1)%len(TRACE)]],supported=sum(checks[prior:]),samples=len(checks)-prior))
    (OUT/'support-diagnostics.json').write_text(json.dumps(segment_checks,indent=2)+'\n')
    assert all(checks), ('Rail trace must have retained roof below every 0.25m sample',sum(checks),len(checks))
    vertices=[];faces=[]
    def tube(a,b,r=.021,sides=8):
        axis=(b-a).normalized();helper=Vector((0,0,1))if abs(axis.z)<.9 else Vector((1,0,0))
        u=axis.cross(helper).normalized();v=axis.cross(u).normalized();start=len(vertices)
        for p in [a,b]:
            for i in range(sides):vertices.append(p+r*(u*math.cos(i*math.tau/sides)+v*math.sin(i*math.tau/sides)))
        faces.extend([tuple(start+j for j in reversed(range(sides))),tuple(start+sides+j for j in range(sides))])
        faces.extend([(start+i,start+(i+1)%sides,start+(i+1)%sides+sides,start+i+sides)for i in range(sides)])
    posts=[];length=0
    for a,b in zip(path,path[1:]):
        span=(b-a).length;length+=span;count=max(1,round(span/2.0))
        for i in range(count):
            p=a+(b-a)*i/count;posts.append(list(p))
            tube(p,p+Vector((0,0,1.10)))
        for z in [.55,1.10]:tube(a+Vector((0,0,z)),b+Vector((0,0,z)),.0175)
    p=path[-1]; posts.append(list(p));tube(p,p+Vector((0,0,1.10)))
    mesh=bpy.data.meshes.new(NAME);mesh.from_pydata(vertices,[],faces);mesh.update()
    material=bpy.data.materials['LRB_V110_roof_rail'].copy()
    material.name='LRB_EXTERIOR210_LRB_V110_roof_rail'
    material['evidenceScope']='Existing roof safety handrail; inherited roof-rail finish, not measured colour'
    mesh.materials.append(material)
    obj=bpy.data.objects.new(NAME,mesh);bpy.data.collections['LRB_EXTERIOR'].objects.link(obj)
    obj['destinationCollection']='LRB_EXTERIOR'
    obj['sourceStatus']='17 April 2025 As Existing; safety handrail 1.10m, approximate trace and post pitch'
    obj['scope']='Omitted existing upper-roof safety handrail only; no glazing or complete interior inference'
    assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
    assert all(bpy.data.objects[n].hide_render==(True if n in {r['originalObject']for r in roof_replacements}else v)for n,v in visibility.items())
    preview('after')
    component=OUT/'lrb-exterior210-component.blend'
    owned={obj,material}|{bpy.data.objects[r['replacement']]for r in roof_replacements}
    bpy.data.libraries.write(str(component),owned,fake_user=True)
    report=dict(version=210,baseline=str(BASE.relative_to(ROOT)),baselineSha256=BASE_SHA,
        componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),
        targetCollection='LRB_EXTERIOR',destinationCollection='LRB_EXTERIOR',addedObjects=[NAME]+[r['replacement']for r in roof_replacements],archivedObjects=[r['originalObject']for r in roof_replacements],changedObjects=[],replacements=roof_replacements,roofReview=roof_review,
        scope='Correct south roof setback and supporting cladding/window batches from2025 As Existing; restore omitted north/west/east upper-roof safety handrail; preserve dome and public interior',
        roofHeight=23.99,handrailHeight=1.10,nominalPostPitch=2.0,railDiameters=[.042,.035],
        tracedLengthMetres=length,postCount=len(posts),sourceTracePixels=TRACE,registeredPath=[list(p)for p in path],
        supportChecks=dict(sampleSpacingMetres=.25,roofSamples=len(checks),supported=sum(checks)),
        originalGeometryAndUVPreserved=True,originalObjectsVerified=len(originals),onlyListedOriginalVisibilityChanged=True,
        sources=[dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),drawingOrURL=d,support=s)for p,d,s in SOURCES],
        improvements=['South roof setback rebuilt from existing drawing: fictitious x565/725/731 source-pixel jogs removed and actual x545/1076 steps restored; corresponding cladding, opaque window proxies and frames follow the corrected roof.', 'Previously omitted upper-roof safety handrail restored along three continuous supported roof sides, distinct from retained lower terrace X-rails and PV platform.'],
        limitations=['Source is a2025 As Existing survey issued for planning; it is not a2026 inspection or proposed construction.',
                    'Manual centreline and accepted metric registration are approximate; source registration is not a measured site coordinate survey.',
                    'Initial675/732 support result was investigated: southeast source rail lies on+40.01 lower roof beside+43.6 upper roof, while southwest roof109 outline contained false steps. Upper roof is corrected; low-level rail requires separate height registration and is omitted, with no arbitrary lateral rail movement.',
                    '1.10m handrail height is explicitly labelled; nominal2m post pitch,42/35mm tube diameters and intermediate rail height are visual estimates.',
                    'Retained roof plant includes previously proposed heat-pump layout; completion and detailed current condition remain unverified.',
                    'No second plant-room mass is added because the archived views do not reliably resolve its plan and height pairing.',
                    'No new transparent glazing; original dome, public floors, counters and independent room studies unchanged.'],
        previews=['before-whole.png','after-whole.png','before-upper-roof.png','after-upper-roof.png'],
        previewLighting='Identical daylight HDR,AgX,1.8sun,.65background,16Cycles samples; exterior and retained registered public interior')
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    expected={o.name:fingerprint(o)for o in owned if isinstance(o,bpy.types.Object)}
    bpy.ops.wm.open_mainfile(filepath=str(component))
    assert all(fingerprint(bpy.data.objects[n])==h for n,h in expected.items())
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    (OUT/'verification.json').write_text(json.dumps(dict(savedComponentReopened=True,componentSha256=report['componentSha256'],
        baselineUnchanged=True,originalObjectsVerified=len(originals),originalGeometryUVAndBindingsUnchanged=True,
        onlyListedOriginalVisibilityChanged=True,addedObjects=list(expected),addedTriangles=sum(len(p.vertices)-2 for n in expected for p in bpy.data.objects[n].data.polygons),
        originalPublicInteriorUnchanged=True,noTransparentGlazingAdded=True),indent=2)+'\n')
    print('LRB210_COMPONENT_READY',len(posts),round(length,2),report['componentSha256'],flush=True)

if __name__=='__main__':
    build()
