"""Recover the photographed John Watkins Plaza outdoor table seating.

Four estimated timber picnic tables flank the existing library approach over
roughly25m. The2021official photograph shows paired benches on A-frame tables,
not only free-standing slatted benches. Library southwest window frontage and
opposite red-brick frontage register the area. Original benches, roads, café,
planting and paving are retained; historical movable furniture is not presented
as an exact current2026inventory. One merged mesh keeps runtime overhead small.
"""
import math
import bpy
from mathutils import Vector

OWNED='SITE174_John_Watkins_Plaza_picnic_seating'
PHOTO='data/collections/streets/derived/review_public_realm_pdf_page75.png'
PHOTO_URL='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/2022-LSE-Public-Realm-Strategy.pdf'
# ENU metre estimates from native frontage corners, not surveyed table centres.
CENTRES=((29.4238,10.2441),(38.5558,2.4681),(27.,2.),(39.,-6.))
ALONG=Vector((.761,-.648,0)).normalized()
ACROSS=Vector((-ALONG.y,ALONG.x,0))


def apply_public_realm174():
    if bpy.data.objects.get(OWNED):
        return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[]}
    scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
    for layer in scene.view_layers:layer.update()
    deps=bpy.context.evaluated_depsgraph_get();vertices=[];faces=[];primitiveVolumes=[];supports=[]
    # Eight box corners indexed(x,y,z), outward winding on every face.
    winding=((0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5))
    def box(center,axes,size):
        first=len(vertices)
        for i in range(8):
            p=Vector(center)
            for axis,dimension,bit in zip(axes,size,(4,2,1)):
                p+=axis*dimension*(.5 if i&bit else -.5)
            vertices.append(tuple(p))
        faces.extend(tuple(first+i for i in f) for f in winding)
        assert axes[0].cross(axes[1]).dot(axes[2])>0.999
        primitiveVolumes.append(math.prod(size))
    def beam(start,end,width,depth):
        direction=(end-start).normalized();side=ALONG
        across=direction.cross(side).normalized()
        box((start+end)/2,(side,across,direction),(width,depth,(end-start).length))
    for table,xy in enumerate(CENTRES):
        center=Vector((*xy,0));footLevels=[]
        for length in (-.65,.65):
            for side in (-.66,.66):
                point=center+ALONG*length+ACROSS*side
                hit=scene.ray_cast(deps,point+Vector((0,0,.35)),Vector((0,0,-1)),distance=.5)
                assert hit[0] and hit[4].name=='SITE_V47_John_Watkins_Plaza', (table,tuple(point),hit[4].name if hit[0] else None)
                assert .039<=hit[1].z<=.051
                samples=[]
                for dx in (-.05,0,.05):
                    for dy in (-.04,0,.04):
                        sample=point+ALONG*dx+ACROSS*dy
                        contact=scene.ray_cast(deps,sample+Vector((0,0,.35)),Vector((0,0,-1)),distance=.5)
                        assert contact[0] and contact[4].name=='SITE_V47_John_Watkins_Plaza'
                        samples.append(contact[1].z)
                ground=max(samples)
                footLevels.append(ground);supports.append({'table':table,'xy':list(point.xy),'groundObject':hit[4].name,'groundHeight':ground,'centerRayHeight':hit[1].z,'footSupportSamples':samples})
                # Bottom-centred bevel-free prism starts1mm above the actual
                # slab/grout top; no legs sink through the retained paving.
                low=point+Vector((0,0,ground+.018))
                high=center+ALONG*length+ACROSS*(side*.48)+Vector((0,0,.767))
                for _ in range(8):
                    direction=(high-low).normalized()
                    low.z=ground+.001+.0375*abs(direction.cross(ALONG).normalized().z)
                beam(low,high,.09,.075)
        axes=(ALONG,ACROSS,Vector((0,0,1)))
        for slat in range(5):
            box(center+ACROSS*((slat-2)*.152)+Vector((0,0,.815)),axes,(1.8,.14,.065))
        for side in (-1,1):
            for slat in (-.075,.075):
                box(center+ACROSS*(side*.655+slat)+Vector((0,0,.5075)),axes,(1.8,.14,.055))
        for length in (-.65,.65):
            box(center+ALONG*length+Vector((0,0,.4625)),axes,(.09,1.64,.065))
            box(center+ALONG*length+Vector((0,0,.75)),axes,(.09,.77,.06))
        box(center+Vector((0,0,.275)),axes,(1.38,.085,.085))
    mesh=bpy.data.meshes.new(OWNED+'_mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
    layer=mesh.uv_layers.new(name='SurfaceUV')
    for face in mesh.polygons:
        origin=mesh.vertices[face.vertices[0]].co;horizontal=(mesh.vertices[face.vertices[1]].co-origin).normalized();vertical=face.normal.cross(horizontal)
        for index in face.loop_indices:
            point=mesh.vertices[mesh.loops[index].vertex_index].co-origin
            layer.data[index].uv=(point.dot(horizontal),point.dot(vertical))
    material=bpy.data.materials.new('SITE174_SITE_V47_wood_weathered_picnic_tables');material.use_nodes=True;material.diffuse_color=(.175,.10,.047,1)
    nodes=material.node_tree.nodes;links=material.node_tree.links;shader=nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.82
    tex=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=6;noise.inputs['Detail'].default_value=2
    ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.13,.069,.030,1);ramp.color_ramp.elements[-1].color=(.215,.132,.073,1)
    links.new(tex.outputs['Object'],noise.inputs['Vector']);links.new(noise.outputs['Fac'],ramp.inputs['Fac']);links.new(ramp.outputs['Color'],shader.inputs['Base Color'])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.15;bump.inputs['Distance'].default_value=.0007;links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
    mesh.materials.append(material);obj=bpy.data.objects.new(OWNED,mesh);bpy.data.collections['03_PUBLIC_REALM'].objects.link(obj)
    obj['sourceReference']=PHOTO;obj['sourceDate']='2021 photograph, published2022; current table inventory unverified';obj['dimensionsEstimated']=True;obj['tableCount']=4
    return {'alreadyApplied':False,'addedObjects':[OWNED],'archivedObjects':[],'changedObjects':[],
            'tableCentresEstimate':[list(p) for p in CENTRES],'supportContacts':supports,'primitiveVolumes':primitiveVolumes,
            'tableDimensionsEstimate':{'length':1.8,'overallBenchWidth':1.60,'tabletopHeight':.8475,'seatHeight':.535},
            'sourcePhoto':PHOTO,'sourceUrl':PHOTO_URL,'sourceDate':'2021; report2022',
            'registration':'Native southwest Library frontage near(23.8708,17.5981)–(77.9363,-28.4538), with opposite brick frontage; movable table centers estimated',
            'limitations':['Four tables recover the photographed outdoor seating type and distribution, not exact historical count or current movable positions.',
                           'Native surface support is checked at each leg; existing mapped café and existing benches remain unchanged.',
                           'No proposed future Portugal Street landscape, unlocated retaining walls, lights or barriers are added.']}
