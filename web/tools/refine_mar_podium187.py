"""Restore the missing eastern north-podium window and its concrete surround.

Nick Kane's built front photograph02 shows three tall two-light windows.
The existing outer windows register the photograph; its middle-right window
falls at localX-12.2, where the current facade incorrectly exposes recessed
hall glazing. Pixel-to-model registration and all new dimensions are estimates.
The opposite open loggia, existing outer windows and internal geometry remain.
Call apply_mar_podium187() in a loaded campus; this module never saves files.
"""
import bpy
from refine_mar_exterior174 import world

NAMES=['MAR187_podium_window_surround','MAR187_podium_window_glass','MAR187_podium_window_joinery']
WINDOW=(-13.8,-10.6,6.0,12.2)

def mesh_object(name,quads,material,collection):
    vertices=[];faces=[]
    for quad in quads:
        offset=len(vertices);vertices.extend(world(*p)for p in quad);faces.append(tuple(range(offset,offset+len(quad))))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.materials.append(material)
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
    uv=mesh.uv_layers.new(name='Metric')
    for face in mesh.polygons:
        for loop in face.loop_indices:
            point=vertices[mesh.loops[loop].vertex_index];uv.data[loop].uv=(point.x,point.z)
    mesh.update();return obj

def box(x0,x1,y0,y1,z0,z1):
    return [[(x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)],
            [(x1,y1,z0),(x0,y1,z0),(x0,y1,z1),(x1,y1,z1)],
            [(x0,y1,z0),(x0,y0,z0),(x0,y0,z1),(x0,y1,z1)],
            [(x1,y0,z0),(x1,y1,z0),(x1,y1,z1),(x1,y0,z1)],
            [(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)],
            [(x0,y1,z0),(x1,y1,z0),(x1,y0,z0),(x0,y0,z0)]]

def apply_mar_podium187():
    if all(bpy.data.objects.get(name)for name in NAMES):return dict(alreadyApplied=True,addedObjects=[],changedObjects=[],archivedObjects=[])
    assert not any(bpy.data.objects.get(name)for name in NAMES),'Partial MAR187 component'
    collection=bpy.data.collections['MAR_EXTERIOR'];a,c,b,d=WINDOW
    # Non-overlapping solid strips surround the photographed aperture.
    quads=[]
    for x0,x1,z0,z1 in [(-15,a,4.6,12.8),(c,-8,4.6,12.8),(a,c,4.6,b),(a,c,d,12.8)]:
        quads.extend(box(x0,x1,20.25,20.8,z0,z1))
    wall=bpy.data.objects['MAR174_north_podium_nonoverlapping_walls']
    mesh_object(NAMES[0],quads,wall.data.materials[0],collection)
    # Same optical finish as the two retained flank windows, explicitly named.
    glass=bpy.data.materials['MAR168_02_01_dielectric'].copy();glass.name='MAR187_podium_window_glass'
    mesh_object(NAMES[1],[[(c,20.59,b),(a,20.59,b),(a,20.59,d),(c,20.59,d)]],glass,collection)
    joinery=bpy.data.objects['MAR174_retained_loggia_00'].data.materials[0]
    frames=[]
    for x in [a,c]:frames.extend(box(x-.026,x+.026,20.58,20.67,b,d))
    for z in [b,(b+d)/2,d]:
        half=.045 if z==(b+d)/2 else .0325
        frames.extend(box(a-.05,c+.05,20.58,20.68,z-half,z+half))
    mesh_object(NAMES[2],frames,joinery,collection)
    return dict(alreadyApplied=False,addedObjects=NAMES,archivedObjects=[],changedObjects=[],
      changes=['Restore missing middle-right two-light podium window and concrete frontage instead of an oversized open hall recess.'],
      windowLocalBounds=list(WINDOW),wallLocalBounds=[-15,-8,20.25,20.8,4.6,12.8],
      sourcePhoto='data/建筑图片/MAR_Marshall Building/01_建筑实拍/architecture_round5_MAR_mar_kane_02.jpg',
      sourceURL='https://nickkane.co.uk/portfolio_page/marshall-building-lse-london-grafton-architects/',
      limitations=['Capture date unknown; no current surveyed dimensions claimed.','Image-based registration, wall extent and aperture dimensions estimated.','Existing rear glazing and interior geometry preserved; opaque window finish does not claim a new room.','Upper fissure and full building massing remain unverified.'])
