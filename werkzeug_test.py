from conf import TOKN, EMAIL
import unittest
from request_handler import Forms, create_msg
from werkzeug.test import Client
from werkzeug.testapp import test_app
from werkzeug.wrappers import BaseResponse, Request
from werkzeug.test import EnvironBuilder
from StringIO import StringIO


class Test_formsender(unittest.TestCase):

    def test_create_msg_with_content(self):
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
        builder = EnvironBuilder(method='POST', data={})
        env = builder.get_environ()
        req = Request(env)
        assert create_msg(req) is None

    def test_create_msg_no_content_get_method(self):
        builder = EnvironBuilder(method='GET', data={})
        env = builder.get_environ()
        req = Request(env)
        assert create_msg(req) is None

    def test_send_email(self):
        app = Forms()
        assert app.send_email({'age': u'test', 'name': u'dict'})

    def test_validate_email_with_valid(self):
        builder = EnvironBuilder(method='POST',
                                 data={'email': 'mrsj@osuosl.org'})
        env = builder.get_environ()
        req = Request(env)
        assert validate_email(req)

    def test_validate_email_with_invalid(self):
        builder = EnvironBuilder(method='POST',
                                 data={'email': 'nope@osuosl.org'})
        env = builder.get_environ()
        req = Request(env)
        assert not validate_email(req)

    def test_validate_name_with_valid(self):
        builder = EnvironBuilder(method='POST', data={'name': 'Matthew'})
        env = builder.get_environ()
        req = Request(env)
        assert validate_name(req)

    def test_validate_name_with_invalid(self):
        builder = EnvironBuilder(method='POST', data={'name': '89~hello/world'})
        env = builder.get_environ()
        req = Request(env)
        assert not validate_name(req)

    def test_is_hidden_field_empty_empty(self):
        builder = EnvironBuilder(method='POST', data={'hidden': ''})
        env = builder.get_environ()
        req = Request(env)
        assert is_hidden_field_empty(req)

    def test_is_hidden_field_empty_full(self):
        builder = EnvironBuilder(method='POST', data={'hidden': 'nope'})
        env = builder.get_environ()
        req = Request(env)
        assert not is_hidden_field_empty(req)

    def test_is_valid_token_valid(self):
        builder = EnvironBuilder(method='POST', data={'tok': TOKN})
        env = builder.get_environ()
        req = Request(env)
        assert is_valid_token(req)

    def test_is_valid_token_invalid(self):
        builder = EnvironBuilder(method='POST', data={'tok': 'I hate FOSS'})
        env = builder.get_environ()
        req = Request(env)
        assert not is_valid_token(req)


if __name__ == '__main__':
    unittest.main()
