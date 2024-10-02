# This Blender add-on is licensed under the MIT License.
#
# MIT License
#
# Copyright (c) 2024 HoloLab Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys
import math
import bpy


bl_info = {
    "name": "Moderate Weight Reduction Tools",
    "author": "HoloLab Inc.",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "3D Viewport > Sidebar > HoloLab",
    "description": "The add-on generates a model from the original model with reduced polygon mesh and optimized textures.",
    "warning": "",
    "support": "COMMUNITY",
    "doc_url": "https://github.com/HoloLabInc/ModerateWeightReductionTools/blob/main/README.md",
    "tracker_url": "https://github.com/HoloLabInc/ModerateWeightReductionTools/issues",
    "category": "Tool"
}

class HoloLab_OT_ModerateWeightReductionTools(bpy.types.Operator):
    bl_idname = "hololab.moderate_weight_reduction_tools"
    bl_label = "Moderate Weight Reduction Tools"
    bl_description = "Generates models with reduced polygon mesh and optimized textures from the original model."
    bl_options = {'REGISTER', 'UNDO'}

    remove_doubles: bpy.props.BoolProperty(
        name="remove_doubles",
        description="If the mesh is split, overlapping vertices are joined.",
        default=False
    )

    decimate_rate: bpy.props.FloatProperty(
        name="decimate_rate",
        description="Ratio of polygon mesh left after reduction.",
        default=0.03,
        min=0.0,
        max=1.0
    )

    texture_name: bpy.props.StringProperty(
        name="texture_name",
        description="Name of new texture.",
        default="texture"
    )

    texture_resolution: bpy.props.EnumProperty(
        name="texture_resolution",
        description="Resolution of new texture.",
        default="1024", 
        items=[
            ("256", "256 x 256", "256 x 256"),
            ("512", "512 x 512", "512 x 512"),
            ("1024", "1024 x 1024", "1024 x 1024"),
            ("2048", "2048 x 2048", "2048 x 2048"),
            ("4096", "4096 x 4096", "4096 x 4096")
        ]
    )

    def execute(self, context):
        self.report({'INFO'}, "execute auto decimation and bake function")

        self.report({'INFO'}, f"{self.remove_doubles=}")
        self.report({'INFO'}, f"{self.decimate_rate=}")
        self.report({'INFO'}, f"{self.texture_name=}")
        self.report({'INFO'}, f"{self.texture_resolution=}")

        previous_language = bpy.context.preferences.view.language
        bpy.context.preferences.view.language = 'en_US'

        try:
            self.clone_target_object()
            self.integration_polygon()
            self.reduction_polygon()
            self.set_material_and_texture()
            self.expand_uv()
            self.apply_auto_smooth()
            self.settings_bake_configurations()
            self.execute_bake()
            self.triangulate_faces()
            self.export_gltf()
        except Exception as e:
            self.report({'ERROR'}, f"{e}")
            return {'CANCELLED'}
        finally:
            bpy.context.preferences.view.language = previous_language

        return {'FINISHED'}

    # clone tartget object
    def clone_target_object(self):
        self.report({'INFO'}, f"{sys._getframe().f_code.co_name}")

        # select source object
        bpy.ops.object.select_all(action='DESELECT')
        object_source = bpy.context.active_object
        if object_source is None:
            self.report({'ERROR'}, "please turn active the source object in outliner or view port.")
            raise Exception("source object is not found.")
        object_source.select_set(True)
        bpy.context.view_layer.objects.active = object_source

        # rename source object
        object_source.name = "Original"

        # duplicate object
        bpy.ops.object.duplicate(linked=False)

        # rename target object
        object_target = bpy.context.active_object
        object_target.name = "Result"

    # integration polygon
    def integration_polygon(self):
        self.report({'INFO'}, f"{sys._getframe().f_code.co_name}")

        # select target object
        bpy.ops.object.select_all(action='DESELECT')
        object_target = bpy.data.objects.get("Result")
        object_target.select_set(True)
        bpy.context.view_layer.objects.active = object_target

        # apply remove doubles
        if self.remove_doubles:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.001)
            bpy.ops.object.mode_set(mode='OBJECT')

    # reduction polygon
    def reduction_polygon(self):
        self.report({'INFO'}, f"{sys._getframe().f_code.co_name}")

        # select target object
        bpy.ops.object.select_all(action='DESELECT')
        object_target = bpy.data.objects.get("Result")
        object_target.select_set(True)
        bpy.context.view_layer.objects.active = object_target

        # decimation
        decimate_modifier = object_target.modifiers.new(name="Decimate", type='DECIMATE')
        decimate_modifier.ratio = self.decimate_rate
        bpy.ops.object.modifier_apply(modifier=decimate_modifier.name)

    # settings material and texture
    def set_material_and_texture(self):
        self.report({'INFO'}, f"{sys._getframe().f_code.co_name}")

        # select source object
        bpy.ops.object.select_all(action='DESELECT')
        object_source = bpy.data.objects.get("Original")
        object_source.select_set(True)
        bpy.context.view_layer.objects.active = object_source

        # rename exist image texture with same name as specified name that are linked in source object material
        for material in object_source.data.materials:
            principled_bsdf = [node for node in material.node_tree.nodes if node.bl_idname == 'ShaderNodeBsdfPrincipled'][0]
            if principled_bsdf.inputs['Base Color'].is_linked is False:
                continue
            image = principled_bsdf.inputs['Base Color'].links[0].from_socket.node.image
            if image.name == self.texture_name:
                image.name += ".original"

        # remove exist image textures that generated at last run　
        exist_images = [image for image in bpy.data.images if image.name == self.texture_name]
        for exist_image in exist_images:
            bpy.data.images.remove(image=exist_image)

        # select target object
        bpy.ops.object.select_all(action='DESELECT')
        object_target = bpy.data.objects.get("Result")
        object_target.select_set(True)
        bpy.context.view_layer.objects.active = object_target

        # clear materials
        object_target.data.materials.clear()

        # add new material
        material = bpy.data.materials.new(name="Material")
        object_target.data.materials.append(material)

        # add image texture node
        material.use_nodes = True
        node_tree = material.node_tree
        image_texture = node_tree.nodes.new(type='ShaderNodeTexImage')
        image_texture.location = (-200, 0)

        # create image texture
        resolution = int(self.texture_resolution)
        image_texture.image = bpy.data.images.new(name=self.texture_name, width=resolution, height=resolution)

        # link color socket from image texture to principled bsdf
        principled_bsdf = [node for node in node_tree.nodes if node.bl_idname == 'ShaderNodeBsdfPrincipled'][0]
        node_tree.links.new(image_texture.outputs['Color'], principled_bsdf.inputs['Base Color'])

    # expand uv
    def expand_uv(self):
        self.report({'INFO'}, f"{sys._getframe().f_code.co_name}")

        # select target object
        bpy.ops.object.select_all(action='DESELECT')
        object_target = bpy.data.objects.get("Result")
        object_target.select_set(True)
        bpy.context.view_layer.objects.active = object_target

        # set smart uv project
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=0.349066, margin_method='FRACTION', island_margin=0.001, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode='OBJECT')

    # apply auto smooth
    def apply_auto_smooth(self):
        self.report({'INFO'}, f"{sys._getframe().f_code.co_name}")

        # select target object
        bpy.ops.object.select_all(action='DESELECT')
        object_target = bpy.data.objects.get("Result")
        object_target.select_set(True)
        bpy.context.view_layer.objects.active = object_target

        # apply auto smooth
        if bpy.app.version < (4, 1, 0):
            bpy.context.object.data.use_auto_smooth = True
            bpy.context.object.data.auto_smooth_angle = math.radians(30)
        else:
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))

    # settings bake configurations
    def settings_bake_configurations(self):
        self.report({'INFO'}, f"{sys._getframe().f_code.co_name}")

        # set render engine to cycles
        bpy.context.scene.render.engine = 'CYCLES'

        # disable pass direct and pass indirect
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False

        # enable selected to active
        bpy.context.scene.render.bake.use_selected_to_active = True

        # set cage extrusion to 0.1m
        bpy.context.scene.render.bake.cage_extrusion = 0.1

        # set margin type to extend
        bpy.context.scene.render.bake.margin_type = 'EXTEND'

        # set bake type to diffuse
        bpy.context.scene.cycles.bake_type = 'DIFFUSE'
        bpy.context.scene.render.bake.use_clear = True

    # execute bake
    def execute_bake(self):
        self.report({'INFO'}, f"{sys._getframe().f_code.co_name}")

        # deselect all object
        bpy.ops.object.select_all(action='DESELECT')

        # select source object
        object_source = bpy.data.objects.get("Original")
        object_source.select_set(True)
        
        # active tartget object
        object_target = bpy.data.objects.get("Result")
        bpy.context.view_layer.objects.active = object_target

        # execute bake
        bpy.ops.object.bake(type='DIFFUSE')

    def triangulate_faces(self):
        self.report({'INFO'}, f"{sys._getframe().f_code.co_name}")

        # select target object
        bpy.ops.object.select_all(action='DESELECT')
        object_target = bpy.data.objects.get("Result")
        object_target.select_set(True)
        bpy.context.view_layer.objects.active = object_target

        # traiangulate faces
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
        bpy.ops.object.mode_set(mode='OBJECT')

    def export_gltf(self):
        # this is workaround for the issue that gltf 2.0 does not export correctly.
        temp_file = os.path.join(bpy.app.tempdir, "temp.glb")
        bpy.ops.export_scene.gltf(filepath=temp_file, use_selection=True)

class HoloLab_OT_SaveBakedTexture(bpy.types.Operator):
    bl_idname = "hololab.save_baked_texture"
    bl_label = "Save Baked Texture"
    bl_description = "Save baked texture to PNG file for export the model as FBX file."
    bl_options = {'REGISTER', 'UNDO'}

    texture_name: bpy.props.StringProperty(
        name="texture_name",
        description="texture name",
        default="texture"
    )

    directory: bpy.props.StringProperty(
        name="directory_path",
        default="",
        maxlen=1024,
        subtype='DIR_PATH',
        description="",
    )

    filter_folder: bpy.props.BoolProperty(
        default=True,
        options={'HIDDEN'},
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.report({'INFO'}, "execute save baked texture function")

        previous_language = bpy.context.preferences.view.language
        bpy.context.preferences.view.language = 'en_US'

        try:
            self.save_texture()
        except Exception as e:
            self.report({'ERROR'}, f"{e}")
            return {'CANCELLED'}
        finally:
            bpy.context.preferences.view.language = previous_language

        return {'FINISHED'}

    def execute(self, context):
        self.report({'INFO'}, "execute save baked texture function")

        previous_language = bpy.context.preferences.view.language
        bpy.context.preferences.view.language = 'en_US'

        try:
            self.save_texture()
        except Exception as e:
            self.report({'ERROR'}, f"{e}")
            return {'CANCELLED'}
        finally:
            bpy.context.preferences.view.language = previous_language

        return {'FINISHED'}

    def save_texture(self):
        self.report({'INFO'}, f"{sys._getframe().f_code.co_name}")

        # select target object
        bpy.ops.object.select_all(action='DESELECT')
        object_target = bpy.data.objects.get("Result")
        if object_target is None:
            return

        # get baked texture
        texture = bpy.data.images[self.texture_name]
        if texture is None:
            return

        # save baked texture
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.type = 'IMAGE_EDITOR'
                for space in area.spaces:
                    if space.type != 'IMAGE_EDITOR':
                        continue
                    space.image = texture
                    filepath = os.path.join(self.directory, f"{self.texture_name}.png")
                    self.report({'INFO'}, f"{filepath}")
                    bpy.ops.image.save_as(filepath=filepath, relative_path=True)
                    break
                area.type = 'VIEW_3D'

class HoloLab_OT_DeleteOriginal(bpy.types.Operator):
    bl_idname = "hololab.delete_original"
    bl_label = "Delete Original"
    bl_description = "Delete unnecessary original object and tetextures from project for export the model as USDZ file."
    bl_options = {'REGISTER', 'UNDO'}

    texture_name: bpy.props.StringProperty(
        name="texture_name",
        description="texture name",
        default="texture"
    )

    def execute(self, context):
        self.report({'INFO'}, "execute delete Original object and texture function")

        previous_language = bpy.context.preferences.view.language
        bpy.context.preferences.view.language = 'en_US'

        try:
            self.delete_texture()
            self.delete_object()
        except Exception as e:
            self.report({'ERROR'}, f"{e}")
            return {'CANCELLED'}
        finally:
            bpy.context.preferences.view.language = previous_language

        return {'FINISHED'}

    def delete_texture(self):
        self.report({'INFO'}, f"{sys._getframe().f_code.co_name}")

        # check target object
        bpy.ops.object.select_all(action='DESELECT')
        object_source = bpy.data.objects.get("Original")
        if object_source is None:
            return

        # delete all textures without specified texture
        images = [image for image in bpy.data.images if image.name != self.texture_name]
        for image in images:
            bpy.data.images.remove(image=image)

    def delete_object(self):
        self.report({'INFO'}, f"{sys._getframe().f_code.co_name}")

        # select target object
        bpy.ops.object.select_all(action='DESELECT')
        object_source = bpy.data.objects.get("Original")
        if object_source is None:
            return

        # delete object
        with bpy.context.temp_override(selected_objects=[object_source]):
            bpy.ops.object.delete()

class HoloLab_PT_SideBar(bpy.types.Panel):
    bl_idname = "hololab.sidebar"
    bl_label = "HoloLab"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "HoloLab"

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="Moderate Weight Reduction Tools", icon='PLUGIN')

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="Mesh Setting:")
        box.prop(scene, "remove_doubles")
        box.prop(scene, "decimate_rate")

        box = layout.box()
        box.label(text="Texture Setting:")
        box.prop(scene, "texture_name")
        box.prop(scene, "texture_resolution")

        op = layout.operator(HoloLab_OT_ModerateWeightReductionTools.bl_idname, text='Start', icon='PLAY')
        op.remove_doubles = scene.remove_doubles
        op.decimate_rate = scene.decimate_rate
        op.texture_name = scene.texture_name
        op.texture_resolution = scene.texture_resolution

        layout.separator()
        layout.label(text="Export:")

        op = layout.operator(HoloLab_OT_SaveBakedTexture.bl_idname, text='Texture', icon='FILE_TICK')
        op.texture_name = scene.texture_name

        layout.label(text="Delete:")

        op = layout.operator(HoloLab_OT_DeleteOriginal.bl_idname, text='Original Model', icon='TRASH')
        op.texture_name = scene.texture_name

def menu_draw(cls, context):
    cls.layout.menu(HoloLab_PT_SideBar.bl_idname)

def register_properies():
    scene = bpy.types.Scene

    scene.remove_doubles = bpy.props.BoolProperty(
        name="Mesh Integration",
        description="If the mesh is split, overlapping vertices are joined.",
        default=False
    )

    scene.decimate_rate = bpy.props.FloatProperty(
        name="Rate of Polygon Left",
        description="Ratio of polygon mesh left after reduction.",
        default=0.03,
        min=0.0,
        max=1.0
    )

    scene.texture_name = bpy.props.StringProperty(
        name="Name",
        description="Name of new texture.",
        default="texture"
    )

    scene.texture_resolution = bpy.props.EnumProperty(
        name="Resolution",
        description="Resolution of new texture.",
        default="1024", 
        items=[
            ("256", "256 x 256", "256 x 256"),
            ("512", "512 x 512", "512 x 512"),
            ("1024", "1024 x 1024", "1024 x 1024"),
            ("2048", "2048 x 2048", "2048 x 2048"),
            ("4096", "4096 x 4096", "4096 x 4096")
        ]
    )

def unregister_properies():
    scene = bpy.types.Scene

    del scene.remove_doubles
    del scene.decimate_rate
    del scene.texture_name
    del scene.texture_resolution

classes = [
    HoloLab_OT_ModerateWeightReductionTools,
    HoloLab_OT_SaveBakedTexture,
    HoloLab_OT_DeleteOriginal,
    HoloLab_PT_SideBar
]

def register():
    for c in classes:
        bpy.utils.register_class(c)
    register_properies()

def unregister():
    unregister_properies()
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
