# Literature

Sources for the "What others have found" section of the front-page README. It
follows `quota_representation/lit`: local PDFs in `papers/` (ignored by Git),
with source URL, version and SHA-256 in `papers.csv`. It is a targeted list,
not a systematic review.

Each entry says how it was checked. **Read** means the passage was found in the
local PDF at the page given. **Secondary** means the work exists and its
bibliographic details were confirmed, but the number comes from another source
or an abstract.

## The "85% of surnames" claim

A circulating sentence reads: "85% of surnames do not convey caste signals in
urban-educated settings … (Mamidi, 2011; Jodhka, 2015; Wiltshire, 2020)." That
is a merge of two sentences in Shukla (2025), and the merge changes what is
being claimed.

Shukla, printed p. 3 (PDF p. 4), **read**:

> While some surnames indicate caste, most do not convey caste signals in
> urban-educated settings (e.g., elite colleges typically located in urban
> centers) due to migration and geographical variation in naming conventions
> (Mamidi, 2011; Jodhka, 2015; Wiltshire, 2020). Among the 15% of students in my
> sample with distinctly caste-identifiable surnames, penalties emerge
> immediately at the first screening round (application reading). For the
> remaining 85% with caste-ambiguous surnames, no early penalty appears …

- The cited works support "most", not a number. Mamidi (2011) is an Oxford
  DPhil on caste signalling and passing in lab games. Jodhka (2015) is a
  sociology monograph. Wiltshire (2020) is a phonetics book on the Indian
  English accent; Shukla's own appendix F cites it for accent. Neither of the
  first two could be read in full here; no copy of either contains an 85% figure
  that we could find, and Vaishnav (2017, p. 751) reports Mamidi's numbers as
  74% and 34% detection rates, not a surname share.
- The 85% is the share of **students at one elite college** whose surname did
  not appear on a list: the state SC/ST schedules, the Anthropological Survey's
  *People of India* volumes, or state gazettes (§4.6.1, printed p. 21). The
  appendix sample sizes agree: 619 identifiable against 3,386 not (Tables OA.7
  and OA.8), 15.5%.
- The paper does not say who coded the names, how a surname listed under
  several castes was handled, or how often the list's caste agreed with the
  student's own recorded category.
- §4.6.1 cites Jodhka (2015) and Parmar (2020) instead, and footnote 9 gives the
  only external number: Bhupatiraju et al. (2024) find caste-neutral surnames
  for 49% of petitioners, 56% of respondents and 50% of judges in Patna High
  Court cases.

So "85%" is a coding outcome for one sample under one list, not a measured
property of Indian surnames. The hosted PDF is older than the abstract on the
author's site, so page numbers may differ in the current draft.

## Studies that code caste from names

| key | what it does with names | number | check |
|---|---|---|---|
| `fisman2017cultural` | Maps borrower and officer surnames to varna for a large Indian bank | Varna assigned for about 17% of borrowers and 40% of officers; all of them General; "within a region there is usually only a single Varna associated with each surname" (DP pp. 14–15) | Read |
| `ash2025ingroup` | Classifies 5M criminal-case names by gender and religion | "We have not managed to develop a reliable correspondence between names and caste" (2021 WP, p. 22); caste in-group is proxied by a shared last name | Read |
| Bhupatiraju et al. (2024), EJELS 1(2): 151–178 | Infers caste from surnames in Patna High Court cases | 49% / 56% / 50% caste-neutral surnames (petitioners / respondents / judges) | Secondary, via Shukla fn. 9; PDF behind a bot wall |
| `shukla2025making` | Codes students' surnames against published caste lists | 15% identifiable | Read |
| `vahini2022decoding` | Trains name classifiers on AIEEE applicants, General vs reserved | 72.6% accuracy from the name, 74.7% with state (Table 1); scored on unique name strings, not people | Read |
| `dasanaike2026llm_v1` | Zero-shot LLM, four categories, 75 people per class | Bihar land records 74%, Rajasthan sarpanch 57%; uses this repo's data; **v1 withdrawn** | Read; do not cite as current |

## Audit studies that assume the name is read

| key | names used | what it implies here | check |
|---|---|---|---|
| `siddique2011evidence` | Distinctively high- and low-caste Tamil names, Chennai | The site behind most observations let applicants declare caste (IZA p. 12), so the signal was not the name alone | Read |
| `datta2016phone` | Gupta / Sharma, Yadav / Ahir, Paswan / Manjhi, Khan / Ahmed, Delhi rentals | Small SC penalty; landlords "may not have been as certain about the caste identity of the SC names" (p. 20) | Read |
| Thorat & Attewell (2007), EPW 42(41) | Dalit, Muslim, high-caste Hindu names | The founding correspondence study | Secondary |
| Banerjee, Bertrand, Datta & Mullainathan (2009), JCE 37(1) | Field-tested caste surnames, Delhi | Gap in call-centre jobs, none in software | Secondary; MIT DSpace rate-limited |

## Context

- `vaishnav2017ethnic`: Bihar voters with full local knowledge misidentify the
  winning candidate's jati 29% of the time but get the broad group right about
  90% of the time (pp. 749, 751).
- `clark2013caste`: majority-SC surnames in Kolkata already proportionally
  represented among pre-Independence physicians; a majority-SC surname is a
  probabilistic label.
- Parmar (2020), *Contemporary Voice of Dalit* 12(2): urban Dalits changing
  surnames to pass. Paywalled; abstract only.
