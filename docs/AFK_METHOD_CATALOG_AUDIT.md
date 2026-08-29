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

### Auxiliary requirement metadata

Generated cooking methods contain both the deterministic model requirement (`cooking: 99` with Cooking cape) and an informational `minimum_cooking` value.

`minimum_cooking` is not an OSRS skill name and was being exposed to the local skill filter as if it were one. Numeric requirement metadata that is not a real skill is now moved to internal `requirement_metadata`, preventing false negatives in the browser skill filter.

## Remaining source-verification work

Structural validation now covers the whole catalogue, but source-level verification should continue group by group. The remaining generated groups are:

1. opal, jade, red topaz, dragonstone and onyx bolt tips
2. rune dart tips
3. fletching unstrung maple/yew/magic longbows
4. stringing maple/yew/magic longbows
5. cooking karambwan, sharks, monkfish, anglerfish and dark crabs
6. gold and gem jewellery rates/levels across all products
7. blowing unpowered orbs
8. water/earth/fire/air battlestaves
9. mining amethyst
10. cutting magic, redwood and camphor logs
11. catching dark crabs

Each group should be checked against current OSRS Wiki mechanics, not merely old money-making headline profit figures. Market profitability remains calculated from live/historical RuneLite/Wiki market observations.

## Audit policy going forward

A catalogue method should only receive `audit.status: verified` after its mechanics have been checked against a current authoritative source. Structural validity alone does not mean source verification.

When a verified assumption changes, update:

1. the method configuration/catalogue
2. `config/method_audit.yaml` when applicable
3. relevant unit tests
4. this audit note if the correction affects a reusable catalogue rule
