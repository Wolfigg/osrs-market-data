# AFK Method Catalogue Audit

Audit baseline: 2026-08-29
Updated: 2026-11-26
Status: complete for the enabled catalogue

This document records the catalogue-quality pass for OSRS Market Board. It is maintainer documentation and is not part of the GitHub Pages public artifact.

## Audit standard

Every enabled money-making method must have defensible values for:

- item IDs and input/output or NPC shop-sale quantities
- a sourced working rate or a clearly labelled rate ceiling
- theoretical cycles per hour where applicable
- interaction/idle interval
- membership status
- skill, quest and equipment requirements
- reusable equipment vs consumed inputs
- GE buy-limit applicability
- fixed coin costs and NPC shop-sale proceeds
- source/reference provenance
- explicit method type rather than frontend inference from text

`load_yaml(config/methods.yaml)` now enforces this at runtime. An enabled method must have positive throughput and interval, valid item quantities, at least one GE output or NPC shop sale, an OSRS Wiki reference, a method type, and `audit.status: verified` with an OSRS Wiki audit source. Invalid catalogue data fails CI/collection instead of silently reaching public rankings.

## Catalogue families verified

### Cannonballs

Steel cannonballs with double ammo mould are modelled as one normalized economic cycle per steel bar: one bar -> four cannonballs. The mould physically processes two bars -> eight cannonballs at a time, but the normalized cycle keeps price, GE-limit and capital arithmetic equivalent. The working model remains conservative relative to the efficient training-table rate.

### Gem bolt tips

Sapphire, emerald, ruby, diamond, opal, jade, red topaz and dragonstone use the ordinary gem-to-bolt-tip recipe. Onyx is explicitly corrected to 24 tips per onyx at level 73 Fletching rather than the ordinary 12-tip output.

### Dart tips

Bronze, iron, steel, mithril, adamant and rune dart tips use one bar -> ten tips. Working throughput is kept separate from the Smiths' Uniform theoretical ceiling.

### Plank Make

All seven supported log tiers are represented: regular, oak, teak, mahogany, camphor, ironwood and rosewood. Each cast consumes one log, one Nature rune and two Astral runes, then charges the corresponding coin fee. The required Earth-rune-supplying staff is reusable equipment and supplies the 15 Earth runes, so those runes are excluded from consumed costs. The ordinary one-log-to-one-plank route is modelled; the optional Sawmill voucher output is not.

Autocast processes one plank every 3.6 seconds. The catalogue uses 833 casts/hour from the Wiki's 75,000 Magic XP/hour lower-attention rate and 1,000/hour as its 90,000 XP/hour theoretical ceiling. The Wiki describes about 90 seconds per 26-log inventory, matching the configured interaction window.

The public capital calculation now includes fixed coin charges, correcting the previous understatement for Plank Make.

### Recharge Dragonstone

The catalogue has separate batch methods for amulets of glory, combat bracelets and skills necklaces. One cast recharges 26 items to four charges. A Water-rune-supplying staff covers the four Water runes; each cast consumes one Astral rune and one Soul rune. The model uses 360 casts/hour, calculated from 35,100 Magic XP/hour divided by 97.5 XP/cast. This is an average 10-second bankstanding cadence, not 10 seconds of unattended AFK time. Casting requires 89 Magic, Lunar Diplomacy and the hard Fremennik Diary; combat bracelets and skills necklaces also require Legends' Quest. The spell does not recharge rings of wealth.

### Fountain of Rune routes

Amulets of glory, combat bracelets and skills necklaces are modelled as six-charge outputs from the Fountain; rings of wealth are modelled as five-charge outputs. The routes use a worn ring of wealth for the return teleport, one full Super energy(4) per trip, and 27-item inventories. Standard routes use the guide's approximately 40 inventories/hour Wilderness Obelisk estimate. Wilderness sword 4 variants use the guide's 60-72 inventory range, with 60/hour as the working rate and 72/hour as the theoretical ceiling. The guide's ring result table lists 216 rings and eight potions, which conflicts with its route text; the ring methods expose the configured rate choice in their notes. The same trip rates are explicit estimates for the other jewellery because the route source does not list separate rates for them. Wilderness death risk is not included in profit.

These are tagged as active routes and displayed separately from AFK methods. Their cycle interval is the route estimate, not an idle window.

### Bankstanding food processing

Pizza bases and pastry dough return their empty jug and pot. Pastry dough uses nine recipes per roughly 15-second inventory, or 2,160/hour, with 2,400/hour retained as the Wiki upper figure. Pizza bases use the guide's 2,400/hour rate. Pie shells use the guide's 2,450-unit batch rate and the 500 pie dish four-hour buy limit is enforced by the calculator. Plain pizzas use the guide's 540-per-half-hour rate and require 68 Cooking in the no-burn model. The Wiki warns that dough, shells and other ingredients can have slow GE resale.

Chocolate bar grinding is included at the Wiki's idle automatic-grinding rate of 1,800 bars/hour, with 9,000/hour recorded as the high-intensity ceiling. The method requires a knife or pestle and mortar and gives no skill experience.

### Longbow cutting

Maple, yew and magic unstrung longbows use the regular-knife Make-X model. A 27-log batch at three ticks per bow gives 48.6 seconds of uninterrupted processing. The public working rate remains 1,500 logs/hour and the sourced regular-knife theoretical ceiling is 1,800/hour.

### Longbow stringing

Maple, yew and magic longbow stringing remains classified as low-interaction bankstanding rather than strict AFK. A normal 14-bow inventory at two ticks per bow gives 16.8 seconds between banking interactions. The 2,400/hour working rate is retained.

### Cooking

Karambwan, sharks, monkfish, anglerfish and dark crabs use a deterministic zero-burn model at 99 Cooking with the Cooking cape. The public working rate remains a conservative 1,300 food/hour. Ordinary Make-X cooking is four ticks per item, so a 28-item inventory gives 67.2 seconds of uninterrupted processing and a 1,500/hour theoretical ceiling.

Cooking karambwan also requires Tai Bwo Wannai Trio. The method intentionally models AFK Make-X cooking, not the high-attention one-tick karambwan technique.

Yellowfin cooking was added from the current Wiki success chart: level 79 minimum, 1,300 fish/hour working throughput, and four location-specific success curves. Cooking gauntlets do not affect yellowfin. A per-food source override preserves the exact money-making guide and its verification date in the compiled method.

`minimum_cooking` remains informational metadata rather than a second fake skill requirement.

### Jewellery

Current access semantics are:

- gold rings, necklaces and unstrung amulets: F2P
- sapphire through diamond rings, necklaces and unstrung amulets: F2P
- dragonstone rings, necklaces and unstrung amulets: members
- all bracelets, including gold bracelets: members

Current throughput guidance is represented as:

- metal-only jewellery: conservative 1,400/hour working model, 1,600/hour theoretical ceiling
- gem + metal jewellery: 1,400/hour working and theoretical model

Reusable moulds are equipment, not consumed inputs.

### Glassblowing

Unpowered orbs retain a conservative 1,600/hour public working rate and use a 1,750/hour theoretical ceiling. With the glassblowing pipe occupying one inventory slot, 27 molten glass at three ticks each gives 48.6 seconds of uninterrupted processing.

### Battlestaves

Water, earth, fire and air battlestaves use 2,450/hour as the practical working rate. Perfect banking is represented separately as the 2,625/hour theoretical ceiling.

### Gathering

Gathering methods intentionally omit random secondary drops so market profit is conservative and reproducible.

- amethyst: 90/hour working model inside the sourced 80-100/hour range
- magic logs: 130/hour, with dragon or crystal axe assumption
- redwood logs: 160/hour midpoint inside the sourced 140-180/hour range, with dragon axe assumption
- camphor logs: 385/hour working model, requiring 66 Woodcutting, 45 Sailing, partial Troubled Tortugans access, dragon axe and log basket for the modelled setup
- dark crabs: 308/hour with lobster pot, one dark fishing bait per catch and the 50 gp Piles noting fee; Wilderness PK risk is not monetised

Gathering AFK intervals are estimates rather than deterministic Make-X timers. They represent the expected interaction cadence for the modelled method and should not be interpreted as guaranteed idle periods.

The engorged bloodwood method converts one sap bucket and one redwood log into 105 seeking arrow shafts, then uses 105 feathers and 105 dragon arrows to make 105 tradeable seeking dragon arrows. The model uses the Wiki guide's 16 full batches/hour; its `118`-second AFK interval is only the average tree progress time with a dragon axe. Sap harvesting adds a click and 45-second drain, and arrow processing is included in the guide's hourly method rate.

### Shop hopping

The catalogue includes Pellem's mixed hide base guide, astral runes from Baba Yaga, cosmic runes from Tal Teklan, jaguar fur from Pellem and Fortis, and GE rune warhammers sold to Skulgrimen. Mixed hide bases use the Wiki money-making guide's 1,485 items/hour and exact 18,803,070 gp shop-purchase total, normalized to 55 batches of 27 items at a 12,662 gp average purchase price. Its Stamina potion input is priced from live GE data.

Astral runes, cosmic runes and jaguar furs use configured average per-item NPC purchase costs, then use live GE directional prices and seller tax for sale proceeds. These purchase costs are shown as a separate table and included in profit and capital calculations. Rune warhammers instead use live GE purchase costs and fixed NPC proceeds of 29,050 gp for the first item sold to an empty Skulgrimen stock; this NPC payment has no GE seller tax and the item's 70-per-four-hours GE buy limit caps sustained throughput at 17.5 per hour.

The non-guide shop-hopping entries use the user's 7-second world-switch time as an upper-bound rate. They exclude shop interactions, travel, banking and GE offer time, so their displayed hourly profit is not a measured end-to-end rate. The app labels these entries Shop hopping and repeats the rate limitation in each method's details.

## Corrections discovered during the audit

The completion pass fixed material catalogue/model errors:

1. Onyx bolt tips were corrected from 12 to 24 output per onyx.
2. Jewellery F2P/members flags were corrected.
3. Jewellery and battlestaff theoretical throughput values were corrected.
4. `minimum_cooking` was removed from player skill filtering.
5. Python boolean access flags are protected from numeric-metadata normalization.
6. Karambwan's Tai Bwo Wannai Trio requirement was added.
7. Camphor's current Sailing and Troubled Tortugans access requirements were added.
8. Longbow, cooking and glassblowing interaction intervals were aligned to deterministic tick timings.
9. Gathering equipment assumptions were added where they underpin the configured rate.
10. Fixed coin costs are now included in public capital requirements.
11. High-liquidity-risk warnings are correctly surfaced as high public market risk.

## Method types

Canonical public interaction types are:

- `bankstanding`
- `make-x`
- `autocast`
- `gathering`
- `shop-hopping`

Generated internal category prefixes such as `strict_afk/fletching`, `bankstanding/crafting`, and `gathering/mining` are normalized to the actual public skill category. Frontend filters consume the explicit method types instead of inspecting method names/descriptions.

## Audit provenance

Hand-maintained methods use detailed machine-readable entries in `config/method_audit.yaml`. Generated methods receive family-audit provenance from the loader using their own OSRS Wiki reference.

This means every enabled method reaches the evaluator with:

```text
audit.status = verified
audit.verified_at = 2026-08-29
audit.source = current OSRS Wiki reference
```

CI asserts this invariant across the entire merged catalogue.

## Ongoing maintenance policy

The backlog audit is complete, but OSRS mechanics can change. `verified` means the configured mechanics were checked against the current source at the audit date, not that they are immutable.

When a source/mechanic changes:

1. update the method configuration/catalogue
2. update `config/method_audit.yaml` for hand-tuned methods where applicable
3. update regression tests
4. update this audit note when the change affects a reusable catalogue rule

Market profitability itself is never copied from Wiki headline GP/hour. It continues to be calculated from current and historical RuneScape Wiki real-time prices API observations using this audited mechanical catalogue.
