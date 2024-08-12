from enum import IntEnum
import bmesh
import bpy

class Lod(IntEnum):
    LOD3 = 1000
    LOD2 = 5000
    LOD1 = 15000
    LOD0 = 30000

    LOCAL_LIMIT = 120000

    @staticmethod
    def intToLod(lod: int) -> 'Lod':
        if lod == 0:
            return Lod.LOD0
        if lod == 1:
            return Lod.LOD1
        if lod == 2:
            return Lod.LOD2
        if lod == 3:
            return Lod.LOD3
        return Lod.LOD3

    @staticmethod
    def getLodGroup(polygonCount: int) -> int:
        if polygonCount > Lod.LOD0:
            return -1
        if polygonCount > Lod.LOD1:
            return 0
        if polygonCount > Lod.LOD2:
            return 1
        if polygonCount > Lod.LOD3:
            return 2
        return 3

def getSceneTriCount(scene: bpy.types.Scene) -> int:
    return sum(getMeshTriCount(obj.data) for obj in scene.objects if obj.type == 'MESH')

def getMeshTriCount(mesh: bpy.types.Mesh) -> int:
    total = 0
    for face in mesh.polygons:
        verts = face.vertices
        total += len(verts) - 2
    return total

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
    
def combineObjects(objList: list[bpy.types.Object]) -> bpy.types.Object:
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

    return bpy.context.view_layer.objects.active

def generateLOD(sampleObj: bpy.types.Object, lodLevel: Lod, overwrite = False, preserveShapeKeys: bool = False) -> bpy.types.Object:
    # Get current triangle count
    sampleObj.update_from_editmode()
    current_triangles = getMeshTriCount(sampleObj.data)

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
            bpy.context.object.active_shape_key_index = 0
            bpy.ops.object.shape_key_remove(all=True)

        # if shape keys, remove the shape key count from the target count
        if shapeKeyObj:
            shapeKeyCount = getMeshTriCount(shapeKeyObj.data)
            targetPolyCount -= shapeKeyCount

        bpy.context.view_layer.objects.active = newLodObject

        # Merge close vertices
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        match lodLevel:
            case Lod.LOD1:
                bpy.ops.mesh.remove_doubles(threshold=0.005)
            case Lod.LOD2:
                bpy.ops.mesh.remove_doubles(threshold=0.0075)
        bpy.ops.object.mode_set(mode='OBJECT')

        # Triangulate
        mod = newLodObject.modifiers.new(name="Triangulate", type='TRIANGULATE')
        bpy.ops.object.modifier_apply(modifier=mod.name)

        # Refresh count after removing shape keys and triangulation
        current_triangles = getMeshTriCount(newLodObject.data)

        match lodLevel:
            case Lod.LOD0 | Lod.LOD1 | Lod.LOD2:
                # Decimate
                mod = newLodObject.modifiers.new(name="Decimate" + lodLevel.name, type='DECIMATE')
                mod.ratio = targetPolyCount / current_triangles
                bpy.ops.object.modifier_apply(modifier=mod.name)
            case Lod.LOD3:
                # Decimate to Lod2, then weld
                mod = newLodObject.modifiers.new(name="Decimate" + lodLevel.name, type='DECIMATE')
                mod.ratio = Lod.LOD2 / current_triangles
                bpy.ops.object.modifier_apply(modifier=mod.name)
                # Weld
                merge_threshold = 0.0
                while getMeshTriCount(newLodObject.data) > targetPolyCount:
                    merge_threshold += 0.005
                    mod = newLodObject.modifiers.new(name="Weld", type='WELD')
                    mod.merge_threshold = merge_threshold
                    bpy.ops.object.modifier_apply(modifier=mod.name)

        # Merge shape keys back
        if shapeKeyObj:
            bpy.context.view_layer.objects.active = newLodObject
            newLodObject.select_set(True)
            shapeKeyObj.select_set(True)
            bpy.ops.object.join()

        # Clean up
        bm = bmesh.new()
        bm.from_mesh(newLodObject.data)
        vertices_to_remove = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=vertices_to_remove, context='VERTS')
        bm.to_mesh(newLodObject.data)
        bm.free()
        newLodObject.data.update()

    return newLodObject
