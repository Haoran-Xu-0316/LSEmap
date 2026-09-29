"""Render before/after G-layer cutaways without modifying either source model."""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage38'
for label, source in [('before', ROOT/'result/blender/LSE_campus_detailed_v37.blend'),
                      ('after', OUT/'registered-atrium-candidate.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(source))
    original = bpy.data.collections['LRB_PUBLIC_INTERIOR_study']
    scene = bpy.data.scenes.new('Ground_zone_review')
    bpy.context.window.scene = scene
    for obj in original.all_objects:
        if obj.type != 'MESH':
            continue
        coords = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        faces = [face for face in obj.data.polygons if all(-.02 <= coords[i].z < 3.9 for i in face.vertices)]
        if not faces:
            continue
        mesh = bpy.data.meshes.new(obj.name+'_review')
        mesh.from_pydata(coords, [], [tuple(face.vertices) for face in faces])
        for material in obj.data.materials:
            mesh.materials.append(material)
        for face, source_face in zip(mesh.polygons, faces):
            face.material_index = source_face.material_index
        copy = bpy.data.objects.new(obj.name+'_review', mesh)
        scene.collection.objects.link(copy)
    camera = bpy.data.objects.new('Review_camera', bpy.data.cameras.new('Review_camera'))
    scene.collection.objects.link(camera)
    camera.location = (72, 8, 110)
    camera.rotation_euler = (Vector((72,8,.32))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 110
    scene.camera = camera
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'BOTH'
    scene.display.shading.background_type = 'WORLD'
    scene.world = bpy.data.worlds.new('Review_world')
    scene.world.color = (.8,.8,.8)
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(OUT/f'registration-{label}.png')
    bpy.ops.render.render(write_still=True)
