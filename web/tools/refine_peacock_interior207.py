"""Build a bounded Peacock historical auditorium component from the 2022 DWG.

Run in Blender's Text Editor. The unchanged v206 campus remains the baseline.
Only PEA_PUBLIC_INTERIOR_study is replaced at integration. The independent
local room is never registered or linked to the geographic campus. Exact DWG
row arcs and section floor anchors are retained; individual seat spacing,
Circle width, wall finishes and cutaway perimeter are estimated. This is not
an exact capacity model, an evacuation plan or a 2026 as-built survey.
"""
from pathlib import Path
import array, hashlib, json, math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/pea-interior207'
BASE = ROOT/'result/blender/LSE_campus_detailed_v206.blend'
COMPONENT = OUT/'peacock-interior207-component.blend'
DESTINATION = 'PEA_PUBLIC_INTERIOR_study'
PREFIX = 'PEA207_'
BASE_SHA = '605fc53169bd40b830fa817d7ecb17be2a6d38658236f3d69c9dd48aedc91c78'
LAYOUT = json.loads((OUT/'historical-layout.json').read_text())
SCOPE = 'Historical 2022/2023 auditorium study; separate local coordinates. Seat spacing and Circle plan width estimated, not a 2026 survey or exact seating chart.'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(obj):
    h=hashlib.sha256(str([list(r)for r in obj.matrix_world]).encode())
    if obj.type=='MESH':
        for data,attribute,kind,width in [(obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1)]:
            values=array.array(kind,[0])*(len(data)*width);data.foreach_get(attribute,values);h.update(values.tobytes())
        for uv in obj.data.uv_layers:
            values=array.array('f',[0])*(len(uv.data)*2);uv.data.foreach_get('uv',values);h.update(values.tobytes())
        h.update(str([m.name if m else None for m in obj.data.materials]).encode())
    return h.hexdigest()


class Builder:
    def __init__(self,collection):
        self.collection=collection;self.groups={};self.seats=[];self.floors=[]
        self.materials={}
        for key,color in {'upholstery':(.30,.022,.034),'carpet':(.095,.095,.12),'frame':(.025,.031,.039),'stage':(.018,.021,.025),'wall':(.10,.115,.135),'rib':(.20,.22,.25),'screen':(.80,.80,.75),'edge':(.43,.34,.20),'curtain':(.34,.018,.032)}.items():
            mat=bpy.data.materials.new(PREFIX+key);mat.diffuse_color=(*color,1);mat.use_nodes=True
            node=mat.node_tree.nodes['Principled BSDF'];node.inputs['Base Color'].default_value=mat.diffuse_color;node.inputs['Roughness'].default_value=.8
            self.materials[key]=mat
    def mesh(self,family,material,vertices,faces):
        key=(family,material)
        if key not in self.groups:self.groups[key]=[[],[]]
        v,f=self.groups[key];offset=len(v);v.extend(vertices);f.extend(tuple(offset+i for i in face)for face in faces)
    def box(self,family,material,centre,size,angle=0):
        x,y,z=centre;a,b,c=[q/2 for q in size];co,si=math.cos(angle),math.sin(angle)
        v=[(x+dx*co-dy*si,y+dx*si+dy*co,z+dz)for dz in [-c,c]for dy in [-b,b]for dx in [-a,a]]
        self.mesh(family,material,v,[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)])
    def prism(self,family,material,points,bottom,top):
        n=len(points);self.mesh(family,material,[(x,y,z)for z in [bottom,top]for x,y in points],[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)])
    def chair(self,x,y,z,angle,level,row):
        co,si=math.cos(angle),math.sin(angle)
        def p(dx,dy,dz):return(x+dx*co-dy*si,y+dx*si+dy*co,z+dz)
        self.box(level+'_seat_cushions','upholstery',p(0,0,.47),(.47,.43,.12),angle)
        outline=[(-.245,.60),(.245,.60),(.245,.93),(.19,1.02),(.10,1.05),(-.10,1.05),(-.19,1.02),(-.245,.93)]
        n=len(outline);self.mesh(level+'_curved_backs','upholstery',[p(dx,dy,dz)for dy in [.17,.255]for dx,dz in outline],[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)])
        self.box(level+'_seat_supports','frame',p(0,.07,.23),(.16,.22,.46),angle)
        for side in [-1,1]:self.box(level+'_armrests','frame',p(side*.265,0,.67),(.045,.45,.045),angle)
        self.seats.append(dict(level=level,row=row,x=x,y=y,floor=z,angle=angle))
    def finish(self):
        objects=[]
        for (family,material),(vertices,faces)in self.groups.items():
            mesh=bpy.data.meshes.new(PREFIX+family+'_mesh');mesh.from_pydata(vertices,[],faces);mesh.update();mesh.materials.append(self.materials[material])
            uv=mesh.uv_layers.new(name='SurfaceUV')
            for poly in mesh.polygons:
                for i in poly.loop_indices:
                    p=mesh.vertices[mesh.loops[i].vertex_index].co
                    uv.data[i].uv=(p.x,p.y)if abs(poly.normal.z)>.5 else(p.x+p.y,p.z)
            obj=bpy.data.objects.new(PREFIX+family,mesh);self.collection.objects.link(obj)
            obj['scope']=SCOPE;obj['buildingCode']='PEA';obj['dimensionsEstimated']=True
            obj['sourceLayout']='2022 operator DWG: row arcs and section floor anchors'
            if family in {'stalls_floor_tiers','circle_floor_tiers'}:self.floors.append(obj)
            objects.append(obj)
        return objects


def build_room(collection):
    b=Builder(collection)
    # Source stage width 19.5m is asymmetric about the centreline:10.1m/9.4m.
    stage=1.05
    b.box('stage_deck','stage',(-.35,-5.35,stage-.15),(19.5,10.7,.30))
    b.box('stage_back','stage',(-.35,-10.70,stage+3.8),(19.5,.18,7.6))
    for side,width,centre in [(-1,3.6,-8.3),(1,2.9,7.95)]:
        b.box('proscenium_piers','frame',(centre,-.1,4.575),(width,.45,9.15))
    # Opening is measured from stage deck to the underside, not header centre.
    b.box('proscenium_header','frame',(0,-.1,7.75),(13,.45,1.60))
    b.box('projection_screen','screen',(0,-1.65,4.78),(9.8,.07,3.2))
    for side in [-1,1]:
        for i in range(14):
            b.box('house_curtain_folds','curtain',(side*(6.55+i*.07),-.42,stage+2.95),(.09,.16+.06*(i%2),5.9))
    apron=[(-5.64,0),(5.64,0),(5.64,1),(3.2,1.6),(0,2),(-3.2,1.6),(-5.64,1)]
    b.prism('pit_lift_forestage','stage',apron,stage-.20,stage)
    b.box('stage_front_fascia','curtain',(0,.04,.47),(11.28,.10,.94))
    # Complete three-bank stalls floor follows the original arcs. Four aisles
    # are the two bank gaps plus the two perimeter aisles, never a centre aisle.
    for row in LAYOUT['stalls']:
        arcs=row['arcs'];radius=arcs[0]['radius'];half=max(abs(p[0])for a in arcs for p in a['points'])+1.0
        def curve(x):return row['y']-(radius-math.sqrt(radius*radius-x*x))
        xs=[-half+2*half*i/48 for i in range(49)]
        poly=[(x,curve(x)-.4102)for x in xs]+[(x,curve(x)+.4102)for x in reversed(xs)]
        b.prism('stalls_floor_tiers','carpet',poly,row['floor']-.20,row['floor'])
        for arc in arcs:
            length=math.radians(arc['end']-arc['start'])*arc['radius'];count=max(1,int(length/.555))
            for i in range(count):
                angle=math.radians(arc['start']+(arc['end']-arc['start'])*(i+.5)/count)
                cx,cy=arc['centre'];x=cx+arc['radius']*math.cos(angle);y=cy-arc['radius']*math.sin(angle)+.10
                # Curve normals converge toward the source arc centre.
                facing=math.atan2(x-cx,y-cy)
                b.chair(x,y,row['floor'], -facing,'stalls',row['index'])
        # Contrasting nosings occur only across the four clear aisle bands.
        for x in [-half+.45,-4.3,4.3,half-.45]:
            b.box('stalls_aisle_nosings','edge',(x,curve(x)-.397,row['floor']+.008),(.78,.035,.016))
    # The DWG provides a longitudinal Circle section but no full Circle seating
    # plan. This restrained width follows the stalls envelope as an estimate.
    circle=LAYOUT['circle'];half=10.5
    for row in circle:
        i=row['index'];front=row['y']-.40
        back=(circle[i+1]['y']-.40)if i+1<len(circle)else row['y']+.55
        # The cross aisle in the source is retained as a wider tread.
        b.box('circle_floor_tiers','carpet',(0,(front+back)/2,row['floor']-.16),(half*2,back-front,.32))
        for lo,hi in [(-9.8,-4.9),(-4.0,4.0),(4.9,9.8)]:
            count=int((hi-lo)/.555)
            for j in range(count):
                x=lo+(hi-lo)*(j+.5)/count
                b.chair(x,row['y'],row['floor'], -math.atan2(x,row['y']+9),'circle',i)
        # Two steps per Circle row keep the approximately0.344m tier rise legible.
        if i>0:
            prev=circle[i-1];z=(row['floor']+prev['floor'])/2
            for x in [-10.15,-4.45,4.45,10.15]:
                b.box('circle_aisle_half_steps','carpet',(x,front-.13,z-.08),(.72,.26,.16))
                b.box('circle_aisle_nosings','edge',(x,front-.25,z+.009),(.70,.035,.018))
    front=circle[0]['y']-.46
    b.box('circle_front_fascia','wall',(0,front,4.56),(21,.18,.74))
    b.box('circle_front_handrail','frame',(0,front-.03,5.10),(21,.07,.08))
    # Side wings/open boxes are spatially evidenced by the photographs and
    # specification. No fourteen exact box-seat coordinates are fabricated.
    for side in [-1,1]:
        b.box('open_side_box_decks','carpet',(side*10.15,10.7,4.44),(1.5,4.0,.30))
        b.box('open_side_box_fronts','wall',(side*9.38,10.7,4.75),(.14,4.0,.78))
        b.box('open_side_box_end','wall',(side*10.15,8.72,4.75),(1.65,.14,.78))
    # Left wall is retained in the cutaway; camera-side/right and rear wall
    # are intentionally omitted so the full volume and Circle remain visible.
    b.box('left_acoustic_wall','wall',(-11.3,10.8,4.35),(.18,21.6,8.7))
    for y in [i*.29 for i in range(74)]:
        b.box('left_vertical_ribs','rib',(-11.18,y,3.0),(.055,.045,4.0))
    for side in [-1,1]:
        b.box('forward_acoustic_sidewall','wall',(side*11.3,3.7,4.35),(.18,7.4,8.7))
    b.box('rear_stalls_crosswalk','carpet',(0,21.65,1.54),(22,1.25,.20))
    objects=b.finish()
    return b,objects


def render_objects(objects,label,views=None):
    scene=bpy.data.scenes.new(PREFIX+'review_'+label)
    for obj in objects:scene.collection.objects.link(obj)
    scene.render.engine='CYCLES';scene.cycles.samples=12
    scene.render.resolution_x=1100;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new(PREFIX+'review_world_'+label);scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.25,.27,.31,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.4
    for name,pos,power,size in [('key',(4,10,17),3400,13),('fill',(-7,-2,11),2200,10),('rear',(1,23,13),2000,10)]:
        data=bpy.data.lights.new(PREFIX+label+name,'AREA');data.energy=power;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj);obj.location=pos;obj.rotation_euler=(Vector((0,5,1))-obj.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new(PREFIX+label+'camera');cam=bpy.data.objects.new(data.name,data);scene.collection.objects.link(cam);scene.camera=cam;cam.data.lens=34
    bpy.context.window.scene=scene
    if views is None:views={'whole':((29,30,23),(0,5,3.1)),'stalls':((.0,12.4,2.40),(0,-1.8,3.65)),'reverse':((0,1.6,3.2),(0,16,4.4))}
    for view,(position,target)in views.items():
        cam.location=position;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(OUT/f'{label}-{view}.png');bpy.ops.render.render(write_still=True)


def verify(objects,seats,baseline):
    floors=[o for o in objects if o.name in [PREFIX+'stalls_floor_tiers',PREFIX+'circle_floor_tiers']]
    vertices=[];faces=[]
    for obj in floors:
        offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices);faces.extend(tuple(offset+i for i in p.vertices)for p in obj.data.polygons)
    tree=BVHTree.FromPolygons(vertices,faces)
    misses=[];height_errors=[]
    for i,seat in enumerate(seats):
        hit=tree.ray_cast(Vector((seat['x'],seat['y'],seat['floor']+.05)),Vector((0,0,-1)),.12)
        if hit[0]is None:misses.append(i)
        else:height_errors.append(abs(hit[0].z-seat['floor']))
    assert not misses,misses
    assert max(height_errors)<.002
    for obj in objects:
        assert obj.type=='MESH' and len(obj.data.uv_layers)==1
        assert all(math.isfinite(v)for vert in obj.data.vertices for v in vert.co)
        assert len(obj.data.uv_layers[0].data)==len(obj.data.loops)
    assert all(fingerprint(bpy.data.objects[name])==value for name,value in baseline.items())
    dimensions={o.name:[round(v,5)for v in o.dimensions]for o in objects}
    return dict(savedComponentReopened=True,originalGeometryUVTransformsPreserved=True,baselineObjectCount=len(baseline),componentObjectCount=len(objects),seatCount=len(seats),stallsSeats=sum(s['level']=='stalls'for s in seats),circleSeats=sum(s['level']=='circle'for s in seats),seatSupportRays=len(seats),seatSupportMisses=misses,maxSeatFloorError=max(height_errors),finiteVertices=True,uvComplete=True,prosceniumOpening=[13,5.9],prosceniumUndersideZ=6.95,stageDeckZ=1.05,stageDepth=10.7,stallsRows=22,circleSectionAnchors=8,stallsAisles=4,dimensions=dimensions,independentLocalRoom=True,campusCollectionUnchanged=True)


def main():
    assert sha(BASE)==BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    source=bpy.data.collections[DESTINATION];originals={o.name:fingerprint(o)for o in bpy.data.objects};source_names=sorted(o.name for o in source.all_objects)
    assert len(source_names)==22
    campus=set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())
    collection=bpy.data.collections.new(PREFIX+'component')
    builder,objects=build_room(collection)
    names=sorted(o.name for o in objects)
    bpy.data.libraries.write(str(COMPONENT),set(objects),fake_user=True,compress=True)
    # Reopen the original source and append only owned objects. This independently
    # checks native serialization without ever writing the source campus.
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    with bpy.data.libraries.load(str(COMPONENT),link=False)as(available,loaded):
        assert set(available.objects)==set(names);loaded.objects=names.copy()
    reopened=list(loaded.objects)
    review=bpy.data.collections.new(PREFIX+'reopened')
    for obj in reopened:review.objects.link(obj)
    for layer in bpy.context.scene.view_layers:layer.update()
    proof=verify(reopened,builder.seats,originals)
    assert campus==set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())
    proof.update(baselineSha256=sha(BASE),componentSha256=sha(COMPONENT),addedObjects=names,archivedObjects=source_names,originalObjectAliases=[])
    (OUT/'verification.json').write_text(json.dumps(proof,indent=2)+'\n')
    audit=dict(baseline=str(BASE.relative_to(ROOT)),baselineSha256=BASE_SHA,component=str(COMPONENT.relative_to(ROOT)),componentSha256=sha(COMPONENT),destinationCollection=DESTINATION,ownedObjects=names,addedObjects=names,archivedObjects=source_names,originalObjectAliases=[],changes=[dict(owned=name,destinationCollection=DESTINATION,retainNewMaterials=True)for name in names],interiorView=dict(position=[0,12.4,2.40],target=[0,-1.8,3.65]),scope=SCOPE,sourceDate='DWG2022; technical PDF filename February2023, header November2022; official photos uploaded July2023',sourceUrls=['https://www.sadlerswells.com/about-us/technical-specifications/sadlers-wells-theatre/peacock-theatre/','https://sadlers-wells-assets.s3.amazonaws.com/uploads/2023/02/Peacock-Theatre-Stage-Auditorium-Plan-2022.zip','https://sadlers-wells-assets.s3.amazonaws.com/uploads/2023/02/Peacock-Theatre-Technical-Specification-Feb-2023.pdf'],sourceRecheck='2026-10-15: official index still links archived2022DWG and2023PDF, despite index label January2024; no2026fitout asserted',layoutEvidence=['64 original stalls bank arcs,22 centre samples and22 section floor anchors','8 Circle section floor anchors and cantilever relationship','4 longitudinal stalls aisles,700/299 nominal capacities from2022specification'],limitations=['Actual individual seat coordinates and Circle plan are not provided in inspected DWG; spacing and Circle width estimated','Modeled seat count is a visual sample, not999 capacity certification','Backstage, foyer, whole building perimeter and current2026fitout excluded','Right and rear auditorium walls and ceiling omitted for this cutaway'],seatCount=proof['seatCount'],stallsSeats=proof['stallsSeats'],circleSeats=proof['circleSeats'])
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    (OUT/'seat-placements.json').write_text(json.dumps(builder.seats,indent=2)+'\n')
    render_objects(list(bpy.data.collections[DESTINATION].all_objects),'before')
    render_objects(reopened,'after')
    assert sha(BASE)==BASE_SHA
    print('PEA207_VERIFIED',len(names),proof['seatCount'],sha(COMPONENT),flush=True)
    bpy.ops.wm.quit_blender()


if __name__=='__main__':main()
