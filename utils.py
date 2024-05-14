from enum import IntEnum
import bpy

# LOCAL_LIMIT = 120000
# LOD0 = 30000
# LOD1 = 15000
# LOD2 = 5000
# LOD3 = 500

class Lod(IntEnum):
    LOD3 = 1500
    LOD2 = 5000
    LOD1 = 15000
    LOD0 = 30000

    LOCAL_LIMIT = 120000

def intToLod(lod: int) -> Lod:
    if lod == 0:
        return Lod.LOD0
    if lod == 1:
        return Lod.LOD1
    if lod == 2:
        return Lod.LOD2
    if lod == 3:
        return Lod.LOD3
    return Lod.LOD3

def getLodGroup(polygonCount: int):
    if polygonCount > Lod.LOD0:
        return -1
    if polygonCount > Lod.LOD1:
        return 0
    if polygonCount > Lod.LOD2:
        return 1
    if polygonCount > Lod.LOD3:
        return 2
    return 3

def getScenePolyCount(scene: bpy.types.Scene):
    # bpy.ops.object.mode_set(mode='EDIT')
    # bpy.ops.mesh.select_all(action='SELECT')  
    # bpy.ops.mesh.quads_convert_to_tris()
    # bpy.ops.object.mode_set(mode='OBJECT') 

    return sum(getMeshPolyCount(obj) for obj in scene.objects)

def getMeshPolyCount(obj: bpy.types.Object):
    if obj.type == 'MESH':
        return len(obj.data.polygons)
    return 0

def seperateShapeKeyMesh(obj: bpy.types.Object) -> bpy.types.Object:
    if obj and obj.type == 'MESH' and obj.data.shape_keys:
        mesh = obj.data
        shape_keys = mesh.shape_keys.key_blocks

        # Get the reference shape key (Basis usually) vertex coordinates
        basis_key = shape_keys[0].data

        # Initialize a list to store influenced vertices
        influenced_vertices = set()

        # Loop through each shape key
        for key in shape_keys[1:]:  # Start from 1 to skip the Basis shape key
            for i, vert in enumerate(key.data):
                # Check if the vertex position in this shape key differs from the Basis
                if vert.co != basis_key[i].co:
                    influenced_vertices.add(i)

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')

        for poly in mesh.polygons:  # Iterate over all polygons
            for idx in poly.vertices:  # Check each vertex in the polygon
                if idx in influenced_vertices:
                    poly.select = True  # Select the polygon if any vertex is influenced
                    break

        # Switch to edit mode and face select mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.context.tool_settings.mesh_select_mode = (False, False, True)  # Enable face selection mode

        # Grow the selection to include adjacent faces
        bpy.ops.mesh.select_more()

        org_obj_list = {searchObj.name for searchObj in bpy.context.selected_objects}
        # Separate the selected faces into a new object
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')

        # Find the newly created object which is the separated part with blendshapes

        for findObj in bpy.context.selected_objects:
            if findObj and findObj.name in org_obj_list:
                # Deselect selected object
                findObj.select_set(False)
            else:
                # Set the new created object to active
                bpy.context.view_layer.objects.active = findObj

        shapeKeyObj = bpy.context.view_layer.objects.active
        shapeKeyObj.name += "_blendshapes"

        return shapeKeyObj
    else:
        print("No active mesh with shape keys found.")
        return None
    
def combineMeshes(objList: list):
    bpy.ops.object.select_all(action='DESELECT')
    
    copylist = []
    for obj in objList:
        newObj = obj.copy()
        newObj.data = obj.data.copy()
        ## UV layers will NOT join unless they have the same name
        for layer in newObj.data.uv_layers:
            layer.name = "UV0"
        copylist.append(newObj)
        bpy.context.collection.objects.link(newObj)
    
    for obj in copylist:
        obj.select_set(True)

    bpy.context.view_layer.objects.active = copylist[0]
    bpy.ops.object.join()

    mod = bpy.context.view_layer.objects.active.modifiers.new(name="Triangulate", type='TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=mod.name)

    return bpy.context.view_layer.objects.active

def generateLOD(sampleObj: bpy.types.Object, lodLevel: Lod, overwrite = False, preserveShapeKeys: bool = False):
    # Get current triangle count
    sampleObj.update_from_editmode()
    current_triangles = getMeshPolyCount(sampleObj)

    targetPolyCount = lodLevel.value

    # Duplicate the object
    if overwrite:
        newLodObject = sampleObj
    else:
        newLodObject = sampleObj.copy()
        newLodObject.data = sampleObj.data.copy()
        bpy.context.collection.objects.link(newLodObject)

    if current_triangles > targetPolyCount:

        bpy.context.view_layer.objects.active = newLodObject

        # Preserve and seperate shape keys
        shapeKeyObj = None
        if newLodObject.data.shape_keys:
            if preserveShapeKeys:
                shapeKeyObj = seperateShapeKeyMesh(newLodObject)

            bpy.ops.object.select_all(action='DESELECT')
            newLodObject.select_set(True)
            bpy.context.view_layer.objects.active = newLodObject
            bpy.ops.object.shape_key_remove(all=True)

        # Apply decimation
        mod = newLodObject.modifiers.new(name="Decimate" + lodLevel.name, type='DECIMATE')

        # if shape keys, remove the shape key count from the target count
        if shapeKeyObj:
            shapeKeyCount = getMeshPolyCount(shapeKeyObj)
            targetPolyCount -= shapeKeyCount

        ratio = targetPolyCount / current_triangles
        mod.ratio = ratio
        bpy.context.view_layer.objects.active = newLodObject
        bpy.ops.object.modifier_apply(modifier=mod.name)

        if shapeKeyObj:
            bpy.context.view_layer.objects.active = newLodObject
            newLodObject.select_set(True)
            shapeKeyObj.select_set(True)
            bpy.ops.object.join()

    return newLodObject
