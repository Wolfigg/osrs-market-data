# Shop-hopping methods

Status: complete

## Outcome

Add shop-hopping methods to Money Makers and make NPC shop revenue distinct from Grand Exchange output revenue and tax.

## Acceptance

- The catalogue includes the mixed hide base guide and additional shop purchase or shop sale methods.
- All methods have item IDs, requirements, OSRS Wiki references and verified audit entries.
- NPC shop purchase costs are visible as separate batch costs and included in capital.
- NPC shop sales can be the sole revenue path and are not charged GE seller tax.
- Public filters identify Shop hopping; method details show NPC sale proceeds separately.
- Shop-hop-only rates are identified as upper bounds when transaction timing is unknown.
- Relevant tests and public-site checks pass; final revision is pushed and merged.

## Sources and rate basis

- [Buying mixed hide bases](https://oldschool.runescape.wiki/w/Money_making_guide/Buying_mixed_hide_bases)
- [Astral rune](https://oldschool.runescape.wiki/w/Astral_rune)
- [Tal Teklan Rune Shop](https://oldschool.runescape.wiki/w/Tal_Teklan_Rune_Shop)
- [Jaguar fur](https://oldschool.runescape.wiki/w/Jaguar_fur)
- [Rune warhammer](https://oldschool.runescape.wiki/w/Rune_warhammer)

The mixed hide method uses the Wiki guide's 1,485 bases/hour. Other methods use the user's 7-second world-switch interval as an upper bound and exclude shop dialogue, travel, banking and GE offer time. Their GP/hour must not be read as a measured full-cycle rate.

## Result

Added six shop-hopping methods, NPC shop purchase and sale economics, a Shop hopping filter, audit records, and documentation. The Python CI suite and Chromium/Firefox browser acceptance checks passed on PR #36. PR #36 was squash-merged as `0dbb10350ea0050f7487751c03d955b2e280085f`.

## Next action

No further action.
