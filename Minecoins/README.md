# Minecoins — Bedrock addon

A single addon that adds a minecoin economy, a digital storage network, and the
server/radio infrastructure it depends on.

## Install

- **Easiest:** double-click `Minecoins.mcaddon` (or open it with Minecraft).
- **Manual:** copy `behavior_pack` → `development_behavior_packs/Minecoins_BP`,
  `resource_pack` → `development_resource_packs/Minecoins_RP`, then enable both
  on the world. **Experimental features → Beta APIs must be ON** (the pack uses
  `@minecraft/server 2.0.0`).
- Requires Minecraft Bedrock 1.21.70+ (script API 2.0.0).

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
- Excluded by design: End City loot (elytra, shulker shell/box, dragon head,
  end crystals) and dungeon-only items (spawners, enchanted golden apple,
  command-only blocks).
- Enchanted books arrive with a random enchantment and level.

### Power + cooling (server infrastructure)
- **Solar panel** — 25 EU/s in daylight. **Battery** — 5000 EU each.
  **Power cable** — connects the grid (BFS over touching blocks, up to ~700).
  **Cooling unit** — 3 EU/s. **Server rack** — 8 EU/s.
- A rack is online only when its grid has ≥1 cooling unit **and** stored energy.
  Energy accrues while the chunks are unloaded (rate × elapsed time, capped 6 h).
- Digital storage needs an online rack within 48 blocks.

### Digital storage
- Per-player virtual vault. Deposit the held stack, withdraw up to 64 of any
  stored type, paginated 15 per page. Survives death and dimension changes.

### Tablet + radio
- **Minecoins Tablet** opens the GUI only with a live signal.
- **Radio tower** covers 1500 blocks; **radio extenders** chain the network
  (each hop up to 1500 blocks from a live node). Tablets work anywhere inside
  the chained coverage.
- **Underground = no signal.** The tablet checks the 40 blocks above you; if you
  are covered, you need **LAN cable** running from a tower down to within 8
  blocks of you. One continuous cable run lights the network back up.

### Clickable GUIs
- Every menu is button-driven: tap a button and it plays the pressure-plate
  click (`random.click`). Opening a menu, depositing and withdrawing all click.
- **Right-click a server rack** to open digital storage on the spot, or a
  **radio tower** for network status — no tablet or signal needed for the rack
  you are standing at. Sneak to place blocks against them instead.

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
| LAN cable ×4 | checker of copper ingot and string |
| Minecoins Tablet | iron corners, glass sides, redstone centre |

## Quick start

1. Craft a tablet, a radio tower, a solar panel, a battery, a power cable,
   a cooling unit and a server rack.
2. Place the tower, then lay cable from the solar panel → battery → rack, and
   put the cooling unit on the same cable run.
3. Place the rack near where you play (within 48 blocks).
4. Right-click with the tablet → **Digital storage**, then **Buy items**.
5. Going mining? Run LAN cable from the tower down to your base.

## Notes / limits

- Grid = blocks touching each other through cable; separate runs are separate grids.
- Solar output follows world daytime (`getTimeOfDay`), not weather.
- "Underground" is detected by the block column above the player, so a roofed
  build counts too — run LAN cable to it.
- Catalog names come from item ids; a few bedrock-only id differences are
  normalised, and any item the game rejects is not charged (purchase fails safe).
