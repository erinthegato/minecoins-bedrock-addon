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
VERSION = [2, 1, 6]

# Creative menu: one collapsible group per tab. The same names are declared
# on the block/item definitions and in item_catalog/crafting_item_catalog.json
# so a block reaches its group whichever route Minecraft reads first.
CATALOG_GROUP = "minecoins:itemGroup.name.server_components"
GUIDE_GROUP = "minecoins:itemGroup.name.guide"
HARDWARE_GROUP = "minecoins:itemGroup.name.hardware"


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------- blocks
BLOCKS = [
    # id, map colour, hardness, light
    ("power_cable", "#4a3a2c", 0.4, 0),
    ("solar_panel", "#1d3f6b", 1.2, 0),
    ("battery", "#2c3a30", 1.4, 2),
    ("cooling_unit", "#9fc4d6", 1.2, 0),
    ("server_rack", "#23252c", 1.6, 3),
    ("radio_tower", "#b03030", 1.5, 6),
    ("radio_extender", "#8a2a2a", 1.2, 4),
    ("monitor", "#2f3540", 1.0, 5),
    ("generator", "#4a3b28", 1.4, 0),
    ("storage_terminal", "#2b3550", 1.2, 4),
]

HALF_BLOCKS = {"battery", "cooling_unit"}
FLAT_BLOCKS = {"solar_panel"}
PIPE_BLOCKS = {"power_cable"}
CARDINALS = ["north", "south", "east", "west"]
PIPE_DIRECTIONS = [
    ("north", (0, 0, -1), 1),
    ("south", (0, 0, 1), 2),
    ("east", (1, 0, 0), 4),
    ("west", (-1, 0, 0), 8),
    ("up", (0, 1, 0), 16),
    ("down", (0, -1, 0), 32),
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


RACK_SIDES = [("north", 1), ("south", 2), ("east", 4), ("west", 8)]

# A rack takes two installable modules; the state repaints the whole cabinet.
MODULES = ["none", "cooling", "battery", "both"]
RACK_TEX = {
    "none": "mcn_server_rack",
    "cooling": "mcn_server_rack_cool",
    "battery": "mcn_server_rack_batt",
    "both": "mcn_server_rack_both",
}
RACK_FRAMES = 8


VARIANT_TEX = {
    ("generator", False): "mcn_generator",
    ("generator", True): "mcn_generator_lit",
    ("storage_terminal", False): "mcn_storage_terminal",
    ("storage_terminal", True): "mcn_storage_terminal_drive",
}


def variant_material(name, on):
    return {"*": {
        "texture": VARIANT_TEX[(name, on)],
        "render_method": "opaque",
        "face_dimming": True,
        "ambient_occlusion": True,
    }}


def rack_material(module):
    return {"*": {
        "texture": RACK_TEX[module],
        "render_method": "opaque",
        "face_dimming": True,
        "ambient_occlusion": True,
    }}


def rack_box(mask=0):
    """Freestanding cabinet centred in its block. Every side that touches
    another rack is stretched out to the block edge, so a row of racks joins into
    one continuous wall instead of leaving a 4px gap between each."""
    x0, x1, z0, z1 = -6, 6, -6, 6
    if mask & 1:
        z0 = -8
    if mask & 2:
        z1 = 8
    if mask & 4:
        x1 = 8
    if mask & 8:
        x0 = -8
    return {"origin": [x0, 0, z0], "size": [x1 - x0, 16, z1 - z0]}


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
    """One pipe, not a fence: a tube crosses the whole block on each axis it is
    connected on, so a run of blocks reads as a single continuous pipe. It pokes
    nowhere it is not attached, and a junction is a plain crossing."""
    x = bool(mask & 4 or mask & 8)
    z = bool(mask & 1 or mask & 2)
    y = bool(mask & 16 or mask & 32)
    cubes = []
    if x:
        cubes.append(cube([-8, 6, -2], [16, 4, 4]))
    if z:
        cubes.append(cube([-2, 6, -8], [4, 4, 16]))
    if x or z:
        cubes.append(cube([-2, 6, -2], [4, 4, 4]))
    if y:
        cubes.append(cube([-2, 0, -2], [4, 16, 4]))
    if not cubes:
        cubes.append(cube([-2, 0, -2], [4, 8, 4]))
    return cubes


for name, colour, hardness, light in BLOCKS:
    description = {
        "identifier": f"minecoins:{name}",
        "menu_category": {"category": "construction", "group": CATALOG_GROUP},
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
        # wall-forming cabinet: each touching side grows out to the block edge
        description["states"] = {
            f"minecoins:{side}": [False, True] for side, _bit in RACK_SIDES
        }
        description["states"]["minecoins:module"] = MODULES
        box0 = rack_box(0)
        components["minecraft:geometry"] = "geometry.mcn_server_rack_0"
        components["minecraft:collision_box"] = box0
        components["minecraft:selection_box"] = box0
        components["minecraft:material_instances"] = rack_material("none")
        permutations = []
        for mask in range(16):
            links = " && ".join(
                f"q.block_state('minecoins:{side}') == "
                f"{'true' if mask & bit else 'false'}"
                for side, bit in RACK_SIDES
            )
            box = rack_box(mask)
            for module in MODULES:
                permutations.append({
                    "condition": f"{links} && q.block_state('minecoins:module') == '{module}'",
                    "components": {
                        "minecraft:geometry": f"geometry.mcn_server_rack_{mask}",
                        "minecraft:collision_box": box,
                        "minecraft:selection_box": box,
                        "minecraft:material_instances": rack_material(module),
                    },
                })
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
    elif name in ("generator", "storage_terminal"):
        # a second texture per state: the firebox lights up, the terminal takes a drive
        state_name = "minecoins:lit" if name == "generator" else "minecoins:drive"
        description["states"] = {state_name: [False, True]}
        components["minecraft:geometry"] = "minecraft:geometry.full_block"
        components["minecraft:material_instances"] = variant_material(name, False)
        permutations = [
            {
                "condition": f"q.block_state('{state_name}') == {'true' if on else 'false'}",
                "components": {"minecraft:material_instances": variant_material(name, on)},
            }
            for on in (False, True)
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
        for mask in range(64):
            condition = " && ".join(
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
        "format_version": "1.21.60",
        "minecraft:block": block_def,
    })

# ---------------------------------------------------------------- items
write(os.path.join(BP, "items", "tablet.json"), {
    "format_version": "1.21.60",
    "minecraft:item": {
        "description": {
            "identifier": "minecoins:tablet",
            "menu_category": {"category": "equipment"},
        },
        "components": {
            "minecraft:icon": {"textures": {"default": "mcn_tablet"}},
            "minecraft:display_name": {"value": "Minecoins Tablet"},
            "minecraft:max_stack_size": 1,
            "minecraft:hand_equipped": True,
            "minecraft:allow_off_hand": True,
            "minecraft:glint": True,
        },
    },
})

# ---------------------------------------------------------------- guide book
write(os.path.join(BP, "items", "guidebook.json"), {
    "format_version": "1.21.60",
    "minecraft:item": {
        "description": {
            "identifier": "minecoins:guidebook",
            "menu_category": {"category": "items", "group": GUIDE_GROUP},
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
        "unlock": {"context": "AlwaysUnlocked"},
        "ingredients": [
            {"item": "minecraft:book"},
            {"item": "minecraft:redstone"},
            {"item": "minecraft:glass"},
        ],
        "result": {"item": "minecoins:guidebook", "count": 1},
    },
})

# Upgrade tiers follow vanilla progression: copper, iron, lapis, diamond, netherite.
TIERS = ["copper", "iron", "lapis", "diamond", "netherite"]
TRACKS = ["speed", "storage", "research"]
HARDWARE = [("flash_drive", "Flash Drive", 1)]
for _tier in TIERS:
    for _track in TRACKS:
        HARDWARE.append((
            f"{_track}_module_{_tier}",
            f"{_tier.capitalize()} {_track.capitalize()} Module",
            16,
        ))
for short, label, stack in HARDWARE:
    write(os.path.join(BP, "items", f"{short}.json"), {
        "format_version": "1.21.60",
        "minecraft:item": {
            "description": {
                "identifier": f"minecoins:{short}",
                "menu_category": {"category": "items", "group": HARDWARE_GROUP},
            },
            "components": {
                "minecraft:icon": {"textures": {"default": f"mcn_{short}"}},
                "minecraft:display_name": {"value": label},
                "minecraft:max_stack_size": stack,
            },
        },
    })

# ----------------------------------------------------- creative item catalog
# menu_category alone is not enough for every block shape: stateful blocks can be
# skipped by the creative menu. The catalog lists every block explicitly in one
# collapsible group. The guide book is listed twice on purpose - the user wants
# it reachable from both the Items and the Equipment tab.
def group(icon, name, items):
    return {
        "group_identifier": {"icon": icon, "name": name},
        "items": items,
    }


write(os.path.join(BP, "item_catalog", "crafting_item_catalog.json"), {
    "format_version": "1.21.60",
    "minecraft:crafting_items_catalog": {
        "categories": [
            {
                "category_name": "construction",
                "groups": [group("minecoins:server_rack", CATALOG_GROUP,
                                 [f"minecoins:{n}" for n, *_ in BLOCKS])],
            },
            {
                "category_name": "items",
                "groups": [
                    group("minecoins:guidebook", GUIDE_GROUP, ["minecoins:guidebook"]),
                    {
                        "group_identifier": {
                            "name": HARDWARE_GROUP,
                            "icon": "minecoins:flash_drive",
                        },
                        "items": [f"minecoins:{short}" for short, _l, _s in HARDWARE],
                    },
                ],
            },
            {
                "category_name": "equipment",
                "groups": [{"items": ["minecoins:tablet"]}],
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
    ("tablet", ["IGI", "GRG", "IRI"],
     {"I": "minecraft:iron_ingot", "G": "minecraft:glass", "R": "minecraft:redstone"}, 1),
    ("monitor", ["IGI", "GRG", "IGI"],
     {"I": "minecraft:iron_ingot", "G": "minecraft:glass", "R": "minecraft:redstone"}, 1),
]
RECIPES += [
    ("generator", ["IRI", "IFI", "IRI"],
     {"I": "minecraft:iron_ingot", "R": "minecraft:redstone", "F": "minecraft:furnace"}, 1),
    ("storage_terminal", ["IGI", "GRG", "III"],
     {"I": "minecraft:iron_ingot", "G": "minecraft:glass", "R": "minecraft:redstone"}, 1),
    ("flash_drive", ["IRI", "RCR", "ICI"],
     {"I": "minecraft:iron_ingot", "R": "minecraft:redstone", "C": "minecraft:copper_ingot"}, 1),
]
MATERIAL_INGOT = {
    "copper": "minecraft:copper_ingot",
    "iron": "minecraft:iron_ingot",
    "lapis": "minecraft:lapis_lazuli",
    "diamond": "minecraft:diamond",
    "netherite": "minecraft:netherite_ingot",
}
CORE_ITEM = {
    "speed": "minecraft:sugar",
    "storage": "minecraft:chest",
    "research": "minecraft:amethyst_shard",
}
for _tier in TIERS:
    for _track in TRACKS:
        RECIPES.append((f"{_track}_module_{_tier}", ["MRM", " S "], {
            "M": MATERIAL_INGOT[_tier],
            "R": "minecraft:redstone",
            "S": CORE_ITEM[_track],
        }, 1))
for name, pattern, keys, count in RECIPES:
    write(os.path.join(BP, "recipes", f"{name}.json"), {
        "format_version": "1.20.10",
        "minecraft:recipe_shaped": {
            "description": {"identifier": f"minecoins:{name}"},
            "tags": ["crafting_table"],
            "unlock": {"context": "AlwaysUnlocked"},
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
for mask in range(16):
    box = rack_box(mask)
    MODELS.append(geo(
        f"geometry.mcn_server_rack_{mask}",
        [cube(box["origin"], box["size"])],
    ))
for direction in CARDINALS:
    box = monitor_box(direction)
    MODELS.append(geo(
        f"geometry.mcn_monitor_{direction}",
        [cube(box["origin"], box["size"])],
    ))
for mask in range(64):
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
    "generator": "Generator",
    "storage_terminal": "Storage Terminal",
    "monitor": "Monitor",
}
lang = [f"tile.minecoins:{n}.name={label}" for n, label in BLOCK_NAMES.items()]
lang.append("item.minecoins:tablet.name=Minecoins Tablet")
lang.append(f"{CATALOG_GROUP}=Server Components")
lang.append(f"{GUIDE_GROUP}=Minecoins Guide")
lang.append(f"{HARDWARE_GROUP}=Server Hardware")
lang.append("item.minecoins:guidebook.name=Minecoins Guide")
for short, label, _stack in HARDWARE:
    lang.append(f"item.minecoins:{short}.name={label}")
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

TEX_DATA = {f"mcn_{n}": {"textures": f"textures/blocks/mcn_{n}"} for n in BLOCK_TEX}
TEX_DATA["mcn_generator_lit"] = {"textures": "textures/blocks/mcn_generator_lit"}
TEX_DATA["mcn_storage_terminal_drive"] = {"textures": "textures/blocks/mcn_storage_terminal_drive"}
for module, tex in RACK_TEX.items():
    TEX_DATA[tex] = {"textures": f"textures/blocks/{tex}"}

write(os.path.join(RP, "textures", "terrain_texture.json"), {
    "resource_pack_name": "minecoins",
    "texture_name": "atlas.terrain",
    "padding": 8,
    "num_mip_levels": 4,
    "texture_data": TEX_DATA,
})

ITEM_TEX = {
    key: {"textures": f"textures/items/{key}"}
    for key in ("mcn_tablet", "mcn_minecoin", "mcn_icon_computer", "mcn_icon_store",
                "mcn_icon_coins", "mcn_icon_docs", "mcn_icon_shutdown",
                "mcn_guidebook", "mcn_flash_drive")
}
for _tier in TIERS:
    for _track in TRACKS:
        ITEM_TEX[f"mcn_{_track}_module_{_tier}"] = {
            "textures": f"textures/items/mcn_{_track}_module_{_tier}"}

write(os.path.join(RP, "textures", "item_texture.json"), {
    "resource_pack_name": "minecoins",
    "texture_name": "atlas.items",
    "texture_data": ITEM_TEX,
})


def png(path, fn, size=16, frames=1):
    """Write a PNG; with frames>1 the frames stack vertically, the layout that
    flipbook_textures.json expects."""
    w, h = size, size * frames
    raw = b""
    for y in range(h):
        raw += bytes([0])
        frame, yy = y // size, y % size
        for x in range(w):
            raw += bytes(fn(x, yy, frame) if frames > 1 else fn(x, yy))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(bytes([137, 80, 78, 71, 13, 10, 26, 10]))
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


# front-panel LEDs: one pixel each, blinking red / green / blue per frame
LEDS = [(2, 4), (13, 4), (3, 9), (12, 9), (6, 12), (9, 12), (7, 6), (10, 6)]
LED_COLORS = [(255, 70, 70), (70, 255, 130), (90, 150, 255), (255, 70, 70),
              (70, 255, 130), (90, 150, 255), (255, 210, 80), (120, 230, 255)]


def rack_pixel(x, y, module, frame):
    """One rack frame: chassis, module hardware, and a pixel that blinks."""
    if x == 0 or y == 0 or x == 15 or y == 15:
        return (14, 15, 19, 255)
    col = (34, 36, 44)
    if y in (3, 4, 8, 9, 12):
        col = (56, 60, 72)
    if module in ("cooling", "both") and 5 <= y <= 7 and x % 3 == 0:
        col = (96, 186, 214)
    if module in ("battery", "both") and 11 <= x <= 13 and 6 <= y <= 10:
        col = (58, 200, 120) if y % 2 else (40, 150, 90)
    for i, led in enumerate(LEDS):
        if (x, y) == led and (frame * 3 + i * 5) % RACK_FRAMES < 3:
            col = LED_COLORS[i]
    return (*col, 255)


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


def tex_generator(x, y, lit):
    if x == 0 or y == 0 or x == 15 or y == 15:
        return (30, 24, 18, 255)
    if 3 <= y <= 6 or 10 <= y <= 12:
        if x % 2 == 0:
            return (255, 148, 52, 255) if lit else (86, 52, 26, 255)
        return (58, 40, 24, 255) if lit else (44, 34, 24, 255)
    if y == 8 and 3 <= x <= 12:
        return (208, 96, 40, 255) if lit else (96, 70, 44, 255)
    return (64, 52, 40, 255) if lit else (48, 42, 34, 255)


def tex_storage_terminal(x, y, drive):
    if x < 1 or y < 1 or x > 14 or y > 14:
        return (24, 28, 38, 255)
    if drive and y <= 2 and 5 <= x <= 10:
        return (198, 206, 214, 255)
    if 3 <= x <= 12 and 4 <= y <= 10:
        if y in (4, 10) or x in (3, 12):
            return (86, 96, 120, 255)
        if y == 7 and 5 <= x <= 10:
            return (84, 214, 250, 255)
        return (32, 74, 122, 255)
    if 4 <= x <= 11 and y == 12:
        return (84, 214, 250, 255) if drive else (60, 84, 110, 255)
    return (44, 52, 70, 255)


def tex_flash_drive(x, y):
    if 6 <= x <= 9 and 2 <= y <= 5:
        return (198, 206, 214, 255)
    if 5 <= x <= 10 and 6 <= y <= 13:
        return (52, 96, 168, 255)
    if 7 <= x <= 8 and 8 <= y <= 11:
        return (120, 220, 255, 255)
    return (0, 0, 0, 0)


TRACK_TINT = {"speed": (214, 78, 62), "storage": (62, 190, 118),
              "research": (168, 110, 226)}
TIER_STUD = {"copper": (198, 120, 72), "iron": (206, 210, 216),
             "lapis": (70, 110, 220), "diamond": (110, 230, 240),
             "netherite": (96, 86, 100)}


def module_icon(x, y, tint, stud):
    """Board in the track colour, with the tier metal on the corner studs."""
    if x < 2 or y < 2 or x > 13 or y > 13:
        return (0, 0, 0, 0)
    if x in (2, 13) or y in (2, 13):
        return (58, 64, 78, 255)
    if (x, y) in ((4, 4), (11, 4), (4, 11), (11, 11)):
        return (*stud, 255)
    if 5 <= x <= 10 and 5 <= y <= 10:
        return (*tint, 255)
    return (38, 44, 56, 255)


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


EXTRA_BLOCK_TEX = {
    "mcn_generator": lambda x, y: tex_generator(x, y, False),
    "mcn_generator_lit": lambda x, y: tex_generator(x, y, True),
    "mcn_storage_terminal": lambda x, y: tex_storage_terminal(x, y, False),
    "mcn_storage_terminal_drive": lambda x, y: tex_storage_terminal(x, y, True),
}

TEXTURES = {
    **{f"mcn_{n}": globals()[f"tex_{n}"]
       for n in BLOCK_TEX if n not in ("server_rack", "generator", "storage_terminal")},
    **EXTRA_BLOCK_TEX,
}
for n, fn in TEXTURES.items():
    png(os.path.join(RP, "textures", "blocks", f"{n}.png"), fn)

# the rack is a flipbook: one band per frame, LEDs blinking red/green/blue
for module, tex in RACK_TEX.items():
    png(os.path.join(RP, "textures", "blocks", f"{tex}.png"),
        (lambda x, y, f, m=module: rack_pixel(x, y, m, f)), 16, RACK_FRAMES)

write(os.path.join(RP, "textures", "flipbook_textures.json"), [
    {
        "flipbook_texture": f"textures/blocks/{tex}",
        "atlas_tile": tex,
        "ticks_per_frame": 4,
        "frames": list(range(RACK_FRAMES)),
    }
    for tex in RACK_TEX.values()
])

ITEM_TEXTURES = {"mcn_tablet": tex_tablet, "mcn_minecoin": tex_minecoin,
                 "mcn_guidebook": tex_guidebook,
                 "mcn_flash_drive": tex_flash_drive}
for _tier in TIERS:
    for _track in TRACKS:
        ITEM_TEXTURES[f"mcn_{_track}_module_{_tier}"] = (
            lambda x, y, tr=_track, ti=_tier: module_icon(
                x, y, TRACK_TINT[tr], TIER_STUD[ti]))
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
