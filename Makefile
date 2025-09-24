PYTEST?=pytest

.PHONY: test test-parsers test-scrapers

test:
	$(PYTEST) -q -s tests

test-parsers:
	$(PYTEST) -q -s tests/parsers

test-scrapers:
	$(PYTEST) -q -s tests/scrapers



