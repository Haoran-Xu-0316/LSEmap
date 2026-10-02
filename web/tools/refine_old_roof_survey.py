"""Reconstruct OLD's stepped roofs from the 2024 roof plan and sections.
Run in Blender Text Editor. Original objects and the detailed entry are retained.
Roof outlines, optical finishes, plant shapes and unlabelled heights are estimates.
"""
from pathlib import Path
import array,hashlib,json,math,shutil,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage113'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v112.blend'))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
plan=json.loads((OUT/'old-roof-survey-geometry.json').read_text())
origin,right,normal=[Vector(plan[k])for k in ['origin','right','outward']]
angle=math.atan2(right.y,right.x)
def fingerprint(o):
    h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
    if o.type=='MESH':
        v=array.array('f',[0])*(3*len(o.data.vertices));i=array.array('i',[0])*len(o.data.loops)
        o.data.vertices.foreach_get('co',v);o.data.loops.foreach_get('vertex_index',i)
        h.update(v.tobytes());h.update(i.tobytes())
    h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
before={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:o.hide_render for o in bpy.data.objects}
archived=[]
for name in ['OLD_V112_retained_Secondary_roof_deck','OLD_D5_houghton112_terrace-decks_roof']:
    o=bpy.data.objects[name];assert not o.hide_render
    o.hide_render=True;o.hide_set(True);archived.append(name)
materials.clear()
for key,source in [('stone','OLD_V52_stone'),('brick','OLD_V77_mansard_brick'),('blue','OLD_Blue_painted_steel')]:
    materials[key]=bpy.data.materials[source].copy();materials[key].name='OLD_V113_'+key
for key,c,rough,metal in [('roof',(.29,.31,.31),.82,0),('glass',(.19,.24,.26),.17,.10),
                          ('frame',(.21,.24,.25),.50,.35),('plant',(.58,.61,.60),.54,.25),
                          ('screen',(.40,.43,.41),.75,.10),('grille',(.12,.15,.16),.70,.30)]:
    m=bpy.data.materials.new('OLD_V113_'+key);m.use_nodes=True;m.diffuse_color=(*c,1)
    p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=m.diffuse_color
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;materials[key]=m
batches={}
def batch(family,key):
    k=family+'_'+key
    if k not in batches:batches[k]=Geometry('OLD','roof113_'+k,key)
    return batches[k]
def point(x,y,z):return origin+right*x+normal*y+Vector((0,0,z))
def box(family,key,x,y,z,w,d,h):
    if min(w,d,h)>.000001:batch(family,key).box(point(x,y,z),(w,d,h),angle)
def face(family,key,coords):batch(family,key).add([point(*p)for p in coords],[tuple(reversed(range(len(coords))))])
def bar(family,key,a,b,radius=.025):
    a,b=point(*a),point(*b);v=b-a;t=v.normalized();u=t.cross(Vector((0,0,1)))
    if u.length<.01:u=right.copy()
    u.normalize();w=t.cross(u)
    vertices=[p+radius*(u*math.cos(i*math.tau/8)+w*math.sin(i*math.tau/8))for p in [a,b]for i in range(8)]
    faces=[(i,(i+1)%8,(i+1)%8+8,i+8)for i in range(8)]+[tuple(reversed(range(8))),tuple(range(8,16))]
    batch(family,key).add(vertices,faces)
for region in plan['roofRegions']:
    for t in region['triangles']:face('decks','roof',[(*p,region['height'])for p in t])
# Close level changes around the lower courtyard and upper blocks. Partition
# wall panels around real openings rather than placing glass on an opaque slab.
openings=[]
for edge in plan['risers']:
    a,b=[Vector(p)for p in [edge['a'],edge['b']]];axis=(b-a).normalized();length=(b-a).length
    outward=Vector((axis.y,-axis.x));theta=angle+math.atan2(axis.y,axis.x)
    # Local y points out of the roof edge in the Houghton coordinate system.
    world_axis=right*axis.x+normal*axis.y
    theta=math.atan2(world_axis.y,world_axis.x)
    def p(x,d,z):
        q=a+axis*x+outward*d;return point(q.x,q.y,z)
    def panel(key,x,z,w,h,depth=0,thickness=.14):
        batch('risers',key).box(p(x,depth,z),(w,thickness,h),theta)
    knots=sorted({edge['low'],edge['high'],*[z for z in [16.5,20.1,23.79,27.14]if edge['low']<z<edge['high']]})
    count=max(1,round(length/2.7));pitch=length/count
    for low,high in zip(knots,knots[1:]):
        glazing=high-low>1.8 and length>2.0
        for i in range(count):
            x=(i+.5)*pitch
            if not glazing:
                panel('stone',x,(low+high)/2,pitch,high-low);continue
            w=min(1.6,pitch*.70);lo=low+.55;hi=high-.40
            for side in [-1,1]:panel('brick',x+side*(pitch+w)/4,(low+high)/2,(pitch-w)/2,high-low)
            panel('brick',x,(low+lo)/2,w,lo-low);panel('brick',x,(hi+high)/2,w,high-hi)
            panel('glass',x,(lo+hi)/2,w,hi-lo,depth=.018,thickness=.035)
            for side in [-1,1]:panel('blue',x+side*(w/2-.025),(lo+hi)/2,.05,hi-lo,depth=.06,thickness=.08)
            for z in [lo,hi,(lo+hi)/2]:panel('blue',x,z,w,.04,depth=.06,thickness=.08)
            opening=p(x-w/4,.018,lo+(hi-lo)/4)
            direction=right*outward.x+normal*outward.y
            openings.append({'point':list(opening),'normal':list(direction),'edge':edge['zone']})
    panel('stone',length/2,edge['high']+.075,length,.15,depth=.015,thickness=.30)
# Central double-pitch glazed roof. AA distinguishes the visible gable from
# the semicircular ceiling underneath; the barrel is not used as its exterior.
def bounds(shape):
    return min(p[0]for p in shape),max(p[0]for p in shape),min(p[1]for p in shape),max(p[1]for p in shape)
a,b,c,d=bounds(plan['skylight']['outline']);mid=(a+b)/2;base=plan['skylight']['base'];ridge=plan['skylight']['ridge']
def gable_z(x):return base+(ridge-base)*(1-abs(x-mid)/((b-a)/2))
for lo,hi in [(a,mid),(mid,b)]:
    face('skylight','glass',[(lo,c,gable_z(lo)),(hi,c,gable_z(hi)),(hi,d,gable_z(hi)),(lo,d,gable_z(lo))])
    for k in range(13):
        y=c+(d-c)*k/12;bar('skylight','frame',(lo,y,gable_z(lo)+.025),(hi,y,gable_z(hi)+.025))
    for k in range(5):
        x=lo+(hi-lo)*k/4;bar('skylight','frame',(x,c,gable_z(x)+.025),(x,d,gable_z(x)+.025))
for y in [c,d]:
    face('skylight-ends','glass',[(a,y,base),(b,y,base),(mid,y,ridge)])
    bar('skylight-ends','frame',(mid,y,base),(mid,y,ridge))
# Independent opaque curved roof at Clare Market, shown in DD. Its curvature
# and metal finish are estimates; it is not misrepresented as a glass atrium.
a,b,c,d=bounds(plan['barrel']['outline']);base=plan['barrel']['base'];rise=plan['barrel']['rise']
for k in range(32):
    x0=a+(b-a)*k/32;x1=a+(b-a)*(k+1)/32
    z0=base+rise*math.sin(math.pi*k/32);z1=base+rise*math.sin(math.pi*(k+1)/32)
    face('barrel','roof',[(x0,c,z0),(x1,c,z1),(x1,d,z1),(x0,d,z0)])
for y in [c,d]:
    coords=[(a,y,base),(b,y,base)]+[(a+(b-a)*k/32,y,base+rise*math.sin(math.pi*k/32))for k in range(31,0,-1)]
    face('barrel-ends','stone',coords)
# Small northern pavilion: double-pitch cap follows the AA section profile.
a,b,c,d=bounds(plan['room']['outline']);base=plan['room']['base'];height=plan['room']['height'];eave=base+height-.45
for v in [[(a,c,base),(b,c,base),(b,c,eave),(a,c,eave)],[(b,c,base),(b,d,base),(b,d,eave),(b,c,eave)],
          [(b,d,base),(a,d,base),(a,d,eave),(b,d,eave)],[(a,d,base),(a,c,base),(a,c,eave),(a,d,eave)]]:face('pavilion','brick',v)
mx=(a+b)/2;my=(c+d)/2
face('pavilion-cap','roof',[(a,c,eave),(b,c,eave),(b,my,base+height),(a,my,base+height)])
face('pavilion-cap','roof',[(a,my,base+height),(b,my,base+height),(b,d,eave),(a,d,eave)])
for x in [a,b]:face('pavilion-gables','brick',[(x,c,eave),(x,d,eave),(x,my,base+height)])
box('pavilion-door','frame',b+.03,my,base+1.05,.07,1.0,2.1)
# Two stepped acoustic enclosures, open above the three distinct heat pumps.
for screen in plan['plant']['screens']:
    outline=screen['outline'];low,high=screen['base'],screen['height']
    for a,b in zip(outline,outline[1:]+outline[:1]):
        axis=Vector(b)-Vector(a);length=axis.length;axis.normalize();centre=(Vector(a)+Vector(b))/2
        world_axis=right*axis.x+normal*axis.y;theta=math.atan2(world_axis.y,world_axis.x)
        for z in [low+.17,high-.075]:batch('screen','frame').box(point(*centre,z),(length,.18,.15),theta)
        count=max(1,round(length/.35))
        for i in range(count):
            q=Vector(a)+axis*length*(i+.5)/count
            batch('screen','screen').box(point(*q,(low+high)/2),(length/count-.025,.14,high-low-.25),theta)
# Platforms, housings, eight schematic fans per plan symbol and access treads.
for index,(centre,unit_base,dim)in enumerate(zip(plan['plant']['centres'],plan['plant']['bases'],plan['plant']['dimensions'])):
    x,y=centre;w,depth,h=dim;roof=27.14 if index<2 else 28.44
    box('platform','frame',x,y,unit_base-.10,w+.7,depth+.7,.20)
    for sx in [-1,1]:
        for sy in [-1,1]:box('platform','frame',x+sx*(w/2+.22),y+sy*(depth/2+.22),(roof+unit_base)/2,.07,.07,unit_base-roof)
    box('heat-pumps','plant',x,y,unit_base+h/2,w,depth,h)
    for sx in [-1,1]:
        for k in range(15):box('heat-pumps','grille',x+sx*(w/2+.008),y,unit_base+.25+k*(h-.50)/14,.022,depth-.20,.036)
    columns,rows=(2,4)if index<2 else(4,2)
    for ix in range(columns):
        for iy in range(rows):
            fx=x+w*((ix+.5)/columns-.5);fy=y+depth*((iy+.5)/rows-.5)
            radius=min(w/columns,depth/rows)*.30
            vs=[point(fx+radius*math.cos(k*math.tau/24),fy+radius*math.sin(k*math.tau/24),unit_base+h+.012)for k in range(24)]
            batch('fans','grille').add(vs,[tuple(range(24))])
    if unit_base-roof>.3:
        steps=6;span=1.8
        for k in range(steps):
            top=roof+(unit_base-roof)*(k+1)/steps
            box('access-steps','frame',x,y-depth/2-.35-span+(k+.5)*span/steps,(roof+top)/2,.90,span/steps,top-roof)
# Exposed edge protection around the upper roof, avoiding shared internal joins.
for edge in plan['risers']:
    if edge['high']<27:continue
    a,b=edge['a'],edge['b'];z=edge['high'];length=math.dist(a,b)
    for h in [.08,1.05]:bar('guardrails','frame',(*a,z+h),(*b,z+h),.020)
    count=max(1,round(length/1.5))
    for i in range(count+1):
        q=[a[k]+(b[k]-a[k])*i/count for k in range(2)];bar('guardrails','frame',(*q,z+.08),(*q,z+1.05),.020)
added=[]
for g in batches.values():
    obj=g.finish();added.append(obj.name)
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    obj['scope']='2024 roof plan and AA/BB/DD sections; unlabelled outlines and plant detail estimated'
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[n])==h for n,h in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage112'/name,OUT/name)
audit={'version':113,'baseline':112,'originalFingerprints':before,'originalVisibility':visibility,
       'archived':archived,'addedObjects':added,'glazingProbes':openings,'plan':plan,
       'limits':plan['limits']}
(OUT/'old-roof-survey-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v113.blend'))
print('OLD_ROOF_SURVEY_SAVED',len(added),len(openings),flush=True)
