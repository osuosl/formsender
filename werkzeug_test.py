from conf import TOKN, EMAIL, CEILING
import smtplib
import unittest
from request_handler import (Forms, create_msg, validate_name, is_valid_email,
                     is_hidden_field_empty, is_valid_token, RateLimiter, rater)
from werkzeug.test import Client
from werkzeug.testapp import test_app
from werkzeug.wrappers import BaseResponse, Request
from werkzeug.test import EnvironBuilder
from StringIO import StringIO
from mock import Mock, create_autospec, MagicMock, patch
from email.mime.text import MIMEText
from validate_email import validate_email
from datetime import datetime


class TestFormsender(unittest.TestCase):

    def test_create_msg_with_content(self):
        """
        Tests create_msg with content in the POST request

        Checks that each element in the request is returned create_msg
        """
        builder = EnvironBuilder(method='POST',
                                 data={'foo' : 'this is some text',
                                      'file': 'my file contents',
                                      'test': 'test.txt'})
        env = builder.get_environ()
        req = Request(env)
        self.assertEqual(create_msg(req)['foo'], builder.form['foo'])
        self.assertEqual(create_msg(req)['file'], builder.form['file'])
        self.assertEqual(create_msg(req)['test'], builder.form['test'])

    def test_create_msg_no_content(self):
        """
        Tests create_msg with no content in the POST request

        Checks that create_msg returns None
        """
        builder = EnvironBuilder(method='POST', data={})
        env = builder.get_environ()
        req = Request(env)
        self.assertIsNone(create_msg(req))

    def test_create_msg_with_content_get_method(self):
        """
        Tests create_msg with content in a GET request

        Checks that create_msg returns None
        """
        builder = EnvironBuilder(method='GET',
                                 data={'foo' : 'this is some text',
                                       'file': 'my file contents',
                                       'test': 'test.txt'})
        env = builder.get_environ()
        req = Request(env)
        self.assertIsNone(create_msg(req))

    def test_send_email(self):
        """
        Tests send_email

        send_email returns True when it successfully sends an email and
        False when unsuccessfull.
        """
        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'hidden': '',
                                       'tokn': TOKN })
        env = builder.get_environ()
        req = Request(env)

        # Construct message for assertion
        msg = create_msg(req)
        msg_send = MIMEText(str(msg))

        # Mock sendmail function
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')

        rater.reset_rate()

        # Call send_email and assert sendmail was called correctly
        real = Forms()
        real.send_email(msg)
        smtplib.SMTP.sendmail.assert_called_with('theform',
                                                 EMAIL,
                                                 msg_send.as_string())

    @patch('request_handler.validate_email')
    def test_validations_valid_data(self, mock_validate_email):
        """
        Tests the form validation with valid data.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'hidden': '',
                                       'tokn': TOKN })
        env = builder.get_environ()
        req = Request(env)

        mock_validate_email.return_value = True
        rater.reset_rate()

        app = Forms()
        resp = app.on_form_page(req)
        self.assertEqual(resp.status_code, 200)

    def test_validations_invalid_name(self):
        """
        Tests the form validation with an invalid name.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        Invalid name field causes an 'Invalid Name' error.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': '   ',
                                       'email': 'example@osuosl.org',
                                       'hidden': '',
                                       'tokn': TOKN })
        env = builder.get_environ()
        req = Request(env)
        rater.reset_rate()
        app = Forms()
        resp = app.on_form_page(req)
        self.assertEqual(resp.status_code, 400)

    def test_validations_invalid_email(self):
        """
        Tests the form validation with an invalid email.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        Invalid email field causes an 'Invalid Email' error.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'invalid@example.com',
                                       'hidden': '',
                                       'tokn': TOKN })
        env = builder.get_environ()
        req = Request(env)
        rater.reset_rate()
        app = Forms()
        resp = app.on_form_page(req)
        self.assertEqual(resp.status_code, 400)

    def test_validations_invalid_hidden(self):
        """
        Tests the form validation with content in the hidden field.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        Content in the hidden field causes an 'Improper Form Submission'
        error.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'hidden': 'r',
                                       'tokn': TOKN })
        env = builder.get_environ()
        req = Request(env)
        rater.reset_rate()
        app = Forms()
        resp = app.on_form_page(req)
        self.assertEqual(resp.status_code, 400)

    def test_validations_invalid_token(self):
        """
        Tests the form validation with an invalid token.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        An invalid token causes the 'Improper Form Submission' error.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'hidden': '',
                                       'tokn': 'evilrobot' })
        env = builder.get_environ()
        req = Request(env)
        rater.reset_rate()
        app = Forms()
        resp = app.on_form_page(req)
        self.assertEqual(resp.status_code, 400)

    @patch('request_handler.validate_email')
    def test_is_valid_email_with_valid(self, mock_validate_email):
        """
        Tests is_valid_email with a valid email

        is_valid_email checks that the email submitted to the form is
        valid and exists. This function call should return true.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'email': 'example@osuosl.org'})
        env = builder.get_environ()
        req = Request(env)

        mock_validate_email.return_value = True

        self.assertTrue(is_valid_email(req))

    def test_is_valid_email_with_invalid(self):
        """
        Tests is_valid_email with an invalid email

        is_valid_email checks that the email submitted to the form is
        valid and exists. This function call should return false.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'email': 'nope@example.com'})
        env = builder.get_environ()
        req = Request(env)
        self.assertFalse(is_valid_email(req))

    def test_validate_name_with_valid(self):
        """
        Tests validate_name with a valid name

        validate_name checks that the name submitted to the form does
        not contain disallowed characters. This function call should return
        true.
        """
        builder = EnvironBuilder(method='POST', data={'name': 'Matthew'})
        env = builder.get_environ()
        req = Request(env)
        self.assertTrue(validate_name(req))

    def test_validate_name_with_invalid(self):
        """
        Tests validate_name with an invalid name

        validate_name checks that the name submitted to the form does
        not contain disallowed characters. This function call should
        return false.
        """
        builder = EnvironBuilder(method='POST', data={'name': '  '})
        env = builder.get_environ()
        req = Request(env)
        self.assertFalse(validate_name(req))

    def test_is_hidden_field_empty_empty(self):
        """
        Tests is_hidden_field_empty with 'hidden' field empty

        is_hidden_field_empty checks that the hidden field in the form
        is empty. This function call should return true.
        """
        builder = EnvironBuilder(method='POST', data={'hidden': ''})
        env = builder.get_environ()
        req = Request(env)
        self.assertTrue(is_hidden_field_empty(req))

    def test_is_hidden_field_empty_full(self):
        """
        Tests is_hidden_field_empty with contents in 'hidden' field

        is_hidden_field_empty checks that the hidden field in the form
        is empty. This function call should return false.
        """
        builder = EnvironBuilder(method='POST', data={'hidden': 'nope'})
        env = builder.get_environ()
        req = Request(env)
        self.assertFalse(is_hidden_field_empty(req))

    def test_is_valid_token_valid(self):
        """
        Tests is_valid_token with TOKN defined in conf.py

        is_valid_token checks that the token provided by the form matches
        token described in the settings file. This function call should
        return true.
        """
        builder = EnvironBuilder(method='POST', data={'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)
        self.assertTrue(is_valid_token(req))

    def test_is_valid_token_invalid(self):
        """
        Tests is_valid_token with invalid token

        is_valid_token checks that the token provided by the form matches
        token described in the settings file. This function call should
        return false.
        """
        builder = EnvironBuilder(method='POST', data={'tokn': 'imarobot'})
        env = builder.get_environ()
        req = Request(env)
        self.assertFalse(is_valid_token(req))

    def test_rate_limiter_valid_rate(self):
        """
        Tests rate limiter with a valid rate
        """
        builder = EnvironBuilder(method='POST', data={'name': 'Valid Guy',
                                        'email': 'example@osuosl.org',
                                        'hidden': '',
                                        'tokn': TOKN })
        rater.reset_rate()
        for i in range(CEILING - 1):
            env = builder.get_environ()
            req = Request(env)
            app = Forms()
            resp = app.on_form_page(req)
            # Avoid duplicate form error
            builder.form['name'] = str(i) + builder.form['name']

        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(app.error)

    def test_rate_limiter_invalid_rate(self):
        """
        Tests rate limiter with an invalid rate
        """
        builder = EnvironBuilder(method='POST', data={'name': 'Valid Guy',
                                        'email': 'example@osuosl.org',
                                        'hidden': '',
                                        'tokn': TOKN })
        rater.reset_rate()
        for i in range(CEILING + 1):
            env = builder.get_environ()
            req = Request(env)
            app = Forms()
            resp = app.on_form_page(req)
            # Avoid duplicate form error
            builder.form['name'] = str(i) + builder.form['email']

        self.assertEqual(resp.status_code, 429)
        self.assertEqual(app.error, 'Too Many Requests')



if __name__ == '__main__':
    unittest.main()
