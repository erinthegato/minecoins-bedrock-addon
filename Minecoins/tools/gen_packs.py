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
VERSION = [1, 4, 0]


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
    ("monitor", "#2f3540", 1.0, 5),
]

HALF_BLOCKS = {"battery", "cooling_unit"}
FLAT_BLOCKS = {"solar_panel"}
PIPE_BLOCKS = {"power_cable", "lan_cable"}
CARDINALS = ["north", "south", "east", "west"]
PIPE_DIRECTIONS = [
    ("north", (0, 0, -1), 1),
    ("south", (0, 0, 1), 2),
    ("east", (1, 0, 0), 4),
    ("west", (-1, 0, 0), 8),
]


def cube(origin, size):
    """Cube with explicit per-face UVs; box UV walks off a 16x16 texture on
    flat/thin shapes and leaves the top face blank."""
    uv = [0, 0]
    return {
        "origin": origin,
        "size": size,
        "uv": {
            "up": {"uv": uv, "uv_size": [size[0], size[2]]},
            "down": {"uv": uv, "uv_size": [size[0], size[2]]},
            "north": {"uv": uv, "uv_size": [size[0], size[1]]},
            "south": {"uv": uv, "uv_size": [size[0], size[1]]},
            "east": {"uv": uv, "uv_size": [size[2], size[1]]},
            "west": {"uv": uv, "uv_size": [size[2], size[1]]},
        },
    }


def rack_box(direction):
    """Freestanding rack: full height, centred on the block space on both
    horizontal axes, so it never hugs a wall. Direction still selects the front
    face, so every cardinal variant shares this box."""
    return {"origin": [-6, 0, -6], "size": [12, 16, 12]}


def monitor_box(direction):
    """Item-frame style wall monitor: a 14x14 panel, 1px deep."""
    if direction == "south":
        return {"origin": [-7, 1, 7], "size": [14, 14, 1]}
    if direction == "east":
        return {"origin": [7, 1, -7], "size": [1, 14, 14]}
    if direction == "west":
        return {"origin": [-8, 1, -7], "size": [1, 14, 14]}
    return {"origin": [-7, 1, -8], "size": [14, 14, 1]}


def pipe_cubes(mask):
    """Fence-style pipe: centre post plus an arm per connected side."""
    cubes = [cube([-2, 0, -2], [4, 16, 4])]
    if mask & 1:
        cubes.append(cube([-2, 6, -8], [4, 4, 6]))
    if mask & 2:
        cubes.append(cube([-2, 6, 2], [4, 4, 6]))
    if mask & 4:
        cubes.append(cube([2, 6, -2], [6, 4, 4]))
    if mask & 8:
        cubes.append(cube([-8, 6, -2], [6, 4, 4]))
    return cubes


for name, colour, hardness, light in BLOCKS:
    description = {
        "identifier": f"minecoins:{name}",
        "menu_category": {"category": "construction"},
    }
    components = {
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
    }
    permutations = None
    if name in HALF_BLOCKS:
        # supporting hardware: half-height model and half-block hitbox
        components["minecraft:geometry"] = f"geometry.mcn_{name}"
        components["minecraft:collision_box"] = {"origin": [-8, 0, -8], "size": [16, 8, 16]}
        components["minecraft:selection_box"] = {"origin": [-8, 0, -8], "size": [16, 8, 16]}
    elif name == "server_rack":
        # full-height cabinet, centred in the block and rotated for its front face
        description["traits"] = {
            "minecraft:placement_direction": {
                "enabled_states": ["minecraft:cardinal_direction"],
                "y_rotation_offset": 180,
            }
        }
        components["minecraft:geometry"] = "geometry.mcn_server_rack_north"
        components["minecraft:collision_box"] = rack_box("north")
        components["minecraft:selection_box"] = rack_box("north")
        permutations = [
            {
                "condition": f"q.block_state('minecraft:cardinal_direction') == '{d}'",
                "components": {
                    "minecraft:geometry": f"geometry.mcn_server_rack_{d}",
                    "minecraft:collision_box": rack_box(d),
                    "minecraft:selection_box": rack_box(d),
                },
            }
            for d in CARDINALS
        ]
    elif name == "monitor":
        # wall terminal: item-frame style panel rotated to the wall it is on
        description["traits"] = {
            "minecraft:placement_direction": {
                "enabled_states": ["minecraft:cardinal_direction"],
                "y_rotation_offset": 180,
            }
        }
        components["minecraft:geometry"] = "geometry.mcn_monitor_north"
        components["minecraft:collision_box"] = monitor_box("north")
        components["minecraft:selection_box"] = monitor_box("north")
        permutations = [
            {
                "condition": f"q.block_state('minecraft:cardinal_direction') == '{d}'",
                "components": {
                    "minecraft:geometry": f"geometry.mcn_monitor_{d}",
                    "minecraft:collision_box": monitor_box(d),
                    "minecraft:selection_box": monitor_box(d),
                },
            }
            for d in CARDINALS
        ]
    elif name in FLAT_BLOCKS:
        # leaf-litter style plate: placeable flat, 1px collision
        components["minecraft:geometry"] = f"geometry.mcn_{name}"
        components["minecraft:collision_box"] = {"origin": [-8, 0, -8], "size": [16, 1, 16]}
        components["minecraft:selection_box"] = {"origin": [-8, 0, -8], "size": [16, 2, 16]}
    elif name in PIPE_BLOCKS:
        description["states"] = {
            f"minecoins:{d}": [False, True] for d, _o, _b in PIPE_DIRECTIONS
        }
        components["minecraft:geometry"] = "geometry.mcn_power_cable_0"
        components["minecraft:collision_box"] = {"origin": [-2, 0, -2], "size": [4, 16, 4]}
        components["minecraft:selection_box"] = {"origin": [-2, 0, -2], "size": [4, 16, 4]}
        permutations = []
        for mask in range(16):
            condition = " and ".join(
                f"q.block_state('minecoins:{d}') == {'true' if mask & bit else 'false'}"
                for d, _o, bit in PIPE_DIRECTIONS
            )
            permutations.append({
                "condition": condition,
                "components": {"minecraft:geometry": f"geometry.mcn_power_cable_{mask}"},
            })
    else:
        components["minecraft:geometry"] = "minecraft:geometry.full_block"

    block_def = {"description": description, "components": components}
    if permutations:
        block_def["permutations"] = permutations
    write(os.path.join(BP, "blocks", f"{name}.json"), {
        "format_version": "1.21.0",
        "minecraft:block": block_def,
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

# ---------------------------------------------------------------- guide book
write(os.path.join(BP, "items", "guidebook.json"), {
    "format_version": "1.21.0",
    "minecraft:item": {
        "description": {
            "identifier": "minecoins:guidebook",
            "menu_category": {"category": "items"},
        },
        "components": {
            "minecraft:icon": {"textures": {"default": "mcn_guidebook"}},
            "minecraft:display_name": {"value": "Minecoins Guide"},
            "minecraft:max_stack_size": 1,
        },
    },
})

write(os.path.join(BP, "recipes", "guidebook.json"), {
    "format_version": "1.20.10",
    "minecraft:recipe_shapeless": {
        "description": {"identifier": "minecoins:guidebook"},
        "tags": ["crafting_table"],
        "ingredients": [
            {"item": "minecraft:book"},
            {"item": "minecraft:redstone"},
            {"item": "minecraft:glass"},
        ],
        "result": {"item": "minecoins:guidebook", "count": 1},
    },
})

# ----------------------------------------------------- creative item catalog
# menu_category alone is not enough for every block shape: stateful blocks can be
# skipped by the creative menu. The catalog lists every block explicitly in one
# collapsible group. The guide book is listed twice on purpose - the user wants
# it reachable from both the Items and the Equipment tab.
CATALOG_GROUP = "minecoins:itemGroup.name.infrastructure"
GUIDE_GROUP = "minecoins:itemGroup.name.guide"


def group(icon, name, items):
    return {
        "group_identifier": {"icon": icon, "name": name},
        "items": items,
    }


write(os.path.join(BP, "item_catalog", "crafting_item_catalog.json"), {
    "format_version": "1.21.0",
    "minecraft:crafting_items_catalog": {
        "categories": [
            {
                "category_name": "construction",
                "groups": [group(CATALOG_GROUP, CATALOG_GROUP,
                                 [f"minecoins:{n}" for n, *_ in BLOCKS])],
            },
            {
                "category_name": "items",
                "groups": [group("minecoins:guidebook", GUIDE_GROUP,
                                 ["minecoins:guidebook"])],
            },
            {
                "category_name": "equipment",
                "groups": [group("minecoins:guidebook", GUIDE_GROUP,
                                 ["minecoins:guidebook"])],
            },
        ],
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
    ("monitor", ["IGI", "GRG", "IGI"],
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

# ---------------------------------------------------------------- models
def geo(identifier, cubes):
    return {
        "description": {
            "identifier": identifier,
            "texture_width": 16,
            "texture_height": 16,
            "visible_bounds_width": 2,
            "visible_bounds_height": 1.5,
            "visible_bounds_offset": [0, 0.5, 0],
        },
        "bones": [{"name": "block", "pivot": [0, 0, 0], "cubes": cubes}],
    }


MODELS = []
for name in ("battery", "cooling_unit"):
    MODELS.append(geo(f"geometry.mcn_{name}", [cube([-8, 0, -8], [16, 8, 16])]))
MODELS.append(geo("geometry.mcn_solar_panel", [cube([-8, 0, -8], [16, 1, 16])]))
for direction in CARDINALS:
    box = rack_box(direction)
    MODELS.append(geo(
        f"geometry.mcn_server_rack_{direction}",
        [cube(box["origin"], box["size"])],
    ))
for direction in CARDINALS:
    box = monitor_box(direction)
    MODELS.append(geo(
        f"geometry.mcn_monitor_{direction}",
        [cube(box["origin"], box["size"])],
    ))
for mask in range(16):
    MODELS.append(geo(f"geometry.mcn_power_cable_{mask}", pipe_cubes(mask)))

write(os.path.join(RP, "models", "blocks", "mcn_models.geo.json"), {
    "format_version": "1.12.0",
    "minecraft:geometry": MODELS,
})

# ---------------------------------------------------------------- language
BLOCK_NAMES = {
    "power_cable": "Power Cable",
    "solar_panel": "Solar Panel",
    "battery": "Battery",
    "cooling_unit": "Cooling Unit",
    "server_rack": "Server Rack",
    "radio_tower": "Radio Tower",
    "radio_extender": "Radio Extender",
    "lan_cable": "LAN Cable",
    "monitor": "Monitor",
}
lang = [f"tile.minecoins:{n}.name={label}" for n, label in BLOCK_NAMES.items()]
lang.append("item.minecoins:tablet.name=Minecoins Tablet")
lang.append(f"{CATALOG_GROUP}=Minecoins")
lang.append(f"{GUIDE_GROUP}=Minecoins Guide")
lang.append("item.minecoins:guidebook.name=Minecoins Guide")
os.makedirs(os.path.join(RP, "texts"), exist_ok=True)
with open(os.path.join(RP, "texts", "en_US.lang"), "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lang) + "\n")

# ---------------------------------------------------------------- manifests
write(os.path.join(BP, "manifest.json"), {
    "format_version": 2,
    "header": {
        "name": "Minecoins Core (Behavior)",
        "description": "Minecoins, digital storage, power grid and radio network.",
        "uuid": UUID_BP,
        "version": VERSION,
        "min_engine_version": [1, 21, 70],
    },
    "modules": [
        {"type": "data", "uuid": UUID_BP_DATA, "version": VERSION},
        {
            "type": "script",
            "language": "javascript",
            "uuid": UUID_BP_SCRIPT,
            "version": VERSION,
            "entry": "scripts/main.js",
        },
    ],
    "dependencies": [
        {"module_name": "@minecraft/server", "version": "2.0.0"},
        {"module_name": "@minecraft/server-ui", "version": "2.0.0"},
        {"uuid": UUID_RP, "version": VERSION},
    ],
    "metadata": {"authors": ["Minecoins"], "generated_with": {"minecoins": ["1.1.0"]}},
})

write(os.path.join(RP, "manifest.json"), {
    "format_version": 2,
    "header": {
        "name": "Minecoins Core (Resources)",
        "description": "Textures for the Minecoins addon.",
        "uuid": UUID_RP,
        "version": VERSION,
        "min_engine_version": [1, 21, 70],
    },
    "modules": [{"type": "resources", "uuid": UUID_RP_RES, "version": VERSION}],
    "dependencies": [{"uuid": UUID_BP, "version": VERSION}],
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
        "mcn_icon_computer": {"textures": "textures/items/mcn_icon_computer"},
        "mcn_icon_store": {"textures": "textures/items/mcn_icon_store"},
        "mcn_icon_coins": {"textures": "textures/items/mcn_icon_coins"},
        "mcn_icon_docs": {"textures": "textures/items/mcn_icon_docs"},
        "mcn_icon_shutdown": {"textures": "textures/items/mcn_icon_shutdown"},
        "mcn_guidebook": {"textures": "textures/items/mcn_guidebook"},
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


def tex_monitor(x, y):
    if x < 2 or y < 2 or x > 13 or y > 13:
        return (58, 64, 76, 255)
    if x == 13 and y == 2:
        return (240, 90, 70, 255)
    if y >= 13:
        return (206, 210, 216, 255)
    if y % 4 == 0:
        return (34, 92, 150, 255)
    return (46, 122, 186, 255)


def icon_computer(x, y):
    if 3 <= x <= 28 and 3 <= y <= 22:
        if x < 6 or x > 25 or y < 6 or y > 19:
            return (190, 192, 198, 255)
        return (72, 152, 222, 255) if y % 4 else (36, 104, 168, 255)
    if 11 <= x <= 20 and 23 <= y <= 27:
        return (150, 152, 158, 255)
    if 7 <= x <= 24 and 28 <= y <= 29:
        return (120, 122, 130, 255)
    return (0, 0, 0, 0)


def icon_store(x, y):
    if 6 <= x <= 25 and 11 <= y <= 28:
        if 6 <= x <= 8 or 23 <= x <= 25:
            return (122, 86, 20, 255)
        if y > 20 and x % 5 == 0:
            return (198, 158, 40, 255)
        return (236, 196, 74, 255)
    if abs(((x - 15.5) ** 2 + (y - 10) ** 2) ** 0.5 - 6) < 1.2 and y <= 11:
        return (122, 86, 20, 255)
    return (0, 0, 0, 0)


def icon_coins(x, y):
    low = ((x - 15.5) ** 2 + (y - 21) ** 2) ** 0.5
    if low <= 9:
        return (120, 82, 16, 255) if low > 7 else (232, 186, 52, 255)
    top = ((x - 15.5) ** 2 + (y - 12) ** 2) ** 0.5
    if top <= 8:
        return (150, 104, 20, 255) if top > 6 else (255, 216, 96, 255)
    return (0, 0, 0, 0)


def icon_docs(x, y):
    if 7 <= x <= 24 and 4 <= y <= 28:
        if x in (7, 24) or y in (4, 28):
            return (150, 152, 158, 255)
        if (x + y) % 7 == 0 and 9 <= y <= 24:
            return (150, 152, 158, 255)
        return (240, 240, 244, 255)
    return (0, 0, 0, 0)


def icon_shutdown(x, y):
    r = ((x - 15.5) ** 2 + (y - 15.5) ** 2) ** 0.5
    if r <= 11:
        if r > 9:
            return (120, 12, 12, 255)
        if 5.0 <= r <= 6.6 and not (y < 15.5 and abs(x - 15.5) < 2.2):
            return (250, 245, 245, 255)
        if abs(x - 15.5) <= 1.4 and 6 <= y <= 15:
            return (250, 245, 245, 255)
        return (196, 32, 32, 255)
    return (0, 0, 0, 0)


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


def tex_guidebook(x, y):
    """Blue help book: spine, cream page edge, redstone clasp, glass sheen."""
    if x < 3 or x > 12 or y < 2 or y > 13:
        return (0, 0, 0, 0)
    if x == 3 or x == 4:
        return (24, 34, 74, 255)
    if 11 <= x <= 12 and 4 <= y <= 11:
        return (232, 226, 198, 255)
    if y == 2 or y == 13 or x == 12:
        return (18, 26, 58, 255)
    if 6 <= x <= 8 and 5 <= y <= 7:
        return (206, 44, 44, 255)
    if (x + y) % 7 == 0:
        return (150, 186, 240, 255)
    return (40, 66, 138, 255)


TEXTURES = {
    **{f"mcn_{n}": globals()[f"tex_{n}"] for n in BLOCK_TEX},
}
for n, fn in TEXTURES.items():
    png(os.path.join(RP, "textures", "blocks", f"{n}.png"), fn)

ITEM_TEXTURES = {"mcn_tablet": tex_tablet, "mcn_minecoin": tex_minecoin,
                 "mcn_guidebook": tex_guidebook}
for n, fn in ITEM_TEXTURES.items():
    png(os.path.join(RP, "textures", "items", f"{n}.png"), fn)

DESKTOP_ICONS = {
    "mcn_icon_computer": icon_computer,
    "mcn_icon_store": icon_store,
    "mcn_icon_coins": icon_coins,
    "mcn_icon_docs": icon_docs,
    "mcn_icon_shutdown": icon_shutdown,
}
for n, fn in DESKTOP_ICONS.items():
    png(os.path.join(RP, "textures", "items", f"{n}.png"), fn, 32)

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


# ---------------------------------------------------- 9x UI skin (main RP)
# Additive JSON-UI skin for server forms, shipped inside the main resource pack.
# Delete ui/server_form.json to fall back to the plain form.
WIN95_FRAME = {
    "type": "image",
    "texture": "textures/ui/mcn_win95_frame",
    "size": ["100% + 8px", "100% + 8px"],
    "offset": [-4, -4],
    "layer": -10,
    "nine_slice_buttom": 6,
    "nine_slice_bottom": 6,
    "nine_slice_left": 6,
    "nine_slice_right": 6,
    "nine_slice_top": 6,
}

SERVER_FORM_UI = {
    "namespace": "server_form",
    "long_form": {
        "modifications": [{
            "array_name": "controls",
            "operation": "insert_front",
            "value": [{"win95_frame": WIN95_FRAME}],
        }]
    },
    "custom_form": {
        "modifications": [{
            "array_name": "controls",
            "operation": "insert_front",
            "value": [{"win95_frame": WIN95_FRAME}],
        }]
    },
}

write(os.path.join(RP, "ui", "server_form.json"), SERVER_FORM_UI)


def win95_frame(x, y):
    if x in (0, 31) or y in (0, 31):
        return (0, 0, 0, 255)
    if x == 1 or y == 1:
        return (255, 255, 255, 255)
    if x == 30 or y == 30:
        return (128, 128, 128, 255)
    if x == 2 or y == 2:
        return (223, 223, 223, 255)
    return (192, 192, 192, 255)


png(os.path.join(RP, "textures", "ui", "mcn_win95_frame.png"), win95_frame, 32)

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
zip_pack(os.path.join(ROOT, "Minecoins.mcaddon"),
         [("Minecoins_BP", BP), ("Minecoins_RP", RP)])
print("generated:", ROOT)
