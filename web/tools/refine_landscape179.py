"""Estimated foliage contours inside retainedWatkins/Houghton tree envelopes.

Only12of522native crown masses receive one triangular subdivision;Houghton's
six existing masses retain their face count. This is estimated presentation,
not surveyed branches/species. Two subdued opaquePBR shades export directly.
"""
import math
import bpy
from mathutils import Vector

SOURCES=('03_PUBLIC_REALM_Plane_tree_crown','SITE167_Houghton_tree_crowns')
TARGETS=('LANDSCAPE179_Watkins_registered_crowns','LANDSCAPE179_Houghton_planter_crowns')
ARCHIVE='LANDSCAPE179_CROWN_ARCHIVE'
STARTS=tuple(range(19404,19908,42))
PHOTO='data/collections/public-realm-2026/user-references/reference-09.png'
PLAZA_PHOTO='data/collections/streets/derived/review_public_realm_pdf_page75.png'
SOURCE_URL='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/2022-LSE-Public-Realm-Strategy.pdf'


def _finish(source,name,color):
    mat=source.copy();mat.name=name;mat.diffuse_color=(*color,1)
    p=mat.node_tree.nodes.get('Principled BSDF');assert p and not p.inputs['Base Color'].is_linked
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.9;p.inputs['Metallic'].default_value=0
    mat['webBaseColor']=list(color)+[1];mat['webRoughness']=.9;mat['webMetallic']=0
    mat['presentationEstimated']=True;mat['sourceURL']=SOURCE_URL
    return mat


def _reshape(points,indices,bounds,seed):
    lo,hi=[Vector(v) for v in bounds];centre=(lo+hi)/2;extent=(hi-lo)/2
    for i in indices:
        q=Vector(((points[i][j]-centre[j])/extent[j] for j in range(3)));q.normalize()
        az=math.atan2(q.y,q.x);e=q.z
        variation=1+.14*math.sin(5*az+seed)*math.cos(4*e+seed*.7)+.075*math.sin(9*az-2*e+seed*.3)
        points[i]=centre+Vector((q[j]*extent[j]*variation for j in range(3)))
    actualLo=Vector((min(points[k][i]for k in indices)for i in range(3)));actualHi=Vector((max(points[k][i]for k in indices)for i in range(3)))
    for k in indices:points[k]=Vector((lo[i]+(points[k][i]-actualLo[i])/(actualHi[i]-actualLo[i])*(hi[i]-lo[i])for i in range(3)))


def _replacement(source,name,isPlaza,owner):
    mesh=source.data;assert len(mesh.vertices)==(21924 if isPlaza else 768)
    starts=STARTS if isPlaza else tuple(range(0,768,128));size=42 if isPlaza else 128
    groups=[set(range(start,start+size))for start in starts];groupsByVertex={i:k for k,g in enumerate(groups)for i in g}
    points=[v.co.copy()for v in mesh.vertices];bounds=[[[min(points[i][j]for i in g)for j in range(3)],[max(points[i][j]for i in g)for j in range(3)]]for g in groups]
    faces=[];slots=[];smooth=[];affectedFaces=[];cornerUV={layer.name:[]for layer in mesh.uv_layers};midpointCache={}
    baseSlot=1 if isPlaza else 0
    def midpoint(a,b,group):
        key=tuple(sorted((a,b)))
        if key not in midpointCache:
            midpointCache[key]=len(points);points.append((points[a]+points[b])/2);groups[group].add(midpointCache[key])
        return midpointCache[key]
    for p in mesh.polygons:
        group=groupsByVertex.get(p.vertices[0]);selected=group is not None and all(groupsByVertex.get(i)==group for i in p.vertices)
        sourceUV={layer.name:[Vector(layer.data[i].uv)for i in p.loop_indices]for layer in mesh.uv_layers}
        if selected and isPlaza:
            assert len(p.vertices)==3;a,b,c=p.vertices;ab=midpoint(a,b,group);bc=midpoint(b,c,group);ca=midpoint(c,a,group)
            newFaces=[(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]
            for f in newFaces:affectedFaces.append(len(faces));faces.append(f);slots.append(baseSlot);smooth.append(True)
            for label,u in sourceUV.items():
                ua,ub,uc=u;uab=(ua+ub)/2;ubc=(ub+uc)/2;uca=(uc+ua)/2
                cornerUV[label].extend([ua,uab,uca,uab,ub,ubc,uca,ubc,uc,uab,ubc,uca])
        else:
            if selected:affectedFaces.append(len(faces))
            faces.append(tuple(p.vertices));slots.append(baseSlot if selected else p.material_index);smooth.append(p.use_smooth)
            for label,uv in sourceUV.items():cornerUV[label].extend(uv)
    for k,group in enumerate(groups):_reshape(points,group,bounds[k],.63+k*.83)
    for i in affectedFaces:
        c=sum((points[j]for j in faces[i]),Vector())/len(faces[i]);field=math.sin(c.x*1.2+c.z*.8)+math.cos(c.y*1.1-c.z*.7);slots[i]=baseSlot+(1 if field>.4 else 0)
    data=bpy.data.meshes.new(name+'_mesh');data.from_pydata(points,[],faces);data.update()
    leaf=mesh.materials[0];dark=_finish(leaf,name+'_foliage_mid',(.10,.17,.055));light=_finish(leaf,name+'_foliage_light',(.125,.195,.068))
    for mat in ([leaf,dark,light]if isPlaza else[dark,light]):data.materials.append(mat)
    for p,slot,shade in zip(data.polygons,slots,smooth):p.material_index=slot;p.use_smooth=shade
    for label,uvs in cornerUV.items():
        layer=data.uv_layers.new(name=label)
        for dst,uv in zip(layer.data,uvs):dst.uv=uv
    target=source.copy();target.data=data;target.name=name;owner.objects.link(target)
    target['presentationEstimated']=True;target['scope']='Retained registered crown envelopes; estimated irregular leaf-mass contours only';target['sourceURL']=SOURCE_URL
    return target,bounds


def apply_landscape179():
    present=[bool(bpy.data.objects.get(n))for n in TARGETS]
    if all(present):return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    assert not any(present),'Partial landscape179 state'
    archive=bpy.data.collections.new(ARCHIVE);bpy.context.scene.collection.children.link(archive);added=[];archived=[];records=[]
    for sourceName,targetName in zip(SOURCES,TARGETS):
        source=bpy.data.objects[sourceName];assert not source.hide_render and len(source.data.materials)==1
        owners=list(source.users_collection);assert len(owners)==1
        isPlaza=sourceName==SOURCES[0];target,bounds=_replacement(source,targetName,isPlaza,owners[0])
        owners[0].objects.unlink(source);archive.objects.link(source);source.hide_render=True;source.hide_set(True)
        added.append(target.name);archived.append(source.name)
        records.append(dict(source=source.name,target=target.name,collection=owners[0].name,modifiedMasses=len(bounds),originalBounds=bounds,verticesBefore=len(source.data.vertices),verticesAfter=len(target.data.vertices),facesBefore=len(source.data.polygons),facesAfter=len(target.data.polygons),materialPrimitivesBefore=1,materialPrimitivesAfter=3 if isPlaza else 2))
    return dict(alreadyApplied=False,addedObjects=added,archivedObjects=archived,changedObjects=[],records=records,
                scope='Four existingWatkins tree positions and twoHoughton planter trees; individual crown envelopes/height ranges retained',
                sourceURL=SOURCE_URL,sourcePhotos=[PLAZA_PHOTO,PHOTO],referenceDates=['2021strategy photograph within2022report','UserHoughton photo capture unknown'],
                presentationEstimated=True,limitations='Foliage silhouettes and twoPBR shades estimated, not measured branches,species or2026survey. No leaf alpha cards or new trees.')
