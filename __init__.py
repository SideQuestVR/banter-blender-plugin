bl_info = {
    "name" : "Banter Avatar Creator",
    "author" : "SideQuest", 
    "description" : "",
    "blender" : (3, 0, 0),
    "version" : (1, 0, 0),
    "location" : "View3D > Sidebar > BANTER",
    "warning" : "",
    "doc_url": "", 
    "tracker_url": "", 
    "category" : "3D View" 
}

from typing import Set
import bpy
from bpy.types import Context
import bpy.utils.previews
from .utils import generateLOD, getMeshPolyCount, intToLod, getLodGroup, Lod

addon_keymaps = {}
_icons = None

class BANTER_PT_Root(bpy.types.Panel):
    bl_label = 'Avatar Creator'
    bl_idname = 'BANTER_PT_Root'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = ''
    bl_category = 'BANTER'
    bl_order = 0
    bl_ui_units_x = 0

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout

#region credentials
        if not bpy.context.scene.banter_bLoggedIn:
            box = layout.box()
            box.alert = False
            box.enabled = True
            box.active = True
            box.use_property_split = False
            box.use_property_decorate = False
            box.alignment = 'EXPAND'
            box.scale_x = 1.0
            box.scale_y = 1.0
            col = box.column(heading='', align=False)
            col.alert = True
            col.enabled = True
            col.active = True
            col.use_property_split = False
            col.use_property_decorate = False
            col.scale_x = 1.0
            col.scale_y = 2.0
            col.alignment = 'EXPAND'
            col.operator_context = "INVOKE_DEFAULT"
            op = col.operator('banter.open_url', text='Link to My Sidequest', icon_value=0, emboss=True, depress=False)
            op = col.operator('banter.login', text='(Fake Login)', icon_value=0, depress=False)
            box.label(text='Link Code: ' + bpy.context.scene.banter_sLoginCode, icon_value=0)
            col = box.column(heading='', align=False)
            row = col.row(heading='', align=False)
        else:
            col = layout.column(heading='', align=False)
            col.alert = False
            col.enabled = True
            col.active = True
            col.use_property_split = False
            col.use_property_decorate = False
            col.scale_x = 1.0
            col.scale_y = 1.0
            col.alignment = 'EXPAND'
            col.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"

            box = col.box()
            box.alert = False
            box.enabled = True
            box.active = True
            box.use_property_split = False
            box.use_property_decorate = False
            box.alignment = 'EXPAND'
            box.scale_x = 1.0
            box.scale_y = 1.0
            box.label(text='Logged in as ' + bpy.context.scene.banter_sUsername, icon_value=0)
            op = box.operator('banter.login', text='Logout', icon_value=0, emboss=True, depress=False)
#endregion
            

            box = col.box()
            box.label(text='Avatar Versions', icon_value=0)
            prop = box.prop(context.scene, 'banter_pLocalAvatar', text='Local Avatar')
            if bpy.context.scene.banter_pLocalAvatar:
                op = box.operator('banter.dummy', text='Remove Head', icon_value=0, emboss=True, depress=False)
            else:
                op = box.operator('banter.dummy', text='Create Local Avatar', icon_value=0, emboss=True, depress=False)
                box.alert = False
                box.enabled = True
                box.active = True
                box.use_property_split = False
                box.use_property_decorate = False
                box.alignment = 'EXPAND'
                box.scale_x = 1.0
                box.scale_y = 1.0
                box.label(text='Import Avatar:', icon_value=0)
                op = box.operator('banter.dummy', text='Load Base Armature', icon_value=0, emboss=True, depress=False)
                op = box.operator('banter.dummy', text='Import RPM Avatar', icon_value=0, emboss=True, depress=False)
                op = box.operator('banter.dummy', text='Import Mixamo Avatar', icon_value=0, emboss=True, depress=False)

            prop = box.prop(context.scene, 'banter_pLod0Avatar', text='Lod0')
            if not bpy.context.scene.banter_pLod0Avatar:
                op = box.operator('banter.dummy', text='Create Lod0', icon_value=0, emboss=True, depress=False)

            prop = box.prop(context.scene, 'banter_pLod1Avatar', text='Lod1')
            if not bpy.context.scene.banter_pLod1Avatar:
                op = box.operator('banter.dummy', text='Create Lod1', icon_value=0, emboss=True, depress=False)
            
            prop = box.prop(context.scene, 'banter_pLod2Avatar', text='Lod2')
            if not bpy.context.scene.banter_pLod2Avatar:
                op = box.operator('banter.dummy', text='Create Lod2', icon_value=0, emboss=True, depress=False)

            prop = box.prop(context.scene, 'banter_pLod3Avatar', text='Lod3')
            if not bpy.context.scene.banter_pLod3Avatar:
                op = box.operator('banter.dummy', text='Create Lod3', icon_value=0, emboss=True, depress=False)

            op = box.operator('banter.dummy', text='Create missing remote Avatar LODs', icon_value=0, emboss=True, depress=False)

            box = col.box()
            box.alert = False
            box.enabled = True
            box.active = True
            box.use_property_split = False
            box.use_property_decorate = False
            box.alignment = 'EXPAND'
            box.scale_x = 1.0
            box.scale_y = 1.0

            col = box.column(heading='', align=True)
            col.alert = False
            col.enabled = True
            col.active = True
            col.use_property_split = False
            col.use_property_decorate = False
            col.scale_x = 1.0
            col.scale_y = 1.0
            col.alignment = 'EXPAND'
            col.operator_context = "INVOKE_DEFAULT"
            op = col.operator('banter.precheck', text='Recheck Requirements', icon_value=0, emboss=True, depress=False)

            if bpy.context.scene.banter_bPassed:
                col.label(text='Passed', icon_value=36)
            else:
                col = col.column(align=True)
                col.alert = False
                col.enabled = True
                col.active = True
                col.use_property_split = False
                col.use_property_decorate = False
                col.scale_x = 1.0
                col.scale_y = 1.0
                col.alignment = 'EXPAND'
                col.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"

                col.label(text='Not all checks are passing:')

                row = col.row()
                row.label(text=f'Local: {Lod.LOCAL_LIMIT}', icon_value=36 if bpy.context.scene.banter_bMeetsLocalLimit else 33)
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

            col = box.column(heading='', align=False)
            col.alert = True
            col.enabled = bpy.context.scene.banter_bPassed
            col.active = bpy.context.scene.banter_bPassed
            col.use_property_split = False
            col.use_property_decorate = False
            col.scale_x = 1.0
            col.scale_y = 2.0
            col.alignment = 'EXPAND'
            col.operator_context = "INVOKE_DEFAULT"
            op = col.operator('banter.dummy', text='Upload Avatar', icon_value=0, emboss=True, depress=False)

class Banter_OT_GenerateMeshForLod(bpy.types.Operator):
    bl_idname = "banter.genlod"
    bl_label = "Generate Mesh for LOD"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    lodLevel: bpy.props.IntProperty(name='LOD Level', description='', default=0, min=-1, max=3, options={'HIDDEN'}) # type: ignore

    @classmethod
    def poll(cls, context):
        return bpy.context.scene.banter_pLocalAvatar is not None

    def execute(self, context):
        print(intToLod(self.lodLevel))

        generateLOD(bpy.context.scene.banter_pLocalAvatar, intToLod(self.lodLevel), True if self.lodLevel == 0 else False)
        return {"FINISHED"}
    

class Banter_OT_OpenUrl(bpy.types.Operator):
    bl_idname = "banter.open_url"
    bl_label = "Open URL"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        exec('import webbrowser')
        exec("webbrowser.open('https://sidequestvr.com/link-sidequest')")
        return {"FINISHED"}



class Banter_OT_UploadToSideQuest(bpy.types.Operator):
    bl_idname = "banter.upload"
    bl_label = "Upload"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        if bpy.context.scene.banter_bPassed:
            op = layout.operator('sn.dummy_button_operator', text='Export and Upload', icon_value=0, emboss=True, depress=False)
        else:
            row = layout.row(heading='', align=False)
            row.alert = True
            row.enabled = True
            row.active = True
            row.use_property_split = False
            row.use_property_decorate = False
            row.scale_x = 1.0
            row.scale_y = 1.0
            row.alignment = 'EXPAND'
            row.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
            row.label(text='ERROR:' + 'Trangles above 30k on remote Avatar' + 'Local Avatar looks like crap', icon_value=0)

    def invoke(self, context, event):
        context.window_manager.invoke_props_popup(self, event)
        return self.execute(context)

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
        localCount = getMeshPolyCount(bpy.context.scene.banter_pLocalAvatar) if bpy.context.scene.banter_pLocalAvatar else 1000000
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

    
class Banter_OT_LogIn(bpy.types.Operator):
    bl_idname = "banter.login"
    bl_label = "Log In"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        if bpy.context.scene.banter_bLoggedIn:
            bpy.context.scene.banter_bLoggedIn = (not bpy.context.scene.banter_bLoggedIn)
        else:
            bpy.context.scene.banter_bLoggedIn = (not bpy.context.scene.banter_bLoggedIn)
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


def register():
    global _icons
    _icons = bpy.utils.previews.new()
    bpy.types.Scene.banter_sLoginCode = bpy.props.StringProperty(name='6erCode', description='', default='XXXXXX', subtype='NONE', maxlen=0)
    bpy.types.Scene.banter_bLoggedIn = bpy.props.BoolProperty(name='LoggedIn', description='', default=True)
    bpy.types.Scene.banter_sUsername = bpy.props.StringProperty(name='UserName', description='', default='Ehleen', subtype='NONE', maxlen=0)

    bpy.types.Scene.banter_bPassed = bpy.props.BoolProperty(name='APassed', description='Test if the Avatar fullfils the requirements', default=False)
    # check props
    bpy.types.Scene.banter_bMeetsLocalLimit = bpy.props.BoolProperty(name='MeetsLocalLimit', description='Test if the Avatar is less than Local Limit', default=False)
    bpy.types.Scene.banter_bMeetsLod0 = bpy.props.BoolProperty(name='MeetsLod0', description='Test if the Avatar is less than LOD0', default=False)
    bpy.types.Scene.banter_bMeetsLod1 = bpy.props.BoolProperty(name='MeetsLod1', description='Test if the Avatar is less than LOD1', default=False)
    bpy.types.Scene.banter_bMeetsLod2 = bpy.props.BoolProperty(name='MeetsLod2', description='Test if the Avatar is less than LOD2', default=False)
    bpy.types.Scene.banter_bMeetsLod3 = bpy.props.BoolProperty(name='MeetsLod3', description='Test if the Avatar is less than LOD3', default=False)

    bpy.types.Scene.banter_pLocalAvatar = bpy.props.PointerProperty(name='LocalAvatar', description='', type=bpy.types.Object)
    bpy.types.Scene.banter_pLod0Avatar = bpy.props.PointerProperty(name='Lod0Avatar', description='', type=bpy.types.Object)
    bpy.types.Scene.banter_pLod1Avatar = bpy.props.PointerProperty(name='Lod1Avatar', description='', type=bpy.types.Object)
    bpy.types.Scene.banter_pLod2Avatar = bpy.props.PointerProperty(name='Lod2Avatar', description='', type=bpy.types.Object)
    bpy.types.Scene.banter_pLod3Avatar = bpy.props.PointerProperty(name='Lod3Avatar', description='', type=bpy.types.Object)

    bpy.utils.register_class(BANTER_PT_Root)

    bpy.utils.register_class(Banter_OT_Dummy)
    bpy.utils.register_class(Banter_OT_LogIn)
    bpy.utils.register_class(Banter_OT_OpenUrl)
    bpy.utils.register_class(Banter_OT_UploadToSideQuest)
    bpy.utils.register_class(Banter_OT_PerformPrecheck)
    bpy.utils.register_class(Banter_OT_GenerateMeshForLod)

def unregister():
    global _icons
    bpy.utils.previews.remove(_icons)
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    for km, kmi in addon_keymaps.values():
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    del bpy.types.Scene.banter_sUsername
    del bpy.types.Scene.banter_bLoggedIn
    del bpy.types.Scene.banter_sLoginCode


    del bpy.types.Scene.banter_bPassed

    del bpy.types.Scene.banter_bMeetsLocalLimit
    del bpy.types.Scene.banter_bMeetsLod0
    del bpy.types.Scene.banter_bMeetsLod1
    del bpy.types.Scene.banter_bMeetsLod2
    del bpy.types.Scene.banter_bMeetsLod3

    del bpy.types.Scene.banter_pLocalAvatar
    del bpy.types.Scene.banter_pLod0Avatar
    del bpy.types.Scene.banter_pLod1Avatar
    del bpy.types.Scene.banter_pLod2Avatar
    del bpy.types.Scene.banter_pLod3Avatar

    bpy.utils.unregister_class(BANTER_PT_Root)

    bpy.utils.unregister_class(Banter_OT_Dummy)
    bpy.utils.unregister_class(Banter_OT_LogIn)
    bpy.utils.unregister_class(Banter_OT_OpenUrl)
    bpy.utils.unregister_class(Banter_OT_UploadToSideQuest)
    bpy.utils.unregister_class(Banter_OT_PerformPrecheck)
    bpy.utils.unregister_class(Banter_OT_GenerateMeshForLod)
