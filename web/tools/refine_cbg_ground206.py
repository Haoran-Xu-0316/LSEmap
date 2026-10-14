"""Complete mapped LSE Square paving and its registered CBG entrance court.

Fixed project paths; regenerate the temporary native snapshot with
result/blender/cbg-ground206/inspect_ground_geometry.py when needed, prepare
in MachineLearning, then open this script in Blender. Verified delivery removes
the large temporary snapshot; paving-plan.json remains the reproducible input.
The component adds bounded walking surfaces only. Existing roads, trees, source
objects and material node trees remain exact. Course sizes and heights are
inherited estimates, not a measured current site survey.
"""
from pathlib import Path
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/cbg-ground206'
BASE=ROOT/'result/blender/LSE_campus_detailed_v205.blend'
SHA='bd8171002dda80d4228b99ded708b1a31da4645d333b518fd10125d8b3278a7a'
PREFIX='SITE206_CBG_'
FLOORS=['CBG203_ROOF_CBG203_WING_retained_CBG202_CBG_D_roof_and_ground_plates','CBG203_WING_registered_teaching_floor_plates','CBG205_PODIUM_registered_podium_floor_roof_plates']
PAVING=['SITE194_SITE_V47_Clare_Market','SITE194_SITE167_Houghton_paving_with_cover_openings','SITE194_Flush_LSE_Square_and_Sheffield_walking_joins','SITE194_SITE_V47_John_Watkins_Plaza']
THRESHOLD='CBG203_WING_retained_CBG202_CBG_D_entry_thresholds'


def prepare_geometry():
    from shapely import affinity,constrained_delaunay_triangles
    from shapely.geometry import Polygon,box,Point,LineString,mapping
    from shapely.ops import unary_union
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
    site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
    native=json.loads((OUT/'walking-geometry.json').read_text());lookup={o['name']:o for o in native}
    square=next(r for r in site['roads'] if r['properties'].get('name')=='LSE Square' and r['geometry']['type']=='Polygon')
    rings=square['geometry']['coordinates'];mapped=Polygon(rings[0],rings[1:])
    def surface(name,lowest=.039):
        return unary_union([Polygon([v[:2] for v in p['v']]).buffer(0) for p in lookup[name]['polygons'] if p['normal'][2]>.5 and min(v[2]for v in p['v'])>=lowest and max(v[2]for v in p['v'])<.15])
    # Actual registered ground floor faces are independent of older CBG mapping.
    floors=unary_union([surface(name,-.01) for name in FLOORS])
    other_buildings=unary_union([Polygon(b['rings'][0],b['rings'][1:]).buffer(0) for b in site['buildings'] if b['rings'] and b.get('code')!='CBG'])
    retained=unary_union([surface(name) for name in PAVING])
    # Four bounded vertices: native mapped square end; registered tower front
    # southwest end; two actual205 teaching floor court corners. Built RSHP020
    # shows the uninterrupted paved square between these two glazed fronts.
    court=Polygon([[40.48518362578718,-52.124262168440836],[34.78702058990411,-64.6139793911883],[33.918171784353945,-56.507879499977136],[36.805964236083994,-50.700186427999746]])
    front_registration=Polygon([rings[0][1],rings[0][2],rings[0][3],[34.78702058990411,-64.6139793911883],[56.078090232349076,-28.410521635325278]])
    assert front_registration.is_valid
    region=unary_union([mapped,court,front_registration]).difference(floors).difference(other_buildings.buffer(.025)).difference(retained).buffer(0)
    assert region.is_valid and not region.is_empty
    assert region.intersection(floors).area<1e-7
    assert all(region.intersection(Polygon(ring)).area<1e-7 for ring in rings[1:])
    def polygons(shape):
        if shape.is_empty:return []
        if shape.geom_type=='Polygon':return [shape]
        return [p for g in shape.geoms for p in polygons(g)]
    def triangles(shape):
        result=[]
        for poly in polygons(shape):
            for tri in constrained_delaunay_triangles(poly).geoms:
                if tri.area>1e-10:result.append([list(p)for p in list(tri.exterior.coords)[:3]])
        assert abs(sum(Polygon(t).area for t in result)-shape.area)<1e-6
        return result
    frame=json.loads((ROOT/'result/blender/cbg-georegistration202/rebuild-mapping.json').read_text())['frame']
    angle=math.degrees(math.atan2(frame['x_unit_SW'][1],frame['x_unit_SW'][0]))
    local=affinity.rotate(region,-angle,origin=(0,0));inner=local.buffer(-.06)
    xmin,ymin,xmax,ymax=local.bounds;length,width=.90,.30;tiles=[]
    for row in range(math.floor(ymin/width),math.ceil(ymax/width)):
        shift=.5*length*(row%2)
        for column in range(math.floor((xmin-shift)/length),math.ceil((xmax-shift)/length)):
            x,y=column*length+shift,row*width
            shape=box(x+.003,y+.003,x+length-.003,y+width-.003).intersection(inner)
            if shape.area<.002:continue
            tiles.append(dict(shade=(row*73856093 ^ column*19349663)%5,triangles=triangles(affinity.rotate(shape,angle,origin=(0,0)))))
    edging=affinity.rotate(local.difference(inner),angle,origin=(0,0))
    # Probe stable tile centres and both walking joins. Heights are sampled
    # against the actual complete scene during component build, not inferred.
    probes=[]
    for ix in range(math.floor(region.bounds[0]),math.ceil(region.bounds[2])):
        for iy in range(math.floor(region.bounds[1]),math.ceil(region.bounds[3])):
            pt=Point(ix+.371,iy+.419)
            if region.buffer(-.08).contains(pt):probes.append([pt.x,pt.y])
    joins=[]
    common=region.boundary.intersection(retained.boundary.buffer(.00005))
    for geom in getattr(common,'geoms',[common]):
        if geom.geom_type=='LineString' and geom.length>.15:
            center=geom.interpolate(.5,normalized=True);joins.append([center.x,center.y])
    thresholds=[]
    for p in lookup[THRESHOLD]['polygons']:
        if p['normal'][2]<.5:continue
        poly=Polygon([v[:2]for v in p['v']]);center=poly.centroid
        # Thresholds project across y0; the public approach is negative localy.
        point=Point(center.x-frame['y_unit_SE_rear'][0]*.70,center.y-frame['y_unit_SE_rear'][1]*.70)
        thresholds.append(dict(point=[point.x,point.y],thresholdZ=p['v'][0][2],insidePaving=region.covers(point)))
    report=dict(mappedSquareId=square['id'],mappedSquareAreaM2=mapped.area,mappedTreePoolCount=len(rings)-1,courtBoundedAreaM2=court.area,
                addedPavingAreaM2=region.area,mappedPartAreaM2=region.intersection(mapped).area,courtBeyondMappedAreaM2=region.intersection(court).difference(mapped).area,registeredFrontBeyondMappedAreaM2=region.difference(mapped).difference(court).area,
                retainedDetailedPavingOverlapM2=region.intersection(retained).area,registeredCBGGroundFootprintOverlapM2=region.intersection(floors).area,
                otherBuildingOverlapM2=region.intersection(other_buildings).area,region=mapping(region),floorFootprint=mapping(floors),mappedTreePools=[mapping(Polygon(r))for r in rings[1:]],
                base=triangles(region),edge=triangles(edging),tiles=tiles,angleDegrees=angle,courseEstimateMetres=[length,width],walkingProbes=probes,retainedBoundaryProbes=joins,thresholdApproaches=thresholds,
                derivation='Exact archived mapped stone-paved LSE Square exterior/hole rings plus bounded205 CBG entrance recess and correction between mapped northeast/southwest front-edge vertices and registered ground-floor facade; subtract actual registered CBG ground floors, other mapped buildings with25mm buffer and existing detailed paving. No corridor buffering or route-width enlargement.',
                references=['result/blender/site_geometry.json','result/blender/cbg-georegistration202/rebuild-mapping.json','data/collections/exteriors/images/cbg_rshp_020.jpg','data/collections/exteriors/images/cbg_rshp_041.jpg','web/tools/prepare_campus_paving.py'])
    (OUT/'paving-plan.json').write_text(json.dumps(report,separators=(',',':'))+'\n')
    print('CBG206_PREPARED',round(region.area,3),len(tiles),len(probes),thresholds,flush=True)


def geometry_signature(obj):
    import array
    digest=hashlib.sha256(str([list(row)for row in obj.matrix_world]).encode())
    for values,field,kind,count in [(obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1),(obj.data.polygons,'loop_total','i',1)]:
        data=array.array(kind,[0])*(len(values)*count);values.foreach_get(field,data);digest.update(data.tobytes())
    for layer in obj.data.uv_layers:
        data=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',data);digest.update(layer.name.encode()+data.tobytes())
    return digest.hexdigest()


def material_signature(material):
    nodes=[]
    for node in material.node_tree.nodes:
        inputs=[]
        for socket in node.inputs:
            if not hasattr(socket,'default_value'):continue
            value=socket.default_value
            try:value=list(value)
            except TypeError:pass
            if isinstance(value,(str,int,float,bool,list)):inputs.append((socket.name,value))
        nodes.append(dict(name=node.name,type=node.type,inputs=inputs,ramp=[(e.position,list(e.color))for e in node.color_ramp.elements]if hasattr(node,'color_ramp')else None))
    links=sorted((l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name)for l in material.node_tree.links)
    return hashlib.sha256(json.dumps(dict(diffuse=list(material.diffuse_color),nodes=nodes,links=links),sort_keys=True).encode()).hexdigest()


def build_component():
    import bpy
    from mathutils import Vector
    sys.path.insert(0,str(ROOT/'web/tools'))
    from integrate_exterior_round194 import object_fingerprint
    from refine_street_connections194 import render_review
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
    previous_geometry={}
    component=OUT/'cbg-ground206-component.blend'
    if component.exists():
        with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=[PREFIX+'square_joint_bed',PREFIX+'square_stone_courses']
        previous_geometry={o.name:geometry_signature(o)for o in dst.objects}
    bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];scene=bpy.context.scene
    before={o.name:object_fingerprint(o)for o in bpy.data.objects}
    plan=json.loads((OUT/'paving-plan.json').read_text());collection=bpy.data.collections['00_SITE']
    # Five independent stone copies receive a photo-informed pale palette.
    # Native node trees stay exact; copied noise, grain and roughness are retained.
    source=bpy.data.objects['SITE194_SITE167_Houghton_paving_with_cover_openings']
    materials=list(source.data.materials);names=[m.name for m in materials]
    grout=next(i for i,n in enumerate(names)if 'grout' in n)
    shades=[next(index for index,n in enumerate(names)if 'slab_'+str(shade)+'_'in n)for shade in range(5)]
    edge=next(i for i,n in enumerate(names)if 'edge_1' in n)
    native_materials={m.name:material_signature(m)for m in bpy.data.materials if m.use_nodes}
    palette=[];center=(.35,.36,.345)
    for shade,(slot,factor)in enumerate(zip(shades,[.82,.91,1.,1.09,1.18])):
        original=materials[slot];target=original.copy();target.name=PREFIX+'pale_gray_stone_'+str(shade)
        old=list(original.diffuse_color);color=tuple(c*factor for c in center)+(1.,)
        target.diffuse_color=color
        for node in target.node_tree.nodes:
            if node.type=='BSDF_PRINCIPLED':node.inputs['Base Color'].default_value=color
            elif node.type=='VALTORGB':
                for element in node.color_ramp.elements:
                    existing=list(element.color);element.color=tuple(existing[i]*color[i]/old[i]for i in range(3))+(existing[3],)
        target['sourceMaterial']=original.name;target['paletteEvidence']='Archived RSHP020 pale gray variegated plaza slabs; visual estimate, not measured albedo'
        materials[slot]=target
        palette.append(dict(source=original.name,target=target.name,sourceDiffuseLinear=old,targetDiffuseLinear=list(color),targetLinearLuminance=.2126*color[0]+.7152*color[1]+.0722*color[2],sourceNodeSignature=native_materials[original.name],targetNodeSignature=material_signature(target),roughness=.88,noiseScale=24.,bumpStrength=.2,bumpDistance=.0005,nodeStructureRetained=True))
    def mesh_object(suffix,sets):
        vertices=[];faces=[];material_ids=[]
        for triangles,z,index in sets:
            for tri in triangles:
                ids=[]
                a,b,c=[Vector((p[0],p[1],z))for p in tri]
                if (b-a).cross(c-a).z<0:tri=list(reversed(tri))
                for p in tri:ids.append(len(vertices));vertices.append((p[0],p[1],z))
                faces.append(tuple(ids));material_ids.append(index)
        mesh=bpy.data.meshes.new(PREFIX+suffix);mesh.from_pydata(vertices,[],faces);mesh.update()
        for material in materials:mesh.materials.append(material)
        for face,index in zip(mesh.polygons,material_ids):face.material_index=index
        uv=mesh.uv_layers.new(name='MetricUV')
        for face in mesh.polygons:
            for loop in face.loop_indices:
                p=mesh.vertices[mesh.loops[loop].vertex_index].co;uv.data[loop].uv=(p.x,p.y)
        obj=bpy.data.objects.new(PREFIX+suffix,mesh);collection.objects.link(obj)
        obj['destinationCollection']='00_SITE';obj['scope']='Mapped stone plaza and bounded registered entrance court; estimated inherited pavement datum/courses';obj['sourceMappedPedestrianArea']=plan['mappedSquareId'];obj['metricUVUnits']='metres'
        return obj
    def probes(points):
        rows=[];deps=bpy.context.evaluated_depsgraph_get()
        for x,y in points:
            hit,pos,normal,face,obj,matrix=scene.ray_cast(deps,Vector((x,y,.25)),Vector((0,0,-1)),distance=.40)
            rows.append(dict(point=[x,y],hit=bool(hit),object=obj.name if hit else None,z=float(pos.z)if hit else None,normalZ=float(normal.z)if hit else None))
        return rows
    walking_before=probes(plan['walkingProbes']);threshold_before=probes([p['point']for p in plan['thresholdApproaches']])
    views=[('square-overview',(35,-38,70),(35,-38,0),56),('southwest-door',(40,-48,8),(38,-57,0),17)]
    for label,loc,target,scale in views:
        if not (OUT/(label+'-before.png')).exists():render_review(scene,OUT/(label+'-before.png'),loc,target,scale)
    owned=[mesh_object('square_joint_bed',[(plan['base'],.04,grout)]),mesh_object('square_stone_courses',[(p['triangles'],.05,shades[p['shade']])for p in plan['tiles']]+[(plan['edge'],.05,edge)])]
    assert all(not previous_geometry or geometry_signature(o)==previous_geometry[o.name]for o in owned),'Geometry changed during palette correction'
    for layer in scene.view_layers:layer.update()
    walking_after=probes(plan['walkingProbes'])
    threshold_occupancy=[p for p in walking_after if p['object']==THRESHOLD and abs(p['z']-.07)<1e-5]
    walking_after=[p for p in walking_after if p not in threshold_occupancy]
    failed=[p for p in walking_after if not (p['hit']and p['object'].startswith(PREFIX)and .0399<=p['z']<=.0501 and p['normalZ']>.99)]
    (OUT/'probe-failures.json').write_text(json.dumps(failed,indent=2)+'\n')
    assert not failed, str(failed[:10])
    threshold_after=probes([p['point']for p in plan['thresholdApproaches']]);assert all(p['object'].startswith(PREFIX)for p in threshold_after)
    sky=[];deps=bpy.context.evaluated_depsgraph_get()
    for p in walking_after[::max(1,len(walking_after)//80)]:
        x,y=p['point'];hit,pos,normal,face,obj,matrix=scene.ray_cast(deps,Vector((x,y,100)),Vector((0,0,-1)),distance=101)
        sky.append(dict(point=[x,y],firstObject=obj.name if hit else None,firstZ=float(pos.z)if hit else None,groundFloorClear=p['z']<.051))
    joins=probes(plan['retainedBoundaryProbes']);assert all(p['hit']and .039<=p['z']<=.051 for p in joins)
    assert all(object_fingerprint(bpy.data.objects[n])==fp for n,fp in before.items()),'Native object changed'
    assert all(material_signature(bpy.data.materials[name])==signature for name,signature in native_materials.items()),'Native material changed'
    component=OUT/'cbg-ground206-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
    report={key:value for key,value in plan.items()if key not in ['base','edge','tiles','walkingProbes','retainedBoundaryProbes']}
    report.update(materialPaletteCopies=palette,addedMaterials=[p['target']for p in palette],materialPaletteEvidence='RSHP020 built photo pale gray slab appearance compared with dark production gallery. Independent linear RGB center(.35,.36,.345), factors.82,.91,1,1.09,1.18; appearance estimate, not measured albedo.',geometrySignatures={o.name:geometry_signature(o)for o in owned},version=206,baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),addedObjects=[o.name for o in owned],archivedObjects=[],changedObjects=[],targetCollection='00_SITE',changes=[dict(source=None,owned=o.name,collection='00_SITE')for o in owned],
                  walkingSurfaceZ=dict(grout=.04,stone=.05,nativeRoad=.024,nativeThreshold=.07),walkingFirstHitBefore=walking_before,walkingFirstHitAfter=walking_after,preservedThresholdOccupancy=threshold_occupancy,thresholdApproachBefore=threshold_before,thresholdApproachAfter=threshold_after,retainedBoundaryAfter=joins,skyFirstHitAfter=sky,
                  verification=dict(nativeMaterialNodeSignaturesUnchanged=True,newGeometryMatchesPreviousComponent=True,nativeFingerprintsUnchanged=True,sourceSha256Unchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA),
                  scope='Complete missing detailed LSE Square paving; connect exact mapped area to registered CBG southwest door recess; preserve six mapped tree pools and all retained native roads/buildings/furniture/materials.',
                  limitations=['Archived GIS boundaries and built photos establish a bounded paved area, not a current surveyed kerb datum.','Slab90x30cm course,6mm joints and40/50mm local heights are estimates inherited from existing campus treatment.','Existing tower thresholds top70mm retain a20mm step above the new50mm stone; no unsupported building datum edit.','Existing low walking-road slabs remain underneath; no change to asphalt networks, vegetation or future Portugal Street schemes.'])
    label,loc,target,scale=views[1]
    render_review(scene,OUT/(label+'-palette-after.png'),loc,target,scale)
    report['renderedViews']=['southwest-door-palette-after.png']
    report['retainedGeometryReviewViews']=[label+'-'+phase+'.png'for label,*_ in views for phase in ['before','after']]
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('CBG206_COMPONENT',len(owned),len(walking_after),flush=True)


if __name__=='__main__':
    try:import bpy
    except ImportError:prepare_geometry()
    else:build_component()
