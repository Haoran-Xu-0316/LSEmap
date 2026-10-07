"""Photo-registered Peacock frontage street furniture, not a surveyed2026 inventory.

Sadler's Wells2023 upload/capture date unknown shows five black bollards and
paired yellow kerb lines. Current venue page corroborates double yellow lines.
Only the visible15.1m marquee frontage is registered; existing street/entry
geometry stays intact. Locations,950mm posts and100mm paint are estimates.
"""
import math
import bpy
from mathutils import Vector

OWNED=('SITE176_PEA_Portugal_frontage_bollards','SITE176_PEA_Portugal_double_yellow_lines')
SOURCE_URL='https://www.sadlerswells.com/your-visit/peacock-theatre/'
PHOTO_URL='https://images.sadlerswells.com/uploads/2023/09/peacock-theatre-scaled.jpeg?resize=1584%2C990&gravity'
A=Vector((-68.1400528,-31.9190674));B=Vector((-54.2232819,-26.0580940));T=(B-A).normalized();N=Vector((T.y,-T.x))
POST_STATIONS=(.6,3.8,7.0,10.2,13.5)


def _support(xy,name):
    o=bpy.data.objects.get(name)
    assert o and o.type=='MESH',name
    inverse=o.matrix_world.inverted()
    hit,p,normal,index=o.ray_cast(inverse@Vector((xy.x,xy.y,1)),inverse.to_3x3()@Vector((0,0,-1)),distance=2)
    assert hit,('Missing expected road support',name,list(xy))
    return (o.matrix_world@p).z


def _material(name,color,roughness,metallic):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=roughness;p.inputs['Metallic'].default_value=metallic
    m['referenceDate']='2023 image upload; photograph capture unknown';m['sourceURL']=SOURCE_URL
    return m


def _object(name,verts,faces,material):
    mesh=bpy.data.meshes.new(name+'_mesh');mesh.from_pydata(verts,[],faces);mesh.update()
    layer=mesh.uv_layers.new(name='MetricSurfaceUV')
    for p in mesh.polygons:
        for i in p.loop_indices:
            v=mesh.vertices[mesh.loops[i].vertex_index].co
            layer.data[i].uv=(v.x*T.x+v.y*T.y,v.z if abs(p.normal.z)<.5 else v.x*N.x+v.y*N.y)
    mesh.materials.append(material);obj=bpy.data.objects.new(name,mesh)
    bpy.data.collections['00_SITE'].objects.link(obj)
    obj['scope']='Visible Peacock Portugal Street frontage, photograph-estimated placement'
    obj['sourceURL']=SOURCE_URL;obj['photoURL']=PHOTO_URL
    return obj


def apply_portugal_environment176():
    present=[bool(bpy.data.objects.get(n)) for n in OWNED]
    if all(present):return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[]}
    assert not any(present),'Partial176 component; refuse duplicate geometry'
    assert bpy.data.collections.get('00_SITE')
    verts=[];faces=[];supports=[]
    # Cast-iron taper/collar silhouette retained as one closed lathe per post.
    profile=((0,.105),(.035,.105),(.055,.078),(.70,.060),(.73,.077),(.775,.077),(.805,.065),(.875,.063),(.935,.046),(.950,.015))
    sides=16
    for station in POST_STATIONS:
        xy=A+T*station+N*1.25;ground=_support(xy,'00_SITE_Road_Portugal Street.001');base=ground+.001;start=len(verts)
        supports.append({'station':station,'xy':list(xy),'ground':ground,'base':base,'support':'00_SITE_Road_Portugal Street.001'})
        for z,r in profile:
            for i in range(sides):
                angle=2*math.pi*i/sides;verts.append((xy.x+r*math.cos(angle),xy.y+r*math.sin(angle),base+z))
        faces.append(tuple(start+i for i in reversed(range(sides))))
        for ring in range(len(profile)-1):
            for i in range(sides):
                j=(i+1)%sides;a=start+ring*sides+i;b=start+ring*sides+j;faces.append((a,b,b+sides,a+sides))
        faces.append(tuple(start+(len(profile)-1)*sides+i for i in range(sides)))
    posts=_object(OWNED[0],verts,faces,_material('SITE176_PEA_cast_iron_black_paint',(.009,.012,.011),.53,.28))
    for p in posts.data.polygons:p.use_smooth=len(p.vertices)==4
    verts=[];faces=[];paintSupports=[]
    cube=((0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5))
    length=(B-A).length
    for offset in (2.0,2.2):
        points=[A+T*station+N*offset for station in (0,length/2,length)]
        heights=[_support(p,'00_SITE_Road_Portugal Street') for p in points]
        assert max(heights)-min(heights)<.001,'Road varies; paint requires curved registration'
        z=max(heights)+.002;centre=A+T*(length/2)+N*offset;start=len(verts)
        for i in range(8):
            q=centre+T*((.5 if i&4 else -.5)*length)+N*((.5 if i&2 else -.5)*.10)
            verts.append((q.x,q.y,z+(.003 if i&1 else 0)))
        # T,N is clockwise, use reversed box winding to keep exterior normals.
        faces.extend(tuple(start+i for i in reversed(f)) for f in cube)
        paintSupports.append({'offset':offset,'stations':[0,length/2,length],'supportHeight':heights,'bottom':z,'support':'00_SITE_Road_Portugal Street'})
    _object(OWNED[1],verts,faces,_material('SITE176_Portugal_road_marking_ochre',(.64,.43,.065),.91,0))
    return {'alreadyApplied':False,'addedObjects':list(OWNED),'archivedObjects':[],'changedObjects':[],
            'reviewScope':'Approximate visible15.1m Peacock frontage: five950mm black bollards and two100mm yellow kerb lines; unchanged entry and footway',
            'sourceURL':SOURCE_URL,'photoURL':PHOTO_URL,'referenceDate':'Image uploadedSeptember2023; capture date unknown; current official page corroborates double yellow restriction, not bollard inventory',
            'supportContacts':supports,'paintSupports':paintSupports,'minimumBetweenPosts':2.99,
            'estimatedUnobstructedInsidePostStrip':3.165,'estimateNote':'Marquee2.02m depth plus1.25m outward offset less105mm post radius; door approach kept inside post row. Not an accessibility survey.',
            'cameraSuggestions':{'overall':{'position':[-63,-38,8],'target':[-62,-27,2.7],'lens':22},'close':{'position':[-63,-38,2],'target':[-59,-28,.6],'lens':29}}}
