#!BPY
# coding:utf-8
"""
 Name: 'MikuMikuDance model (.pmd)...'
 Blender: 248
 Group: 'Import'
 Tooltip: 'Import PMD file for MikuMikuDance.'
"""
__author__= ["ousttrue"]
__version__= "2.2"
__url__=()
__bpydoc__="""
pmd Importer

This script imports a pmd into Blender for editing.

0.1 20091126: first implement.
0.2 20091209: implement IK.
0.3 20091210: implement morph target.
0.4 20100305: use english name.
0.5 20100408: cleanup not used vertices.
0.6 20100416: fix fornt face. texture load fail safe. add progress.
0.7 20100506: C extension.
0.8 20100521: add shape_key group.
1.0 20100530: add invisilbe bone tail(armature layer 2).
1.1 20100608: integrate 2.4 and 2.5.
1.2 20100616: implement rigid body.
1.3 20100619: fix for various models.
1.4 20100623: fix constraint name.
1.5 20100626: refactoring.
1.6 20100629: sphere map.
1.7 20100703: implement bone group.
1.8 20100710: implement toon texture.
1.9 20100718: keep model name, comment.
2.0 20100724: update for Blender2.53.
2.1 20100731: add full python module.
2.2 20101005: update for Blender2.54.
2.3 20101228: update for Blender2.55.
"""
bl_addon_info = {
        'category': 'Import/Export',
        'name': 'Import: MikuMikuDance Model Format (.pmd)',
        'author': 'ousttrue',
        'version': (2, 2),
        'blender': (2, 5, 3),
        'location': 'File > Import',
        'description': 'Import from the MikuMikuDance Model Format (.pmd)',
        'warning': '', # used for warning icon and text in addons panel
        'wiki_url': 'http://sourceforge.jp/projects/meshio/wiki/FrontPage',
        'tracker_url': 'http://sourceforge.jp/ticket/newticket.php?group_id=5081',
        }

MMD_SHAPE_GROUP_NAME='_MMD_SHAPE'
MMD_MB_NAME='mb_name'
MMD_MB_COMMENT='mb_comment'
MMD_COMMENT='comment'
BASE_SHAPE_NAME='Basis'
RIGID_NAME='rigid_name'
RIGID_SHAPE_TYPE='rigid_shape_type'
RIGID_PROCESS_TYPE='rigid_process_type'
RIGID_BONE_NAME='rigid_bone_name'
#RIGID_LOCATION='rigid_loation'
RIGID_GROUP='ribid_group'
RIGID_INTERSECTION_GROUP='rigid_intersection_group'
RIGID_WEIGHT='rigid_weight'
RIGID_LINEAR_DAMPING='rigid_linear_damping'
RIGID_ANGULAR_DAMPING='rigid_angular_damping'
RIGID_RESTITUTION='rigid_restitution'
RIGID_FRICTION='rigid_friction'
CONSTRAINT_NAME='constraint_name'
CONSTRAINT_A='const_a'
CONSTRAINT_B='const_b'
CONSTRAINT_POS_MIN='const_pos_min'
CONSTRAINT_POS_MAX='const_pos_max'
CONSTRAINT_ROT_MIN='const_rot_min'
CONSTRAINT_ROT_MAX='const_rot_max'
CONSTRAINT_SPRING_POS='const_spring_pos'
CONSTRAINT_SPRING_ROT='const_spring_rot'
TOON_TEXTURE_OBJECT='ToonTextures'


###############################################################################
# import
###############################################################################
import os
import sys
import math

try:
    # C extension
    from meshio import pmd, englishmap
    print('use meshio C module')
except ImportError:
    # full python
    from .pymeshio import englishmap
    from .pymeshio import mmd as pmd
    pmd.IO=pmd.PMDLoader

# for 2.5
import bpy
import mathutils

# wrapper
from . import bl25 as bl

xrange=range

def createPmdMaterial(m, index):
    material = bpy.data.materials.new("Material")
    # diffuse
    material.diffuse_shader='FRESNEL'
    material.diffuse_color=([m.diffuse.r, m.diffuse.g, m.diffuse.b])
    material.alpha=m.diffuse.a
    # specular
    material.specular_shader='TOON'
    material.specular_color=([m.specular.r, m.specular.g, m.specular.b])
    material.specular_toon_size=int(m.shinness)
    # ambient
    material.mirror_color=([m.ambient.r, m.ambient.g, m.ambient.b])
    # flag
    material.subsurface_scattering.use=True if m.flag==1 else False
    # other
    material.name="m_%02d" % index
    material.preview_render_type='FLAT'
    material.use_transparency=True
    return material

def poseBoneLimit(n, b):
    if n.endswith("_t"):
        return
    if n.startswith("knee_"):
        b.lock_ik_y=True
        b.lock_ik_z=True
        b.lock_ik_x=False
        # IK limit
        b.use_ik_limit_x=True
        b.ik_min_x=0
        b.ik_max_x=180
    elif n.startswith("ankle_"):
        #b.ik_dof_y=False
        pass

def setSphereMap(material, index, blend_type='MULTIPLY'):
    slot=material.texture_slots[index]
    slot.texture_coords='NORMAL'
    slot.mapping='SPHERE'
    slot.blend_type=blend_type


###############################################################################
def VtoV(v):
    return bl.createVector(v.x, v.y, v.z)


def convert_coord(pos):
    """
    Left handed y-up to Right handed z-up
    """
    return (pos.x, pos.z, pos.y)


def to_radian(degree):
    return math.pi * degree / 180


def get_bone_name(l, index):
    if index==0xFFFF:
        return l.bones[0].getName()

    if index < len(l.bones):
        name=englishmap.getEnglishBoneName(l.bones[index].getName())
        if name:
            return name
        return l.bones[index].getName()
    print('invalid bone index', index)
    return l.bones[0].getName()


def get_group_name(g):
    group_name=englishmap.getEnglishBoneGroupName(g.getName().strip())
    if not group_name:
        group_name=g.getName().strip()
    return group_name


def __importToonTextures(io, tex_dir):
    mesh, meshObject=bl.mesh.create(TOON_TEXTURE_OBJECT)
    material=bl.material.create(TOON_TEXTURE_OBJECT)
    bl.mesh.addMaterial(mesh, material)
    for i in range(10):
        t=io.getToonTexture(i)
        path=os.path.join(tex_dir, t.getName())
        texture, image=bl.texture.create(path)
        bl.material.addTexture(material, texture, False)
    return meshObject, material


def __importShape(obj, l, vertex_map):
    if len(l.morph_list)==0:
        return

    # set shape_key pin
    bl.object.pinShape(obj, True)

    # find base
    base=None
    for s in l.morph_list:
        if s.type==0:
            base=s

            # create vertex group
            bl.object.addVertexGroup(obj, MMD_SHAPE_GROUP_NAME)
            hasShape=False
            for i in s.indices:
                if i in vertex_map:
                    hasShape=True
                    bl.object.assignVertexGroup(
                            obj, MMD_SHAPE_GROUP_NAME, vertex_map[i], 0)
            if not hasShape:
                return
    assert(base)

    # create base key
    baseShapeBlock=bl.object.addShapeKey(obj, BASE_SHAPE_NAME)
    # mesh
    mesh=bl.object.getData(obj)
    mesh.update()

    # each skin
    for s in l.morph_list:
        if s.type==0:
            continue

        # name
        name=englishmap.getEnglishSkinName(s.getName())
        if not name:
            name=s.getName()

        # 25
        new_shape_key=bl.object.addShapeKey(obj, name)

        for index, offset in zip(s.indices, s.pos_list):
            try:
                vertex_index=vertex_map[base.indices[index]]
                bl.shapekey.assign(new_shape_key, vertex_index,
                        mesh.vertices[vertex_index].co+
                        bl.createVector(*convert_coord(offset)))
            except IndexError as msg:
                print(msg)
                print(index, len(base.indices), len(vertex_map))
                print(len(mesh.vertices))
                print(base.indices[index])
                print(vertex_index)
                break
            except KeyError:
                #print 'this mesh not has shape vertices'
                break

    # select base shape
    bl.object.setActivateShapeKey(obj, 0)


def __build(armature, b, p, parent):
    name=englishmap.getEnglishBoneName(b.getName())
    if not name:
        name=b.getName()

    bone=bl.armature.createBone(armature, name)

    if parent and (b.tail_index==0 or b.type==6 or b.type==7 or b.type==9):
        # 先端ボーン
        bone.head = bl.createVector(*convert_coord(b.pos))
        bone.tail=bone.head+bl.createVector(0, 1, 0)
        bone.parent=parent
        if bone.name=="center_t":
            # センターボーンは(0, 1, 0)の方向を向いていないと具合が悪い
            parent.tail=parent.head+bl.createVector(0, 1, 0)
            bone.head=parent.tail
            bone.tail=bone.head+bl.createVector(0, 1, 0)
        else:
            if parent.tail==bone.head:
                pass
            else:
                print('diffurence with parent.tail and head', name)

        if b.type!=9:
            bl.bone.setConnected(bone)
        # armature layer 2
        bl.bone.setLayerMask(bone, [0, 1])
    else:
        # 通常ボーン
        bone.head = bl.createVector(*convert_coord(b.pos))
        bone.tail = bl.createVector(*convert_coord(b.tail))
        if parent:
            bone.parent=parent
            if parent.tail==bone.head:
                bl.bone.setConnected(bone)

    if bone.head==bone.tail:
        bone.tail=bone.head+bl.createVector(0, 1, 0)

    for c in b.children:
        __build(armature, c, b, bone)


def __importArmature(l):
    armature, armature_object=bl.armature.create()

    # build bone
    bl.armature.makeEditable(armature_object)
    for b in l.bones:
        if not b.parent:
            __build(armature, b, None, None)
    bl.armature.update(armature)
    bl.enterObjectMode()

    # IK constraint
    pose = bl.object.getPose(armature_object)
    for ik in l.ik_list:
        target=l.bones[ik.target]
        name = englishmap.getEnglishBoneName(target.getName())
        if not name:
            name=target.getName()
        p_bone = pose.bones[name]
        if not p_bone:
            print('not found', name)
            continue
        if len(ik.children) >= 16:
            print('over MAX_CHAINLEN', ik, len(ik.children))
            continue
        effector_name=englishmap.getEnglishBoneName(
                l.bones[ik.index].getName())
        if not effector_name:
            effector_name=l.bones[ik.index].getName()

        constraint=bl.armature.createIkConstraint(armature_object,
                p_bone, effector_name, ik)

    bl.armature.makeEditable(armature_object)
    bl.armature.update(armature)
    bl.enterObjectMode()

    # create bone group
    for i, g in enumerate(l.bone_group_list):
        name=get_group_name(g)
        bl.object.createBoneGroup(armature_object, name, "THEME%02d" % (i+1))

    # assign bone to group
    for b_index, g_index in l.bone_display_list:
        # bone
        b=l.bones[b_index]
        bone_name=englishmap.getEnglishBoneName(b.getName())
        if not bone_name:
            bone_name=b.getName()
        # group
        g=l.bone_group_list[g_index-1]
        group_name=get_group_name(g)

        # assign
        pose.bones[bone_name].bone_group=pose.bone_groups[group_name]

    bl.enterObjectMode()

    return armature_object


def __import16MaerialAndMesh(meshObject, l,
        material_order, face_map, tex_dir, toon_material):

    mesh=bl.object.getData(meshObject)
    ############################################################
    # material
    ############################################################
    bl.progress_print('create materials')
    mesh_material_map={}
    textureMap={}
    imageMap={}
    index=0

    for material_index in material_order:
        try:
            m=l.materials[material_index]
            mesh_material_map[material_index]=index
        except KeyError:
            break

        material=createPmdMaterial(m, material_index)

        # main texture
        texture_name=m.getTexture()
        if texture_name!='':
            for i, t in enumerate(texture_name.split('*')):
                if t in textureMap:
                    texture=textureMap[t]
                else:
                    path=os.path.join(tex_dir, t)
                    texture, image=bl.texture.create(path)
                    textureMap[texture_name]=texture
                    imageMap[material_index]=image
                texture_index=bl.material.addTexture(material, texture)
                if t.endswith('sph'):
                    # sphere map
                    setSphereMap(material, texture_index)
                elif t.endswith('spa'):
                    # sphere map
                    setSphereMap(material, texture_index, 'ADD')

        # toon texture
        toon_index=bl.material.addTexture(
                material,
                bl.material.getTexture(
                    toon_material,
                    0 if m.toon_index==0xFF else m.toon_index
                    ),
                False)

        bl.mesh.addMaterial(mesh, material)

        index+=1

    ############################################################
    # vertex
    ############################################################
    bl.progress_print('create vertices')
    # create vertices
    vertices=[]
    for v in l.each_vertex():
        vertices.append(convert_coord(v.pos))

    ############################################################
    # face
    ############################################################
    bl.progress_print('create faces')
    # create faces
    mesh_face_indices=[]
    mesh_face_materials=[]
    used_vertices=set()

    for material_index in material_order:
        face_offset=face_map[material_index]
        m=l.materials[material_index]
        material_faces=l.indices[face_offset:face_offset+m.vertex_count]

        def degenerate(i0, i1, i2):
            """
            縮退しているか？
            """
            return i0==i1 or i1==i2 or i2==i0

        for j in xrange(0, len(material_faces), 3):
            i0=material_faces[j]
            i1=material_faces[j+1]
            i2=material_faces[j+2]
            # flip
            triangle=[i2, i1, i0]
            if degenerate(*triangle):
                continue
            mesh_face_indices.append(triangle[0:3])
            mesh_face_materials.append(material_index)
            used_vertices.add(i0)
            used_vertices.add(i1)
            used_vertices.add(i2)

    ############################################################
    # create vertices & faces
    ############################################################
    bl.mesh.addGeometry(mesh, vertices, mesh_face_indices)

    ############################################################
    # vertex bone weight
    ############################################################
    # create vertex group
    vertex_groups={}
    for v in l.each_vertex():
        vertex_groups[v.bone0]=True
        vertex_groups[v.bone1]=True
    for i in vertex_groups.keys():
        bl.object.addVertexGroup(meshObject, get_bone_name(l, i))

    # vertex params
    bl.mesh.useVertexUV(mesh)
    for i, v, mvert in zip(xrange(len(l.vertices)),
        l.each_vertex(), mesh.vertices):
        # normal, uv
        bl.vertex.setNormal(mvert, convert_coord(v.normal))
        # bone weight
        w1=float(v.weight0)/100.0
        w2=1.0-w1
        bl.object.assignVertexGroup(meshObject, get_bone_name(l, v.bone0),
            i,  w1)
        bl.object.assignVertexGroup(meshObject, get_bone_name(l, v.bone1),
            i,  w2)

    ############################################################
    # face params
    ############################################################
    used_map={}
    bl.mesh.addUV(mesh)
    for i, (face, material_index) in enumerate(
            zip(mesh.faces, mesh_face_materials)):
        try:
            index=mesh_material_map[material_index]
        except KeyError as message:
            print(message, mesh_material_map, m)
            assert(False)
        bl.face.setMaterial(face, index)
        material=mesh.materials[index]
        used_map[index]=True
        if bl.material.hasTexture(material):
            uv_array=[l.getUV(i) for i in bl.face.getIndices(face)]
            bl.mesh.setFaceUV(mesh, i, face,
                    # fix uv
                    [(uv.x, 1.0-uv.y) for uv in uv_array],
                    imageMap.get(index, None))

        # set smooth
        bl.face.setSmooth(face, True)

    mesh.update()

    ############################################################
    # clean up not used vertices
    ############################################################
    bl.progress_print('clean up vertices not used')
    remove_vertices=[]
    vertex_map={}
    for i, v in enumerate(l.each_vertex()):
        if i in used_vertices:
            vertex_map[i]=len(vertex_map)
        else:
            remove_vertices.append(i)

    bl.mesh.vertsDelete(mesh, remove_vertices)

    bl.progress_print('%s created' % mesh.name)
    return vertex_map


def __importMaterialAndMesh(io, tex_dir, toon_material):
    """
    @param l[in] mmd.PMDLoader
    @param filename[in]
    """
    ############################################################
    # shpaeキーで使われるマテリアル優先的に前に並べる
    ############################################################
    # shapeキーで使われる頂点インデックスを集める
    shape_key_used_vertices=set()
    if len(io.morph_list)>0:
        # base
        base=None
        for s in io.morph_list:
            if s.type!=0:
                continue
            base=s
            break
        assert(base)

        for index in base.indices:
            shape_key_used_vertices.add(index)

    # マテリアルに含まれる頂点がshape_keyに含まれるか否か？
    def isMaterialUsedInShape(offset, m):
        for i in xrange(offset, offset+m.vertex_count):
            if io.indices[i] in shape_key_used_vertices:
                return True

    material_with_shape=set()

    # 各マテリアルの開始頂点インデックスを記録する
    face_map={}
    face_count=0
    for i, m in enumerate(io.materials):
        face_map[i]=face_count
        if isMaterialUsedInShape(face_count, m):
            material_with_shape.add(i)
        face_count+=m.vertex_count

    # shapeキーで使われる頂点のあるマテリアル
    material_with_shape=list(material_with_shape)
    material_with_shape.sort()

    # shapeキーに使われていないマテリアル
    material_without_shape=[]
    for i in range(len(io.materials)):
        if not i in material_with_shape:
            material_without_shape.append(i)

    # メッシュの生成
    def __splitList(l, length):
        for i in range(0, len(l), length):
            yield l[i:i+length]

    def __importMeshAndShape(material16, name):
        mesh, meshObject=bl.mesh.create(name)

        # activate object
        bl.object.deselectAll()
        bl.object.activate(meshObject)

        # shapeキーで使われる順に並べなおしたマテリアル16個分の
        # メッシュを作成する
        vertex_map=__import16MaerialAndMesh(
                meshObject, io, material16, face_map, tex_dir, toon_material)

        # crete shape key
        __importShape(meshObject, io, vertex_map)

        mesh.update()
        return meshObject

    mesh_objects=[__importMeshAndShape(material16, 'with_shape')
        for material16 in __splitList(material_with_shape, 16)]

    mesh_objects+=[__importMeshAndShape(material16, 'mesh')
        for material16 in __splitList(material_without_shape, 16)]

    return mesh_objects


def __importConstraints(io):
    print("create constraint")
    container=bl.object.createEmpty('Constraints')
    layer=[
        True, False, False, False, False, False, False, False, False, False,
        False, False, False, False, False, False, False, False, False, False,
            ]
    material=bl.material.create('constraint')
    material.diffuse_color=(1, 0, 0)
    constraintMeshes=[]
    for i, c in enumerate(io.constraints):
        bpy.ops.mesh.primitive_uv_sphere_add(
                segments=8,
                rings=4,
                size=0.1,
                location=(c.pos.x, c.pos.z, c.pos.y),
                layer=layer
                )
        meshObject=bl.object.getActive()
        constraintMeshes.append(meshObject)
        mesh=bl.object.getData(meshObject)
        bl.mesh.addMaterial(mesh, material)
        meshObject.name='c_%d' % i
        #meshObject.draw_transparent=True
        #meshObject.draw_wire=True
        meshObject.max_draw_type='SOLID'
        rot=c.rot
        meshObject.rotation_euler=(-rot.x, -rot.z, -rot.y)

        meshObject[CONSTRAINT_NAME]=c.getName()
        meshObject[CONSTRAINT_A]=io.rigidbodies[c.rigidA].getName()
        meshObject[CONSTRAINT_B]=io.rigidbodies[c.rigidB].getName()
        meshObject[CONSTRAINT_POS_MIN]=VtoV(c.constraintPosMin)
        meshObject[CONSTRAINT_POS_MAX]=VtoV(c.constraintPosMax)
        meshObject[CONSTRAINT_ROT_MIN]=VtoV(c.constraintRotMin)
        meshObject[CONSTRAINT_ROT_MAX]=VtoV(c.constraintRotMax)
        meshObject[CONSTRAINT_SPRING_POS]=VtoV(c.springPos)
        meshObject[CONSTRAINT_SPRING_ROT]=VtoV(c.springRot)

    for meshObject in reversed(constraintMeshes):
        bl.object.makeParent(container, meshObject)

    return container


def __importRigidBodies(io):
    print("create rigid bodies")

    container=bl.object.createEmpty('RigidBodies')
    layer=[
        True, False, False, False, False, False, False, False, False, False,
        False, False, False, False, False, False, False, False, False, False,
            ]
    material=bl.material.create('rigidBody')
    rigidMeshes=[]
    for i, rigid in enumerate(io.rigidbodies):
        if rigid.boneIndex==0xFFFF:
            # no reference bone
            bone=io.bones[0]
        else:
            bone=io.bones[rigid.boneIndex]
        pos=bone.pos+rigid.position

        if rigid.shapeType==pmd.SHAPE_SPHERE:
            bpy.ops.mesh.primitive_ico_sphere_add(
                    location=(pos.x, pos.z, pos.y),
                    layer=layer
                    )
            bpy.ops.transform.resize(
                    value=(rigid.w, rigid.w, rigid.w))
        elif rigid.shapeType==pmd.SHAPE_BOX:
            bpy.ops.mesh.primitive_cube_add(
                    location=(pos.x, pos.z, pos.y),
                    layer=layer
                    )
            bpy.ops.transform.resize(
                    value=(rigid.w, rigid.d, rigid.h))
        elif rigid.shapeType==pmd.SHAPE_CAPSULE:
            bpy.ops.mesh.primitive_tube_add(
                    location=(pos.x, pos.z, pos.y),
                    layer=layer
                    )
            bpy.ops.transform.resize(
                    value=(rigid.w, rigid.w, rigid.h))
        else:
            assert(False)

        meshObject=bl.object.getActive()
        mesh=bl.object.getData(meshObject)
        rigidMeshes.append(meshObject)
        bl.mesh.addMaterial(mesh, material)
        meshObject.name='r_%d' % i
        meshObject[RIGID_NAME]=rigid.getName()
        #meshObject.draw_transparent=True
        #meshObject.draw_wire=True
        meshObject.max_draw_type='WIRE'
        rot=rigid.rotation
        meshObject.rotation_euler=(-rot.x, -rot.z, -rot.y)

        # custom properties
        meshObject[RIGID_SHAPE_TYPE]=rigid.shapeType
        meshObject[RIGID_PROCESS_TYPE]=rigid.processType

        bone_name = englishmap.getEnglishBoneName(bone.getName())
        if not bone_name:
            bone_name=bone.getName()
        meshObject[RIGID_BONE_NAME]=bone_name

        meshObject[RIGID_GROUP]=rigid.group
        meshObject[RIGID_INTERSECTION_GROUP]=rigid.target
        meshObject[RIGID_WEIGHT]=rigid.weight
        meshObject[RIGID_LINEAR_DAMPING]=rigid.linearDamping
        meshObject[RIGID_ANGULAR_DAMPING]=rigid.angularDamping
        meshObject[RIGID_RESTITUTION]=rigid.restitution
        meshObject[RIGID_FRICTION]=rigid.friction

    for meshObject in reversed(rigidMeshes):
        bl.object.makeParent(container, meshObject)

    return container


def _execute(filepath=""):
    """
    load pmd file to context.
    """

    # load pmd
    bl.progress_set('load %s' % filepath, 0.0)

    io=pmd.IO()
    if not io.read(filepath):
        bl.message("fail to load %s" % filepath)
        return
    bl.progress_set('loaded', 0.1)

    # create root object
    model_name=io.getEnglishName()
    if len(model_name)==0:
        model_name=io.getName()
    root=bl.object.createEmpty(model_name)
    root[MMD_MB_NAME]=io.getName()
    root[MMD_MB_COMMENT]=io.getComment()
    root[MMD_COMMENT]=io.getEnglishComment()

    # toon textures
    tex_dir=os.path.dirname(filepath)
    toonTextures, toonMaterial=__importToonTextures(io, tex_dir)
    bl.object.makeParent(root, toonTextures)

    # import mesh
    mesh_objects=__importMaterialAndMesh(io, tex_dir, toonMaterial)
    for o in mesh_objects:
        bl.object.makeParent(root, o)

    # import armature
    armature_object=__importArmature(io)
    if armature_object:
        bl.object.makeParent(root, armature_object)
        armature = bl.object.getData(armature_object)

        # add armature modifier
        for o in mesh_objects:
            bl.modifier.addArmature(o, armature_object)

        # Limitation
        for n, b in bl.object.getPose(armature_object).bones.items():
            poseBoneLimit(n, b)

    # import rigid bodies
    rigidBodies=__importRigidBodies(io)
    if rigidBodies:
        bl.object.makeParent(root, rigidBodies)

    # import constraints
    constraints=__importConstraints(io)
    if constraints:
        bl.object.makeParent(root, constraints)

    bl.object.activate(root)

