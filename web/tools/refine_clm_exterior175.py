"""Restore the photographed low guards across Clement's ground-floor windows.

The2025-10-08 authored official LSE Property Handbook(p18, printed16) shows
black framed low guard panels in front of both flanking ground-floor window
banks. Capture date is unknown. The native174 façade currently lacks these
continuous guards. Their curved registration follows the retained street bays;
span, profile and height are estimates, not a measured2026 condition survey.
Existing columns, doors, window optics, upper stonework and roof stay intact.
"""
import math
import bpy
from mathutils import Vector

OWNED='CLM_EXTERIOR175_ground_window_frontage_guards'
PHOTO='result/blender/clm_exterior175/official-page18-image7.png'
URL='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf'
SEGMENTS = [[0,
  5.4314518319260605,
  [99.45853424072266, -148.11692810058594],
  [0.8998045325279236, -0.4362931251525879],
  [-0.4362931251525879, -0.8998045325279236]],
 [5.4314518319260605,
  14.54677492783562,
  [104.34577941894531, -150.48663330078125],
  [0.9397959113121033, -0.34173622727394104],
  [-0.34173622727394104, -0.9397959113121033]],
 [14.54677492783562,
  24.731364266618833,
  [112.91232299804688, -153.60166931152344],
  [0.9910821914672852, -0.13325197994709015],
  [-0.13325197994709015, -0.9910821914672852]],
 [24.731364266618833,
  31.43782726525609,
  [123.00608825683594, -154.9587860107422],
  [0.9999322891235352, 0.011637834832072258],
  [0.011637834832072258, -0.9999322891235352]]]
SPANS = ((3.6, 8.5), (22.2, 27.8))



def _point(s,d,z):
    segment=next((r for r in SEGMENTS if s<=r[1]),SEGMENTS[-1])
    start,end,a,u,n=segment
    xy=Vector(a)+Vector(u)*(s-start)+Vector(n)*d
    return Vector((xy.x,xy.y,z))


def apply_clm_exterior175():
    if bpy.data.objects.get(OWNED):
        return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[]}
    scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
    for layer in scene.view_layers:layer.update()
    deps=bpy.context.evaluated_depsgraph_get();verts=[];faces=[];volumes=[];supports=[]
    winding=((0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5))
    def beam(a,b,width,depth):
        direction=(b-a).normalized()
        normal=Vector((0,0,1)) if abs(direction.z)<.5 else Vector((1,0,0))
        side=normal.cross(direction).normalized();across=direction.cross(side).normalized()
        axes=(side,across,direction);size=(width,depth,(b-a).length);first=len(verts)
        assert side.cross(across).dot(direction)>.999
        for k in range(8):
            p=(a+b)/2
            for axis,dim,bit in zip(axes,size,(4,2,1)):p+=axis*dim*(.5 if k&bit else -.5)
            verts.append(tuple(p))
        faces.extend(tuple(first+k for k in f) for f in winding);volumes.append(math.prod(size))
    for bank,(start,end) in enumerate(SPANS):
        pitch=(end-start)/16;posts=[]
        for j in range(17):
            s=start+j*pitch;xy=_point(s,.84,0)
            hit=scene.ray_cast(deps,xy+Vector((0,0,1.1)),Vector((0,0,-1)),distance=1.3)
            assert hit[0] and -.06<=hit[1].z<=.15,(bank,j,hit[4].name if hit[0] else None,hit[1].z if hit[0] else None)
            base=hit[1].z+.003;posts.append((s,base));supports.append({'bank':bank,'s':s,'world':list(xy.xy),'supportObject':hit[4].name,'supportZ':hit[1].z,'clearance':.003})
            beam(_point(s,.84,base),_point(s,.84,base+.89),.045,.045)
        for j,((a,za),(b,zb)) in enumerate(zip(posts,posts[1:])):
            for height,thickness in ((.095,.045),(.48,.035),(.89,.055)):
                # Split rails at source curvature vertices; straight beams do
                # not cut the convex frontage or bridge across a curved corner.
                cuts=[a]+[r[1] for r in SEGMENTS[:-1] if a<r[1]<b]+[b]
                for aa,bb in zip(cuts,cuts[1:]):
                    az=za+(zb-za)*(aa-a)/(b-a);bz=za+(zb-za)*(bb-a)/(b-a)
                    beam(_point(aa,.84,az+height),_point(bb,.84,bz+height),.045,thickness)
    mesh=bpy.data.meshes.new(OWNED+'_mesh');mesh.from_pydata(verts,[],faces);mesh.update();uv=mesh.uv_layers.new(name='SurfaceUV')
    for face in mesh.polygons:
        origin=mesh.vertices[face.vertices[0]].co;horizontal=(mesh.vertices[face.vertices[1]].co-origin).normalized();vertical=face.normal.cross(horizontal)
        for i in face.loop_indices:
            point=mesh.vertices[mesh.loops[i].vertex_index].co-origin;uv.data[i].uv=(point.dot(horizontal),point.dot(vertical))
    material=bpy.data.materials.new('CLM_EXTERIOR175_satin_dark_bronze_frontage_iron');material.use_nodes=True;material.diffuse_color=(.012,.016,.014,1)
    shader=material.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=material.diffuse_color;shader.inputs['Metallic'].default_value=.38;shader.inputs['Roughness'].default_value=.58
    mesh.materials.append(material);obj=bpy.data.objects.new(OWNED,mesh);bpy.data.collections['CLM_EXTERIOR'].objects.link(obj)
    obj['reference']=PHOTO;obj['sourceURL']=URL;obj['sourceDate']='PDF creation2025-10-08; photograph date unknown';obj['dimensionsEstimated']=True
    return {'alreadyApplied':False,'addedObjects':[OWNED],'archivedObjects':[],'changedObjects':[],
            'bankSpansEstimate':[list(r) for r in SPANS],'frontageOffsetEstimate':.84,'heightEstimate':.89,
            'sourcePhoto':PHOTO,'sourceURL':URL,'photoCaptureDate':'Unknown','officialPDFCreationDate':'2025-10-08',
            'supports':supports,'primitiveVolumes':volumes,'glassChanged':False,
            'scope':'Two continuous low guard banks at lower street window frontage; doors and colonnade route remain clear',
            'reviewScope':'Complete convex CLM street frontage plus close lower window/guard/column/side portal relationship; upper tree-obscured features not rebuilt',
            'groundWindowReview':'Retained existing window grid broadly matches the visible official frontage photo; finer casement detail and current sash state unverified',
            'cameraSuggestions':[{'label':'wholeExterior','position':[113,-196,16.5],'target':[114.48,-151.91,13.5],'lens':35},
                                 {'label':'lowerFrontage','position':[103.4,-166.2,3.7],'target':[105.7,-151.3,3.7],'lens':38}],
            'limitations':['The official photo verifies the frontage guard type and approximate span; exact height/profile and movable signage remain unverified.',
                           'No unseen basement excavation, unseen gate, current plant works or upper sculptural reconstruction inferred from the tree-obscured image.',
                           'Native support may be the flat ground datum where sidewalk coverage is absent; kerb grading is not a surveyed source.',
                           'Window dimensions, ground levels, seven bays, existing glass optics, carved portal forms and roof remain inherited estimates.']}
