PY?=python

help:
	      @echo 'Makefile for Formsender                                       '
				@echo '                                                              '
				@echo 'Usage:                                                        '
				@echo '   make run       run the application on http://localhost:5000'
				@echo '   make clean     remove the generated files                  '
				@echo '   make tests     run tests                                   '
				@echo '   make flake     run flake8 on application                   '
				@echo '                                                              '

run:
	      $(PY) request_handler.py

clean:
	      rm *.pyc

tests:
	      $(PY) tests.py

flake:
	      flake8 request_handler.py
	      flake8 tests.py
