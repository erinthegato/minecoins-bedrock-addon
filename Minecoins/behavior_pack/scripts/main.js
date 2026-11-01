/**
 * Minecoins Core
 * - Minecoin mining: +1 minecoin / 5 real minutes with chat notification
 * - Digital storage (server rack, requires power + cooling)
 * - Power grid: solar panels -> power cable -> battery -> server rack / cooling
 * - Radio: tower (1500 block range), extenders repeat the network
 * - Underground: no radio signal; vault reached by flash drive + terminal
 * - Catalog: buy nearly every obtainable item, diamond tier most expensive
 */
import { world, system, ItemStack, EquipmentSlot, BlockPermutation } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";

const COIN_MS = 300000; // 5 real minutes
const RANGE = 1500;
const RACK_REACH = 48;
const GRID_LIMIT = 700;

const B = {
  cable: "minecoins:power_cable",
  panel: "minecoins:solar_panel",
  battery: "minecoins:battery",
  cooling: "minecoins:cooling_unit",
  rack: "minecoins:server_rack",
  tower: "minecoins:radio_tower",
  extender: "minecoins:radio_extender",
  monitor: "minecoins:monitor",
  generator: "minecoins:generator",
  terminal: "minecoins:storage_terminal",
};
const TABLET = "minecoins:tablet";
const GUIDE_BOOK = "minecoins:guidebook";
const GRID_BLOCKS = [B.cable, B.panel, B.battery, B.cooling, B.rack, B.generator, B.terminal];
const NODE_BLOCKS = [B.tower, B.extender];

/* Fence-style pipe connections: the block state drives which arms render. */
const PIPE_LINKS = [
  ["minecoins:north", 0, 0, -1],
  ["minecoins:south", 0, 0, 1],
  ["minecoins:east", 1, 0, 0],
  ["minecoins:west", -1, 0, 0],
  ["minecoins:up", 0, 1, 0],
  ["minecoins:down", 0, -1, 0],
];
/* Each pipe family connects to its own set of blocks. */
const PIPE_LINKS_BY_TYPE = {
  [B.cable]: new Set([B.cable, B.panel, B.battery, B.cooling, B.rack, B.generator, B.terminal]),
};

const PIPE_IDS = new Set([B.cable]);

/* Rack hardware: modules bolt into the cabinet and repaint it. */
const MODULE_OF = { [B.battery]: "battery", [B.cooling]: "cooling" };
const HEAT_MAX = 100;          // a rack that reaches this shuts itself down
const HEAT_GAIN = 0.9;         // degrees per second while running
const HEAT_DROP = 2.2;         // degrees per second while cooled
const RACK_BATTERY_CAP = 1000; // a fitted battery module

/* Upgrade tiers follow vanilla progress: copper, iron, lapis, diamond, netherite. */
const TIERS = ["copper", "iron", "lapis", "diamond", "netherite"];
const MAX_TIER = TIERS.length;
const UPGRADES = {};
for (const [i, tier] of TIERS.entries()) {
  for (const track of ["speed", "storage", "research"]) {
    const cap = (s) => s[0].toUpperCase() + s.slice(1);
    UPGRADES[`minecoins:${track}_module_${tier}`] = {
      key: track,
      tier: i + 1,
      label: `${cap(tier)} ${cap(track)}`,
    };
  }
}
function upgradeItem(key, tier) {
  const i = Math.max(1, Math.min(MAX_TIER, tier)) - 1;
  return `minecoins:${key}_module_${TIERS[i]}`;
}
const DRIVE = "minecoins:flash_drive";
const STACK = 64;              // one vault slot holds one stack
const SLOTS_PER_RACK = 27;     // a lone rack opens 27 slots
const SLOTS_PER_STORAGE = 27;  // every storage module adds 27 more
const GEN_PER_GENERATOR = 40;  // EU/s while a generator burns
const DRAW_PER_TERMINAL = 2;   // EU/s
const FUEL_SECONDS = {
  "minecraft:coal": 60,
  "minecraft:charcoal": 45,
  "minecraft:leaf_litter": 6,
};
/* Research opens catalogue bands, one per tier of module. */
const RESEARCH_UNLOCK = {
  "Blocks": 0, "Materials": 1, "Food": 1, "Redstone": 2,
  "Tools": 3, "Armor": 3, "Enchanted Books": 4, "Diamond": 5,
};

function refreshPipe(dim, loc) {
  const b = dim.getBlock(loc);
  if (!b) return;
  const links = PIPE_LINKS_BY_TYPE[b.typeId];
  if (!links) return;
  const states = {};
  for (const [state, dx, dy, dz] of PIPE_LINKS) {
    const n = dim.getBlock({ x: loc.x + dx, y: loc.y + dy, z: loc.z + dz });
    states[state] = !!n && links.has(n.typeId);
  }
  try { b.setPermutation(BlockPermutation.resolve(b.typeId, states)); } catch { /* ignore */ }
}

/* Racks join to their horizontal neighbours, wall-fashion. */
const RACK_LINKS = [
  ["minecoins:north", 0, 0, -1],
  ["minecoins:south", 0, 0, 1],
  ["minecoins:east", 1, 0, 0],
  ["minecoins:west", -1, 0, 0],
];

function refreshRack(dim, loc) {
  const b = dim.getBlock(loc);
  if (!b || b.typeId !== B.rack) return;
  const states = {};
  for (const [state, dx, dy, dz] of RACK_LINKS) {
    const n = dim.getBlock({ x: loc.x + dx, y: loc.y + dy, z: loc.z + dz });
    states[state] = !!n && n.typeId === B.rack;
  }
  states["minecoins:module"] = b.permutation.getState("minecoins:module") ?? "none";
  try { b.setPermutation(BlockPermutation.resolve(B.rack, states)); } catch { /* ignore */ }
}

function refreshAround(dim, loc) {
  refreshPipe(dim, loc);
  refreshRack(dim, loc);
  for (const o of [[0, 0, -1], [0, 0, 1], [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0]]) {
    const n = { x: loc.x + o[0], y: loc.y + o[1], z: loc.z + o[2] };
    refreshPipe(dim, n);
    refreshRack(dim, n);
  }
}

const P_NODES = "mc:nodes";
const P_RACKS = "mc:racks";
const P_ENERGY = "mc:energy";
const P_CHAIN = "mc:chain";
const P_COINS = "mc:coins";
const P_LAST = "mc:last";
const P_STORE = "mc:store";
const P_HEAT = "mc:heat";
const P_MODS = "mc:rackmods";
const P_FUEL = "mc:fuel";
const P_TERM = "mc:terminal";

/* ------------------------------------------------------------------ catalog */
const PRICE = { 1: 2, 2: 6, 3: 14, 4: 25, 5: 50, 6: 75 };

const RAW_CATALOG = {
  "Blocks": `
    stone|1 cobblestone|1 deepslate|1 dirt|1 sand|1 gravel|1 clay|1 netherrack|1 end_stone|2
    glass|1 glass_pane|1 oak_planks|1 spruce_planks|1 birch_planks|1 jungle_planks|1
    acacia_planks|1 dark_oak_planks|1 mangrove_planks|1 cherry_planks|1
    oak_log|1 spruce_log|1 birch_log|1 jungle_log|1 acacia_log|1 dark_oak_log|1
    bricks|2 stone_bricks|2 sandstone|1 obsidian|3 glowstone|2 moss_block|2
    iron_block|3 gold_block|3 coal_block|2 emerald_block|4 lapis_block|3 redstone_block|3
    copper_block|3 amethyst_block|3 quartz_block|3
    white_wool|1 black_wool|1 red_wool|1 blue_wool|1 green_wool|1`,
  "Materials": `
    coal|1 charcoal|1 iron_ingot|2 copper_ingot|2 gold_ingot|3 netherite_scrap|4 netherite_ingot|4
    redstone|1 lapis_lazuli|2 emerald|3 quartz|2 amethyst_shard|2 stick|1 string|1 feather|1
    leather|1 flint|1 gunpowder|2 bone|1 bone_meal|1 blaze_rod|2 blaze_powder|2 ender_pearl|3
    ghast_tear|3 slime_ball|2 magma_cream|2 phantom_membrane|2 honeycomb|2 clay_ball|1 brick|1
    paper|1 book|1 sugar|1 wheat|1 egg|1 glass_bottle|1 spider_eye|1 fermented_spider_eye|2
    ink_sac|1 glow_ink_sac|2 prismarine_shard|2 nautilus_shell|3 heart_of_the_sea|4
    turtle_scute|3 honey_bottle|2 name_tag|3 saddle|4 lead|2`,
  "Tools": `
    wooden_sword|1 wooden_pickaxe|1 wooden_axe|1 wooden_shovel|1 wooden_hoe|1
    stone_sword|1 stone_pickaxe|1 stone_axe|1 stone_shovel|1 stone_hoe|1
    golden_sword|2 golden_pickaxe|2 golden_axe|2 golden_shovel|2 golden_hoe|2
    iron_sword|3 iron_pickaxe|3 iron_axe|3 iron_shovel|3 iron_hoe|3
    bow|2 crossbow|3 arrow|1 spectral_arrow|2 trident|4 shield|3 fishing_rod|2
    flint_and_steel|2 shears|2 bucket|2 water_bucket|2 lava_bucket|3 milk_bucket|2
    compass|3 clock|3 spyglass|3`,
  "Armor": `
    leather_helmet|1 leather_chestplate|1 leather_leggings|1 leather_boots|1
    golden_helmet|2 golden_chestplate|2 golden_leggings|2 golden_boots|2
    chainmail_helmet|2 chainmail_chestplate|2 chainmail_leggings|2 chainmail_boots|2
    iron_helmet|3 iron_chestplate|3 iron_leggings|3 iron_boots|3
    turtle_helmet|3 netherite_helmet|4 netherite_chestplate|4 netherite_leggings|4 netherite_boots|4`,
  "Food": `
    apple|1 golden_apple|4 bread|1 cooked_beef|2 cooked_porkchop|2 cooked_chicken|2
    cooked_mutton|2 cooked_rabbit|2 cooked_cod|2 cooked_salmon|2 carrot|1 potato|1
    baked_potato|1 beetroot|1 melon_slice|1 sweet_berries|1 glow_berries|2 cake|3 cookie|1
    pumpkin_pie|2 mushroom_stew|2 rabbit_stew|2 beetroot_soup|2 dried_kelp|1`,
  "Redstone": `
    redstone_torch|2 repeater|2 comparator|2 piston|2 sticky_piston|3 observer|3 hopper|3
    dropper|2 dispenser|2 lever|1 stone_button|1 stone_pressure_plate|1 tripwire_hook|2
    target|2 daylight_detector|3 note_block|1 jukebox|2 rail|1 powered_rail|2 detector_rail|2
    activator_rail|2 minecart|3 chest_minecart|3 hopper_minecart|3 tnt|2 redstone_lamp|2
    iron_door|2 iron_trapdoor|2 oak_door|1 oak_trapdoor|1 ladder|1 torch|1 lantern|2
    soul_lantern|2 campfire|1 anvil|4 enchanting_table|4 bookshelf|3 brewing_stand|3
    cauldron|3 crafting_table|1 furnace|1 blast_furnace|3 smoker|3 chest|1 barrel|1 red_bed|2`,
  // Enchanted books: tier 4, one below the diamond tier.
  "Enchanted Books": `enchanted_book|4`,
  // Most expensive tier: diamonds and diamond equipment.
  "Diamond": `
    diamond|6 diamond_block|6 diamond_ore|6
    diamond_sword|5 diamond_pickaxe|5 diamond_axe|5 diamond_shovel|5 diamond_hoe|5
    diamond_helmet|5 diamond_chestplate|5 diamond_leggings|5 diamond_boots|5`,
};

const BUY = new Map(); // id -> { price, cat, name }
const CATALOG = {};    // cat -> [ids]
for (const [cat, raw] of Object.entries(RAW_CATALOG)) {
  CATALOG[cat] = [];
  for (const token of raw.trim().split(/\s+/)) {
    if (!token) continue;
    const [shortId, tier] = token.split("|");
    const id = "minecraft:" + shortId;
    BUY.set(id, { price: PRICE[tier], tier: Number(tier), cat, name: pretty(shortId) });
    CATALOG[cat].push(id);
  }
}

function pretty(id) {
  return id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/* -------------------------------------------------------------- persistence */
function readList(prop) {
  try {
    const v = world.getDynamicProperty(prop);
    return v ? JSON.parse(v) : [];
  } catch { return []; }
}
function writeList(prop, arr) {
  try { world.setDynamicProperty(prop, JSON.stringify(arr)); } catch { /* full */ }
}
function readMap(prop) {
  try {
    const v = world.getDynamicProperty(prop);
    return v ? JSON.parse(v) : {};
  } catch { return {}; }
}
function writeMap(prop, obj) {
  try { world.setDynamicProperty(prop, JSON.stringify(obj)); } catch { /* full */ }
}
function key(e) { return `${e.d}|${e.x}|${e.y}|${e.z}`; }
function locKey(dimId, loc) {
  return `${dimId}|${Math.floor(loc.x)}|${Math.floor(loc.y)}|${Math.floor(loc.z)}`;
}

function addEntry(prop, e) {
  const list = readList(prop);
  if (list.some((o) => key(o) === key(e))) return;
  list.push(e);
  writeList(prop, list);
}
function removeEntry(prop, e) {
  writeList(prop, readList(prop).filter((o) => key(o) !== key(e)));
}

/* ------------------------------------------------------------------ coins */
function coins(p) {
  const v = p.getDynamicProperty(P_COINS);
  return typeof v === "number" ? v : 0;
}
function setCoins(p, n) {
  p.setDynamicProperty(P_COINS, Math.max(0, Math.floor(n)));
}
function hash(str) {
  let x = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    x ^= str.charCodeAt(i);
    x = Math.imul(x, 0x01000193);
  }
  return (x >>> 0).toString(16).padStart(8, "0");
}
/** Append an immutable-ish block to the minecoin ledger. */
function ledger(player, amount, kind) {
  const chain = readList(P_CHAIN);
  const prev = chain.length ? chain[chain.length - 1].h : "00000000";
  chain.push({
    h: hash(`${prev}|${player.id}|${amount}|${kind}|${Date.now()}|${chain.length}`),
    prev,
    p: player.name.slice(0, 16),
    a: amount,
    k: kind,
    t: Date.now(),
  });
  while (chain.length > 64) chain.shift();
  writeList(P_CHAIN, chain);
}

system.runInterval(() => {
  const now = Date.now();
  for (const p of world.getAllPlayers()) {
    let last = p.getDynamicProperty(P_LAST);
    if (typeof last !== "number") { p.setDynamicProperty(P_LAST, now); continue; }
    const gap = now - last;
    // Left the world for a while: do not pay out offline time.
    if (gap > COIN_MS * 2) { p.setDynamicProperty(P_LAST, now); continue; }
    if (gap < COIN_MS) continue;
    let cycles = 0;
    while (now - last >= COIN_MS) { last += COIN_MS; cycles++; }
    p.setDynamicProperty(P_LAST, last);
    const paying = Math.max(1, payRate(p.dimension));
    const gained = paying * cycles;
    const bal = coins(p) + gained;
    setCoins(p, bal);
    ledger(p, gained, "mine");
    p.sendMessage(`§b[Minecoins] §f+${gained} minecoin§7 · balance §e${bal}§7 · ${paying} rack${paying === 1 ? "" : "s"} paying`);
    p.playSound("random.orb", { volume: 0.6, pitch: 1.4 });
    p.onScreenDisplay.setActionBar(`§e+${gained} minecoin §7(${bal})`);
  }
}, 40);

/* ----------------------------------------------- tablet held in the offhand */
function offhandTablet(player) {
  try {
    const eq = player.getComponent("minecraft:equippable");
    const item = eq?.getEquipment(EquipmentSlot.Offhand);
    return !!item && item.typeId === TABLET;
  } catch { return false; }
}

system.runInterval(() => {
  for (const p of world.getAllPlayers()) {
    if (!offhandTablet(p)) continue;
    const rack = nearestRack(p);
    if (!rack) {
      p.onScreenDisplay.setActionBar("§8[server] §7no rack within 48 blocks");
      continue;
    }
    const g = evalGrid(p.dimension, rack, false);
    if (!g.rack) continue;
    const heat = Math.round(Math.max(0, ...g.racks.map((r) => r.heat ?? 0)));
    const pct = g.capacity ? Math.round((g.energy / g.capacity) * 100) : 0;
    const heatColour = heat >= 80 ? "§c" : heat >= 45 ? "§e" : "§a";
    const battColour = pct >= 50 ? "§a" : pct > 10 ? "§e" : "§c";
    p.onScreenDisplay.setActionBar(
      `§8[server] §7heat ${heatColour}${heat}%§7 · ` +
      `§7coins §e${g.perMin.toFixed(1)}§7/min §8(§f${g.live}§7/§f${g.rack}§8)§7 · ` +
      `§7battery ${battColour}${pct}%§7 · §7solar §f${g.gen}§7/§f${g.draw}§7 EU/s`);
  }
}, 40);

/* ------------------------------------------------------------- block events */
world.afterEvents.playerPlaceBlock.subscribe((ev) => {
  const id = ev.block.typeId;
  const e = {
    d: ev.block.dimension.id,
    x: ev.block.location.x,
    y: ev.block.location.y,
    z: ev.block.location.z,
  };
  if (NODE_BLOCKS.includes(id)) {
    addEntry(P_NODES, e);
    if (id === B.tower) ev.player.sendMessage("§b[Radio] §fTower online §7· range 1500 blocks");
    else ev.player.sendMessage("§b[Radio] §fExtender linked §7· needs a tower within 1500 blocks");
  }
  if (id === B.rack) addEntry(P_RACKS, e);
  if (PIPE_IDS.has(id) || GRID_BLOCKS.includes(id) || NODE_BLOCKS.includes(id)) {
    const dim = ev.block.dimension;
    const at = { x: ev.block.location.x, y: ev.block.location.y, z: ev.block.location.z };
    refreshAround(dim, at);
    system.run(() => refreshAround(dim, at));
  }
});

world.afterEvents.playerBreakBlock.subscribe((ev) => {
  const id = ev.brokenBlockPermutation.type.id;
  const e = {
    d: ev.block.dimension.id,
    x: ev.block.location.x,
    y: ev.block.location.y,
    z: ev.block.location.z,
  };
  if (NODE_BLOCKS.includes(id)) removeEntry(P_NODES, e);
  if (id === B.rack) removeEntry(P_RACKS, e);
  if (PIPE_IDS.has(id) || GRID_BLOCKS.includes(id) || NODE_BLOCKS.includes(id)) {
    const dim = ev.block.dimension;
    const at = { x: ev.block.location.x, y: ev.block.location.y, z: ev.block.location.z };
    refreshAround(dim, at);
    system.run(() => refreshAround(dim, at));
  }
});

/* ------------------------------------------------------------------ radio */
function dist(a, b) {
  const dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

function liveNodes(dimId) {
  const dim = world.getDimension(dimId);
  const out = [];
  for (const e of readList(P_NODES)) {
    if (e.d !== dimId) continue;
    const b = dim.getBlock({ x: e.x, y: e.y, z: e.z });
    if (!b || !NODE_BLOCKS.includes(b.typeId)) continue;
    out.push({ ...e, type: b.typeId });
  }
  return out;
}

/** Towers extend the network through extenders, each link up to 1500 blocks. */
function reachableNodes(dimId) {
  const nodes = liveNodes(dimId);
  const live = new Set();
  const queue = [];
  for (const n of nodes) {
    if (n.type === B.tower) { live.add(key(n)); queue.push(n); }
  }
  while (queue.length) {
    const cur = queue.pop();
    for (const n of nodes) {
      if (live.has(key(n))) continue;
      if (dist(cur, n) <= RANGE) { live.add(key(n)); queue.push(n); }
    }
  }
  return nodes.filter((n) => live.has(key(n)));
}

function isUnderground(player) {
  const d = player.dimension;
  const x = Math.floor(player.location.x);
  const y = Math.floor(player.location.y);
  const z = Math.floor(player.location.z);
  for (let i = 1; i <= 40; i++) {
    const b = d.getBlock({ x, y: y + i, z });
    if (!b) return false;
    if (!b.isAir && !b.isLiquid) return true;
  }
  return false;
}

function signalFor(player) {
  const nodes = reachableNodes(player.dimension.id);
  if (!nodes.length) {
    return { ok: false, why: "§cNo radio tower in this dimension.", underground: isUnderground(player) };
  }
  const underground = isUnderground(player);
  if (underground) {
    // No radio underground. Storage is reached with a drive and a terminal instead.
    return { ok: false, why: "§cNo signal underground — carry a paired flash drive to a powered terminal.", underground };
  }
  const near = nodes.some((n) => dist(n, player.location) <= RANGE);
  if (!near) return { ok: false, why: `§cOut of range — no radio node within ${RANGE} blocks.`, underground };
  return { ok: true, why: "§aRadio signal", underground };
}

/* ------------------------------------------------------------------- power */
const GEN_PER_PANEL = 25;   // EU/s
const DRAW_PER_RACK = 8;    // EU/s
const DRAW_PER_COOLER = 3;  // EU/s
const BATTERY_CAP = 5000;

function evalGrid(dim, start, apply = true) {
  const counts = { panel: 0, battery: 0, cooling: 0, rack: 0, generator: 0, terminal: 0 };
  const cells = [];
  const racks = [];
  const gens = [];
  const mods = readMap(P_MODS);
  const fuel = readMap(P_FUEL);
  const seen = new Set();
  const queue = [start];
  const sx = start.x, sy = start.y, sz = start.z;
  while (queue.length && seen.size < GRID_LIMIT) {
    const loc = queue.shift();
    const k = `${loc.x},${loc.y},${loc.z}`;
    if (seen.has(k)) continue;
    if (Math.abs(loc.x - sx) + Math.abs(loc.y - sy) + Math.abs(loc.z - sz) > 96) continue;
    seen.add(k);
    const b = dim.getBlock(loc);
    if (!b) continue;
    const t = b.typeId;
    if (t === B.panel) counts.panel++;
    else if (t === B.battery) {
      counts.battery++;
      cells.push({ loc: { x: loc.x, y: loc.y, z: loc.z }, cap: BATTERY_CAP });
    } else if (t === B.cooling) counts.cooling++;
    else if (t === B.rack) {
      counts.rack++;
      const module = b.permutation.getState("minecoins:module") ?? "none";
      const up = mods[locKey(dim.id, loc)] ?? {};
      racks.push({
        x: loc.x, y: loc.y, z: loc.z, module,
        speed: up.speed ?? 0, storage: up.storage ?? 0, research: up.research ?? 0,
      });
      if (module === "battery" || module === "both") {
        cells.push({ loc: { x: loc.x, y: loc.y, z: loc.z }, cap: RACK_BATTERY_CAP });
      }
    } else if (t === B.generator) {
      counts.generator++;
      gens.push({ x: loc.x, y: loc.y, z: loc.z });
    } else if (t === B.terminal) {
      counts.terminal++;
    } else if (t !== B.cable) continue;
    for (const o of [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]]) {
      queue.push({ x: loc.x + o[0], y: loc.y + o[1], z: loc.z + o[2] });
    }
  }

  const burning = gens.filter((g) => {
    const rec = fuel[locKey(dim.id, g)];
    return !!rec && rec.s > 0;
  }).length;
  const gen = counts.panel * GEN_PER_PANEL + burning * GEN_PER_GENERATOR;
  const draw = counts.rack * DRAW_PER_RACK + counts.cooling * DRAW_PER_COOLER
    + counts.terminal * DRAW_PER_TERMINAL;
  const store = readMap(P_ENERGY);
  const now = Date.now();
  const capacity = cells.reduce((a, c) => a + c.cap, 0);
  let total = 0;
  let oldest = now;
  for (const cell of cells) {
    const rec = store[locKey(dim.id, cell.loc)];
    total += rec && typeof rec.e === "number" ? rec.e : 0;
    if (rec && typeof rec.t === "number") oldest = Math.min(oldest, rec.t);
  }
  const elapsed = Math.min((now - oldest) / 1000, 6 * 3600);
  total = Math.max(0, Math.min(capacity, total + (gen - draw) * elapsed));

  const day = world.getTimeOfDay() < 12000;
  const coolingModules = racks.filter((r) => r.module === "cooling" || r.module === "both").length;
  const cooled = counts.cooling > 0 || coolingModules > 0;
  const result = {
    ok: counts.rack > 0 && cooled && total > 0,
    cooled,
    energy: total,
    gen: day ? gen : 0,
    draw,
    capacity,
    racks,
    ...counts,
  };

  const heat = apply ? applyHeat(dim, result, now) : readMap(P_HEAT);
  for (const r of result.racks) {
    const rec = heat[locKey(dim.id, r)];
    r.heat = rec && typeof rec.h === "number" ? rec.h : 0;
  }
  result.hot = result.racks.filter((r) => r.heat >= HEAT_MAX).length;
  result.live = result.racks.length - result.hot;
  result.ok = result.ok && result.live > 0;
  result.pay = result.racks
    .filter((r) => r.heat < HEAT_MAX)
    .reduce((a, r) => a + 1 + (r.speed ?? 0), 0);
  result.perMin = result.pay / 5;
  result.slots = counts.rack * SLOTS_PER_RACK
    + result.racks.reduce((a, r) => a + (r.storage ?? 0), 0) * SLOTS_PER_STORAGE;
  result.research = result.racks.reduce((a, r) => Math.max(a, r.research ?? 0), 0);

  if (apply && gens.length) {
    let touched = false;
    for (const g of gens) {
      const k = locKey(dim.id, g);
      const rec = fuel[k];
      if (!rec || !(rec.s > 0)) continue;
      rec.s = Math.max(0, rec.s - elapsed);
      fuel[k] = rec;
      touched = true;
      setGeneratorLit(dim, g, rec.s > 0);
    }
    if (touched) writeMap(P_FUEL, fuel);
  }

  if (apply && cells.length) {
    const unit = capacity ? total / capacity : 0;
    for (const cell of cells) store[locKey(dim.id, cell.loc)] = { e: unit * cell.cap, t: now };
    const keys = Object.keys(store);
    if (keys.length > 250) {
      keys.sort((a, b) => (store[a].t || 0) - (store[b].t || 0));
      for (const k of keys.slice(0, keys.length - 250)) delete store[k];
    }
    writeMap(P_ENERGY, store);
  }
  return result;
}

/** Heat climbs while a powered rack runs and falls once it is cooled. */
function applyHeat(dim, grid, now) {
  const map = readMap(P_HEAT);
  for (const r of grid.racks) {
    const k = locKey(dim.id, r);
    const prev = map[k];
    const dt = prev && typeof prev.t === "number" ? Math.min((now - prev.t) / 1000, 120) : 0;
    let h = prev && typeof prev.h === "number" ? prev.h : 0;
    if (grid.energy > 0) h += HEAT_GAIN * dt;
    if (grid.cooled) h -= HEAT_DROP * dt;
    map[k] = { h: Math.max(0, Math.min(HEAT_MAX, h)), t: now };
  }
  const keys = Object.keys(map);
  if (keys.length > 250) {
    keys.sort((a, b) => (map[a].t || 0) - (map[b].t || 0));
    for (const k of keys.slice(0, keys.length - 250)) delete map[k];
  }
  writeMap(P_HEAT, map);
  return map;
}

/** Coins per five minutes: a live rack pays 1, each speed tier pays 1 more. */
function payRate(dim) {
  const done = new Set();
  let pay = 0;
  for (const e of readList(P_RACKS)) {
    if (e.d !== dim.id) continue;
    if (done.has(locKey(dim.id, e))) continue;
    const b = dim.getBlock({ x: e.x, y: e.y, z: e.z });
    if (!b || b.typeId !== B.rack) continue;
    const g = evalGrid(dim, e, true);
    for (const r of g.racks) done.add(locKey(dim.id, r));
    if (g.energy > 0) pay += g.pay;
  }
  return pay;
}

function nearestRack(player) {
  const dimId = player.dimension.id;
  let best = null, bestD = Infinity;
  for (const e of readList(P_RACKS)) {
    if (e.d !== dimId) continue;
    const d = dist(e, player.location);
    if (d < bestD) { bestD = d; best = e; }
  }
  return bestD <= RACK_REACH ? best : null;
}

function serverStatus(player) {
  const rack = nearestRack(player);
  if (!rack) return { ok: false, why: "§cNo server rack within 48 blocks.", grid: null };
  const grid = evalGrid(player.dimension, rack, true);
  if (!grid.rack) return { ok: false, why: "§cServer rack missing.", grid: null };
  if (grid.energy <= 0) return { ok: false, why: "§cNo power — charge a battery with solar panels.", grid };
  if (!grid.cooled) return { ok: false, why: "§cNo cooling — hold a Cooling Unit and use it on the rack.", grid };
  if (grid.live === 0) return { ok: false, why: "§cEvery rack is at 100% heat — let the cooling catch up.", grid };
  return { ok: true, why: "§aServer online", grid };
}

/* --------------------------------------------------------- digital storage */
function loadStore(player) {
  try {
    const v = player.getDynamicProperty(P_STORE);
    return v ? JSON.parse(v) : {};
  } catch { return {}; }
}
function saveStore(player, s) {
  player.setDynamicProperty(P_STORE, JSON.stringify(s));
}
function totalStored(s) {
  return Object.values(s).reduce((a, b) => a + b, 0);
}
/** One slot holds one stack, so a big count costs more than one slot. */
function slotsFor(count) {
  return Math.ceil(count / STACK);
}
function slotsUsed(s) {
  return Object.values(s).reduce((a, c) => a + slotsFor(c), 0);
}

/** Pick how many to move: 1, 8, 16, 32, 64, or the whole stack. */
async function askAmount(player, max, heading) {
  const steps = [1, 8, 16, 32, 64].filter((n) => n <= max);
  if (!steps.includes(max)) steps.push(max);
  const form = new ActionFormData()
    .title(WIN_TITLE)
    .body(winBody(heading, [`§7Available§8: §f${max}`, `§8Pick how many to move.`]));
  for (const n of steps) form.button(BTN(`§f${n}`));
  const res = await show(form, player);
  if (res.canceled || res.selection === undefined) return 0;
  return steps[res.selection] ?? 0;
}

function giveItem(player, id, amount) {
  const inv = player.getComponent("minecraft:inventory");
  if (!inv) return false;
  const stack = new ItemStack(id, amount);
  if (id === "minecraft:enchanted_book") {
    try {
      const ench = stack.getComponent("minecraft:enchantable");
      const pool = ["protection", "sharpness", "efficiency", "unbreaking", "fortune", "power", "mending", "looting"];
      const type = pool[Math.floor(Math.random() * pool.length)];
      ench?.addEnchantment({ type, level: 1 + Math.floor(Math.random() * 3) });
    } catch { /* keep plain book */ }
  }
  const left = inv.container.addItem(stack);
  if (left) player.dimension.spawnItem(left, player.location);
  return true;
}

async function openStorage(player, grid, label = "VAULT") {
  if (!grid || !grid.rack) {
    player.sendMessage("§b[Storage] §cNo server behind this vault.");
    return;
  }
  const capacity = grid.slots;
  const eq = player.getComponent("minecraft:equippable");
  let page = 0;
  for (;;) {
    const store = loadStore(player);
    const used = slotsUsed(store);
    const entries = Object.entries(store).filter(([, c]) => c > 0).sort((a, b) => b[1] - a[1]);
    const per = 15;
    const pages = Math.max(1, Math.ceil(entries.length / per));
    page = Math.max(0, Math.min(page, pages - 1));
    const slice = entries.slice(page * per, page * per + per);
    const held = eq?.getEquipment(EquipmentSlot.Mainhand);

    const form = new ActionFormData()
      .title(WIN_TITLE)
      .body(winBody(`My Documents — ${label}`, [
        `Slots§8: §f${used}§7/§f${capacity}§7 · items §f${totalStored(store)}`,
        `Held§8: ${held ? `§f${held.typeId.replace("minecraft:", "").replace(/_/g, " ")} §7x§f${held.amount}` : "§7nothing"}`,
        statusLine(grid),
        `§8Page ${page + 1}/${pages}`,
      ]))
      .button(BTN("§8[§9 Deposit held stack §8]"), UI_ICON.docs)
      .button(BTN("§8[§9 Server status §8]"), UI_ICON.computer);
    for (const [id, c] of slice) {
      form.button(BTN(`§f${id.replace("minecraft:", "").replace(/_/g, " ")} §7x§e${c}`), UI_ICON.store);
    }
    if (pages > 1) { form.button(BTN("§8< Previous")); form.button(BTN("§8Next >")); }

    const res = await show(form, player);
    if (res.canceled || res.selection === undefined) return;
    const sel = res.selection;

    if (sel === 0) {
      const stack = eq?.getEquipment(EquipmentSlot.Mainhand);
      if (!stack) { player.sendMessage("§b[Storage] §cHold a stack to deposit."); continue; }
      const want = await askAmount(player, stack.amount, "Deposit how many?");
      if (!want) continue;
      const s = loadStore(player);
      const id = stack.typeId;
      const before = slotsFor(s[id] || 0);
      const after = slotsFor((s[id] || 0) + want);
      if (slotsUsed(s) + (after - before) > capacity) {
        player.sendMessage("§b[Storage] §cOut of slots — fit a storage module or add a rack.");
        player.playSound("note.bass");
        continue;
      }
      s[id] = (s[id] || 0) + want;
      saveStore(player, s);
      if (stack.amount > want) stack.amount -= want;
      else eq.setEquipment(EquipmentSlot.Mainhand, undefined);
      player.playSound("random.pop");
      player.sendMessage(`§b[Storage] §f+${want} ${id.replace("minecraft:", "").replace(/_/g, " ")}`);
      continue;
    }
    if (sel === 1) { await openStatus(player, grid); continue; }

    const idx = sel - 2;
    if (idx >= 0 && idx < slice.length) {
      const [id, count] = slice[idx];
      const want = await askAmount(player, Math.min(count, 64), "Withdraw how many?");
      if (!want) continue;
      const s = loadStore(player);
      s[id] = (s[id] || 0) - want;
      if (s[id] <= 0) delete s[id];
      saveStore(player, s);
      giveItem(player, id, want);
      player.playSound("random.pop");
      player.sendMessage(`§b[Storage] §f-${want} ${id.replace("minecraft:", "").replace(/_/g, " ")}`);
      continue;
    }
    if (pages > 1) {
      const nav = sel - 2 - slice.length;
      if (nav === 0) page--;
      else if (nav === 1) page++;
    }
  }
}

async function openStatus(player, grid) {
  const nodes = reachableNodes(player.dimension.id);
  const sig = signalFor(player);
  await show(
    new ActionFormData()
      .title(WIN_TITLE)
      .body(winBody("System Properties", [
        statusLine(grid ?? null),
        `Panels §f${grid?.panel ?? 0}§7  Batteries §f${grid?.battery ?? 0}§7  Cooling §f${grid?.cooling ?? 0}§7  Racks §f${grid?.rack ?? 0}`,
        `Live racks§8: §f${grid?.live ?? 0}§7/§f${grid?.rack ?? 0}§7 · heat §f${Math.round(Math.max(0, ...(grid?.racks ?? []).map((r) => r.heat ?? 0)))}%§7 · payout §e${(grid?.perMin ?? 0).toFixed(1)}§7/min`,
        `Vault§8: §f${grid?.slots ?? 0}§7 slots · research §f${grid?.research ?? 0}§7 · generators §f${grid?.generator ?? 0}§7 · terminals §f${grid?.terminal ?? 0}`,
        `Radio nodes §f${nodes.length}§7 (range §f${RANGE}§7 each)`,
        `Link§8: ${sig.why}`,
        `§8Power flows through power cable; cooling sits on the rack's grid.`,
      ]))
      .button(BTN("§8[§9 OK §8]")),
    player
  );
}

async function openBuy(player, cat, grid) {
  for (;;) {
    const list = CATALOG[cat] || [];
    const form = new ActionFormData()
      .title(WIN_TITLE)
      .body(winBody(`Exploring — C:\\MINECOINS\\STORE\\${cat.toUpperCase()}`, [
        `Balance§8: §e${coins(player)} minecoins`,
        statusLine(grid),
      ]))
      .button(BTN("§8[§9 .. (up one level) §8]"), UI_ICON.computer);
    const level = grid ? grid.research ?? 0 : 0;
    const need = RESEARCH_UNLOCK[cat] ?? 0;
    for (const id of list) {
      const info = BUY.get(id);
      if (need > level) {
        form.button(BTN(`§8${info.name} - locked`));
        continue;
      }
      form.button(BTN(`§f${info.name} §7- §e${info.price}`), iconFor(id));
    }
    const res = await show(form, player);
    if (res.canceled || res.selection === undefined) return false;
    if (res.selection === 0) return true;
    const id = list[res.selection - 1];
    if (!id) return false;
    const info = BUY.get(id);
    if ((RESEARCH_UNLOCK[cat] ?? 0) > (grid ? grid.research ?? 0 : 0)) {
      player.sendMessage(`§b[Store] §c${cat} needs research tier ${RESEARCH_UNLOCK[cat]} — fit a module to a rack.`);
      player.playSound("note.bass");
      continue;
    }
    const bal = coins(player);
    if (bal < info.price) {
      player.sendMessage(`§b[Minecoins] §cNeed ${info.price - bal} more minecoins.`);
      player.playSound("note.bass");
      continue;
    }
    setCoins(player, bal - info.price);
    giveItem(player, id, 1);
    ledger(player, -info.price, "buy");
    player.playSound("random.levelup", { volume: 0.5 });
    player.sendMessage(`§b[Minecoins] §f-${info.price} §7bought §f${info.name} §7· balance §e${bal - info.price}`);
  }
}

function iconFor(id) {
  const short = id.replace("minecraft:", "");
  if (BUY.get(id)?.cat === "Enchanted Books") return "textures/items/enchanted_book";
  if (["sword", "pickaxe", "axe", "shovel", "hoe"].some((t) => short.endsWith("_" + t))) {
    return `textures/items/${short}`;
  }
  return undefined;
}

async function openChain(player) {
  const chain = readList(P_CHAIN).slice(-8).reverse();
  const lines = chain.length
    ? chain.map((b) => `${b.h} ${b.a >= 0 ? "§a+" : "§c"}${b.a} §f${b.k} §8(${b.p})`)
    : ["§7Ledger is empty — mine a minecoin first."];
  await show(
    new ActionFormData()
      .title(WIN_TITLE)
      .body(winBody("Notepad — LEDGER.DAT", [
        `Blocks §f${readList(P_CHAIN).length}§7/64 §8(hash-chained)`,
        ...lines,
      ]))
      .button(BTN("§8[§9 OK §8]")),
    player
  );
}

/* ---------------------------------------------------------------- tablet UI */
/* --------------------------------------------------------- tablet desktop */
/* Plain server-form desktop: one button per program, no pointer state. */
const PROGRAMS = [
  { name: "My Computer", act: "status", icon: UI_ICON.computer },
  { name: "Network Neighborhood", act: "network", icon: UI_ICON.computer },
  { name: "Minecoins.exe", act: "chain", icon: UI_ICON.coins },
  { name: "Store", act: "store", icon: UI_ICON.store },
  { name: "My Documents", act: "storage", icon: UI_ICON.docs },
];

async function launchProgram(player, act, grid) {
  if (act === "status") return openStatus(player, grid);
  if (act === "network") return openNetwork(player);
  if (act === "chain") return openChain(player);
  if (act === "store") return openStore(player, grid);
  if (act === "storage") return openStorage(player, grid, "TABLET");
  return undefined;
}

async function openDesktop(player, label = "Tablet") {
  const sig = signalFor(player);
  if (!sig.ok) {
    player.sendMessage(`§b[${label}] ${sig.why}`);
    player.onScreenDisplay.setActionBar("§cNo connection");
    player.playSound("note.bass");
    return;
  }
  const st = serverStatus(player);
  const form = new ActionFormData()
    .title(WIN_TITLE)
    .body(winBody(`Desktop — ${OS_NAME}`, [
      `§7Minecoins§8: §e${coins(player)} §8· §7Server§8: ${st.ok ? "§aonline" : "§coffline"}`,
      `§7Link§8: ${sig.why}`,
      `§7Storage§8: §f${totalStored(loadStore(player))}§7 items`,
      ``,
      `§8Pick a program. Close the window to shut it down.`,
    ]));
  for (const prog of PROGRAMS) form.button(BTN(`${prog.name}`), prog.icon);
  const res = await show(form, player);
  if (res.canceled || res.selection === undefined) return;
  const picked = PROGRAMS[res.selection];
  if (picked) await launchProgram(player, picked.act, st.grid);
}

async function openNetwork(player) {
  const dimId = player.dimension.id;
  const nodes = reachableNodes(dimId);
  const towers = liveNodes(dimId).filter((n) => n.type === B.tower).length;
  const sig = signalFor(player);
  await show(
    new ActionFormData()
      .title(WIN_TITLE)
      .body(winBody("Network Neighborhood", [
        `§7Radio towers§8: §f${towers} §8· §7live nodes§8: §f${nodes.length}`,
        `§7Range per hop§8: §f${RANGE} §7blocks`,
        `§7Position§8: ${isUnderground(player) ? "§cunderground" : "§asurface"}`,
        `§7Link§8: ${sig.why}`,
        `§8Underground needs a paired drive in a powered terminal, not radio.`,
      ]))
      .button(BTN("§8[§9 OK §8]")),
    player
  );
}

async function openStore(player, grid) {
  for (;;) {
    const cats = Object.keys(CATALOG);
    const menu = new ActionFormData()
      .title(WIN_TITLE)
      .body(winBody("Exploring — C:\\MINECOINS\\STORE", [
        `Balance§8: §e${coins(player)} minecoins`,
        statusLine(grid),
        `§7Research§8: tier §f${grid?.research ?? 0}§8 · §7vault slots§8: §f${grid?.slots ?? 0}`,
        `§8Diamonds are the premium tier; books sit just below.`,
      ]))
      .button(BTN("§8[§9 .. (up one level) §8]"), UI_ICON.computer);
    const level = grid ? grid.research ?? 0 : 0;
    for (const c of cats) {
      const need = RESEARCH_UNLOCK[c] ?? 0;
      menu.button(BTN(need > level ? `§8[${c} §7- tier ${need}§8]` : `§8[§f${c} §8]`), UI_ICON.docs);
    }
    const pick = await show(menu, player);
    if (pick.canceled || pick.selection === undefined || pick.selection === 0) return;
    const cat = cats[pick.selection - 1];
    if (!cat || !CATALOG[cat]) continue;
    if (!(await openBuy(player, cat, grid))) return;
  }
}

/* ------------------------------------------------------------------ guide */
const GUIDE_PAGES = [
  {
    name: "1. Start here",
    lines: [
      "Craft a §fMinecoins Tablet§8: §7iron, glass and redstone.",
      "Craft a §fRadio Tower§8: §7iron, copper and redstone.",
      "Place the tower under open sky, then use the tablet.",
      "Every rack that is powered and cool pays §e1§7 per §f5 real minutes§7.",
      "Hold the tablet in your §foffhand§7 for heat, payout and battery at a glance.",
      "This guide needs no radio signal - read it anywhere.",
    ],
  },
  {
    name: "2. Power grid",
    lines: [
      "§fSolar Panel§7 makes §a25 EU/s§7, and only in daylight.",
      "§fPower Cable§7 links panels, batteries, racks and coolers.",
      "§fBattery§7 stores §a5000 EU§7 each; charge it, then run the rack.",
      "§fServer Rack§7 draws §c8 EU/s§7, each §fCooling Unit§7 §c3 EU/s§7.",
      "Pipes run one tube per axis, up and down included - no wrench needed.",
      "The rack front blinks red, green and blue while it is running.",
    ],
  },
  {
    name: "3. Cooling and storage",
    lines: [
      "A running rack heats up; at §c100%§7 it shuts down and stops paying.",
      "Hold a §fCooling Unit§7 and use it on a rack to bolt cooling in.",
      "Hold a §fBattery§7 the same way: §a1000 EU§7 stored inside the rack.",
      "Sneak and use a rack to pull its modules back out.",
      "The cabinet repaints itself as modules go in: fins, cells, or both.",
      "Click the rack, or pick My Documents on the tablet, to reach the vault.",
      "Deposit or withdraw 1, 8, 16, 32 or 64 at a time.",
      "Slots start at §f27 per rack§7; each Storage Module adds §f27§7 more.",
    ],
  },
  {
    name: "4. Radio and flash drives",
    lines: [
      "The tablet only opens with signal: §f1500 blocks§7 from a tower.",
      "§fRadio Extender§7 repeats the network, hop by hop.",
      "Underground there is no radio at all - carry a drive instead.",
      "Pair a §fFlash Drive§7 by using it on a rack.",
      "Insert it into a §fStorage Terminal§7 and use the terminal.",
      "The terminal needs power: feed a §fGenerator§7 coal, charcoal or leaf litter.",
      "Click a §fMonitor§7 block for the same screens on a wall.",
    ],
  },
  {
    name: "5. Upgrades",
    lines: [
      "Modules climb the usual ladder: §fcopper, iron, lapis, diamond, netherite§7.",
      "Speed§8: §e+1§7 minecoin per 5 minutes per tier, up to §e+5§7.",
      "Storage§8: §f+27§7 vault slots per tier, up to §f162§7 on one rack.",
      "Research§8: one catalogue band per tier - materials at copper, tools at",
      "lapis, books at diamond and the diamond catalogue at netherite.",
      "Fitting a higher tier replaces the module already in that rack.",
    ],
  },
  {
    name: "6. Minecoins and the store",
    lines: [
      "Your balance is shown on the tablet desktop and in the store.",
      "Prices run in tiers: §7 2, 6, 14, 25, 50, 75§7 minecoins.",
      "§bDiamonds§7 and diamond gear sit at the top of the catalog.",
      "§dEnchanted books§7 are the tier just below diamonds.",
      "Minecoins.exe on the tablet shows the hash-chained ledger.",
    ],
  },
];

async function openGuide(player) {
  for (;;) {
    const form = new ActionFormData()
      .title(WIN_TITLE)
      .body(winBody("Minecoins Guide - C:\\MINECOINS\\GUIDE.HLP", [
        `§7Chapters§8: §f${GUIDE_PAGES.length}§8 · §7Minecoins§8: §e${coins(player)}`,
        `§8Choose a chapter. Close the window to put the guide away.`,
      ]));
    for (const page of GUIDE_PAGES) form.button(BTN(`${page.name}`));
    const res = await show(form, player);
    if (res.canceled || res.selection === undefined) return;
    const page = GUIDE_PAGES[res.selection];
    if (!page) continue;
    const back = await show(
      new ActionFormData()
        .title(WIN_TITLE)
        .body(winBody(page.name, page.lines))
        .button(BTN("§8[§9 Back to contents §8]")),
      player
    );
    if (!back || back.canceled || back.selection === undefined) return;
  }
}

/* ------------------------------------------------------------- flash drives */
function bindOf(loc, dimId) {
  return `${dimId}|${Math.floor(loc.x)}|${Math.floor(loc.y)}|${Math.floor(loc.z)}`;
}

function parseBind(bind) {
  if (typeof bind !== "string") return null;
  const [d, x, y, z] = bind.split("|");
  if (!d || x === undefined) return null;
  return { d, x: Number(x), y: Number(y), z: Number(z) };
}

/** Use a drive on a rack to pair it with that server. */
function bindHeldDrive(player, loc) {
  const eq = player.getComponent("minecraft:equippable");
  const stack = eq?.getEquipment(EquipmentSlot.Mainhand);
  if (!stack || stack.typeId !== DRIVE) return false;
  stack.setDynamicProperty("mc:bind", bindOf(loc, player.dimension.id));
  eq.setEquipment(EquipmentSlot.Mainhand, stack);
  return true;
}

function boundGrid(bind) {
  const b = parseBind(bind);
  if (!b) return null;
  try {
    return evalGrid(world.getDimension(b.d), { x: b.x, y: b.y, z: b.z }, false);
  } catch { return null; }
}

function terminalState(block, on) {
  try {
    if (!!block.permutation.getState("minecoins:drive") !== on) {
      block.setPermutation(BlockPermutation.resolve(B.terminal, { "minecoins:drive": on }));
    }
  } catch { /* ignore */ }
}

function insertDrive(player, loc) {
  const eq = player.getComponent("minecraft:equippable");
  const stack = eq?.getEquipment(EquipmentSlot.Mainhand);
  if (!stack || stack.typeId !== DRIVE) {
    player.sendMessage("§b[Terminal] §cHold a flash drive to insert it.");
    return;
  }
  const bind = stack.getDynamicProperty("mc:bind");
  if (typeof bind !== "string") {
    player.sendMessage("§b[Terminal] §cThis drive is blank — use it on a server rack first.");
    return;
  }
  const map = readMap(P_TERM);
  map[locKey(player.dimension.id, loc)] = bind;
  writeMap(P_TERM, map);
  if (stack.amount > 1) stack.amount -= 1;
  else eq.setEquipment(EquipmentSlot.Mainhand, undefined);
  const b = player.dimension.getBlock({ x: loc.x, y: loc.y, z: loc.z });
  if (b) terminalState(b, true);
  player.playSound("random.click");
  player.sendMessage("§b[Terminal] §fDrive inserted.");
}

function ejectDrive(player, loc) {
  const map = readMap(P_TERM);
  const k = locKey(player.dimension.id, loc);
  const bind = map[k];
  const b = player.dimension.getBlock({ x: loc.x, y: loc.y, z: loc.z });
  if (!bind) {
    if (b) terminalState(b, false);
    player.sendMessage("§b[Terminal] §7No drive inserted.");
    return;
  }
  delete map[k];
  writeMap(P_TERM, map);
  if (b) terminalState(b, false);
  const stack = new ItemStack(DRIVE, 1);
  stack.setDynamicProperty("mc:bind", bind);
  const inv = player.getComponent("minecraft:inventory");
  const left = inv?.container.addItem(stack);
  if (left) player.dimension.spawnItem(left, player.location);
  player.playSound("random.pop");
  player.sendMessage("§b[Terminal] §7Drive ejected.");
}

async function openTerminal(player, loc) {
  const dim = player.dimension;
  const block = dim.getBlock({ x: loc.x, y: loc.y, z: loc.z });
  if (!block || block.typeId !== B.terminal) return;
  const drive = readMap(P_TERM)[locKey(dim.id, loc)];
  if (!drive) {
    player.sendMessage("§b[Terminal] §cNo drive inserted — hold a flash drive and use the terminal.");
    player.playSound("note.bass");
    return;
  }
  const grid = evalGrid(dim, loc, true);
  if (grid.energy <= 0) {
    player.sendMessage("§b[Terminal] §cNo power — wire it to a generator and feed the firebox.");
    player.playSound("note.bass");
    return;
  }
  const remote = boundGrid(drive);
  if (!remote || !remote.rack) {
    player.sendMessage("§b[Terminal] §cThat drive points at no server.");
    return;
  }
  await openStorage(player, remote, "FLASH DRIVE");
}

/* ---------------------------------------------------------------- generator */
function setGeneratorLit(dim, loc, on) {
  try {
    const b = dim.getBlock(loc);
    if (!b || b.typeId !== B.generator) return;
    if (!!b.permutation.getState("minecoins:lit") === on) return;
    b.setPermutation(BlockPermutation.resolve(B.generator, { "minecoins:lit": on }));
  } catch { /* ignore */ }
}

function feedGenerator(player, loc) {
  const eq = player.getComponent("minecraft:equippable");
  const stack = eq?.getEquipment(EquipmentSlot.Mainhand);
  if (!stack) return;
  const secs = FUEL_SECONDS[stack.typeId];
  if (!secs) return;
  const map = readMap(P_FUEL);
  const k = locKey(player.dimension.id, loc);
  const rec = map[k] ?? { s: 0, n: 0 };
  const want = Math.min(stack.amount, 16);
  rec.s = Math.min(3600, (rec.s || 0) + secs * want);
  rec.n = (rec.n || 0) + want;
  map[k] = rec;
  writeMap(P_FUEL, map);
  if (stack.amount > want) stack.amount -= want;
  else eq.setEquipment(EquipmentSlot.Mainhand, undefined);
  player.playSound("random.fizz", { volume: 0.4 });
  player.sendMessage(`§b[Generator] §f+${want} fuel §7· §f${Math.round(rec.s)}s in the firebox`);
}

/* ----------------------------------------------------------- rack hardware */
function rackAt(player, loc) {
  const b = player.dimension.getBlock({ x: loc.x, y: loc.y, z: loc.z });
  return b && b.typeId === B.rack ? b : null;
}

function setModuleState(block, module) {
  const states = { "minecoins:module": module };
  for (const [state, dx, dy, dz] of RACK_LINKS) {
    const n = block.dimension.getBlock({
      x: block.location.x + dx, y: block.location.y + dy, z: block.location.z + dz,
    });
    states[state] = !!n && n.typeId === B.rack;
  }
  try { block.setPermutation(BlockPermutation.resolve(B.rack, states)); } catch { /* ignore */ }
}

function installModule(player, loc, want) {
  const block = rackAt(player, loc);
  if (!block) return;
  const cur = block.permutation.getState("minecoins:module") ?? "none";
  if (cur === "both" || cur === want) {
    player.sendMessage("§b[Hardware] §7That rack already carries this module.");
    player.playSound("note.bass");
    return;
  }
  const eq = player.getComponent("minecraft:equippable");
  const held = eq?.getEquipment(EquipmentSlot.Mainhand);
  if (!held || held.typeId !== (want === "cooling" ? B.cooling : B.battery)) {
    player.sendMessage("§b[Hardware] §cHold the module in your mainhand.");
    return;
  }
  if (held.amount > 1) held.amount -= 1;
  else eq.setEquipment(EquipmentSlot.Mainhand, undefined);
  setModuleState(block, cur === "none" ? want : "both");
  player.playSound("random.anvil_use", { volume: 0.5, pitch: 1.4 });
  player.sendMessage(`§b[Hardware] §f${want === "cooling" ? "Cooling" : "Battery"} module fitted §7· rack repainted`);
}

function installUpgrade(player, loc, key, label, tier) {
  const block = rackAt(player, loc);
  if (!block) return;
  const map = readMap(P_MODS);
  const k = locKey(player.dimension.id, loc);
  const rec = map[k] ?? { speed: 0, storage: 0, research: 0 };
  if ((rec[key] || 0) >= tier) {
    player.sendMessage(`§b[Hardware] §7This rack is already at ${label} or better.`);
    player.playSound("note.bass");
    return;
  }
  const eq = player.getComponent("minecraft:equippable");
  const held = eq?.getEquipment(EquipmentSlot.Mainhand);
  if (!held) return;
  if (held.amount > 1) held.amount -= 1;
  else eq.setEquipment(EquipmentSlot.Mainhand, undefined);
  rec[key] = tier;
  map[k] = rec;
  writeMap(P_MODS, map);
  player.playSound("random.anvil_use", { volume: 0.5, pitch: 1.2 });
  player.sendMessage(`§b[Hardware] §f${label}§7 fitted §8(tier ${tier}/${MAX_TIER})`);
}

function stripModules(player, loc) {
  const block = rackAt(player, loc);
  if (!block) return;
  const cur = block.permutation.getState("minecoins:module") ?? "none";
  const map = readMap(P_MODS);
  const k = locKey(player.dimension.id, loc);
  const up = map[k] ?? {};
  const give = [];
  if (cur === "cooling" || cur === "both") give.push(B.cooling);
  if (cur === "battery" || cur === "both") give.push(B.battery);
  for (const key of ["speed", "storage", "research"]) {
    const tier = up[key] ?? 0;
    if (tier > 0) give.push(upgradeItem(key, tier));
  }
  if (!give.length) {
    player.sendMessage("§b[Hardware] §7No modules fitted.");
    return;
  }
  delete map[k];
  writeMap(P_MODS, map);
  setModuleState(block, "none");
  for (const id of give) giveItem(player, id, 1);
  player.playSound("random.break", { volume: 0.5 });
  player.sendMessage(`§b[Hardware] §7Pulled ${give.length} module${give.length === 1 ? "" : "s"} out.`);
}

/* ------------------------------------------ physical, clickable block GUIs */
function openLocalGui(player, typeId, loc) {
  click(player);
  if (typeId === B.rack) {
    const grid = loc ? evalGrid(player.dimension, loc, true) : null;
    openStorage(player, grid, "RACK").catch(() => player.sendMessage("§b[Storage] §cLink error."));
  } else if (typeId === B.monitor) {
    openDesktop(player, "Monitor").catch(() => {});
  } else {
    const rack = nearestRack(player);
    openStatus(player, rack ? evalGrid(player.dimension, rack, true) : null).catch(() => {});
  }
}

try {
  world.beforeEvents.playerInteractWithBlock.subscribe((ev) => {
    const block = ev.block;
    if (!block) return;
    if (PIPE_IDS.has(block.typeId) && ev.player.isSneaking) {
      const player = ev.player;
      const dim = block.dimension;
      const l = block.location;
      const parts = PIPE_LINKS.map(([state, dx, dy, dz]) => {
        const n = dim.getBlock({ x: l.x + dx, y: l.y + dy, z: l.z + dz });
        const on = block.permutation.getState(state) ? "on" : "off";
        return `${state.slice(10)}=${on} -> ${n ? n.typeId.slice(10) : "void"}`;
      });
      const line = `§7[cable] §f${block.typeId.slice(10)}  ${parts.join("   ")}`;
      system.run(() => player.sendMessage(line));
      return;
    }
    if (block.typeId === B.terminal) {
      const at = { x: block.location.x, y: block.location.y, z: block.location.z };
      const player = ev.player;
      const holding = ev.itemStack?.typeId;
      ev.cancel = true;
      if (player.isSneaking) system.run(() => ejectDrive(player, at));
      else if (holding === DRIVE) system.run(() => insertDrive(player, at));
      else system.run(() => openTerminal(player, at));
      return;
    }
    if (block.typeId === B.generator && ev.itemStack && FUEL_SECONDS[ev.itemStack.typeId]) {
      const at = { x: block.location.x, y: block.location.y, z: block.location.z };
      const player = ev.player;
      ev.cancel = true;
      system.run(() => feedGenerator(player, at));
      return;
    }
    if (block.typeId === B.rack) {
      const at = { x: block.location.x, y: block.location.y, z: block.location.z };
      if (ev.itemStack && ev.itemStack.typeId === DRIVE) {
        ev.cancel = true;
        const player = ev.player;
        system.run(() => {
          if (bindHeldDrive(player, at)) {
            player.playSound("random.levelup", { volume: 0.4 });
            player.sendMessage("§b[Drive] §fPaired with this server.");
          }
        });
        return;
      }
      const upgrade = ev.itemStack ? UPGRADES[ev.itemStack.typeId] : undefined;
      if (upgrade) {
        ev.cancel = true;
        const player = ev.player;
        system.run(() => installUpgrade(player, at, upgrade.key, upgrade.label, upgrade.tier));
        return;
      }
      const want = ev.itemStack ? MODULE_OF[ev.itemStack.typeId] : undefined;
      if (want) {
        ev.cancel = true;
        const player = ev.player;
        system.run(() => installModule(player, at, want));
        return;
      }
      if (ev.player.isSneaking) {
        ev.cancel = true;
        const player = ev.player;
        system.run(() => stripModules(player, at));
        return;
      }
    }
    if (ev.player.isSneaking) return;
    if (![B.rack, B.tower, B.monitor].includes(block.typeId)) return;
    ev.cancel = true;
    const player = ev.player;
    const typeId = block.typeId;
    const at = { x: block.location.x, y: block.location.y, z: block.location.z };
    system.run(() => openLocalGui(player, typeId, at));
  });
} catch {
  // Engine without this before-event: the tablet remains the entry point.
}

world.afterEvents.itemUse.subscribe((ev) => {
  const item = ev.itemStack;
  if (!item) return;
  const player = ev.source;
  if (item.typeId === GUIDE_BOOK) {
    openGuide(player).catch(() => {
      player.sendMessage("§b[Guide] §cCould not open the guide.");
    });
    return;
  }
  if (item.typeId !== TABLET) return;
  openDesktop(player, "Tablet").catch(() => {
    player.sendMessage("§b[Tablet] §cConnection interrupted.");
  });
});

/* first join: a fresh ledger entry so balances are auditable */
world.afterEvents.playerSpawn.subscribe((ev) => {
  if (!ev.initialSpawn) return;
  const p = ev.player;
  p.setDynamicProperty(P_LAST, Date.now());
  if (!p.getDynamicProperty("mc:guide")) {
    p.setDynamicProperty("mc:guide", true);
    try { giveItem(p, GUIDE_BOOK, 1); } catch { /* inventory not ready yet */ }
  }
  if (coins(p) === 0 && !readList(P_CHAIN).some((b) => b.p === p.name.slice(0, 16))) {
    p.sendMessage("§b[Minecoins] §fWelcome — you mine 1 minecoin every 5 real minutes. Craft a Minecoins Tablet.");
  }
});
