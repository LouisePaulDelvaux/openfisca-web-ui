STATIC_DIR=openfisca_web_ui/static
TESTS_DIR=openfisca_web_ui/tests

all: check test

build-dev: install-npm compile-i18n-python
	./node_modules/.bin/gulp dev

build-prod: install-npm compile-i18n-python
	./node_modules/.bin/gulp prod

check: flake8 jshint

check-syntax-errors:
	@# This is a hack around flake8 not displaying E910 errors with the select option.
	@# Do not analyse .gitignored files.
	@# `make` needs `$$` to output `$`. Ref: http://stackoverflow.com/questions/2382764.
	test -z "`flake8 --first $(shell git ls-files | grep "\.py$$") | grep E901`"

clean: clean-js-dist clean-pyc
	rm -Rf cache/templates/

clean-js-dist:
	./node_modules/.bin/gulp clean:dist

clean-pyc:
	find . -name '*.pyc' -exec rm \{\} \;

compile-i18n-python:
	python setup.py compile_catalog

ctags:
	ctags --recurse=yes --exclude=node_modules --exclude=openfisca_web_ui/static/dist .

flake8:
	@# Do not analyse .gitignored files.
	@# `make` needs `$$` to output `$`. Ref: http://stackoverflow.com/questions/2382764.
	flake8 `git ls-files | grep "\.py$$"`

install-npm:
	npm install

jshint:
	./node_modules/.bin/jsxhint ${STATIC_DIR}/js

poedit: update-i18n-python
	poedit openfisca_web_ui/i18n/fr/LC_MESSAGES/openfisca-web-ui.po
	make compile-i18n-python

test: check-syntax-errors
	nosetests $(TESTS_DIR) --stop --with-doctest

test-ci: check-syntax-errors flake8
	nosetests $(TESTS_DIR) --with-doctest

update-i18n: update-i18n-js update-i18n-python

update-i18n-python:
	python setup.py extract_messages update_catalog

update-i18n-js:
	./openfisca_web_ui/scripts/extract_i18n_json_messages.py --all --no-delete-regex='.+:.+'

update-npm-modules:
	[ -f ./node_modules/.bin/npm-check-updates ] || npm install
	./node_modules/.bin/npm-check-updates -u; npm install

watch:
	./node_modules/.bin/gulp watch
