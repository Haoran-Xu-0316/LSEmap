"""Restore five photographed COL first-floor three-column window frames.

Callable on a loaded scene. The LSE Mathematics public Athena Swan application
contains a clearer Garrick corner/Houghton frontage photograph on page6. It
supports the corner and nearest four street windows, not every upper window.
Application April2020; online publication indexed2022; photo capture unknown.
Existing apertures, top lights, glass, stone, roof and colours remain unchanged.
"""
from pathlib import Path
import hashlib,math
import bpy,bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
SOURCE='COL_NEXT_portal_window_three_columns'
OWNED='COL_NEXT_EXTERIOR167_five_three_column_windows'


def apply_col_exterior167():
    if bpy.data.objects.get(OWNED):
        return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[]}
    source=bpy.data.objects[SOURCE];assert not source.hide_render
    glass=bpy.data.objects['COL_V99_retained_D4_recessed_glass']
    groups=[];bm=bmesh.new();bm.from_mesh(glass.data);seen=set()
    for seed in bm.verts:
        if seed in seen:continue
        todo=[seed];seen.add(seed);points=[]
        while todo:
            v=todo.pop();points.append(glass.matrix_world@v.co)
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other not in seen:seen.add(other);todo.append(other)
        if abs(min(p.z for p in points)-5.6)<.1 and abs(max(p.z for p in points)-7.95)<.1:
            groups.append(points)
    bm.free()
    spans=[(Vector((8.045785583024937,-127.24588402251834,0)),Vector((5.831283376451804,-125.39900274397166,0)),1),
           (Vector((5.831283376451804,-125.39900274397166,0)),Vector((3.46404238662079,-99.55374993886971,0)),4)]
    selected=[]
    for origin,end,count in spans:
        axis=(end-origin).normalized();normal=Vector((-axis.y,axis.x,0));length=(end-origin).length
        candidates=[]
        for points in groups:
            center=sum(points,Vector())/len(points);d=center-origin;x=d.dot(axis)
            if 0<x<length and abs(d.dot(normal)+.4)<.01:
                candidates.append((x,center,points))
        candidates.sort(key=lambda row:row[0]);assert len(candidates)>=count
        for _,center,points in candidates[:count]:
            width=max(p.dot(axis)for p in points)-min(p.dot(axis)for p in points)
            selected.append({'center':center,'axis':axis,'normal':normal,'width':width})
    assert len(selected)==5
    replacement=source.copy();replacement.data=source.data.copy();replacement.name=OWNED
    bpy.data.collections['COL_EXTERIOR'].objects.link(replacement)
    bm=bmesh.new();bm.from_mesh(replacement.data);bm.verts.ensure_lookup_table();bm.verts.index_update()
    seen=set();parts=[];removed=[]
    for seed in bm.verts:
        if seed in seen:continue
        todo=[seed];seen.add(seed);part=[]
        while todo:
            v=todo.pop();part.append(v)
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other not in seen:seen.add(other);todo.append(other)
        points=[replacement.matrix_world@v.co for v in part];center=sum(points,Vector())/len(points)
        if abs(min(p.z for p in points)-5.6)>.01 or abs(max(p.z for p in points)-7.95)>.01:continue
        for row in selected:
            delta=center-row['center']
            if abs(delta.dot(row['axis']))<.01 and abs(delta.dot(row['normal'])-.1)<.01:
                parts.append((part,row));removed.extend(v.index for v in part);break
    assert len(parts)==5
    for part,row in parts:
        geometry=list({v for v in part}|{e for v in part for e in v.link_edges}|{f for v in part for f in v.link_faces})
        for sign in [-1,1]:
            duplicate=bmesh.ops.duplicate(bm,geom=geometry)
            vertices=[v for v in duplicate['geom']if isinstance(v,bmesh.types.BMVert)];assert len(vertices)==8
            shift=replacement.matrix_world.inverted().to_3x3()@(row['axis']*sign*row['width']/6)
            for v in vertices:v.co+=shift
        bmesh.ops.delete(bm,geom=part,context='VERTS')
    bm.to_mesh(replacement.data);bm.free();replacement.data.update()
    assert len(replacement.data.vertices)==len(source.data.vertices)+40
    source.hide_render=True;source.hide_set(True)
    return {'alreadyApplied':False,'addedObjects':[OWNED],'archivedObjects':[SOURCE],'changedObjects':[],
            'removedVertexIndices':removed,
            'windows':[dict(center=list(r['center']),axis=list(r['axis']),normal=list(r['normal']),width=r['width'],heightRange=[5.6,7.95])for r in selected],
            'sourceUrl':'https://www.lse.ac.uk/Mathematics/assets/documents/PUBLIC-AthSw-For-Website.pdf',
            'sourceFile':'result/blender/col_detail167/mathematics-public-2022.pdf','sourcePage':6,
            'applicationDate':'April2020','pdfCreationDate':'2022-09-28','photographicCaptureDate':'unknown',
            'scope':'Garrick chamfer corner and four nearest Houghton first-floor windows only',
            'limitations':['Same section and estimated aperture dimensions retained; equal-thirds spacing is photo estimated',
                           'No roof, hidden rear massing, upper-floor windows, stone/glass optics or interiors altered',
                           'Older official photograph supports historic window division; not a2026survey']}
