Formsender
==========

![CI](https://github.com/osuosl/formsender/actions/workflows/ci.yml/badge.svg)

Formsender is a WSGI application that accepts a POST request from an HTML form,
validates and rate-limits the submission, and creates a ticket in
[Request Tracker (RT)](https://bestpractical.com/request-tracker) through its
REST2 API.

Features:

* Honeypot, shared-token, rate-limit, duplicate-detection, and reCAPTCHA checks
  to filter out spam and abuse.
* File uploads are attached to the ticket.
* Form fields can be mapped to RT custom fields.
* A single image can serve multiple RT instances (one container per instance)
  by setting the `RT_URL` environment variable.

Configure
---------

The file `conf.py.dist` reads its settings from environment variables. Copy it
to `conf.py` (`cp conf.py.dist conf.py`) and supply the environment variables
described in the [usage documentation]
(http://formsender.readthedocs.org/en/latest/usage.html). At minimum you must
set `TOKEN`, `RECAPTCHA_SECRET`, and `RT_TOKEN`.

Deploy
------

Formsender is distributed as a container image published to the GitHub Container
Registry at `ghcr.io/osuosl/formsender`. The image runs the app under Gunicorn
(see `entrypoint.sh`). To run it:

```
docker run -p 5000:5000 \
  -e TOKEN=... \
  -e RECAPTCHA_SECRET=... \
  -e RT_TOKEN=... \
  -e RT_URL=https://support.example.org/REST/2.0/ \
  ghcr.io/osuosl/formsender:master
```

See the [Docker documentation]
(http://formsender.readthedocs.org/en/latest/docker.html) for more detail. Because
Formsender is a standard WSGI application, it can also be deployed under any WSGI
server of your choice (e.g. [uWSGI](https://uwsgi-docs.readthedocs.org/en/latest/)
or [Gunicorn](https://docs.gunicorn.org/en/stable/)).

Develop
-------

To set up a development instance and run the tests, check out the
[Formsender usage documentation]
(http://formsender.readthedocs.org/en/latest/usage.html). In short:

```
pip install -r requirements-dev.txt   # runtime deps + lint/test/docs tooling
cp conf.py.dist conf.py
make flake      # lint
make coverage   # run the test suite with a coverage report
```

The production image installs only `requirements.txt` (runtime dependencies);
`requirements-dev.txt` adds the lint, test, and Sphinx docs tooling on top.
