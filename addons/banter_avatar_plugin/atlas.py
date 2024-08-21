import bpy


def bakeAtlas(obj: bpy.types.Object):
    # Set render engine to Cycles
    if bpy.context.scene.render.engine != "CYCLES":
        bpy.context.scene.render.engine = "CYCLES"

    # Set render samples to 4
    bpy.context.scene.cycles.samples = 4

    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")

    # Set the active object
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Create and select a new UV map
    if obj.type == "MESH":
        uv_map_name = "AtlasUV"
        uv_map = None
        if uv_map_name not in obj.data.uv_layers:
            uv_map = obj.data.uv_layers.new(name=uv_map_name)
        else:
            uv_map = obj.data.uv_layers.get(uv_map_name)
        uv_map.active = True

    # Ensure we are in edit mode to access UV operations
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")

    # Temporarily switch one of the areas to an Image Editor with UV mode for packing
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            old_type = area.type
            area.type = "IMAGE_EDITOR"
            area.spaces.active.mode = "UV"

            # Select all UVs in the UV editor
            bpy.ops.uv.select_all(action="SELECT")

            # Pack UV islands with detailed settings
            bpy.ops.uv.pack_islands(
                udim_source="CLOSEST_UDIM",
                rotate=True,
                rotate_method="ANY",
                scale=True,
                merge_overlap=False,
                margin_method="SCALED",
                margin=0.001,
                pin=False,
                pin_method="LOCKED",
                shape_method="CONCAVE",
            )

            # Restore the area type back to the original
            area.type = old_type
            break

    # Return to object mode
    bpy.ops.object.mode_set(mode="OBJECT")

    # Create a new texture and assign it to all material slots
    texture_name = "AvatarLOD"
    image = bpy.data.images.new(texture_name, width=1024, height=1024)

    # Ensure correct name tracked
    texture_name = image.name

    # Add a new named texture node specifically for baking and assign it to all materials
    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if mat:
            # Add a new image texture node named specifically for the bake process
            node_tree = mat.node_tree
            tex_image = node_tree.nodes.new(type="ShaderNodeTexImage")
            tex_image.image = image
            tex_image.name = "BakeTexImage"
            node_tree.nodes.active = tex_image

    # Set bake settings
    bpy.context.scene.cycles.bake_type = "DIFFUSE"
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    bpy.context.scene.render.bake.margin = 512

    # Perform the baking operation
    bpy.ops.object.bake(type="DIFFUSE")

    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if mat and mat.node_tree:
            # Remove only the texture nodes created for baking (named "BakeTexImage")
            for node in mat.node_tree.nodes:
                if node.name == "BakeTexImage":
                    mat.node_tree.nodes.remove(node)

    # Remove all materials from the object
    obj.data.materials.clear()

    # Create a new material with the baked texture
    new_mat = bpy.data.materials.new(name="AvatarLODMat")
    new_mat.use_nodes = True
    bsdf = new_mat.node_tree.nodes.get("Principled BSDF")

    # Add the baked image texture node
    tex_image = new_mat.node_tree.nodes.new(type="ShaderNodeTexImage")
    tex_image.image = bpy.data.images.get(texture_name)

    # Connect the texture node to the BSDF shader's Base Color input
    new_mat.node_tree.links.new(bsdf.inputs["Base Color"], tex_image.outputs["Color"])

    # Assign the new material to the object
    obj.data.materials.append(new_mat)

    # Remove all UV maps except for the "AtlasUV"
    uv_layers = obj.data.uv_layers
    existing_uv_maps = [uv_map.name for uv_map in uv_layers]
    if uv_map_name in existing_uv_maps:
        for uv_map in existing_uv_maps:
            if uv_map != uv_map_name and uv_map in uv_layers:
                uv_layers.remove(uv_layers[uv_map])

    print("Baking and cleanup completed.")
