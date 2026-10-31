# Minecoins

> **Disclaimer:** This cannot generate Minecraft's paid, actual currency.
> The "minecoins" in this addon are a fictional in-game currency belonging to
> this addon. They are unrelated to Minecraft's purchasable Minecoins and cannot
> produce, redeem or convert into them, or into any real money.

A Minecraft Bedrock addon - one behaviour pack plus one resource pack - that adds
a minecoin economy, a per-player digital storage vault, and the server, power and
radio infrastructure those systems depend on.

## What it adds

- **Minecoins** - +1 every 5 real minutes while online, announced in chat and
  recorded in a hash-chained 64-block ledger.
- **Digital storage** - a virtual vault per player that survives death and
  dimension changes.
- **Power grid** - solar panels, batteries, fence-style power cable and
  half-height cooling units.
- **Server racks that form walls** - side-by-side cabinets join into one
  continuous rack wall and re-seam when a neighbour is removed. A rack is only
  online with cooling and stored energy on the same grid.
- **Radio network** - towers with 1500-block range, chained extenders, and LAN
  cable for underground bases that have no sky signal.
- **Tablet and wall monitor** - form-based GUI for the store, vault, ledger and
  network status.
- **Minecoins Guide** - a craftable guide book, also handed out on first spawn.
- Nine blocks, eleven recipes, and one collapsible creative group,
  **Server Components**.

## Download

Grab the latest `Minecoins.mcaddon` from
[Releases](https://github.com/erinthegato/minecoins-bedrock-addon/releases) and
open it with Minecraft, or install the BP + RP `.mcpack` pair manually.

## Install

1. Enable **Minecoins Core (Behavior)** and **Minecoins (Resources)** on the
   world.
2. Turn on **Beta APIs** under Experimental Features.
3. Requires Bedrock **1.21.70+** (script API 2.0.0).

## Building

`python Minecoins/tools/gen_packs.py` regenerates every pack file and the
`.mcaddon`. The generator is the single source of truth for blocks, models,
textures, recipes, the creative item catalog and the manifests.

## Documentation

Systems, prices, recipes and a quick start are in
[`Minecoins/README.md`](Minecoins/README.md).
