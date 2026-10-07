"""Historical SAW fourth-to-fifth connection study from the2014 guide.

Pages27/28 identify the retained central circulation zone and upper curved
stair arrangement. The intervening flight is an estimated connectivity study,
not a traced/surveyed stair or a2026 as-built reconstruction. The fifth-floor
landing is shared with the existing171 flight rather than duplicated.
"""
from pathlib import Path
import math,hashlib
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
PARENT='SAW_PUBLIC_INTERIOR_study'
COLLECTION='SAW_STRUCTURE172_historical_fourth_fifth_connection'
NAMES=['SAW172_fourth_to_fifth_curved_treads','SAW172_fourth_floor_landing','SAW172_fourth_fifth_guards']
GUIDE='data/documents/saw_occupants_guide_2014.pdf'
SOURCE_URL='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/SAW/Final-Web-version-of-Occupants-Guide.pdf'
CENTER=(-61.67495,13.33058)
LOWER_Z,UPPER_Z=14.1,18.0
INNER_RADIUS,OUTER_RADIUS,STEPS=1.05,2.88,26
# End beside the171 lower landing's start edge, then cross its existing arc
# to the171 flight. A0.0003rad seam avoids coincident/coplanar source faces.
END_ANGLE=math.radians(-70)-.36-.0003
START_ANGLE=END_ANGLE-math.pi


def apply_saw_structure172():
    """Add one contiguous upper connection without editing retained source."""
    if COLLECTION in bpy.data.collections:
        assert all(n in bpy.data.objects for n in NAMES)
        return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    assert 'SAW171_upper_stair_landings'in bpy.data.objects,'Requires accepted171 connection'
    collection=bpy.data.collections.new(COLLECTION);bpy.data.collections[PARENT].children.link(collection)
    collection['evidenceYear']=2014;collection['registration']='Retained central void and fifth-floor shared landing; estimated intervening flight'
    materials=[]
    for name,color in [('SAW172_historical_concrete',(.49,.49,.45,1)),('SAW172_historical_guard',(.075,.079,.075,1))]:
        m=bpy.data.materials.new(name);m.diffuse_color=color;m.use_nodes=True
        s=m.node_tree.nodes.get('Principled BSDF');s.inputs['Base Color'].default_value=color;s.inputs['Roughness'].default_value=.68;materials.append(m)
    groups=[([],[]),([],[]),([],[])]
    def point(radius,angle):return CENTER[0]+radius*math.cos(angle),CENTER[1]+radius*math.sin(angle)
    def solid(group,footprint,bottom,top):
        verts,faces=groups[group];start=len(verts);n=len(footprint)
        verts.extend((x,y,z)for z in(bottom,top)for x,y in footprint)
        faces.extend([tuple(start+i for i in reversed(range(n))),tuple(start+n+i for i in range(n))])
        faces.extend((start+i,start+(i+1)%n,start+n+(i+1)%n,start+n+i)for i in range(n))
    for i in range(STEPS):
        a=START_ANGLE+math.pi*i/STEPS;b=START_ANGLE+math.pi*(i+1)/STEPS;z=LOWER_Z+(UPPER_Z-LOWER_Z)*(i+1)/STEPS
        solid(0,[point(INNER_RADIUS,a),point(OUTER_RADIUS,a),point(OUTER_RADIUS,b),point(INNER_RADIUS,b)],z-.11,z)
        solid(2,[point(OUTER_RADIUS+.018,a),point(OUTER_RADIUS+.07,a),point(OUTER_RADIUS+.07,b),point(OUTER_RADIUS+.018,b)],z+.005,z+1.05)
    floor=bpy.data.objects['SAW_SAW_floor_14.1'];tree=BVHTree.FromPolygons([floor.matrix_world@v.co for v in floor.data.vertices],[tuple(p.vertices)for p in floor.data.polygons])
    angles=[START_ANGLE-.36+(.36-.0003)*i/60 for i in range(61)];distances=[]
    for angle in angles:
        radius=OUTER_RADIUS
        while radius<10:
            x,y=point(radius,angle)
            if tree.ray_cast(Vector((x,y,LOWER_Z+.1)),Vector((0,0,-1)),.2)[0]is not None:break
            radius+=.002
        assert radius<10;distances.append(radius)
    edges=[r-.003 for r in distances];assert min(edges)>OUTER_RADIUS
    solid(1,[point(INNER_RADIUS,angles[0])]+[point(r,a)for r,a in zip(edges,angles)]+[point(INNER_RADIUS,angles[-1])],LOWER_Z-.12,LOWER_Z)
    for index,(name,(verts,faces))in enumerate(zip(NAMES,groups)):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
        uv=mesh.uv_layers.new(name='MetricUV')
        for loop in mesh.loops:
            v=mesh.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(v.x,v.y)
        mesh.materials.append(materials[1 if index==2 else 0]);o=bpy.data.objects.new(name,mesh);collection.objects.link(o)
        o['sourceURL']=SOURCE_URL;o['evidenceYear']=2014;o['dimensions']='Estimated, not surveyed'
    return dict(alreadyApplied=False,addedObjects=NAMES[:],archivedObjects=[],changedObjects=[],historicalStudy=True,
        source=dict(file=GUIDE,sha256=hashlib.sha256((ROOT/GUIDE).read_bytes()).hexdigest(),sourceURL=SOURCE_URL,pages=[27,28],publicationYear=2014),
        registration=dict(center=CENTER,fourthDatum=LOWER_Z,fifthDatum=UPPER_Z,startAngle=START_ANGLE,endAngle=END_ANGLE,estimatedSteps=STEPS,estimatedRadii=[INNER_RADIUS,OUTER_RADIUS],sharedLanding='SAW171_upper_stair_landings',fourthLandingBoundaryRadii=edges),
        limitations=['The guide establishes historical floor/circulation relationships; fourth-to-fifth flight geometry is inferred for connectivity, not an exact trace of page28.',
                    'Dimensions, angles, guards, floor heights and retained axis registration are estimates. Publication2014 does not verify current2026 condition.',
                    'Side stair/lift cores, basement circulation and individual rooms remain incomplete. Retained source geometry/UV/materials are untouched.'])
