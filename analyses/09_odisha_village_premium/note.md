# Does the village premium travel outside Bihar?

Bihar's land records support the strongest single result in this repo. Across
141 jatis a surname alone leaves 47 mistakes per 100, and a
surname together with a village leaves 17. The question
that result raises is whether the 30-point difference describes
surnames and villages in general or describes Bihar.

The Odisha Record of Rights records a jati and a village for every tenant, which
makes the same measurement possible elsewhere. Scored on the same protocol
across **30 districts and 10,604 villages**, a village
adds 24 points where in Bihar it adds 30.
Relative to what the surname leaves unresolved, the village closes
55% of the remainder here against
64% in Bihar.

![What a village adds, in Bihar and in Odisha](out/fig/village_premium.png)

Put on analysis 02's axis the two places cross. Odisha is the easier target at
every size of place except the finest -- 47 against
44 with no place at all -- and Bihar overtakes it exactly when
the village arrives. The village does something in Bihar that no larger unit
does; Odisha's gain is spread more evenly across the scales.

![Error rising as the place gets bigger, in both places](out/fig/atrophy.png)

## What is being compared, and what is not

The two levels are not comparable and the figure is drawn so as not to invite
the comparison. Bihar sorts people among 141 curated jatis; Odisha sorts them
among 1,397 label strings. A harder target produces more mistakes
whatever the surname does, so the quantity that carries across places is the
distance between the two rungs rather than the height of either.

The surname alone leaves 47.3 mistakes in Bihar and
44.0 here, which is close but not the same, and nothing follows
from how close it is. They are counting against 141 groups and
1,397, so similar heights are not evidence that surnames are equally
informative.

6,507 label strings were recorded and 1,397 are
scored. What qualifies a label is reach rather than size: it has to appear in
more than one village of 10,604, and then either carry
50 or more households or be found in 5 or more of them. That removes
4,359 labels and 16,894 tenants,
**0.35%
of the record**, and moves the premium by
-0.05.

Size alone was the wrong test and the removal list said so. A flat floor of
fifty households cut `ମହିଶ୍ୟ` (47 households across 26 villages), `ଚନ୍ଦ୍ର ବଂଶି`
(48 across 30) and `ପାଟସାଲିଆ` (47 across 23) for missing the round number by a
household or two, which is not a defensible thing to have done to recognised
castes. A label carried across many villages has earned its place whatever its
size, and what the floor now removes is led by `ତିବତିୟାନ` -- Tibetan, 173
households in one village -- `ବିବାହିତା ଶୁଣ୍ଢି`, which is a phrase rather than a
jati, and `ଖଣ୍ଡାୟତ ବା. ନିଜଗାଁ`, which is a residence marker that leaked into the
caste field upstream. Two thirds of what goes sits in a single village.
Of what stays, 387 labels carry 99% of tenants,
against Bihar's 141 curated jatis.

## The premium is not one number

Pooling districts hides that they disagree. Scored separately, the premium runs
from 2 to 23 points across the
30 districts large enough to score, with a median of
11.

| district | tenants | labels | surname | + village | premium |
|---|---|---|---|---|---|
| ବୌଦ୍ଧ | 84,955 | 170 | 43.7 | 20.9 | **22.8** |
| ଗଂଜାମ | 72,800 | 143 | 32.7 | 14.7 | **18.0** |
| ଗଜପତି | 410,207 | 503 | 47.8 | 32.0 | **15.9** |
| କେନ୍ଦୁଝର | 77,168 | 142 | 31.9 | 16.3 | **15.6** |
| ନୟାଗଡ଼ | 34,829 | 112 | 33.4 | 17.8 | **15.5** |
| ନୂଆପଡ଼ା | 80,403 | 188 | 11.1 | 7.3 | **3.8** |
| ମୟୂରଭଞ୍ଜ | 44,668 | 167 | 14.5 | 10.8 | **3.6** |
| ନବରଂଗପୁର | 56,033 | 130 | 9.1 | 6.5 | **2.6** |
| ଦେବଗଡ଼ | 11,937 | 128 | 29.1 | 26.6 | **2.4** |
| ପୁରୀ | 15,329 | 37 | 11.2 | 9.0 | **2.2** |

*The five districts with the largest premium and the five with the smallest.*

Gajapati, the single district this analysis first reported, gives 16 points scored on its own, against the 24 pooled across the state. The figure published from one district was 20.

**The pooled premium is larger than every district's.** Pooled it is
24; the largest single district is 23
and the median is 11. That is not a paradox and it
is not an error. Naming a village in the pooled problem also names a district
and a region, so the village is carrying geography the district-level scores
have already held fixed. Read the pooled number as what a village is worth to
someone guessing anywhere in Odisha, and the district numbers as what it is
worth to someone who already knows the district. Bihar's 30 is
a pooled figure too, so the pooled row is the like-for-like comparison.

## Three choices that could have produced this result, and did not

A result assembled from a scraped record and a normalisation layer invites the
objection that the analyst's choices produced it. Three such choices were varied.

**How readily two spellings are judged one jati.** Spelling proposes a merge
and never decides it: `ଚମାର`/`କମାର`, `ଗଣ୍ଡ`/`ଗଣ୍ଡା` and `ଭୂମିଆ`/`ଭୂମିଜ` are
each one edit apart and each two different jatis. A candidate is confirmed only
when a second signal agrees -- two spellings of one jati are carried by the same
surnames -- and that gate is the choice. Moving it from 0.15 to 0.60 moves the
premium by 0.13.

| surname-profile gate | groups | surname | + village | premium |
|---|---|---|---|---|
| 0 | 1366 | 44.0 | 19.9 | **24.1** |
| 0 | 1397 | 44.0 | 19.9 | **24.1** |
| 0 | 1439 | 44.3 | 20.1 | **24.2** |
| 0 | 1523 | 44.5 | 20.3 | **24.2** |

414,803 households were merged and
4,661 candidates refused, every one of them published
with both of its scores in `out/tab/jati_merges.csv` and `jati_refused.csv`.

**Whether religion is stripped from the label.** A jati recorded as `ପାଣ` and
one recorded as `ପାଣ ଖ୍ରୀଷ୍ଟିୟାନ` are two prediction targets unless the
religion is removed, and treating religion as a predictor is not something this
repo does. Removing it moves the premium from 24.1 to
23.3. Both are reported because the choice is substantive.

**Which token is taken as the surname.**
90% of tenants share a token with the
father or husband named beside them, and that token is last
92% of the time and first
6%. The last token is therefore the surname
in Odisha, which is the opposite of Maharashtra (analysis 04) and the reason the
test is run per state rather than assumed.

## Limits

**The scrape is not finished.** It has reached 30 districts and
10,604 villages, a fraction of the state's estimated 25 million
khatiyans. Districts entered the crawl in a deliberate order rather than at
random, so what is scored here is not a random sample of Odisha, and the
per-district table is the honest way to read it.

**A finished village is a census; a village in progress is not.** The fetch no
longer caps khatiyans per village, so a completed village is enumerated rather
than sampled: a median of
98 khatiyans per village across
10,609 villages, against a median of 35 when this
analysis first ran, with a maximum of
4,424. Villages the crawl is still
working through remain partial, and a partial village is a weaker cue than a
complete one, so the premium is still biased **downward** and the gap to Bihar
remains an upper bound.

**The floor is a claim, not a cleanup.** It is swept in `out/tab/floors.csv`
alongside the merge gate, and across every setting tried -- no floor at all
through to ten villages -- the premium sits between
24.04 and 24.11. Cutting the
group count from 6,507 to 1,397 does not move the
answer, which is the reason it is safe to do and the reason it is reported
rather than applied quietly.

**Most label strings still cannot be checked.** A merge is confirmed by
comparing surname profiles, and below about 25 households that comparison stops
discriminating: subsampling a known-same pair to ten rows gives scores as low as
0.16, and a known-different pair reaches 0.21. So
4,661 candidates are refused, and all but 187 of those
are refused for being too rare to check rather than for failing the check.
6,507 label strings become 1,397. Those rare
labels carry a quarter of one percent of tenants between them, so they cost
almost nothing in the scoring, but they are the reason the group count stays in
the thousands. A fuller layer is being built in `upnaam` and will replace this
one.

---

*Odisha Record of Rights collected in
[ror_odisha_2026](https://github.com/in-rolls/ror_odisha_2026). Bihar rungs from analysis
02.*
