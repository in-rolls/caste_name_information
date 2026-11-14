# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.1.0] - 2026-11-13

### Added

- **Analysis 11, the OBC / General line, from Rajasthan's panchayat
  candidates.** SECC records Scheduled Caste, Scheduled Tribe or neither, so no
  analysis built on it can separate OBC from General. Rajasthan's State Election
  Commission publishes the category each of 206,673 candidates declared to
  stand. Re-weighted to the state's shares and scored on districts the guesser
  has never seen, knowing nothing leaves 50 mistakes per 100 and the last name
  39. The surname ranks an OBC above a General candidate 76 times in 100, about
  as well as it ranks a Dalit above a non-Dalit there, 72. Of 93 surnames that
  are at least 90% one category, 63 are the name of a jati and 23 the clan of
  one. The 2020–22 sarpanch records also give a father's or husband's name, and
  adding the relative's surname saves 3 mistakes per 100. The OBC/General split
  used for re-weighting, 50:19, is an assumption, since no census records it.
- **Analysis 12, the village premium in Rajasthan's land records**, and
  analysis 09 rebuilt on the same pipeline (see Changed). On the September 12
  snapshot the village takes the error from 60.9 to 40.6 per 100. It needs more
  caution than Odisha: the premium falls to 9.6 points when repeated owner
  identities are consolidated on matching signatures, and 84.5% of eligible
  entries have no space in the recorded name, so the "surname" is often the
  whole name. It measures name plus village, not a family-surname effect.
- **What others have found.** A front-page section and `lit/` set the repo's
  figures beside the published ones: Fisman et al., Ash et al., Bhupatiraju et
  al., and Shukla's elite-college list count. The widely repeated "85% of
  surnames do not convey caste" traces to Shukla's §4.6.1, where it is the
  share of one college's students whose surname appears on no SC/ST schedule,
  People of India volume or state gazette. That is a list-coverage count, not a
  measure of what a surname signals. `lit/papers.csv` records where each PDF
  came from and its SHA-256; the PDFs themselves are not committed.
- **Analysis 10, Kerala, where the question often has no object.** 1.4M PSC
  select lists, the largest caste-linked name file here. 78% of last tokens are
  a single letter and only 27% of candidates have a written surname: a name is a
  given name plus initials standing for a father and a house. Scoring Scheduled
  Caste against the other caste categories, the last token ranks a Dalit's
  higher 59 times in 100, a written surname 70, and the given name 69. The
  informative part of a Kerala name is the part no surname method reads, which
  is a stronger version of analyses 04 and 08: there a last-token rule reads the
  wrong token, here it reads a letter because there is no other token.

  The Muslim and Christian buckets are set aside, since Kerala reserves for both
  and scoring them would make religion a predictor. Blanks are dropped as
  missing at random by instruction, and the note records that the label pattern
  contradicts it: `MENON` and `NAMBOOTHIRI` appear zero times because a forward
  caste has no reservation to claim, so dropping blanks removes the most
  distinctive non-Dalit names and pushes every figure down. They are a floor.

- **A mechanism for the weakest state in analysis 07, from upnaam's Punjab
  roll.** Punjab ranks 0.55 against a floor of 0.50 and the analysis did not say
  why. The roll does: `singh` at 38% and `kaur` at 26% cover 64% of the state,
  nearer 71% once `kanr`, which is Kaur misspelled, is counted with it. Neither
  is a family name, so a state where two names that were never lineage markers
  cover two thirds of the population cannot have surnames that identify caste.
  That connects the weakest state to the sex-marking names of analysis 03, which
  were unconnected before.
- **The first cross-source check in the repo.** Every concentration figure came
  from instate. upnaam's resolved rolls give a second read from a different
  collection: Bihar agrees at 5 names against 4 and 65% against 67%, Punjab at 2
  against 2 and 85% against 88%. Rajasthan disagrees twentyfold, and the reason
  is known, since the resolver abstains on two thirds of that state, so the roll
  describes a selected third. Maharashtra cannot be compared, because analysis
  04 found it writes the surname first and analysis 03 withdrew it. Tests hold
  all three outcomes, including the disagreement.
- **Punjab in analysis 05's sex split**, the one resolved state it was not
  using and the most sex-marked naming system in the country. Women's names cost
  0.6 more mistakes per hundred than men's there. Four states now, still no
  consistent direction, and Punjab's estimate rests on 19% of the state.

- **Analysis 07, where a surname works and where it does not.** The national
  figure hides a spread from 67% of the gap closed in Assam to 0% in Haryana.
  What carries a state is one or two large decisive names, not many of them:
  Punjab has five majority-Dalit surnames among its 25 commonest and closes 3%,
  Assam has two and closes 67%, because one of them is `das`. Each state's
  coverage is printed beside its result, and the ordering survives cutting every
  state to its 25 commonest names.
- **Analysis 08, what a surname reveals about caste in Karnataka.** Karnataka is
  absent from SECC, so the Public Service Commission select lists are the only
  caste-linked name data the project has for the state. Recovering a surname
  takes a step first, because the last token is a single letter 34% of the time.
  The guess is then wrong about 62 of every 100 Scheduled Caste candidates and
  17 of every 100 General ones, which is analysis 05's national finding
  reproduced on a different state, source and label set.

- The front page now shows the skew. Sorted by frequency, the ten commonest
  surnames in India cover 32% of everybody and not one of them moves the guess
  off the base rate, while the 2,930 names ranked 1001 and below cover 6% of
  people and 625 of them do. The figure pairing frequency against Dalit share
  was already built and was not linked from the README.

### Changed

- **Analysis 09 rebuilt on a shared land-record pipeline, and scored on all
  of Odisha's saved records rather than one district.** Odisha and Rajasthan now
  go through one package, `last_name_basis.land_records`: it snapshots the
  crawler checkpoints, reconciles them against what the crawl attempted,
  consolidates owner lists repeated across plots, and holds out whole accounts
  when scoring. Across 12.16 million eligible owner entries the village takes
  the error from 50.6 to 25.6 per 100, a premium of 25.0 points, and the
  completed-village, matching-signature and label-normalisation checks keep it
  at 25–27. The target is now the recorded caste label as written, with no
  spelling merges or rare-label floor, so the old note's Gajapati figures and
  its comparison of Odisha's and Bihar's ladders are gone. Both notes are
  generated from the September 12 snapshot and need the local crawler data to
  rebuild.
- **The roll-weighted figures move with instate's revised rolls.** instate
  3.3 to 3.6, released in September, recovered missing rolls, among them Jammu
  and Kashmir, Gujarat and Andhra Pradesh, which changes how common each
  surname is. Rebuilt
  against it, the national guess goes from 25 mistakes per 100 to 19 with the
  surname (was 20), the Dalit ranks higher 81 times in 100 (was 80), the table
  covers 58% of names on the roll (was 59), and 19 names cover a quarter of
  India (was 18; 100 counting only names a brother and sister share, was 103).
  Figures weighted by SECC rather than by the rolls, including analysis 05's 66
  and 4 per 100, do not change.
- **Name concentration is the mechanism, not an artifact, and the first attempt
  at saying so was wrong too.** The repo had been writing about sex-marking and
  universal names as measurement problems: analysis 03 said counting them makes
  Indian naming "look far more concentrated than it is", which implies the real
  figure is the one with them removed. Devi, Singh and Kaur are the names people
  write on forms. Their spread is a process that removed caste information, not
  noise hiding it.

  The correction to that was also too simple. Concentration alone does not
  predict which states have weak surnames: Bihar's dominant names touch 78% of
  its pairs and Bihar ranks 0.96, while Punjab's touch 93% and Punjab ranks
  0.55. What separates them is whether the dominant names sit where the state
  sits. Removing Kerala's `nair` and `pillai`, which are 0.00 Dalit against a
  state of 0.08, makes the guess *worse*; removing Punjab's `singh` makes it
  better.

  Stated without an index: `singh` is 9% of Bihar's extract and almost never
  Dalit there against a state that is 18% Dalit, and 73% of Punjab's with a
  Dalit share of 0.38 against a state of 0.38. Across ten states the correlation
  between a name's coverage and its distance from the state is -0.51. A name
  that spreads to everyone stops distinguishing anyone. Uttarakhand does not fit
  and is named as not fitting.

  This is a decomposition and not an identified mediation, which the note says.

- **The headline measure was accuracy against the largest category, which the
  base rate inflates.** A rule naming the majority is right 70 times in 100 in a
  population that is 70% one group, whatever surnames reveal, so "wrong 25 times
  knowing nothing, 20 with the surname" was largely a statement about how many
  Indians are not Dalit.

  Measured by ranking instead: take one Dalit and one non-Dalit at random and
  order the pair by what their surnames say, and the Dalit ranks higher 80 times
  in 100 on roll weights, 86 on SECC weights, against 50 for a surname carrying
  nothing. Adivasi against everyone else is 91. So a surname is far from silent,
  and the repo had been saying it reveals little.

  Both figures are right and the gap between them is the finding. A surname
  moves the odds a great deal and rarely moves the decision, because only 19% of
  people are Dalit and raising the odds still usually leaves them under a half.
  That is also why the errors fall where they do: the rule almost never answers
  "Dalit", so it misses 66 of every 100 Dalits while getting 96 of every 100
  other people right. The differential in claim 4 is claim 1 seen from the other
  side.

- **The same defect changed a conclusion in analysis 07.** It grouped Kerala,
  Uttar Pradesh, Punjab and Haryana together at the bottom on gap-closed. On the
  ranking measure Kerala is 0.85, level with Maharashtra's 0.86, while Punjab is
  0.55 and Haryana 0.59 against a floor of 0.50. Kerala's surnames separate
  Dalit from non-Dalit perfectly well and seldom change the answer, because only
  8% of its extract is Scheduled Caste. Punjab's and Haryana's genuinely carry
  little. The old column could not tell those apart, and the note's blanket
  refusal to compare Kerala against Punjab is replaced by the measure that makes
  the comparison possible.

- **The README is organised by claim rather than by analysis.** It had nine
  sections, one per analysis, numbered in the order the analyses were built,
  which is a table of contents and not an argument. The structure also could not
  hold: analysis 08 is both a measurement result and a differential result, and
  analysis 06 is both a place result and the ceiling, so a section per analysis
  had to repeat them or split them arbitrarily. Karnataka in particular read as
  a stray section because it was the eighth thing built.

  Five claims now carry it: a surname reveals little and the average overstates
  it; "last name" is not one thing across India; the place carries what the name
  does not; the failure is not spread evenly; the exposure is in the linkage.
  Each cites the analyses behind it, and an index table keeps the repository
  navigable. The section formerly called "Reading the results" is gone, since it
  existed only to state the argument after nine sections had failed to.

  Nothing was dropped in the move: every number and every figure survives, and
  the Karnataka naive-versus-cleaned figure is now used, illustrating the third
  way the last-token assumption breaks alongside sex-marking names and
  Maharashtra's ordering.

- **Analysis 08 rebuilt around the repo's question, and its stated purpose
  corrected.** It had reported an initials measurement and a prediction exercise
  without connecting either to what the repo asks. The justification given for
  it was also wrong: the initials were said to contaminate analysis 03's
  Karnataka concentration figure, and they do not, because analysis 03 reads
  instate and instate contains no single-letter last names at all, 1.9M entries
  with a minimum length of six. The real reason the analysis belongs is that
  Karnataka is absent from SECC. The directory is renamed
  `08_karnataka_psc`, the finding is now the differential by category, and the
  resolve rule is aligned with analysis 09's, which moves the headline from 43.9
  to 40.0.
- **Analysis 08's null reversed on more data.** Cleaning initials out of
  Karnataka's last-token column was reported as making prediction slightly
  worse, on 14,854 candidates. The collection has since reached 48,395 and the
  sign is stable the other way: 45.3 mistakes per 100 naive against 43.9
  cleaned, with a blind rate of 52.5, so cleaning recovers about a sixth of what
  a name is worth there. The earlier figure was underpowered. What did not
  change is that a third of last tokens are single letters, that the ten
  commonest all are, and that the cleaned column resolves fewer candidates than
  the naive one, which is what shows the naive rule was pooling on initials.
- **Cut defensive prose.** The front page opened by denying three things it had
  not been accused of. Removed, along with "and it is not a caveat" in two
  files, a section headed "Three things this cannot support", and an instruction
  to the reader about what may be reported.

### Fixed

- **Every analysis that reads a sister repository had stopped running.** The
  checkouts moved under their GitHub organisations (`appeler/instate`,
  `in-rolls/upnaam` and so on), and a dozen copies of the same path helper
  still looked in the old places. Some analyses crashed. Others ran and wrote notes
  with their data silently missing: analysis 07's said the two commonest Punjab
  names "cover **0%** of the state". One table, `last_name_basis.siblings`, now
  says where each repository lives, and the land-record pipeline's
  `--github-dir` flag is gone in favour of the same `GITHUB_DIR`. The Rajasthan
  crawler was also misnamed (`ror_raj_2026` for `ror_rajasthan_2026`), and a
  test now checks both crawler paths.
- Analysis 11 read SECC from a sibling checkout of outkast; it and analysis 01
  now read the copy shipped in the installed package, which is a dependency.
- Analysis 06 crashed on pandas 3, where a failed lookup yields `pd.NA` rather
  than `NaN` and `np.isnan` rejects it.
- The README quoted three numbers no test checked: the 80 and 91 ranking
  figures and the share covered once Singh and Kumar are added. All three had
  drifted. They are now guarded, and analysis 03's "eighteen names" is read
  from the output instead of being written into the note and the figure title.

## [1.0.1] - 2026-08-26

One wrong sentence in the most citable claim, and the reversal it forces.

### Fixed

- **A wrong sentence in the most citable claim.** The front page and analysis 05
  said "a Dalit is guessed wrong 29 times in 100 against a blind rate of 30 --
  the name buys essentially nothing". The 29 was `1 - max(p)` averaged over the
  Dalits carrying each name, which measures how vague those names are; it is a
  property of names, not of people, and it was set against a population-wide
  blind rate. Scored consistently, the guess is wrong about 66 of every 100
  Dalits and 4 of every 100 people outside the schedules, and those weight up to
  the 20-per-hundred headline exactly.

  This reverses part of the old claim. The name is not useless for Dalits: it
  takes them from wrong about all of them to wrong about 66 in a hundred, and it
  does more still for Adivasis. What survives, and is stronger, is the disparity --
  seventeen-fold -- and the consequence for audits, which now rests on the right
  mechanism: two thirds of Dalits land in the comparison group.

  `by_caste` now reports `wrong_per_100`, `blind_wrong_per_100` and the old
  quantity renamed `name_vagueness_per_100`, and the figure plots recall error
  against each group's own blind rate rather than plotting vagueness under an
  axis labelled as error.
- Coverage for the sex split is now measured after the merge onto the caste
  table in analysis 05's own note, matching the front page.

## [1.0.0] - 2026-08-26

Six analyses of one question: pick a person at random, know only their last
name, and how often are you wrong about their caste?

The answer is a bracket rather than a number. Knowing nothing costs 25 mistakes
per hundred and the name alone costs 20, so the name is worth about five. Put
the same name next to a village and it is worth thirty. That gap, not the
average, is the finding.

### Analyses

- **01 surname to category.** All-India SC/ST/Other from SECC. The name saves
  five mistakes per hundred on average, changes nothing for 91% of people, and
  the three commonest surnames in India are among the least informative.
- **02 surname by geography.** Bihar land records, 141 jatis. A surname and a
  village leave 17 mistakes per hundred; the surname alone leaves 47.
- **03 how few names.** India's commonest last name records the bearer's sex,
  not her family. Names of that kind cover 10.5% of the country and make Indian
  naming look far more concentrated than it is.
- **04 which token is the surname.** A token shared between an elector and their
  father or husband is an inherited one. The test confirms ten sex-marking names,
  splits Singh (78% transmitted) from Kumar (8%), and found that Maharashtra
  writes the surname first, which withdrew two states from analysis 03.
- **05 who has an uninformative name.** The errors are not spread evenly. A
  Dalit is guessed wrong 29 times per hundred against a blind rate of 30; someone
  outside the schedules, 17. The method is accurate about the advantaged and
  blind about the disadvantaged. *(Corrected in Unreleased: the 29 was not what
  this sentence claims it was.)*
- **06 neighbours.** Holding out whole villages, the surrounding surnames rescue
  precisely the names that say nothing alone. Chaudhary goes from 80 mistakes to
  56. The bracket closes at 9 once the roll's cues are matched against a caste
  register.

### Added

- `tests/test_readme_numbers.py` pins all 28 headline figures on the front page
  to the outputs they come from, so a re-run analysis cannot silently leave a
  stale number in the README.
- `src/last_name_basis/upnaam.py`, a validated reader for versioned
  recorded-surname resolution.

### Fixed

- The front page claimed an electoral roll gets you to 9 mistakes per hundred.
  Caste is printed on no roll; the 9 requires matching the roll's cues against a
  caste register of the same population.
- All four rows of analysis 06's bracket are now scored on the same held-out
  villages. They had been split independently and shared only 2,509 of some
  8,300 test villages, so the rows described different people.
- The front page quoted two different blind rates, 25 and 30, without saying
  that the first is weighted by the electoral roll and the second by SECC.
- Analysis 02's surname-and-village figure was the plug-in estimate, 16. Half
  those cells hold one household, so the leave-one-out figure of 17 is the one
  that answers the question.
- The share of people whose name makes the guess *harder* was given as 32%,
  which matched neither weighting. It is 16%.
- Sex-marking names were said to cover 19% of the country. That figure includes
  Singh and Kumar, which analysis 04 shows are not the same case. The
  sex-marking names alone cover 10.5%.
- `in-rolls/jati` is private, and analyses 02 and 06 read their ladders from a
  local clone of it. The README linked it as though a reader could follow.

[Unreleased]: https://github.com/in-rolls/caste-name-information/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/in-rolls/caste-name-information/releases/tag/v1.0.1
[1.0.0]: https://github.com/in-rolls/caste-name-information/releases/tag/v1.0.0
