import unittest
import werkzeug
from werkzeug.wrappers import Request
from werkzeug.test import EnvironBuilder
from mock import Mock, patch
import conf
import time
import request_handler as handler
import rt


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
                                       'token': conf.TOKEN,
                                       'redirect': 'http://www.example.com',
                                       'g-recaptcha-response': ''})
        env = builder.get_environ()
        req = Request(env)
        # Mock external validate_email so returns true in Travis
        mock_validate_email.return_value = True
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

    @patch('request_handler.validate_email')
    def test_rate_limiter_valid_rate(self, mock_validate_email):
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
        # Mock validate email so returns true in Travis
        mock_validate_email.return_value = True
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
                                       'token': conf.TOKEN,
                                       'g-recaptcha-response': ''})
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

    @patch('request_handler.validate_email')
    def test_same_submission(self, mock_validate_email):
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


if __name__ == '__main__':
    unittest.main()
