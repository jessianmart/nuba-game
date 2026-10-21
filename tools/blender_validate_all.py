import bpy
import json
import os
import math
from mathutils import Vector, Quaternion, Matrix

STAGE_JSON = r"c:\Users\jessi\Documents\antigravity\goofy-mendeleev\public\assets\stage\stage_3d.json"
MODELS_DIR = r"c:\Users\jessi\Documents\antigravity\goofy-mendeleev\public\assets\models"
ANMS_JSON = r"c:\Users\jessi\Documents\antigravity\goofy-mendeleev\public\assets\data\animations.json"
ASSETS_DIR = r"c:\Users\jessi\Documents\antigravity\goofy-mendeleev\public\assets"
OUT_STAGE_IMG = r"C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch\stage_after.png"
OUT_ANM_IMG = r"C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch\databook_and_anms_validation.png"


def setup_scene(res_x=1280, res_y=720):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y

    world = bpy.data.worlds.new("World")
    scene.world = world
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.45, 0.72, 0.96, 1.0)
        bg.inputs[1].default_value = 1.1

    sun_data = bpy.data.lights.new("Sun", type='SUN')
    sun_data.energy = 3.4
    sun_obj = bpy.data.objects.new("Sun", sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(48), math.radians(22), math.radians(28))
    return scene


def render_fixed_stage():
    scene = setup_scene(1360, 768)
    with open(STAGE_JSON, "r", encoding="utf-8") as f:
        stg = json.load(f)

    SCALE = 0.022
    mat_cache = {}

    def get_mat(tex_rel, name):
        is_river = "river" in name
        key = (tex_rel, is_river)
        if key in mat_cache:
            return mat_cache[key]
        mat = bpy.data.materials.new(name=f"smat_{len(mat_cache)}")
        mat.use_backface_culling = False
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        bsdf = nodes.get("Principled BSDF")
        bsdf.inputs["Roughness"].default_value = 0.65 if is_river else 0.85
        if tex_rel:
            tpath = os.path.join(ASSETS_DIR, tex_rel.replace("/", os.sep))
            if os.path.exists(tpath):
                tex_node = nodes.new("ShaderNodeTexImage")
                tex_node.image = bpy.data.images.load(tpath)
                links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
                if not is_river:
                    links.new(tex_node.outputs["Alpha"], bsdf.inputs["Alpha"])
        mat_cache[key] = mat
        return mat

    for sm in stg["meshes"]:
        pos = sm["positions"]
        tris = sm["indices"]
        uvs = sm["uvs"]
        nv = len(pos) // 3
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
    cam_data.lens = 26
    cam_data.clip_end = 2000.0
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    cam_obj.location = (0.0, -72.0, 52.0)
    cam_obj.rotation_euler = (math.radians(54), 0.0, 0.0)

    scene.render.filepath = OUT_STAGE_IMG
    bpy.ops.render.render(write_still=True)
    print("Rendered stage_after.png")


def pose_vertex_threejs(vx, vy, vz, si, sw, j_bind, w_pos, w_rot):
    rx, ry, rz = 0.0, 0.0, 0.0
    for k in range(4):
        w = sw[k]
        if w <= 0.0001:
            continue
        b = si[k]
        jb = j_bind.get(b, (0.0, 0.0, 0.0))
        jp = w_pos.get(b, (0.0, 0.0, 0.0))
        q = w_rot.get(b, Quaternion((1.0, 0.0, 0.0, 0.0)))
        dv = Vector((vx - jb[0], vy - jb[1], vz - jb[2]))
        rv = q @ dv
        rx += w * (jp[0] + rv.x)
        ry += w * (jp[1] + rv.y)
        rz += w * (jp[2] + rv.z)
    return (rx, ry, rz)


def render_databook_and_animations():
    scene = setup_scene(1600, 720)
    with open(ANMS_JSON, "r", encoding="utf-8") as f:
        anms = json.load(f)

    # Floor reference grid plane
    bpy.ops.mesh.primitive_plane_add(size=60.0, location=(0.0, 0.0, 0.0))
    fl_mat = bpy.data.materials.new("FloorMat")
    fl_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.14, 0.19, 0.26, 1.0)
    bpy.context.active_object.data.materials.append(fl_mat)

    # Showcase 6 characters with different heights AND authentic extracted APK animations:
    # (cid, x_offset, clip_name, frame_fraction)
    showcase = [
        ("1nrt", -10.5, "jutsu", 0.55),   # Naruto (147.5cm / 4.92m) - Rasengan Strike!
        ("1ssk",  -6.3, "attack", 0.45),  # Sasuke (153.2cm / 5.11m) - Uchiha Combo!
        ("1roc",  -2.1, "attack2", 0.50), # Rock Lee (162.1cm / 5.40m) - Konoha High Kick!
        ("1itc",   2.1, "idle", 0.20),    # Itachi (175.2cm / 5.84m) - Akatsuki Stance
        ("1kks",   6.3, "jutsu", 0.50),   # Kakashi (181.0cm / 6.03m) - Raikiri Charge!
        ("1jry",  10.5, "idle", 0.0),     # Jiraiya (191.2cm / 6.37m) - Towering Sannin!
    ]

    mat_cache = {}
    for cid, x_off, clip_key, frac in showcase:
        with open(os.path.join(MODELS_DIR, f"{cid}.json"), "r", encoding="utf-8") as mf:
            mdata = json.load(mf)

        bones_meta = mdata["bones"]
        j_bind = {i: tuple(bones_meta[i]["pos"]) for i in range(len(bones_meta))}
        parents_cb = {i: bones_meta[i]["parent"] for i in range(len(bones_meta))}

        clip = anms.get(cid, {}).get(clip_key) or anms.get(cid, {}).get("idle")
        nf = clip["numFrames"]
        fi = min(nf - 1, max(0, int(round(frac * (nf - 1)))))

        # Evaluate 20-bone Three.js FK at frame fi
        w_pos = {0: (0.0, 0.0, 0.0)}
        w_rot = {0: Quaternion((1.0, 0.0, 0.0, 0.0))}
        p_off = clip["pelvisPos"][fi]
        w_pos[1] = (j_bind[1][0] + p_off[0], p_off[1], j_bind[1][2] + p_off[2])
        q1 = clip["bones"]["1"][fi]  # [qx, qy, qz, qw]
        w_rot[1] = Quaternion((q1[3], q1[0], q1[1], q1[2]))

        for cb in range(2, 20):
            p_cb = parents_cb[cb]
            q_arr = clip["bones"][str(cb)][fi]
            qloc = Quaternion((q_arr[3], q_arr[0], q_arr[1], q_arr[2]))
            rel_b = Vector((
                j_bind[cb][0] - j_bind[p_cb][0],
                j_bind[cb][1] - j_bind[p_cb][1],
                j_bind[cb][2] - j_bind[p_cb][2],
            ))
            r_rel = w_rot[p_cb] @ rel_b
            w_pos[cb] = (w_pos[p_cb][0] + r_rel.x, w_pos[p_cb][1] + r_rel.y, w_pos[p_cb][2] + r_rel.z)
            w_rot[cb] = w_rot[p_cb] @ qloc

        for sm_i, sm in enumerate(mdata["meshes"]):
            pos = sm["positions"]
            tris = sm["indices"]
            uvs = sm["uvs"]
            si = sm["skinIndices"]
            sw = sm["skinWeights"]
            nv = len(pos) // 3
            verts = []
            for v in range(nv):
                px, py, pz = pose_vertex_threejs(
                    pos[v*3], pos[v*3+1], pos[v*3+2],
                    si[v*4:(v+1)*4], sw[v*4:(v+1)*4],
                    j_bind, w_pos, w_rot
                )
                # Three.js (x, y_up, z_fwd) -> Blender (x + x_off, -z_fwd, y_up)
                verts.append((px + x_off, -pz, py))
            faces = [(tris[t], tris[t+1], tris[t+2]) for t in range(0, len(tris), 3)]
            mesh = bpy.data.meshes.new(f"{cid}_{sm_i}")
            mesh.from_pydata(verts, [], faces)
            uv_layer = mesh.uv_layers.new(name="UVMap")
            for poly in mesh.polygons:
                for li in poly.loop_indices:
                    vi = mesh.loops[li].vertex_index
                    uv_layer.data[li].uv = (uvs[vi*2], 1.0 - uvs[vi*2+1])
            mesh.update()
            obj = bpy.data.objects.new(f"{cid}_{sm_i}", mesh)
            scene.collection.objects.link(obj)
            tex_rel = sm.get("texture")
            if tex_rel:
                if tex_rel not in mat_cache:
                    mat = bpy.data.materials.new(name=f"cmat_{len(mat_cache)}")
                    mat.use_backface_culling = False
                    bsdf = mat.node_tree.nodes["Principled BSDF"]
                    bsdf.inputs["Roughness"].default_value = 0.85
                    tpath = os.path.join(ASSETS_DIR, tex_rel.replace("/", os.sep))
                    if os.path.exists(tpath):
                        tn = mat.node_tree.nodes.new("ShaderNodeTexImage")
                        tn.image = bpy.data.images.load(tpath)
                        mat.node_tree.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
                    mat_cache[tex_rel] = mat
                obj.data.materials.append(mat_cache[tex_rel])

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 30
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    cam_obj.location = (0.0, -25.0, 3.4)
    cam_obj.rotation_euler = (math.radians(87), 0.0, 0.0)

    scene.render.filepath = OUT_ANM_IMG
    bpy.ops.render.render(write_still=True)
    print("Rendered databook_and_anms_validation.png")


if __name__ == "__main__":
    render_fixed_stage()
    render_databook_and_animations()
