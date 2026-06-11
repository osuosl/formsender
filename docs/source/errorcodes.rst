.. _errorcodes:

Error Codes and Logs
====================

Formsender tracks its errors using error codes. These error codes are sent to
the redirect url as explained `below`_. Additionally, Formsender `logs`_ its
errors and activities to standard output.

.. _below:

Error Codes
-----------

Formsender returns different error codes in a query string to the redirect url
when invalid data is sent from the form.

============   ========================    =============================================================
Error Number   Error Message               Cause
============   ========================    =============================================================
1              Invalid Email               User submitted an invalid email
2              Invalid Name                Name field was empty
3              Improper Form Submission    Honeypot was not empty, token was invalid, or fields_to_join referenced a missing field
4              Too Many Requests           Number of submissions violated CEILING variable from conf.py
5              Duplicate Request           This request is a duplicate of an earlier request
6              Invalid Recaptcha           The reCAPTCHA response failed verification
============   ========================    =============================================================

Two further error conditions are not returned as redirect error codes: a request
body larger than ``MAX_CONTENT_LENGTH`` is rejected with an HTTP ``413`` error,
and a malformed or empty POST renders a local error page with an HTTP ``400``
status.

These error codes can be handled with a little javascript in your redirect page:

.. code-block:: JavaScript

    // Get error number and message from query string
    function getQueryVariable(variable) {
      var query = window.location.search.substring(1);
      var vars = query.split("&");
      for (var i = 0; i < vars.length; i++) {
        var pair = vars[i].split("=");
        if(pair[0] == variable) {
          return pair[1];
        }
      }
      return (false);
    }

    var errorNumber = getQueryVariable("error");
    var errorMessage = getQueryVariable("message");

    // errorMessage will only be a string if a query string is present.
    // If a query string is present, there was an error. Format the message.
    if (typeof errorMessage == "string") {
      errorMessage = errorMessage.replace("+", " ").replace("/", "");
    }

    // If both these exist, there was an error with the submission, write to page
    if (errorNumber && errorMessage) {
      document.write("<h3 style='color:red'>An error occurred with your form submission</h3>",
                     "<p style='color:red'>Error number: ", errorNumber, "</p>",
                     "<p style='color:red'>Error message: ", errorMessage, "</p>");
    }

.. _logs:

Logs
----

In addition to the error codes sent to the redirect url, Formsender logs its
activity to standard output in the format ``LEVEL formsender: <message>``. Under
Docker/Gunicorn these lines are captured by the container's log stream. Rejected
submissions are logged at ``WARNING``; successful submissions and details are
logged at ``DEBUG``:

.. code-block:: none

  DEBUG formsender: creating ticket from: <submission-email>
  DEBUG formsender: ticket queue: <queue>
  DEBUG formsender: attaching file: <filename>
  DEBUG formsender: custom fields: ['CompanyName', 'WorkingGroups']
  WARNING formsender: received Duplicate Request: <submission-name> from <submission-email>
  WARNING formsender: received Too Many Requests: <submission-name> from <submission-email>
  WARNING formsender: received Invalid Email: <submission-email> from <submission-email>
  WARNING formsender: received Invalid Name:  from <submission-email>
  WARNING formsender: received Improper Form Submission: <submission-name> from <submission-email>
  WARNING formsender: received Invalid Recaptcha: <submission-name> from <submission-email>
