"""Restore the photographed Clement House side-portal clerestory windows.

Fixed Blender component builder. The official estate photograph shows a narrow
three-light upper transom above the three-column main sash. The inherited native
portal windows stop too low and leave an unframed black strip below the main
entablature. Extend only the photographed portal-window heads and matching reveal/frame
ends; keep their sill, lower glazing grid, glass optics, stone finish and rooms.
Photograph capture date is unknown; the 0.585m extension is an estimated fit.
"""
from pathlib import Path
import array
import hashlib
import importlib.util
import json

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v213.blend'
BASE_SHA='31b15a84a0080a69db300183d107d51cddc019a9b54a6aed609e6ab050222bbb'
OUT=ROOT/'result/blender/clm-exterior214'
PREFIX='CLM214_'
DELTA=.585
PHOTO_URL='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/Clement-House-web.jpg'
PORTALS=[Vector((101.5576,-148.9347,5.84))]
TARGET='CLM_EXTERIOR'


def fingerprint(obj):
    digest=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    uv={}
    if obj.type=='MESH':
        for data,key,kind,width in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
            values=array.array(kind,[0])*(len(data)*width);data.foreach_get(key,values);digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values)
            uv[layer.name]=hashlib.sha256(values.tobytes()).hexdigest()
    return {'geometry':digest.hexdigest(),'uv':uv,'materials':[m.name if m else None for m in getattr(obj.data,'materials',[])]}


def material_fingerprint(material):
    if not material.use_nodes:return repr(tuple(material.diffuse_color))
    nodes=[]
    for node in material.node_tree.nodes:
        values=[]
        for socket in node.inputs:
            if not hasattr(socket,'default_value'):continue
            value=socket.default_value
            if hasattr(value,'__iter__') and not isinstance(value,str):value=list(value)
            elif not isinstance(value,(str,int,float,bool,type(None))):value=str(value)
            values.append((socket.name,value))
        nodes.append((node.name,node.bl_idname,values,getattr(getattr(node,'image',None),'name',None)))
    links=sorted((link.from_node.name,link.from_socket.name,link.to_node.name,link.to_socket.name) for link in material.node_tree.links)
    return hashlib.sha256(json.dumps([nodes,links],sort_keys=True).encode()).hexdigest()


def islands(obj):
    bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();seen=set();result=[]
    for seed in bm.verts:
        if seed.index in seen:continue
        todo=[seed];seen.add(seed.index);indices=[]
        while todo:
            vertex=todo.pop();indices.append(vertex.index)
            for edge in vertex.link_edges:
                other=edge.other_vert(vertex)
                if other.index not in seen:seen.add(other.index);todo.append(other)
        points=[obj.matrix_world@bm.verts[i].co for i in indices]
        centre=sum(points,Vector())/len(points)
        result.append((indices,centre,min(p.z for p in points),max(p.z for p in points)))
    bm.free();return result


def portal_island(centre,low,high):
    return 4.2<low<7.5 and 6.95<high<7.5 and any((centre.xy-p.xy).length<1.45 for p in PORTALS)


def build_transom():
    material=bpy.data.materials['CLM196_FINISH_CLM_D3_bronze_or_dark_painted_metal']
    glass=bpy.data.objects['CLM196_FINISH_GLASS181_CLM_NEXT_ENVELOPE_street_glass']
    vertices=[];faces=[];back_vertices=[];back_faces=[];records=[]
    winding=((0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6))
    for indices,centre,low,high in islands(glass):
        if not (abs(low-4.565)<.01 and abs(high-7.70)<.01 and centre.x<110):continue
        points=[glass.matrix_world@glass.data.vertices[i].co for i in indices]
        direction=Vector((.8998045,-.4362931,0)) if centre.x<110 else Vector((.9999323,.0116378,0))
        normal=Vector((direction.y,-direction.x,0))
        projections=[p.dot(direction) for p in points];depths=[p.dot(normal) for p in points]
        lo,hi=min(projections),max(projections);front=max(depths)+.026
        start=len(vertices)
        for k in range(8):
            p=direction*(hi if k&4 else lo)+normal*(front+.0375 if k&2 else front-.0375)+Vector((0,0,7.115+(.026 if k&1 else -.026)))
            vertices.append(tuple(p))
        faces.extend(tuple(start+k for k in face) for face in winding)
        back_start=len(back_vertices)
        for k in range(8):
            p=direction*(hi-.02 if k&4 else lo+.02)+normal*(min(depths)-.18 if k&2 else min(depths)-.22)+Vector((0,0,7.70 if k&1 else 7.125))
            back_vertices.append(tuple(p))
        back_faces.extend(tuple(back_start+k for k in face) for face in winding)
        records.append({'backingIsConservativeEnclosureProxy':True,'backingDepthBehindInnerGlass':.18,'center':list(centre),'span':hi-lo,'normal':list(normal),'glassHeadBefore':7.115,'glassHeadAfter':7.70,'transomCenter':7.115,'upperLightHeightEstimate':.559})
    assert len(records)==1
    mesh=bpy.data.meshes.new(PREFIX+'portal_clerestory_transoms_mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
    uv=mesh.uv_layers.new(name='SurfaceUV')
    for polygon in mesh.polygons:
        origin=mesh.vertices[polygon.vertices[0]].co;u=(mesh.vertices[polygon.vertices[1]].co-origin).normalized();v=polygon.normal.cross(u)
        for index in polygon.loop_indices:
            delta=mesh.vertices[mesh.loops[index].vertex_index].co-origin;uv.data[index].uv=(delta.dot(u),delta.dot(v))
    mesh.materials.append(material)
    obj=bpy.data.objects.new(PREFIX+'portal_clerestory_transoms',mesh);bpy.data.collections[TARGET].objects.link(obj)
    obj['sourceURL']=PHOTO_URL;obj['photographCaptureDate']='Unknown';obj['dimensionsEstimated']=True
    backing_mesh=bpy.data.meshes.new(PREFIX+'portal_upper_light_enclosure_mesh')
    backing_mesh.from_pydata(back_vertices,[],back_faces);backing_mesh.update()
    backing_uv=backing_mesh.uv_layers.new(name='SurfaceUV')
    for polygon in backing_mesh.polygons:
        origin=backing_mesh.vertices[polygon.vertices[0]].co;u=(backing_mesh.vertices[polygon.vertices[1]].co-origin).normalized();v=polygon.normal.cross(u)
        for index in polygon.loop_indices:
            delta=backing_mesh.vertices[backing_mesh.loops[index].vertex_index].co-origin;backing_uv.data[index].uv=(delta.dot(u),delta.dot(v))
    backing_mesh.materials.append(bpy.data.materials['CLM_D3_stone_shadow_joints'])
    backing=bpy.data.objects.new(PREFIX+'portal_upper_light_conservative_enclosure',backing_mesh)
    bpy.data.collections[TARGET].objects.link(backing)
    backing['scope']='Bounded dark opaque proxy behind the added upper light; no surveyed interior or invented room'
    backing['dimensionsEstimated']=True;backing['replaceWhenVerifiedInteriorAvailable']=True
    return obj,backing,records


def preview(phase):
    spec=importlib.util.spec_from_file_location('clm196_preview',ROOT/'web/tools/refine_clm_exterior196.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.OUT=OUT
    module.preview(phase)


def ray_mesh(obj,point,normal):
    vertices=[obj.matrix_world@v.co for v in obj.data.vertices]
    tree=BVHTree.FromPolygons(vertices,[tuple(p.vertices) for p in obj.data.polygons],all_triangles=False)
    hit=tree.ray_cast(point+normal*.4,-normal,1)
    return {'hit':hit[0] is not None,'distance':hit[3]}


def trace_native(origin,direction,distance,exclude):
    closest=None
    for obj in bpy.data.objects:
        if obj.type!='MESH' or obj.hide_render or obj.name in exclude:continue
        vertices=[obj.matrix_world@v.co for v in obj.data.vertices]
        if not vertices:continue
        # Bound culling before allocating each individual mesh tree.
        lo=[min(v[k] for v in vertices) for k in range(3)];hi=[max(v[k] for v in vertices) for k in range(3)]
        if any(abs(direction[k])<1e-7 and not lo[k]-.001<=origin[k]<=hi[k]+.001 for k in range(3)):continue
        tree=BVHTree.FromPolygons(vertices,[tuple(p.vertices) for p in obj.data.polygons],all_triangles=False)
        hit=tree.ray_cast(origin,direction,distance)
        if hit[0] is None or closest is not None and hit[3]>=closest['distance']:continue
        polygon=obj.data.polygons[hit[2]]
        material=obj.data.materials[polygon.material_index] if obj.data.materials else None
        closest={'object':obj.name,'point':list(hit[0]),'distance':hit[3],'material':material.name if material else None}
    return closest


def cross_section():
    normal=Vector((-.4362931,-.8998045,0));tangent=Vector((.8998045,-.4362931,0))
    origin=PORTALS[0]+tangent*.13;segments=[]
    for obj in bpy.data.collections[TARGET].all_objects:
        if obj.type!='MESH' or obj.hide_render:continue
        vertices=[obj.matrix_world@v.co for v in obj.data.vertices]
        for polygon in obj.data.polygons:
            points=[vertices[i] for i in polygon.vertices]
            if min(p.z for p in points)>8.25 or max(p.z for p in points)<6.8:continue
            signed=[(p-origin).dot(tangent) for p in points];hits=[]
            for i,a in enumerate(points):
                j=(i+1)%len(points);b=points[j];aa,bb=signed[i],signed[j]
                if aa*bb<0:
                    hit=a+(b-a)*aa/(aa-bb)
                    if all((hit-old).length>1e-5 for old in hits):hits.append(hit)
            if len(hits)!=2:continue
            section=[[(p-origin).dot(normal),p.z] for p in hits]
            if min(p[0] for p in section)>.5 or max(p[0] for p in section)<-.5:continue
            segments.append({'object':obj.name,'segment':section,'glass':'street_glass' in obj.name})
    return {'cutOrigin':list(origin),'outwardNormal':list(normal),'cutPlaneNormal':list(tangent),'coordinates':'horizontal is outward depth from glass centre in metres; vertical is native world height in metres','segments':segments}


def write_cross_section(before,after):
    (OUT/'native-longitudinal-section.json').write_text(json.dumps({'before':before,'after':after},indent=2)+'\n')
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="740" viewBox="0 0 1000 740"><rect width="1000" height="740" fill="#fafafa"/><defs><clipPath id="left"><rect x="60" y="75" width="400" height="580"/></clipPath><clipPath id="right"><rect x="550" y="75" width="400" height="580"/></clipPath></defs>']
    for index,(phase,section) in enumerate((('Before',before),('After',after))):
        ox=60+index*490
        svg.append(f'<text x="{ox}" y="35" font-size="20" font-family="Arial">{phase}: native portal head section</text>')
        for z in (6.8,7.115,7.4,7.7,8.055,8.25):
            y=75+(8.25-z)/1.45*580
            svg.append(f'<path d="M{ox},{y}h400" stroke="#ddd"/><text x="{ox}" y="{y-5}" font-family="Arial" font-size="12">z={z:.3f}m</text>')
        svg.append(f'<g clip-path="url({"left" if index==0 else "right"})">')
        for item in section['segments']:
            (d1,z1),(d2,z2)=item['segment'];x1=ox+(d1+.5)*400;x2=ox+(d2+.5)*400;y1=75+(8.25-z1)/1.45*580;y2=75+(8.25-z2)/1.45*580
            colour='#267aaf' if item['glass'] else '#a13c3c' if 'conservative_enclosure' in item['object'] else '#555'
            svg.append(f'<path d="M{x1},{y1}L{x2},{y2}" stroke="{colour}" stroke-width="2" fill="none"><title>{item["object"]}</title></path>')
        svg.append('</g>')
        svg.append(f'<text x="{ox}" y="685" font-family="Arial" font-size="13">Interior -0.5m / glass 0m / exterior +0.5m</text>')
    svg.append('<text x="60" y="722" font-family="Arial" font-size="13">Blue: glass. Red: conservative dark enclosure. Gray: stone and joinery. Dimensions are model estimates.</text></svg>')
    (OUT/'native-longitudinal-section.svg').write_text(''.join(svg))


def build_component():
    OUT.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:layer.update()
    originals={o.name:fingerprint(o) for o in bpy.data.objects}
    original_materials={m.name:material_fingerprint(m) for m in bpy.data.materials}
    room_collections={c.name:sorted(o.name for o in c.all_objects) for c in bpy.data.collections if any(k in c.name.lower() for k in ('room','interior'))}
    section_before=cross_section()
    preview('before')
    replacements=[];modified_vertices={};owned=[]
    for source in list(bpy.data.collections[TARGET].all_objects):
        if source.type!='MESH' or source.hide_render:continue
        if not any(term in source.name.lower() for term in ('window','reveal','lintel','glazing_seal','stepped_jamb')) and source.name!='CLM_NEXT_ENVELOPE_open_four_sided_reveals' and 'street_glass' not in source.name:continue
        selected=[row for row in islands(source) if portal_island(*row[1:])]
        if not selected:continue
        indices={i for group,centre,low,high in selected for i in group if (source.matrix_world@source.data.vertices[i].co).z>6.95}
        assert indices
        obj=source.copy();obj.data=source.data.copy();obj.name=PREFIX+source.name
        obj['originalObject']=source.name;obj['changeScope']='Extend left side-portal window heads by0.585m; retain lower grid and all optics/finish'
        bpy.data.collections[TARGET].objects.link(obj);inverse=obj.matrix_world.inverted()
        for index in indices:
            point=obj.matrix_world@obj.data.vertices[index].co;point.z+=DELTA;obj.data.vertices[index].co=inverse@point
        obj.data.update();source.hide_render=True;source.hide_set(True);obj.hide_render=False;obj.hide_set(False)
        owned.append(obj);modified_vertices[obj.name]=sorted(indices)
        replacements.append({'originalObject':source.name,'original':source.name,'replacement':obj.name,'targetCollection':TARGET})
        assert len(obj.data.vertices)==len(source.data.vertices) and len(obj.data.polygons)==len(source.data.polygons)
        assert fingerprint(obj)['uv']==originals[source.name]['uv']
        assert fingerprint(obj)['materials']==originals[source.name]['materials']
        for index,(old,new) in enumerate(zip(source.data.vertices,obj.data.vertices)):
            difference=(obj.matrix_world@new.co)-(source.matrix_world@old.co)
            assert abs(difference.x)<1e-5 and abs(difference.y)<1e-5
            assert abs(difference.z-(DELTA if index in indices else 0))<2e-5
    assert len(replacements)>=7,len(replacements)
    # The original glass is now hidden; address its visible replacement directly.
    original_glass=bpy.data.objects['CLM196_FINISH_GLASS181_CLM_NEXT_ENVELOPE_street_glass']
    replacement_glass=bpy.data.objects[PREFIX+original_glass.name]
    # build_transom expects the visible modified mesh, preserving every optical slot.
    original_name=original_glass.name;original_glass.name=original_name+'_lookup';replacement_glass.name=original_name
    transom,backing,portal_records=build_transom()
    replacement_glass.name=PREFIX+original_name;original_glass.name=original_name
    owned.extend([transom,backing])
    checks=[]
    for portal in portal_records:
        normal=Vector(portal['normal']);point=Vector(portal['center']);point.z=7.40
        # Off-centre to avoid original vertical mullions.
        direction=Vector((-normal.y,normal.x,0));point+=direction*.13
        before=ray_mesh(original_glass,point,normal);after=ray_mesh(replacement_glass,point,normal)
        assert not before['hit'] and after['hit']
        # Inspect actual native mesh on both sides of the new upper light.
        front=trace_native(point+normal*.35,-normal,.37,exclude={replacement_glass.name,transom.name})
        back=trace_native(point-normal*.055,-normal,30,exclude={replacement_glass.name,transom.name})
        assert front is None,front
        assert back is not None and back['object']==backing.name and .13<back['distance']<.17,back
        checks.append({'probe':list(point),'normal':list(normal),'beforeGlass':before,'afterGlass':after,'newHeadGlassVerified':True,
                       'frontOpaqueObstruction':front,'behindGlazingFirstMesh':back,'nativeCrossSectionVerified':True})
    bm=bmesh.new();bm.from_mesh(transom.data)
    assert all(edge.is_manifold for edge in bm.edges)
    assert bm.calc_volume()>0
    transom_validation={'manifold':True,'positiveVolume':bm.calc_volume(),'vertices':len(bm.verts),'faces':len(bm.faces)};bm.free()
    bm=bmesh.new();bm.from_mesh(backing.data)
    assert all(edge.is_manifold for edge in bm.edges) and bm.calc_volume()>0
    backing_validation={'manifold':True,'positiveVolume':bm.calc_volume(),'vertices':len(bm.verts),'faces':len(bm.faces),'hasSurfaceUV':len(backing.data.uv_layers)>0};bm.free()
    assert all(fingerprint(bpy.data.objects[name])==state for name,state in originals.items())
    assert all(material_fingerprint(bpy.data.materials[name])==state for name,state in original_materials.items())
    assert all(sorted(o.name for o in bpy.data.collections[name].all_objects)==members for name,members in room_collections.items())
    section_after=cross_section()
    write_cross_section(section_before,section_after)
    preview('after')
    component=OUT/'clm-exterior214-component.blend'
    bpy.data.libraries.write(str(component),set(owned),fake_user=True)
    report={'version':214,'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':BASE_SHA,
            'componentPath':str(component.relative_to(ROOT)),'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),
            'targetCollection':TARGET,'addedObjects':[o.name for o in owned],
            'archivedObjects':[r['originalObject'] for r in replacements],'changedObjects':[],
            'replacements':replacements,'modifiedVertexIndices':modified_vertices,'portalWindowLayout':portal_records,
            'meshValidation':{'headGlazingRays':checks,'newTransom':transom_validation,'newBoundedEnclosure':backing_validation,'nativeLongitudinalSection':'native-longitudinal-section.json','sectionPreview':'native-longitudinal-section.svg'},
            'originalStates':{r['originalObject']:originals[r['originalObject']] for r in replacements},
            'originalGeometryPreserved':True,'originalUVPreserved':True,'originalMaterialNodesPreserved':True,'roomsPreserved':True,
            'replacementScope':'Only selected upper vertices of left side-portal window assemblies move vertically0.585m; all other vertices, topology, original UVs, material nodes and public interiors are preserved.',
            'source':{'url':PHOTO_URL,'pageURL':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate',
                      'local':'result/blender/clm-exterior214/official-estate-portal.jpg','sha256':hashlib.sha256((OUT/'official-estate-portal.jpg').read_bytes()).hexdigest(),
                      'liveRechecked':'2026-10-15','httpStatus':200,'matchesArchivedEstateImage':True,'photographCaptureDate':'Unknown',
                      'photoApproximatePixelRatios':{'imageSize':[300,400],'mainSashY':[59,133],'upperLightY':[35,54],'upperToMainSashHeight':19/74,'nativeUpperToMainSashHeight':.559/2.55,'scope':'Manual approximate image reading; perspective and low image resolution limit precision'},
                      'observed':'Side-portal main three-column sash has a separate shallow upper three-light transom below the stone head.'},
            'previews':['before-whole.png','after-whole.png','before-portal.png','after-portal.png'],
            'limitations':['Portal head extension and transom dimensions are photograph-guided estimates, not surveyed dimensions.',
                          'Official close photo documents the left side portal only; the other side portal remains unchanged.',
                          'No photograph capture date is known; live source availability does not establish2026 physical condition.',
                          'The added opaque upper-light backing is a conservative unobserved enclosure proxy, not a claim about a room, blind or surveyed wall.','Existing seven tall bays, opaque spandrels, other window divisions, sculpture approximations, rear envelope and roof geometry remain inherited estimates.']}
    saved={o.name:fingerprint(o) for o in owned}
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(component))
    assert all(fingerprint(bpy.data.objects[name])==state for name,state in saved.items())
    report['verification']={'savedComponentReopened':True,'componentObjects':len(saved),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA,'unchangedOriginalObjects':len(originals),'unchangedOriginalMaterials':len(original_materials),'preservedInteriorCollections':len(room_collections)}
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('CLM214_COMPONENT_READY',len(owned),flush=True)


if __name__=='__main__':
    build_component()
