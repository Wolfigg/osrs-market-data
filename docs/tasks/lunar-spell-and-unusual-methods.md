---
status: in_progress
---
# Lunar spell and unusual shop methods

## Next action

Finish review and merge the follow-up PR adding three unusual shop-hopping methods.

## Scope

Add profitable Lunar spell methods that are absent from the catalogue and add shop-pack methods suggested by the project's unusual money-making research. Recharge Dragonstone and Plank Make already exist, so they are not duplicated.

## Acceptance

- Tan Leather, Spin Flax, Superglass Make, Humidify, and Hunter Kit use verified mechanics, sourced rates, item IDs, requirements and runes.
- Expected Superglass Make yield is modelled as an average, not a guaranteed integer output.
- Sandworm and bone bolt shop packs have separate NPC purchase costs, output items, requirements, and hop-only ceiling labels.
- Bandit's brew, papyrus and spades are added from the live unusual-method list with verified NPC stock, costs, access requirements and hop-only ceiling labels.
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
- [The Big Heist Lodge](https://oldschool.runescape.wiki/w/The_Big_Heist_Lodge)
- [Rasolo](https://oldschool.runescape.wiki/w/Rasolo)
- [Spade](https://oldschool.runescape.wiki/w/Spade)
- [User-provided unusual money-making site](https://unusualmoneymaking.com/)

The live unusual-method page displayed 118 Unusual Methods and 14 Special Methods when reviewed on 2026-11-27. Bandit's brew, papyrus and spades were added from that list. OSRS Wiki shop data supplies the configured NPC prices, stock and access requirements; market proceeds continue to use the app's live price and liquidity model. The seven-second rate is a hop-only ceiling, not a measured end-to-end rate.
