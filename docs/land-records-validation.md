# Initial land-record pipeline validation: September 12, 2026

This records the first completed shared-pipeline runs. Future refreshes generate new analysis notes; these validation results remain tied to the snapshots below.

## Full saved-data runs

| State | Successful captures audited / saved | Eligible owner entries | Eligible accounts | Eligible villages | Surname error | Surname + village error | Premium (points) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Odisha | 5,569,849 / 5,569,849 | 12,155,300 | 5,308,212 | 18,142 | 50.56 | 25.56 | 25.00 |
| Rajasthan | 1,973,582 / 1,973,582 | 3,622,666 | 688,245 | 3,075 | 60.88 | 40.57 | 20.31 |

Both runs use `audit_mode: census` and `sampling_limit: 0`. The unit is a recorded owner entry, not a verified unique person. Odisha covers eligible entries in 30 districts; Rajasthan currently covers four. These are unfinished, nonrandom portal captures, so the estimates do not describe either state’s full population.

Odisha audited all 16,018,459 saved cells, including 20,281 PDF captures. Retained PDF bytes, checksums and recorded printed provenance passed validation. Its 680 ownerless successful captures remain extraction gaps. Failure histories also retain 21,400 unresolved exact option keys, including 332 whose last logged failure is classified as a PDF source defect; these are separate from the successful-payload census. No decoder-labelled failure key remains unresolved in that disposition ledger. Rajasthan audited 718,335 direct payloads and resolved 1,255,247 inferred plot links. Those links would otherwise expand into 7,762,991 repeated owner entries; the pipeline does not count them as additional owners. Rajasthan retains 8,847 ownerless-capture and 8,294 missing-account-identity exclusions; these categories can overlap.

All 254 Odisha and eight Rajasthan interrupted gzip endings were observed open at capture. No unverified interrupted endings, duplicate successful source keys, or provenance mismatches were reported. These are frozen-prefix observations, not claims about the portals’ current state. Seven Odisha legacy completion sidecars remain unverified. Source-unit counters such as `unique_saved_accounts` are summed within checkpoint files; `primary.accounts` is the distinct eligible account count after consolidation.

## Material sensitivity in Rajasthan

The primary premium is 20.31 points; confirmed-complete-village scoring gives 20.34. Matching-signature consolidation gives 9.55 points across 2,641,685 entries. A full aggregate check reproduced the membership change: 891,906 repeated consistent-signature entries collapse, and 89,075 entries in 25,425 conflicting-label signatures are excluded. The 4,417 entries without a relative remain unconsolidated.

The surname-plus-village global-fallback share rises from 20.0% to 31.0%. Repeated identities across accounts, homonyms, conflicting source labels, changed observation weights and reduced local training support are competing contributors. This check confirms that the sensitivity substantially changes membership and support; it does not isolate a person-level effect. The holdout unit also changes, so 9.55 is not a formal lower bound.

Odisha’s corresponding premium is 26.64 points under signature consolidation, 25.61 in completed villages, and 25.42 under exploratory label normalization. The primary recorded-label result uses neither normalization merges nor a rare-label floor.

## Verification

- All 22 pipeline tests and both generated-output reconciliation tests passed: **24 passed**. Tests include exhaustive account-holdout comparison, exact option identities, joint-owner multiplicity, PDF provenance, source repair and parser invalidation, warm/cold census equality, snapshot replay, concurrent rewrite detection, CLI completion, district scoring, normalization and failure cleanup.
- Independent full-output checks verified both manifest hashes, every declared artifact hash, Parquet row counts, exact `(account, slot)` uniqueness, eligibility predicates, and account/village counts. District denominators sum to statewide denominators. Both figures were visually inspected.
- `make ci-docker` passed Black, isort, flake8 and pytest: **162 passed, 26 skipped**. Skips reflect external datasets unavailable inside the standard Python container.
- The broader local `make ci` run passed linting and reported **183 passed, two skipped, one failure** before the last two integration tests were added. The unchanged analysis-03 test `test_removing_titles_changes_what_concentration_means` expects 18 names at 25% coverage; the current data yields 19. Installing the released `instate==3.3.0` reproduced the same mismatch. No assertion was weakened.
- `git diff --check` passed. Unrelated analysis-11 work was preserved.

## Execution and retained evidence

The scorer uses compact integer dictionaries, two DuckDB threads and a 2 GB memory setting. Interrupted attempts exposed excessive wide-table spill and a parameterized-view restriction; both were corrected and regression-tested. Only this pipeline’s disposable database/spill files were cleaned. Immutable inputs, parsed census shards and crawler originals were retained.

Odisha reused all 18,367 previously completed census shards after AST checks established unchanged Odisha extraction and checkpoint-reading logic. The cache-reuse receipt is private at `.local/land-records/census-cache-reuse.json`. The executed two-state command replayed that preserved Odisha snapshot and captured fresh Rajasthan inputs.

Power logs show clamshell sleep from 17:54 PDT until full wake at 18:14:52, with maintenance wakes. The running analysis resumed automatically. Both states finished at 18:27:32 PDT. Free disk space was approximately 12 GB afterward. No crawler or four-hour scheduler configuration was changed. The temporary CI container exited; the shared Docker runtime was left running because another repository still had an active container.

Private completed-run locations and computational manifest hashes:

- **Odisha**: `.local/land-records/runs/odisha/2026-09-13T004033.565706Z`; manifest SHA-256 `20094905d9b9b88fb76d8e0afebf3b272ef7fcf2912878d1c8dd86dab874c255`. Capture interval `2026-09-12T23:20:55.655306+00:00` to `2026-09-12T23:21:26.482006+00:00` (UTC).
- **Rajasthan**: `.local/land-records/runs/rajasthan/2026-09-13T011605.989716Z`; manifest SHA-256 `f130ceb8642bb147c2236794c190873db5c0235fd4367d821b4585b5d10fa39f`. Capture interval `2026-09-13T01:15:58.970722+00:00` to `2026-09-13T01:16:05.986325+00:00` (UTC).

Each run also retains an `output-audit.json` with the independent aggregate checks. No identifiable owner records appear in this report.
