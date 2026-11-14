# Rajasthan recorded-name investigation: September 12, 2026

The 84.5% figure is a count of whitespace-delimited name fields in the saved
analysis data. It does not mean that 84.5% of Rajasthan residents have only a
given name, or that their legal names contain one word. The Bhu-Naksha endpoint
supplies predominantly unspaced owner names in the captured districts. The
analysis takes the final token; for an unspaced name, that is the whole field.
It has not established a family-surname effect.

## Reproduced denominator

The original frozen run contains **3,060,282 single-token names out of
3,622,666 eligible owner entries (84.475963%)**. These are entries after account
consolidation, not unique people or distinct name strings. Eligibility requires
usable recorded name and caste fields. Odisha's corresponding count is
73,070 / 12,155,300 (0.601137%).

| Captured district | Eligible entries | Single-token entries | Percent |
|---|---:|---:|---:|
| Ajmer (01) | 1,816,966 | 1,534,159 | 84.435 |
| Bikaner (02) | 459,733 | 394,295 | 85.766 |
| Churu (03) | 591,515 | 493,804 | 83.481 |
| Nagaur (21) | 754,452 | 638,024 | 84.568 |

All four captured districts were checked. No district or relation group was
selected to establish a population-wide naming claim. The crawl is incomplete
and geographically selective.

## Competing explanations and checks

**Downstream first-word extraction:** rejected for this denominator. The adapter
only applies Unicode NFC and whitespace normalization to the name field. An
independent re-read matched all **3,622,666 / 3,622,666** eligible entries to the
saved source names using source sheet, account, name and relative. The comparison
collapsed duplicate matching keys before joining, so repeated co-owner slots did
not multiply the audit denominator.

**Incorrect relation boundary:** the census read every one of **718,335 / 718,335**
direct saved payloads across 5,203 frozen checkpoint files. Across 3,663,241
numbered owner lines with an explicit relation marker, an independent boundary
scan found **zero** differences between the full preceding name and the parser's
name, after the documented normalization. It found zero multiword-to-single-token
changes within those lines. Embedded sheet and plot identities all matched.
The eight interrupted gzip endings were already identified as open streams at
capture; every complete saved line before those tails was included.

**Source formatting:** supported. Eight fresh official-portal controls, one
single-token and one multiword case per district, returned matching plot/sheet
identities and exactly the saved owner names. These targeted transport controls
supplement the census; they are not estimates of population prevalence. The
endpoint returns the owner name, relative, caste and residence in one marked
text block; the parser keeps the complete name before the relation marker.
This does not verify names against another register or establish that this
endpoint supplies every part of a person's legal name.

Spacing is substantive for this metric: the eligible data contain 14,361 entries
spelled `रामलाल` and 182 spelled `राम लाल`. Across all eligible data, 1,477,244
single-token entries have a spaced spelling counterpart elsewhere when spaces
are removed. These are string comparisons, not assertions that the entries refer
to the same people, nor a license to insert spaces into names automatically.

**Embedded newlines:** a separate, reproducible parser defect. The full census
found 3,287 multiline owner blocks. Joining their continuations changes 22
owner names, including 17 one-token-to-multiword changes, as well as 221 relative,
313 caste, 3,229 residence and 230 share fields; these counts overlap. All 22
changed-name entries previously lacked a parsed caste field and were excluded
from the 84.5% denominator. This defect therefore does not explain that figure.
Two fresh portal responses reproduced the saved multiline blocks with matching
identities.

## Repair and recurring diagnostics

The Rajasthan parser now keeps continuation lines with their numbered owner,
retains the original multiline text, and stops at a new owner or metadata block.
Government-owner entries retain their existing treatment. Raw checkpoints were
not edited and the crawler was not restarted. Only its supervised audit job was
reloaded to use the corrected parser.

The shared pipeline now records `eligible_name_entries`, `single_token_names`
and `multitoken_names` for both states on every refresh. Their denominator
includes entries without relatives; the separate relative-token agreement
statistics remain conditional on a recorded relative. Generated notes explain
that whitespace tokens do not establish family-name position.

The original run remains preserved at
`.local/land-records/runs/rajasthan/2026-09-13T011605.989716Z`. Its computational
manifest SHA-256 is
`f130ceb8642bb147c2236794c190873db5c0235fd4367d821b4585b5d10fa39f`.
Aggregate census receipts, the diagnostic code and the corrected-parser replay
manifest are retained privately under
`.local/land-records/investigations/20260912-rajasthan-name-tokens/`.

Verification: the new continuation regression tests fail with the old parser.
The repaired parser passes all 53 Rajasthan tests, Ruff, Pyright and pydoclint.
All 25 retained continuation cases agree with independently joined owner blocks
after whitespace normalization. The shared pipeline and README checks pass
74 tests, Black, isort and flake8. The corrected-parser replay uses exactly the
original frozen checkpoints, so newly scraped records cannot explain a change
in the analysis.

## Corrected full-census result

The replay completed at **20:14 PDT on September 12, 2026**. It retains all
3,687,887 parsed owner entries and recovers **220 additional eligible entries**:
3,622,886 in total. There are **3,060,418 / 3,622,886 single-token names
(84.474587%)**, still **84.5%** at one decimal. The original single-token claim
was not produced by the newline defect.

The primary village premium changes from **20.3142 to 20.3159 points**;
the matching-signature sensitivity changes from **9.5515 to 9.5507 points**.
The README's rounded 20.3-point and 9.6-point results are unchanged. The current
analysis note and figure have been regenerated from the corrected census.

The corrected run is
`.local/land-records/runs/rajasthan/2026-09-13T030713.588580Z`, with computational
manifest SHA-256
`6c9ced02de699a1a6895e07a07f38272202fdcf044142158bab6be63dce308f8`.
Independent verification checked every declared output artifact hash, all
3,622,886 eligible rows and account-slot keys, the exact token denominator,
district totals, and identical source-checkpoint hashes before and after the
repair. The original run and raw inputs remain intact.

## Handling joined spellings in the analysis

The next comparison holds all 3,622,886 eligible entries, 688,265 accounts,
20,307 caste labels, weights and account holdouts fixed. It uses the whole
recorded name, then removes spaces from that name to construct a second
prediction key. `रामलाल` and `राम लाल` share that second key; no word boundary
or family-name label is inferred. Original names and owner entries remain intact.

| Name cue | Error per 100 | With village | Village premium (points) |
|---|---:|---:|---:|
| Final token benchmark | 60.8853 | 40.5694 | 20.3159 |
| Whole recorded name | 60.1928 | 40.5932 | 19.5995 |
| Whole name without spaces | 60.2122 | 40.4800 | 19.7322 |

There are 201,850 distinct recorded names and 180,468 distinct keys after space
removal. The 20,918 groups containing more than one recorded spacing form cover
1,829,502 entries. This is a census of string variation, not verified identity
matching. Different names can also collide after removing spaces.

Space removal produces 4,101 fewer errors with village but 706 more without
village: changes of -0.1132 and +0.0195 percentage points respectively. This
mixed, small effect supports retaining it as a sensitivity rather than declaring
all such merges correct. The roughly 20-point village result survives use of
whole names and is not driven by whitespace tokenization.

The practical remedy is to separate **name comparison** from **surname
extraction**. The shared pipeline now performs these whole-name and spacing
checks automatically. It does not split joined names using a guessed dictionary,
copy caste labels into the name, or treat the final component as a verified
surname. Surname-specific claims still require independent evidence of a family
name; whitespace normalization cannot supply that evidence.

This run began scoring at 2026-09-13T03:22:55.697597+00:00 (UTC; see the manifest for completion
of all outputs). Its directory is `.local/land-records/runs/rajasthan/2026-09-13T032234.615894Z` and its manifest
SHA-256 is `1f0c6a656c41c165c54d14c57223e0bd0b842ff563865ad3e6fa0ba7b25e0045`. The source inputs and eligible membership
are identical to the corrected-parser baseline. All 75 relevant tests, Black,
isort and flake8 pass, including an exhaustive synthetic account-holdout check
with spacing variants in the same account and conflicting labels across accounts.
