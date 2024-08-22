bl_info = {
    "name": "Banter Avatar Configurator",
    "author": "SideQuest",
    "description": "Configure and upload custom avatars for the Bantaverse",
    "blender": (4, 2, 0),
    "version": (0, 2, 0),
    "location": "View3D > Sidebar > BANTER",
    "support": "COMMUNITY",
    "category": "3D View",
}

VERSION = bl_info["version"]


def get_version_string():
    return str(VERSION[0]) + "." + str(VERSION[1]) + "." + str(VERSION[2])


import os
from typing import List
import bpy
import bpy.utils.previews
from bpy_extras.io_utils import ExportHelper
from .sq_app_api import SqAppApi
from .utils import Lod, combineObjects, generateLOD, getMeshTriCount, getMaterialCount
from .atlas import bakeAtlas

addon_keymaps = {}
_icons = None
sq_api = SqAppApi()


def meshpointer_poll(self, object):
    return object.type == "MESH"


def armaturepointer_poll(self, object):
    return object.type == "ARMATURE"


def headmesh_poll(self, object):
    for item in bpy.context.scene.banter_cLocalAvatarObjects:
        if item.object == object:
            return True
    return False


class BanterAvatarCollection(bpy.types.PropertyGroup):
    object: bpy.props.PointerProperty(type=bpy.types.Object, poll=meshpointer_poll)  # type: ignore


def getObjectsPolyCount(objects: List[BanterAvatarCollection]):
    return sum(
        getMeshTriCount(item.object.data)
        for item in objects
        if item.object and item.object.type == "MESH"
    )


class BANTER_UL_MeshList(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):

        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.prop(
                item, "object", text="", emboss=False, icon="OUTLINER_DATA_MESH"
            )

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"

    def draw_filter(self, context, layout):
        pass


# region Panels
class BANTER_PT_Configurator(bpy.types.Panel):
    bl_label = "Avatar Configurator"
    bl_idname = "BANTER_PT_Configurator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_context = ""
    bl_category = "BANTER"

    def draw(self, context):
        layout = self.layout

        # Armature
        col = layout.column(heading="Armature")
        col.prop(
            context.scene, "banter_pArmature", text="", icon="OUTLINER_OB_ARMATURE"
        )
        if not bpy.context.scene.banter_pArmature:
            col.operator("banter.import_armature", text="Create Default Armature")

        layout.separator()
        # Local Avatar
        col = layout.column()
        col.label(text="Local Avatar Meshes")
        if (
            bpy.context.scene.banter_cLocalAvatarObjects
            and len(bpy.context.scene.banter_cLocalAvatarObjects) > 0
        ):
            meshrow = col.row()
            meshrow.template_list(
                "BANTER_UL_MeshList",
                "",
                bpy.data.scenes[0],
                "banter_cLocalAvatarObjects",
                bpy.data.scenes[0],
                "banter_cLocalAvatarObjects_Active",
            )
            meshcol = meshrow.column(align=True)
            meshcol.operator("banter.add_object_local_avatar", icon="ADD", text="")
            meshcol.operator(
                "banter.remove_object_local_avatar", icon="REMOVE", text=""
            )
            layout.prop(
                context.scene,
                "banter_pLocalHeadMesh",
                text="Head Mesh",
                icon="OUTLINER_DATA_MESH",
            )
        else:
            innercol = col.column(align=True)
            innercol.label(text="No Local Avatar Meshes")
            innercol.operator(
                "banter.add_object_local_avatar", text="Use Selected Objects"
            )
            innercol.operator("banter.dummy", text="Import RPM Avatar")
            innercol.operator("banter.dummy", text="Import Mixamo Avatar")

        layout.separator()
        # LODs
        aLodIsMissing = False
        col = layout.row(align=True)
        col.prop(
            context.scene, "banter_pLod0Avatar", text="LOD0", icon="OUTLINER_DATA_MESH"
        )
        if not bpy.context.scene.banter_pLod0Avatar:
            aLodIsMissing = True

        col = layout.row(align=True)
        col.prop(
            context.scene, "banter_pLod1Avatar", text="LOD1", icon="OUTLINER_DATA_MESH"
        )
        if not bpy.context.scene.banter_pLod1Avatar:
            aLodIsMissing = True

        col = layout.row(align=True)
        col.prop(
            context.scene, "banter_pLod2Avatar", text="LOD2", icon="OUTLINER_DATA_MESH"
        )
        if not bpy.context.scene.banter_pLod2Avatar:
            aLodIsMissing = True

        col = layout.row(align=True)
        col.prop(
            context.scene, "banter_pLod3Avatar", text="LOD3", icon="OUTLINER_DATA_MESH"
        )
        if not bpy.context.scene.banter_pLod3Avatar:
            aLodIsMissing = True

        if aLodIsMissing:
            layout.operator(
                "banter.genmissinglods", text="Create LODs from Local Avatar"
            )

        layout.separator()
        # Shader
        # col = layout.column()
        # col.prop(context.scene, 'banter_pShaderHint', text='Avatar Shader')


class BANTER_PT_Validator(bpy.types.Panel):
    bl_label = "Validator"
    bl_idname = "BANTER_PT_Validator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_context = ""
    bl_category = "BANTER"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        op = col.operator("banter.validator", text="Run Validator")

        if bpy.context.scene.banter_bPassed:
            col.label(text="Passed", icon="CHECKMARK")
        else:
            col = col.column(align=True)
            col.label(text="Not all checks are passing:")

            # Armature
            if not bpy.context.scene.banter_pArmature:
                col.label(text="Armature")
                row = col.row()
                row.label(
                    text=f"Armature is not set",
                    icon=self.icon_bool(bpy.context.scene.banter_pArmature),
                )

            col.separator()

            # Tris
            if not bpy.context.scene.banter_bTrisPassed:
                col.label(text="Tris:")

                row = col.row()
                row.label(
                    text=f"Local: {Lod.LOCAL_LIMIT}",
                    icon=self.icon_bool(bpy.context.scene.banter_bLocalTris),
                )
                if not bpy.context.scene.banter_bLocalTris:
                    pass

                row = col.row()
                row.label(
                    text=f"LOD0: {Lod.LOD0}",
                    icon=self.icon_bool(bpy.context.scene.banter_bLod0Tris),
                )
                if not bpy.context.scene.banter_bLod0Tris:
                    op = row.operator("banter.genlod", text="Fix")
                    op.lodLevel = 0

                row = col.row()
                row.label(
                    text=f"LOD1: {Lod.LOD1}",
                    icon=self.icon_bool(bpy.context.scene.banter_bLod1Tris),
                )
                if not bpy.context.scene.banter_bLod1Tris:
                    op = row.operator("banter.genlod", text="Fix")
                    op.lodLevel = 1

                row = col.row()
                row.label(
                    text=f"LOD2: {Lod.LOD2}",
                    icon=self.icon_bool(bpy.context.scene.banter_bLod2Tris),
                )
                if not bpy.context.scene.banter_bLod2Tris:
                    op = row.operator("banter.genlod", text="Fix")
                    op.lodLevel = 2

                row = col.row()
                row.label(
                    text=f"LOD3: {Lod.LOD3}",
                    icon=self.icon_bool(bpy.context.scene.banter_bLod3Tris),
                )
                if not bpy.context.scene.banter_bLod3Tris:
                    op = row.operator("banter.genlod", text="Fix")
                    op.lodLevel = 3

            # Materials
            if not bpy.context.scene.banter_bMatsPassed:
                col.label(text="Materials:")

                if not bpy.context.scene.banter_bLod0Mats:
                    row = col.row()
                    row.label(
                        text="LOD0: 1 material maximum",
                        icon=self.icon_bool(bpy.context.scene.banter_bLod0Mats),
                    )
                    if bpy.context.scene.banter_pLod0Avatar:
                        op = row.operator("banter.atlasmaterial", text="Fix")
                        op.targetObj = bpy.context.scene.banter_pLod0Avatar

                if not bpy.context.scene.banter_bLod1Mats:
                    row = col.row()
                    row.label(
                        text="LOD1: 1 material maximum",
                        icon=self.icon_bool(bpy.context.scene.banter_bLod1Mats),
                    )
                    if bpy.context.scene.banter_pLod1Avatar:
                        op = row.operator("banter.atlasmaterial", text="Fix")
                        op.targetObj = bpy.context.scene.banter_pLod1Avatar

                if not bpy.context.scene.banter_bLod2Mats:
                    row = col.row()
                    row.label(
                        text="LOD2: 1 material maximum",
                        icon=self.icon_bool(bpy.context.scene.banter_bLod2Mats),
                    )
                    if bpy.context.scene.banter_pLod2Avatar:
                        op = row.operator("banter.atlasmaterial", text="Fix")
                        op.targetObj = bpy.context.scene.banter_pLod2Avatar

                if not bpy.context.scene.banter_bLod3Mats:
                    row = col.row()
                    row.label(
                        text="LOD3: 1 material maximum",
                        icon=self.icon_bool(bpy.context.scene.banter_bLod3Mats),
                    )
                    if bpy.context.scene.banter_pLod3Avatar:
                        op = row.operator("banter.atlasmaterial", text="Fix")
                        op.targetObj = bpy.context.scene.banter_pLod3Avatar

        col.label(text="Warnings:")
        if not bpy.context.scene.banter_pLocalHeadMesh:
            col.label(text="No Head Mesh Selected", icon="ERROR")

    def icon_bool(self, b: bool) -> int:
        return "CHECKMARK" if b else "PANEL_CLOSE"


class BANTER_PT_Exporter(bpy.types.Panel):
    bl_label = "Export"
    bl_idname = "BANTER_PT_Exporter"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_context = ""
    bl_category = "BANTER"
    bl_options = {"DEFAULT_CLOSED"}
    _timer = None

    def draw(self, context):
        layout = self.layout
        if sq_api.user is None:
            col = layout.column()
            op = col.operator("banter.export_avatars", text="Export Avatars")
            col.label(text="To Sign In: ")
            col.label(text="Go to " + sq_api.login_code.verification_url)
            col.label(text="and put in " + sq_api.login_code.code)
            # props = bpy.context.scene.CodeProp
            # col.prop(props, "code", text=sq_api.login_code.code)
            col.label(text="Please allow up to 10s after you enter the code.")
            op = col.operator("banter.open_url", text="Open Page")
            op.url = "https://sidequestvr.com/link-sidequest"
        else:
            col = layout.column()
            col.label(text="Logged in as " + sq_api.user.name)
            op = col.operator("banter.upload_avatars", text="Export & Upload Avatars")
            op = col.operator("banter.export_avatars", text="Export Avatars Only")
            col.separator()
            op = col.operator("banter.logout", text="Logout")


# endregion


# region Operators
class Banter_OT_GenerateMissingLods(bpy.types.Operator):
    bl_idname = "banter.genmissinglods"
    bl_label = "Generate Missing LODs"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        return (
            bpy.context.scene.banter_cLocalAvatarObjects is not None
            and len(bpy.context.scene.banter_cLocalAvatarObjects) > 0
            and (
                bpy.context.scene.banter_pLod0Avatar is None
                or bpy.context.scene.banter_pLod1Avatar is None
                or bpy.context.scene.banter_pLod2Avatar is None
                or bpy.context.scene.banter_pLod3Avatar is None
            )
        )

    def execute(self, context):
        if bpy.context.scene.banter_cLocalAvatarObjects is None:
            return {"CANCELLED"}

        if bpy.context.scene.banter_pLod0Avatar is None:
            bpy.ops.banter.genlod(lodLevel=0)
        if bpy.context.scene.banter_pLod1Avatar is None:
            bpy.ops.banter.genlod(lodLevel=1)
        if bpy.context.scene.banter_pLod2Avatar is None:
            bpy.ops.banter.genlod(lodLevel=2)
        if bpy.context.scene.banter_pLod3Avatar is None:
            bpy.ops.banter.genlod(lodLevel=3)

        return {"FINISHED"}


class Banter_OT_GenerateMeshForLod(bpy.types.Operator):
    bl_idname = "banter.genlod"
    bl_label = "Generate Mesh for LOD"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    lodLevel: bpy.props.IntProperty(name="LOD Level", description="", default=0, min=-1, max=3, options={"HIDDEN"})  # type: ignore

    @classmethod
    def poll(cls, context):
        return bpy.context.scene.banter_cLocalAvatarObjects is not None

    def execute(self, context):

        objects = []
        for item in bpy.context.scene.banter_cLocalAvatarObjects:
            if item.object:
                objects.append(item.object)

        targetObj = combineObjects(objects)
        targetObj.name = "Avatar_LOD" + str(self.lodLevel)

        lodObj = generateLOD(
            targetObj,
            Lod.intToLod(self.lodLevel),
            True,
            True if self.lodLevel == 0 else False,
        )

        # Bake an atlas material if needed
        if getMaterialCount(lodObj) > 1:
            bpy.ops.banter.atlasmaterial(targetObj=lodObj.name)

        match self.lodLevel:
            case 0:
                bpy.context.scene.banter_pLod0Avatar = lodObj
            case 1:
                bpy.context.scene.banter_pLod1Avatar = lodObj
            case 2:
                bpy.context.scene.banter_pLod2Avatar = lodObj
            case 3:
                bpy.context.scene.banter_pLod3Avatar = lodObj

        return {"FINISHED"}


class Banter_OT_AddObjectToLocalAvatarList(bpy.types.Operator):
    bl_idname = "banter.add_object_local_avatar"
    bl_label = "Add Meshes"
    bl_description = (
        "Adds selected meshes to the list of meshes that define your local avatar"
    )
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        for obj in context.selected_objects:
            if obj.type == "MESH":
                return True
        return False

    def execute(self, context):
        for obj in context.selected_objects:
            self.add_recursive(obj)
        return {"FINISHED"}

    def add_recursive(self, obj):
        if obj.type == "MESH":
            exists = False
            for checkObj in bpy.context.scene.banter_cLocalAvatarObjects:
                if checkObj.object == obj:
                    exists = True
                    break
            if not exists:
                ref = bpy.context.scene.banter_cLocalAvatarObjects.add()
                ref.object = obj
        for child in obj.children:
            self.add_recursive(child)


class Banter_OT_RemoveObjectFromLocalAvatarList(bpy.types.Operator):
    bl_idname = "banter.remove_object_local_avatar"
    bl_label = "Remove Mesh"
    bl_description = "Removes the highlighted mesh from the list of meshes that define your local avatar"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        return (
            context.scene.banter_cLocalAvatarObjects
            and len(context.scene.banter_cLocalAvatarObjects) > 0
        )

    def execute(self, context):
        context.scene.banter_cLocalAvatarObjects.remove(
            context.scene.banter_cLocalAvatarObjects_Active
        )
        return {"FINISHED"}


class Banter_OT_OpenUrl(bpy.types.Operator):
    bl_idname = "banter.open_url"
    bl_label = "Open URL"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    url: bpy.props.StringProperty(name="URL", options={"HIDDEN"})  # type: ignore

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set("")
        return not False

    def execute(self, context):
        exec("import webbrowser")
        exec(f"webbrowser.open('{self.url}')")
        return {"FINISHED"}


class Banter_OT_ImportArmature(bpy.types.Operator):
    bl_idname = "banter.import_armature"
    bl_label = "Import Banter Armature"
    bl_description = "Imports the default Banter armature"

    def execute(self, context):
        script_directory = os.path.dirname(os.path.realpath(__file__))
        filepath = os.path.join(script_directory, "resources/default_bs_rig.blend")

        with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
            data_to.objects = [
                name for name in data_from.objects if name.startswith("BArmature")
            ]

        for obj in data_to.objects:
            if obj is not None:
                bpy.context.collection.objects.link(obj)
                if not bpy.context.scene.banter_pArmature:
                    if obj.type == "ARMATURE":
                        bpy.context.scene.banter_pArmature = obj

        return {"FINISHED"}


class Banter_OT_AtlasMaterial(bpy.types.Operator):
    bl_idname = "banter.atlasmaterial"
    bl_label = "Atlas Material"
    bl_description = "Atlas Material"
    bl_options = {"REGISTER", "UNDO"}

    targetObj: bpy.props.StringProperty(
        name="Target object name", default=""
    )  # type: ignore

    def execute(self, context):
        bakeAtlas(bpy.data.objects[self.targetObj])
        return {"FINISHED"}


class Banter_OT_RunValidator(bpy.types.Operator):
    bl_idname = "banter.validator"
    bl_label = "Validator"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        localTris = (
            getObjectsPolyCount(bpy.context.scene.banter_cLocalAvatarObjects)
            if bpy.context.scene.banter_cLocalAvatarObjects
            else 1000000
        )
        lod0Tris = (
            getMeshTriCount(bpy.context.scene.banter_pLod0Avatar.data)
            if bpy.context.scene.banter_pLod0Avatar
            else 1000000
        )
        lod1Tris = (
            getMeshTriCount(bpy.context.scene.banter_pLod1Avatar.data)
            if bpy.context.scene.banter_pLod1Avatar
            else 1000000
        )
        lod2Tris = (
            getMeshTriCount(bpy.context.scene.banter_pLod2Avatar.data)
            if bpy.context.scene.banter_pLod2Avatar
            else 1000000
        )
        lod3Tris = (
            getMeshTriCount(bpy.context.scene.banter_pLod3Avatar.data)
            if bpy.context.scene.banter_pLod3Avatar
            else 1000000
        )

        # Tris
        bpy.context.scene.banter_bLocalTris = localTris <= Lod.LOCAL_LIMIT
        bpy.context.scene.banter_bLod0Tris = lod0Tris <= Lod.LOD0
        bpy.context.scene.banter_bLod1Tris = lod1Tris <= Lod.LOD1
        bpy.context.scene.banter_bLod2Tris = lod2Tris <= Lod.LOD2
        bpy.context.scene.banter_bLod3Tris = lod3Tris <= Lod.LOD3

        bpy.context.scene.banter_bTrisPassed = (
            bpy.context.scene.banter_bLocalTris
            and bpy.context.scene.banter_bLod0Tris
            and bpy.context.scene.banter_bLod1Tris
            and bpy.context.scene.banter_bLod2Tris
            and bpy.context.scene.banter_bLod3Tris
            and True
        )

        # Materials
        bpy.context.scene.banter_bLod0Mats = 2 > (
            getMaterialCount(bpy.context.scene.banter_pLod0Avatar)
            if bpy.context.scene.banter_pLod0Avatar
            else 0
        )
        bpy.context.scene.banter_bLod1Mats = 2 > (
            getMaterialCount(bpy.context.scene.banter_pLod1Avatar)
            if bpy.context.scene.banter_pLod1Avatar
            else 0
        )
        bpy.context.scene.banter_bLod2Mats = 2 > (
            getMaterialCount(bpy.context.scene.banter_pLod2Avatar)
            if bpy.context.scene.banter_pLod2Avatar
            else 0
        )
        bpy.context.scene.banter_bLod3Mats = 2 > (
            getMaterialCount(bpy.context.scene.banter_pLod3Avatar)
            if bpy.context.scene.banter_pLod3Avatar
            else 0
        )

        bpy.context.scene.banter_bMatsPassed = (
            bpy.context.scene.banter_bLod0Mats
            and bpy.context.scene.banter_bLod1Mats
            and bpy.context.scene.banter_bLod2Mats
            and bpy.context.scene.banter_bLod3Mats
            and True
        )

        # Final check
        bpy.context.scene.banter_bPassed = (
            bpy.context.scene.banter_pArmature is not None
            and bpy.context.scene.banter_bTrisPassed
            and bpy.context.scene.banter_bMatsPassed
            and True
        )

        return {"FINISHED"}


class Banter_OT_LogOut(bpy.types.Operator):
    bl_idname = "banter.logout"
    bl_label = "Log Out"
    bl_description = ""
    bl_options = {"REGISTER"}

    def execute(self, context):
        sq_api.logout()
        return {"FINISHED"}


class Banter_OT_ExportAvatars(bpy.types.Operator, ExportHelper):
    bl_idname = "banter.export_avatars"
    bl_label = "Export Avatars"
    bl_description = ""
    bl_options = {"REGISTER"}

    filter_glob: bpy.props.StringProperty(default="*.glb", options={"HIDDEN"})  # type: ignore
    filename_ext = ".glb"
    filename = "banter_avatar"

    def invoke(self, context, event):
        return ExportHelper.invoke(self, context, event)

    @classmethod
    def poll(cls, context):
        return bpy.context.scene.banter_bPassed

    def execute(self, context):
        try:
            self.report({"INFO"}, "Avatar export started...")
            # Double check for tricky people
            bpy.ops.banter.validator("INVOKE_DEFAULT")
            if not bpy.context.scene.banter_bPassed:
                self.report(
                    {"ERROR"},
                    "Precheck failed. Please fix the issues before exporting.",
                )
                return {"CANCELLED"}

            path, ext = os.path.splitext(self.filepath)
            highpath = self.filepath
            lowpath = path + f"_lods{ext}"

            # select elements of local avatar
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            bpy.context.scene.banter_pArmature.select_set(True)
            for item in bpy.context.scene.banter_cLocalAvatarObjects:
                if item.object:
                    item.object.select_set(True)

            bpy.context.scene.banter_bIsCurrentlyExporting = True
            bpy.ops.export_scene.gltf(
                filepath=highpath, check_existing=False, use_selection=True
            )
            bpy.context.scene.banter_sLocalExportPath = highpath
            bpy.context.scene.banter_bIsCurrentlyExporting = False

            print(lowpath)
            # select lods
            bpy.ops.object.select_all(action="DESELECT")
            bpy.context.scene.banter_pArmature.select_set(True)
            bpy.context.scene.banter_pLod0Avatar.select_set(True)
            bpy.context.scene.banter_pLod1Avatar.select_set(True)
            bpy.context.scene.banter_pLod2Avatar.select_set(True)
            bpy.context.scene.banter_pLod3Avatar.select_set(True)

            bpy.context.scene.banter_bIsCurrentlyExporting = True
            bpy.ops.export_scene.gltf(
                filepath=lowpath, check_existing=False, use_selection=True
            )
            bpy.context.scene.banter_sLodExportPath = lowpath
            bpy.context.scene.banter_bIsCurrentlyExporting = False
            self.report({"INFO"}, "Avatar export complete.")
            return {"FINISHED"}
        except Exception:
            bpy.context.scene.banter_sLocalExportPath = ""
            bpy.context.scene.banter_sLodExportPath = ""
            raise Exception("Export failed")


class Banter_OT_UploadAvatars(Banter_OT_ExportAvatars):
    bl_idname = "banter.upload_avatars"
    bl_label = "Upload Avatars"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return bpy.context.scene.banter_bPassed

    def execute(self, context):
        try:
            Banter_OT_ExportAvatars.execute(self, context)
            sq_api.upload_avatars(
                bpy.context.scene.banter_sLocalExportPath,
                bpy.context.scene.banter_sLodExportPath,
            )
            self.report({"INFO"}, "Avatar upload complete.")
        except Exception as e:
            self.report({"ERROR"}, str(e))

        bpy.context.scene.banter_sLocalExportPath = ""
        bpy.context.scene.banter_sLodExportPath = ""
        return {"FINISHED"}


class Banter_OT_Dummy(bpy.types.Operator):
    bl_idname = "banter.dummy"
    bl_label = "Dummy Op"
    bl_description = "Dummy Op"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return False

    def execute(self, context):
        return {"FINISHED"}


# endregion


# region Lifecycle
def register():
    global _icons
    _icons = bpy.utils.previews.new()

    bpy.utils.register_class(BANTER_UL_MeshList)

    bpy.utils.register_class(BANTER_PT_Configurator)
    bpy.utils.register_class(BANTER_PT_Validator)
    bpy.utils.register_class(BANTER_PT_Exporter)

    bpy.utils.register_class(Banter_OT_Dummy)
    bpy.utils.register_class(Banter_OT_LogOut)
    bpy.utils.register_class(Banter_OT_UploadAvatars)
    bpy.utils.register_class(Banter_OT_ExportAvatars)
    bpy.utils.register_class(Banter_OT_OpenUrl)
    bpy.utils.register_class(Banter_OT_ImportArmature)
    bpy.utils.register_class(Banter_OT_AtlasMaterial)
    bpy.utils.register_class(Banter_OT_RunValidator)
    bpy.utils.register_class(Banter_OT_GenerateMissingLods)
    bpy.utils.register_class(Banter_OT_GenerateMeshForLod)
    bpy.utils.register_class(Banter_OT_AddObjectToLocalAvatarList)
    bpy.utils.register_class(Banter_OT_RemoveObjectFromLocalAvatarList)

    bpy.utils.register_class(BanterAvatarCollection)

    bpy.types.Scene.banter_bIsCurrentlyExporting = bpy.props.BoolProperty(
        name="PluginIsCurrentlyExporting", description="", default=False
    )

    # check props
    bpy.types.Scene.banter_bPassed = bpy.props.BoolProperty(
        name="APassed",
        description="Test if the Avatar fullfils the requirements",
        default=False,
    )

    # tris
    bpy.types.Scene.banter_bTrisPassed = bpy.props.BoolProperty(
        name="TrisPassed", description="All Tri checks Passed", default=False
    )
    bpy.types.Scene.banter_bLocalTris = bpy.props.BoolProperty(
        name="LocalTris", description="Mesh meets local tri limits", default=False
    )
    bpy.types.Scene.banter_bLod0Tris = bpy.props.BoolProperty(
        name="Lod0Tris", description="Mesh meets LOD0 tri limits", default=False
    )
    bpy.types.Scene.banter_bLod1Tris = bpy.props.BoolProperty(
        name="Lod1Tris", description="Mesh meets LOD1 tri limits", default=False
    )
    bpy.types.Scene.banter_bLod2Tris = bpy.props.BoolProperty(
        name="Lod2Tris", description="Mesh meets LOD2 tri limits", default=False
    )
    bpy.types.Scene.banter_bLod3Tris = bpy.props.BoolProperty(
        name="Lod3Tris", description="Mesh meets LOD3 tri limits", default=False
    )

    # materials
    bpy.types.Scene.banter_bMatsPassed = bpy.props.BoolProperty(
        name="MatsPassed", description="All Material checks Passed", default=False
    )
    bpy.types.Scene.banter_bLod0Mats = bpy.props.BoolProperty(
        name="Lod0Mats", description="Mesh meets LOD0 material limits", default=False
    )
    bpy.types.Scene.banter_bLod1Mats = bpy.props.BoolProperty(
        name="Lod1Mats", description="Mesh meets LOD1 material limits", default=False
    )
    bpy.types.Scene.banter_bLod2Mats = bpy.props.BoolProperty(
        name="Lod2Mats", description="Mesh meets LOD2 material limits", default=False
    )
    bpy.types.Scene.banter_bLod3Mats = bpy.props.BoolProperty(
        name="Lod3Mats", description="Mesh meets LOD3 material limits", default=False
    )

    # pointer props
    bpy.types.Scene.banter_pArmature = bpy.props.PointerProperty(
        name="Armature",
        description="",
        type=bpy.types.Object,
        poll=armaturepointer_poll,
    )
    bpy.types.Scene.banter_cLocalAvatarObjects = bpy.props.CollectionProperty(
        name="LocalAvatar", description="", type=BanterAvatarCollection
    )
    bpy.types.Scene.banter_cLocalAvatarObjects_Active = bpy.props.IntProperty(
        name="LocalAvatarSelectedObject", description="", default=0
    )
    bpy.types.Scene.banter_pLocalHeadMesh = bpy.props.PointerProperty(
        name="Local Head Mesh",
        description="This mesh will be hidden in Banter so your view isn't blocked",
        type=bpy.types.Object,
        poll=headmesh_poll,
    )
    bpy.types.Scene.banter_pLod0Avatar = bpy.props.PointerProperty(
        name="Avatar LOD0",
        description=f"Tri Limit {Lod.LOD0}\nShapekeys allowed",
        type=bpy.types.Object,
        poll=meshpointer_poll,
    )
    bpy.types.Scene.banter_pLod1Avatar = bpy.props.PointerProperty(
        name="Avatar LOD1",
        description=f"Tri Limit {Lod.LOD1}\nShapekeys will be stripped",
        type=bpy.types.Object,
        poll=meshpointer_poll,
    )
    bpy.types.Scene.banter_pLod2Avatar = bpy.props.PointerProperty(
        name="Avatar LOD2",
        description=f"Tri Limit {Lod.LOD2}\nShapekeys will be stripped",
        type=bpy.types.Object,
        poll=meshpointer_poll,
    )
    bpy.types.Scene.banter_pLod3Avatar = bpy.props.PointerProperty(
        name="Avatar LOD3",
        description=f"Tri Limit {Lod.LOD3}\nShapekeys will be stripped",
        type=bpy.types.Object,
        poll=meshpointer_poll,
    )

    bpy.types.Scene.banter_pShaderHint = bpy.props.EnumProperty(
        name="ShaderHint",
        description="Shader to use in Banter",
        items=[
            ("PBR", "PBR", "Default PBR"),
            ("TOON", "Toon", "Toon shader"),
            ("FALLBACK", "(Fallback) Diffuse", "Default diffuse shader"),
        ],
        default="FALLBACK",
    )

    # export props
    bpy.types.Scene.banter_sLocalExportPath = bpy.props.StringProperty(
        name="LocalExportPath",
        description="Local Export Path",
        default="",
        subtype="DIR_PATH",
    )
    bpy.types.Scene.banter_sLodExportPath = bpy.props.StringProperty(
        name="LodExportPath",
        description="Lod Export Path",
        default="",
        subtype="DIR_PATH",
    )


def unregister():
    global _icons
    bpy.utils.previews.remove(_icons)
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    for km, kmi in addon_keymaps.values():
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    del bpy.types.Scene.banter_bIsCurrentlyExporting

    # del bpy.types.Scene.CodeProp
    del bpy.types.Scene.banter_bPassed

    del bpy.types.Scene.banter_bTrisPassed
    del bpy.types.Scene.banter_bLocalTris
    del bpy.types.Scene.banter_bLod0Tris
    del bpy.types.Scene.banter_bLod1Tris
    del bpy.types.Scene.banter_bLod2Tris
    del bpy.types.Scene.banter_bLod3Tris

    del bpy.types.Scene.banter_bMatsPassed
    del bpy.types.Scene.banter_bLod0Mats
    del bpy.types.Scene.banter_bLod1Mats
    del bpy.types.Scene.banter_bLod2Mats
    del bpy.types.Scene.banter_bLod3Mats

    del bpy.types.Scene.banter_pArmature
    del bpy.types.Scene.banter_cLocalAvatarObjects
    del bpy.types.Scene.banter_cLocalAvatarObjects_Active
    del bpy.types.Scene.banter_pLocalHeadMesh
    del bpy.types.Scene.banter_pLod0Avatar
    del bpy.types.Scene.banter_pLod1Avatar
    del bpy.types.Scene.banter_pLod2Avatar
    del bpy.types.Scene.banter_pLod3Avatar

    del bpy.types.Scene.banter_pShaderHint

    del bpy.types.Scene.banter_sLocalExportPath
    del bpy.types.Scene.banter_sLodExportPath

    bpy.utils.unregister_class(BanterAvatarCollection)

    bpy.utils.unregister_class(BANTER_PT_Exporter)
    bpy.utils.unregister_class(BANTER_PT_Configurator)
    bpy.utils.unregister_class(BANTER_PT_Validator)

    bpy.utils.unregister_class(BANTER_UL_MeshList)

    bpy.utils.unregister_class(Banter_OT_Dummy)
    bpy.utils.unregister_class(Banter_OT_LogOut)
    bpy.utils.unregister_class(Banter_OT_UploadAvatars)
    bpy.utils.unregister_class(Banter_OT_ExportAvatars)
    bpy.utils.unregister_class(Banter_OT_OpenUrl)
    bpy.utils.unregister_class(Banter_OT_ImportArmature)
    bpy.utils.unregister_class(Banter_OT_AtlasMaterial)
    bpy.utils.unregister_class(Banter_OT_RunValidator)
    bpy.utils.unregister_class(Banter_OT_GenerateMissingLods)
    bpy.utils.unregister_class(Banter_OT_GenerateMeshForLod)
    bpy.utils.unregister_class(Banter_OT_AddObjectToLocalAvatarList)
    bpy.utils.unregister_class(Banter_OT_RemoveObjectFromLocalAvatarList)


# endregion


# region glTF Hooks
class glTF2ExportUserExtension:
    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension  # type: ignore

        self.Extension = Extension

    def gather_asset_hook(self, gltf2_asset, export_settings):
        if bpy.context.scene.banter_bIsCurrentlyExporting:
            gltf2_asset.generator = "Banter Avatar Creator v" + get_version_string()
            if (
                bpy.context.scene.banter_pShaderHint
                and bpy.context.scene.banter_pShaderHint != "FALLBACK"
            ):
                self.ensure_extras(gltf2_asset)
                gltf2_asset.extras["BANTER_avatar_shader"] = (
                    bpy.context.scene.banter_pShaderHint
                )

    def gather_node_hook(self, gltf2_node, blender_object, export_settings):
        if bpy.context.scene.banter_bIsCurrentlyExporting:
            # switch also covers duplicate lods, i.e. if lod1 can also meet
            # the limits of lod2 and lod3, this will still work
            match blender_object.name:
                case bpy.context.scene.banter_pLod0Avatar.name:
                    self.ensure_extras(gltf2_node)
                    gltf2_node.extras["BANTER_avatar_lod"] = 0
                case bpy.context.scene.banter_pLod1Avatar.name:
                    self.ensure_extras(gltf2_node)
                    gltf2_node.extras["BANTER_avatar_lod"] = 1
                case bpy.context.scene.banter_pLod2Avatar.name:
                    self.ensure_extras(gltf2_node)
                    gltf2_node.extras["BANTER_avatar_lod"] = 2
                case bpy.context.scene.banter_pLod3Avatar.name:
                    self.ensure_extras(gltf2_node)
                    gltf2_node.extras["BANTER_avatar_lod"] = 3
                case _:
                    pass

            if bpy.context.scene.banter_pLocalHeadMesh:
                if blender_object.name == bpy.context.scene.banter_pLocalHeadMesh.name:
                    self.ensure_extras(gltf2_node)
                    gltf2_node.extras["BANTER_avatar_component"] = "HEAD"

    def ensure_extras(self, gltf2_object):
        if gltf2_object.extras is None:
            gltf2_object.extras = {}


# endregion
