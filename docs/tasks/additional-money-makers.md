---
status: done
---
# Additional money makers

## Next action

Treat any future catalogue expansion as a separate task.

## Outcome and scope

Extend the hand-authored Money Makers catalogue with Fountain of Rune charge routes and additional bankstanding processors. Expose active Wilderness routes with their own public classification so route cycles are not presented as AFK intervals.

## Inputs

- [AFK Method Catalogue Audit](../AFK_METHOD_CATALOG_AUDIT.md)
- [Recharging rings of wealth](https://oldschool.runescape.wiki/w/Money_making_guide/Recharging_rings_of_wealth)
- [Fountain of Rune](https://oldschool.runescape.wiki/w/Fountain_of_Rune)
- [Making pizza bases](https://oldschool.runescape.wiki/w/Money_making_guide/Making_pizza_bases)
- [Making pastry dough](https://oldschool.runescape.wiki/w/Money_making_guide/Making_pastry_dough)
- [Making pie shells](https://oldschool.runescape.wiki/w/Money_making_guide/Making_pie_shells)
- [Cooking plain pizzas](https://oldschool.runescape.wiki/w/Money_making_guide/Cooking_plain_pizzas)
- [Grinding chocolate bars](https://oldschool.runescape.wiki/w/Money_making_guide/Grinding_chocolate_bars)

## Acceptance

- Eight Fountain route variants carry explicit inputs, outputs, requirements and audit records.
- Five additional processing methods use sourced recipe and rate assumptions.
- Active routes appear as `Active route` in public method data and can be selected with public filters.
- A note records the ring guide's inconsistent route-text and result-table rates.
- Relevant tests pass; the task note records actual validation and merge state.

## Results

Merged as PR #37 in commit `06096b82a8b9056bfb72fe338971ca8e7211b11d`. GitHub Actions CI run #210 passed the full pytest suite and Chromium/Firefox browser acceptance on the code head `172ab2653a6cf2d69f0604037b85736452a3836d`. Local YAML parsing and method/audit consistency, Python compilation, and `node --check web/assets/app.js` passed. Local pytest could not run because pytest is not installed in the workspace; the CI test job ran the suite.

## Sources and rate choices

Fountain baseline uses the route guide's approximately 40 inventories/hour with the Wilderness Obelisk. Wilderness sword 4 methods use the low end of the stated 60-72 inventories/hour range. The same trip rate is an explicit estimate for other jewellery because the route guide does not give separate figures. One full Super energy(4) is charged per trip; Wilderness death risk is not priced.

Pastry dough uses nine items per ~15-second inventory (2,160/hour) and keeps the Wiki's 2,400/hour as an upper rate. Pizza bases use 2,400/hour. Pie shells use a 2,450-unit source batch with the 500/4h pie-dish limit. Plain pizzas use 540 per 30 minutes and level 68 Cooking. Chocolate grinding uses the 1,800/hour idle rate and records 9,000/hour as the high-intensity ceiling.
