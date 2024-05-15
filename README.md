# Banter Avatar Creator plugin for Blender

Currently performs LOD checking and decimation from local avatar.
LOD0 will split any mesh affected by shapekeys/blendshapes and not count towards decimation.
LOD1-3 will remove shapekeys/blendshapes and decimate the whole mesh.
This could potentially result in LOD1 having more detail than LOD0 in non-blendshape areas.

### TODO How to use (here's some WIP notes)
1. Load the plugin the usual way.
1. In the sidebar tray, locate the 'BANTER' tab.
1. Assign the local armature to the slot, or generate a new one.
1. Assign your avatar's meshes to the local avatar section, by selecting the objects and pressing 'Use Selected Objects'
1. Assign or generate LODs of your avatar.
1. You can then press 'Check requirements'
1. If required, each fix button will generate a new LOD per the requirements.
