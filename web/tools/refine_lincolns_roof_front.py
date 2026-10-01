"""Add the photographed 51L front roof slope, dormers and metal edge rail.
Run in Blender Text Editor. Preserve native 92 and every original object.
The July 2025 LSE image supports front roof character only. Dimensions,
left obscured pediment and hidden dormer depth remain estimates.
"""
from pathlib import Path
import array, hashlib, json, math, shutil, sys
import bpy, bmesh
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage93'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v92.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text())if p['code']=='51L')
wall=profile['walls'][1]
origin=Vector((*wall['p'],0))
right=Vector(((wall['q'][0]-wall['p'][0])/wall['length'],(wall['q'][1]-wall['p'][1])/wall['length'],0))
normal=Vector((*wall['outward'],0))
length=wall['length']
base=20.98;rise=1.60;roof_depth=2.10
front_depth=.16;back_depth=1.12
window_width=.95;window_bottom=21.08;window_top=21.90
head=22.02;peak=22.70
pitch=length/3

def fingerprint(o):
    h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
    if o.type=='MESH':
        h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode())
    return h.hexdigest()
before={o.name:fingerprint(o)for o in bpy.data.objects}
materials.clear()
def material(key,color,roughness,metallic=0):
    m=bpy.data.materials.new('51L_V93_'+key);m.use_nodes=True
    m.diffuse_color=(*color,1)
    shader=m.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value=m.diffuse_color
    shader.inputs['Roughness'].default_value=roughness
    shader.inputs['Metallic'].default_value=metallic
    materials[key]=m
material('slate',(.075,.088,.099),.83)
material('stone',(.69,.67,.61),.78)
material('frame',(.76,.77,.74),.68)
material('recess',(.42,.41,.37),.85)
material('metal',(.48,.52,.51),.47,.65)
materials['glass']=bpy.data.materials['EXT20_glass']
groups={}
def batch(key):
    if key not in groups:groups[key]=Geometry('51L','roof93_'+key,key)
    return groups[key]
def point(x,depth,z):return origin+right*x+normal*depth+Vector((0,0,z))
def box(key,x,depth,z,w,t,h):batch(key).box(point(x,depth,z),(w,t,h),math.atan2(right.y,right.x))
def prism(key,outline,back,front):
    count=len(outline)
    vs=[point(x,d,z)for d in [back,front]for x,z in outline]
    faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]
    faces += [(j,(j+1)%count,(j+1)%count+count,j+count)for j in range(count)]
    batch(key).add(vs,faces)
def roof_panel(x0,x1,d0,d1):
    z0,z1=base+rise*(-d0)/roof_depth,base+rise*(-d1)/roof_depth
    vs=[point(x,d,z+offset)for offset in [-.06,0]for x,d,z in [(x0,d0,z0),(x1,d0,z0),(x1,d1,z1),(x0,d1,z1)]]
    batch('slate').add(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
def dormer_roof_panel(x0,x1,z0,z1):
    vs=[point(x,d,z+offset)for offset in [0,.055]for x,d,z in [(x0,-front_depth,z0),(x1,-front_depth,z1),(x1,-back_depth,z1),(x0,-back_depth,z0)]]
    batch('slate').add(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])

# Slots prevent the sloping slate surface from passing through dormer glazing.
half=.70
centers=[(i+.5)*pitch for i in range(3)]
spans=[(0,centers[0]-half)]
spans += [(centers[i]+half,centers[i+1]-half)for i in range(2)]
spans += [(centers[-1]+half,length)]
for x0,x1 in spans:roof_panel(x0,x1,-.04,-back_depth)
roof_panel(0,length,-back_depth,-roof_depth)
dormers=[]
for bay,x in enumerate(centers):
    # Positive edge coordinates map screen-left. The clear right pediment is curved.
    kind='segmental'if bay==0 else'triangular'
    lo,hi=window_bottom,window_top
    for side in [-1,1]:
        box('stone',x+side*(window_width/2+.075),-.145,(lo+hi)/2,.15,.17,hi-lo+.09)
        box('slate',x+side*.62,-(front_depth+back_depth)/2,(base+head)/2,.09,back_depth-front_depth,head-base)
    box('stone',x,-.145,lo-.06,window_width+.30,.21,.12)
    box('stone',x,-.145,hi+.07,window_width+.30,.21,.14)
    box('glass',x,-.20,(lo+hi)/2,window_width,.035,hi-lo)
    for side in [-1,1]:box('frame',x+side*window_width/2,-.105,(lo+hi)/2,.045,.07,hi-lo)
    for j in range(4):box('frame',x,-.10,lo+(hi-lo)*j/3,window_width,.07,.028)
    for j in [1,2]:box('frame',x-window_width/2+window_width*j/3,-.10,(lo+hi)/2,.025,.07,hi-lo)
    if kind=='triangular':
        outline=[(x-half,head),(x+half,head),(x,peak)]
        prism('stone',outline,-.19,-.075)
        # A shallow inset face separates the pediment panel from its pale surround.
        prism('recess',[(x-.48,head+.12),(x+.48,head+.12),(x,peak-.15)],-.083,-.073)
        dormer_roof_panel(x-half,x,head+.07,peak+.07)
        dormer_roof_panel(x,x+half,peak+.07,head+.07)
        back_outline=[(x-half,base),(x+half,base),(x+half,head),(x,peak),(x-half,head)]
    else:
        samples=[(-half+2*half*j/32,head+.64*(1-((-half+2*half*j/32)/half)**2))for j in range(33)]
        outline=[(x-half,head-.025),(x+half,head-.025)]+[(x+xx,z)for xx,z in reversed(samples)]
        prism('stone',outline,-.19,-.075)
        inner_half=.49
        inner=[(-inner_half+2*inner_half*j/24,head+.12+.38*(1-((-inner_half+2*inner_half*j/24)/inner_half)**2))for j in range(25)]
        prism('recess',[(x-inner_half,head+.10),(x+inner_half,head+.10)]+[(x+xx,z)for xx,z in reversed(inner)],-.083,-.073)
        for (x0,z0),(x1,z1)in zip(samples,samples[1:]):dormer_roof_panel(x+x0,x+x1,z0+.07,z1+.07)
        back_outline=[(x-half,base),(x+half,base)]+[(x+xx,z)for xx,z in reversed(samples)]
    prism('slate',back_outline,-back_depth-.025,-back_depth)
    dormers.append({'bay':bay,'centerX':x,'pediment':kind,'glassBottom':lo,'glassTop':hi,
                    'width':window_width,'frontDepth':front_depth,'backDepth':back_depth,
                    'scope':'Left triangular shape partly tree-obscured'if bay==2 else'Clear central triangular/right segmental silhouette'})
# Slim metal edge rail visibly spans the front in the published photograph.
for x in [0,pitch,2*pitch,length]:
    box('metal',x,.08,base+.40,.038,.038,.80)
for z in [base+.16,base+.80]:
    box('metal',length/2,.08,z,length+.08,.038,.038)
added=[]
for key,g in groups.items():
    obj=g.finish()
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free()
    added.append(obj.name)
assert all(fingerprint(bpy.data.objects[n])==value for n,value in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage92'/name,OUT/name)
if not(OUT/'catalogue-before.json').exists():shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
audit={'version':93,'baseline':92,'baselineFingerprint':before,'addedObjects':added,
       'frame':{'origin':list(origin),'right':list(right),'normal':list(normal),'length':length},
       'base':base,'rise':rise,'roofDepth':roof_depth,'dormers':dormers,
       'sourceUrl':'https://www.lse.ac.uk/global-school-of-sustainability/news/2025/first-recipients-Global-Sustainability-Research-Fund',
       'published':'2025-07-31','captureDate':None,
       'limitations':['Only photographed front roof band represented; rear roof layout unknown',
                      'Dimensions, hidden depth, glazing grid and left obscured pediment estimated',
                      'Original roof slab retained beneath the new front band',
                      'GIS chamfer still needs photographed rounded-corner correction']}
(OUT/'lincolns-roof-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v93.blend'))
print('LINCOLNS_ROOF_FRONT_SAVED',dormers,flush=True)
