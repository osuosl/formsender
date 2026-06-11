.. _integration_testing:

Integration Testing Against a Real RT
=====================================

This howto walks through wiring Formsender to a real Request Tracker (RT)
instance and driving it end to end from the two OSUOSL Hugo sites. It is meant
for integration testing: standing up the whole chain locally (or in a throwaway
VM) and confirming that a form submission lands as a ticket with the right
queue, body, attachments, and custom fields.

The chain
---------

::

    browser ──POST──▶ website form ──POST──▶ formsender ──REST2 token──▶ RT
    (osuosl.org /                            (this app)                  (osl-rt
     openpower.foundation)                                               cookbook)

* The website renders an HTML form that POSTs to Formsender.
* Formsender validates the submission and creates a ticket through RT's REST2
  API using a token.
* RT is provided by the ``osl-rt`` cookbook, which ships REST2 and token
  authentication and creates the queues you configure.

Three things must line up across the whole chain, and they are the usual cause
of a failed integration:

#. The form's ``send_to`` value must equal an RT **queue name**
   (case-sensitive).
#. Any ``custom_fields`` the form declares must be **custom fields that exist in
   RT** and are applied to that queue.
#. The form ``token`` must equal Formsender's ``TOKEN``, and the reCAPTCHA site
   key in the form must pair with Formsender's ``RECAPTCHA_SECRET``.

1. Stand up a test RT with osl-rt
---------------------------------

The ``osl-rt`` cookbook deploys RT over plain HTTP with the ``RT::Extension::REST2``
and ``RT::Authen::Token`` plugins (both are core on RT 5 / EL10). Its Test
Kitchen suites are the quickest way to get a working instance:

.. code-block:: none

    $ cd .../osuosl-cookbooks/osl-rt
    $ kitchen converge default

The instance is configured from the ``request-tracker`` data bag (see
``test/integration/data_bags/request-tracker/default.json``). The important key
for Formsender is ``queues`` -- a map of *queue name* to *email local-part*.
**Every** ``send_to`` value your forms use must appear here as a queue name. For
example, to exercise both sites add their queues:

.. code-block:: json

    "queues": {
      "Support": "support",
      "HostingRequests": "hosting",
      "AARCH64-Hosting": "aarch64",
      "PowerDev": "powerdev",
      "PowerCI": "powerci",
      "IBM-Z-CI": "ibmzci",
      "general": "general",
      "members": "members",
      "events": "events",
      "marketing": "marketing",
      "press": "press",
      "boardofdirectors": "board",
      "steeringcommittee": "steering",
      "hub": "hub",
      "passport": "passport",
      "isarfc": "isarfc"
    }

Re-converge after editing the data bag; osl-rt creates only the queues that are
missing, so existing queues and tickets are left untouched.

The REST2 endpoint is ``http://<fqdn>/REST/2.0/``. The default suite serves the
host ``example.org`` (with the on-box alias ``rtlocal``). To reach it from a
Formsender running off the RT host, make the ``fqdn`` resolve to the RT instance
-- either set a real ``fqdn`` in the data bag, or add a ``/etc/hosts`` entry
pointing the chosen name at the kitchen VM's IP.

Custom fields
~~~~~~~~~~~~~

osl-rt creates queues but **not** custom fields. The OpenPOWER forms map onto RT
custom fields (``CompanyName``, ``ProjectName``, ``WorkingGroups``, ``RequestType``,
and so on -- see the form partials), so for those mappings to populate, the
custom fields must already exist in RT and be applied to the target queue.
Create them once in the RT web UI under **Admin → Custom Fields** (set *Applies
to* = Tickets and add them to the relevant queues), or script it with the ``rt``
CLI. If a declared custom field does not exist in RT, the ticket create call
fails, so create them before testing the OpenPOWER forms.

2. Create an RT auth token
--------------------------

Formsender authenticates to REST2 with a token (``RT_TOKEN``), not a password.
Create one for a user that has the **CreateTicket** right on the target queues
(``root`` already does):

#. Log in to the RT web UI as ``root`` (the ``root-password`` from the data bag,
   ``my-epic-rt`` in the default suite).
#. Open **Logged in as root → Settings → Auth Tokens**.
#. Create a token (give it a description like ``formsender``) and copy the value
   -- RT shows it only once.

That value is Formsender's ``RT_TOKEN``. You can sanity-check it directly::

    $ curl -s -H 'Authorization: token <RT_TOKEN>' \
        http://<fqdn>/REST/2.0/queues/all | jq '.items[].id'

3. Run Formsender pointed at the test RT
----------------------------------------

Configure Formsender with the RT endpoint and token, a form token, and a
reCAPTCHA secret. For local testing, use Google's official reCAPTCHA test
credentials, which always validate as success:

* site key (goes in the form): ``6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI``
* secret (``RECAPTCHA_SECRET``): ``6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe``

Run the container (or ``make run`` from a checkout):

.. code-block:: none

    $ docker run -p 5000:5000 \
        -e TOKEN=foo \
        -e RECAPTCHA_SECRET=6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe \
        -e RT_TOKEN=<RT_TOKEN> \
        -e RT_URL=http://<fqdn>/REST/2.0/ \
        ghcr.io/osuosl/formsender:master

Confirm it is up:

.. code-block:: none

    $ curl -s http://localhost:5000/server-status
    OK

4. Point the websites at Formsender
-----------------------------------

openpower.foundation
~~~~~~~~~~~~~~~~~~~~~

This site is already wired for a local Formsender in its development config
(``config/development/params.toml``): ``forms.endpoint`` points at
``http://localhost:5000``, ``forms.token`` is ``foo``, and ``forms.recaptcha_sitekey``
is the Google test site key. Make sure Formsender's ``TOKEN`` matches
``forms.token`` and its ``RECAPTCHA_SECRET`` is the matching test secret (above),
then run Hugo in the development environment:

.. code-block:: none

    $ cd .../openpower.foundation
    $ hugo server -e development

Browse to a form (Contact, HUB, Passport, or ISA RFC), submit it, and Formsender
will redirect to the ``redirect`` page (``/form-submitted/``) on success.

osuosl.org website
~~~~~~~~~~~~~~~~~~

The OSL site hardcodes the Formsender host, form token, and reCAPTCHA site key
inline in each form (under ``content/services/*.md``). For local testing,
temporarily repoint a form at your Formsender: change its ``action`` to
``http://localhost:5000``, set the hidden ``token`` to match Formsender's
``TOKEN``, and use the reCAPTCHA test site key. Its ``send_to`` queues
(``HostingRequests``, ``AARCH64-Hosting``, ``PowerDev``, ``PowerCI``,
``IBM-Z-CI``) must exist in the RT instance (step 1). Then run the site locally
with ``hugo server`` and submit the form.

5. Verify the ticket
---------------------

After a successful submission, confirm the ticket in RT. The newest ticket id::

    $ curl -s -H 'Authorization: token <RT_TOKEN>' \
        'http://<fqdn>/REST/2.0/tickets?query=id>0&orderby=-id' \
        | jq '.items[0].id'

Then inspect it, checking the queue, subject, body, and any custom fields (the
``fields=Queue`` expansion inlines the queue name, which is otherwise just a
reference)::

    $ curl -s -H 'Authorization: token <RT_TOKEN>' \
        'http://<fqdn>/REST/2.0/ticket/<id>?fields=Queue' \
        | jq '{Queue: .Queue.Name, Subject, CustomFields}'

For a form with a file upload (the ISA RFC form), confirm the attachment is
present on the ticket's first transaction in the RT web UI, or via the REST2
attachments endpoint.

Common pitfalls
---------------

* **404 / wrong vhost from REST2.** RT serves by virtual host. Reach it via the
  configured ``fqdn`` (or ``rtlocal`` on-box), not a bare IP, so the request
  matches RT's vhost.
* **"Queue not found".** The ``send_to`` value does not match an RT queue name
  exactly (it is case-sensitive). Add the queue to the data bag and re-converge.
* **Ticket create fails when custom fields are set.** A name in ``custom_fields``
  is not a custom field that exists in RT and is applied to the queue. Create and
  apply it first.
* **"Invalid Recaptcha".** The form's site key and Formsender's
  ``RECAPTCHA_SECRET`` are not a matching pair. Use the Google test pair above
  for local testing.
* **413 on submit.** The upload exceeded ``MAX_CONTENT_LENGTH`` (default 10 MiB).

