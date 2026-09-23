"""Shared metric facade primitives for the local Blender study builders."""
import math
import bpy
from mathutils import Matrix, Vector

materials = {}

class Geometry:
    """One mesh per material/component family, with metric face coordinates."""
    def __init__(self, code, name, material):
        self.name = code + '_D5_' + name
        self.collection = bpy.data.collections[code + '_EXTERIOR']
        self.material = materials[material]
        self.vertices, self.faces, self.uvs = [], [], []
        self.parts = 0

    def add(self, vertices, faces):
        start = len(self.vertices)
        self.vertices.extend(vertices)
        for face in faces:
            self.faces.append(tuple(start + i for i in face))
            points = [Vector(vertices[i]) for i in face]
            origin = points[0]
            u = (points[1] - origin).normalized()
            normal = (points[1] - origin).cross(points[-1] - origin).normalized()
            v = normal.cross(u)
            self.uvs.append([((p-origin).dot(u), (p-origin).dot(v)) for p in points])
        self.parts += 1

    def box(self, location, dimensions, angle=0):
        c, s = math.cos(angle), math.sin(angle)
        vertices = []
        for x, y, z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]:
            x, y = x * dimensions[0] / 2, y * dimensions[1] / 2
            vertices.append((location[0]+c*x-s*y, location[1]+s*x+c*y, location[2]+z*dimensions[2]/2))
        self.add(vertices, [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])

    def finish(self):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        layer = mesh.uv_layers.new(name='SurfaceUV')
        for poly, coords in zip(mesh.polygons, self.uvs):
            for index, uv in zip(poly.loop_indices, coords):
                layer.data[index].uv = uv
        mesh.materials.append(self.material)
        obj = bpy.data.objects.new(self.name, mesh)
        self.collection.objects.link(obj)
        obj['component_count'] = self.parts
        obj['scope'] = 'Photographed street character; dimensions and unseen elevations estimated'
        if not any(k in self.name for k in ['glass', 'roof', 'brick']):
            bevel = obj.modifiers.new('Small construction edges', 'BEVEL')
            bevel.width = .012
            bevel.segments = 2
        return obj

class Facade:
    def __init__(self, profile, wall, groups):
        self.profile, self.wall, self.groups = profile, wall, groups
        self.length = wall['length']
        self.u = Vector(((wall['q'][0]-wall['p'][0])/self.length, (wall['q'][1]-wall['p'][1])/self.length))
        self.n = Vector(wall['outward'])
        self.angle = math.atan2(self.u.y, self.u.x)

    def point(self, x, z, depth=0):
        p = self.wall['p']
        return (p[0]+self.u.x*x+self.n.x*depth, p[1]+self.u.y*x+self.n.y*depth, z)

    def group(self, name, material):
        key = name + '_' + material
        if key not in self.groups:
            self.groups[key] = Geometry(self.profile['code'], key, material)
        return self.groups[key]

    def box(self, name, material, x, z, width, height, depth=.25, offset=-.12):
        if width > .001 and height > .001:
            self.group(name, material).box(self.point(x,z,offset), (width,depth,height), self.angle)

    def arch(self, name, material, x, spring, radius, thickness, depth=.3):
        group = self.group(name, material)
        for i in range(24):
            a, b = i*math.pi/24, (i+1)*math.pi/24
            vertices = [self.point(x+r*math.cos(t), spring+r*math.sin(t), d)
                        for d in [-.04,depth] for r,t in [(radius,a),(radius,b),(radius+thickness,b),(radius+thickness,a)]]
            group.add(vertices, [(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)])

    def label(self, body, x, z, size, material='frame', depth=.26):
        curve = bpy.data.curves.new(self.profile['code']+'_D5_sign', 'FONT')
        curve.body, curve.align_x, curve.size, curve.extrude = body, 'CENTER', size, .001
        curve.materials.append(materials[material])
        obj = bpy.data.objects.new(curve.name, curve)
        bpy.data.collections[self.profile['code']+'_EXTERIOR'].objects.link(obj)
        obj.location = self.point(x,z,depth)
        # Text's local right direction must point right when viewed from the street.
        right = Vector((-self.n.y,self.n.x,0))
        obj.rotation_euler = Matrix((right,Vector((0,0,1)),Vector((*self.n,0)))).transposed().to_euler()

