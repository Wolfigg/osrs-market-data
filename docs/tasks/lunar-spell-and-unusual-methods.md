---
status: done
---
# Lunar spell and unusual shop methods

## Next action

None. The change is merged to `master` and the public Pages site shows the added methods.

## Scope

Add profitable Lunar spell methods that are absent from the catalogue and add shop-pack methods suggested by the project's unusual money-making research. Recharge Dragonstone and Plank Make already exist, so they are not duplicated.

## Acceptance

- Tan Leather, Spin Flax, Superglass Make, Humidify, and Hunter Kit use verified mechanics, sourced rates, item IDs, requirements and runes.
- Expected Superglass Make yield is modelled as an average, not a guaranteed integer output.
- Sandworm and bone bolt shop packs have separate NPC purchase costs, output items, requirements, and hop-only ceiling labels.
- Each enabled method has a verified OSRS Wiki audit record.
- The catalogue is validated, CI passes, and the change is merged to `master`.

## Validation

- PR #38 merged to `master` as `77eb10dcbb4587d406166604da3cf3a0f4044e5c`.
- CI run 214 passed: 244 tests; Chromium and Firefox browser acceptance passed.
- The live Pages site loaded with the new Tan Leather, Spin Flax, and Humidify entries.

## Sources and limitation

- [Recharge Dragonstone](https://oldschool.runescape.wiki/w/Recharge_Dragonstone)
- [Tan Leather](https://oldschool.runescape.wiki/w/Tan_Leather)
- [Spin Flax](https://oldschool.runescape.wiki/w/Spin_Flax)
- [Superglass Make](https://oldschool.runescape.wiki/w/Money_making_guide/Casting_Superglass_Make)
- [Humidifying clay](https://oldschool.runescape.wiki/w/Money_making_guide/Humidifying_clay)
- [Filling buckets with water](https://oldschool.runescape.wiki/w/Money_making_guide/Filling_buckets_with_water)
- [Hunter kit](https://oldschool.runescape.wiki/w/Money_making_guide/Casting_Hunter_kit)
- [Tynan's Fishing Supplies](https://oldschool.runescape.wiki/w/Tynan%27s_Fishing_Supplies)
- [Nardok's Bone Weapons](https://oldschool.runescape.wiki/w/Nardok%27s_Bone_Weapons)
- [User-provided unusual money-making site](https://unusualmoneymaking.com/)

The unusual money-making page returned a database-load error and no method rows when checked on 2026-11-27. Sandworm packs and bone bolt packs are included as previously discussed shop-hopping candidates; their game mechanics and shop prices are verified against the OSRS Wiki. The seven-second rate is a hop-only ceiling, not a measured end-to-end rate.
