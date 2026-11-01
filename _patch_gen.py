import sys

GEN = "Minecoins/tools/gen_packs.py"
t = open(GEN, encoding="utf-8", newline="").read()


def rep(old, new, n=1):
    global t
    c = t.count(old)
    if c != n:
        sys.exit("MISMATCH %r %d" % (old[:70], c))
    t = t.replace(old, new)


rep("VERSION = [1, 7, 0]\n", "VERSION = [2, 0, 0]\n")

# ---------------------------------------------------------------- blocks
rep('''BLOCKS = [
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
]''',
'''BLOCKS = [
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
]''')

# ------------------------------------------------- variants for lit/drive blocks
rep('''def rack_material(module):''',
'''VARIANT_TEX = {
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


def rack_material(module):''')

# ------------------------------------------------------ block definitions
rep('''    elif name in FLAT_BLOCKS:''',
'''    elif name in ("generator", "storage_terminal"):
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
    elif name in FLAT_BLOCKS:''')

# ---------------------------------------------------------------- items
rep('''# ----------------------------------------------------- creative item catalog''',
'''HARDWARE = [
    ("flash_drive", "Flash Drive", 1),
    ("speed_module", "Speed Module", 16),
    ("storage_module", "Storage Module", 16),
    ("research_module", "Research Module", 16),
]
for short, label, stack in HARDWARE:
    write(os.path.join(BP, "items", f"{short}.json"), {
        "format_version": "1.21.60",
        "minecraft:item": {
            "description": {
                "identifier": f"minecoins:{short}",
                "menu_category": {"category": "items", "group": CATALOG_GROUP},
            },
            "components": {
                "minecraft:icon": {"textures": {"default": f"mcn_{short}"}},
                "minecraft:display_name": {"value": label},
                "minecraft:max_stack_size": stack,
            },
        },
    })

# ----------------------------------------------------- creative item catalog''')

# ---------------------------------------------------------------- recipes
rep('''for name, pattern, keys, count in RECIPES:''',
'''RECIPES += [
    ("generator", ["IRI", "IFI", "IRI"],
     {"I": "minecraft:iron_ingot", "R": "minecraft:redstone", "F": "minecraft:furnace"}, 1),
    ("storage_terminal", ["IGI", "GRG", "III"],
     {"I": "minecraft:iron_ingot", "G": "minecraft:glass", "R": "minecraft:redstone"}, 1),
    ("flash_drive", ["IRI", "RCR", "ICI"],
     {"I": "minecraft:iron_ingot", "R": "minecraft:redstone", "C": "minecraft:copper_ingot"}, 1),
    ("speed_module", ["GRG", "RSR", "GRG"],
     {"G": "minecraft:gold_ingot", "R": "minecraft:redstone", "S": "minecraft:sugar"}, 1),
    ("storage_module", ["IRI", "RCR", "IRI"],
     {"I": "minecraft:iron_ingot", "R": "minecraft:redstone", "C": "minecraft:chest"}, 1),
    ("research_module", ["BRB", "RSR", "BRB"],
     {"B": "minecraft:book", "R": "minecraft:redstone", "S": "minecraft:amethyst_shard"}, 1),
]
for name, pattern, keys, count in RECIPES:''')

# ---------------------------------------------------------------- language
rep('''    "lan_cable": "LAN Cable",''', '''    "generator": "Generator",
    "storage_terminal": "Storage Terminal",''')
rep('''lang.append("item.minecoins:guidebook.name=Minecoins Guide")''',
'''lang.append("item.minecoins:guidebook.name=Minecoins Guide")
for short, label, _stack in HARDWARE:
    lang.append(f"item.minecoins:{short}.name={label}")''')

# ---------------------------------------------------------------- textures
rep('''def tex_monitor(x, y):''',
'''def tex_generator(x, y, lit):
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


def tex_module_speed(x, y):
    return module_icon(x, y, (214, 78, 62))


def tex_module_storage(x, y):
    return module_icon(x, y, (62, 190, 118))


def tex_module_research(x, y):
    return module_icon(x, y, (168, 110, 226))


def module_icon(x, y, tint):
    if x < 2 or y < 2 or x > 13 or y > 13:
        return (0, 0, 0, 0)
    if x in (2, 13) or y in (2, 13):
        return (58, 64, 78, 255)
    if (x, y) in ((4, 4), (11, 4), (4, 11), (11, 11)):
        return (206, 210, 216, 255)
    if 5 <= x <= 10 and 5 <= y <= 10:
        return (*tint, 255)
    return (38, 44, 56, 255)


def tex_monitor(x, y):''')

rep('''TEXTURES = {
    **{f"mcn_{n}": globals()[f"tex_{n}"] for n in BLOCK_TEX if n != "server_rack"},
}''',
'''EXTRA_BLOCK_TEX = {
    "mcn_generator": lambda x, y: tex_generator(x, y, False),
    "mcn_generator_lit": lambda x, y: tex_generator(x, y, True),
    "mcn_storage_terminal": lambda x, y: tex_storage_terminal(x, y, False),
    "mcn_storage_terminal_drive": lambda x, y: tex_storage_terminal(x, y, True),
}

TEXTURES = {
    **{f"mcn_{n}": globals()[f"tex_{n}"]
       for n in BLOCK_TEX if n not in ("server_rack", "generator", "storage_terminal")},
    **EXTRA_BLOCK_TEX,
}''')

rep('''TEX_DATA = {f"mcn_{n}": {"textures": f"textures/blocks/mcn_{n}"} for n in BLOCK_TEX}
for module, tex in RACK_TEX.items():
    TEX_DATA[tex] = {"textures": f"textures/blocks/{tex}"}''',
'''TEX_DATA = {f"mcn_{n}": {"textures": f"textures/blocks/mcn_{n}"} for n in BLOCK_TEX}
TEX_DATA["mcn_generator_lit"] = {"textures": "textures/blocks/mcn_generator_lit"}
TEX_DATA["mcn_storage_terminal_drive"] = {"textures": "textures/blocks/mcn_storage_terminal_drive"}
for module, tex in RACK_TEX.items():
    TEX_DATA[tex] = {"textures": f"textures/blocks/{tex}"}''')

rep('''ITEM_TEXTURES = {"mcn_tablet": tex_tablet, "mcn_minecoin": tex_minecoin,
                 "mcn_guidebook": tex_guidebook}''',
'''ITEM_TEXTURES = {"mcn_tablet": tex_tablet, "mcn_minecoin": tex_minecoin,
                 "mcn_guidebook": tex_guidebook,
                 "mcn_flash_drive": tex_flash_drive,
                 "mcn_speed_module": tex_module_speed,
                 "mcn_storage_module": tex_module_storage,
                 "mcn_research_module": tex_module_research}''')

rep('''        "mcn_guidebook": {"textures": "textures/items/mcn_guidebook"},''',
'''        "mcn_guidebook": {"textures": "textures/items/mcn_guidebook"},
        "mcn_flash_drive": {"textures": "textures/items/mcn_flash_drive"},
        "mcn_speed_module": {"textures": "textures/items/mcn_speed_module"},
        "mcn_storage_module": {"textures": "textures/items/mcn_storage_module"},
        "mcn_research_module": {"textures": "textures/items/mcn_research_module"},''')

open(GEN, "w", encoding="utf-8", newline="\n").write(t)
print("generator patched for 2.0.0")
