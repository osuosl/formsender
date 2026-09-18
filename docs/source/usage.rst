.. _usage:

How To Use Formsender
=====================

Formsender is configured through ``conf.py``. Copy the template
(``cp conf.py.dist conf.py``) and adjust it to match your setup. The template
reads secrets and instance-specific values from environment variables and
defines the remaining tunables as plain values:

.. code-block:: python

    import os

    TOKEN = os.environ['TOKEN']
    CEILING = 10
    DUPLICATE_CHECK_TIME = 3600  # seconds
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # bytes
    HOST = "0.0.0.0"
    PORT = 5000
    TRUSTED_PROXY_COUNT = int(os.environ.get('TRUSTED_PROXY_COUNT') or 0)
    TURNSTILE_SECRET = os.environ.get('TURNSTILE_SECRET')
    ALTCHA_HMAC_KEY = os.environ.get('ALTCHA_HMAC_KEY')
    RECAPTCHA_SECRET = os.environ.get('RECAPTCHA_SECRET')
    CAPTCHA_ALLOWED_HOSTNAMES = os.environ.get('CAPTCHA_ALLOWED_HOSTNAMES')
    RECAPTCHA_MIN_SCORE = 0.5
    ALTCHA_ALGORITHM = 'PBKDF2/SHA-256'
    ALTCHA_COST = 5000
    ALTCHA_EXPIRES = 600
    URL = os.environ.get('RT_URL', "https://support.osuosl.org/REST/2.0/")
    RT_TOKEN = os.environ['RT_TOKEN']
    SENTRY_URI = os.environ.get('SENTRY_URI')

Environment variables
---------------------

These must be supplied in the environment Formsender runs in (for example with
``docker run -e``):

* ``TOKEN`` is the shared secret used to authenticate a form submission. It must
  match the hidden ``token`` field in your form. See the
  `form setup documentation`_.
* At least one captcha provider secret. A form picks its provider by which
  response field it posts (see the `form setup documentation`_), and Formsender
  only accepts providers whose secret is set, so an instance can serve several
  sites during a migration and drop a provider by unsetting its secret.

  .. warning::

     The submission chooses the provider, not the server. Any provider
     configured on an instance can be used by any form it serves, so a bot can
     answer a Turnstile form with whichever configured provider it finds
     easiest. Configure only the providers your forms actually use, and unset
     each one as soon as the last form using it has migrated.

  * ``TURNSTILE_SECRET`` is the `Cloudflare Turnstile`_ widget secret. Formsender
    verifies the ``cf-turnstile-response`` field against Cloudflare's
    ``siteverify`` endpoint. Pair it with the site key embedded in your form.
    Turnstile is free and the site does not need to be behind Cloudflare.
  * ``ALTCHA_HMAC_KEY`` enables `ALTCHA`_, a self-hosted proof-of-work captcha.
    Formsender issues signed challenges from its ``/altcha`` endpoint and
    verifies the ``altcha`` field locally, so no third-party service is
    involved. Use a long random string (for example ``openssl rand -hex 32``).
    The key signs the challenges, so it must be **the same on every container
    serving a site and stable across restarts**; a container that mints its own
    key rejects every challenge issued by another one. ALTCHA also carries no
    origin information, so ``CAPTCHA_ALLOWED_HOSTNAMES`` cannot apply to it.
  * ``RECAPTCHA_SECRET`` is the Google reCAPTCHA secret key (v2 or v3).
    Formsender verifies the ``g-recaptcha-response`` field against Google's
    ``siteverify`` endpoint. Note that Google's free tier is limited to 10,000
    verifications a month per Google Cloud project.
* ``CAPTCHA_ALLOWED_HOSTNAMES`` (optional) is a comma-separated list of
  hostnames. When set, a Turnstile or reCAPTCHA token is only accepted if the
  provider reports it was solved on one of those hosts. This stops a token
  minted on another site that shares the same key pair from being replayed.
  Setting it to a value that names no hostnames is a configuration error and
  Formsender refuses to start, rather than silently skipping the check.
* ``TRUSTED_PROXY_COUNT`` (optional, default ``0``) is the number of
  ``X-Forwarded-For`` hops to trust. Set it to ``1`` when Formsender runs
  behind a single reverse proxy such as HAProxy. Without it the captcha
  provider is told the proxy's IP address instead of the sender's, which
  degrades the provider's own risk scoring. Leave it at ``0`` when Formsender
  is reachable directly, where the header can be forged.
* ``RT_TOKEN`` is the RT authentication token used to connect to the RT REST2
  API. It belongs to an RT user with permission to create tickets in the target
  queues.
* ``RT_URL`` (optional) overrides the RT REST2 endpoint. It defaults to
  ``https://support.osuosl.org/REST/2.0/``. Setting it lets a single image serve
  a different RT instance, so one container can be run per RT instance.
* ``SENTRY_URI`` (optional) is a Sentry DSN. When set, errors are reported to
  Sentry.

.. _Cloudflare Turnstile: https://developers.cloudflare.com/turnstile/
.. _ALTCHA: https://altcha.org/

Creating a Cloudflare Turnstile widget
--------------------------------------

Turnstile is configured per site in the Cloudflare dashboard, under
**Turnstile**, then **Add widget**. A widget is one site key and secret key
pair, so create one widget per website rather than one per form. A free Cloudflare account is
enough, and the website does not need to be proxied through Cloudflare.

Fill the **Add Widget** form in as follows:

Widget name
    Free text, only used to identify the widget in the dashboard later. Name it
    after the site it protects and the application using it, for example
    ``osuosl.org formsender``.

Hostnames
    The hostnames allowed to display this widget. This is the **website's** own
    hostname, not Formsender's, so the OSL widget lists ``osuosl.org`` and the
    OpenPOWER Foundation widget lists ``openpowerfoundation.org``. A hostname
    also covers its subdomains, so ``openpowerfoundation.org`` already allows
    ``www.openpowerfoundation.org`` and there is no need to add it. A free
    account allows up to ten hostnames per widget. Do not add ``localhost``
    here; use the test credentials in the :ref:`integration_testing`
    documentation for local work instead.

Widget Mode
    **Managed**. Cloudflare then decides per visitor how much friction to
    apply, so most people get a non-interactive check and only risky traffic
    sees a challenge. Non-interactive and Invisible both lower that ceiling,
    which is the opposite of what a spam problem calls for.

Skip future security rule challenges for verified visitors
    Leave this **off**. Pre-clearance issues a cookie that bypasses Cloudflare
    WAF rules, and it only does anything when the site is proxied through
    Cloudflare. It has no effect on whether Formsender accepts a submission.

Creating the widget produces the two keys, both shown on the widget's page in
the dashboard:

* The **site key** is public. It goes in the form markup as ``data-sitekey``
  (see the `form setup documentation`_) and can live in the website's
  repository.
* The **secret key** is private. It becomes Formsender's ``TURNSTILE_SECRET``.
  Keep it out of the website's repository; in the OSL deployment it belongs in
  the encrypted Chef data bag the container reads its environment from.

If you set ``CAPTCHA_ALLOWED_HOSTNAMES``, note that it is matched exactly and
does not imply subdomains the way the widget's own hostname list does. List
every hostname that actually serves a form, so a site reachable as both
``example.org`` and ``www.example.org`` needs both entries.

In-file settings
----------------

These are defined directly in ``conf.py`` and can be edited as needed:

* ``CEILING`` is the maximum number of submissions Formsender will accept per
  second before returning a ``Too Many Requests`` error.
* ``DUPLICATE_CHECK_TIME`` is the window (in seconds) over which identical
  submissions are treated as duplicates.
* ``MAX_CONTENT_LENGTH`` is the maximum size (in bytes) of a submitted request
  body, including any file uploads. Larger requests are rejected with a ``413``
  error. Defaults to 10 MiB.
* ``RECAPTCHA_MIN_SCORE`` is the lowest reCAPTCHA v3 score (0.0 to 1.0) that
  is accepted. It has no effect on v2 keys, which return no score.
* ``ALTCHA_ALGORITHM`` and ``ALTCHA_COST`` set the proof-of-work function and
  its iteration count for ALTCHA challenges. Raising the cost makes every
  submission (human or bot) spend more CPU in the browser, and costs the server
  the same work again when it verifies. The algorithm must be one of
  ``PBKDF2/SHA-256`` (the default, and what the browser widget expects),
  ``PBKDF2/SHA-384``, ``PBKDF2/SHA-512``, ``SHA-256``, ``SHA-384`` or
  ``SHA-512``. Formsender refuses to start on any other value. Note that the
  cost is a weak lever: it falls on every visitor's browser as much as on a
  bot, so ALTCHA raises the price of bulk submission rather than preventing
  it. Use Turnstile where that matters.
* ``ALTCHA_EXPIRES`` is how long (in seconds) an issued ALTCHA challenge can be
  redeemed. A redeemed challenge is refused afterwards, but that record lives
  in one worker process, so with several workers or containers a solved
  challenge can be spent once per worker within this window. Keep it short.
* ``HOST`` and ``PORT`` are the interface and port the development server
  (``make run``) listens on. In production the bind address is set by the WSGI
  server instead (see ``entrypoint.sh``).

Logging
-------

Formsender writes its logs to standard output in the format
``LEVEL formsender: <message>``. Under Docker/Gunicorn these are captured by the
container's log stream. See the `error codes documentation`_ for the messages
Formsender emits.

Set Up A Development Instance
-----------------------------

To set up a development instance, first start a virtual environment like so:

.. code-block:: none

    $ python3 -m venv venv
    $ source venv/bin/activate


Now install the development requirements (these pull in the runtime
requirements plus the lint, test, and docs tooling; the production image
installs only ``requirements.txt``):

.. code-block:: none

    $ pip install -r requirements-dev.txt


Before you run Formsender, copy the contents of ``conf.py.dist`` into a new file
called ``conf.py`` as described above, and export the required environment
variables (``TOKEN``, ``RT_TOKEN``, and at least one captcha secret).

You can lint the application with flake8:

.. code-block:: none

    $ make flake

Run the test suite (the tests mock all external calls, so no real RT or
captcha credentials are needed):

.. code-block:: none

    $ make tests

Run the test suite with a coverage report (enforces full coverage):

.. code-block:: none

    $ make coverage

To run the application locally for development purposes:

.. code-block:: none

    $ make run

The app will now wait at ``HOST:PORT`` for a form to be submitted, and will
create an RT ticket from each valid submission. If you left the conf file
unchanged, this starts the application at ``http://localhost:5000``, ready to
receive POST requests from forms. There are very specific requirements these
forms must adhere to. Instructions on how to set up a form that speaks to
Formsender can be found in the `form setup documentation`_.

Local Form Testing
------------------

An example of a simple form can be found in ``templates/index.html``. If you
open this in your browser, you can use it to POST to the ``PORT`` defined in
``conf.py``. The form redirects to ``http://www.osuosl.org`` on success; change
the ``redirect`` field value to any site you wish. To confirm that tickets are
actually being created, point ``RT_URL`` and ``RT_TOKEN`` at a test RT instance
and watch its queues.

.. _form setup documentation: http://formsender.readthedocs.org/en/latest/form_setup.html
.. _error codes documentation: http://formsender.readthedocs.org/en/latest/errorcodes.html
