import unittest
from request_handler import Forms
from request_handler import create_app


import os
import redis
import urlparse
import smtplib
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import redirect
from jinja2 import Environment, FileSystemLoader
from email.mime.text import MIMEText

class TestForms(unittest.TestCase):

    def test_it_works(self):
        form = Forms({
            'redis_host':       'localhost',
            'redis_port':       6379
        })
        assert form.send_email({'age': u'19', 'name': u'matthew'})

    def test_create_app(self):
        app = create_app()
        trueApp = Forms({
            'redis_host':       'localhost',
            'redis_port':       6379
        })
        trueApp.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/static':  os.path.join(os.path.dirname(__file__), 'static')
        })
        print app
        print trueApp
        assert app == trueApp

    def test_form_page(self):
        message = {'age': u'19', 'name': u'matthew'}

if __name__ == '__main__':
    unittest.main()
