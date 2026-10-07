"""Build two independent historical room samples from paired LSE sources.

Call build_room_samples() in a loaded campus. No campus source is opened or saved.
CBG.1.04: seven six-seat groups. CKK.1.07:50 red seats in six unequal rows.
Plan scales, hidden construction and heights are estimates, never a2026survey.
"""
from pathlib import Path
import hashlib
import math
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
PALETTE={'wall':(.76,.77,.73),'white':(.85,.86,.81),'seat':(.79,.82,.79),
 'red':(.64,.025,.032),'carpet':(.13,.15,.15),'ckk_carpet':(.31,.32,.29),
 'dark':(.035,.045,.047),'steel':(.46,.49,.48),'glass':(.53,.65,.66),
 'blind':(.10,.11,.105),'baffle':(.025,.075,.13),'duct':(.66,.69,.67),
 'light':(.92,.92,.84),'screen':(.79,.81,.78)}
ROOMS=[('CBG','CBG.1.04','CBG104_ROOM167_study','cbg-104',42),
       ('CKK','CKK.1.07','CKK107_ROOM167_study','ckk-107',50)]


class RoomGeometry:
    """Batch by construction family/material with metric UVs on every face."""
    def __init__(self,collection,prefix):
        self.collection,self.prefix=collection,prefix
        self.batches={};self.materials={};self.solid_proof={}
        for key,color in PALETTE.items():
            mat=bpy.data.materials.new(prefix+key);mat.use_nodes=True;mat.diffuse_color=(*color,1)
            shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color
            shader.inputs['Roughness'].default_value=.78
            if key=='steel':shader.inputs['Metallic'].default_value=.5;shader.inputs['Roughness'].default_value=.38
            if key=='glass':shader.inputs['Transmission Weight'].default_value=.88;shader.inputs['Roughness'].default_value=.14;mat['webOpacity']=.25
            if key=='light':shader.inputs['Emission Color'].default_value=(*color,1);shader.inputs['Emission Strength'].default_value=.5
            self.materials[key]=mat
    def add(self,family,material,vertices,faces):
        vertices=[Vector(v) for v in vertices]
        # Each added component is closed and consistently wound outward.
        edges={}
        for face in faces:
            for a,b in zip(face,face[1:]+face[:1]):
                edge=(min(a,b),max(a,b));count,balance=edges.get(edge,(0,0))
                edges[edge]=(count+1,balance+(1 if a<b else -1))
        assert all(count==2 and balance==0 for count,balance in edges.values()), (family,'inconsistent edge winding')
        center=sum(vertices,Vector())/len(vertices)
        signed_volume=0
        for face in faces:
            a=vertices[face[0]]-center
            for i in range(1,len(face)-1):
                signed_volume += a.dot((vertices[face[i]]-center).cross(vertices[face[i+1]]-center))/6
        assert signed_volume>1e-9, (family,'nonpositive signed volume',signed_volume)
        proof=self.solid_proof.setdefault(family,{'closedComponents':0,'minimumSignedVolume':signed_volume,'allEdgesOppositelyPaired':True})
        proof['closedComponents']+=1;proof['minimumSignedVolume']=min(proof['minimumSignedVolume'],signed_volume)
        key=(family,material)
        vs,fs=self.batches.setdefault(key,([],[]));offset=len(vs);vs.extend(tuple(v) for v in vertices)
        fs.extend(tuple(offset+i for i in f) for f in faces)
    def box(self,family,material,center,size,angle=0):
        c,s=math.cos(angle),math.sin(angle);vs=[]
        for a,b,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]:
            x,y=a*size[0]/2,b*size[1]/2
            vs.append((center[0]+c*x-s*y,center[1]+s*x+c*y,center[2]+z*size[2]/2))
        self.add(family,material,vs,[(2,6,4,0),(5,7,3,1),(4,5,1,0),(3,7,6,2),(1,3,2,0),(6,7,5,4)])
    def prism(self,family,material,outline,z,h):
        outline=list(outline)
        area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(outline,outline[1:]+outline[:1]))
        assert abs(area)>1e-10
        if area<0:outline.reverse()
        n=len(outline);vs=[(x,y,level) for level in [z,z+h] for x,y in outline]
        self.add(family,material,vs,[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])
    def tube(self,family,material,a,b,r=.015):
        a,b=Vector(a),Vector(b);d=(b-a).normalized();u=d.cross(Vector((0,0,1)))
        if u.length<.01:u=d.cross(Vector((0,1,0)))
        u.normalize();v=d.cross(u);n=8
        vs=[p+r*(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n)) for p in [a,b] for i in range(n)]
        self.add(family,material,vs,[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])
    def chair(self,x,y,angle=0,red=False):
        c,s=math.cos(angle),math.sin(angle)
        def at(a,b,z):return(x+c*a-s*b,y+s*a+c*b,z)
        if red:
            self.box('red_chair_seats','red',at(0,0,.45),(.46,.43,.045),angle)
            self.box('red_chair_backs','red',at(0,.225,.70),(.46,.047,.46),angle)
            for sx in [-1,1]:
                for sy in [-1,1]:self.tube('chair_black_legs','dark',at(sx*.19,sy*.19,.025),at(sx*.19,sy*.16,.44),.014)
        else:
            # Curved white shell, with black sled base, observed inCBG photograph.
            profile=[(-.23,.46),(-.10,.447),(.10,.451),(.21,.49),(.27,.64),(.28,.80),(.282,.90)]
            vs=[]
            for skin in [0,1]:
                for j,(py,pz) in enumerate(profile):
                    for i in range(7):
                        t=(i/6-.5)*2;vs.append(at(t*.23,py+(skin*.022 if j>=3 else 0),pz+(.022*t*t if j<4 else -.033*t*t)-(skin*.022 if j<3 else 0)))
            count=49;faces=[]
            for skin in range(2):
                for j in range(6):
                    for i in range(6):
                        a=skin*count+j*7+i;f=(a,a+1,a+8,a+7);faces.append(f if skin==0 else tuple(reversed(f)))
            for j in range(6):
                for i in [0,6]:
                    a=j*7+i;b=a+7;face=(a,b,b+count,a+count)
                    faces.append(face if i==0 else tuple(reversed(face)))
            for j in [0,6]:
                for i in range(6):
                    a=j*7+i;face=(a,a+1,a+1+count,a+count)
                    faces.append(tuple(reversed(face)) if j==0 else face)
            self.add('white_moulded_chair_shells','seat',vs,faces)
            for sx in [-1,1]:
                self.tube('chair_sleds','dark',at(sx*.20,-.28,.025),at(sx*.20,.29,.025),.012)
                self.tube('chair_sleds','dark',at(sx*.20,-.28,.025),at(sx*.19,-.12,.43),.012)
                self.tube('chair_sleds','dark',at(sx*.20,.29,.025),at(sx*.19,.15,.45),.012)
    def finish(self):
        objects=[]
        for (family,key),(vs,fs) in self.batches.items():
            mesh=bpy.data.meshes.new(self.prefix+family);mesh.from_pydata(vs,[],fs);mesh.materials.append(self.materials[key]);mesh.update()
            uv=mesh.uv_layers.new(name='SurfaceUV')
            for face in mesh.polygons:
                points=[mesh.vertices[i].co for i in face.vertices];u=(points[1]-points[0]).normalized();v=face.normal.cross(u)
                for index,p in zip(face.loop_indices,points):uv.data[index].uv=((p-points[0]).dot(u),(p-points[0]).dot(v))
            obj=bpy.data.objects.new(mesh.name,mesh);self.collection.objects.link(obj);objects.append(obj)
        used={m for obj in objects for m in obj.data.materials}
        for mat in self.materials.values():
            if mat not in used and mat.users==0:bpy.data.materials.remove(mat)
        return objects


def curved_table(g,x,y,angle):
    corners=[Vector((.96*math.cos(angle+i*math.tau/3),.96*math.sin(angle+i*math.tau/3))) for i in range(3)]
    outline=[]
    for i,a in enumerate(corners):
        b,c=corners[(i+1)%3],corners[(i+2)%3]
        start=.87*a+.13*b;end=.13*a+.87*b;middle=(a+b)/2;control=middle+middle.normalized()*.12
        for j in range(8):
            t=j/8;v=(1-t)**2*start+2*t*(1-t)*control+t*t*end;outline.append((x+v.x,y+v.y))
        next_start=.87*b+.13*c
        for j in range(4):
            t=j/4;v=(1-t)**2*end+2*t*(1-t)*b+t*t*next_start;outline.append((x+v.x,y+v.y))
    g.prism('seven_three_lobed_tabletops','white',outline,.74,.045)
    seats=[]
    for i,a in enumerate(corners):
        g.tube('table_steel_legs','steel',(x+a.x*.66,y+a.y*.66,.025),(x+a.x*.68,y+a.y*.68,.736),.032)
        b=corners[(i+1)%3];normal=((a+b)/2).normalized()
        for t in [.30,.70]:
            q=a.lerp(b,t)+normal*.53;px,py=x+q.x,y+q.y
            g.chair(px,py,math.atan2(normal.y,normal.x)-math.pi/2);seats.append([px,py])
    return seats


def cbg104(g):
    scale=.032
    def p(x,y):return((x-335)*scale,(y-491)*scale)
    x0,y0=p(159,322);x1,y1=p(512,660)
    g.box('floor','carpet',((x0+x1)/2,(y0+y1)/2,-.08),(x1-x0,y1-y0,.16))
    for x in [x0-.05,x1+.05]:g.box('cutaway_side_walls','wall',(x,(y0+y1)/2,.17),(.1,y1-y0,.34))
    # Plan places one rear door aroundx321; leaf construction is unknown.
    dx=p(323,660)[0]
    for a,b in [(x0,dx-.6),(dx+.6,x1)]:g.box('cutaway_rear_wall','wall',((a+b)/2,y1+.05,.17),(b-a,.1,.34))
    g.box('rear_door_plan_marker','steel',(dx,y1,.015),(1.2,.10,.02))
    g.box('front_head','wall',(0,y0,3.5),(x1-x0,.3,.30))
    for x in [x0+.12,x1-.12]:g.box('front_piers','wall',(x,y0,1.75),(.24,.28,3.5))
    for a,b in [(x0+.25,-1.6),(-1.6,1.6),(1.6,x1-.25)]:
        g.box('front_glass','glass',((a+b)/2,y0,1.68),(b-a,.03,3.20))
        for x in [a,b]:g.box('front_mullions','steel',(x,y0+.04,1.70),(.055,.08,3.28))
    # Photo shows clear flanking windows and dark backing around the screen.
    sx=p(340,322)[0]
    g.box('screen_frame','dark',(sx,y0+.19,2.12),(3.08,.08,2.32));g.box('projection_screen','screen',(sx,y0+.242,2.12),(2.92,.025,2.17))
    g.box('central_screen_blackout_backing','blind',(sx,y0+.08,1.68),(3.38,.025,3.12))
    for x in [sx-2.52,sx+2.52]:
        g.box('front_speakers','white',(x,y0+.23,3.03),(.37,.22,.40))
        g.tube('speaker_hangers','steel',(x,y0+.15,3.23),(x,y0+.15,3.56),.011)
    lx,ly=p(422,375);g.box('photo_av_lectern','steel',(lx,ly,.56),(.98,.65,1.12));g.box('lectern_top','dark',(lx,ly,1.14),(1.10,.75,.055))
    g.box('lectern_monitor','dark',(lx+.15,ly-.04,1.40),(.45,.07,.29));g.tube('lectern_monitor_stand','steel',(lx+.15,ly,1.16),(lx+.15,ly,1.31),.02)
    seats=[];tables=[]
    for px,py,angle in [(240,388,math.pi/2),(333,405,-math.pi/2),(442,463,math.pi/2),(218,495,math.pi/2),(221,591,-math.pi/2),(333,560,math.pi/2),(442,578,-math.pi/2)]:
        x,y=p(px,py);seats+=curved_table(g,x,y,angle);tables.append({'planPixel':[px,py],'center':[x,y],'orientation':angle,'seats':6})
    for x in [-4.1,-1.4,1.4,4.1]:
        g.tube('exposed_front_ducts','duct',(x,y0+.15,3.72),(x,y0+2.12,3.72),.16)
        outline=[(x+.88*math.cos(i*math.tau/32),y0+.94+.51*math.sin(i*math.tau/32)) for i in range(32)]
        g.prism('blue_front_acoustic_rafts','baffle',outline,3.16,.06)
    for y in [y0+.22,y0+1.86]:g.box('linear_light_bodies','steel',(0,y,3.33),(x1-x0-.5,.11,.075));g.box('linear_diffusers','light',(0,y,3.281),(x1-x0-.55,.075,.023))
    g.box('ceiling_projector','white',(0,y0+1.05,3.72),(.56,.46,.24));g.box('projector_lens','dark',(0,y0+.809,3.70),(.11,.025,.11))
    return seats,{'tableCount':7,'groups':tables,'estimatedMetersPerPlanPixel':scale,'roomBounds':[x0,y0,x1,y1]}


def ckk107(g):
    scale=.023
    def p(px,py):return((py-295)*scale,(px-275)*scale)
    x0,y0=p(20,60);x1,y1=p(520,520)
    g.box('floor','ckk_carpet',((x0+x1)/2,(y0+y1)/2,-.08),(x1-x0,y1-y0,.16))
    for x in [x0-.05,x1+.05]:g.box('cutaway_side_walls','wall',(x,(y0+y1)/2,.17),(.10,y1-y0,.34))
    # Rear/right-side door positions retained as floor markers from the plan;
    # unknown door heights, swings and corridor connections are not fabricated.
    for py in [195,278,378]:
        dx,dy=p(520,py);g.box('rear_door_plan_markers','steel',(dx,dy,.015),(.94,.1,.02))
    dx,dy=p(100,520);g.box('side_door_plan_marker','steel',(dx,dy,.015),(.1,1.08,.02))
    g.box('front_wall','wall',((x0+x1)/2,y0-.08,1.62),(x1-x0,.16,3.24))
    screen_x=p(20,247)[0]
    g.box('screen_frame','dark',(screen_x,y0+.055,1.89),(3.28,.09,2.43));g.box('projection_screen','screen',(screen_x,y0+.114,1.89),(3.07,.025,2.25))
    g.box('mobile_whiteboard','white',(screen_x+3.24,y0+.34,1.51),(2.34,.08,1.56))
    for x in [screen_x+4.04,screen_x+2.43]:g.tube('whiteboard_trolley','steel',(x,y0+.34,.06),(x,y0+.34,.79),.025)
    # Lecturer station on photo right; plan front-right desk traced.
    lx,ly=p(93,129);g.box('lecturer_desk','white',(lx,ly,.75),(2.06,.75,.055))
    for sx in [-.86,.86]:g.box('lecturer_desk_piers','steel',(lx+sx,ly,.36),(.055,.58,.70))
    g.box('lecturer_monitor','dark',(lx+.30,ly-.12,1.06),(.46,.075,.31));g.tube('monitor_stand','steel',(lx+.3,ly,.79),(lx+.3,ly,1.00),.02)
    seats=[];rows=[]
    # Exactly50 student symbols, excluding the separate lecturer chair.
    for px,count in [(168,8),(232,8),(296,10),(360,10),(424,8),(488,6)]:
        plan_ys=[86+40.5*i for i in range(count)]
        centers=[p(px,py) for py in plan_ys]
        for x,y in centers:g.chair(x,y,red=True);seats.append([x,y])
        left,right=min(p[0] for p in centers)-.44,max(p[0] for p in centers)+.44;depth=centers[0][1]-.41
        g.box('six_continuous_white_table_rows','white',((left+right)/2,depth,.75),(right-left,.51,.05))
        for x in [left+.20,right-.20,(left+right)/2]:g.box('table_row_steel_supports','steel',(x,depth,.36),(.05,.43,.70))
        rows.append({'planColumnX':px,'planSeatYs':plan_ys,'seats':count,'tableSpan':[left,right],'tableY':depth})
    # Two windows along the plan top wall; panes/blinds approximate and cut away.
    for px,width in [(168,1.55),(275,1.75)]:
        wx,wy=p(px,65);g.box('plan_side_window_glass','glass',(wx,wy,1.74),(.03,width,1.66))
        for yy in [wy-width/2,wy+width/2]:g.box('window_jambs','steel',(wx+.03,yy,1.74),(.06,.04,1.74))
        g.box('blackout_window_blinds','blind',(wx+.05,wy,2.38),(.025,width, .34))
    g.box('front_ceiling_soffit','wall',((x0+x1)/2,y0+.82,3.14),(x1-x0,1.68,.16))
    for x in [-3.6,-.2,3.2]:g.box('ceiling_light_diffusers','light',(x,y0+.82,3.049),(.15,1.21,.018))
    g.box('projector_body','dark',(screen_x,y0+1.26,2.88),(.53,.43,.20));g.box('projector_lens','steel',(screen_x,y0+1.038,2.88),(.10,.025,.10))
    return seats,{'tableCount':6,'rows':rows,'estimatedMetersPerPlanPixel':scale,'roomBounds':[x0,y0,x1,y1],'tiering':'No steps asserted; plan has no metric level annotations'}


def build_room_samples():
    """Create separate room scenes, return complete exporter authoring records."""
    if all(bpy.data.collections.get(c) for _,_,c,_,_ in ROOMS):
        records=[]
        for _,_,c,_,_ in ROOMS:
            collection=bpy.data.collections[c];assert collection.get('roomSamples167')
            import json
            records.append(json.loads(collection['authoringRecord']))
        return {'alreadyApplied':True,'addedObjects':[o.name for _,_,c,_,_ in ROOMS for o in bpy.data.collections[c].all_objects],'collections':[c for _,_,c,_,_ in ROOMS],'spaces':records,'changedObjects':[],'archivedObjects':[]}
    assert not any(bpy.data.collections.get(c) for _,_,c,_,_ in ROOMS)
    photo_plan={
      'CBG.1.04':['a40c88749e8f_CBG.1.04.gif','332e97e2f95c_CBG.1.04.jpg'],
      'CKK.1.07':['9518577ee72b_CKK.1.07.GIF','e668d23ec609_CKK.1.07.jpg']}
    import json
    records=[];audits=[];added=[]
    for code,room,collection_name,space_id,capacity in ROOMS:
        collection=bpy.data.collections.new(collection_name);collection['roomSample']=True;collection['roomCode']=room;collection['roomSamples167']=True
        scene=bpy.data.scenes.new('ROOM167_'+room.replace('.',''));scene.collection.children.link(collection)
        g=RoomGeometry(collection,room.replace('.','')+'_R167_')
        seats,layout=cbg104(g) if code=='CBG' else ckk107(g)
        assert len(seats)==capacity
        spacing=min(math.dist(a,b) for i,a in enumerate(seats) for b in seats[i+1:]);assert spacing>.51,(room,spacing)
        objects=g.finish();added.extend(o.name for o in objects)
        for o in objects:o['roomCode']=room;o['scope']='Historical official room-only sample; dimensions/hidden construction estimated'
        chair=next(o for o in objects if 'chair_seats' in o.name or 'chair_shells' in o.name);chair['studentSeatCount']=capacity
        label=room+('分组教室' if code=='CBG' else '排式教室')
        scope=f'依据LSE官方同房号平面与照片建立{capacity}座历史教学室样本。桌椅位置按平面描摹，颜色与可见设备按照片估算；米制尺度、层高及不可见构造未测量。侧后墙和部分顶面剖开，不推测楼内连通，不代表2026年布置。'
        if code=='CKK':scope+='历史页面使用旧名NAB.1.07，同号CKK资产用于房间样本。'
        native_position=[14,15,12];target=[0,0,1.0]
        # Three.js export transforms Blender(x,y,z) to(x,z,-y).
        record={'id':space_id,'label':label,'code':code,'collection':collection_name,'scope':scope,
                'gallery':space_id+'-interior','interiorView':{'position':[14,12,-15],'target':[0,1,0],'fov':50},
                'interiorStudy':{'kind':'room-sample','label':label,'scope':scope}}
        collection['authoringRecord']=json.dumps(record,ensure_ascii=False);collection['studentSeatCount']=capacity
        refs=[]
        for file in photo_plan[room]:
            path=ROOT/'data/collections/interiors/images'/file
            suffix='photos/'+room+'.jpg' if file.lower().endswith('.jpg') else room+('.GIF' if code=='CKK' else '.gif')
            refs.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'url':'https://www.lse.ac.uk/assets/roomInformation/images/'+suffix,'captureDate':'unknown; historical archive, not2026survey'})
        page_name='8ebbe67b4538_3.htm' if code=='CBG' else '95464b86315e_2.htm'
        page=ROOT/'data/collections/interiors/pages'/page_name
        refs.append({'path':str(page.relative_to(ROOT)),'sha256':hashlib.sha256(page.read_bytes()).hexdigest(),'url':'https://www.lse.ac.uk/admin/timetables/confirmed_old/ttrooms/'+('cbg/3.htm' if code=='CBG' else 'nab/2.htm'),'pageRefresh':'17Aug2022 02:30; not photo creation date'})
        audits.append({'roomCode':room,'studentSeatCount':capacity,'seatCenters':seats,'minimumSeatCenterSpacing':spacing,'layout':layout,'closedSolidProof':g.solid_proof,'meshCount':len(objects),'sources':refs,'nativeCamera':native_position,'nativeTarget':target,'scene':scene.name,'authoring':record})
        records.append(record)
    return {'alreadyApplied':False,'addedObjects':added,'collections':[c for _,_,c,_,_ in ROOMS],'spaces':records,'roomAudits':audits,'changedObjects':[],'archivedObjects':[]}


def apply_room_samples167():
    """Assembly entry point, adding rooms without changing the campus scene."""
    return build_room_samples()
