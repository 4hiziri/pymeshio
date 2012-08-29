# coding: utf-8
import sys
import os

from . import pmx
from .pmx import reader as pmx_reader
pmx.reader=pmx_reader


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
    def __init__(self):
        self.indices=[]
        self.material_index=0


def convert_coord(xyz):
    """
    Left handed y-up to Right handed z-up
    """
    # swap y and z
    tmp=xyz.y
    xyz.y=xyz.z
    xyz.z=tmp
    return xyz


class Mesh(object):
    __slots__=[
            'vertices', 'faces',
            ]
    def __init__(self):
        self.vertices=[]
        self.faces=[]

    def convert_coord(self):
        for v in self.vertices:
            v.pos=convert_coord(v.pos)
            v.normal=convert_coord(v.normal)


class GenericModel(object):
    __slots__=[
            'filepath',
            'name', 'english_name',
            'comment', 'english_comment',
            'meshes', 'materials', 'textures',
            'bones',
            ]

    def __init__(self):
        self.filepath=None
        self.name=None
        self.english_name=None
        self.comment=None
        self.english_comment=None
        self.meshes=[]
        self.materials=[]


    def convert_coord(self):
        for b in self.bones:
            b.position=convert_coord(b.position)
            b.tail_position=convert_coord(b.tail_position)

        for m in self.meshes:
            m.convert_coord()


    def load_pmx(self, src):
        mesh=Mesh()
        self.meshes.append(mesh)

        self.filepath=src.path
        self.name=src.name
        self.english_name=src.english_name
        self.comment=src.english_name
        self.english_comment=src.english_comment

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
                    pos=v.position.clone(),
                    uv=v.uv.clone(),
                    normal=v.normal.clone(),
                    skinning=skinning)
            return vertex
        mesh.vertices=[parse_pmx_vertex(v) for v in src.vertices]

        # textures
        self.textures=src.textures[:]

        # materials
        def parse_pmx_material(m):
            material=Material(m.name)
            material.english_name=m.english_name
            material.diffuse_color=m.diffuse_color.clone()
            material.alpha=m.alpha
            material.specular_color=m.specular_color.clone()
            material.specular_factor=m.specular_factor
            material.ambient_color=m.ambient_color.clone()
            material.flag=m.flag
            material.edge_color=m.edge_color.clone()
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
        def indices():
            for i in src.indices:
                yield i
        it=indices()
        for i, m in enumerate(src.materials):
            for _ in range(0, m.vertex_count, 3):
                face=Face()
                face.indices=[next(it), next(it), next(it)]
                face.material_index=i
                mesh.faces.append(face)

        # bones
        self.bones=src.bones[:]

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
            # left handed Y-up to right handed Z-up
            model.convert_coord()

        elif ext==".mqo":
            from . import mqo
            import mqo.reader
            m=mqo.reader.read_from_file(filepath)

        else:
            print('unknown file type: '+ext)
            return

        return model

