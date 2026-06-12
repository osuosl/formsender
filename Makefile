PY?=python3

help:
	      @echo 'Makefile for Formsender                                       '
				@echo '                                                              '
				@echo 'Usage:                                                        '
				@echo '   make run       run the application on http://localhost:5000'
				@echo '   make clean     remove the generated files                  '
				@echo '   make tests     run tests                                   '
				@echo '   make coverage  run tests with coverage report              '
				@echo '   make flake     run flake8 on application                   '
				@echo '                                                              '

run:
	      $(PY) request_handler.py

clean:
	      rm *.pyc

tests:
	      $(PY) tests.py

coverage:
	      coverage run -m unittest tests
	      coverage report

flake:
	      flake8 request_handler.py
	      flake8 tests.py
