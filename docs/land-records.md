# Land-record village premium

Run from `caste-name-information` after `uv venv .venv` and
`uv pip install --python .venv/bin/python -e '.[dev]'`:

```sh
make land-premium
make a09
make a12
```

The first command refreshes Odisha and Rajasthan; the other two refresh one state.
Inputs are the `in-rolls/ror_odisha_2026` and `in-rolls/ror_rajasthan_2026` checkouts
under `GITHUB_DIR` (default `~/Documents/GitHub`). No network requests, crawler restarts,
source writes, or scheduler changes are part of a refresh.

## Ownership and data flow

The shared package is `src/last_name_basis/land_records/`:

| Module | Responsibility |
|---|---|
| `storage.py` | Fixed byte-prefix capture, immutable content-addressed objects, complete-line reading |
| `adapters.py` | Source parser imports, exact identities, geography, PDF provenance, account lists |
| `quality.py` | Attempt dispositions and exact unresolved source keys, independently cached from owner parsing |
| `pipeline.py` | Census reconciliation, consolidation, eligibility, sensitivities, run orchestration |
| `scoring.py` | The same account-held-out modal scorer for both states |
| `report.py` | Aggregate tables, figure and result-driven narrative |
| `__main__.py` | Command entry point |

Analysis 09 and analysis 12 contain thin entry points and generated aggregate
reports. Analysis 11 remains the separate Rajasthan election-candidate analysis.
Odisha's `jati.py` is retained only for the exploratory normalization sensitivity;
it does not define the primary target or Rajasthan labels.

## Snapshots and refreshes

On this workstation, `.local/land-records` links to
`/Volumes/Staging/land-records/last-name-basis/land-records`. Both neighboring
crawler `raw` directories also link into that volume. Keep Staging mounted during
refreshes. Existing commands and manifest paths remain valid; the migration
preserved all snapshots, caches, source backups and hardlinks, with SHA-256
verification receipts under `/Volumes/Staging/land-records/`.

Each refresh inventories all current checkpoint files and captures their observed
byte lengths. Capture spans an interval, not an instantaneous statewide cutoff.
Appending writers may leave unfinished gzip streams. The reader retains complete
JSON lines, reports incomplete endings, and distinguishes files observed open
from endings whose activity could not be established. It never repairs raw data.
Malformed closed files and provenance failures are reported, not silently called
portal misses. These issues prevent affected units from being called complete.

`.local/land-records/objects/` preserves input bytes by SHA-256, including parsers,
frames, completion sidecars, approved PDF aliases, referenced PDFs and health
context. Unchanged objects are shared between runs. Parsed Parquet shards live in
`cache/`; changed, repaired or removed inputs cannot persist through a current
inventory. Parser/dependency changes invalidate their caches. PDF dependencies
are checked even when a checkpoint file is unchanged.

Every run has a private directory under `.local/land-records/runs/<state>/` with
its input and completed manifests, consolidated owners, eligible entries,
aggregate results and report. `.local/` is ignored by Git. Inputs and sparse
name/label mappings are private, including the normalization merge ledger.
No automatic deletion policy removes snapshots or crawler backups.

```sh
.venv/bin/python -m last_name_basis.land_records --snapshot /absolute/path/to/manifest.json
.venv/bin/python -m last_name_basis.land_records --snapshot /absolute/path/to/manifest.json --rebuild
```

Use a completed `manifest.json`, retaining its content-addressed objects. The
second command reparses instead of using cached shards. A refresh lock permits
one analysis writer at a time. Requested states finish before latest outputs are
selected; partial run directories remain available for diagnosis. The
`latest.json` pointer identifies completed runs; reports are replaceable exports.
DuckDB uses two threads, a 2 GB memory setting and disk spill. Input parsing works
one checkpoint at a time. Inspect available disk space before retaining many runs.

## Dictionary and join contract

Canonical owner rows are strings except the Boolean `complete` field:

| Field | Meaning |
|---|---|
| `district`, `village` | Source district code and a JSON-encoded composite geographic identity |
| `account` | Composite village/account identity; Odisha retains exact untrimmed option value |
| `source_unit` | Relative checkpoint path within the source checkout |
| `list_hash`, `slot` | Order-independent owner-list fingerprint and within-list occurrence slot |
| `name`, `relative`, `relation`, `residence` | Parsed owner fields, with NFC/whitespace cleanup |
| `jati` | Recorded caste label; no primary merge, category assignment, rare-label floor or gloss removal |
| `surname` | Final nonempty name token, explicitly a proxy |
| `signature` | Village, name, relative, relation and residence; possible identity, not a person ID |
| `format` | `html` or `pdf` for Odisha; `json_info` for Rajasthan’s map API text |
| `complete` | Captured source-unit completion flag; use the separately checked complete-village subset for analysis |

`owners.parquet` follows `SCHEMA.json`. `eligible.parquet` adds `weight`, a
DOUBLE fixed at 1 for each retained owner entry. Aggregate score denominators
therefore count owner entries, including repeated co-owner slots.

Odisha joins district/tahsil/village to its frame and keys accounts by the actual
option value, never its printed label. Repeated successful keys must agree.
Rajasthan joins `giscode` to its sheet frame, checks embedded plot identity and
resolves references within that sheet. The village composite includes district,
tehsil, RI, halka and village. Account owner lists repeat over plots: consolidate
identical lists within village/khata, retaining repeated co-owner slots. Conflicting
lists are excluded and counted. Do not merge owners across unrelated accounts in
the primary data. Missing account identities remain unresolved.

The eligible subset requires a nonempty name and caste containing a letter or
number. All other consolidated entries remain in the private owners table and
census denominators. Government/institutional entries are not assumed to be people;
ones without caste are excluded by the same missing-target rule. Missingness,
invalid source records and geographical selection can affect interpretation.

### Count scopes

Source counters are accumulated across checkpoint files. In particular,
`unique_saved_accounts` counts distinct account keys within each source file;
in Rajasthan the same village/account may appear in multiple sheets. It is
not the statewide number of distinct accounts or people. `primary.accounts`
counts distinct eligible composite accounts after consolidation, and
`repeated_account_entries_removed` records cross-sheet list repetition.
Likewise, inferred plot links are saved plot coverage, not additional owners.

## Estimand and evaluation

The motivating question concerns people represented in land records. Observable
primary results weight recorded owner entries equally after removing repeated
account-list expansions. They do not estimate population or household error.
Joint ownership stays visible. A matching-signature sensitivity collapses exact
within-village identity-field matches where a relative is present, excluding
conflicting caste labels. It can conflate homonyms and miss repeated people; its
holdout changes to the signature and it is not a formal error bound.

Predict the modal recorded label with no cue, surname, village, or surname plus
village, excluding the entire target account each time. Empty local training
cells fall back to the global distribution after the same exclusion. Lexical ties
are deterministic; no training observations means unsupported. Report denominators
and fallbacks. Village premium is surname error minus surname-plus-village error;
the relative premium divides that difference by surname error. Negative premiums
are possible under held-out evaluation and are never test failures.

Compute pooled, district-specific and confirmed-complete-village results. Odisha
completion requires exact-option sidecars agreeing with the captured account
count. Rajasthan completion requires every enumerated sheet of a village to have
clean completion evidence. Capture completion is not verified owner extraction.
Relative-name token agreement is reported as a conditional surname-proxy diagnostic.
Bihar's existing results remain context, because labels, units and protocols differ.

## Validation

`make ci` runs pytest, Black, isort and flake8; `make ci-docker` repeats the suite
in the repository's standard Python image. Tests compare the scorer with exhaustive
account holdout, exercise source identities and exclusions, and check snapshot
replay and changed-input behavior. Generated-result tests check arithmetic and
reconciliation, not a preferred ordering of states or monotonically improving cues.

The disk-backed ingestion uses [DuckDB's Parquet reader](https://duckdb.org/docs/stable/data/parquet/overview)
and [configuration controls](https://duckdb.org/docs/current/configuration/overview).

The [initial validation report](land-records-validation.md) records the first full
production runs, their checks and the material Rajasthan signature sensitivity.

## Whole-name and spacing checks

Every refresh also runs `name_representation_sensitivity` in the shared
`pipeline.py`, using the same scorer in `scoring.py`. It compares the entire
recorded name with the same string after removing spaces. Both preserve the
eligible entries, caste labels, account holdout and weights. The generated note
places them beside the final-token benchmark. Removing spaces can align spellings
such as `रामलाल` and `राम लाल`; it is a prediction-key sensitivity, not surname
extraction or owner deduplication. Original names remain in the canonical data.
No dictionary, inferred caste label or guessed word boundary enters this check.
