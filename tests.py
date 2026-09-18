import unittest
import werkzeug
import base64
import json
from io import BytesIO
from datetime import datetime, timedelta
from werkzeug.wrappers import Request
from werkzeug.test import EnvironBuilder, Client
from werkzeug.datastructures import MultiDict
from mock import Mock, patch
import conf
import time
import request_handler as handler
import captcha
import altcha
import rt


def setUpModule():
    """Give every test a configured captcha provider"""
    # conf.py reads these from the environment, so a developer running the
    # suite without them set would otherwise hit the startup check.
    for name, value in (('TURNSTILE_SECRET', 'test-turnstile-secret'),
                        ('ALTCHA_HMAC_KEY', 'test-altcha-key'),
                        ('RECAPTCHA_SECRET', 'test-recaptcha-secret'),
                        ('CAPTCHA_ALLOWED_HOSTNAMES', None),
                        ('TRUSTED_PROXY_COUNT', 0)):
        setattr(conf, name, value)


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
        self.assertEqual(handler.create_msg(req), None)

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
        self.assertEqual(handler.create_msg(req), None)

    def test_send_email(self):
        """
        Tests send_email

        send_email returns True when it successfully sends an email to a
        default address and errors out when unsuccessful.
        """
        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'last_name': '',
                                       'token': conf.TOKEN,
                                       'redirect': 'http://www.example.com'})
        env = builder.get_environ()
        req = Request(env)

        # Construct message for assertion
        msg = handler.create_msg(req)
        msg_subj = handler.set_mail_subject(msg)

        # Mock create_ticket function
        with patch('rt.rest2.Rt') as mock_rt:
            instance = mock_rt.return_value
            # Call send_ticket and assert ticket creation returns new ticket ID
            handler.create_app()
            handler.send_ticket(msg, msg_subj)
            instance.create_ticket.assert_called_with(queue='General',
                                                      subject=msg_subj,
                                                      Requestor='noreply@osuosl.org',
                                                      content=msg)

    def test_extract_attachments(self):
        """
        Tests extract_attachments

        An uploaded file becomes an rt.rest2.Attachment carrying the original
        filename, content type, and bytes; empty file inputs are ignored.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'rfcfile': (BytesIO(b'proposal bytes'),
                                                   'proposal.pdf',
                                                   'application/pdf'),
                                       'emptyfile': (BytesIO(b''), '')})
        req = Request(builder.get_environ())

        attachments = handler.extract_attachments(req)

        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].file_name, 'proposal.pdf')
        self.assertEqual(attachments[0].file_type, 'application/pdf')
        self.assertEqual(attachments[0].file_content, b'proposal bytes')

    def test_send_ticket_with_attachments(self):
        """
        Tests send_ticket passes attachments through to create_ticket only when
        files are present.
        """
        attachment = rt.rest2.Attachment('proposal.pdf', 'application/pdf',
                                         b'proposal bytes')
        with patch('rt.rest2.Rt') as mock_rt:
            instance = mock_rt.return_value
            handler.send_ticket('body', 'subj', 'General',
                                'noreply@osuosl.org', [attachment])
            instance.create_ticket.assert_called_with(
                queue='General', subject='subj', content='body',
                Requestor='noreply@osuosl.org', attachments=[attachment])

    def test_extract_custom_fields(self):
        """
        Tests extract_custom_fields

        A declarative 'custom_fields' mapping turns form fields into an RT
        CustomFields dict; single values stay scalar, repeated values (e.g.
        checkbox groups) become a list, and consumed field names are returned.
        """
        builder = EnvironBuilder(method='POST',
                                 data=MultiDict([
                                     ('custom_fields',
                                      'CompanyName:companyname,'
                                      'WorkingGroups:workgroups'),
                                     ('companyname', 'OPF'),
                                     ('workgroups', 'AI'),
                                     ('workgroups', 'Hardware')]))
        req = Request(builder.get_environ())

        custom_fields, consumed = handler.extract_custom_fields(req)

        self.assertEqual(custom_fields['CompanyName'], 'OPF')
        self.assertEqual(custom_fields['WorkingGroups'], ['AI', 'Hardware'])
        self.assertEqual(consumed, {'companyname', 'workgroups'})

    def test_format_message_excludes_custom_fields(self):
        """
        Tests format_message leaves excluded (custom-field) source fields out of
        the ticket body.
        """
        msg = {'name': 'Valid Guy', 'email': 'example@osuosl.org',
               'companyname': 'OPF', 'message': 'hello'}
        body = handler.format_message(msg, exclude={'companyname'})
        self.assertNotIn('OPF', body)
        self.assertIn('hello', body)

    @patch('captcha.is_valid_captcha')
    @patch('request_handler.validate_email')
    def test_validations_valid_data(self, mock_validate_email,
                                    mock_recaptcha):
        """
        Tests the form validation with valid data.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'last_name': '',
                                       'token': conf.TOKEN,
                                       'redirect': 'http://www.example.com',
                                       'g-recaptcha-response': ''})
        env = builder.get_environ()
        req = Request(env)
        # Mock external services so they return valid in CI
        mock_validate_email.return_value = True
        mock_recaptcha.return_value = (True, 'test')
        app = handler.create_app()
        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt = Mock('rt.rest2.Rt')
        app.on_form_page(req)
        self.assertEqual(app.error, None)

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
                                       'token': conf.TOKEN,
                                       'redirect': 'http://www.example.com'})
        env = builder.get_environ()
        req = Request(env)
        # Mock external validate_email so returns true in Travis
        mock_validate_email.return_value = True
        app = handler.create_app()
        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt = Mock('rt.rest2.Rt')
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
                                       'token': conf.TOKEN,
                                       'redirect': 'http://www.example.com'})
        env = builder.get_environ()
        req = Request(env)
        # Mock external validate_email so returns false in Travis
        mock_validate_email.return_value = False
        app = handler.create_app()
        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt = Mock('rt.rest2.Rt')
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
                                       'token': conf.TOKEN,
                                       'redirect': 'http://www.example.com'})
        env = builder.get_environ()
        req = Request(env)
        # Mock external validate_email so returns true in Travis
        mock_validate_email.return_value = True
        app = handler.create_app()
        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt = Mock('rt.rest2.Rt')
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
                                       'token': 'evilrobot',
                                       'redirect': 'http://www.example.com'})
        env = builder.get_environ()
        req = Request(env)
        # Mock external validate_email so returns true in Travis
        mock_validate_email.return_value = True
        app = handler.create_app()
        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt = Mock('rt.rest2.Rt')
        app.on_form_page(req)
        self.assertEqual(app.error, 'Improper Form Submission')

    @patch('request_handler.validate_email')
    def test_validations_invalid_fields_to_join(self, mock_validate_email):
        """
        Tests the form validation with an invalid 'fields_to_join' field.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        An invalid token causes the 'Improper Form Submission' error.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'last_name': '',
                                       'token': conf.TOKEN,
                                       'redirect': 'http://www.example.com',
                                       'fields_to_join': 'name,missing,email'})
        env = builder.get_environ()
        req = Request(env)
        # Mock external validate_email so returns true in Travis
        mock_validate_email.return_value = True
        app = handler.create_app()
        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt = Mock('rt.rest2.Rt')
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
        Tests is_valid_token with TOKEN defined in conf.py

        is_valid_token checks that the token provided by the form matches
        token described in the settings file. This function call should
        return true.
        """
        builder = EnvironBuilder(method='POST', data={'token': conf.TOKEN})
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
        builder = EnvironBuilder(method='POST', data={'token': 'imarobot'})
        env = builder.get_environ()
        req = Request(env)
        self.assertFalse(handler.is_valid_token(req))

    @patch('captcha.is_valid_captcha')
    @patch('request_handler.validate_email')
    def test_rate_limiter_valid_rate(self, mock_validate_email,
                                     mock_recaptcha):
        """
        Tests rate limiter with a valid rate
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'last_name': '',
                                       'token': conf.TOKEN,
                                       'redirect': 'http://www.example.com',
                                       'g-recaptcha-response': ''})
        # Mock external services so they return valid in CI
        mock_validate_email.return_value = True
        mock_recaptcha.return_value = (True, 'test')
        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt = Mock('rt.rest2.Rt')
        app = handler.create_app()
        for i in range(conf.CEILING - 1):
            env = builder.get_environ()
            req = Request(env)
            resp = app.on_form_page(req)
            # Avoid duplicate form error
            builder.form['name'] = str(i) + builder.form['name']

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(app.error, None)

    @patch('request_handler.validate_email')
    def test_rate_limiter_invalid_rate(self, mock_validate_email):
        """
        Tests rate limiter with an invalid rate
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'last_name': '',
                                       'token': conf.TOKEN,
                                       'redirect': 'http://www.example.com',
                                       'g-recaptcha-response': ''})
        # Mock validate email so returns true in Travis
        mock_validate_email.return_value = True
        env = builder.get_environ()
        req = Request(env)
        app = handler.create_app()
        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt = Mock('rt.rest2.Rt')
        for i in range(conf.CEILING + 1):
            app.on_form_page(req)
            # Avoid duplicate form error
            builder.form['name'] = str(i) + builder.form['email']

        self.assertEqual(app.error, 'Too Many Requests')

    @patch('captcha.is_valid_captcha')
    @patch('request_handler.validate_email')
    def test_redirect_url_valid_data(self, mock_validate_email,
                                     mock_recaptcha):
        """
        Tests the user is redirected to appropriate location
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'token': conf.TOKEN,
                                       'g-recaptcha-response': ''})
        env = builder.get_environ()
        req = Request(env)

        # Mock external services so they return valid in CI
        mock_validate_email.return_value = True
        mock_recaptcha.return_value = (True, 'test')

        # Create app and mock redirect
        app = handler.create_app()
        werkzeug.utils.redirect = Mock('werkzeug.utils.redirect')
        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt = Mock('rt.rest2.Rt')
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
                                       'token': conf.TOKEN})
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
        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt = Mock('rt.rest2.Rt')
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
                                       'token': conf.TOKEN})
        env = builder.get_environ()
        req = Request(env)

        # Mock validate email so returns true in Travis
        mock_validate_email.return_value = True

        # Create app and mock redirect
        app = handler.create_app()
        werkzeug.utils.redirect = Mock('werkzeug.utils.redirect')
        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt = Mock('rt.rest2.Rt')
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
                                       'token': 'wrong token'})
        env = builder.get_environ()
        req = Request(env)

        # Mock validate email so returns true in Travis
        mock_validate_email.return_value = True

        # Create app and mock redirect
        app = handler.create_app()
        werkzeug.utils.redirect = Mock('werkzeug.utils.redirect')
        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt = Mock('rt.rest2.Rt')
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
                                       'token': conf.TOKEN,
                                       'g-recaptcha-response': ''})
        env = builder.get_environ()
        req = Request(env)

        # Mock validate email so returns true in Travis
        mock_validate_email.return_value = True
        app = handler.create_app()
        werkzeug.utils.redirect = Mock('werkzeug.utils.redirect')
        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt = Mock('rt.rest2.Rt')
        for i in range(conf.CEILING + 1):
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
                                       'token': conf.TOKEN})
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
                                       'token': conf.TOKEN})
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
                                       'token': conf.TOKEN})
        env = builder.get_environ()
        req = Request(env)
        target_message = ("Contact:\n"
                          "--------\n"
                          "NAME:   Valid Guy\n"
                          "EMAIL:   example@osuosl.org\n\n"
                          "Information:\n"
                          "------------\n"
                          "Some Field:\n"
                          "This is multi line and should not be on the same "
                          "line as the title\n\n")
        message = handler.create_msg(req)
        formatted_message = handler.format_message(message)
        self.assertEqual(formatted_message, target_message)

    def test_set_mail_subject_with_both_options(self):
        """
        set_mail_subject(message) returns the string
        "message['mail_subject_prefix']: message[message['mail_subject_key']"
        when both are available
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'mail_subject_prefix': 'Hosting',
                                       'mail_subject_key': 'project',
                                       'project': 'PGD',
                                       'token': conf.TOKEN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        self.assertEqual(handler.set_mail_subject(message), 'Hosting: PGD')

    def test_set_mail_subject_with_subj_prefix(self):
        """
        set_mail_subject(message) returns the string
        "message['mail_subject_prefix']" when it is the only field available
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'mail_subject_prefix': 'Hosting',
                                       'token': conf.TOKEN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        self.assertEqual(handler.set_mail_subject(message), 'Hosting')

    def test_set_mail_subject_with_subj_key(self):
        """
        set_mail_subject(message) returns the string
        "message[message['mail_subject_prefix']]" when it is the only field
        available
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'mail_subject_key': 'project',
                                       'project': 'PGD',
                                       'token': conf.TOKEN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        self.assertEqual(handler.set_mail_subject(message), 'PGD')

    def test_set_mail_subject_with_subj_key_missing(self):
        """
        set_mail_subject(message) returns the default string 'Form Submission'
        when no configuration fields are available
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'mail_subject_key': 'project',
                                       'token': conf.TOKEN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        self.assertEqual(handler.set_mail_subject(message), 'Form Submission')

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
                                       'token': conf.TOKEN})
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
                                       'token': conf.TOKEN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        subject = handler.set_mail_subject(message)
        self.assertEqual(subject, 'Form Submission')

    def test_send_to_address(self):
        """
        send_to_adress(message) returns the string in message['send_to']
        when it is present, otherwise it returns 'default'
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'send_to': 'support',
                                       'token': conf.TOKEN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        address = handler.send_to_address(message)
        self.assertEqual(address, 'support')

    def test_send_to_address_with_nothing(self):
        """
        send_to_adress(message) returns the string in message['send_to']
        when it is present, otherwise it returns 'OSLSupport'
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'token': conf.TOKEN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        address = handler.send_to_address(message)
        self.assertEqual(address, 'OSLSupport')

    def test_send_to_address_with_key_only(self):
        """
        send_to_adress(message) returns the string in message['send_to']
        when it is present, otherwise it returns 'OSLSupport'
        """

        # Build test environment
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'send_to': '',
                                       'token': conf.TOKEN})
        env = builder.get_environ()
        req = Request(env)
        # Create message from request and call set_mail_subject()
        message = handler.create_msg(req)
        address = handler.send_to_address(message)
        self.assertEqual(address, 'OSLSupport')

    @patch('captcha.is_valid_captcha')
    @patch('request_handler.validate_email')
    def test_same_submission(self, mock_validate_email, mock_recaptcha):
        """
        Tests that the same form is not sent twice.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'last_name': '',
                                       'token': conf.TOKEN,
                                       'redirect': 'http://www.example.com',
                                       'g-recaptcha-response': ''})

        env = builder.get_environ()

        # Mock create_ticket function so it doesn't send an actual ticket
        rt.rest2.Rt.create_ticket = Mock('rt.rest2.Rt.create_ticket')
        mock_validate_email.return_value = True
        mock_recaptcha.return_value = (True, 'test')

        # Create apps
        app = handler.create_app()

        # Will cause a duplicate with the last call because
        # first app.name = 'Valid Guy' = last app.name
        req = Request(env)
        app.on_form_page(req)
        self.assertEqual(app.error, None)

        # Update name so not a duplicate
        builder.form['name'] = 'Another Guy'
        env = builder.get_environ()
        req = Request(env)
        app.on_form_page(req)
        self.assertEqual(app.error, None)

        # Update name so not a duplicate
        builder.form['name'] = 'A Third Guy'
        env = builder.get_environ()
        req = Request(env)
        app.on_form_page(req)
        self.assertEqual(app.error, None)

        # Duplicate with first app because
        # first app.name = 'Valid Guy' = this app.name
        builder.form['name'] = 'Valid Guy'
        env = builder.get_environ()
        req = Request(env)
        app.on_form_page(req)

        self.assertEqual(app.error, 'Duplicate Request')

    @patch('request_handler.validate_email')
    def test_send_email_default(self, mock_validate_email):
        """
        Tests that the form is sent to the correct default address when
        the 'send_to' field is set to an empty string.

        Returns true if the form has been sent to support@osuosl.org
        Errors out if unsuccessful
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'send_to': '',
                                       'last_name': '',
                                       'token': conf.TOKEN,
                                       'redirect': 'http://www.example.com'})
        env = builder.get_environ()
        req = Request(env)

        # Construct message for assertion
        msg = handler.create_msg(req)
        msg_subj = handler.set_mail_subject(msg)

        # Mock create_ticket function
        with patch('rt.rest2.Rt') as mock_rt:
            instance = mock_rt.return_value
            handler.create_app()

            # Call send_ticket and assert ticket creation returns new ticket ID
            handler.send_ticket(msg, msg_subj)
            instance.create_ticket.assert_called_with(queue='General',
                                                      subject=msg_subj,
                                                      Requestor='noreply@osuosl.org',
                                                      content=msg)

    def test_server_status_view_responds_OK_on_GET(self):
        """
        Tests that the view for health check by monitoring software works.

        Will return HTTP 200 when sent a GET request

        """
        builder = EnvironBuilder(method='GET')

        app = handler.create_app()
        env = builder.get_environ()
        req = Request(env)
        resp = app.on_server_status(req)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(app.error, None)

    def test_server_status_view_responds_with_HTTP_400_on_non_GET_request(self):
        """
        Tests that the view for health check by monitoring software works.

        Will return HTTP 400 when sent anything other than a GET request

        """
        for m in [
                'POST',
                'OPTIONS',
                'PATCH',
                'HEAD',
                'PUT',
                'DELETE',
                'TRACE'
                ]:
            builder = EnvironBuilder(method=m)

            app = handler.create_app()
            env = builder.get_environ()
            req = Request(env)
            resp = app.on_server_status(req)

            self.assertEqual(resp.status_code, 400)
            self.assertEqual(app.error, None)

    def test_string_comp_from_fields_to_join(self):
        """
        Tests that values can be pulled from form fields and composed into a
        string to be included in the body of the email.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'some_field': "This is some info.",
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'token': conf.TOKEN,
                                       'fields_to_join': 'name,email,date,some_field'})
        env = builder.get_environ()
        req = Request(env)
        target_message = ("Contact:\n"
                          "--------\n"
                          "NAME:   Valid Guy\n"
                          "EMAIL:   example@osuosl.org\n\n"
                          "Information:\n"
                          "------------\n"
                          "Fields To Join:\n"
                          "Valid Guy:example@osuosl.org:%s:This is some info.\n\n"
                          "Some Field:\n"
                          "This is some info.\n\n" % str(int(time.time())))

        message = handler.create_msg(req)
        formatted_message = handler.format_message(message)
        self.assertEqual(formatted_message, target_message)

    def test_string_comp_with_fields_to_join_name(self):
        """
        Tests that value from fields_to_join_name field can be used as keys for
        fields_to_join data
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'example@osuosl.org',
                                       'some_field': "This is some info.",
                                       'redirect': 'http://www.example.com',
                                       'last_name': '',
                                       'token': conf.TOKEN,
                                       'fields_to_join_name': 'With New Field Name',
                                       'fields_to_join': 'name,email,date,some_field'})
        env = builder.get_environ()
        req = Request(env)
        target_message = ("Contact:\n"
                          "--------\n"
                          "NAME:   Valid Guy\n"
                          "EMAIL:   example@osuosl.org\n\n"
                          "Information:\n"
                          "------------\n"
                          "Some Field:\n"
                          "This is some info.\n\n"
                          "With New Field Name:\n"
                          "Valid Guy:example@osuosl.org:"
                          "%s:This is some info.\n\n" % str(int(time.time())))

        message = handler.create_msg(req)
        formatted_message = handler.format_message(message)
        self.assertEqual(formatted_message, target_message)

    # WSGI dispatch / routing

    def test_wsgi_server_status_ok(self):
        """
        A GET to /server-status routed through the full WSGI stack
        (__call__ -> wsgi_app -> dispatch_request) returns HTTP 200.
        """
        app = handler.create_app(with_static=False)
        client = Client(app)
        resp = client.get('/server-status')
        self.assertEqual(resp.status_code, 200)

    def test_wsgi_unknown_route_returns_404(self):
        """
        A request to an unmapped URL raises an HTTPException that
        dispatch_request catches and returns to the client as a 404.
        """
        app = handler.create_app(with_static=False)
        client = Client(app)
        resp = client.get('/does-not-exist')
        self.assertEqual(resp.status_code, 404)

    def test_on_form_page_get_renders_error(self):
        """
        A GET (non-POST) to the form page with otherwise valid fields falls
        through to the local error page (HTTP 400).
        """
        app = handler.create_app()
        req = Request(EnvironBuilder(method='GET').get_environ())
        with patch.object(handler.Forms, 'are_fields_invalid',
                          return_value=False):
            resp = app.on_form_page(req)
        self.assertEqual(resp.status_code, 400)

    def test_handle_no_error_empty_message_renders_error(self):
        """
        When create_msg yields no message, handle_no_error renders the local
        error page instead of creating a ticket.
        """
        app = handler.create_app()
        req = Request(EnvironBuilder(method='POST', data={}).get_environ())
        with patch('request_handler.create_msg', return_value=None):
            resp = app.handle_no_error(req)
        self.assertEqual(resp.status_code, 400)

    def test_handle_no_error_forwards_attachment_and_custom_fields(self):
        """
        handle_no_error builds the ticket with the requested queue, uploaded
        attachments, and declared custom fields, then redirects.
        """
        builder = EnvironBuilder(method='POST', data={
            'name': 'Valid Guy',
            'email': 'example@osuosl.org',
            'redirect': 'http://www.example.com',
            'send_to': 'SomeQueue',
            'custom_fields': 'CompanyName:companyname',
            'companyname': 'OPF',
            'attachment': (BytesIO(b'file data'), 'doc.txt'),
        })
        req = Request(builder.get_environ())
        app = handler.create_app()
        with patch('rt.rest2.Rt') as mock_rt:
            instance = mock_rt.return_value
            resp = app.handle_no_error(req)

        self.assertEqual(resp.status_code, 302)
        _, kwargs = instance.create_ticket.call_args
        self.assertEqual(kwargs['queue'], 'SomeQueue')
        self.assertEqual(kwargs['CustomFields'], {'CompanyName': 'OPF'})
        self.assertEqual(len(kwargs['attachments']), 1)
        self.assertEqual(kwargs['attachments'][0].file_name, 'doc.txt')

    # Attachment / custom-field edge cases

    def test_extract_attachments_skips_empty_content(self):
        """A file input with a name but no content is not attached."""
        req = Request(EnvironBuilder(method='POST', data={
            'f': (BytesIO(b''), 'empty.txt')}).get_environ())
        self.assertEqual(handler.extract_attachments(req), [])

    def test_extract_custom_fields_skips_invalid_entries(self):
        """
        Mapping entries without a colon, or with an empty CF name or field
        name, are ignored entirely. An entry pointing at an empty form field
        sets no custom field, but the field is still consumed so an unfilled
        optional field does not show up as a blank line in the ticket body.
        """
        req = Request(EnvironBuilder(method='POST', data=MultiDict([
            ('custom_fields',
             'NoColon,:headless,Tailless:,Good:companyname,Empty:blankfield'),
            ('companyname', 'OPF'),
            ('blankfield', '')])).get_environ())
        custom_fields, consumed = handler.extract_custom_fields(req)
        self.assertEqual(custom_fields, {'Good': 'OPF'})
        self.assertEqual(consumed, {'companyname', 'blankfield'})

    # Controller reset branches

    def test_controller_rate_violation_resets_after_a_second(self):
        """
        After more than a second elapses, is_rate_violation resets the rate
        counter and reports no violation.
        """
        controller = handler.Controller()
        controller.start_time = datetime.now() - timedelta(seconds=2)
        controller.rate = conf.CEILING + 5
        self.assertFalse(controller.is_rate_violation())
        self.assertEqual(controller.rate, 0)

    def test_controller_duplicate_resets_after_timeout(self):
        """
        Once DUPLICATE_CHECK_TIME has passed, the hash list is reset and the
        submission is no longer considered a duplicate.
        """
        controller = handler.Controller()
        controller.hash_list = ['oldhash']
        controller.start_time_hash = (
            datetime.now()
            - timedelta(seconds=conf.DUPLICATE_CHECK_TIME + 1))
        self.assertFalse(controller.is_duplicate('whatever'))
        self.assertEqual(controller.hash_list, [])


class TestCaptcha(unittest.TestCase):
    """
    Tests the pluggable captcha backends in captcha.py and the pieces of the
    request handler that use them.
    """

    KEY = 'unit-test-altcha-key'

    def setUp(self):
        # Every provider configured unless a test says otherwise
        self.settings = patch.multiple(conf, TURNSTILE_SECRET='ts-secret',
                                       ALTCHA_HMAC_KEY=self.KEY,
                                       RECAPTCHA_SECRET='rc-secret',
                                       CAPTCHA_ALLOWED_HOSTNAMES=None,
                                       ALTCHA_ALGORITHM='SHA-256',
                                       ALTCHA_COST=1, ALTCHA_EXPIRES=600,
                                       RECAPTCHA_MIN_SCORE=0.5, create=True)
        self.settings.start()
        self.addCleanup(self.settings.stop)
        self.controller = handler.Controller()

    @staticmethod
    def request(**fields):
        builder = EnvironBuilder(method='POST', data=fields,
                                 environ_base={'REMOTE_ADDR': '203.0.113.5'})
        return Request(builder.get_environ())

    @staticmethod
    def siteverify(body, status=200):
        """A fake requests.post returning the given JSON body"""
        response = Mock()
        response.json.return_value = body
        if status >= 400:
            response.raise_for_status.side_effect = \
                handler.captcha.requests.HTTPError(str(status))
        return Mock(return_value=response)

    def solved_payload(self, **challenge_kwargs):
        """A solved ALTCHA payload for a challenge issued with the test key"""
        challenge_kwargs.setdefault('expires_at', int(time.time()) + 60)
        challenge_kwargs.setdefault('hmac_secret', self.KEY)
        challenge = altcha.create_challenge('SHA-256', 1, **challenge_kwargs)
        solution = altcha.solve_challenge(challenge)
        return altcha.Payload(challenge, solution).to_base64()

    # Provider selection

    def test_no_captcha_field_is_rejected(self):
        valid, provider = captcha.is_valid_captcha(self.request(name='x'),
                                                   self.controller)
        self.assertEqual((valid, provider), (False, None))

    def test_empty_captcha_field_is_rejected(self):
        req = self.request(**{'cf-turnstile-response': ''})
        self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                         (False, None))

    def test_unconfigured_provider_is_rejected(self):
        with patch.object(conf, 'TURNSTILE_SECRET', None):
            with patch('captcha.session.post') as post:
                req = self.request(**{'cf-turnstile-response': 'tok'})
                self.assertEqual(captcha.is_valid_captcha(req,
                                                          self.controller),
                                 (False, 'turnstile'))
                post.assert_not_called()

    def test_configured_providers(self):
        self.assertEqual(captcha.configured_providers(),
                         ['turnstile', 'altcha', 'recaptcha'])
        with patch.multiple(conf, TURNSTILE_SECRET=None,
                            RECAPTCHA_SECRET=''):
            self.assertEqual(captcha.configured_providers(), ['altcha'])

    def test_create_app_requires_a_provider(self):
        with patch.multiple(conf, TURNSTILE_SECRET=None, ALTCHA_HMAC_KEY=None,
                            RECAPTCHA_SECRET=None):
            with self.assertRaises(RuntimeError):
                handler.create_app()

    # Turnstile

    def test_turnstile_success(self):
        post = self.siteverify({'success': True, 'hostname': 'osuosl.org'})
        with patch('captcha.session.post', post):
            req = self.request(**{'cf-turnstile-response': 'tok'})
            self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                             (True, 'turnstile'))
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], captcha.TURNSTILE_VERIFY_URL)
        self.assertEqual(kwargs['data']['secret'], 'ts-secret')
        self.assertEqual(kwargs['data']['response'], 'tok')
        self.assertEqual(kwargs['data']['remoteip'], req.remote_addr)
        self.assertEqual(kwargs['timeout'], captcha.VERIFY_TIMEOUT)

    def test_turnstile_failure(self):
        post = self.siteverify({'success': False,
                                'error-codes': ['invalid-input-response']})
        with patch('captcha.session.post', post):
            req = self.request(**{'cf-turnstile-response': 'tok'})
            self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                             (False, 'turnstile'))

    def test_turnstile_network_error_fails_closed(self):
        post = Mock(side_effect=captcha.requests.ConnectionError('down'))
        with patch('captcha.session.post', post):
            req = self.request(**{'cf-turnstile-response': 'tok'})
            self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                             (False, 'turnstile'))

    def test_turnstile_http_error_fails_closed(self):
        post = self.siteverify({}, status=500)
        with patch('captcha.session.post', post):
            req = self.request(**{'cf-turnstile-response': 'tok'})
            self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                             (False, 'turnstile'))

    def test_hostname_allowlist(self):
        req = self.request(**{'cf-turnstile-response': 'tok'})
        with patch.object(conf, 'CAPTCHA_ALLOWED_HOSTNAMES',
                          'osuosl.org, www.osuosl.org'):
            post = self.siteverify({'success': True,
                                    'hostname': 'WWW.osuosl.org'})
            with patch('captcha.session.post', post):
                self.assertTrue(captcha.is_valid_captcha(req,
                                                         self.controller)[0])
            post = self.siteverify({'success': True,
                                    'hostname': 'evil.example'})
            with patch('captcha.session.post', post):
                self.assertFalse(captcha.is_valid_captcha(req,
                                                          self.controller)[0])
            post = self.siteverify({'success': True})
            with patch('captcha.session.post', post):
                self.assertFalse(captcha.is_valid_captcha(req,
                                                          self.controller)[0])

    # reCAPTCHA

    def test_recaptcha_success(self):
        post = self.siteverify({'success': True})
        with patch('captcha.session.post', post):
            req = self.request(**{'g-recaptcha-response': 'tok'})
            self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                             (True, 'recaptcha'))
        args, kwargs = post.call_args
        self.assertEqual(args[0], captcha.RECAPTCHA_VERIFY_URL)
        self.assertEqual(kwargs['data']['secret'], 'rc-secret')

    def test_recaptcha_v3_score_threshold(self):
        req = self.request(**{'g-recaptcha-response': 'tok'})
        with patch('captcha.session.post',
                   self.siteverify({'success': True, 'score': 0.3})):
            self.assertFalse(captcha.is_valid_captcha(req,
                                                      self.controller)[0])
        with patch('captcha.session.post',
                   self.siteverify({'success': True, 'score': 0.9})):
            self.assertTrue(captcha.is_valid_captcha(req,
                                                     self.controller)[0])

    def test_recaptcha_failure(self):
        with patch('captcha.session.post',
                   self.siteverify({'success': False})):
            req = self.request(**{'g-recaptcha-response': 'tok'})
            self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                             (False, 'recaptcha'))

    # ALTCHA

    def test_altcha_round_trip(self):
        req = self.request(altcha=self.solved_payload())
        self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                         (True, 'altcha'))

    def test_altcha_replay_is_rejected(self):
        payload = self.solved_payload()
        req = self.request(altcha=payload)
        self.assertTrue(captcha.is_valid_captcha(req, self.controller)[0])
        # A challenge is only spent once the submission produced a ticket
        self.controller.commit_challenge()
        # Same challenge again, even in a different submission
        req = self.request(altcha=payload, name='someone else')
        self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                         (False, 'altcha'))
        # A fresh challenge is still fine
        req = self.request(altcha=self.solved_payload())
        self.assertTrue(captcha.is_valid_captcha(req, self.controller)[0])

    def test_altcha_expired_is_rejected(self):
        payload = self.solved_payload(expires_at=int(time.time()) - 1)
        req = self.request(altcha=payload)
        self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                         (False, 'altcha'))

    def test_altcha_no_expiry_is_rejected(self):
        payload = self.solved_payload(expires_at=None)
        req = self.request(altcha=payload)
        self.assertFalse(captcha.is_valid_captcha(req, self.controller)[0])

    def test_altcha_wrong_key_is_rejected(self):
        payload = self.solved_payload(hmac_secret='someone-elses-key')
        req = self.request(altcha=payload)
        self.assertFalse(captcha.is_valid_captcha(req, self.controller)[0])

    def test_altcha_malformed_payload_is_rejected(self):
        for payload in ('garbage!', 'e30=', 'W10='):
            req = self.request(altcha=payload)
            self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                             (False, 'altcha'))

    def test_controller_forgets_expired_challenges(self):
        self.assertFalse(self.controller.is_replayed_challenge(
            'old', time.time() - 1))
        self.controller.commit_challenge()
        self.assertFalse(self.controller.is_replayed_challenge(
            'new', time.time() + 60))
        self.controller.commit_challenge()
        self.assertNotIn('old', self.controller.seen_challenges)
        self.assertTrue(self.controller.is_replayed_challenge(
            'new', time.time() + 60))

    def test_altcha_challenge_endpoint(self):
        client = Client(handler.create_app())
        resp = client.get('/altcha')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'], '*')
        self.assertEqual(resp.headers['Cache-Control'], 'no-store')
        body = resp.get_json()
        self.assertIn('signature', body)
        self.assertEqual(body['parameters']['algorithm'], 'SHA-256')
        self.assertGreater(body['parameters']['expiresAt'], time.time())
        # Issued challenges verify with the configured key
        challenge = altcha.Challenge.from_dict(body)
        solution = altcha.solve_challenge(challenge)
        payload = altcha.Payload(challenge, solution).to_base64()
        self.assertTrue(altcha.verify_solution(payload, self.KEY).verified)
        # Two challenges are never the same
        self.assertNotEqual(body['parameters']['nonce'],
                            client.get('/altcha').get_json()
                            ['parameters']['nonce'])

    def test_altcha_challenge_endpoint_options_and_unconfigured(self):
        client = Client(handler.create_app())
        resp = client.options('/altcha')
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'], '*')
        self.assertEqual(client.post('/altcha').status_code, 405)
        with patch.object(conf, 'ALTCHA_HMAC_KEY', None):
            self.assertEqual(client.get('/altcha').status_code, 404)

    # Request handler integration

    @patch('request_handler.validate_email')
    def test_form_page_rejects_bad_captcha_with_error_6(self,
                                                        mock_validate_email):
        mock_validate_email.return_value = True
        req = self.request(name='Valid Guy', email='example@osuosl.org',
                           last_name='', token=conf.TOKEN,
                           redirect='http://www.example.com',
                           altcha='garbage!')
        app = handler.create_app()
        with patch('werkzeug.utils.redirect') as redirect:
            app.on_form_page(req)
        self.assertEqual(app.error, 'Invalid Captcha')
        redirect.assert_called_with(
            'http://www.example.com?error=6&message=Invalid+Captcha',
            code=302)

    @patch('request_handler.validate_email')
    def test_form_page_accepts_altcha_end_to_end(self, mock_validate_email):
        mock_validate_email.return_value = True
        req = self.request(name='Valid Guy', email='example@osuosl.org',
                           last_name='', token=conf.TOKEN,
                           redirect='http://www.example.com',
                           altcha=self.solved_payload())
        app = handler.create_app()
        with patch('request_handler.send_ticket') as send_ticket:
            with patch('werkzeug.utils.redirect') as redirect:
                app.on_form_page(req)
        self.assertEqual(app.error, None)
        send_ticket.assert_called_once()
        body = send_ticket.call_args[0][0]
        self.assertNotIn('Altcha', body)
        self.assertNotIn(req.form['altcha'], body)
        redirect.assert_called_with('http://www.example.com', code=302)

    def test_dedup_message_ignores_captcha_fields(self):
        first = self.request(name='x', email='a@b.co', redirect='r',
                             **{'cf-turnstile-response': 'token-1'})
        second = self.request(name='x', email='a@b.co', redirect='r',
                              altcha='token-2')
        self.assertEqual(handler.dedup_message(first),
                         handler.dedup_message(second))
        # The hash is taken over the string form, so field order must not
        # change the identity of a submission
        reordered = self.request(**{'redirect': 'r', 'email': 'a@b.co',
                                    'altcha': 'token-3', 'name': 'x'})
        self.assertEqual(str(handler.dedup_message(first)),
                         str(handler.dedup_message(reordered)))
        self.assertFalse(self.controller.is_duplicate(
            handler.dedup_message(first)))
        self.assertTrue(self.controller.is_duplicate(
            handler.dedup_message(second)))

    def test_format_message_hides_all_captcha_fields(self):
        msg = {'name': 'n', 'email': 'e', 'redirect': 'r', 'topic': 'hi',
               'cf-turnstile-response': 'TURNSTILE-TOKEN',
               'altcha': 'ALTCHA-TOKEN',
               'g-recaptcha-response': 'RECAPTCHA-TOKEN'}
        body = handler.format_message(msg)
        self.assertIn('hi', body)
        for field in captcha.FIELDS:
            # format_message title-cases keys, so check both spellings and
            # the value, which is what must never reach a ticket
            self.assertNotIn(field, body)
            self.assertNotIn(handler.convert_key_to_title(field), body)
            self.assertNotIn(msg[field], body)


class TestCaptchaHardening(unittest.TestCase):
    """
    Tests that each rejection path fails closed rather than raising, and that
    the settings that gate them are validated.
    """

    KEY = 'unit-test-altcha-key'

    def setUp(self):
        self.settings = patch.multiple(conf, TURNSTILE_SECRET='ts-secret',
                                       ALTCHA_HMAC_KEY=self.KEY,
                                       RECAPTCHA_SECRET='rc-secret',
                                       CAPTCHA_ALLOWED_HOSTNAMES=None,
                                       ALTCHA_ALGORITHM='SHA-256',
                                       ALTCHA_COST=1, ALTCHA_EXPIRES=600,
                                       RECAPTCHA_MIN_SCORE=0.5,
                                       TRUSTED_PROXY_COUNT=0, create=True)
        self.settings.start()
        self.addCleanup(self.settings.stop)
        self.controller = handler.Controller()

    @staticmethod
    def request(**fields):
        builder = EnvironBuilder(method='POST', data=fields,
                                 environ_base={'REMOTE_ADDR': '203.0.113.5'})
        return Request(builder.get_environ())

    @staticmethod
    def json_response(body):
        response = Mock()
        response.json.return_value = body
        return Mock(return_value=response)

    def altcha_payload(self, **parameters):
        """A solved payload whose challenge parameters can be overridden"""
        challenge = altcha.create_challenge('SHA-256', 1, hmac_secret=self.KEY,
                                            expires_at=int(time.time()) + 60)
        payload = altcha.Payload(challenge, altcha.solve_challenge(challenge))
        raw = payload.to_dict()
        raw['challenge']['parameters'].update(parameters)
        return base64.b64encode(json.dumps(raw).encode()).decode()

    def test_altcha_rejects_wrongly_typed_fields(self):
        """Attacker-chosen JSON types must not escape as a 500"""
        for expires_at in ('9999999999', [1], {'a': 1}):
            req = self.request(altcha=self.altcha_payload(
                expiresAt=expires_at))
            self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                             (False, 'altcha'))

    def test_altcha_rejects_wrongly_typed_counter(self):
        payload = json.loads(base64.b64decode(self.altcha_payload()))
        payload['solution']['counter'] = 2 ** 64
        raw = base64.b64encode(json.dumps(payload).encode()).decode()
        self.assertEqual(
            captcha.is_valid_captcha(self.request(altcha=raw),
                                     self.controller), (False, 'altcha'))

    def test_siteverify_non_object_response_is_rejected(self):
        """A proxy or error page that returns valid but scalar JSON"""
        for body in ('blocked', 42, True, None, ['nope']):
            with patch('captcha.session.post', self.json_response(body)):
                req = self.request(**{'cf-turnstile-response': 'tok'})
                self.assertEqual(
                    captcha.is_valid_captcha(req, self.controller),
                    (False, 'turnstile'))

    def test_error_codes_alongside_success_are_rejected(self):
        """reCAPTCHA fails open on quota: success true plus an error code"""
        body = {'success': True, 'score': 0.9,
                'error-codes': ['quota-exceeded']}
        with patch('captcha.session.post', self.json_response(body)):
            req = self.request(**{'g-recaptcha-response': 'tok'})
            self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                             (False, 'recaptcha'))

    def test_unusable_score_is_rejected(self):
        with patch('captcha.session.post',
                   self.json_response({'success': True, 'score': 'high'})):
            req = self.request(**{'g-recaptcha-response': 'tok'})
            self.assertFalse(captcha.is_valid_captcha(req,
                                                      self.controller)[0])

    def test_unset_min_score_falls_back_to_the_default(self):
        """A setting present but None must not be used as a threshold"""
        with patch.object(conf, 'RECAPTCHA_MIN_SCORE', None):
            with patch('captcha.session.post',
                       self.json_response({'success': True, 'score': 0.9})):
                req = self.request(**{'g-recaptcha-response': 'tok'})
                self.assertTrue(captcha.is_valid_captcha(req,
                                                         self.controller)[0])
            with patch('captcha.session.post',
                       self.json_response({'success': True, 'score': 0.1})):
                req = self.request(**{'g-recaptcha-response': 'tok'})
                self.assertFalse(captcha.is_valid_captcha(req,
                                                          self.controller)[0])

    def test_empty_hostname_allowlist_is_a_configuration_error(self):
        """A typo must not silently switch the check off"""
        for raw in (' , ', ',', '   '):
            with patch.object(conf, 'CAPTCHA_ALLOWED_HOSTNAMES', raw):
                with self.assertRaises(RuntimeError):
                    captcha.check_configuration()
                with self.assertRaises(RuntimeError):
                    handler.create_app()

    def test_unknown_altcha_algorithm_is_a_configuration_error(self):
        """The library falls back to plain SHA for anything it knows not"""
        for algorithm in ('nonsense', 'PBKDF2/SHA256', 'SCRYPT', 'ARGON2ID'):
            with patch.object(conf, 'ALTCHA_ALGORITHM', algorithm):
                with self.assertRaises(RuntimeError):
                    handler.create_app()
        with patch.object(conf, 'ALTCHA_ALGORITHM', 'PBKDF2/SHA-512'):
            self.assertEqual(captcha.altcha_algorithm(), 'PBKDF2/SHA-512')

    def test_configured_providers_are_logged_at_startup(self):
        with patch.object(handler.logging.getLogger('formsender'),
                          'info') as info:
            handler.create_app()
        self.assertIn('turnstile, altcha, recaptcha', info.call_args[0][1])

    def test_create_app_does_not_stack_log_handlers(self):
        logger = handler.logging.getLogger('formsender')
        before = len(logger.handlers)
        handler.create_app()
        handler.create_app()
        self.assertEqual(len(logger.handlers), before)

    # Request handling

    def test_failed_captcha_does_not_block_a_retry(self):
        """A rejected submission must not register as a duplicate"""
        fields = dict(name='Valid Guy', email='example@osuosl.org',
                      last_name='', token=conf.TOKEN,
                      redirect='http://www.example.com')
        app = handler.create_app()
        with patch('request_handler.validate_email', return_value=True):
            app.on_form_page(self.request(altcha='garbage!', **fields))
            self.assertEqual(app.error, 'Invalid Captcha')
            # Same body, this time with a captcha the user actually solved
            payload = self.altcha_payload()
            with patch('request_handler.send_ticket'):
                with patch('werkzeug.utils.redirect'):
                    app.on_form_page(self.request(altcha=payload, **fields))
        self.assertEqual(app.error, None)

    def test_duplicate_is_still_caught_after_a_valid_captcha(self):
        fields = dict(name='Valid Guy', email='example@osuosl.org',
                      last_name='', token=conf.TOKEN,
                      redirect='http://www.example.com')
        app = handler.create_app()
        with patch('request_handler.validate_email', return_value=True):
            with patch('captcha.is_valid_captcha',
                       return_value=(True, 'test')):
                with patch('request_handler.send_ticket'):
                    with patch('werkzeug.utils.redirect'):
                        app.on_form_page(self.request(**fields))
                        self.assertEqual(app.error, None)
                        app.on_form_page(self.request(**fields))
        self.assertEqual(app.error, 'Duplicate Request')

    def test_challenge_endpoint_accepts_head_and_limits_rate(self):
        client = Client(handler.create_app())
        self.assertEqual(client.head('/altcha').status_code, 200)
        for _ in range(conf.CEILING):
            client.get('/altcha')
        self.assertEqual(client.get('/altcha').status_code, 429)

    def test_forwarded_for_is_used_when_proxies_are_trusted(self):
        """Behind haproxy REMOTE_ADDR is the proxy, which is useless here"""
        post = self.json_response({'success': True})
        with patch.object(conf, 'TRUSTED_PROXY_COUNT', 1):
            client = Client(handler.create_app())
            with patch('captcha.session.post', post), \
                    patch('request_handler.send_ticket'), \
                    patch('request_handler.validate_email',
                          return_value=True):
                client.post('/', data={'name': 'x',
                                       'email': 'example@osuosl.org',
                                       'last_name': '', 'token': conf.TOKEN,
                                       'redirect': 'http://example.com',
                                       'cf-turnstile-response': 'tok'},
                            headers={'X-Forwarded-For': '198.51.100.7'},
                            environ_base={'REMOTE_ADDR': '140.211.9.50'})
        self.assertEqual(post.call_args[1]['data']['remoteip'],
                         '198.51.100.7')

    def test_remote_addr_is_used_without_a_trusted_proxy(self):
        post = self.json_response({'success': True})
        with patch('captcha.session.post', post):
            captcha.is_valid_captcha(
                self.request(**{'cf-turnstile-response': 'tok'}),
                self.controller)
        self.assertEqual(post.call_args[1]['data']['remoteip'], '203.0.113.5')

    def test_redeemed_challenges_do_not_grow_without_bound(self):
        expiry = time.time() + 600
        for index in range(handler.MAX_SEEN_CHALLENGES):
            self.controller.is_replayed_challenge('nonce-%d' % index, expiry)
            self.controller.commit_challenge()
        self.assertEqual(len(self.controller.seen_challenges),
                         handler.MAX_SEEN_CHALLENGES)
        self.controller.is_replayed_challenge('one-more', expiry)
        self.controller.commit_challenge()
        self.assertLess(len(self.controller.seen_challenges),
                        handler.MAX_SEEN_CHALLENGES)

    def test_captcha_payload_is_not_logged_with_the_submission(self):
        app = handler.create_app()
        payload = self.altcha_payload()
        req = self.request(name='Valid Guy', email='example@osuosl.org',
                           last_name='', token=conf.TOKEN,
                           redirect='http://www.example.com', altcha=payload)
        with patch.object(app, 'logger') as logger:
            with patch('request_handler.validate_email', return_value=True):
                with patch('request_handler.send_ticket'):
                    with patch('werkzeug.utils.redirect'):
                        app.on_form_page(req)
        logged = ' '.join(str(call) for call in logger.debug.call_args_list)
        self.assertIn('Valid Guy', logged)
        self.assertNotIn(payload, logged)

    def test_issued_challenge_verifies_with_the_shipped_defaults(self):
        """The mint and verify paths must agree on the real conf.py values"""
        defaults = patch.multiple(conf, ALTCHA_ALGORITHM='PBKDF2/SHA-256',
                                  ALTCHA_COST=5000, ALTCHA_EXPIRES=600)
        with defaults:
            client = Client(handler.create_app())
            body = client.get('/altcha').get_json()
            self.assertEqual(body['parameters']['algorithm'],
                             'PBKDF2/SHA-256')
            challenge = altcha.Challenge.from_dict(body)
            solution = altcha.solve_challenge(challenge)
            self.assertIsNotNone(solution)
            payload = altcha.Payload(challenge, solution).to_base64()
            req = self.request(altcha=payload)
            self.assertEqual(captcha.is_valid_captcha(req, self.controller),
                             (True, 'altcha'))

    def test_challenge_survives_a_failure_after_the_captcha_check(self):
        """An RT outage must not burn the sender's solved challenge"""
        fields = dict(name='Persistent', email='p@osuosl.org', last_name='',
                      token=conf.TOKEN, redirect='http://www.example.com')
        payload = self.altcha_payload()
        app = handler.create_app()
        with patch('request_handler.validate_email', return_value=True):
            with patch('request_handler.send_ticket',
                       side_effect=RuntimeError('RT down')):
                with self.assertRaises(RuntimeError):
                    app.on_form_page(self.request(altcha=payload, **fields))
            # Same page, same solved challenge, RT back
            with patch('request_handler.send_ticket') as send_ticket:
                with patch('werkzeug.utils.redirect'):
                    app.on_form_page(self.request(altcha=payload,
                                                  name='Persistent Two',
                                                  email='p@osuosl.org',
                                                  last_name='',
                                                  token=conf.TOKEN,
                                                  redirect='http://e.com'))
        self.assertEqual(app.error, None)
        send_ticket.assert_called_once()

    def test_a_challenge_is_spent_once_a_ticket_exists(self):
        fields = dict(name='Spender', email='s@osuosl.org', last_name='',
                      token=conf.TOKEN, redirect='http://www.example.com')
        payload = self.altcha_payload()
        app = handler.create_app()
        with patch('request_handler.validate_email', return_value=True):
            with patch('request_handler.send_ticket'):
                with patch('werkzeug.utils.redirect'):
                    app.on_form_page(self.request(altcha=payload, **fields))
                    self.assertEqual(app.error, None)
                    app.on_form_page(self.request(altcha=payload,
                                                  name='Spender Two',
                                                  email='s@osuosl.org',
                                                  last_name='',
                                                  token=conf.TOKEN,
                                                  redirect='http://e.com'))
        self.assertEqual(app.error, 'Invalid Captcha')


if __name__ == '__main__':
    unittest.main()
