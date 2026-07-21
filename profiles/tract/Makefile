# TRACT specification build & checks.

.PHONY: lint lint-strict pdf check coverage

## lint — internal-consistency checks over the spec (see tools/lint.py).
## Every check exists because a real contradiction survived human review.
lint:
	@python3 tools/lint.py

## lint-strict — as above, but warnings also fail. Use before a release tag.
lint-strict:
	@python3 tools/lint.py --warn-as-error

## pdf — markdown -> single HTML -> PDF via the installed Chrome. No LaTeX.
## First run: (cd build && npm install)
pdf:
	@cd build && node build.mjs

## coverage — reports how many conformance cases are planned vs. how many have a vector.
## Honest by design: both numbers come from counting things on disk (SUITE.md rows,
## conformance/vectors/*.json files), never a hardcoded total or a computed percentage, so
## this can't silently go stale as the vector corpus grows past whatever number a comment
## once claimed. It says nothing about full vs. partial coverage of a given case — that
## nuance lives in conformance/vectors/README.md's own table, which this target points at
## rather than trying to summarise in one line.
coverage:
	@planned=$$(grep -c '^| TRACT-' conformance/SUITE.md 2>/dev/null || echo 0); \
	vectors=$$(ls conformance/vectors/*.json 2>/dev/null | wc -l | tr -d ' '); \
	echo "conformance: $$planned case(s) planned in conformance/SUITE.md, $$vectors vector file(s) present in conformance/vectors/ (see conformance/vectors/README.md for exactly which SUITE.md ids each one covers, fully or partially)"

check: lint
