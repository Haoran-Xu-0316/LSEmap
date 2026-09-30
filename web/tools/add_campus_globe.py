"""Add the inverted LSE globe to the preserved edition44 Blender campus."""
from pathlib import Path
import math
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage45'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v44.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
collection = bpy.data.collections['03_PUBLIC_REALM']
position = (-48.9262, -20.3711, 2.040)
bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=2, location=position)
globe = bpy.context.object
globe.name = 'SITE_V45_The_World_Turned_Upside_Down'
for owner in list(globe.users_collection):
    owner.objects.unlink(globe)
collection.objects.link(globe)
globe.rotation_euler = (math.pi, 0, math.radians(110))
for face in globe.data.polygons:
    face.use_smooth = True
material = bpy.data.materials.new('SITE_V45_globe_cartography')
material.use_nodes = True
material.diffuse_color = (.60,.76,.83,1)
material['globeMap'] = True
shader = material.node_tree.nodes['Principled BSDF']
shader.inputs['Roughness'].default_value = .38
shader.inputs['Metallic'].default_value = 0
texture = material.node_tree.nodes.new('ShaderNodeTexImage')
texture.image = bpy.data.images.load(str(OUT/'globe-map.png'))
texture.image.pack()
material.node_tree.links.new(texture.outputs['Color'], shader.inputs['Base Color'])
globe.data.materials.append(material)
globe['artwork'] = 'The World Turned Upside Down, Mark Wallinger, 2019'
globe['diameterMetres'] = 4
globe['scope'] = 'Approximate OSM position; estimated heading and reconstructed map palette'
for layer in bpy.context.scene.view_layers:
    layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v45.blend'))
(OUT/'globe-audit.json').write_text(json.dumps({'version':45,'baseline':44,'addedObject':globe.name,'position':position,'diameterMetres':4,'northPoleAtGround':True,'mapPacked':True,'source':'https://www.lse.ac.uk/news/latest-news-from-lse/03-mar-19/lse-unveils-new-sculpture-by-mark-wallinger','limitations':['Placement from OSM is approximate','Heading, colours and lettering estimated']},indent=2)+'\n')
print('GLOBE_SAVED')
