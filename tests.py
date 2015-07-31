import smtplib
import unittest
import werkzeug
from werkzeug.wrappers import Request
from werkzeug.test import EnvironBuilder
from mock import Mock, patch
from email.mime.text import MIMEText
from conf import TOKN, EMAIL, CEILING
import request_handler as handler


class TestFormsender(unittest.TestCase):

    def test_create_msg_with_content(self):
        """
        Tests create_msg with content in the POST request

        Checks that each element in the request is returned create_msg
        """
        builder = EnvironBuilder(method='POST',
                                 data={'foo': 'this is some text',
                                       'file': 'my file contents',
                                       'test': 'test.txt',
                                       'redirect': 'http://www.example.com'})
        env = builder.get_environ()
        req = Request(env)
        self.assertEqual(handler.create_msg(req)['foo'], builder.form['foo'])
        self.assertEqual(handler.create_msg(req)['file'], builder.form['file'])
        self.assertEqual(handler.create_msg(req)['test'], builder.form['test'])

    def test_create_msg_no_content(self):
        """
        Tests create_msg with no content in the POST request

        Checks that create_msg returns None
        """
        builder = EnvironBuilder(method='POST', data={})
        env = builder.get_environ()
        req = Request(env)
        self.assertIsNone(handler.create_msg(req))

    def test_create_msg_with_content_get_method(self):
        """
        Tests create_msg with content in a GET request

        Checks that create_msg returns None
        """
        builder = EnvironBuilder(method='GET',
                                 data={'foo': 'this is some text',
                                       'file': 'my file contents',
                                       'test': 'test.txt'})
        env = builder.get_environ()
        req = Request(env)
        self.assertIsNone(handler.create_msg(req))

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
                                       'last_name': '',
                                       'tokn': TOKN,
                                       'redirect': 'http://www.example.com'})
        env = builder.get_environ()
        req = Request(env)

        # Construct message for assertion
        msg = handler.create_msg(req)
        msg_send = MIMEText(str(msg))
        msg_from = handler.set_mail_from(msg)
        msg_subj = handler.set_mail_subject(msg)
        msg_send['Subject'] = msg_subj

        # Mock sendmail function so it doesn't send an actual email
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')

        # Call send_email and assert sendmail was called correctly
        handler.create_app()
        handler.send_email(msg, msg_from, msg_subj)
        smtplib.SMTP.sendmail.assert_called_with(msg_from,
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
                                       'last_name': '',
                                       'tokn': TOKN,
                                       'redirect': 'http://www.example.com'})
        env = builder.get_environ()
        req = Request(env)
        # Mock external validate_email so returns true in Travis
        mock_validate_email.return_value = True

        app = handler.create_app()
        # Mock sendmail function so it doesn't send an actual email
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')
        app.on_form_page(req)
        self.assertIsNone(app.error)

    @patch('request_handler.validate_email')
    def test_validations_invalid_name(self, mock_validate_email):
        """
        Tests the form validation with an invalid name.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        Invalid name field causes an 'Invalid Name' error.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': '   ',
                                       'email': 'example@osuosl.org',
                                       'last_name': '',
                                       'tokn': TOKN,
                                       'redirect': 'http://www.example.com'})
        env = builder.get_environ()
        req = Request(env)
        # Mock external validate_email so returns true in Travis
        mock_validate_email.return_value = True
        app = handler.create_app()
        # Mock sendmail function so it doesn't send an actual email
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')
        app.on_form_page(req)
        self.assertEqual(app.error, 'Invalid Name')

    @patch('request_handler.validate_email')
    def test_validations_invalid_email(self, mock_validate_email):
        """
        Tests the form validation with an invalid email.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        Invalid email field causes an 'Invalid Email' error.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'invalid@example.com',
                                       'last_name': '',
                                       'tokn': TOKN,
                                       'redirect': 'http://www.example.com'})
        env = builder.get_environ()
        req = Request(env)
        # Mock external validate_email so returns false in Travis
        mock_validate_email.return_value = False
        app = handler.create_app()
        # Mock sendmail function so it doesn't send an actual email
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')
        app.on_form_page(req)
        self.assertEqual(app.error, 'Invalid Email')

    @patch('request_handler.validate_email')
    def test_validations_invalid_hidden(self, mock_validate_email):
        """
        Tests the form validation with content in the hidden last_name field.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        Content in the hidden last_name field causes an 'Improper Form
        Submission' error.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'last_name': '!',
                                       'tokn': TOKN,
                                       'redirect': 'http://www.example.com'})
        env = builder.get_environ()
        req = Request(env)
        # Mock external validate_email so returns true in Travis
        mock_validate_email.return_value = True
        app = handler.create_app()
        # Mock sendmail function so it doesn't send an actual email
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')
        app.on_form_page(req)
        self.assertEqual(app.error, 'Improper Form Submission')

    @patch('request_handler.validate_email')
    def test_validations_invalid_token(self, mock_validate_email):
        """
        Tests the form validation with an invalid token.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        An invalid token causes the 'Improper Form Submission' error.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'last_name': '',
                                       'tokn': 'evilrobot',
                                       'redirect': 'http://www.example.com'})
        env = builder.get_environ()
        req = Request(env)
        # Mock external validate_email so returns true in Travis
        mock_validate_email.return_value = True
        app = handler.create_app()
        # Mock sendmail function so it doesn't send an actual email
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')
        app.on_form_page(req)
        self.assertEqual(app.error, 'Improper Form Submission')

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
        # Mock external validate_email so returns true in Travis
        mock_validate_email.return_value = True

        self.assertTrue(handler.is_valid_email(req))

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
        self.assertFalse(handler.is_valid_email(req))

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
        self.assertTrue(handler.validate_name(req))

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
        self.assertFalse(handler.validate_name(req))

    def test_is_hidden_field_empty_empty(self):
        """
        Tests is_hidden_field_empty with 'last_name' field empty

        is_hidden_field_empty checks that the last_name field in the form
        is empty. This function call should return true.
        """
        builder = EnvironBuilder(method='POST', data={'last_name': ''})
        env = builder.get_environ()
        req = Request(env)
        self.assertTrue(handler.is_hidden_field_empty(req))

    def test_is_hidden_field_empty_full(self):
        """
        Tests is_hidden_field_empty with contents in 'last_name' field

        is_hidden_field_empty checks that the last_name field in the form
        is empty. This function call should return false.
        """
        builder = EnvironBuilder(method='POST', data={'last_name': 'nope'})
        env = builder.get_environ()
        req = Request(env)
        self.assertFalse(handler.is_hidden_field_empty(req))

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
        self.assertTrue(handler.is_valid_token(req))

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
        self.assertFalse(handler.is_valid_token(req))

    @patch('request_handler.validate_email')
    def test_rate_limiter_valid_rate(self, mock_validate_email):
        """
        Tests rate limiter with a valid rate
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'last_name': '',
                                       'tokn': TOKN,
                                       'redirect': 'http://www.example.com'})
        # Mock validate email so returns true in Travis
        mock_validate_email.return_value = True
        # Mock sendmail function so it doesn't send an actual email
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')
        for i in range(CEILING - 1):
            env = builder.get_environ()
            req = Request(env)
            app = handler.create_app()
            resp = app.on_form_page(req)
            # Avoid duplicate form error
            builder.form['name'] = str(i) + builder.form['name']

        self.assertEqual(resp.status_code, 302)
        self.assertIsNone(app.error)

    @patch('request_handler.validate_email')
    def test_rate_limiter_invalid_rate(self, mock_validate_email):
        """
        Tests rate limiter with an invalid rate
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'last_name': '',
                                       'tokn': TOKN,
                                       'redirect': 'http://www.example.com'})
        # Mock validate email so returns true in Travis
        mock_validate_email.return_value = True
        env = builder.get_environ()
        req = Request(env)
        app = handler.create_app()
        # Mock sendmail function so it doesn't send an actual email
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')
        for i in range(CEILING + 1):
            app.on_form_page(req)
            # Avoid duplicate form error
            builder.form['name'] = str(i) + builder.form['email']

        self.assertEqual(app.error, 'Too Many Requests')

    @patch('request_handler.validate_email')
    def test_redirect_url_valid_data(self, mock_validate_email):
        """
        Tests the user is redirected to appropriate location
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)

        # Mock validate email so returns true in Travis
        mock_validate_email.return_value = True

        # Create app and mock redirect
        app = handler.create_app()
        werkzeug.utils.redirect = Mock('werkzeug.utils.redirect')
        # Mock sendmail function so it doesn't send an actual email
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')
        app.on_form_page(req)

        werkzeug.utils.redirect.assert_called_with('http://www.example.com',
                                                   code=302)

    @patch('request_handler.validate_email')
    def test_redirect_url_error_1(self, mock_validate_email):
        """
        Tests the user is redirected to appropriate location
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'nope@example.com',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)

        # Mock validate email so returns false in Travis
        # Not technically necessary because this will return false in Travis
        # regardless since it can't find the SMTP server, but kept here for
        # consistency
        mock_validate_email.return_value = False

        # Create app and mock redirect
        app = handler.create_app()
        werkzeug.utils.redirect = Mock('werkzeug.utils.redirect')
        # Mock sendmail function so it doesn't send an actual email
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')
        app.on_form_page(req)

        werkzeug.utils.redirect.assert_called_with(
            'http://www.example.com?error=1&message=Invalid+Email',
            code=302)

    @patch('request_handler.validate_email')
    def test_redirect_url_error_2(self, mock_validate_email):
        """
        Tests the user is redirected to appropriate location
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': '',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)

        # Mock validate email so returns true in Travis
        mock_validate_email.return_value = True

        # Create app and mock redirect
        app = handler.create_app()
        werkzeug.utils.redirect = Mock('werkzeug.utils.redirect')
        # Mock sendmail function so it doesn't send an actual email
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')
        app.on_form_page(req)

        werkzeug.utils.redirect.assert_called_with(
            'http://www.example.com?error=2&message=Invalid+Name',
            code=302)

    @patch('request_handler.validate_email')
    def test_redirect_url_error_3(self, mock_validate_email):
        """
        Tests the user is redirected to appropriate location
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '!',
                                       'tokn': 'wrong token'})
        env = builder.get_environ()
        req = Request(env)

        # Mock validate email so returns true in Travis
        mock_validate_email.return_value = True

        # Create app and mock redirect
        app = handler.create_app()
        werkzeug.utils.redirect = Mock('werkzeug.utils.redirect')
        # Mock sendmail function so it doesn't send an actual email
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')
        app.on_form_page(req)

        werkzeug.utils.redirect.assert_called_with(
            'http://www.example.com?error=3&message=Improper+Form+Submission',
            code=302)

    @patch('request_handler.validate_email')
    def test_redirect_url_error_4(self, mock_validate_email):
        """
        Tests the user is redirected to appropriate location
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)

        # Mock validate email so returns true in Travis
        mock_validate_email.return_value = True
        app = handler.create_app()
        werkzeug.utils.redirect = Mock('werkzeug.utils.redirect')
        # Mock sendmail function so it doesn't send an actual email
        smtplib.SMTP.sendmail = Mock('smtplib.SMTP.sendmail')
        for i in range(CEILING + 1):
            app.on_form_page(req)
            # Avoid duplicate form error
            builder.form['name'] = str(i) + builder.form['name']

        werkzeug.utils.redirect.assert_called_with(
            'http://www.example.com?error=4&message=Too+Many+Requests',
            code=302)

    def test_strip_incoming_redirect_query(self):
        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'www.example.com?mal=param',
                                       'last_name': '',
                                       'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)
        message = handler.create_msg(req)
        self.assertEqual(message['redirect'], 'www.example.com')

    def test_strip_incoming_redirect_no_query(self):
        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'www.example.com',
                                       'last_name': '',
                                       'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)
        message = handler.create_msg(req)
        self.assertEqual(message['redirect'], builder.form['redirect'])

    def test_format_message(self):
        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'some_field': ("This is multi line and "
                                                      "should not be on the "
                                                      "same line as the title"),
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)
        target_message = ("Contact:\n"
                          "--------\n"
                          "NAME:   Valid Guy\n"
                          "EMAIL:   example@osuosl.org\n\n"
                          "Information:\n"
                          "------------\n"
                          "Some Field:\n\n"
                          "This is multi line and should not be on the same "
                          "line as the title\n\n")
        message = handler.create_msg(req)
        formatted_message = handler.format_message(message)
        self.assertEqual(formatted_message, target_message)

    def test_set_mail_subject_with_subj(self):
        """
        set_mail_subject(message) returns the string in message['mail_subject']
        when it is present, otherwise it returns 'Form Submission'
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'mail_subject': 'Test Form',
                                       'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        subject = handler.set_mail_subject(message)
        self.assertEqual(subject, 'Test Form')

    def test_set_mail_subject_with_nothing(self):
        """
        set_mail_subject(message) returns the string in message['mail_subject']
        when it is present, otherwise it returns 'Form Submission'
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        subject = handler.set_mail_subject(message)
        self.assertEqual(subject, 'Form Submission')

    def test_set_mail_subject_with_key_only(self):
        """
        set_mail_subject(message) returns the string in message['mail_subject']
        when it is present, otherwise it returns 'Form Submission'
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'mail_subject': '',
                                       'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        subject = handler.set_mail_subject(message)
        self.assertEqual(subject, 'Form Submission')

    def test_set_mail_from_with_from(self):
        """
        set_mail_from(message) returns the string in message['mail_from'] when
        it is present, otherwise it returns 'Form'
        """
        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'mail_from': 'Test Form at example.com',
                                       'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        mail_from = handler.set_mail_from(message)
        self.assertEqual(mail_from, 'Test Form at example.com')

    def test_set_mail_from_with_nothing(self):
        """
        set_mail_from(message) returns the string in message['mail_from'] when
        it is present, otherwise it returns 'Form'
        """
        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        mail_from = handler.set_mail_from(message)
        self.assertEqual(mail_from, 'Form')

    def test_set_mail_from_with_key_only(self):
        """
        set_mail_from(message) returns the string in message['mail_from'] when
        it is present, otherwise it returns 'Form'
        """
        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'mail_from': '',
                                       'tokn': TOKN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        mail_from = handler.set_mail_from(message)
        self.assertEqual(mail_from, 'Form')


if __name__ == '__main__':
    unittest.main()
