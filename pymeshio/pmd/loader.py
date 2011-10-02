#coding: utf-8
import io
import pymeshio.common
import pymeshio.pmd


class Loader(pymeshio.common.BinaryLoader):
    """pmx loader
    """
    def __init__(self, ios, version):
        super(Loader, self).__init__(ios)
        self.version=version

    def read_text(self, size):
        """read cp932 text
        """
        src=self.unpack("%ds" % size, size)
        assert(type(src)==bytes)
        pos = src.find(b"\x00")
        if pos==-1:
            return src
        else:
            return src[:pos]

    def read_vertex(self):
        return pymeshio.pmd.Vertex(
                self.read_vector3(),
                self.read_vector3(),
                self.read_vector2(),
                self.read_uint(2),
                self.read_uint(2),
                self.read_uint(1),
                self.read_uint(1))

    def read_material(self):
        return pymeshio.pmd.Material(
                diffuse_color=self.read_rgb(),
                alpha=self.read_float(),
                specular_factor=self.read_float(),
                specular_color=self.read_rgb(),
                ambient_color=self.read_rgb(),
                toon_index=self.read_uint(1),
                edge_flag=self.read_uint(1),
                vertex_count=self.read_uint(4),
                texture_file=self.read_text(20)
                )

    def read_bone(self):
        name=self.read_text(20)
        parent_index=self.read_uint(2)
        tail_index=self.read_uint(2)
        bone=pymeshio.pmd.createBone(name, self.read_uint(1))
        bone.parent_index=parent_index
        bone.tail_index=tail_index
        bone.ik_index = self.read_uint(2)
        bone.pos = self.read_vector3()
        return bone

    def read_ik(self):
        ik=pymeshio.pmd.IK(self.read_uint(2), self.read_uint(2))
        ik.length = self.read_uint(1)
        ik.iterations = self.read_uint(2)
        ik.weight = self.read_float()
        ik.children=[self.read_uint(2) for _ in range(ik.length)]
        return ik

    def read_morph(self):
        morph=pymeshio.pmd.Morph(self.read_text(20))
        morph_size = self.read_uint(4)
        morph.type = self.read_uint(1)
        for j in range(morph_size):
            morph.indices.append(self.read_uint(4))
            morph.pos_list.append(self.read_vector3())
        return morph

    def read_rigidbody(self):
        return pymeshio.pmd.RigidBody(
                name=self.read_text(20), 
                bone_index=self.read_uint(2),
                collision_group=self.read_uint(1),
                no_collision_group=self.read_uint(2),
                shape_type=self.read_uint(1),
                shape_size=self.read_vector3(),
                shape_position=self.read_vector3(),
                shape_rotation=self.read_vector3(),
                mass=self.read_float(),
                linear_damping=self.read_float(),
                angular_damping=self.read_float(),
                restitution=self.read_float(),
                friction=self.read_float(),
                mode=self.read_uint(1)
                )

    def read_joint(self):
        return pymeshio.pmd.Joint(
                name=self.read_text(20),
                rigidbody_index_a=self.read_uint(4),
                rigidbody_index_b=self.read_uint(4),
                position=self.read_vector3(),
                rotation=self.read_vector3(),
                translation_limit_min=self.read_vector3(),
                translation_limit_max=self.read_vector3(),
                rotation_limit_min=self.read_vector3(),
                rotation_limit_max=self.read_vector3(),
                spring_constant_translation=self.read_vector3(),
                spring_constant_rotation=self.read_vector3())



def __load(loader, model):
    # model info
    model.name=loader.read_text(20)
    model.comment=loader.read_text(256) 

    # model data
    model.vertices=[loader.read_vertex()
            for _ in range(loader.read_uint(4))]
    model.indices=[loader.read_uint(2)
            for _ in range(loader.read_uint(4))]
    model.materials=[loader.read_material()
            for _ in range(loader.read_uint(4))]
    model.bones=[loader.read_bone()
            for _ in range(loader.read_uint(2))]
    model.ik_list=[loader.read_ik()
            for _ in range(loader.read_uint(2))]
    model.morphs=[loader.read_morph()
            for _ in range(loader.read_uint(2))]
    model.morph_indices=[loader.read_uint(2)
            for _ in range(loader.read_uint(1))]
    model.bone_group_list=[loader.read_text(50)
            for _ in range(loader.read_uint(1))]
    model.bone_display_list=[(loader.read_uint(2), loader.read_uint(1))
            for _i in range(loader.read_uint(4))]

    if loader.is_end():
        # EOF
        return True

    ############################################################
    # extend1: english name
    ############################################################
    if loader.read_uint(1)==0:
        print("no extend flag")
        return True
    model.english_name=loader.read_text(20)
    model.english_comment=loader.read_text(256)
    for bone in model.bones:
        bone.english_name=loader.read_text(20)
    for morph in model.morphs:
        if morph.name==b'base':
            continue
        morph.english_name=loader.read_text(20)
    model.bone_group_english_list=[loader.read_text(50)
            for _ in model.bone_group_list]

    ############################################################
    # extend2: toon_textures
    ############################################################
    if loader.is_end():
        # EOF
        return True
    model.toon_textures=[loader.read_text(100)
            for _ in range(10)]

    ############################################################
    # extend2: rigidbodies and joints
    ############################################################
    if loader.is_end():
        # EOF
        return True
    model.rigidbodies=[loader.read_rigidbody()
            for _ in range(loader.read_uint(4))]
    model.joints=[loader.read_joint()
            for _ in range(loader.read_uint(4))]

    return True


def load_from_file(path):
    return load(io.BytesIO(pymeshio.common.readall(path)))


def load(ios):
    assert(isinstance(ios, io.IOBase))
    loader=pymeshio.common.BinaryLoader(ios)

    # header
    signature=loader.unpack("3s", 3)
    if signature!=b"Pmd":
        raise pymeshio.common.ParseException(
                "invalid signature: {0}".format(signature))
    version=loader.read_float()

    model=pymeshio.pmd.Model(version)
    loader=Loader(loader.ios, version)
    if(__load(loader, model)):
        # check eof
        if not loader.is_end():
            #print("can not reach eof.")
            pass

        # build bone tree
        for i, child in enumerate(model.bones):
            if child.parent_index==0xFFFF:
                # no parent
                model.no_parent_bones.append(child)
                child.parent=None
            else:
                # has parent
                parent=model.bones[child.parent_index]
                child.parent=parent
                parent.children.append(child)
            # 後位置
            if child.hasChild():
                child.tail=model.bones[child.tail_index].pos

        return model



