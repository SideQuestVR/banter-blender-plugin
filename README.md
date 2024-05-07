# Banter Avatar Creator plugin for Blender

Currently performs LOD checking and decimation from local avatar only.
LOD0 will split any mesh affected by shapekeys/blendshapes and not count towards decimation.
LOD1-3 will remove shapekeys/blendshapes and decimate the whole mesh.
This could potentially result in LOD1 having more detail than LOD0 in non-blendshape areas.

### TODO How to use (here's some WIP notes)
1. Load the plugin the usual way.
1. Import your avatar.
1. In the sidebar tray, locate the 'BANTER' tab.
1. Assign the local avatar to the slot.
1. You can then press 'Check requirements'
1. Each fix button will generate a new LOD per the requirements.
