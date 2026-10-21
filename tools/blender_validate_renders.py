import json
import math
import os
import bpy
from mathutils import Euler, Matrix, Vector

OUT_IMG = r"C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch\blender_validation.png"
os.makedirs(os.path.dirname(OUT_IMG), exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def compute_posed_vertices(model_data, pose_rots, pelvis_dy=0.0):
    """
    Exact Linear Blend Skinning (LBS) matching THREE.SkinnedMesh:
    v' = sum_k w_k * (M_world[b_k] * M_bind_inv[b_k] * v_bind)
    where all coordinates are in 0..5.4m normalized space (scale = 1.0).
    Look: Three.js is (X right, Y up, Z forward).
    We compute LBS in Three.js space first, then convert to Blender (X, -Z, Y) for rendering!
    """
    bones = model_data["bones"]
    nb = len(bones)

    # 1. Bind matrices in Three.js world space
    bind_world = [Matrix.Identity(4) for _ in range(nb)]
    bind_inv = [Matrix.Identity(4) for _ in range(nb)]
    for i, b in enumerate(bones):
        bind_world[i] = Matrix.Translation(Vector(b["pos"]))
        bind_inv[i] = bind_world[i].inverted()

    # 2. Local offsets from parent in bind pose
    local_pos = []
    for i, b in enumerate(bones):
        p = b["parent"]
        if p >= 0:
            local_pos.append(Vector(b["pos"]) - Vector(bones[p]["pos"]))
        else:
            local_pos.append(Vector(b["pos"]))

    # 3. Posed world matrices in Three.js space
    posed_world = [Matrix.Identity(4) for _ in range(nb)]
    for i, b in enumerate(bones):
        p = b["parent"]
        lp = local_pos[i].copy()
        if i == 1:
            lp.y += pelvis_dy
        rx, ry, rz = pose_rots.get(i, (0.0, 0.0, 0.0))
        # Three.js default Euler order is 'XYZ'
        rot_mat = Euler((rx, ry, rz), "XYZ").to_matrix().to_4x4()
        loc_mat = Matrix.Translation(lp) @ rot_mat
        if p >= 0:
            posed_world[i] = posed_world[p] @ loc_mat
        else:
            posed_world[i] = loc_mat

    skin_mats = [posed_world[i] @ bind_inv[i] for i in range(nb)]
    return skin_mats, posed_world


def build_character_in_blender(cid, x_offset, z_offset, pose_name, pose_rots, pelvis_dy=0.0):
    path = os.path.join("public", "assets", "models", f"{cid}.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    skin_mats, _ = compute_posed_vertices(data, pose_rots, pelvis_dy)

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
            # Convert Three.js Y-up (x, y, z) -> Blender Z-up (x + x_offset, -z + z_offset, y)
            verts_bl.append((v_out.x + x_offset, -v_out.z + z_offset, v_out.y))

        faces = []
        for i in range(0, len(indices), 3):
            i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]
            if i0 != i1 and i1 != i2 and i0 != i2:
                faces.append((i0, i1, i2))

        mesh_data = bpy.data.meshes.new(f"{cid}_{pose_name}_{sm_idx}")
        mesh_data.from_pydata(verts_bl, [], faces)
        mesh_data.update()

        # UV layer (flip V for Blender bottom-left vs NUCC top-left)
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
                mat.use_nodes = True
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


def main():
    clear_scene()

    # Define the exact poses from game.js animateCharacterRig
    pose_idle = {
        2: (0.06, 0.0, 0.0),
        3: (0.05, -0.10, 0.0),
        5: (0.0, 0.08, 0.0),
        7: (-0.22, 0.0, -0.46),
        11: (-0.16, 0.0, 0.46),
        8: (-0.58, 0.0, 0.0),
        12: (-0.52, 0.0, 0.0),
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
        7: (0.92, 0.0, -0.32),
        11: (0.92, 0.0, 0.32),
        8: (-0.28, 0.0, 0.0),
        12: (-0.28, 0.0, 0.0),
        14: (0.68, 0.0, 0.0),
        15: (0.85, 0.0, 0.0),
        17: (-0.68, 0.0, 0.0),
        18: (0.22, 0.0, 0.0),
    }

    pose_jutsu = {
        2: (0.30, 0.0, 0.0),
        3: (0.22, -0.24, 0.0),
        5: (-0.28, 0.15, 0.0),
        7: (-1.10, -0.30, -0.25),
        11: (-1.28, 0.30, 0.20),
        8: (-0.42, 0.0, 0.0),
        12: (-0.32, 0.0, 0.0),
        14: (-0.62, 0.0, 0.0),
        15: (0.72, 0.0, 0.0),
        17: (0.50, 0.0, 0.0),
        18: (0.30, 0.0, 0.0),
    }

    pose_attack = {
        2: (0.20, 0.42, 0.0),
        3: (0.10, 0.28, 0.0),
        5: (0.0, -0.32, 0.0),
        7: (-1.35, 0.0, -0.15),
        11: (-0.35, 0.0, 0.35),
        8: (-0.20, 0.0, 0.0),
        12: (-0.85, 0.0, 0.0),
        14: (-0.35, 0.0, 0.0),
        15: (0.45, 0.0, 0.0),
        17: (0.35, 0.0, 0.0),
        18: (0.45, 0.0, 0.0),
    }

    # Build 5 characters across different poses in Blender 5.2
    build_character_in_blender("1nrt", -9.0, 0.0, "idle", pose_idle, pelvis_dy=-0.04)
    build_character_in_blender("1nrt", -4.5, 0.0, "run", pose_run, pelvis_dy=-0.12)
    build_character_in_blender("1ssk",  0.0, 0.0, "jutsu", pose_jutsu, pelvis_dy=-0.16)
    build_character_in_blender("1kks",  4.5, 0.0, "attack", pose_attack, pelvis_dy=-0.10)
    build_character_in_blender("1jry",  9.0, 0.0, "idle", pose_idle, pelvis_dy=-0.04)

    # Add Floor Pedestal Plane
    bpy.ops.mesh.primitive_plane_add(size=28.0, location=(0.0, 0.0, 0.0))

    # Add Sun Light
    light_data = bpy.data.lights.new(name="SunLight", type="SUN")
    light_data.energy = 3.8
    light_obj = bpy.data.objects.new(name="SunLight", object_data=light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.rotation_euler = (math.radians(50), math.radians(15), math.radians(25))

    # Add Fill Light
    fill_data = bpy.data.lights.new(name="FillLight", type="SUN")
    fill_data.energy = 1.8
    fill_obj = bpy.data.objects.new(name="FillLight", object_data=fill_data)
    bpy.context.collection.objects.link(fill_obj)
    fill_obj.rotation_euler = (math.radians(75), 0.0, math.radians(-140))

    # Add Camera looking at the 5 posed characters
    cam_data = bpy.data.cameras.new(name="ValCam")
    cam_data.lens = 35
    cam_obj = bpy.data.objects.new(name="ValCam", object_data=cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = (0.0, -17.5, 3.6)
    cam_obj.rotation_euler = (math.radians(84), 0.0, 0.0)
    bpy.context.scene.camera = cam_obj

    # Render settings
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 620
    scene.render.filepath = OUT_IMG
    bpy.ops.render.render(write_still=True)
    print("Saved Blender validation render to", OUT_IMG)


if __name__ == "__main__":
    main()
