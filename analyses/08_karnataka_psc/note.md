# What a surname reveals about caste in Karnataka

Karnataka is absent from the census extract this repo runs on. outkast covers
nineteen states and Karnataka is not among them; in the south it holds only
Kerala and Tamil Nadu. The Public Service Commission select lists are therefore
the only caste-linked name data available for the state, and they can be asked
the repo's own question.

They come with two conditions that shape everything below. The candidates are
people who applied for and obtained state government jobs, so nothing here
describes Karnataka's population. And the category is one the candidate declared
in order to claim a quota, not caste as an observer would record it.

## Recovering the surname

The last token is a single letter **34% of the time**.
The six commonest are

`S` (2,601), `R` (1,794), `K` (1,741), `N` (1,682), `B` (1,156), `C` (994)

and dropping single letters gives a different list entirely:

`Kumar` (1,079), `Patil` (607), `Naik` (523), `Manjunatha` (375), `Biradar` (230), `Rathod` (177)

Two inventories of "Karnataka's commonest surnames" from the same 48,395
names. Analysis 04 found Maharashtra failing the last-token
assumption by writing the surname first; this is the same assumption failing by
abbreviation. Everything below uses the cleaned surname, which is the last token
longer than one character.

![What a last-token rule calls a surname](out/fig/naive_vs_clean.png)

## The surname works for one category and largely fails the rest

| category | share of candidates | wrong knowing nothing | wrong with the surname |
|---|---|---|---|
| General | 48% | 0 | **17** |
| OBC | 30% | 100 | **58** |
| Scheduled Caste | 18% | 100 | **62** |
| Scheduled Tribe | 4% | 100 | **74** |

The guess is wrong about 62 of every 100 Scheduled Caste candidates and
17 of every 100 General ones, an error **3.6 times
larger** for the group the quota exists for. Analysis 05 found the same direction
nationally, from SECC and the electoral rolls, sorting people into three census
categories. This is a different state, a different source and a different set of
labels, and it points the same way.

![What the guess gets wrong, by the candidate's own category](out/fig/by_category.png)

Overall the surname takes the error from 52.5 mistakes per 100 to
40.0, closing **24% of the
gap**. Among the states in analysis 07 that would sit between Tamil Nadu at 9%
and Uttarakhand at 28%, and far below Bihar at 61%. The comparison is
suggestive and not like-for-like: four quota categories are not three census
categories, and job applicants are not a population.

## Two smaller results

**Cleaning the initials out buys 2.0 mistakes
per hundred**, from 41.9 to
40.0. An earlier version of this note reported that
difference as slightly negative, on 14,854 candidates. At 48,395 the sign
is stable and the other way round, so the earlier reading was underpowered.

**The PIN code is worth almost nothing**, 51.3 against
a blind 52.5. Geography does the opposite in Bihar, where a village takes
47 mistakes down to 17. Whether that is a fact about Karnataka or about a
recruitment list drawn from across the state, this data cannot say.

## How the numbers are computed

Every figure is leave-one-out: a candidate's own record is excluded from the
table used to score them. Most surnames here appear once or twice, so a plug-in
score would report memorization. A cue is used when at least one *other*
candidate shares it, which is the rule analysis 09 uses; requiring two instead
moves the headline from 40.0 to 43.9.

Karnataka's backward-class codes are collapsed into one OBC bucket, which folds
in 2B, a religion-defined category this repo does not report separately.

---

*Karnataka PSC select lists, collected in
[pranaam](https://github.com/appeler/pranaam).*
