# coding: utf-8
import sys
import os

from . import pmx
import pmx.reader


class Material(object):
    __slots__=[
            'name',
            'english_name',
            'diffuse_color',
            'alpha',
            'specular_color',
            'specular_factor',
            'ambient_color',
            'flag',
            'edge_color',
            'edge_size',
            'texture_index',
            'sphere_texture_index',
            'sphere_mode',
            'toon_sharing_flag',
            'toon_texture_index',
            'comment',
            ]
    def __init__(self, name):
        self.name=name


class Vector2(object):
    __slots__=[
            'x', 'y',
            ]
    def __init__(self, x, y):
        self.x=x
        self.y=y


class Vector3(object):
    __slots__=[
            'x', 'y', 'z'
            ]
    def __init__(self, x, y, z):
        self.x=x
        self.y=y
        self.z=z


class Vertex(object):
    __slots__=[
            'pos',
            'normal',
            'uv',
            'skinning',
            ]
    def __init__(self, pos, uv, normal=None, skinning=None):
        self.pos=pos
        self.uv=uv
        self.normal=normal
        self.skinning=skinning


class Face(object):
    __slots__=['indices', 'material_index']
    def __init__(self, *indices):
        self.indices=indices
        self.material_index=0


class Mesh(object):
    __slots__=[
            'vertices', 'faces',
            ]
    def __init__(self):
        self.vertices=[]
        self.faces=[]


class GenericModel(object):
    __slots__=[
            'meshes',  'materials', 'textures',
            ]

    def __init__(self):
        self.meshes=[]
        self.materials=[]

    def load_pmx(self, src):
        mesh=Mesh()
        self.meshes.append(mesh)

        # vertices
        def parse_pmx_vertex(v):
            if isinstance(v.deform, pmx.Bdef1):
                skinning=[(v.deform.index0, 1.0)]
            elif isinstance(v.deform, pmx.Bdef2):
                skinning=[
                        (v.deform.index0, v.deform.weight0), 
                        (v.deform.index1, 1.0-v.deform.weight0)
                        ]
            else:
                raise 'unknown deform !'
            vertex=Vertex(
                    pos=Vector3(v.position.x, v.position.y, v.position.z),
                    uv=Vector2(v.uv.x, v.uv.y),
                    normal=Vector3(v.normal.x, v.normal.y, v.normal.z),
                    skinning=skinning)
            return vertex
        mesh.vertices=[parse_pmx_vertex(v) for v in src.vertices]

        # textures
        self.textures=src.textures[:]

        # materials
        def parse_pmx_material(m):
            material=Material(m.name)
            material.english_name=m.english_name
            material.diffuse_color=m.diffuse_color
            material.alpha=m.alpha
            material.specular_color=m.specular_color
            material.specular_factor=m.specular_factor
            material.ambient_color=m.ambient_color
            material.flag=m.flag
            material.edge_color=m.edge_color
            material.edge_size=m.edge_size
            material.texture_index=m.texture_index
            material.sphere_texture_index=m.sphere_texture_index
            material.sphere_mode=m.sphere_mode
            material.toon_sharing_flag=m.toon_sharing_flag
            material.toon_texture_index=m.toon_texture_index
            material.comment=m.comment
            return material
        self.materials=[parse_pmx_material(m) for m in src.materials]

        # faces
        def it():
            for i in src.indices:
                yield i
        for i, m in enumerate(src.materials):
            for _ in range(0, m.vertex_count, 3):
                face=Face(it(), it(), it())
                face.material_index=i
                mesh.faces.append(face)
            
    @staticmethod
    def read_from_file(filepath):
        if not os.path.exists(filepath):
            return

        stem, ext=os.path.splitext(filepath)
        ext=ext.lower()

        model=GenericModel()
        if ext==".pmd":
            from . import pmd
            import pmd.reader
            m=pmd.reader.read_from_file(filepath)

        elif ext==".pmx":
            m=pmx.reader.read_from_file(filepath)
            if not m:
                return
            model.load_pmx(m)

        elif ext==".mqo":
            from . import mqo
            import mqo.reader
            m=mqo.reader.read_from_file(filepath)

        else:
            print('unknown file type: '+ext)
            return

        return model

