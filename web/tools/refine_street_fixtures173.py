"""Fill the mapped Houghton/New Inn walking-surface seam without tile meshes.

Native172 leaves this estimated10.14m² portion of New Inn Passage atz0.024,
while the photographed continuous Houghton stone approach is atz0.05. Outline
is clipped to source road, subtracts existing paving and mapped building rings,
and retains a3mm isolation joint. Original geometry and materials stay intact.
Photo date unknown; this is a reference-informed approximation, not a survey.
"""
import bpy
from mathutils import Vector

OWNED='SITE173_Houghton_New_Inn_flush_paving_join'
PHOTO='data/collections/public-realm-2026/user-references/reference-09.png'
PATCH = {'polygons': [{'outer': [(5.285913258458404, -96.72574656639358),
                         (5.037478284875984, -98.54959182334512),
                         (5.374527835479644, -98.37363586706445),
                         (7.215072362727327, -93.90235637916373),
                         (6.860808415683523, -93.68098765432916),
                         (6.444860833193122, -94.28965997131004),
                         (4.3337777496290935, -93.1320332518961),
                         (4.1168411022845115, -93.5895533392779),
                         (4.040995378379718, -93.55358937985409),
                         (3.4179364488543693, -94.46532915846142),
                         (3.1036400480468025, -94.96463798772984),
                         (2.840632825689736, -96.8954649766313),
                         (4.371221982770636, -96.09642236088868),
                         (4.487464341294105, -96.03936817921947),
                         (4.49124887176246, -96.03762692577091),
                         (4.731519947549578, -95.9412134087231),
                         (4.7355173833064805, -95.93983533203554),
                         (4.984180716534064, -95.86776724898215),
                         (4.988294774747156, -95.8667944667696),
                         (5.2428872680766245, -95.81979036713061),
                         (5.247078276176648, -95.81923102565831),
                         (5.505082405100334, -95.79774877671323),
                         (5.509308033780641, -95.797610962477),
                         (5.724317930871082, -95.80115110817769)],
               'holes': [],
               'triangles': [[(4.371221982770636, -96.09642236088868),
                              (2.840632825689736, -96.8954649766313),
                              (3.1036400480468025, -94.96463798772984)],
                             [(4.1168411022845115, -93.5895533392779),
                              (3.4179364488543693, -94.46532915846142),
                              (4.040995378379718, -93.55358937985409)],
                             [(4.1168411022845115, -93.5895533392779),
                              (4.3337777496290935, -93.1320332518961),
                              (6.444860833193122, -94.28965997131004)],
                             [(6.444860833193122, -94.28965997131004),
                              (6.860808415683523, -93.68098765432916),
                              (7.215072362727327, -93.90235637916373)],
                             [(5.285913258458404, -96.72574656639358),
                              (5.374527835479644, -98.37363586706445),
                              (5.037478284875984, -98.54959182334512)],
                             [(5.374527835479644, -98.37363586706445),
                              (5.285913258458404, -96.72574656639358),
                              (5.724317930871082, -95.80115110817769)],
                             [(4.487464341294105, -96.03936817921947),
                              (4.371221982770636, -96.09642236088868),
                              (3.1036400480468025, -94.96463798772984)],
                             [(5.509308033780641, -95.797610962477),
                              (6.444860833193122, -94.28965997131004),
                              (5.724317930871082, -95.80115110817769)],
                             [(5.724317930871082, -95.80115110817769),
                              (7.215072362727327, -93.90235637916373),
                              (5.374527835479644, -98.37363586706445)],
                             [(3.4179364488543693, -94.46532915846142),
                              (4.487464341294105, -96.03936817921947),
                              (3.1036400480468025, -94.96463798772984)],
                             [(5.505082405100334, -95.79774877671323),
                              (6.444860833193122, -94.28965997131004),
                              (5.509308033780641, -95.797610962477)],
                             [(7.215072362727327, -93.90235637916373),
                              (5.724317930871082, -95.80115110817769),
                              (6.444860833193122, -94.28965997131004)],
                             [(4.487464341294105, -96.03936817921947),
                              (3.4179364488543693, -94.46532915846142),
                              (4.49124887176246, -96.03762692577091)],
                             [(5.247078276176648, -95.81923102565831),
                              (6.444860833193122, -94.28965997131004),
                              (5.505082405100334, -95.79774877671323)],
                             [(4.49124887176246, -96.03762692577091),
                              (3.4179364488543693, -94.46532915846142),
                              (4.731519947549578, -95.9412134087231)],
                             [(6.444860833193122, -94.28965997131004),
                              (5.247078276176648, -95.81923102565831),
                              (4.1168411022845115, -93.5895533392779)],
                             [(4.731519947549578, -95.9412134087231),
                              (3.4179364488543693, -94.46532915846142),
                              (4.7355173833064805, -95.93983533203554)],
                             [(5.2428872680766245, -95.81979036713061),
                              (4.1168411022845115, -93.5895533392779),
                              (5.247078276176648, -95.81923102565831)],
                             [(4.7355173833064805, -95.93983533203554),
                              (3.4179364488543693, -94.46532915846142),
                              (4.984180716534064, -95.86776724898215)],
                             [(4.988294774747156, -95.8667944667696),
                              (4.1168411022845115, -93.5895533392779),
                              (5.2428872680766245, -95.81979036713061)],
                             [(4.1168411022845115, -93.5895533392779),
                              (4.984180716534064, -95.86776724898215),
                              (3.4179364488543693, -94.46532915846142)],
                             [(4.984180716534064, -95.86776724898215),
                              (4.1168411022845115, -93.5895533392779),
                              (4.988294774747156, -95.8667944667696)]]},
              {'outer': [(7.1563051124390356, -93.2485758153241),
                         (6.995768000333056, -93.48349603147712),
                         (7.307346735571035, -93.67819200582368),
                         (7.43668381346305, -93.36399030364134)],
               'holes': [],
               'triangles': [[(7.1563051124390356, -93.2485758153241),
                              (7.43668381346305, -93.36399030364134),
                              (7.307346735571035, -93.67819200582368)],
                             [(7.307346735571035, -93.67819200582368),
                              (6.995768000333056, -93.48349603147712),
                              (7.1563051124390356, -93.2485758153241)]]}],
 'area': 10.14303095862028,
 'sourceRoad': 'Road_New Inn Passage.002',
 'bottom': 0.024000000208616257,
 'top': 0.05}


def apply_street_fixtures173():
    if bpy.data.objects.get(OWNED):
        return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[]}
    assert bpy.data.objects.get(PATCH['sourceRoad']), 'Expected mapped road retained'
    assert bpy.data.objects.get('SITE167_Houghton_paving_with_cover_openings')
    verts=[];faces=[];lookup={}
    def vertex(p,z):
        key=(round(p[0],7),round(p[1],7),round(z,7))
        if key not in lookup:lookup[key]=len(verts);verts.append(key)
        return lookup[key]
    for polygon in PATCH['polygons']:
        for t in polygon['triangles']:
            a,b,c=t
            if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:t=list(reversed(t))
            faces.append([vertex(p,PATCH['top']) for p in t])
            faces.append([vertex(p,PATCH['bottom']) for p in reversed(t)])
        for ring in [polygon['outer']]+polygon['holes']:
            for a,b in zip(ring,ring[1:]+ring[:1]):
                faces.append([vertex(a,PATCH['bottom']),vertex(b,PATCH['bottom']),vertex(b,PATCH['top']),vertex(a,PATCH['top'])])
    mesh=bpy.data.meshes.new(OWNED+'_mesh');mesh.from_pydata(verts,[],faces);mesh.update()
    uv=mesh.uv_layers.new(name='SurfaceUV')
    # Metric orientation follows existing Houghton staggered-sett courses.
    u=Vector((0.43271524132966066, 0.9015306538998069));v=Vector((-0.9015306538998069, 0.43271524132966066))
    for face in mesh.polygons:
        for index in face.loop_indices:
            p=mesh.vertices[mesh.loops[index].vertex_index].co
            point=Vector((p.x,p.y));uv.data[index].uv=(point.dot(u)-(-80.39918901011148),point.dot(v)-(-46.50139762046013))
    material=bpy.data.materials.new('SITE173_SITE_V47_slab_Houghton_paving_continuation');material.use_nodes=True
    material.diffuse_color=(.18,.195,.188,1);nodes=material.node_tree.nodes;links=material.node_tree.links
    shader=nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.88
    tex=nodes.new('ShaderNodeTexCoord');brick=nodes.new('ShaderNodeTexBrick')
    brick.inputs['Scale'].default_value=1;brick.inputs['Brick Width'].default_value=.30;brick.inputs['Row Height'].default_value=.15
    brick.inputs['Mortar Size'].default_value=.004;brick.inputs['Mortar Smooth'].default_value=.002
    brick.inputs['Color1'].default_value=(.171,.18525,.1786,1);brick.inputs['Color2'].default_value=(.1845,.199875,.1927,1)
    brick.inputs['Mortar'].default_value=(.073,.079,.075,1)
    links.new(tex.outputs['UV'],brick.inputs['Vector']);links.new(brick.outputs['Color'],shader.inputs['Base Color'])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.0008
    links.new(brick.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
    material['scope']='Estimated stone courses match retained172 Houghton palette; no photograph texture'
    mesh.materials.append(material);obj=bpy.data.objects.new(OWNED,mesh)
    bpy.data.collections['03_PUBLIC_REALM'].objects.link(obj)
    obj['reference']=PHOTO;obj['dimensionsEstimated']=True;obj['geometryRole']='Ground walking surface continuation'
    obj['sourceRoad']=PATCH['sourceRoad'];obj['topHeight']=PATCH['top'];obj['sourceRoadTop']=PATCH['bottom']
    return {'alreadyApplied':False,'addedObjects':[OWNED],'archivedObjects':[],'changedObjects':[],
            'areaEstimate':PATCH['area'],'topHeight':PATCH['top'],'filledLevelDifferenceEstimate':PATCH['top']-PATCH['bottom'],
            'isolationJointEstimate':.003,'paverDimensionsEstimate':[.30,.15],
            'photoReference':PHOTO,'photoDate':'Unknown; user-supplied photo',
            'registration':'Existing native New Inn Passage.002 outline; subtract native Houghton top paving faces, mapped building footprints and actual CBG/COL ground-height mesh sections',
            'limitations':['Small paved transition is inferred from continuous photographed walking surface, not a measured current layout.',
                           'Only existing mapped walking-road footprint is filled; no inferred full terrace, boundary wall or additional barrier.',
                           'Original road remains the supporting source beneath; original buildings, posts, tree boxes and utility covers remain unchanged.']}
