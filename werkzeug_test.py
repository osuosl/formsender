import unittest
from request_handler import Forms, create_msg
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
        assert app.send_email({'age': u'test', 'name': u'dict'})


if __name__ == '__main__':
    unittest.main()
