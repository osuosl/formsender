import os
import urlparse
import smtplib
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import redirect
from jinja2 import Environment, FileSystemLoader
from email.mime.text import MIMEText
from conf import EMAIL

"""
WSGI Application

This application listens to a form. When the form is submitted, this
application takes the information submitted, formats it into a python
dictiononary, then emails it to a specified email
"""
class Forms(object):

    def __init__(self):
        # Sets up the path to the template files
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        # Sets up the environment (I don't know what that means)
        # Jinja is a templating engine for python
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                                     autoescape=True)
        # When the browser is pointed at the root of the website, call
        # on_form_page
        self.url_map = Map([Rule('/', endpoint='form_page')])

    # Renders a webpage based on a template
    def render_template(self, template_name, **context):
        # Need to figure out what jinja is
        t = self.jinja_env.get_template(template_name)
        # Renders things somehow
        return Response(t.render(context), mimetype='text/html')

    # Really important. Handles deciding what happens
    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, 'on_' + endpoint)(request, **values)
        except HTTPException, e:
            return e

    # This starts the app. I think
    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    # Calls something. This is important but I don't know why
    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    # Sets up and sends the email
    def send_email(self, msg):
        # Format the message
        msg_send = MIMEText(str(msg))
        # Sets up a temporary mail server to send from (I think)
        s = smtplib.SMTP('localhost')
        # Attempts to send the mail to EMAIL, with the message formatted as a
        # string
        try:
            s.sendmail('theform', EMAIL, msg_send.as_string())
            s.quit()
            return True
        except:
            s.quit()
            return False

    # Renders form if form was previously empty, the successfully emailed page
    # if not
    def on_form_page(self, request):
        error = None
        # Creates the message to be emailed from the request. Returns either a
        # message or None
        message = create_msg(request)
        # If there is a message, call send email, then display the success page.
        if message:
            self.send_email(message)
            return self.render_template('submitted.html', error=error, url=message)
        # If there is no message, render the form
        return self.render_template('index.html', error=error, url=message)


# Standalone/helper functions
# This does things that I don't understand
def create_app(with_static=True):
    app = Forms()
    if with_static:
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/static':  os.path.join(os.path.dirname(__file__), 'static')
        })
    return app

# Creates the message to be sent in the email
# This could use some improvement, as it currently just sends a dict with no
# formatting. Needs to be made prettier
def create_msg(request):
    message = dict()
    if request.method == 'POST':
        # Takes the information from the request and puts it into the message
        # dict
        for key in request.form:
            message[key] = request.form[key]
        # If there is a message, return it, otherwise return None
        if message:
            return message
        return None
    return None


# Application logic
if __name__ == '__main__':
    from werkzeug.serving import run_simple
    # Creates the app
    app = create_app()
    # Starts the listener thingy
    run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
