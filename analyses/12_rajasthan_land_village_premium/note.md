# Rajasthan land records: village premium

Snapshot: 2026-09-13T01:15:58.970722+00:00 to 2026-09-13T01:16:05.986325+00:00 (UTC).

Surname error: **60.89** per 100; surname plus village: **40.57**. Village premium: **20.32 percentage points**, removing 33.37% of surname error.

![Prediction errors](out/fig/village_premium.png)

## What the records support

The question concerns people represented in land records. The measurable unit is a recorded owner entry after consolidating repeated account lists across plots. Entries are not verified unique people or households. Joint-owner multiplicity is retained; matching names across accounts are not automatically merged.

The target is the recorded caste field, with Unicode NFC and whitespace cleanup only. The final name token is the surname proxy. Rare labels and parenthetical text remain. Results describe aggregate predictability, not individual caste identity.

Each prediction excludes every eligible entry from its account. An empty cue cell falls back to the global mode after excluding that same account; a completely empty training set is unsupported. Ties follow lexical label order.

The crawl is unfinished and geography was not selected at random. This is a census of saved checkpoint prefixes, not a census of either state or its landholders. Missing caste/name fields and extraction failures may be selective. The direction of incomplete-coverage bias is unknown. Bihar remains contextual: target labels, observation units and scoring protocols differ.

## Census reconciliation

| Quantity | Count |
|---|---:|
| active incomplete streams | 8 |
| audited record denominator | 1,973,582 |
| audited record numerator | 1,973,582 |
| audited successful records | 718,335 |
| caste fill rate | 0.9824425206086846 |
| checkpoint files | 5,203 |
| confirmed complete units | 5,195 |
| confirmed complete villages | 5,195 |
| conflicting entries excluded | 0 |
| conflicting entries retained | 0 |
| consolidated owner entries | 3,687,887 |
| cross sheet conflicting accounts | 0 |
| districts with owner entries | 4 |
| dns failed attempts | 0 |
| dns unresolved keys | 0 |
| eligible entries | 3,622,886 |
| empty caste entries | 64,750 |
| empty name entries | 58 |
| excluded entries | 65,001 |
| expected units | 50,109 |
| failed attempts | 655 |
| failed attempts without identity | 0 |
| gzip tail or decode error | 8 |
| http failed attempts | 653 |
| http unresolved keys | 0 |
| inferred plot links | 1,255,247 |
| missing account identity | 8,294 |
| name fill rate | 0.9999842728369931 |
| other failed attempts | 0 |
| other unresolved keys | 0 |
| ownerless successful records | 8,847 |
| parsed owner entries before consolidation | 3,687,887 |
| parsed shard entries | 3,687,887 |
| pdf decoder failed attempts | 0 |
| pdf decoder unresolved keys | 0 |
| pdf provenance failed attempts | 0 |
| pdf provenance unresolved keys | 0 |
| pdf source failed attempts | 0 |
| pdf source unresolved keys | 0 |
| portal miss attempts | 352,463 |
| repeated account entries removed | 0 |
| repeated plot owner entries | 7,762,991 |
| saved attempt rows | 2,331,895 |
| successful attempts | 1,973,582 |
| timeout failed attempts | 2 |
| timeout unresolved keys | 0 |
| unique saved accounts | 710,041 |
| unique successful source keys | 1,973,582 |
| unresolved failed source keys | 0 |
| villages with owner entries | 3,096 |

Audited successful-record and cell counts above are numerators; saved successful attempts and saved cells are their denominators. Failed or invalid payloads remain explicit exclusions. Fill rates cover consolidated saved entries, not the population.

PDF cells reuse the source decoder’s all-page extraction. Original bytes, checksums, page-count metadata, printed account/village identity, and approved spelling evidence are retained and verified. This downstream run does not claim an independent OCR audit.

Failure counts describe attempts; unresolved-source-key counts remove keys with a saved successful answer or an explicit portal miss. These are distinct from ownerless successful captures. Failure categories reflect logged reasons.

## Sensitivities

| Analysis | Entries | Premium (points) |
|---|---:|---:|
| complete villages | 3,618,892 | 20.34 |
| signature sensitivity | 2,641,844 | 9.55 |

The signature sensitivity collapses exact within-village matches of owner name, relative name, relation and residence when a relative is present. Conflicting caste labels are excluded from that sensitivity. Homonyms and absent relatives prevent interpreting it as verified person deduplication. Its holdout unit changes to that signature; it does not establish a bound on person-level error.

Odisha normalization, when present, is the former surname-assisted merge and label-floor method. It is exploratory because the target construction sees the full surname distribution; the recorded-label primary result does not use those merges.

## Surname proxy diagnostic

- entries with relative: 3,618,469
- entries sharing any token: 75,012
- entries sharing first token: 2,284
- entries sharing last token: 69,690
- eligible name entries: 3,622,886
- single token names: 3,060,418
- multitoken names: 562,468

Name-length counts cover every eligible owner entry, including entries without a relative. A token is whitespace-delimited: joined spellings count as one token. For a single-token name the final-token proxy is the entire recorded name; neither one nor several tokens establishes that a family name is present.

Token agreement is conditional on an available relative; first and last matches can overlap. It does not establish surname position for every owner.

## Whole-name and spacing comparison

These checks replace the final-token cue with the entire recorded name, then compare it with the same name after removing spaces. The eligible entries, caste labels, weights and account holdout stay fixed. Space removal gives `रामलाल` and `राम लाल` the same prediction key; it does not identify word boundaries, recover a surname, or merge owner entries.

| Name cue | Error per 100 | With village | Premium (points) |
|---|---:|---:|---:|
| Final token | 60.89 | 40.57 | 20.32 |
| Whole recorded name | 60.19 | 40.59 | 19.60 |
| Whole name without spaces | 60.21 | 40.48 | 19.73 |

Spacing-variant groups: 20,918; entries in those groups: 1,829,502 / 3,622,886. A group has more than one distinct recorded spelling that becomes identical after removing spaces. Different names can also collide under this transformation, so it is reported as a sensitivity, not a verified spelling correction.

## District results

| District code | Entries | Premium (points) |
|---|---:|---:|
| 01 | 1,817,072 | 30.09 |
| 02 | 459,755 | 2.60 |
| 03 | 591,564 | 0.91 |
| 21 | 754,495 | 9.45 |

District scores recompute the training population within each district. A pooled village cue also conveys district and region; pooled and district premiums answer different conditioning questions.

Run `2026-09-13T032234.615894Z`; manifest SHA-256 `1f0c6a656c41c165c54d14c57223e0bd0b842ff563865ad3e6fa0ba7b25e0045`.
