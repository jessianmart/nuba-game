import bpy
import json
import os
import math

STAGE_JSON = r"c:\Users\jessi\Documents\antigravity\goofy-mendeleev\public\assets\stage\stage_3d.json"
ASSETS_DIR = r"c:\Users\jessi\Documents\antigravity\goofy-mendeleev\public\assets"
OUT_IMG = r"c:\Users\jessi\Documents\antigravity\goofy-mendeleev\public\assets\stage\chunin_arena_blender.png"

with open(STAGE_JSON, "r", encoding="utf-8") as f:
    stg = json.load(f)

print(f"Loaded {len(stg['meshes'])} submeshes, {stg['verts']} verts, {stg['tris']} tris")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
try:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception:
    scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.48, 0.72, 0.96, 1.0)
    bg.inputs[1].default_value = 1.0

sun_data = bpy.data.lights.new("Sun", type='SUN')
sun_data.energy = 3.2
sun_obj = bpy.data.objects.new("Sun", sun_data)
scene.collection.objects.link(sun_obj)
sun_obj.rotation_euler = (math.radians(48), math.radians(25), math.radians(30))

SCALE = 0.022
mat_cache = {}

def get_mat(tex_rel, name):
    key = (tex_rel, "dome" in name or "bac" in name)
    if key in mat_cache:
        return mat_cache[key]
    mat = bpy.data.materials.new(name=f"mat_{len(mat_cache)}")
    mat.use_nodes = True
    mat.use_backface_culling = False
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.9
    if tex_rel:
        tpath = os.path.join(ASSETS_DIR, tex_rel.replace("/", os.sep))
        if os.path.exists(tpath):
            tex_node = nodes.new("ShaderNodeTexImage")
            tex_node.image = bpy.data.images.load(tpath)
            links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
            links.new(tex_node.outputs["Alpha"], bsdf.inputs["Alpha"])
            mat.blend_method = 'CLIP' if hasattr(mat, 'blend_method') else 'OPAQUE'
    mat_cache[key] = mat
    return mat

for i, sm in enumerate(stg["meshes"]):
    pos = sm["positions"]
    tris = sm["indices"]
    uvs = sm["uvs"]
    nv = len(pos) // 3
    # Convert Three.js (x, y_up, z) -> Blender (x, -z, y_up)
    verts = [(pos[v*3]*SCALE, -pos[v*3+2]*SCALE, pos[v*3+1]*SCALE) for v in range(nv)]
    faces = [(tris[t], tris[t+1], tris[t+2]) for t in range(0, len(tris), 3) if tris[t] < nv and tris[t+1] < nv and tris[t+2] < nv]
    mesh = bpy.data.meshes.new(sm["name"])
    mesh.from_pydata(verts, [], faces)
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vi = mesh.loops[li].vertex_index
            u = uvs[vi*2] if vi*2 < len(uvs) else 0.0
            v = uvs[vi*2+1] if vi*2+1 < len(uvs) else 0.0
            if math.isnan(u) or math.isinf(u): u = 0.0
            if math.isnan(v) or math.isinf(v): v = 0.0
            uv_layer.data[li].uv = (u, 1.0 - v)
    mesh.update()
    obj = bpy.data.objects.new(sm["name"], mesh)
    scene.collection.objects.link(obj)
    obj.data.materials.append(get_mat(sm.get("texture"), sm["name"].lower()))

cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 28
cam_data.clip_end = 2000.0
cam_obj = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj
# Position camera to overlook the Chunin Arena combat floor, statue, and spectator balconies
cam_obj.location = (0.0, -70.0, 38.0)
cam_obj.rotation_euler = (math.radians(68), 0.0, 0.0)

scene.render.filepath = OUT_IMG
bpy.ops.render.render(write_still=True)
print("Rendered stage_before.png")
