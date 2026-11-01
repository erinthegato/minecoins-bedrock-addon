# Minecoins — Bedrock addon

A single addon that adds a minecoin economy, a digital storage network, and the
server/radio infrastructure it depends on.

> **Disclaimer:** This cannot generate Minecraft's paid, actual currency.
> Minecoins here is a fictional in-game currency belonging to this addon - it
> has no connection to, and cannot produce, Minecraft's purchasable Minecoins or
> any real money.

## Install

- **Easiest:** double-click `Minecoins.mcaddon` (or open it with Minecraft).
- **Manual:** copy `behavior_pack` → `development_behavior_packs/Minecoins_BP`,
  `resource_pack` → `development_resource_packs/Minecoins_RP`, then enable both
  on the world. **Experimental features → Beta APIs must be ON** (the pack uses
  `@minecraft/server 2.0.0`).
- Requires Minecraft Bedrock 1.21.70+ (script API 2.0.0).

### Guide book
`minecoins:guidebook` is a shapeless craft (book + redstone + glass) and every
player gets one on their first spawn. Using it opens a six-chapter help
window: start here, power grid, cooling and storage, radio and flash drives,
upgrades, minecoins and the store. It works anywhere - no radio needed - and it is listed in the
creative menu under the **Items** tab.

### Creative menu
All ten blocks sit in a collapsible group, **Server Components**, at the end of
the Construction tab. The flash drive and the three modules sit in the same group
under Items. The tablet is in Equipment; the guide book is in Items. Group membership is declared on every block and item and
repeated in `item_catalog/crafting_item_catalog.json`.

## Features

### Minecoins
- +1 minecoin every **5 real minutes** while online, with a chat line, action-bar
  popup and sound each time.
- Leaving the world for more than ~10 minutes pauses accrual (no offline farming).
- Every payout and purchase appends a hash-chained block to a 64-block ledger
  (`Tablet → Ledger`) — each block stores `prev` hash, player, amount and kind.

### Catalog
- Tablet → **Buy items**, 8 categories, ~200 obtainable vanilla items.
- Pricing tiers (coins): base **2**, common **6**, mid **14**, high **25**,
  **Diamond equipment 50**, **diamonds / diamond blocks & ore 75** —
  diamonds are the premium tier, enchanted books (25) sit directly below it.
- The store is **gated**: tiers 1-2 are open from the start, Research I opens
  tier 3, II opens tiers 4 and 5, and III opens diamonds. Every crafting recipe
  stays available in survival regardless.
- Excluded by design: End City loot (elytra, shulker shell/box, dragon head,
  end crystals) and dungeon-only items (spawners, enchanted golden apple,
  command-only blocks).
- Enchanted books arrive with a random enchantment and level.

### Power + cooling (server infrastructure)
- **Solar panel** — 25 EU/s in daylight, a flat 1-pixel plate like leaf litter
  (walkable, stack it against walls, place it flush on floors).
- **Battery** — 5000 EU each. **Cooling unit** — 3 EU/s, both half-height blocks
  (half-block model and half-block hitbox).
- **Server rack** — 8 EU/s and a full-height cabinet centred in its block.
  Racks placed side by side join into one continuous wall: every touching
  side grows out to the block edge, and the seam closes again when a
  neighbour is removed. It draws power through the cable run and needs a
  cooling unit on the same grid.
- **Power cable** - one continuous pipe. It runs a tube through the block on
  every axis it is attached to, up and down included, so a run of cables reads as a
  single pipe with the odd junction instead of a row of fence posts. It still joins
  the grid by touching blocks (BFS, up to ~700).
- **Flash drive and storage terminal** - pair a drive by using it on a rack, then
  insert it into a terminal; the vault opens anywhere the terminal has power, with
  no cable run back to the server.
- **Rack modules** - hold a Cooling Unit or a Battery and use it on a rack to bolt
  it in; the cabinet repaints itself (vent fins, battery cells, or both). Sneak and
  use the rack to pull the modules back out.
- **Heat** - a powered rack climbs toward 100%; cooling drives it back down. At
  100% that rack shuts itself down and stops paying.
- **Offhand readout** - carry the tablet in your offhand for the nearest server's
  heat, minecoins per minute and battery charge, without opening a window.
- **Blinking LEDs** - the rack front is an eight-frame animated texture, red,
  green and blue pixels stepping through it.
- **Payout scales with racks** - every powered, cool rack pays 1 minecoin per 5
  real minutes, minimum 1.
- **27 slots to start** - a single rack opens 27 vault slots; each Storage Module
  adds another 27. One slot holds one stack, so bulk counts cost more slots.
- **Upgrade modules** - Speed, Storage and Research, three tiers each, fitted by
  holding the module and using it on a rack.
- **Generator** - burns coal, charcoal or leaf litter for 40 EU/s, so a base away
  from the solar array still runs.
- **The store is gated** - cheap tiers are open from the start, diamonds and the
  expensive half need Research I-III fitted. Everything is still craftable in
  survival.
- A rack is online when its grid holds energy and cooling — a fitted cooling
  module or a cooling unit on the same run. Energy accrues while the chunks are
  unloaded (rate × elapsed time, capped 6 h).
- A vault is readable at the rack itself, or anywhere through a paired drive in a
  powered storage terminal.

### Digital storage
- Per-player virtual vault, opened at a rack or through a drive in a terminal.
  Survives death and dimension changes.
- Slots, not unlimited stacks: a rack opens **27**, each Storage Module adds 27
  more, and one slot holds one stack of 64.
- Deposit and withdraw 1, 8, 16, 32, 64 at a time (or the whole held stack),
  paginated 15 entries per page. The slot check runs before anything moves.

### Tablet + radio
- **Minecoins Tablet** opens the GUI only with a live signal.
- **Radio tower** covers 1500 blocks; **radio extenders** chain the network
  (each hop up to 1500 blocks from a live node). Tablets work anywhere inside
  the chained coverage.
- **Underground = no signal.** The tablet checks the 40 blocks above you. Your
  vault is still reachable down there: pair a flash drive at the server, carry it
  down, and insert it into a powered storage terminal.

### Clickable GUIs
- Every menu is button-driven: tap a button and it plays the pressure-plate
  click (`random.click`). Opening a menu, depositing and withdrawing all click.
- The OS is **mineOS-09**, modelled on a classic 9x desktop: teal-tinted body,
  a `File  Edit  View  Go  Favorites  Help` menu bar, a `Start` status bar with
  a live clock, and six desktop icons (My Computer, Network Neighborhood,
  Minecoins.exe, Store, My Documents, Shut Down) using custom 32px icons.
  Windows are named like the reference: `Exploring — C:\MINECOINS\STORE`,
  `System Properties`, `My Documents — …`, `Notepad — LEDGER.DAT`.
  Bedrock draws the form frame and buttons itself, so the window body is themed
  rather than pixel-reskinned.
- **Plain desktop**: one button per program (My Computer, Network,
  Minecoins.exe, Store, My Documents). Closing the window quits in one
  press - no pointer state and no screen re-opening behind you.
- **Right-click a server rack** for digital storage, a **radio tower** for
  network status, or a **monitor** for the full desktop — a monitor needs the
  same radio link as the tablet. Sneak to place blocks against them, and sneak +
  use a rack to pull its modules back out.

### Monitor
- Wall-mounted terminal with item-frame style geometry: a 14x14 panel 1 pixel
  deep, rotated to the wall you place it on, with a 2-light-pixel glow tip.
- Opening it shows the same Minecoins 95 desktop as the tablet.

## Crafting

| Item | Recipe |
| --- | --- |
| Power cable ×4 | iron – redstone – iron |
| Solar panel | 3 glass / 3 quartz / 3 redstone |
| Battery | iron ring, redstone corners, copper centre |
| Cooling unit | iron corners, packed ice sides, redstone centre |
| Server rack | iron top/bottom rows, chest–redstone–chest middle |
| Radio tower | copper on top, iron–redstone–iron, iron row |
| Radio extender | copper–redstone–copper |
| Generator | iron ring, furnace centre, redstone corners |
| Storage terminal | iron corners, glass sides, redstone centre |
| Flash drive | iron, redstone and copper checker |
| Speed module | gold corners, redstone sides, sugar centre |
| Storage module | iron corners, redstone sides, chest centre |
| Research module | book corners, redstone sides, amethyst centre |
| Minecoins Tablet | iron corners, glass sides, redstone centre |
| Monitor | iron corners, glass frame, redstone centre |

## Quick start

1. Craft a tablet, a radio tower, a solar panel, a battery, a power cable,
   a cooling unit and a server rack.
2. Place the tower, then lay cable from the solar panel → battery → rack, and
   put the cooling unit on the same cable run.
3. Place the rack near where you play (within 48 blocks).
4. Right-click with the tablet → **Digital storage**, then **Buy items**.
5. Going mining? Pair a flash drive at the rack, craft a storage terminal, feed
   the generator some coal, and insert the drive down there.

## Notes / limits

- Grid = blocks touching each other through cable; separate runs are separate grids.
- Solar output follows world daytime (`getTimeOfDay`), not weather.
- "Underground" is detected by the block column above the player, so a roofed
  build counts too — use a drive and a terminal instead of radio.
- Catalog names come from item ids; a few bedrock-only id differences are
  normalised, and any item the game rejects is not charged (purchase fails safe).
