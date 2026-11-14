# Rajasthan land-record village premium

Run `make a12`, or `make land-premium` for both states.

The shared implementation and data dictionary are documented in
[the pipeline guide](../../docs/land-records.md). Read the generated [note](note.md)
for the current snapshot, census reconciliation, results and limitations.

Recorded caste labels are the primary target. The unit is a recorded owner entry
after consolidating repeated account lists across plots, not a verified unique
person or household. Entire accounts are held out when scoring.
