"""Add the independently attributed 5LF townhouse; preserve edition 05.
Run inside Blender. Official LSE's address-map link supplies the location point;
the containing OSM polygon supplies the envelope. Vertical dimensions are estimates.
"""
from pathlib import Path
import json, math, sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, Facade, materials
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage06'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v05.blend'))
scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
building=next(b for b in site['buildings'] if b['id']=='way/1184094775')
root=next(c for c in bpy.data.collections['02_LSE_BUILDINGS'].children if c.name.startswith('5LF_'))
collection=bpy.data.collections.new('5LF_EXTERIOR');root.children.link(collection)
# Only the exact duplicate context envelope is replaced.
removed=[]
for o in list(bpy.data.collections['01_CITY_CONTEXT_estimated_heights'].objects):
    if o.name.startswith('Context_way/1184094775'):
        removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
assert removed,'Expected context envelope was not found'
colors={'brick':(.31,.25,.14),'white':(.72,.72,.68),'glass':(.085,.14,.17),'frame':(.69,.71,.70),'black':(.018,.022,.020),'slate':(.10,.12,.13),'clay':(.35,.15,.07)}
materials.clear()
for name,color in colors.items():
    m=bpy.data.materials.new('5LF_'+name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=.3 if name in {'glass','black'} else .8
    if name=='brick':
        n=m.node_tree.nodes;l=m.node_tree.links;uv=n.new('ShaderNodeTexCoord');t=n.new('ShaderNodeTexBrick');t.inputs['Scale'].default_value=1;t.inputs['Brick Width'].default_value=.225;t.inputs['Row Height'].default_value=.078;t.inputs['Mortar Size'].default_value=.006
        t.inputs['Color1'].default_value=(*color,1);t.inputs['Color2'].default_value=(.24,.19,.115,1);t.inputs['Mortar'].default_value=(.20,.19,.16,1);l.new(uv.outputs['UV'],t.inputs['Vector']);l.new(t.outputs['Color'],p.inputs['Base Color'])
    materials[name]=m
profile={'code':'5LF'};groups={};ring=building['rings'][0];height=14.0
for edge,(p,q) in enumerate(zip(ring,ring[1:]+ring[:1])):
    length=math.dist(p,q);u=Vector(((q[0]-p[0])/length,(q[1]-p[1])/length));n=Vector((u.y,-u.x));mid=(Vector(p)+Vector(q))/2
    if n.dot(mid-Vector(building['center']))<0:n=-n
    wall={'p':p,'q':q,'length':length,'outward':list(n)};f=Facade(profile,wall,groups)
    if edge==1:front=f
    if edge!=1:
        f.box('unobserved_envelope','brick',length/2,height/2,length,height)
        continue
    bands=[(0,4.3,.9,3.5),(4.3,8.0,4.75,7.4),(8.0,11.2,8.55,10.65),(11.2,14,11.72,13.38)]
    pitch=length/3
    for level,(z0,z1,lo,hi) in enumerate(bands):
        mat='white' if level==0 else 'brick'
        for bay in range(3):
            x=(bay+.5)*pitch;width=1.16 if level else 1.23
            f.box('pier',mat,x-pitch/2+(pitch-width)/4,(lo+hi)/2,(pitch-width)/2,hi-lo)
            f.box('pier',mat,x+pitch/2-(pitch-width)/4,(lo+hi)/2,(pitch-width)/2,hi-lo)
            f.box('spandrel',mat,x,(z0+lo)/2,pitch,lo-z0)
            f.box('head',mat,x,(hi+z1)/2,pitch,z1-hi)
            door=level==0 and bay==2
            f.box('door' if door else 'glass','black' if door else 'glass',x,(lo+hi)/2,width,hi-lo,.04,-.14)
            for side in [-1,1]:f.box('jamb','black' if door else 'frame',x+side*width/2,(lo+hi)/2,.06,hi-lo,.16,-.015)
            for z in [lo,hi,(lo+hi)/2]:f.box('horizontal_rail','black' if door else 'frame',x,z,width,.055,.12,0)
            if not door:f.box('sash_vertical','frame',x,(lo+hi)/2,.035,hi-lo,.08,0)
            if door:
                for z in [1.20,1.9,2.7]:f.box('door_panel','black',x,z,.85,.52,.065,-.06)
                f.box('door_handle','clay',x-.33,1.8,.045,.2,.08,.02)
            else:f.box('sill','white',x,lo-.055,width+.18,.12,.40,.035)
    for z in [4.28,14.08]:f.box('cornice','white' if z<5 else 'brick',length/2,z,length,.18,.42,.05)
    for z in [1.15,1.8,2.45,3.10,3.75]:f.box('ground_rustication','slate',length/2,z,length,.012,.012,.018)
    # Steps, railing and terminal piers follow the visible forecourt treatment.
    door_x=pitch*2.5
    for i in range(5):f.box('entry_step','slate',door_x,.08+i*.17,1.5,.16,.35,1.6-i*.28)
    for j in range(33):
        x=.12+j*(length-.24)/32
        if abs(x-door_x)<.8:continue
        f.box('railing_pickets','black',x,.78,.025,1.50,.025,1.9)
    for start,end in [(0,door_x-.8),(door_x+.8,length)]:
        for z in [.45,1.18]:f.box('railing_rails','black',(start+end)/2,z,end-start,.035,.035,1.9)
    for x in [.14,length-.14]:f.box('forecourt_pier','white',x,.94,.30,1.88,.34,1.9)
roof=Geometry('5LF','roof','slate')
for tri in building['triangles']:roof.add([(x,y,height) for x,y in tri],[(0,1,2)])
groups['roof']=roof
for x in [.3,front.length-.3]:
    front.box('chimney_stack','brick',x,14.95,.43,1.9,.85,-2.0)
    for offset in [-.2,.2]:front.box('chimney_pot','clay',x,16.03,.20,.40,.20,-2+offset)
for g in groups.values():g.finish()
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v06.blend'))
report={'code':'5LF','height':height,'floors':4,'exteriorDirection':[front.n.x,.6,-front.n.y],'scope':'Official LSE address-map point is inside the attributed OSM polygon. Front facade follows archived estate imagery; heights and rear geometry remain estimated.','osmId':building['id'],'sourcePoint':{'longitude':-.1182048,'latitude':51.5168142},'sourcePage':'https://info.lse.ac.uk/staff/services/faculty-accommodation/property-portfolio/five-lincolns-inn-fields','sourceMap':'https://goo.gl/maps/hm3DbTQC8eH2','removedContextObjects':removed}
(OUT/'attribution.json').write_text(json.dumps(report,indent=2)+'\n')
print('RESOLVED_5LF',report,flush=True)
