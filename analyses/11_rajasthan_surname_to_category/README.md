# 11 — What a surname reveals about caste category in Rajasthan

Every analysis here built on SECC can tell a Dalit or an Adivasi from everyone
else and nothing finer, because the census records nothing finer. Panchayat
election records do: every candidate declares SC, ST, OBC or General to stand,
and Rajasthan's State Election Commission publishes it beside the name. This is
the only free source in the repo that separates OBC from General.

**Scope, before the numbers.** The category is self-declared on a nomination
form. The sample is shaped by reservation: seats reserved for a category take
only that category's candidates, so ST is 20% of the 206,673 records against
13.5% of the state, and every score is given on the sample as it comes and
re-weighted to Rajasthan's shares. The OBC/General split used for that,
50:19, is an assumption, since no census records it. A third of the names are
one word, so for them the "surname" is a given name.

**Finding.** Re-weighted, knowing nothing leaves **50 mistakes per 100** and
the last name **39**, on districts the guesser has never seen.

Only the 2020–22 sarpanch contestant records also give a father's or husband's
name. Among candidates with that information, the guesser assigns the wrong
category (SC, ST, OBC or General) **40.5 times per 100 candidates using the
candidate's own surname**, and **37.5 times using both surnames**. Adding the
relative's surname therefore saves about **3 mistakes per 100 candidates**.
Both figures use the same candidates, category weights and held-out districts;
the 39 above uses the larger sample that also includes election winners.

The surname ranks a Dalit above a non-Dalit 72 times in 100, an Adivasi above
a non-Adivasi 79 times, and **an OBC above a General 76 times**, the line SECC
cannot draw. Of 93 surnames that are at least 90% one category, 63
are literally the name of a jati and 23 the clan of one. `kanwar` is 89%
General, because it is what Rajput women are called; `verma` is 92% Scheduled
Caste. Against outkast's SECC extract the SC and ST shares of shared surnames
correlate at 0.98 and 0.99.

Run with `make a11`. Read [the note](note.md).
