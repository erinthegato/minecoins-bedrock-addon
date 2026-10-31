/**
 * Minecoins Core
 * - Minecoin mining: +1 minecoin / 5 real minutes with chat notification
 * - Digital storage (server rack, requires power + cooling)
 * - Power grid: solar panels -> power cable -> battery -> server rack / cooling
 * - Radio: tower (1500 block range), extenders repeat the network
 * - Underground: no radio signal, must run LAN cable from a tower
 * - Catalog: buy nearly every obtainable item, diamond tier most expensive
 */
import { world, system, ItemStack, EquipmentSlot } from "@minecraft/server";
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
  lan: "minecoins:lan_cable",
};
const TABLET = "minecoins:tablet";
const GRID_BLOCKS = [B.cable, B.panel, B.battery, B.cooling, B.rack];
const NODE_BLOCKS = [B.tower, B.extender];

const P_NODES = "mc:nodes";
const P_RACKS = "mc:racks";
const P_ENERGY = "mc:energy";
const P_CHAIN = "mc:chain";
const P_COINS = "mc:coins";
const P_LAST = "mc:last";
const P_STORE = "mc:store";

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
    BUY.set(id, { price: PRICE[tier], cat, name: pretty(shortId) });
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
    let gained = 0;
    while (now - last >= COIN_MS) { last += COIN_MS; gained++; }
    p.setDynamicProperty(P_LAST, last);
    const bal = coins(p) + gained;
    setCoins(p, bal);
    ledger(p, gained, "mine");
    p.sendMessage(`§b[Minecoins] §f+${gained} minecoin§7 · balance §e${bal}`);
    p.playSound("random.orb", { volume: 0.6, pitch: 1.4 });
    p.onScreenDisplay.setActionBar(`§e+${gained} minecoin §7(${bal})`);
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

/** LAN cable run from the player to (near) a radio node. */
function lanLink(player, nodes) {
  if (!nodes.length) return false;
  const dim = player.dimension;
  const p = player.location;
  const px = Math.floor(p.x), py = Math.floor(p.y), pz = Math.floor(p.z);
  const seen = new Set();
  const queue = [];
  for (let dx = -6; dx <= 6; dx++) {
    for (let dy = -3; dy <= 3; dy++) {
      for (let dz = -6; dz <= 6; dz++) {
        if (dist({ x: px + dx, y: py + dy, z: pz + dz }, p) > 8) continue;
        const b = dim.getBlock({ x: px + dx, y: py + dy, z: pz + dz });
        if (b && b.typeId === B.lan) {
          const k = `${b.location.x},${b.location.y},${b.location.z}`;
          if (!seen.has(k)) { seen.add(k); queue.push(b.location); }
        }
      }
    }
  }
  const nearNode = (loc) => nodes.some((n) => dist(n, loc) <= 8);
  let steps = 0;
  while (queue.length && steps++ < 600) {
    const loc = queue.pop();
    if (nearNode(loc)) return true;
    for (const o of [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]]) {
      const np = { x: loc.x + o[0], y: loc.y + o[1], z: loc.z + o[2] };
      const k = `${np.x},${np.y},${np.z}`;
      if (seen.has(k)) continue;
      const b = dim.getBlock(np);
      if (b && b.typeId === B.lan) { seen.add(k); queue.push(np); }
    }
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
    if (!lanLink(player, nodes)) {
      return { ok: false, why: "§cNo signal underground — run LAN cable from a radio tower down to you.", underground };
    }
    return { ok: true, why: "§aLinked by LAN cable (underground)", underground };
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
  const counts = { panel: 0, battery: 0, cooling: 0, rack: 0 };
  const batteries = [];
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
    else if (t === B.battery) { counts.battery++; batteries.push({ ...loc }); }
    else if (t === B.cooling) counts.cooling++;
    else if (t === B.rack) counts.rack++;
    else if (t !== B.cable) continue;
    for (const o of [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]]) {
      queue.push({ x: loc.x + o[0], y: loc.y + o[1], z: loc.z + o[2] });
    }
  }

  const gen = counts.panel * GEN_PER_PANEL;
  const draw = counts.rack * DRAW_PER_RACK + counts.cooling * DRAW_PER_COOLER;
  const store = readMap(P_ENERGY);
  const now = Date.now();
  let total = 0;
  let oldest = now;
  for (const loc of batteries) {
    const rec = store[locKey(dim.id, loc)];
    total += rec && typeof rec.e === "number" ? rec.e : 0;
    if (rec && typeof rec.t === "number") oldest = Math.min(oldest, rec.t);
  }
  const elapsed = Math.min((now - oldest) / 1000, 6 * 3600);
  total = Math.max(0, Math.min(batteries.length * BATTERY_CAP, total + (gen - draw) * elapsed));

  const day = world.getTimeOfDay() < 12000;
  const result = {
    ok: counts.rack > 0 && counts.cooling > 0 && total > 0,
    cooled: counts.cooling > 0,
    energy: total,
    gen: day ? gen : 0,
    draw,
    capacity: batteries.length * BATTERY_CAP,
    ...counts,
  };
  if (apply && batteries.length) {
    const each = total / batteries.length;
    for (const loc of batteries) store[locKey(dim.id, loc)] = { e: each, t: now };
    const keys = Object.keys(store);
    if (keys.length > 250) {
      keys.sort((a, b) => (store[a].t || 0) - (store[b].t || 0));
      for (const k of keys.slice(0, keys.length - 250)) delete store[k];
    }
    writeMap(P_ENERGY, store);
  }
  return result;
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
  if (!grid.cooled) return { ok: false, why: "§cServer rack has no cooling unit on its power grid — overheating.", grid };
  if (grid.energy <= 0) return { ok: false, why: "§cNo power — charge a battery with solar panels.", grid };
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

/** Pressure-plate style click on every GUI press. */
function click(player) {
  player.playSound("random.click", { volume: 0.9, pitch: 1.15 });
}

async function show(form, player) {
  try {
    const res = await form.show(player);
    if (res && res.selection !== undefined) click(player);
    return res;
  } catch {
    return { canceled: true };
  }
}

function statusLine(grid) {
  if (!grid) return "§7Power: §cno grid";
  const pct = grid.capacity ? Math.round((grid.energy / grid.capacity) * 100) : 0;
  return `§7Energy §e${Math.round(grid.energy)}§7/${grid.capacity} (§a${pct}%§7) · §7gen §f${grid.gen}§7 · draw §f${grid.draw} EU/s`;
}

async function openStorage(player, requireSignal = true) {
  if (requireSignal && !signalFor(player).ok) { player.sendMessage("§b[Minecoins] §cNo signal — tablet offline."); return; }
  const st = serverStatus(player);
  if (!st.ok) { player.sendMessage(`§b[Storage] ${st.why}`); return; }

  let page = 0;
  for (;;) {
    const store = loadStore(player);
    const entries = Object.entries(store).filter(([, c]) => c > 0).sort((a, b) => b[1] - a[1]);
    const per = 15;
    const pages = Math.max(1, Math.ceil(entries.length / per));
    page = Math.max(0, Math.min(page, pages - 1));
    const slice = entries.slice(page * per, page * per + per);

    const form = new ActionFormData()
      .title("§bDigital Storage")
      .body(`§7Stored: §f${totalStored(store)} items §7in §f${entries.length} stacks\n${statusLine(st.grid)}\n§8Page ${page + 1}/${pages}`)
      .button("§aDeposit held item")
      .button("§bServer status");
    for (const [id, c] of slice) {
      form.button(`§f${id.replace("minecraft:", "").replace(/_/g, " ")} §7×§e${c}`);
    }
    if (pages > 1) { form.button("§8< Previous"); form.button("§8Next >"); }

    const res = await show(form, player);
    if (res.canceled || res.selection === undefined) return;
    const sel = res.selection;

    if (sel === 0) {
      const eq = player.getComponent("minecraft:equippable");
      const held = eq?.getEquipment(EquipmentSlot.Mainhand);
      if (!held) { player.sendMessage("§b[Storage] §cHold an item to deposit."); continue; }
      const s = loadStore(player);
      s[held.typeId] = (s[held.typeId] || 0) + held.amount;
      saveStore(player, s);
      eq.setEquipment(EquipmentSlot.Mainhand, undefined);
      // (click handled by show())
      player.sendMessage(`§b[Storage] §f+${held.amount} ${held.typeId.replace("minecraft:", "")}`);
      continue;
    }
    if (sel === 1) { await openStatus(player, st.grid); continue; }
    const idx = sel - 2;
    if (idx >= 0 && idx < slice.length) {
      const [id, count] = slice[idx];
      const take = Math.min(64, count);
      const s = loadStore(player);
      s[id] = (s[id] || 0) - take;
      if (s[id] <= 0) delete s[id];
      saveStore(player, s);
      giveItem(player, id, take);
      player.playSound("random.pop");
      player.sendMessage(`§b[Storage] §f-${take} ${id.replace("minecraft:", "")}`);
      continue;
    }
    if (pages > 1) {
      const navIndex = sel - 2 - slice.length;
      if (navIndex === 0) page--;
      else if (navIndex === 1) page++;
    }
  }
}

async function openStatus(player, grid) {
  const nodes = reachableNodes(player.dimension.id);
  const sig = signalFor(player);
  const body =
    `${statusLine(grid ?? null)}\n` +
    `§7Panels: §f${grid?.panel ?? 0} §7Batteries: §f${grid?.battery ?? 0} §7Cooling: §f${grid?.cooling ?? 0} §7Racks: §f${grid?.rack ?? 0}\n` +
    `§7Radio nodes: §f${nodes.length} §7(range §f${RANGE}§7 each)\n` +
    `§7Link: §f${sig.why.replace(/§./g, "")}\n` +
    `§8Power flows through power cable. Cooling must sit on the rack's grid.`;
  await show(new ActionFormData().title("§bNetwork Status").body(body).button("Back"), player);
}

async function openBuy(player, cat, grid) {
  for (;;) {
    const list = CATALOG[cat] || [];
    const form = new ActionFormData()
      .title(`§b${cat}`)
      .body(`§7Balance: §e${coins(player)} minecoins\n${statusLine(grid)}`)
      .button("§8< Back");
    for (const id of list) {
      const info = BUY.get(id);
      form.button(`§f${info.name} §7- §e${info.price}`, iconFor(id));
    }
    const res = await show(form, player);
    if (res.canceled || res.selection === undefined || res.selection === 0) return;
    const id = list[res.selection - 1];
    if (!id) return;
    const info = BUY.get(id);
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
    ? chain.map((b) => `§7${b.h} ${b.a >= 0 ? "§a+" : "§c"}${b.a} §f${b.k} §8(${b.p})`).join("\n")
    : "§7Ledger is empty — mine a minecoin first.";
  await show(
    new ActionFormData()
      .title("§bMinecoin Ledger")
      .body(`§7Blocks: §f${readList(P_CHAIN).length}/64 §8(hash-chained)\n\n${lines}`)
      .button("Back"),
    player
  );
}

/* ---------------------------------------------------------------- tablet UI */
async function openTablet(player) {
  const sig = signalFor(player);
  if (!sig.ok) {
    player.sendMessage(`§b[Tablet] ${sig.why}`);
    player.onScreenDisplay.setActionBar("§cNo connection");
    player.playSound("note.bass");
    return;
  }
  const st = serverStatus(player);
  for (;;) {
    const form = new ActionFormData()
      .title("§bMinecoins Tablet")
      .body(
        `§7Balance: §e${coins(player)} minecoins\n` +
        `§7Link: §a${sig.why.replace(/§./g, "")}\n` +
        `§7Server: ${st.ok ? "§aonline" : "§coffline"} §8${st.grid ? `${Math.round(st.grid.energy)} EU` : ""}`
      )
      .button("Buy items", "textures/items/emerald")
      .button("Digital storage", "textures/blocks/mcn_server_rack")
      .button("Ledger", "textures/items/mcn_minecoin")
      .button("Network status", "textures/blocks/mcn_radio_tower");

    const res = await show(form, player);
    if (res.canceled || res.selection === undefined) return;
    if (res.selection === 0) {
      const cats = Object.keys(CATALOG);
      const pick = await show(
        new ActionFormData()
          .title("§bCatalog")
          .body(`§7Balance: §e${coins(player)} minecoins\n§8Diamonds are the premium tier; enchanted books sit below them.`)
          .button("§8< Back")
          .button("§fBlocks")
          .button("Tools").button("Armor").button("Food").button("Materials")
          .button("Redstone").button("Enchanted Books").button("§bDiamond"),
        player
      );
      if (pick.canceled || pick.selection === undefined || pick.selection === 0) continue;
      // menu order differ from CATALOG key order, so map explicitly
      const order = ["Blocks", "Tools", "Armor", "Food", "Materials", "Redstone", "Enchanted Books", "Diamond"];
      const cat = order[pick.selection - 1] || cats[0];
      if (CATALOG[cat]) await openBuy(player, cat, st.grid);
    } else if (res.selection === 1) {
      await openStorage(player);
    } else if (res.selection === 2) {
      await openChain(player);
    } else if (res.selection === 3) {
      await openStatus(player, st.grid);
    }
  }
}

/* ------------------------------------------ physical, clickable block GUIs */
function openLocalGui(player, typeId) {
  click(player);
  if (typeId === B.rack) {
    openStorage(player, false).catch(() => player.sendMessage("§b[Storage] §cLink error."));
  } else {
    const rack = nearestRack(player);
    openStatus(player, rack ? evalGrid(player.dimension, rack, true) : null).catch(() => {});
  }
}

try {
  world.beforeEvents.playerInteractWithBlock.subscribe((ev) => {
    const block = ev.block;
    if (!block || ev.player.isSneaking) return;
    if (block.typeId !== B.rack && block.typeId !== B.tower) return;
    ev.cancel = true;
    const player = ev.player;
    const typeId = block.typeId;
    system.run(() => openLocalGui(player, typeId));
  });
} catch {
  // Engine without this before-event: the tablet remains the entry point.
}

world.afterEvents.itemUse.subscribe((ev) => {
  const item = ev.itemStack;
  if (!item || item.typeId !== TABLET) return;
  const player = ev.source;
  openTablet(player).catch(() => {
    player.sendMessage("§b[Tablet] §cConnection interrupted.");
  });
});

/* first join: a fresh ledger entry so balances are auditable */
world.afterEvents.playerSpawn.subscribe((ev) => {
  if (!ev.initialSpawn) return;
  const p = ev.player;
  p.setDynamicProperty(P_LAST, Date.now());
  if (coins(p) === 0 && !readList(P_CHAIN).some((b) => b.p === p.name.slice(0, 16))) {
    p.sendMessage("§b[Minecoins] §fWelcome — you mine 1 minecoin every 5 real minutes. Craft a Minecoins Tablet.");
  }
});
