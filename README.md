Formsender
==========

![travis](https://travis-ci.org/osuosl/formsender.svg?branch=develop)

Sends emails containing the information in a form.

To start the application, run `python request_handler.py` or `make run`. This
will start the application running locally `http://localhost:5000`.

The application is now waiting at port 5000 and can be sent POST requests from
forms. There are very specific requirements these forms must adhere to.
Instructions on how to set up a form that speaks to Formsender can be found in
the [documentation](./docs/src/form_setup.rst).

The application can be tested by running `make tests` and you can run flake8 on
the source code by running `make flake`.

To remove .pyc files run `make clean`
