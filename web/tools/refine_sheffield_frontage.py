"""Rebuild SHF's long Sheffield Street facade from attributed estate photographs.
Run in Blender's Text Editor. Native49 remains intact. Hidden native components
are retained as archives; roof depth and dimensions are estimates, not a survey.
"""
from pathlib import Path
import bpy,json,sys,math,hashlib,array
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage50';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,Facade,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v49.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
originals=list(bpy.data.objects)
def fingerprint(o):
    digest=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
    if o.type=='MESH':digest.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes())
    return digest.hexdigest()
before={o.name:fingerprint(o)for o in originals}
profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text())if p['code']=='SHF')
profile['front']=6;profile['height']=16.60;profile['floors']=5
hidden=[]
# Snapshot before visibility changes invalidate Blender's RNA collection iterator.
for o in list(bpy.data.collections['SHF_EXTERIOR'].all_objects):
    if not o.hide_render:o.hide_render=True;o.hide_set(True);hidden.append(o.name)
materials.clear()
colors={'brick':(.30,.235,.14),'white':(.76,.74,.69),'frame':(.78,.77,.71),'stone':(.48,.46,.40),'glass':(.20,.30,.34),'door':(.045,.052,.046),'metal':(.07,.08,.075),'slate':(.14,.17,.18),'leaf':(.11,.19,.065),'red':(.47,.008,.016)}
for key,color in colors.items():
    m=bpy.data.materials.new('SHF_V50_'+key);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=.78
    if key=='glass':p.inputs['Roughness'].default_value=.22;p.inputs['Metallic'].default_value=.15
    if key=='frame':p.inputs['Roughness'].default_value=.53
    if key=='brick':
        nodes=m.node_tree.nodes;links=m.node_tree.links;uv=nodes.new('ShaderNodeTexCoord');tex=nodes.new('ShaderNodeTexBrick')
        for name,value in [('Scale',1),('Brick Width',.225),('Row Height',.078),('Mortar Size',.006)]:tex.inputs[name].default_value=value
        tex.inputs['Color1'].default_value=(*color,1);tex.inputs['Color2'].default_value=tuple(c*.80 for c in color)+(1,);tex.inputs['Mortar'].default_value=(.32,.30,.24,1)
        links.new(uv.outputs['UV'],tex.inputs['Vector']);links.new(tex.outputs['Color'],p.inputs['Base Color'])
        bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.0015
        links.new(tex.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],p.inputs['Normal'])
    materials[key]=m
groups={};frontwall=dict(next(w for w in profile['walls']if w['index']==6))
# Use viewer-right coordinates so the door and fascia lettering retain the photo's order.
frontwall['p'],frontwall['q']=frontwall['q'],frontwall['p']
front=Facade(profile,frontwall,groups);L=front.length;pitch=L/4
centers=[pitch*(i+.5)for i in range(4)];windows=[]
def window(f,x,z,w,h,lights=4,rows=3,label='window'):
    f.box(label+'_glass','glass',x,z,w-.10,h-.10,.035,-.125)
    for side in [-1,1]:f.box(label+'_jamb','frame',x+side*(w/2-.035),z,.07,h,.13,-.035)
    for zz in [z-h/2,z+h/2]:f.box(label+'_frame','frame',x,zz,w,.075,.13,-.035)
    for j in range(1,lights):f.box(label+'_mullion','frame',x-w/2+w*j/lights,z,.038,h,.12,-.025)
    for j in range(1,rows):f.box(label+'_transom','frame',x,z-h/2+h*j/rows,w,.042,.12,-.025)
    f.box(label+'_sill','white',x,z-h/2-.055,w+.25,.11,.34,.035)

def wall_with_openings(f,z0,z1,holes,material):
    xs=sorted(set([0,f.length,*[v for h in holes for v in h[:2]]]));zs=sorted(set([z0,z1,*[v for h in holes for v in h[2:]]]))
    for x0,x1 in zip(xs,xs[1:]):
        for low,high in zip(zs,zs[1:]):
            if any(a<(x0+x1)/2<b and c<(low+high)/2<d for a,b,c,d in holes):continue
            f.box('wall','white'if material=='white'else material,(x0+x1)/2,(low+high)/2,x1-x0,high-low,.30,-.18)

holes_white=[];holes_brick=[]
levels=[(1.20,1.20),(4.30,2.20),(7.95,2.40),(11.65,2.40),(14.90,1.30)]
width=pitch*.69
for i,x in enumerate(centers):
    for level,(z,h)in enumerate(levels):
        if i==2 and level==0:continue
        holes=(x-width/2,x+width/2,z-h/2,z+h/2)
        (holes_white if level<2 else holes_brick).append(holes)
        window(front,x,z,width,h,4,2 if level in [0,1,4]else 3)
        windows.append({'bay':i,'level':level,'center':[x,z],'size':[width,h]})
        if level>=2:
            front.box('stone_lintel','white',x,z+h/2+.13,width+.42,.23,.30,.01)
            front.box('lintel_end','stone',x,z+h/2+.13,width+.68,.14,.34,.035)
# Entry below the third bay, with a black pair of doors and a glazed transom.
door_x=centers[2];door_w=2.30
holes_white.append((door_x-door_w/2,door_x+door_w/2,.08,3.12))
wall_with_openings(front,0,6.30,holes_white,'white');wall_with_openings(front,6.30,16.60,holes_brick,'brick')
for x in [door_x-door_w/2,door_x,door_x+door_w/2]:front.box('door_jamb','frame',x,1.60,.11,3.12,.20,.00)
for side in [-1,1]:
    x=door_x+side*door_w/4
    front.box('door_leaf','door',x,1.15,door_w/2-.09,2.10,.085,-.055)
    front.box('door_light','glass',x,2.28,door_w/2-.19,1.10,.035,.003)
    front.box('door_handle','metal',door_x+side*.12,1.16,.028,.43,.045,.045)
window(front,door_x,2.92,door_w,.35,4,1,'door_transom')
# Fascia, masonry cornices, white base plinth and recessed panel field.
for z,h,depth,offset in [(6.03,.54,.25,.03),(6.35,.13,.34,.06),(10.06,.18,.39,.07),(16.56,.20,.44,.10),(16.78,.14,.55,.14)]:
    front.box('continuous_cornice','white'if z<6.6 else 'stone',L/2,z,L,h,depth,offset)
for j in range(72):front.box('cornice_dentil','stone',(j+.5)*L/72,16.38,.10,.14,.28,.065)
for x in centers:front.box('base_plinth','door',x,.08,pitch,.16,.20,-.08)
front.label('SHEFFIELD ST.',L-2.55,6.03,.34,'metal',.19)
front.label('9 AND 10',L-1.50,5.66,.20,'metal',.19)
front.label('9  10',.79,6.03,.32,'metal',.19)
front.box('LSE_square','red',pitch*1.40,6.04,.40,.40,.045,.22)
front.label('LSE',pitch*1.40,5.93,.23,'frame',.25)
# Modest horizontal black planters are visible above the white fascia.
for x in centers:
    front.box('window_box','door',x,6.43,width+.12,.20,.27,.10)
    for j in range(6):
        front.box('window_box_foliage','leaf',x-width/2+(j+.5)*width/6,6.58,.20,.18,.22,.10)
# Exact footprint remains. Secondary elevations are restrained where unseen.
for wall in profile['walls']:
    if wall['index']==6:continue
    f=Facade(profile,wall,groups)
    if wall['length']<1.0 or wall['party']:
        f.box('party_wall','brick',f.length/2,8.30,f.length,16.60,.25,-.14);continue
    xs=[f.length*(i+.5)/max(1,round(f.length/3.8))for i in range(max(1,round(f.length/3.8)))]
    holes=[]
    for x in xs:
        for z,h in levels:
            w=min(1.50,f.length*.55);holes.append((x-w/2,x+w/2,z-h/2,z+h/2));window(f,x,z,w,h,2,2,'secondary')
    wall_with_openings(f,0,6.30,[h for h in holes if h[3]<6.30],'white')
    wall_with_openings(f,6.30,16.60,[h for h in holes if h[2]>6.30],'brick')
    f.box('secondary_band','stone',f.length/2,16.65,f.length,.20,.34,.015)
# Four broad dormers and an inset slate mansard. Unseen roof depth estimated.
ring=profile['building']['rings'][0];center=Vector((*profile['building']['center'],0));roof=Geometry('SHF','roof50','slate');roof.name='SHF_V50_mansard_roof'
inner=[center+(Vector((*xy,0))-center)*.70 for xy in ring]
for i in range(len(ring)):
    j=(i+1)%len(ring)
    roof.add([(*ring[i],16.80),(*ring[j],16.80),(inner[j].x,inner[j].y,18.60),(inner[i].x,inner[i].y,18.60)],[(3,2,1,0)])
for triangle in profile['building']['triangles']:
    pts=[center+(Vector((*xy,0))-center)*.70 for xy in triangle]
    roof.add([(p.x,p.y,18.60)for p in pts],[(0,1,2)])
for x in centers:
    w=2.25
    for side in [-1,1]:front.box('dormer_cheek','white',x+side*(w/2+.025),17.64,.10,1.40,1.12,-.51)
    front.box('dormer_base','white',x,16.98,w+.20,.16,1.12,-.51)
    front.box('dormer_cap','slate',x,18.37,w+.27,.14,1.20,-.49)
    window(front,x,17.65,w,1.14,4,2,'dormer')
added=[]
for g in groups.values():
    g.name=g.name.replace('SHF_D5_','SHF_V50_')
    obj=g.finish()
    if g.material.name=='SHF_V50_brick':
        # Wall UVs use horizontal metres and world height, independent of box winding.
        uv=obj.data.uv_layers.active.data
        for polygon in obj.data.polygons:
            normal=polygon.normal
            tangent=Vector((-normal.y,normal.x,0))
            vertical=abs(normal.z)<.9
            if vertical:tangent.normalize()
            for loop_index in polygon.loop_indices:
                point=obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
                uv[loop_index].uv=(point.dot(tangent),point.z) if vertical else (point.x,point.y)
    added.append(obj.name)
added.append(roof.finish().name)
for layer in bpy.context.scene.view_layers:layer.update()
changed=[o.name for o in originals if fingerprint(o)!=before[o.name]];assert changed==[],changed
for name in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/name).write_bytes((ROOT/'result/blender/stage49'/name).read_bytes())
direction=[front.n.x,.65,-front.n.y]
record={'code':'SHF','height':16.60,'floors':5,'exteriorDirection':direction,'scope':'Four-bay Sheffield Street elevation from official photographs; dimensions and roof depth estimated; no interior claimed','reference':profile['reference'],'components':sum(g.parts for g in groups.values())}
(OUT/'shf-manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
cam=Vector(front.point(L/2,10,23));target=Vector(front.point(L/2,9,0))
audit={'version':50,'baseline':49,'frontEdge':6,'formerFrontEdge':5,'frontRight':list(front.u),'frontOutward':list(front.n),'frontLength':L,'windowBays':4,'dormers':4,'whiteBaseHeight':6.30,'brickParapetHeight':16.60,'roofHeight':18.60,'windows':windows,'changedExistingGeometry':changed,'hiddenArchives':hidden,'addedObjects':added,'footprint':ring,'camera':list(cam),'target':list(target),'limitations':['Official image capture date unknown, not evidence of a 2026 as-built survey','Floor heights, doorway width, roof depth and secondary elevations remain estimated','No attributed interior plan or photo available; interior not invented']}
(OUT/'shf-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v50.blend'))
print('SHEFFIELD_FRONTAGE_SAVED',L,direction)
