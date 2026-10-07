"""Restore COL's smooth ordinary street piers and Aldwych incised reed bands.

The2025/26LSE property handbook shows the main portal's ordinary stone piers
with fine vertical reed bands rather than the deep horizontal corner courses.
The official Mathematics photograph supports the smooth Houghton ordinary
piers and distinct rusticated Garrick corner. Capture dates remain unknown.
Reed spacing and depth are estimated, not measured. Existing upper rows and
roof are outside the support of these cropped photographs and are retained.
Only modifies an already loaded scene; it never opens or saves a campus.
"""
import bpy,bmesh
from mathutils import Vector

COLLECTION='COL_EXTERIOR175_smooth_street_piers'
ARCHIVE='COL_EXTERIOR175_retained_sources'
SOURCES=['COL_D4_rustication_recesses','COL_D4_stone_wall_piers']
NAMES=['COL175_retained_corner_courses','COL175_retained_original_stone_piers','COL175_aldwych_incised_piers']
# Existing mapped footprint/Garrick chamfer axes, independent of old audit files.
FRAME_POINTS=[(10,(21.860380038873103,-127.57961763971016),(8.045785583024937,-127.24588402251834)),(11,(8.045785583024937,-127.24588402251834),(5.831283376451804,-125.39900274397166)),(12,(5.831283376451804,-125.39900274397166),(3.46404238662079,-99.55374993886971))]
FRAMES=[]
for i,a,b in FRAME_POINTS:
    origin=Vector((*a,0));end=Vector((*b,0));axis=(end-origin).normalized();normal=Vector((-axis.y,axis.x,0));FRAMES.append((i,origin,axis,normal,(end-origin).length))
PHOTOS=['data/建筑图片/COL_Columbia House/01_建筑实拍/small_round5_COL_handbook-000.png','result/blender/col_detail167/mathematics-003.jpg','data/建筑图片/COL_Columbia House/01_建筑实拍/exteriors_lse_estate_004.jpg']
SOURCE_URLS=['https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf','https://www.lse.ac.uk/Mathematics/assets/documents/PUBLIC-AthSw-For-Website.pdf','https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate']

def registration(points):
    center=sum(points,Vector())/len(points)
    def distance(f):
        _,o,u,n,length=f;x=(center-o).dot(u);outside=max(0,-x,x-length);return((center-o).dot(n)**2+outside**2)**.5
    f=min(FRAMES,key=distance);index,origin,axis,normal,length=f
    return dict(facade=index,axis=axis,normal=normal,origin=origin,length=length,x=[min((p-origin).dot(axis)for p in points),max((p-origin).dot(axis)for p in points)],depth=[min((p-origin).dot(normal)for p in points),max((p-origin).dot(normal)for p in points)],z=[min(p.z for p in points),max(p.z for p in points)])

def components(obj):
    # The two inherited source batches are separate eight-vertex closed boxes.
    assert len(obj.data.vertices)%8==0
    return [(i,registration([obj.matrix_world@v.co for v in obj.data.vertices[i:i+8]]))for i in range(0,len(obj.data.vertices),8)]

def retained_clone(source,name,indices,col):
    obj=source.copy();obj.data=source.data.copy();obj.name=name;obj.data.name=name;col.objects.link(obj)
    bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i]for i in indices],context='VERTS');bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.update()
    return obj

def carved_mesh(rows,material):
    # Three registered whole piers replace six adjacent source half boxes. A
    # common occupancy grid cuts genuine12mm recesses and keeps each boundary
    # face once. No dark strip is overlaid onto a coplanar stone surface.
    vertices=[];faces=[];details=[]
    frame=FRAMES[0];_,origin,axis,normal,_=frame
    def face(ps):
        start=len(vertices);vertices.extend(origin+axis*x+normal*y+Vector((0,0,z))for x,y,z in ps);faces.append(tuple(range(start,start+len(ps))))
    for row in rows:
        x0,x1=row['x'];y0,y1=row['depth'];z0,z1=row['z'];inset=.12
        centers=[x0+inset+(x1-x0-2*inset)*(i+.5)/14 for i in range(14)]
        cuts=[(x-.007,x+.007)for x in centers];xs=sorted({x0,x1,*[x for c in cuts for x in c]});ys=[y0,y1-.012,y1];zs=[z0,5.60,5.72,7.78,7.90,z1]
        def groove(x,z):return any(a<x<b for a,b in cuts)and(5.60<z<5.72 or 7.78<z<7.90)
        cells={(i,j,k)for i in range(len(xs)-1)for j in range(2)for k in range(len(zs)-1)if j==0 or not groove((xs[i]+xs[i+1])/2,(zs[k]+zs[k+1])/2)}
        for i,j,k in sorted(cells):
            a,b=xs[i:i+2];c,d=ys[j:j+2];e,f=zs[k:k+2]
            if(i-1,j,k)not in cells:face([(a,c,e),(a,c,f),(a,d,f),(a,d,e)])
            if(i+1,j,k)not in cells:face([(b,d,e),(b,d,f),(b,c,f),(b,c,e)])
            if(i,j-1,k)not in cells:face([(a,c,e),(b,c,e),(b,c,f),(a,c,f)])
            if(i,j+1,k)not in cells:face([(b,d,e),(a,d,e),(a,d,f),(b,d,f)])
            if(i,j,k-1)not in cells:face([(a,c,e),(a,d,e),(b,d,e),(b,c,e)])
            if(i,j,k+1)not in cells:face([(a,d,f),(a,c,f),(b,c,f),(b,d,f)])
        details.append(dict(xBounds=[x0,x1],depthBounds=[y0,y1],heightBounds=[z0,z1],reedCountPerBand=14,reedWidthM=.014,incisionDepthM=.012,heightBands=[[5.60,5.72],[7.78,7.90]]))
    mesh=bpy.data.meshes.new(NAMES[2]);mesh.from_pydata(vertices,[],faces);mesh.materials.append(material)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
    uv=mesh.uv_layers.new(name='COL175_metric_stone_uv')
    for f in mesh.polygons:
        for i in f.loop_indices:
            p=mesh.vertices[mesh.loops[i].vertex_index].co-origin;uv.data[i].uv=(p.dot(axis),p.z)
    return mesh,details

def apply_col_exterior175():
    if all(bpy.data.objects.get(n)for n in NAMES):return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    assert not any(bpy.data.objects.get(n)for n in NAMES),'Partial COL175 component'
    for n in SOURCES:assert not bpy.data.objects[n].hide_render,n
    parent=bpy.data.collections['COL_EXTERIOR'];col=bpy.data.collections.new(COLLECTION);parent.children.link(col)
    archive=bpy.data.collections.new(ARCHIVE);parent.children.link(archive);archive.hide_render=True
    grooves=bpy.data.objects[SOURCES[0]];removed_grooves=[];groove_rows=[]
    for start,row in components(grooves):
        center=sum(row['x'])/2
        ordinary=(row['facade']==10 and center<row['length']-.90)or(row['facade']==12 and center>.90)
        if ordinary:removed_grooves.extend(range(start,start+8));groove_rows.append(dict(vertexStart=start,facade=row['facade'],xBounds=row['x'],heightBounds=row['z']))
    assert len(removed_grooves)>1500
    retained_clone(grooves,NAMES[0],removed_grooves,col)
    piers=bpy.data.objects[SOURCES[1]];removed_piers=[];parts=[]
    for start,row in components(piers):
        center=sum(row['x'])/2
        if row['facade']==10 and abs(row['z'][0]-4.8)<.001 and abs(row['z'][1]-8.6)<.001 and 2<center<12.5:
            removed_piers.extend(range(start,start+8));parts.append(row)
    assert len(parts)==6
    retained_clone(piers,NAMES[1],removed_piers,col)
    parts.sort(key=lambda r:r['x'][0]);joined=[]
    for a,b in zip(parts[::2],parts[1::2]):
        assert abs(a['x'][1]-b['x'][0])<.00002
        joined.append(dict(x=[a['x'][0],b['x'][1]],depth=[max(a['depth'][0],b['depth'][0]),min(a['depth'][1],b['depth'][1])],z=a['z']))
    material=piers.data.materials[0].copy();material.name='COL175_retained_portland_stone'
    mesh,reed_details=carved_mesh(joined,material);obj=bpy.data.objects.new(NAMES[2],mesh);col.objects.link(obj)
    for n in SOURCES:source=bpy.data.objects[n];archive.objects.link(source);source.hide_render=True;source.hide_set(True)
    for n in NAMES:bpy.data.objects[n]['componentKey']=n
    for layer in bpy.context.scene.view_layers:layer.update()
    return dict(alreadyApplied=False,addedObjects=NAMES,archivedObjects=SOURCES,changedObjects=[],removedOrdinaryRusticationBoxes=len(removed_grooves)//8,removedGrooveVertexIndices=removed_grooves,removedPierVertexIndices=removed_piers,ordinaryFacadeGroovesRemoved=groove_rows,registeredCarvedPiers=reed_details,photographs=PHOTOS,sourceURLs=SOURCE_URLS,
        retainedCloneNormals='Closed inherited boxes reoriented outward; vertex positions and point-to-UV bindings retained.',registrationSource='Retained mapped COL street segments10/11/12 and source stone piers. Photo-based ordinary/corner distinction; metric reed dimensions estimated.',
        reviewScope='COL下部两条临街立面普通石柱去除错误横缝；保留真实街角块石并建立主入口旁3根柱子的浅竖槽。整栋已对照照片复核，但上层窗列和屋顶仍为估算，未声称全楼实测。',sourceURL=SOURCE_URLS[0],sourceStage='Property handbook2025/26; Mathematics applicationApril2020/PDF2022; photo capture dates unknown.',
        limitations=['Reed count14, width14mm, depth12mm and height bands estimated from clear handbook view, not a measured survey.','Ordinary lower piers of both street faces use the photographed smooth-stone interpretation; nearest corner returns retain rustication.','Upper window counts/roof remain estimated because available photographs crop their full extent; this is not complete2026facade verification.','Existing stone and glass material/opacity values retained; no guessed room/backing transparency.','Source geometry, UV, worldmatrix and materials archived intact. Retained clone faces keep UV; reconstructed piers use new metric UV.'])
