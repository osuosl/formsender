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
        request = Request(env)
        assert (create_msg(request)['foo'] == builder.form['foo'] and
               create_msg(request)['file'] == builder.form['file'] and
               create_msg(request)['test'] == builder.form['test'])

    def test_create_msg_no_content(self):
        builder = EnvironBuilder(method='POST', data={})
        env = builder.get_environ()
        request = Request(env)
        assert create_msg(request) is None

    def test_create_msg_no_content_get_method(self):
        builder = EnvironBuilder(method='GET', data={})
        env = builder.get_environ()
        request = Request(env)
        assert create_msg(request) is None

    def test_send_email(self):
        form = Forms()
        assert form.send_email({'age': u'test', 'name': u'dict'})


if __name__ == '__main__':
    unittest.main()
