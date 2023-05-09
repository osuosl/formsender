Formsender
==========

![travis](https://travis-ci.org/osuosl/formsender.svg?branch=develop)

Formsender is a WSGI app that accepts a POST request from a form and uses the
RT REST API to create and manage tickets at support.osuosl.org.
Formsender can be deployed using a WSGI server of your choice.

Deploy
------

To deploy Formsender, set it up in a persistent environment with the
dependencies described in `setup.py` installed.

The file `conf.py.dist` contains the settings Formsender needs to run. Copy
the contents into a new file named `conf.py` in the same directory. These
settings can be changed to reflect your setup. Explanations of what each setting
does can be found in the [documentation]
(http://formsender.readthedocs.org/en/latest/).

Formsender is a WSGI application. For help with deploying a WSGI app you can
take a look at the [uWSGI](https://uwsgi-docs.readthedocs.org/en/latest/) and
[Gunicorn](http://docs.gunicorn.org/en/19.3/) documentation.

To set up a development instance, check out the [Formsender usage documentation]
(http://formsender.readthedocs.org/en/latest/usage.html)
