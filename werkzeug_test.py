from conf import TOKN, EMAIL
import unittest
from request_handler import (Forms, create_msg, validate_name, is_valid_email,
                             is_hidden_field_empty, is_valid_token)
from werkzeug.test import Client
from werkzeug.testapp import test_app
from werkzeug.wrappers import BaseResponse, Request
from werkzeug.test import EnvironBuilder
from StringIO import StringIO


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
        assert (create_msg(req)['foo'] == builder.form['foo'] and
               create_msg(req)['file'] == builder.form['file'] and
               create_msg(req)['test'] == builder.form['test'])

    def test_create_msg_no_content(self):
        """
        Tests create_msg with no content in the POST request

        Checks that create_msg returns None
        """
        builder = EnvironBuilder(method='POST', data={})
        env = builder.get_environ()
        req = Request(env)
        assert create_msg(req) is None

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
        assert create_msg(req) is None

    def test_send_email(self):
        """
        Tests send_email

        send_email returns True when it successfully sends an email and
        False when unsuccessfull.
        """
        app = Forms()
        assert app.send_email({'name': u'Valid Guy',
                               'email': u'mrsj@osuosl.org',
                               'hidden': '',
                               'tokn': TOKN})

    def test_validations_valid_data(self):
        """
        Tests the form validation with valid data.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'mrsj@osuosl.org',
                                       'hidden': '',
                                       'tokn': TOKN })
        env = builder.get_environ()
        req = Request(env)
        app = Forms()
        app.on_form_page(req)
        assert app.error is None

    def test_validations_invalid_name(self):
        """
        Tests the form validation with an invalid name.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        Invalid name field causes an 'Invalid Name' error.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'r0b0tm@n!',
                                       'email': 'mrsj@osuosl.org',
                                       'hidden': '',
                                       'tokn': TOKN })
        env = builder.get_environ()
        req = Request(env)
        app = Forms()
        app.on_form_page(req)
        assert app.error == 'Invalid Name'

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
        app = Forms()
        app.on_form_page(req)
        assert app.error == 'Invalid Email'

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
                                       'email': 'mrsj@osuosl.org',
                                       'hidden': 'r',
                                       'tokn': TOKN })
        env = builder.get_environ()
        req = Request(env)
        app = Forms()
        app.on_form_page(req)
        assert app.error == 'Improper Form Submission'

    def test_validations_invalid_token(self):
        """
        Tests the form validation with an invalid token.

        on_form_page checks for valid fields in submitted form and
        returns an error message if an invalid field is found.
        An invalid token causes the 'Improper Form Submission' error.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'name': 'Valid Guy',
                                       'email': 'mrsj@osuosl.org',
                                       'hidden': '',
                                       'tokn': 'evilrobot' })
        env = builder.get_environ()
        req = Request(env)
        app = Forms()
        app.on_form_page(req)
        assert app.error == 'Improper Form Submission'

    def test_is_valid_email_with_valid(self):
        """
        Tests is_valid_email with a valid email

        is_valid_email checks that the email submitted to the form is
        valid and exists. This function call should return true.
        """
        builder = EnvironBuilder(method='POST',
                                 data={'email': 'mrsj@osuosl.org'})
        env = builder.get_environ()
        req = Request(env)
        assert is_valid_email(req)

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
        assert is_valid_email(req) is False

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
        assert validate_name(req)

    def test_validate_name_with_invalid(self):
        """
        Tests validate_name with an invalid name

        validate_name checks that the name submitted to the form does
        not contain disallowed characters. This function call should
        return false.
        """
        builder = EnvironBuilder(method='POST', data={'name':
                                                      '89~hello/world'})
        env = builder.get_environ()
        req = Request(env)
        assert validate_name(req) is False

    def test_is_hidden_field_empty_empty(self):
        """
        Tests is_hidden_field_empty with 'hidden' field empty

        is_hidden_field_empty checks that the hidden field in the form
        is empty. This function call should return true.
        """
        builder = EnvironBuilder(method='POST', data={'hidden': ''})
        env = builder.get_environ()
        req = Request(env)
        assert is_hidden_field_empty(req)

    def test_is_hidden_field_empty_full(self):
        """
        Tests is_hidden_field_empty with contents in 'hidden' field

        is_hidden_field_empty checks that the hidden field in the form
        is empty. This function call should return false.
        """
        builder = EnvironBuilder(method='POST', data={'hidden': 'nope'})
        env = builder.get_environ()
        req = Request(env)
        assert is_hidden_field_empty(req) is False

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
        assert is_valid_token(req)

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
        assert is_valid_token(req) is False


if __name__ == '__main__':
    unittest.main()
