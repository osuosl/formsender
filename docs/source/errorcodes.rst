.. _error-codes:

Error Codes
===========

Formsender returns different error codes when invalid data is sent from the
form.

============   ========================    =============================================================
Error Number   Error Message               Cause
============   ========================    =============================================================
1              Invalid Email               User submitted an invalid email
2              Invalid Name                Name field was empty
3              Improper Form Submission    Hidden field was not empty or token was invalid
4              Too Many Requests           Number of submissions violated CEILING variable from conf.py
============   ========================    =============================================================
