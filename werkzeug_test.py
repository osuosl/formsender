from werkzueg.test import Client
from werkzueg.testapp import test_app
from werkzeug.wrappers import BaseResponse, Request
from werkzeug.test import EnvironBuilder

from request_handler import *

class FormsTestCase():
    def test_things(self):
        builder = EnvironBuilder(method='POST', data={'age': '4', 'name':
            'banana'})
        env = builder.get_environ()

        req = Request(env)

if __name__ == '__main__':
#do things
