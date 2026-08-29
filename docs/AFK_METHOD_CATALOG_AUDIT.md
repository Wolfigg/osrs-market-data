# AFK Method Catalogue Audit

Date: 2026-08-29

This document records the catalogue-quality pass for OSRS Profit Finder. It is maintainer documentation and is not part of the GitHub Pages public artifact.

## Audit goals

Every enabled AFK/bankstanding method should have defensible values for:

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
- explicit method type rather than UI inference from text

## Runtime structural validation

`load_yaml(config/methods.yaml)` now validates the merged built-in + hand-tuned catalogue before collection. Enabled methods must have:

- positive `cycles_per_hour`
- `theoretical_cycles_per_hour >= cycles_per_hour` when provided
- positive AFK interval
- at least one output
- positive input/output quantities and item IDs
- an OSRS Wiki reference
- at least one explicit/inferred method type

Invalid catalogue data fails collection/CI rather than silently reaching the public ranking.

## Explicit method semantics

Public method-type filters no longer depend on keywords in names/descriptions.

Canonical types currently used:

- `bankstanding`
- `make-x`
- `autocast`
- `gathering`

Generated category prefixes such as `strict_afk/fletching`, `bankstanding/crafting`, and `gathering/mining` are now treated as internal catalogue semantics. The public category is normalized to the actual skill, for example `Fletching` or `Mining`.

## Hand-tuned methods verified in this pass

Detailed machine-readable provenance is in `config/method_audit.yaml`.

Verified groups:

- steel cannonballs with double ammo mould
- sapphire, emerald, ruby and diamond bolt tips
- mahogany Plank Make
- camphor Plank Make
- bronze, iron, steel, mithril and adamant dart tips

For Plank Make, Earth runes remain excluded from consumed inputs because the configured method explicitly assumes an Earth-rune-supplying staff. Nature/Astral runes and the per-log coin charge remain consumed costs.

For cannonballs, the configured economic cycle is one steel bar -> four cannonballs. The double ammo mould processes two bars -> eight cannonballs physically, but the normalized per-bar cycle is economically equivalent and keeps buy-limit/capital arithmetic straightforward.

## Generated-method groups checked in this pass

Source verification also covered several built-in groups even where their AFK interval still needs separate observational validation:

- opal, jade, red topaz, dragonstone and onyx bolt-tip quantities/levels
- rune dart-tip quantity and level
- jewellery access rules and throughput assumptions
- battlestaff throughput
- amethyst working rate
- magic-log working rate
- redwood-log working range
- camphor-log rate basis
- dark-crab catch rate, bait use and Piles noting cost

These checks are encoded as loader corrections/regression tests where the generated defaults were wrong.

## Corrections discovered during source verification

### Jewellery membership

The generated catalogue previously marked all gold jewellery as F2P and all gem jewellery as members-only. That is not correct.

Current access model:

- gold rings, necklaces and unstrung amulets: F2P
- sapphire through diamond rings, necklaces and unstrung amulets: F2P
- dragonstone rings, necklaces and unstrung amulets: members
- all bracelets, including gold bracelets: members

The loader now applies these known access corrections to the generated catalogue before optional hand-maintained overrides.

Primary references:

- https://oldschool.runescape.wiki/w/Jewellery
- https://oldschool.runescape.wiki/w/Crafting/Experience_table
- https://oldschool.runescape.wiki/w/Bracelet

### Jewellery throughput

Current Crafting training guidance uses:

- 1,400 items/hour for gem + metal-bar jewellery
- 1,600 items/hour for metal-bar-only jewellery

The public profit model remains intentionally conservative at 1,400/hour for gold-only jewellery because its existing 69-second interaction window is based on a slower practical bankstanding cycle. The theoretical ceiling is now 1,600/hour. Gem jewellery remains 1,400/hour and no longer advertises an unsupported 1,450/hour theoretical value.

Primary reference:

- https://oldschool.runescape.wiki/w/Pay-to-play_Crafting_training

### Battlestaff throughput

The current training guide assumes 2,450 battlestaves/hour and states that perfect banking can reach 2,625/hour. The working rate was already correct; the theoretical ceiling has been corrected from 2,500 to 2,625.

Primary reference:

- https://oldschool.runescape.wiki/w/Pay-to-play_Crafting_training

### Onyx bolt tips

Onyx is an exception to the ordinary 12-tip precious-gem conversion. One onyx produces 24 onyx bolt tips at level 73 Fletching. The generated catalogue previously used 12, which halved output value and therefore materially understated profit.

Primary references:

- https://oldschool.runescape.wiki/w/Fletching
- https://oldschool.runescape.wiki/w/Onyx_bolt_tips

### Auxiliary requirement metadata

Generated cooking methods contain both the deterministic model requirement (`cooking: 99` with Cooking cape) and an informational `minimum_cooking` value.

`minimum_cooking` is not an OSRS skill name and was being exposed to the local skill filter as if it were one. Numeric requirement metadata that is not a real skill is now moved to internal `requirement_metadata`, preventing false negatives in the browser skill filter.

Python booleans are explicitly excluded from this conversion because `bool` is a subclass of `int`; otherwise flags such as `members: false` would incorrectly be stripped from the requirements object.

### Gathering equipment assumptions

Requirements now expose equipment used by the sourced rates rather than only the skill level:

- magic logs: dragon or crystal axe
- redwood logs: dragon axe
- camphor logs: dragon axe and log basket, matching the feedback basis used by the configured rate
- dark crabs: lobster pot

Secondary-drop boosting gear is not required where the corresponding secondary value is intentionally omitted from the profit model. For example, redwood bird nests are excluded, so Twitcher's gloves are not required by this model.

## Remaining source-verification work

Structural validation now covers the whole catalogue. Remaining source-level work is narrower:

1. AFK/interaction intervals for gathering methods, which are less deterministic than Make-X intervals
2. unstrung maple/yew/magic longbow practical rates and intervals
3. stringing maple/yew/magic longbow practical rates and intervals
4. cooking karambwan, sharks, monkfish, anglerfish and dark crabs, especially burn-free model assumptions
5. detailed jewellery per-product level/output review beyond the shared throughput/access rules
6. blowing unpowered orbs
7. generated bolt-tip practical throughput for the less-common gems

Each group should be checked against current OSRS Wiki mechanics, not merely old money-making headline profit figures. Market profitability remains calculated from live/historical RuneLite/Wiki market observations.

## Audit policy going forward

A catalogue method should only receive `audit.status: verified` after its mechanics have been checked against a current authoritative source. Structural validity alone does not mean source verification.

When a verified assumption changes, update:

1. the method configuration/catalogue
2. `config/method_audit.yaml` when applicable
3. relevant unit tests
4. this audit note if the correction affects a reusable catalogue rule
