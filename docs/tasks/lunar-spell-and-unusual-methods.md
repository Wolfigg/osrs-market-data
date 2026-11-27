---
status: done
---
# Lunar spell and unusual shop methods

## Next action

None. The timing correction is merged to `master`.

## Scope

Add profitable Lunar spell methods that are absent from the catalogue and add shop-pack methods suggested by the project's unusual money-making research. Recharge Dragonstone and Plank Make already exist, so they are not duplicated.

## Acceptance

- Tan Leather, Spin Flax, Superglass Make, Humidify, and Hunter Kit use verified mechanics, sourced rates, item IDs, requirements and runes.
- Expected Superglass Make yield is modelled as an average, not a guaranteed integer output.
- Sandworm and bone bolt shop packs have separate NPC purchase costs, output items and requirements, with provisional cycle estimates that count pack purchases and openings and retain a distinct hop-only ceiling.
- Bandit's brew, limestone and spades are added from the live unusual-method list with verified NPC stock, costs and access requirements, plus provisional cycle estimates and a separate hop-only ceiling.
- Each enabled method has a verified OSRS Wiki audit record.
- The catalogue is validated, CI passes, and the change is merged to `master`.

## Shop-hop cycle timing follow-up

The prior model used the seven-second world-hop interval as the full cycle for ten shop-hopping methods. Their configured rate now includes a provisional 0.6-second tick per shop-open action, transaction action, and pack-opening action. Full-stocking Baba Yaga's 250 astral runes uses five Buy-50 transaction actions. The sandworm cycle has one pack opening; the bone-bolt cycle has two. The estimated cycles/hour are derived as `3600 / estimated_cycle_seconds`: 339.6 for Baba Yaga, 409.1 for sandworm packs, 383.0 for bone bolt packs, and 439.0 for the other one-transaction methods. Travel, banking, and GE offer time remain excluded, so these are estimates rather than measured end-to-end rates. The mixed-hide method keeps its guide-based rate.

- Source for tick length and shop batch sizes: [Game tick](https://oldschool.runescape.wiki/w/Game_tick), [Shop](https://oldschool.runescape.wiki/w/Shop).
- PR #44 merged to `master` as `30ce7d66406c80bc86ab568deb59e1cc820a4d1b`.
- CI run 227 passed: catalogue test job and Chromium/Firefox browser acceptance.

## Validation

- PR #38 merged to `master` as `77eb10dcbb4587d406166604da3cf3a0f4044e5c`.
- CI run 214 passed: 244 tests; Chromium and Firefox browser acceptance passed.
- The live Pages site loaded with the new Tan Leather, Spin Flax, and Humidify entries.
- PR #39 added Bandit's brew, Papyrus and Spades; PR #40 fixed YAML formatting required by the publish workflow; PR #41 corrected the Hunter Kit output mapping from item ID 598 to Unlit torch ID 596; PR #42 replaced Papyrus with Limestone because the app had no usable current Papyrus price.
- PR #42 CI passed the test and browser-acceptance jobs. The master refresh run `46018065761` completed successfully.
- The published catalogue was checked on 2026-11-27. It shows Bandit's brew, Limestone from Razmire and Spades; the merged Lunar catalogue includes Recharge Dragonstone jewelry and other spell methods.
- PR #44 corrected shop-hop throughput to include shop interactions and pack openings; the current rate model remains provisional until an end-to-end loop is measured.

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
- [Razmire Builders Merchants](https://oldschool.runescape.wiki/w/Razmire_Builders_Merchants)
- [Limestone](https://oldschool.runescape.wiki/w/Limestone)
- [Spade](https://oldschool.runescape.wiki/w/Spade)
- [User-provided unusual money-making site](https://unusualmoneymaking.com/)

The live unusual-method page displayed 118 Unusual Methods and 14 Special Methods when reviewed on 2026-11-27. Bandit's brew, limestone and spades were added from that list. OSRS Wiki shop data supplies the configured NPC prices, stock and access requirements; the limestone model buys one item per world at the fully stocked 10 gp price. Market proceeds use the app's live price and liquidity model. The ten methods that previously used the seven-second hop-only ceiling now use a provisional cycle-time estimate. One 0.6-second game tick is budgeted for each shop-open action, purchase or sale transaction, and pack opening. The hop-only ceiling remains 3600 / 7 = 514.3 cycles/hour. The mixed-hide method retains its separate guide-based throughput estimate.
