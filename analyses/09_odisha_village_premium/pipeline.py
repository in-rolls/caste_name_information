"""Run the shared Odisha land-record analysis."""

from last_name_basis.land_records.pipeline import main

if __name__ == "__main__":
    main(["--states", "odisha"])
