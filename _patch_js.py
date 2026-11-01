import sys

JS = "Minecoins/behavior_pack/scripts/main.js"
t = open(JS, encoding="utf-8", newline="").read()


def rep(old, new, n=1):
    global t
    c = t.count(old)
    if c != n:
        sys.exit("MISMATCH %r %d" % (old[:70], c))
    t = t.replace(old, new)


def cut(start, end, new):
    global t
    i = t.index(start)
    j = t.index(end, i)
    t = t[:i] + new + t[j:]


# ------------------------------------------------------------ block ids
rep('''  lan: "minecoins:lan_cable",
  monitor: "minecoins:monitor",''',
'''  monitor: "minecoins:monitor",
  generator: "minecoins:generator",
  terminal: "minecoins:storage_terminal",''')

rep("const GRID_BLOCKS = [B.cable, B.panel, B.battery, B.cooling, B.rack];",
    "const GRID_BLOCKS = [B.cable, B.panel, B.battery, B.cooling, B.rack, B.generator, B.terminal];")

rep('''const PIPE_LINKS_BY_TYPE = {
  [B.cable]: new Set([B.cable, B.panel, B.battery, B.cooling, B.rack]),
  [B.lan]: new Set([B.lan, B.tower, B.extender]),
};''',
'''const PIPE_LINKS_BY_TYPE = {
  [B.cable]: new Set([B.cable, B.panel, B.battery, B.cooling, B.rack, B.generator, B.terminal]),
};''')

rep("const PIPE_IDS = new Set([B.cable, B.lan]);", "const PIPE_IDS = new Set([B.cable]);")

# ------------------------------------------------------------ constants
rep("const RACK_BATTERY_CAP = 1000; // a fitted battery module",
'''const RACK_BATTERY_CAP = 1000; // a fitted battery module

/* Upgrade modules: three tiers each, stacked by fitting more than one. */
const UPGRADES = {
  "minecoins:speed_module": { key: "speed", label: "Speed", max: 3 },
  "minecoins:storage_module": { key: "storage", label: "Storage", max: 3 },
  "minecoins:research_module": { key: "research", label: "Research", max: 3 },
};
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
const RESEARCH_GATE = { 1: 0, 2: 0, 3: 1, 4: 2, 5: 2, 6: 3 };''')

rep('const P_HEAT = "mc:heat";',
'''const P_HEAT = "mc:heat";
const P_MODS = "mc:rackmods";
const P_FUEL = "mc:fuel";
const P_TERM = "mc:terminal";''')

# ------------------------------------------------------------ radio: no LAN
cut("/** LAN cable run from the player to (near) a radio node. */", "function signalFor(player) {", "")

rep('''  const underground = isUnderground(player);
  if (underground) {
    if (!lanLink(player, nodes)) {
      return { ok: false, why: "§cNo signal underground — run LAN cable from a radio tower down to you.", underground };
    }
    return { ok: true, why: "§aLinked by LAN cable (underground)", underground };
  }''',
'''  const underground = isUnderground(player);
  if (underground) {
    // No radio underground. Storage is reached with a drive and a terminal instead.
    return { ok: false, why: "§cNo signal underground — carry a paired flash drive to a powered terminal.", underground };
  }''')

# ------------------------------------------------------------ grid: fuel, terminals
rep('''  const counts = { panel: 0, battery: 0, cooling: 0, rack: 0 };
  const cells = [];
  const racks = [];''',
'''  const counts = { panel: 0, battery: 0, cooling: 0, rack: 0, generator: 0, terminal: 0 };
  const cells = [];
  const racks = [];
  const gens = [];
  const mods = readMap(P_MODS);
  const fuel = readMap(P_FUEL);''')

rep('''      const module = b.permutation.getState("minecoins:module") ?? "none";
      racks.push({ x: loc.x, y: loc.y, z: loc.z, module });''',
'''      const module = b.permutation.getState("minecoins:module") ?? "none";
      const up = mods[locKey(dim.id, loc)] ?? {};
      racks.push({
        x: loc.x, y: loc.y, z: loc.z, module,
        speed: up.speed ?? 0, storage: up.storage ?? 0, research: up.research ?? 0,
      });''')

rep('''    } else if (t !== B.cable) continue;''',
'''    } else if (t === B.generator) {
      counts.generator++;
      gens.push({ x: loc.x, y: loc.y, z: loc.z });
    } else if (t === B.terminal) {
      counts.terminal++;
    } else if (t !== B.cable) continue;''')

rep('''  const gen = counts.panel * GEN_PER_PANEL;
  const draw = counts.rack * DRAW_PER_RACK + counts.cooling * DRAW_PER_COOLER;''',
'''  const burning = gens.filter((g) => {
    const rec = fuel[locKey(dim.id, g)];
    return !!rec && rec.s > 0;
  }).length;
  const gen = counts.panel * GEN_PER_PANEL + burning * GEN_PER_GENERATOR;
  const draw = counts.rack * DRAW_PER_RACK + counts.cooling * DRAW_PER_COOLER
    + counts.terminal * DRAW_PER_TERMINAL;''')

rep('''  if (apply && cells.length) {
    const unit = capacity ? total / capacity : 0;''',
'''  if (apply && gens.length) {
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
    const unit = capacity ? total / capacity : 0;''')

rep('''  result.ok = result.ok && result.live > 0;
  result.perMin = result.live / 5;''',
'''  result.ok = result.ok && result.live > 0;
  result.pay = result.racks
    .filter((r) => r.heat < HEAT_MAX)
    .reduce((a, r) => a + 1 + (r.speed ?? 0), 0);
  result.perMin = result.pay / 5;
  result.slots = counts.rack * SLOTS_PER_RACK
    + result.racks.reduce((a, r) => a + (r.storage ?? 0), 0) * SLOTS_PER_STORAGE;
  result.research = result.racks.reduce((a, r) => Math.max(a, r.research ?? 0), 0);''')

# ------------------------------------------------------------ pay rate
rep('''/** Racks that are powered and below the heat limit, one grid at a time. */
function onlineRacks(dim) {
  const done = new Set();
  let n = 0;
  for (const e of readList(P_RACKS)) {
    if (e.d !== dim.id) continue;
    if (done.has(locKey(dim.id, e))) continue;
    const b = dim.getBlock({ x: e.x, y: e.y, z: e.z });
    if (!b || b.typeId !== B.rack) continue;
    const g = evalGrid(dim, e, true);
    for (const r of g.racks) done.add(locKey(dim.id, r));
    if (g.energy > 0) n += g.live;
  }
  return n;
}''',
'''/** Coins per five minutes: a live rack pays 1, each speed tier pays 1 more. */
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
}''')

rep("const paying = Math.max(1, onlineRacks(p.dimension));",
    "const paying = Math.max(1, payRate(p.dimension));")

# ------------------------------------------------------------ storage rewrite
cut("/* --------------------------------------------------------- digital storage */",
    "async function openStatus(player, grid) {",
'''/* --------------------------------------------------------- digital storage */
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

''')

# ------------------------------------------------------------ drives, terminal, fuel
rep("/* ----------------------------------------------------------- rack hardware */",
'''/* ------------------------------------------------------------- flash drives */
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

/* ----------------------------------------------------------- rack hardware */''')

# ------------------------------------------------------------ rack upgrades
rep('''function stripModules(player, loc) {''',
'''function installUpgrade(player, loc, key, label, max) {
  const block = rackAt(player, loc);
  if (!block) return;
  const map = readMap(P_MODS);
  const k = locKey(player.dimension.id, loc);
  const rec = map[k] ?? { speed: 0, storage: 0, research: 0 };
  if ((rec[key] || 0) >= max) {
    player.sendMessage(`§b[Hardware] §7${label} is already at tier ${max}.`);
    player.playSound("note.bass");
    return;
  }
  const eq = player.getComponent("minecraft:equippable");
  const held = eq?.getEquipment(EquipmentSlot.Mainhand);
  if (!held) return;
  if (held.amount > 1) held.amount -= 1;
  else eq.setEquipment(EquipmentSlot.Mainhand, undefined);
  rec[key] = (rec[key] || 0) + 1;
  map[k] = rec;
  writeMap(P_MODS, map);
  player.playSound("random.anvil_use", { volume: 0.5, pitch: 1.2 });
  player.sendMessage(`§b[Hardware] §f${label} tier ${rec[key]}§7 fitted`);
}

function stripModules(player, loc) {''')

# ------------------------------------------------------------ interactions
rep('''    if (block.typeId === B.rack) {
      const at = { x: block.location.x, y: block.location.y, z: block.location.z };
      const want = ev.itemStack ? MODULE_OF[ev.itemStack.typeId] : undefined;''',
'''    if (block.typeId === B.terminal) {
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
        system.run(() => installUpgrade(player, at, upgrade.key, upgrade.label, upgrade.max));
        return;
      }
      const want = ev.itemStack ? MODULE_OF[ev.itemStack.typeId] : undefined;''')

# ------------------------------------------------------------ rack GUI needs the grid
rep('''function openLocalGui(player, typeId) {
  click(player);
  if (typeId === B.rack) {
    openStorage(player, false).catch(() => player.sendMessage("§b[Storage] §cLink error."));''',
'''function openLocalGui(player, typeId, loc) {
  click(player);
  if (typeId === B.rack) {
    const grid = loc ? evalGrid(player.dimension, loc, true) : null;
    openStorage(player, grid, "RACK").catch(() => player.sendMessage("§b[Storage] §cLink error."));''')

rep('''    const player = ev.player;
    const typeId = block.typeId;
    system.run(() => openLocalGui(player, typeId));''',
'''    const player = ev.player;
    const typeId = block.typeId;
    const at = { x: block.location.x, y: block.location.y, z: block.location.z };
    system.run(() => openLocalGui(player, typeId, at));''')

# ------------------------------------------------------------ tablet storage entry
rep('  if (act === "storage") return openStorage(player);',
    '  if (act === "storage") return openStorage(player, grid, "TABLET");')

# ------------------------------------------------------------ shop gating
rep('    BUY.set(id, { price: PRICE[tier], cat, name: pretty(shortId) });',
    '    BUY.set(id, { price: PRICE[tier], tier: Number(tier), cat, name: pretty(shortId) });')

rep('''    for (const id of list) {
      const info = BUY.get(id);
      form.button(BTN(`§f${info.name} §7- §e${info.price}`), iconFor(id));
    }''',
'''    const level = grid ? grid.research ?? 0 : 0;
    for (const id of list) {
      const info = BUY.get(id);
      const need = RESEARCH_GATE[info.tier] ?? 0;
      if (need > level) {
        form.button(BTN(`§8${info.name} - locked, research ${need}`));
        continue;
      }
      form.button(BTN(`§f${info.name} §7- §e${info.price}`), iconFor(id));
    }''')

rep('''    const info = BUY.get(id);
    const bal = coins(player);''',
'''    const info = BUY.get(id);
    if ((RESEARCH_GATE[info.tier] ?? 0) > (grid ? grid.research ?? 0 : 0)) {
      player.sendMessage("§b[Store] §cLocked — fit a Research Module to a rack.");
      player.playSound("note.bass");
      continue;
    }
    const bal = coins(player);''')

rep('''        `Balance§8: §e${coins(player)} minecoins`,
        statusLine(grid),
        `§8Diamonds are the premium tier; books sit just below.`,''',
'''        `Balance§8: §e${coins(player)} minecoins`,
        statusLine(grid),
        `§7Research§8: tier §f${grid?.research ?? 0}§8 · §7vault slots§8: §f${grid?.slots ?? 0}`,
        `§8Diamonds are the premium tier; books sit just below.`,''')

# ------------------------------------------------------------ status screen
rep('''        `Live racks§8: §f${grid?.live ?? 0}§7/§f${grid?.rack ?? 0}§7 · heat §f${Math.round(Math.max(0, ...(grid?.racks ?? []).map((r) => r.heat ?? 0)))}%§7 · payout §e${(grid?.perMin ?? 0).toFixed(1)}§7/min`,''',
'''        `Live racks§8: §f${grid?.live ?? 0}§7/§f${grid?.rack ?? 0}§7 · heat §f${Math.round(Math.max(0, ...(grid?.racks ?? []).map((r) => r.heat ?? 0)))}%§7 · payout §e${(grid?.perMin ?? 0).toFixed(1)}§7/min`,
        `Vault§8: §f${grid?.slots ?? 0}§7 slots · research §f${grid?.research ?? 0}§7 · generators §f${grid?.generator ?? 0}§7 · terminals §f${grid?.terminal ?? 0}`,''')

# ------------------------------------------------------------ guide
rep('''  {
    name: "4. Radio and LAN",
    lines: [
      "The tablet only opens with signal: §f1500 blocks§7 from a tower.",
      "§fRadio Extender§7 repeats the network, hop by hop.",
      "Underground there is no radio at all - dig with a plan.",
      "Run §fLAN Cable§7 from a tower down to your base to link it.",
      "Click a §fMonitor§7 block for the same screens on a wall.",
    ],
  },''',
'''  {
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
  },''')

rep('''      "Deposit takes your held stack; pick an entry to withdraw 64.",
      "The vault is per player and works within §f48 blocks§7 of the rack.",''',
'''      "Deposit or withdraw 1, 8, 16, 32 or 64 at a time.",
      "Slots start at §f27 per rack§7; each Storage Module adds §f27§7 more.",''')

rep('''  {
    name: "5. Minecoins and the store",''',
'''  {
    name: "5. Upgrades",
    lines: [
      "Modules tier up to three: fit the same one again to raise it.",
      "§fSpeed Module§7: §e1§7 extra minecoin per 5 minutes, per tier.",
      "§fStorage Module§7: §f27§7 more vault slots, per tier.",
      "§fResearch Module§7: unlocks the pricier half of the store.",
      "Research I opens tiers 3, II opens 4 and 5, III opens diamonds.",
    ],
  },
  {
    name: "6. Minecoins and the store",''')

open(JS, "w", encoding="utf-8", newline="\n").write(t)
print("script patched for 2.0.0")
