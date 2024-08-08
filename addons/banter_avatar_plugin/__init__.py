bl_info = {
    "name" : "Banter Avatar Creator",
    "author" : "SideQuest", 
    "description" : "Create and upload avatars to Banter",
    "blender" : (4, 2, 0),
    "version" : (1, 0, 0),
    "location" : "View3D > Sidebar > BANTER",
    "support": 'COMMUNITY', 
    "category" : "3D View" 
}

import os
from typing import List
import bpy
import bpy.utils.previews
from .utils import combineMeshes, generateLOD, getMeshPolyCount, intToLod, getLodGroup, Lod
from .sq_app_api import SqAppApi

addon_keymaps = {}
_icons = None
sq_api = SqAppApi()

class banter_avatar_collection(bpy.types.PropertyGroup):
    mesh: bpy.props.PointerProperty(type=bpy.types.Object) # type: ignore

def getObjectsPolyCount(objects: List[banter_avatar_collection]):
    return sum(getMeshPolyCount(obj.mesh) for obj in objects)

class BANTER_UL_MeshList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "mesh", text="", emboss=False, )#icon_value=layout.icon(item.mesh.data))

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'

#region Panels
class BANTER_PT_Configurator(bpy.types.Panel):
    bl_label = 'Avatar Configurator'
    bl_idname = 'BANTER_PT_Configurator'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = ''
    bl_category = 'BANTER'

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout

#region Armature
        col = layout.column(heading='Armature')
        col.prop(context.scene, 'banter_pArmature', text='', icon='OUTLINER_OB_ARMATURE')
        if not bpy.context.scene.banter_pArmature:
            col.operator('banter.import_armature', text='Create Default Armature', icon_value=0, emboss=True, depress=False)
#endregion
        layout.separator()
#region Local Avatar
        col = layout.column()
        col.label(text="Local Avatar")
        if bpy.context.scene.banter_cLocalAvatar and len(bpy.context.scene.banter_cLocalAvatar) > 0:
            meshrow = col.row()
            meshrow.template_list("BANTER_UL_MeshList", "", bpy.data.scenes[0], "banter_cLocalAvatar", bpy.data.scenes[0], "banter_cLocalAvatarSelectedMesh")
            meshcol = meshrow.column(align=True)
            meshcol.operator("banter.add_object_local_avatar", icon="ADD", text="")
            meshcol.operator("banter.remove_object_local_avatar", icon="REMOVE", text="")
            layout.prop(context.scene, 'banter_pLocalHeadMesh', text='Head Mesh')
        else:
            innercol = col.column(align=True)
            innercol.label(text='No Local Avatar Meshes')
            innercol.operator("banter.add_object_local_avatar", text="Use Selected Objects")
            innercol.operator('banter.dummy', text='Import RPM Avatar')
            innercol.operator('banter.dummy', text='Import Mixamo Avatar')
#endregion
        layout.separator()
#region LODs
        aLodIsMissing = False
        col = layout.row(align=True)
        col.prop(context.scene, 'banter_pLod0Avatar', text='LOD0', icon="OUTLINER_DATA_MESH")
        if not bpy.context.scene.banter_pLod0Avatar:
            col.operator('banter.dummy', icon="ADD", text="")
            aLodIsMissing = True

        col = layout.row(align=True)
        col.prop(context.scene, 'banter_pLod1Avatar', text='LOD1', icon="OUTLINER_DATA_MESH")
        if not bpy.context.scene.banter_pLod1Avatar:
            col.operator('banter.dummy', icon="ADD", text="")
            aLodIsMissing = True
        
        col = layout.row(align=True)
        col.prop(context.scene, 'banter_pLod2Avatar', text='LOD2', icon="OUTLINER_DATA_MESH")
        if not bpy.context.scene.banter_pLod2Avatar:
            col.operator('banter.dummy', icon="ADD", text="")
            aLodIsMissing = True

        col = layout.row(align=True)
        col.prop(context.scene, 'banter_pLod3Avatar', text='LOD3', icon="OUTLINER_DATA_MESH")
        if not bpy.context.scene.banter_pLod3Avatar:
            col.operator('banter.dummy', icon="ADD", text="")
            aLodIsMissing = True

        if aLodIsMissing: 
            layout.operator('banter.genmissinglods', text='Create missing remote Avatar LODs')
#endregion

class BANTER_PT_Validator(bpy.types.Panel):
    bl_label = 'Validator'
    bl_idname = 'BANTER_PT_Validator'
    bl_space_type = "VIEW_3D"
    bl_region_type = 'UI'
    bl_context = ''
    bl_category = 'BANTER'
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def draw(self, context):
        return True
    
    def draw(self, context):
        layout = self.layout

        col = layout.column(heading='', align=True)
        op = col.operator('banter.precheck', text='Recheck Requirements', icon_value=0, emboss=True, depress=False)

        if bpy.context.scene.banter_bPassed:
            col.label(text='Passed', icon_value=36)
        else:
            col = col.column(align=True)
            col.label(text='Not all checks are passing:')

            row = col.row()
            row.label(text=f'Local: {Lod.LOCAL_LIMIT}', icon_value=36 if bpy.context.scene.banter_bMeetsLocalLimit else 33,)
            if not bpy.context.scene.banter_bMeetsLocalLimit:
                pass
                # op = row.operator('banter.genlod', text='Fix')
                # op.lodLevel = -1

            row = col.row()
            row.label(text=f'LOD0: {Lod.LOD0}', icon_value=36 if bpy.context.scene.banter_bMeetsLod0 else 33)
            if not bpy.context.scene.banter_bMeetsLod0:
                op = row.operator('banter.genlod', text='Fix')
                op.lodLevel = 0

            row = col.row()
            row.label(text=f'LOD1: {Lod.LOD1}', icon_value=36 if bpy.context.scene.banter_bMeetsLod1 else 33)
            if not bpy.context.scene.banter_bMeetsLod1:
                op = row.operator('banter.genlod', text='Fix')
                op.lodLevel = 1
            
            row = col.row()
            row.label(text=f'LOD2: {Lod.LOD2}', icon_value=36 if bpy.context.scene.banter_bMeetsLod2 else 33)
            if not bpy.context.scene.banter_bMeetsLod2:
                op = row.operator('banter.genlod', text='Fix')
                op.lodLevel = 2
            
            row = col.row()
            row.label(text=f'LOD3: {Lod.LOD3}', icon_value=36 if bpy.context.scene.banter_bMeetsLod3 else 33)
            if not bpy.context.scene.banter_bMeetsLod3:
                op = row.operator('banter.genlod', text='Fix')
                op.lodLevel = 3

class BANTER_PT_Exporter(bpy.types.Panel):
    bl_label = 'Export'
    bl_idname = 'BANTER_PT_Exporter'
    bl_space_type = "VIEW_3D"
    bl_region_type = 'UI'
    bl_context = ''
    bl_category = 'BANTER'
    bl_options = {"DEFAULT_CLOSED"}
    _timer = None

    @classmethod
    def draw(self, context):
        return True
    
    def draw(self, context):
        layout = self.layout
        if(sq_api.user is None):
            col = layout.column(heading='', align=False)
            # op = col.operator('banter.login', text='(Fake Login)', icon_value=0, depress=False)
            col.label(text='To Sign In: ' , icon_value=0)
            col.label(text='Go to ' + sq_api.login_code.verification_url , icon_value=0)
            col.label(text='and put in ' + sq_api.login_code.code , icon_value=0)
            # props = bpy.context.scene.CodeProp
            # col.prop(props, "code", text=sq_api.login_code.code)
            col.label(text='Please allow up to 10s after you enter the code.' , icon_value=0)
            op = col.operator('banter.open_url', text='Open Page', icon_value=0, emboss=True, depress=False)
            op.url = "https://links.sidetestvr.com/link"
        else:
            col = layout.column(heading='', align=False)
            col.label(text='Logged in as ' + sq_api.user.name, icon_value=0)
            op = col.operator('banter.export_avatars', text='Export Avatars', icon_value=0, emboss=True, depress=False)
            op = col.operator('banter.upload_avatars', text='Export & Upload Avatars', icon_value=0, emboss=True, depress=False)
            op = col.operator('banter.logout', text='Logout', icon_value=0, emboss=True, depress=False)
#endregion

#region Operators
class Banter_OT_GenerateMissingLods(bpy.types.Operator):
    bl_idname = "banter.genmissinglods"
    bl_label = "Generate Missing LODs"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        return bpy.context.scene.banter_cLocalAvatar is not None and \
            len(bpy.context.scene.banter_cLocalAvatar) > 0 and \
            (bpy.context.scene.banter_pLod0Avatar is None or \
            bpy.context.scene.banter_pLod1Avatar is None or \
            bpy.context.scene.banter_pLod2Avatar is None or \
            bpy.context.scene.banter_pLod3Avatar is None)
    
    def execute(self, context):
        if bpy.context.scene.banter_cLocalAvatar is None:
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

    lodLevel: bpy.props.IntProperty(name='LOD Level', description='', default=0, min=-1, max=3, options={'HIDDEN'}) # type: ignore

    @classmethod
    def poll(cls, context):
        return bpy.context.scene.banter_cLocalAvatar is not None

    def execute(self, context):

        meshes = []
        for obj in bpy.context.scene.banter_cLocalAvatar:
            if obj.mesh:
                meshes.append(obj.mesh)

        targetObj = combineMeshes(meshes)
        targetObj.name = 'Avatar_LOD' + str(self.lodLevel)
        print(targetObj.name)

        lodObj = generateLOD(targetObj, intToLod(self.lodLevel), True, True if self.lodLevel == 0 else False)

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
    bl_description = "Adds selected meshes to the list of meshes that define your local avatar"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        return (obj for obj in context.selected_objects if obj.type == 'MESH')

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                item = context.scene.banter_cLocalAvatar.add()
                item.mesh = obj
        return {"FINISHED"}

class Banter_OT_RemoveObjectFromLocalAvatarList(bpy.types.Operator):
    bl_idname = "banter.remove_object_local_avatar"
    bl_label = "Remove Mesh"
    bl_description = "Removes the highlighted mesh from the list of meshes that define your local avatar"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        return context.scene.banter_cLocalAvatar and len(context.scene.banter_cLocalAvatar) > 0

    def execute(self, context):
        context.scene.banter_cLocalAvatar.remove(context.scene.banter_cLocalAvatarSelectedMesh)
        return {"FINISHED"}

class Banter_OT_OpenUrl(bpy.types.Operator):
    bl_idname = "banter.open_url"
    bl_label = "Open URL"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    url: bpy.props.StringProperty(name='URL', description='', default='') # type: ignore

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        exec('import webbrowser')
        exec(f"webbrowser.open('{self.url}')")
        return {"FINISHED"}

class Banter_OT_ImportArmature(bpy.types.Operator):
    bl_idname = "banter.import_armature"
    bl_label = "Import Banter Armature"
    bl_description = "Imports the default Banter armature"

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        script_directory = os.path.dirname(os.path.realpath(__file__))
        filepath = os.path.join(script_directory, "resources/default_bs_rig.blend")

        with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
            data_to.objects = [name for name in data_from.objects if name.startswith('BArmature')]
        
        for obj in data_to.objects:
            if obj is not None:
                bpy.context.collection.objects.link(obj)
                if not bpy.context.scene.banter_pArmature:
                    if obj.type == 'ARMATURE':
                        bpy.context.scene.banter_pArmature = obj
        
        return {'FINISHED'}

class Banter_OT_PerformPrecheck(bpy.types.Operator):
    bl_idname = "banter.precheck"
    bl_label = "Precheck"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        localCount = getObjectsPolyCount(bpy.context.scene.banter_cLocalAvatar) if bpy.context.scene.banter_cLocalAvatar else 1000000
        lod0lodLevel = getLodGroup(getMeshPolyCount(bpy.context.scene.banter_pLod0Avatar) if bpy.context.scene.banter_pLod0Avatar else 1000000)
        lod1lodLevel = getLodGroup(getMeshPolyCount(bpy.context.scene.banter_pLod1Avatar) if bpy.context.scene.banter_pLod1Avatar else 1000000)
        lod2lodLevel = getLodGroup(getMeshPolyCount(bpy.context.scene.banter_pLod2Avatar) if bpy.context.scene.banter_pLod2Avatar else 1000000)
        lod3lodLevel = getLodGroup(getMeshPolyCount(bpy.context.scene.banter_pLod3Avatar) if bpy.context.scene.banter_pLod3Avatar else 1000000)

        bpy.context.scene.banter_bMeetsLocalLimit = (localCount <= Lod.LOCAL_LIMIT)
        bpy.context.scene.banter_bMeetsLod0 = (lod0lodLevel >= 0)
        bpy.context.scene.banter_bMeetsLod1 = (lod1lodLevel >= 1)
        bpy.context.scene.banter_bMeetsLod2 = (lod2lodLevel >= 2)
        bpy.context.scene.banter_bMeetsLod3 = (lod3lodLevel >= 3)

        bpy.context.scene.banter_bPassed = \
            bpy.context.scene.banter_bMeetsLod0 and \
            bpy.context.scene.banter_bMeetsLod1 and \
            bpy.context.scene.banter_bMeetsLod2 and \
            bpy.context.scene.banter_bMeetsLod3

        # if bpy.context.scene.banter_bPassed:
        #     bpy.context.scene.banter_bPassed = (not bpy.context.scene.banter_bPassed)
        # else:
        #     bpy.context.scene.banter_bPassed = (not bpy.context.scene.banter_bPassed)
        return {"FINISHED"}

class Banter_OT_LogOut(bpy.types.Operator):
    bl_idname = "banter.logout"
    bl_label = "Log Out"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        sq_api.logout()
        return {"FINISHED"}
    
class Banter_OT_ExportAvatars(bpy.types.Operator, ExportHelper):
    bl_idname = "banter.export_avatars"
    bl_label = "Export Avatars"
    bl_description = ""
    bl_options = {"REGISTER"}

    #directory: bpy.props.StringProperty(subtype='DIR_PATH') # type: ignore
    #filename: bpy.props.StringProperty(subtype= default="banter_avatar.glb") # type: ignore
    #filepath = bpy.props.StringProperty(subtype='FILE_PATH', default="banter_avatar.glb") # type: ignore

    filter_glob: bpy.props.StringProperty(default='*.glb', options={'HIDDEN'}) # type: ignore
    filename_ext = '.glb'
    filename = "banter_avatar"

    def invoke(self, context, event):
        return ExportHelper.invoke(self, context, event)

    @classmethod
    def poll(cls, context):
        return bpy.context.scene.banter_bPassed

    def execute(self, context):        
        try:
            path, ext = os.path.splitext(self.filepath)
            highpath = self.filepath
            lowpath = path + f"_lods{ext}"

            #select elements of local avatar
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.scene.banter_pArmature.select_set(True)
            for obj in bpy.context.scene.banter_cLocalAvatar:
                if obj.mesh:
                    obj.mesh.select_set(True)

            bpy.context.scene.banter_bIsCurrentlyExporting = True
            bpy.ops.export_scene.gltf(filepath=highpath, check_existing=False, use_selection=True)
            bpy.context.scene.banter_sLocalExportPath = highpath
            bpy.context.scene.banter_bIsCurrentlyExporting = False

            print(lowpath)
            #select lods
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.scene.banter_pArmature.select_set(True)
            bpy.context.scene.banter_pLod0Avatar.select_set(True)
            bpy.context.scene.banter_pLod1Avatar.select_set(True)
            bpy.context.scene.banter_pLod2Avatar.select_set(True)
            bpy.context.scene.banter_pLod3Avatar.select_set(True)

            bpy.context.scene.banter_bIsCurrentlyExporting = True
            bpy.ops.export_scene.gltf(filepath=lowpath, check_existing=False, use_selection=True)
            bpy.context.scene.banter_sLodExportPath = lowpath
            bpy.context.scene.banter_bIsCurrentlyExporting = False
            return {"FINISHED"}
        except Exception:
            bpy.context.scene.banter_sLocalExportPath = ""
            bpy.context.scene.banter_sLodExportPath = ""
            raise Exception("Export failed")

class Banter_OT_UploadAvatars(bpy.types.Operator):
    bl_idname = "banter.upload_avatars"
    bl_label = "Upload Avatars"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return bpy.context.scene.banter_bPassed
    
    def invoke(self, context, event):
        bpy.ops.banter.export_avatars("INVOKE_DEFAULT")
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        if bpy.context.scene.banter_sLocalExportPath and bpy.context.scene.banter_sLodExportPath:
            return self.execute(context)
        return {'PASS_THROUGH'}

    def execute(self, context):
        sq_api.upload_avatars(bpy.context.scene.banter_sLocalExportPath, bpy.context.scene.banter_sLodExportPath)
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
#endregion

#region Lifecycle
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
    bpy.utils.register_class(Banter_OT_PerformPrecheck)
    bpy.utils.register_class(Banter_OT_GenerateMissingLods)
    bpy.utils.register_class(Banter_OT_GenerateMeshForLod)
    bpy.utils.register_class(Banter_OT_AddObjectToLocalAvatarList)
    bpy.utils.register_class(Banter_OT_RemoveObjectFromLocalAvatarList)

    bpy.utils.register_class(banter_avatar_collection)



    # bpy.types.Scene.CodeProp = bpy.props.PointerProperty(type=CodeProp)
    bpy.types.Scene.banter_bIsCurrentlyExporting = bpy.props.BoolProperty(name='PluginIsCurrentlyExporting', description='', default=False)

    bpy.types.Scene.banter_bPassed = bpy.props.BoolProperty(name='APassed', description='Test if the Avatar fullfils the requirements', default=False)
    # check props
    bpy.types.Scene.banter_bMeetsLocalLimit = bpy.props.BoolProperty(name='MeetsLocalLimit', description='Test if the Avatar is less than Local Limit', default=False)
    bpy.types.Scene.banter_bMeetsLod0 = bpy.props.BoolProperty(name='MeetsLod0', description='Test if the Avatar is less than LOD0', default=False)
    bpy.types.Scene.banter_bMeetsLod1 = bpy.props.BoolProperty(name='MeetsLod1', description='Test if the Avatar is less than LOD1', default=False)
    bpy.types.Scene.banter_bMeetsLod2 = bpy.props.BoolProperty(name='MeetsLod2', description='Test if the Avatar is less than LOD2', default=False)
    bpy.types.Scene.banter_bMeetsLod3 = bpy.props.BoolProperty(name='MeetsLod3', description='Test if the Avatar is less than LOD3', default=False)

    bpy.types.Scene.banter_pArmature = bpy.props.PointerProperty(name='Armature', description='', type=bpy.types.Object)
    bpy.types.Scene.banter_cLocalAvatar = bpy.props.CollectionProperty(name='LocalAvatar', description='', type=banter_avatar_collection)
    bpy.types.Scene.banter_cLocalAvatarSelectedMesh = bpy.props.IntProperty(name='LocalAvatarSelectedMesh', description='', default=0)
    bpy.types.Scene.banter_pLocalHeadMesh = bpy.props.PointerProperty(name='Local Head Mesh', description="This mesh will be hidden in Banter so your view isn't blocked", type=bpy.types.Mesh)
    bpy.types.Scene.banter_pLod0Avatar = bpy.props.PointerProperty(name='Avatar LOD0', description='Shapekeys allowed', type=bpy.types.Object)
    bpy.types.Scene.banter_pLod1Avatar = bpy.props.PointerProperty(name='Avatar LOD1', description='Shapekeys will be stripped', type=bpy.types.Object)
    bpy.types.Scene.banter_pLod2Avatar = bpy.props.PointerProperty(name='Avatar LOD2', description='Shapekeys will be stripped', type=bpy.types.Object)
    bpy.types.Scene.banter_pLod3Avatar = bpy.props.PointerProperty(name='Avatar LOD3', description='Shapekeys will be stripped', type=bpy.types.Object)

    # export props
    bpy.types.Scene.banter_sLocalExportPath = bpy.props.StringProperty(name='LocalExportPath', description='Local Export Path', default="", subtype='DIR_PATH')
    bpy.types.Scene.banter_sLodExportPath = bpy.props.StringProperty(name='LodExportPath', description='Lod Export Path', default="", subtype='DIR_PATH')

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

    del bpy.types.Scene.banter_bMeetsLocalLimit
    del bpy.types.Scene.banter_bMeetsLod0
    del bpy.types.Scene.banter_bMeetsLod1
    del bpy.types.Scene.banter_bMeetsLod2
    del bpy.types.Scene.banter_bMeetsLod3

    del bpy.types.Scene.banter_pArmature
    del bpy.types.Scene.banter_cLocalAvatar
    del bpy.types.Scene.banter_cLocalAvatarSelectedMesh
    del bpy.types.Scene.banter_pLocalHeadMesh
    del bpy.types.Scene.banter_pLod0Avatar
    del bpy.types.Scene.banter_pLod1Avatar
    del bpy.types.Scene.banter_pLod2Avatar
    del bpy.types.Scene.banter_pLod3Avatar

    del bpy.types.Scene.banter_sLocalExportPath
    del bpy.types.Scene.banter_sLodExportPath

    bpy.utils.unregister_class(banter_avatar_collection)

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
    bpy.utils.unregister_class(Banter_OT_PerformPrecheck)
    bpy.utils.unregister_class(Banter_OT_GenerateMissingLods)
    bpy.utils.unregister_class(Banter_OT_GenerateMeshForLod)
    bpy.utils.unregister_class(Banter_OT_AddObjectToLocalAvatarList)
    bpy.utils.unregister_class(Banter_OT_RemoveObjectFromLocalAvatarList)

#endregion

#region glTF Hooks
class glTF2ExportUserExtension:
    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension # type: ignore
        self.Extension = Extension
    
    def gather_asset_hook(self, gltf2_asset, export_settings):
        if bpy.context.scene.banter_bIsCurrentlyExporting:
            v = bl_info["version"]
            gltf2_asset.generator=f"Banter Avatar Creator v{v[0]}.{v[1]}.{v[2]}"
#endregion
