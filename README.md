Formsender
==========

![travis](https://travis-ci.org/osuosl/formsender.svg?branch=develop)

Formsender is a WSGI app that accepts a POST request from a form and emails the
contents in a formatted message to a configurable address. Formsender can be
deployed using a WSGI server of your choice.

Deploy
------

To deploy Formsender, set it up in a persistent environment with the
dependencies described in `setup.py` installed.

The file `conf.py.dist` contains the settings Formsender needs to run. Copy
the contents into a new file named `conf.py` in the same directory. These
settings can be changed to reflect your setup. Explanations of what each setting
does can be found in the documentation.

Formsender is a WSGI application. For help with deploying a WSGI app you can
take a look at the [uWSGI](https://uwsgi-docs.readthedocs.org/en/latest/) and
[Gunicorn](http://docs.gunicorn.org/en/19.3/) documentation.

Set Up A Development Instance
-----------------------------

Start a virtual environment like so:

```
$ virtualenv venv
$ source venv/bin/activate
```

Now install the requirements:

```
$ pip install -r requirements.txt
```

Before you run Formsender, you must copy the contents of `conf.py.dist` into a
new file called `conf.py`. The settings in here can be changed depending on the
configuration you want. More information can be found in the docs.

To start the application, run `python request_handler.py` or `make run`. If you
left the conf file unchanged, this will start the application running locally at
`http://localhost:5000`.

The application is now waiting at port 5000 and can be sent POST requests from
forms. There are very specific requirements these forms must adhere to.
Instructions on how to set up a form that speaks to Formsender can be found in
the [documentation](http://formsender.readthedocs.org/en/latest/).

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
