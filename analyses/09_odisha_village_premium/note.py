"""Render analysis 09's note from its outputs."""

from __future__ import annotations

import json
from pathlib import Path

import jati
import pandas as pd

HERE = Path(__file__).resolve().parent
TAB, FIG = HERE / "out/tab", "out/fig"


def main() -> None:
    path = TAB / "summary.json"
    if not path.exists():
        print("skipped: analysis 09 not built")
        return
    s = json.loads(path.read_text())
    g = s["odisha"]["as recorded"]
    gr = s["odisha"]["religion stripped"]
    b = s["bihar"]
    pos = s["surname_position"]
    nrm = s["normalisation"]
    sens = pd.DataFrame(s["sensitivity"])
    floors = pd.DataFrame(s["floors"])
    o_rows = g["households"]
    norm_hh = f"{jati.MIN_JATI_HOUSEHOLDS} or more"
    norm_reach = f"{jati.MIN_JATI_REACH} or more of them"
    districts = s["districts"]
    per = pd.DataFrame(s["by_district"]).sort_values("premium", ascending=False)

    sens_rows = "\n".join(
        f"| {int(r.threshold)} | {int(r.groups)} | {r.surname:.1f} | "
        f"{r.surname_village:.1f} | **{r.premium:.1f}** |"
        for r in sens.itertuples()
    )
    district_rows = "\n".join(
        f"| {r.district} | {int(r.households):,} | {int(r.groups)} | "
        f"{r.surname:.1f} | {r.surname_village:.1f} | **{r.premium:.1f}** |"
        for r in pd.concat([per.head(5), per.tail(5)]).itertuples()
    )
    gaj = per[per["district"].str.contains("ଗଜପତି", na=False)]
    gajapati = gaj.iloc[0] if len(gaj) else None
    gajapati_line = (
        ""
        if gajapati is None
        else (
            f"\nGajapati, the single district this analysis first reported, "
            f"gives {gajapati['premium']:.0f} points scored on its own, against "
            f"the {g['premium']:.0f} pooled across the state. The figure "
            f"published from one district was 20.\n"
        )
    )

    md = f"""# Does the village premium travel outside Bihar?

Bihar's land records support the strongest single result in this repo. Across
141 jatis a surname alone leaves {b['surname']:.0f} mistakes per 100, and a
surname together with a village leaves {b['surname_village']:.0f}. The question
that result raises is whether the {b['premium']:.0f}-point difference describes
surnames and villages in general or describes Bihar.

The Odisha Record of Rights records a jati and a village for every tenant, which
makes the same measurement possible elsewhere. Scored on the same protocol
across **{len(districts)} districts and {s['villages']:,} villages**, a village
adds {g['premium']:.0f} points where in Bihar it adds {b['premium']:.0f}.
Relative to what the surname leaves unresolved, the village closes
{g['premium_share']:.0f}% of the remainder here against
{b['premium_share']:.0f}% in Bihar.

![What a village adds, in Bihar and in Odisha]({FIG}/village_premium.png)

Put on analysis 02's axis the two places cross. Odisha is the easier target at
every size of place except the finest -- {b['surname']:.0f} against
{g['surname']:.0f} with no place at all -- and Bihar overtakes it exactly when
the village arrives. The village does something in Bihar that no larger unit
does; Odisha's gain is spread more evenly across the scales.

![Error rising as the place gets bigger, in both places]({FIG}/atrophy.png)

## What is being compared, and what is not

The two levels are not comparable and the figure is drawn so as not to invite
the comparison. Bihar sorts people among 141 curated jatis; Odisha sorts them
among {g['groups']:,} label strings. A harder target produces more mistakes
whatever the surname does, so the quantity that carries across places is the
distance between the two rungs rather than the height of either.

The surname alone leaves {b['surname']:.1f} mistakes in Bihar and
{g['surname']:.1f} here, which is close but not the same, and nothing follows
from how close it is. They are counting against {b['groups']} groups and
{g['groups']:,}, so similar heights are not evidence that surnames are equally
informative.

{nrm['strings_in']:,} label strings were recorded and {g['groups']:,} are
scored. What qualifies a label is reach rather than size: it has to appear in
more than one village of {s['villages']:,}, and then either carry
{norm_hh} households or be found in {norm_reach}. That removes
{nrm['labels_floored']:,} labels and {nrm['households_floored']:,} tenants,
**{100 * nrm['households_floored'] / (o_rows + nrm['households_floored']):.2f}%
of the record**, and moves the premium by
{floors.iloc[0]['premium'] - g['premium']:+.2f}.

Size alone was the wrong test and the removal list said so. A flat floor of
fifty households cut `ମହିଶ୍ୟ` (47 households across 26 villages), `ଚନ୍ଦ୍ର ବଂଶି`
(48 across 30) and `ପାଟସାଲିଆ` (47 across 23) for missing the round number by a
household or two, which is not a defensible thing to have done to recognised
castes. A label carried across many villages has earned its place whatever its
size, and what the floor now removes is led by `ତିବତିୟାନ` -- Tibetan, 173
households in one village -- `ବିବାହିତା ଶୁଣ୍ଢି`, which is a phrase rather than a
jati, and `ଖଣ୍ଡାୟତ ବା. ନିଜଗାଁ`, which is a residence marker that leaked into the
caste field upstream. Two thirds of what goes sits in a single village.
Of what stays, {nrm['labels_covering_99pct']} labels carry 99% of tenants,
against Bihar's 141 curated jatis.

## The premium is not one number

Pooling districts hides that they disagree. Scored separately, the premium runs
from {per['premium'].min():.0f} to {per['premium'].max():.0f} points across the
{len(per)} districts large enough to score, with a median of
{per['premium'].median():.0f}.

| district | tenants | labels | surname | + village | premium |
|---|---|---|---|---|---|
{district_rows}

*The five districts with the largest premium and the five with the smallest.*
{gajapati_line}
**The pooled premium is larger than every district's.** Pooled it is
{g['premium']:.0f}; the largest single district is {per['premium'].max():.0f}
and the median is {per['premium'].median():.0f}. That is not a paradox and it
is not an error. Naming a village in the pooled problem also names a district
and a region, so the village is carrying geography the district-level scores
have already held fixed. Read the pooled number as what a village is worth to
someone guessing anywhere in Odisha, and the district numbers as what it is
worth to someone who already knows the district. Bihar's {b['premium']:.0f} is
a pooled figure too, so the pooled row is the like-for-like comparison.

## Three choices that could have produced this result, and did not

A result assembled from a scraped record and a normalisation layer invites the
objection that the analyst's choices produced it. Three such choices were varied.

**How readily two spellings are judged one jati.** Spelling proposes a merge
and never decides it: `ଚମାର`/`କମାର`, `ଗଣ୍ଡ`/`ଗଣ୍ଡା` and `ଭୂମିଆ`/`ଭୂମିଜ` are
each one edit apart and each two different jatis. A candidate is confirmed only
when a second signal agrees -- two spellings of one jati are carried by the same
surnames -- and that gate is the choice. Moving it from 0.15 to 0.60 moves the
premium by {sens['premium'].max() - sens['premium'].min():.2f}.

| surname-profile gate | groups | surname | + village | premium |
|---|---|---|---|---|
{sens_rows}

{nrm['households_merged']:,} households were merged and
{nrm['candidates_refused']:,} candidates refused, every one of them published
with both of its scores in `out/tab/jati_merges.csv` and `jati_refused.csv`.

**Whether religion is stripped from the label.** A jati recorded as `ପାଣ` and
one recorded as `ପାଣ ଖ୍ରୀଷ୍ଟିୟାନ` are two prediction targets unless the
religion is removed, and treating religion as a predictor is not something this
repo does. Removing it moves the premium from {g['premium']:.1f} to
{gr['premium']:.1f}. Both are reported because the choice is substantive.

**Which token is taken as the surname.**
{100 * pos['share_sharing_a_token']:.0f}% of tenants share a token with the
father or husband named beside them, and that token is last
{100 * pos['positions']['last']:.0f}% of the time and first
{100 * pos['positions']['first']:.0f}%. The last token is therefore the surname
in Odisha, which is the opposite of Maharashtra (analysis 04) and the reason the
test is run per state rather than assumed.

## Limits

**The scrape is not finished.** It has reached {len(districts)} districts and
{s['villages']:,} villages, a fraction of the state's estimated 25 million
khatiyans. Districts entered the crawl in a deliberate order rather than at
random, so what is scored here is not a random sample of Odisha, and the
per-district table is the honest way to read it.

**A finished village is a census; a village in progress is not.** The fetch no
longer caps khatiyans per village, so a completed village is enumerated rather
than sampled: a median of
{s['sampling']['khatiyans_per_village_median']:.0f} khatiyans per village across
{s['sampling']['villages']:,} villages, against a median of 35 when this
analysis first ran, with a maximum of
{s['sampling']['khatiyans_per_village_max']:,}. Villages the crawl is still
working through remain partial, and a partial village is a weaker cue than a
complete one, so the premium is still biased **downward** and the gap to Bihar
remains an upper bound.

**The floor is a claim, not a cleanup.** It is swept in `out/tab/floors.csv`
alongside the merge gate, and across every setting tried -- no floor at all
through to ten villages -- the premium sits between
{floors['premium'].min():.2f} and {floors['premium'].max():.2f}. Cutting the
group count from {nrm['strings_in']:,} to {g['groups']:,} does not move the
answer, which is the reason it is safe to do and the reason it is reported
rather than applied quietly.

**Most label strings still cannot be checked.** A merge is confirmed by
comparing surname profiles, and below about 25 households that comparison stops
discriminating: subsampling a known-same pair to ten rows gives scores as low as
0.16, and a known-different pair reaches 0.21. So
{nrm['candidates_refused']:,} candidates are refused, and all but 187 of those
are refused for being too rare to check rather than for failing the check.
{nrm['strings_in']:,} label strings become {nrm['strings_out']:,}. Those rare
labels carry a quarter of one percent of tenants between them, so they cost
almost nothing in the scoring, but they are the reason the group count stays in
the thousands. A fuller layer is being built in `upnaam` and will replace this
one.

---

*Odisha Record of Rights collected in
[odisha-ror](https://github.com/in-rolls/ror_odisha_2026). Bihar rungs from analysis
02.*
"""
    out = HERE / "note.md"
    out.write_text(md)
    print(f"wrote {out} ({len(md.splitlines())} lines)")


if __name__ == "__main__":
    main()
