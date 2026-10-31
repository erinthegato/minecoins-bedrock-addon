#!/usr/bin/env python3
"""Generates the Minecoins Bedrock addon: manifests, blocks, items, recipes,
textures (PNG) and the packaged .mcaddon. Run from the project root:
    python Minecoins/tools/gen_packs.py
"""
import json, math, os, struct, zlib, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "behavior_pack")
RP = os.path.join(ROOT, "resource_pack")

UUID_BP = "6f2d1f1c-9a3b-4b1e-8c2a-2a5f3d7b1a01"
UUID_BP_DATA = "6f2d1f1c-9a3b-4b1e-8c2a-2a5f3d7b1a02"
UUID_BP_SCRIPT = "6f2d1f1c-9a3b-4b1e-8c2a-2a5f3d7b1a03"
UUID_RP = "6f2d1f1c-9a3b-4b1e-8c2a-2a5f3d7b1a04"
UUID_RP_RES = "6f2d1f1c-9a3b-4b1e-8c2a-2a5f3d7b1a05"


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------- blocks
BLOCKS = [
    # id, texture key, map colour, hardness, light, cat
    ("power_cable", "#4a3a2c", 0.4, 0),
    ("solar_panel", "#1d3f6b", 1.2, 0),
    ("battery", "#2c3a30", 1.4, 2),
    ("cooling_unit", "#9fc4d6", 1.2, 0),
    ("server_rack", "#23252c", 1.6, 3),
    ("radio_tower", "#b03030", 1.5, 6),
    ("radio_extender", "#8a2a2a", 1.2, 4),
    ("lan_cable", "#c07a2c", 0.5, 0),
]

for name, colour, hardness, light in BLOCKS:
    write(os.path.join(BP, "blocks", f"{name}.json"), {
        "format_version": "1.21.0",
        "minecraft:block": {
            "description": {
                "identifier": f"minecoins:{name}",
                "menu_category": {"category": "construction"},
            },
            "components": {
                "minecraft:geometry": "minecraft:geometry.full_block",
                "minecraft:material_instances": {
                    "*": {
                        "texture": f"mcn_{name}",
                        "render_method": "opaque",
                        "face_dimming": True,
                        "ambient_occlusion": True,
                    }
                },
                "minecraft:destructible_by_mining": {"seconds_to_destroy": hardness},
                "minecraft:destructible_by_explosion": {"explosion_resistance": 6},
                "minecraft:map_color": colour,
                "minecraft:light_emission": light,
            },
        },
    })

# ---------------------------------------------------------------- items
write(os.path.join(BP, "items", "tablet.json"), {
    "format_version": "1.21.0",
    "minecraft:item": {
        "description": {
            "identifier": "minecoins:tablet",
            "menu_category": {"category": "equipment", "group": "itemGroup.name.miscFood"},
        },
        "components": {
            "minecraft:icon": {"textures": {"default": "mcn_tablet"}},
            "minecraft:display_name": {"value": "Minecoins Tablet"},
            "minecraft:max_stack_size": 1,
            "minecraft:hand_equipped": True,
            "minecraft:glint": True,
        },
    },
})

# ---------------------------------------------------------------- recipes
RECIPES = [
    ("power_cable", ["IRI"], {"I": "minecraft:iron_ingot", "R": "minecraft:redstone"}, 4),
    ("solar_panel", ["GGG", "QQQ", "RRR"],
     {"G": "minecraft:glass", "Q": "minecraft:quartz", "R": "minecraft:redstone"}, 1),
    ("battery", ["IRI", "RCR", "IRI"],
     {"I": "minecraft:iron_ingot", "R": "minecraft:redstone", "C": "minecraft:copper_ingot"}, 1),
    ("cooling_unit", ["IPI", "PRP", "IPI"],
     {"I": "minecraft:iron_ingot", "P": "minecraft:packed_ice", "R": "minecraft:redstone"}, 1),
    ("server_rack", ["III", "CRC", "III"],
     {"I": "minecraft:iron_ingot", "C": "minecraft:chest", "R": "minecraft:redstone"}, 1),
    ("radio_tower", [" C ", "IRI", "III"],
     {"I": "minecraft:iron_ingot", "C": "minecraft:copper_ingot", "R": "minecraft:redstone"}, 1),
    ("radio_extender", ["CRC"],
     {"C": "minecraft:copper_ingot", "R": "minecraft:redstone"}, 1),
    ("lan_cable", ["CSC", "SCS", "CSC"],
     {"C": "minecraft:copper_ingot", "S": "minecraft:string"}, 4),
    ("tablet", ["IGI", "GRG", "IRI"],
     {"I": "minecraft:iron_ingot", "G": "minecraft:glass", "R": "minecraft:redstone"}, 1),
]
for name, pattern, keys, count in RECIPES:
    write(os.path.join(BP, "recipes", f"{name}.json"), {
        "format_version": "1.20.10",
        "minecraft:recipe_shaped": {
            "description": {"identifier": f"minecoins:{name}"},
            "tags": ["crafting_table"],
            "pattern": pattern,
            "key": {k: {"item": v} for k, v in keys.items()},
            "result": {"item": f"minecoins:{name}", "count": count},
        },
    })

# ---------------------------------------------------------------- manifests
write(os.path.join(BP, "manifest.json"), {
    "format_version": 2,
    "header": {
        "name": "Minecoins Core (Behavior)",
        "description": "Minecoins, digital storage, power grid and radio network.",
        "uuid": UUID_BP,
        "version": [1, 0, 0],
        "min_engine_version": [1, 21, 70],
    },
    "modules": [
        {"type": "data", "uuid": UUID_BP_DATA, "version": [1, 0, 0]},
        {
            "type": "script",
            "language": "javascript",
            "uuid": UUID_BP_SCRIPT,
            "version": [1, 0, 0],
            "entry": "scripts/main.js",
        },
    ],
    "dependencies": [
        {"module_name": "@minecraft/server", "version": "2.0.0"},
        {"module_name": "@minecraft/server-ui", "version": "2.0.0"},
        {"uuid": UUID_RP, "version": [1, 0, 0]},
    ],
    "metadata": {"authors": ["Minecoins"], "generated_with": {"minecoins": ["1.0.0"]}},
})

write(os.path.join(RP, "manifest.json"), {
    "format_version": 2,
    "header": {
        "name": "Minecoins Core (Resources)",
        "description": "Textures for the Minecoins addon.",
        "uuid": UUID_RP,
        "version": [1, 0, 0],
        "min_engine_version": [1, 21, 70],
    },
    "modules": [{"type": "resources", "uuid": UUID_RP_RES, "version": [1, 0, 0]}],
    "dependencies": [{"uuid": UUID_BP, "version": [1, 0, 0]}],
    "metadata": {"authors": ["Minecoins"]},
})

# ---------------------------------------------------------------- textures
BLOCK_TEX = [n for n, *_ in BLOCKS]

write(os.path.join(RP, "textures", "terrain_texture.json"), {
    "resource_pack_name": "minecoins",
    "texture_name": "atlas.terrain",
    "padding": 8,
    "num_mip_levels": 4,
    "texture_data": {
        f"mcn_{n}": {"textures": f"textures/blocks/mcn_{n}"} for n in BLOCK_TEX
    },
})

write(os.path.join(RP, "textures", "item_texture.json"), {
    "resource_pack_name": "minecoins",
    "texture_name": "atlas.items",
    "texture_data": {
        "mcn_tablet": {"textures": "textures/items/mcn_tablet"},
        "mcn_minecoin": {"textures": "textures/items/mcn_minecoin"},
    },
})


def png(path, fn, size=16):
    w = h = size
    raw = b""
    for y in range(h):
        raw += b"\x00"
        for x in range(w):
            raw += bytes(fn(x, y))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        f.write(chunk(b"IEND", b""))


def border(x, y, col, w=1, size=16):
    if x < w or y < w or x >= size - w or y >= size - w:
        return col
    return None


def shade(col, d):
    return tuple(max(0, min(255, c + d)) for c in col)


def tex_power_cable(x, y):
    b = border(x, y, (22, 20, 18))
    if b:
        return (*b, 255)
    if 7 <= x <= 8 or 7 <= y <= 8:
        return (196, 126, 58, 255)
    return (52, 48, 44, 255)


def tex_solar_panel(x, y):
    b = border(x, y, (168, 178, 190), 2)
    if b:
        return (*b, 255)
    if x % 5 == 0 or y % 5 == 0:
        return (72, 118, 176, 255)
    return (24, 52, 92, 255)


def tex_battery(x, y):
    b = border(x, y, (120, 130, 120))
    if b:
        return (*b, 255)
    if x in (3, 4, 5) and 3 <= y <= 12:
        return (64, 226, 122, 255)
    if x in (10, 11, 12) and 5 <= y <= 12:
        return (44, 170, 96, 255)
    return (38, 46, 40, 255)


def tex_cooling_unit(x, y):
    b = border(x, y, (96, 120, 132))
    if b:
        return (*b, 255)
    if 4 <= x <= 11 and (y % 4 in (1, 2)):
        return (58, 74, 86, 255)
    return (172, 206, 222, 255)


def tex_server_rack(x, y):
    if x == 0 or y == 0 or x == 15 or y == 15:
        return (14, 15, 19, 255)
    if y in (3, 4, 8, 9, 12):
        return (56, 60, 72, 255)
    if (x, y) in ((2, 4), (13, 4), (2, 9), (13, 9), (6, 12)):
        return (60, 255, 150, 255)
    return (34, 36, 44, 255)


def tex_radio_tower(x, y):
    if x in (7, 8) or y in (0, 15):
        return (68, 62, 58, 255)
    if (x + y) % 6 < 3:
        return (206, 44, 44, 255)
    return (228, 226, 222, 255)


def tex_radio_extender(x, y):
    if x in (0, 15) or y in (0, 15):
        return (44, 40, 38, 255)
    d = max(abs(x - 7.5), abs(y - 7.5))
    if 3 <= d <= 4:
        return (200, 48, 48, 255)
    if d < 2:
        return (255, 190, 90, 255)
    return (70, 62, 58, 255)


def tex_lan_cable(x, y):
    if x in (0, 15) or y in (0, 15):
        return (48, 34, 18, 255)
    if 6 <= x <= 9 and 6 <= y <= 9:
        return (60, 44, 28, 255)
    return (206, 130, 46, 255)


def tex_tablet(x, y):
    if x < 2 or y < 2 or x > 13 or y > 13:
        return (0, 0, 0, 0)
    if x < 4 or y < 4 or x > 11 or y > 11:
        return (40, 44, 52, 255)
    if 1 <= y <= 2:
        return (20, 150, 200, 255)
    return (26, 178, 220, 255) if (x + y) % 7 else (150, 240, 255, 255)


def tex_minecoin(x, y):
    d = ((x - 7.5) ** 2 + (y - 7.5) ** 2) ** 0.5
    if d > 7.6:
        return (0, 0, 0, 0)
    if d > 6.2:
        return (150, 104, 20, 255)
    if d > 4.6:
        return (235, 184, 46, 255)
    if d < 2.2:
        return (120, 78, 12, 255)
    return (255, 214, 92, 255)


TEXTURES = {
    **{f"mcn_{n}": globals()[f"tex_{n}"] for n in BLOCK_TEX},
}
for n, fn in TEXTURES.items():
    png(os.path.join(RP, "textures", "blocks", f"{n}.png"), fn)

ITEM_TEXTURES = {"mcn_tablet": tex_tablet, "mcn_minecoin": tex_minecoin}
for n, fn in ITEM_TEXTURES.items():
    png(os.path.join(RP, "textures", "items", f"{n}.png"), fn)

# ---------------------------------------------------------------- pack icon
ICON = 128


def icon_pixel(x, y):
    s = ICON - 1
    cx = cy = s / 2
    m = 14

    # rounded corners
    qx, qy = min(x, s - x), min(y, s - y)
    if qx < m and qy < m and (qx - m) ** 2 + (qy - m) ** 2 > m * m:
        return (0, 0, 0, 0)

    def shade(col, d):
        return tuple(max(0, min(255, c + d)) for c in col)

    # dark gradient panel with a faint circuit grid
    t = y / s
    base = (int(20 + 18 * t), int(27 + 24 * t), int(40 + 34 * t))
    if x % 16 == 0 or y % 16 == 0:
        base = shade(base, 5)
    bg = (*base, 255)

    # radio waves, top-right
    ax, ay = 100, 28
    ar = math.hypot(x - ax, y - ay)
    ang = math.atan2(y - ay, x - ax)
    if (19 <= ar <= 22 or 28 <= ar <= 31) and 1.65 <= ang <= 2.95:
        return (92, 234, 240, 255)

    # minecoin
    dx, dy = x - cx, y - cy
    r = math.hypot(dx, dy)
    if r <= 35:
        if r > 32:
            return (108, 74, 14, 255)
        if r > 28:
            return (240, 194, 62, 255)
        if r > 25:
            return (180, 130, 22, 255)
        d = abs(dx) + abs(dy)
        if d <= 12:
            return (255, 234, 154, 255) if d <= 6 else (146, 100, 16, 255)
        return (218, 168, 38, 255) if (dy < 0) else (200, 150, 28, 255)

    # LED nodes
    for nx, ny in ((22, 100), (36, 100), (100, 100), (110, 84)):
        if abs(x - nx) <= 3 and abs(y - ny) <= 3:
            return (60, 255, 160, 255)
    if (abs(y - 100) <= 1 and 22 <= x <= 110) or (abs(x - 100) <= 1 and 28 <= y <= 100):
        return (58, 62, 78, 255)

    return bg


png(os.path.join(BP, "pack_icon.png"), icon_pixel, ICON)
png(os.path.join(RP, "pack_icon.png"), icon_pixel, ICON)

# ---------------------------------------------------------------- packaging
def zip_pack(out, folders):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, src in folders:
            for base, _dirs, files in os.walk(src):
                for f in files:
                    full = os.path.join(base, f)
                    rel = os.path.relpath(full, src)
                    z.write(full, os.path.join(arc, rel))


zip_pack(os.path.join(ROOT, "Minecoins_BP.mcpack"), [("", BP)])
zip_pack(os.path.join(ROOT, "Minecoins_RP.mcpack"), [("", RP)])
zip_pack(os.path.join(ROOT, "Minecoins.mcaddon"), [("Minecoins_BP", BP), ("Minecoins_RP", RP)])
print("generated:", ROOT)
