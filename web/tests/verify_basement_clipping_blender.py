"""Exercise the actual exporter helper without executing a campus export."""
from pathlib import Path
import ast
import bpy
import bmesh
source=Path(__file__).resolve().parents[1]/'tools/export_scene.py'
function=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='clip_below_ground')
exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'))
for height in [-3,0,3]:
 bpy.ops.mesh.primitive_cube_add(size=2,location=(0,0,height))
 obj=bpy.context.object
 mesh=obj.data.copy();mesh.transform(obj.matrix_world)
 material=bpy.data.materials.new('Retained material');mesh.materials.append(material)
 mesh.uv_layers.new(name='SurfaceUV')
 clip_below_ground(mesh)
 assert all(v.co.z>=-1e-5 for v in mesh.vertices)
 assert len(mesh.polygons)==(0 if height==-3 else 5 if height==0 else 6)
 assert mesh.materials[0]==material
 assert mesh.uv_layers.get('SurfaceUV')
print('BASEMENT_CLIP_CHECK_PASSED: underground, crossing, above-ground; UV and materials retained')
