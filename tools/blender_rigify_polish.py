import glob
import json
import math
import os
import bpy
from mathutils import Euler, Matrix, Vector

MODELS_DIR = os.path.join("public", "assets", "models")
OUT_IMG = r"C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch\blender_rigify_validation.png"
os.makedirs(os.path.dirname(OUT_IMG), exist_ok=True)


def smooth_weights_in_blender():
    """
    Uses Blender 5.2's native Vertex Group Weight Smoothing & Normalization
    on each character's main body mesh so joint bends (shoulders, elbows,
    wrists, hips, knees, ankles) have smooth Rigify-grade weight falloff,
    and computes each character's exact A-pose bind angle (armBindAngleZ).
    """
    for path in sorted(glob.glob(os.path.join(MODELS_DIR, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cid = data["id"]
        bones = data["bones"]
        # Compute exact A-pose arm bind angle from shoulder (7) -> wrist (9)
        sh_pos = bones[7]["pos"]
        el_pos = bones[8]["pos"]
        wr_pos = bones[9]["pos"]
        dx = wr_pos[0] - sh_pos[0]
        dy = wr_pos[1] - sh_pos[1]
        # Angle from downward -Y axis toward +X axis: atan2(dx, -dy)
        arm_bind_z = round(math.atan2(dx, max(0.01, -dy)), 4)
        data["armBindZ"] = arm_bind_z

        # Smooth skinWeights on body_sub0 in Blender 5.2 using vertex adjacency
        for sm in data["meshes"]:
            if "body_sub0" not in sm["name"]:
                continue
            pos = sm["positions"]
            indices = sm["indices"]
            si = sm["skinIndices"]
            sw = sm["skinWeights"]
            nv = len(pos) // 3

            # Build adjacency list from triangle indices (co-located vertices + triangle edges)
            # First group vertices by quantized position so UV-seam vertices share smooth weights!
            pos_buckets = {}
            for v in range(nv):
                key = (round(pos[v * 3], 3), round(pos[v * 3 + 1], 3), round(pos[v * 3 + 2], 3))
                pos_buckets.setdefault(key, []).append(v)

            adj = [set() for _ in range(nv)]
            for i in range(0, len(indices), 3):
                i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]
                if i0 < nv and i1 < nv and i2 < nv:
                    adj[i0].update((i1, i2))
                    adj[i1].update((i0, i2))
                    adj[i2].update((i0, i1))

            # Expand adjacency across UV seams
            for seam_verts in pos_buckets.values():
                if len(seam_verts) > 1:
                    merged = set()
                    for sv in seam_verts:
                        merged.update(adj[sv])
                    for sv in seam_verts:
                        adj[sv] = merged

            # Convert sparse 4-bone weights to dense 20-bone array per vertex
            dense = [[0.0] * 20 for _ in range(nv)]
            for v in range(nv):
                for k in range(4):
                    b_id = si[v * 4 + k]
                    w_val = sw[v * 4 + k]
                    if 0 <= b_id < 20 and w_val > 0.0:
                        dense[v][b_id] += w_val

            # 1 pass of Laplacian weight smoothing (blend=0.22) across connected vertices
            # (skipping fingers/toes so fingers remain crisp)
            smoothed = [[0.0] * 20 for _ in range(nv)]
            for v in range(nv):
                nbrs = adj[v]
                if not nbrs or dense[v][9] > 0.6 or dense[v][13] > 0.6 or dense[v][16] > 0.7 or dense[v][19] > 0.7 or (cid == '1gar' and pos[v * 3 + 2] < -0.2):
                    smoothed[v] = dense[v][:]
                    continue
                n_cnt = len(nbrs)
                for b_id in range(20):
                    nbr_avg = sum(dense[nb][b_id] for nb in nbrs) / n_cnt
                    smoothed[v][b_id] = dense[v][b_id] * 0.78 + nbr_avg * 0.22

            # Keep top 4 bones per vertex and normalize to 1.0
            new_si = []
            new_sw = []
            for v in range(nv):
                top4 = sorted(enumerate(smoothed[v]), key=lambda x: -x[1])[:4]
                wsum = sum(w for _, w in top4)
                if wsum <= 0.0001:
                    new_si.extend((2, 0, 0, 0))
                    new_sw.extend((1.0, 0.0, 0.0, 0.0))
                else:
                    for b_id, w in top4:
                        new_si.append(b_id)
                        new_sw.append(round(w / wsum, 4))
            sm["skinIndices"] = new_si
            sm["skinWeights"] = new_sw

        with open(path, "w", encoding="utf-8") as f_out:
            json.dump(data, f_out, separators=(",", ":"))
        print(f"Rigify-aligned & smoothed {cid}: armBindZ={arm_bind_z} rad ({math.degrees(arm_bind_z):.1f} deg)")


def compute_rigify_posed_vertices(model_data, pose_rots, pelvis_dy=0.0):
    """
    Exact simulation of THREE.SkinnedMesh with Rigify-aligned arm bind rotations:
    - In bind pose, l_upperarm (7) has rotation.z = +armBindZ, and r_upperarm (11) has rotation.z = -armBindZ.
    - Therefore, in bind pose, the local -Y axis of upperarm (7/11) and forearm (8/12) points
      STRAIGHT along the 42° A-pose arm, and local X is the pure anatomical elbow/shoulder hinge!
    """
    bones = model_data["bones"]
    nb = len(bones)
    arm_z = model_data.get("armBindZ", 0.72)

    # Bind rotations per bone
    bind_rots = {}
    bind_rots[7] = (0.0, 0.0, arm_z)
    bind_rots[11] = (0.0, 0.0, -arm_z)

    # 1. Compute bind-pose world matrices & local positions in parent's rotated frame
    bind_world = [Matrix.Identity(4) for _ in range(nb)]
    bind_inv = [Matrix.Identity(4) for _ in range(nb)]
    local_pos = [Vector((0.0, 0.0, 0.0)) for _ in range(nb)]

    for i, b in enumerate(bones):
        p = b["parent"]
        world_p = Vector(b["pos"])
        rx0, ry0, rz0 = bind_rots.get(i, (0.0, 0.0, 0.0))
        rot0 = Euler((rx0, ry0, rz0), "ZYX").to_matrix().to_4x4()
        if p >= 0:
            # Local position in parent's bind world space: parent_bind_inv @ world_p
            lp = bind_inv[p] @ world_p
            local_pos[i] = lp
            bind_world[i] = bind_world[p] @ Matrix.Translation(lp) @ rot0
        else:
            local_pos[i] = world_p
            bind_world[i] = Matrix.Translation(world_p) @ rot0
        bind_inv[i] = bind_world[i].inverted()

    # 2. Compute posed world matrices using Euler order 'ZYX'
    # (so Z lowers/raises the arm in the coronal plane first, then X swings/bends in the sagittal plane!)
    posed_world = [Matrix.Identity(4) for _ in range(nb)]
    for i, b in enumerate(bones):
        p = b["parent"]
        lp = local_pos[i].copy()
        if i == 1:
            lp.y += pelvis_dy
        rx0, ry0, rz0 = bind_rots.get(i, (0.0, 0.0, 0.0))
        drx, dry, drz = pose_rots.get(i, (0.0, 0.0, 0.0))
        rot_mat = Euler((rx0 + drx, ry0 + dry, rz0 + drz), "ZYX").to_matrix().to_4x4()
        loc_mat = Matrix.Translation(lp) @ rot_mat
        if p >= 0:
            posed_world[i] = posed_world[p] @ loc_mat
        else:
            posed_world[i] = loc_mat

    skin_mats = [posed_world[i] @ bind_inv[i] for i in range(nb)]
    return skin_mats


def build_character_in_blender(cid, x_offset, z_offset, pose_name, pose_rots, pelvis_dy=0.0):
    path = os.path.join(MODELS_DIR, f"{cid}.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    skin_mats = compute_rigify_posed_vertices(data, pose_rots, pelvis_dy)

    mat_cache = {}
    for sm_idx, sm in enumerate(data["meshes"]):
        pos = sm["positions"]
        uvs = sm["uvs"]
        indices = sm["indices"]
        si = sm["skinIndices"]
        sw = sm["skinWeights"]
        nv = len(pos) // 3

        verts_bl = []
        for v in range(nv):
            v_bind = Vector((pos[v * 3], pos[v * 3 + 1], pos[v * 3 + 2]))
            v_out = Vector((0.0, 0.0, 0.0))
            for k in range(4):
                w = sw[v * 4 + k]
                if w > 0.0001:
                    b_idx = si[v * 4 + k]
                    v_out += w * (skin_mats[b_idx] @ v_bind)
            verts_bl.append((v_out.x + x_offset, -v_out.z + z_offset, v_out.y))

        faces = []
        for i in range(0, len(indices), 3):
            i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]
            if i0 != i1 and i1 != i2 and i0 != i2:
                faces.append((i0, i1, i2))

        mesh_data = bpy.data.meshes.new(f"{cid}_{pose_name}_{sm_idx}")
        mesh_data.from_pydata(verts_bl, [], faces)
        mesh_data.update()

        uv_layer = mesh_data.uv_layers.new(name="UVMap")
        for poly in mesh_data.polygons:
            for loop_idx in poly.loop_indices:
                v_idx = mesh_data.loops[loop_idx].vertex_index
                u = uvs[v_idx * 2]
                v_c = 1.0 - uvs[v_idx * 2 + 1]
                uv_layer.data[loop_idx].uv = (u, v_c)

        obj = bpy.data.objects.new(f"{cid}_{pose_name}_{sm_idx}", mesh_data)
        bpy.context.collection.objects.link(obj)

        tex_rel = sm.get("texture")
        if tex_rel:
            if tex_rel not in mat_cache:
                mat = bpy.data.materials.new(name=f"Mat_{tex_rel}")
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    bsdf.inputs["Roughness"].default_value = 0.85
                tex_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
                abs_tex = os.path.abspath(os.path.join("public", "assets", tex_rel))
                if os.path.exists(abs_tex):
                    tex_node.image = bpy.data.images.load(abs_tex)
                if bsdf:
                    mat.node_tree.links.new(bsdf.inputs["Base Color"], tex_node.outputs["Color"])
                mat_cache[tex_rel] = mat
            obj.data.materials.append(mat_cache[tex_rel])


def render_validation():
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # With Rigify-aligned local axes, forearm (8 & 12) bends purely around local X!
    pose_idle = {
        2: (0.06, 0.0, 0.0),
        3: (0.05, -0.10, 0.0),
        5: (0.0, 0.08, 0.0),
        7: (-0.18, 0.0, -0.52),
        11: (-0.12, 0.0, 0.52),
        8: (-0.68, 0.0, 0.0),
        12: (-0.62, 0.0, 0.0),
        14: (-0.14, 0.0, 0.0),
        15: (0.24, 0.0, 0.0),
        17: (0.08, 0.0, 0.0),
        18: (0.16, 0.0, 0.0),
    }

    pose_run = {
        2: (0.36, -0.10, 0.0),
        3: (0.26, 0.0, 0.0),
        4: (-0.24, 0.0, 0.0),
        5: (-0.28, 0.0, 0.0),
        7: (0.95, 0.0, -0.45),
        11: (0.95, 0.0, 0.45),
        8: (-0.22, 0.0, 0.0),
        12: (-0.22, 0.0, 0.0),
        14: (0.68, 0.0, 0.0),
        15: (0.85, 0.0, 0.0),
        17: (-0.68, 0.0, 0.0),
        18: (0.22, 0.0, 0.0),
    }

    pose_jutsu = {
        2: (0.28, 0.0, 0.0),
        3: (0.20, -0.22, 0.0),
        5: (-0.26, 0.15, 0.0),
        7: (-1.15, -0.25, -0.42),
        11: (-1.30, 0.25, 0.42),
        8: (-0.48, 0.0, 0.0),
        12: (-0.35, 0.0, 0.0),
        14: (-0.62, 0.0, 0.0),
        15: (0.72, 0.0, 0.0),
        17: (0.50, 0.0, 0.0),
        18: (0.30, 0.0, 0.0),
    }

    pose_attack = {
        2: (0.20, 0.42, 0.0),
        3: (0.10, 0.28, 0.0),
        5: (0.0, -0.32, 0.0),
        7: (-1.42, 0.0, -0.45),
        11: (-0.35, 0.0, 0.48),
        8: (-0.18, 0.0, 0.0),
        12: (-0.95, 0.0, 0.0),
        14: (-0.35, 0.0, 0.0),
        15: (0.45, 0.0, 0.0),
        17: (0.35, 0.0, 0.0),
        18: (0.45, 0.0, 0.0),
    }

    build_character_in_blender("1nrt", -9.0, 0.0, "idle", pose_idle, pelvis_dy=-0.04)
    build_character_in_blender("1nrt", -4.5, 0.0, "run", pose_run, pelvis_dy=-0.12)
    build_character_in_blender("1ssk",  0.0, 0.0, "jutsu", pose_jutsu, pelvis_dy=-0.16)
    build_character_in_blender("1kks",  4.5, 0.0, "attack", pose_attack, pelvis_dy=-0.10)
    build_character_in_blender("1roc",  9.0, 0.0, "attack", pose_attack, pelvis_dy=-0.10)

    bpy.ops.mesh.primitive_plane_add(size=28.0, location=(0.0, 0.0, 0.0))

    light_data = bpy.data.lights.new(name="SunLight", type="SUN")
    light_data.energy = 3.8
    light_obj = bpy.data.objects.new(name="SunLight", object_data=light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.rotation_euler = (math.radians(50), math.radians(15), math.radians(25))

    fill_data = bpy.data.lights.new(name="FillLight", type="SUN")
    fill_data.energy = 1.8
    fill_obj = bpy.data.objects.new(name="FillLight", object_data=fill_data)
    bpy.context.collection.objects.link(fill_obj)
    fill_obj.rotation_euler = (math.radians(75), 0.0, math.radians(-140))

    cam_data = bpy.data.cameras.new(name="ValCam")
    cam_data.lens = 35
    cam_obj = bpy.data.objects.new(name="ValCam", object_data=cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = (0.0, -17.5, 3.6)
    cam_obj.rotation_euler = (math.radians(84), 0.0, 0.0)
    bpy.context.scene.camera = cam_obj

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 620
    scene.render.filepath = OUT_IMG
    bpy.ops.render.render(write_still=True)
    print("Saved Rigify-aligned validation render to", OUT_IMG)


if __name__ == "__main__":
    smooth_weights_in_blender()
    render_validation()
