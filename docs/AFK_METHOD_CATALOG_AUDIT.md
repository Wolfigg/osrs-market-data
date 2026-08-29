# AFK Method Catalogue Audit

Date: 2026-08-29
Status: complete for the enabled catalogue

This document records the completed catalogue-quality pass for OSRS Profit Finder. It is maintainer documentation and is not part of the GitHub Pages public artifact.

## Audit standard

Every enabled AFK/bankstanding method must have defensible values for:

- item IDs and input/output quantities
- realistic cycles per hour
- theoretical cycles per hour where applicable
- interaction/idle interval
- membership status
- skill, quest and equipment requirements
- reusable equipment vs consumed inputs
- GE buy-limit applicability
- fixed coin costs
- source/reference provenance
- explicit method type rather than frontend inference from text

`load_yaml(config/methods.yaml)` now enforces this at runtime. An enabled method must have positive throughput and interval, valid item quantities, at least one output, an OSRS Wiki reference, a method type, and `audit.status: verified` with an OSRS Wiki audit source. Invalid catalogue data fails CI/collection instead of silently reaching public rankings.

## Catalogue families verified

### Cannonballs

Steel cannonballs with double ammo mould are modelled as one normalized economic cycle per steel bar: one bar -> four cannonballs. The mould physically processes two bars -> eight cannonballs at a time, but the normalized cycle keeps price, GE-limit and capital arithmetic equivalent. The working model remains conservative relative to the efficient training-table rate.

### Gem bolt tips

Sapphire, emerald, ruby, diamond, opal, jade, red topaz and dragonstone use the ordinary gem-to-bolt-tip recipe. Onyx is explicitly corrected to 24 tips per onyx at level 73 Fletching rather than the ordinary 12-tip output.

### Dart tips

Bronze, iron, steel, mithril, adamant and rune dart tips use one bar -> ten tips. Working throughput is kept separate from the Smiths' Uniform theoretical ceiling.

### Plank Make

Mahogany and camphor Plank Make remain autocast/bankstanding methods, not High Alch exits. Nature/Astral runes and per-log coin charges are consumed costs. Earth runes are excluded because the configured method assumes an Earth-rune-supplying staff, which is reusable equipment.

The public capital calculation now includes fixed coin charges, correcting the previous understatement for Plank Make.

### Longbow cutting

Maple, yew and magic unstrung longbows use the regular-knife Make-X model. A 27-log batch at three ticks per bow gives 48.6 seconds of uninterrupted processing. The public working rate remains 1,500 logs/hour and the sourced regular-knife theoretical ceiling is 1,800/hour.

### Longbow stringing

Maple, yew and magic longbow stringing remains classified as low-interaction bankstanding rather than strict AFK. A normal 14-bow inventory at two ticks per bow gives 16.8 seconds between banking interactions. The 2,400/hour working rate is retained.

### Cooking

Karambwan, sharks, monkfish, anglerfish and dark crabs use a deterministic zero-burn model at 99 Cooking with the Cooking cape. The public working rate remains a conservative 1,300 food/hour. Ordinary Make-X cooking is four ticks per item, so a 28-item inventory gives 67.2 seconds of uninterrupted processing and a 1,500/hour theoretical ceiling.

Cooking karambwan also requires Tai Bwo Wannai Trio. The method intentionally models AFK Make-X cooking, not the high-attention one-tick karambwan technique.

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

Market profitability itself is never copied from Wiki headline GP/hour. It continues to be calculated from current and historical RuneLite/Wiki market observations using this audited mechanical catalogue.
