Formsender
==========

![travis](https://travis-ci.org/osuosl/formsender.svg?branch=develop)

Sends emails containing the information in a form.

Installation
------------

Start a virtual environment like so:

```
$ virtualenv venv
$ source venv/bin/activate
```

Now install the requirements:

```
$ pip install -r requirements.txt
```

To start the application, run `python request_handler.py` or `make run`. This
will start the application running locally `http://localhost:5000`.

The application is now waiting at port 5000 and can be sent POST requests from
forms. There are very specific requirements these forms must adhere to.
Instructions on how to set up a form that speaks to Formsender can be found in
the [documentation]
(https://github.com/osuosl/formsender/blob/develop/docs/source/form_setup.rst).

The application can be tested by running `make tests` and you can run flake8 on
the source code by running `make flake`.

To remove .pyc files run `make clean`

Local Form Testing
------------------

An example of a simple form can be found in `templates/index.html`. If you open
this in your browser, you can use that to POST a form to `PORT` defined in
`conf.py`. The form currently redirects to http://www.osuosl.org but you can
change the `redirect` field value to any site you wish. To see if your setup is
actually sending an email, change the `EMAIL` setting in `conf.py` to your
personal address.
