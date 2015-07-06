import os
import urlparse
import smtplib
import werkzeug
import urllib
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException
from werkzeug.wsgi import SharedDataMiddleware
from jinja2 import Environment, FileSystemLoader
from email.mime.text import MIMEText
from conf import EMAIL, TOKN, CEILING
from validate_email import validate_email
from datetime import datetime

#WSGI Application
class Forms(object):
    """
    This class listens for a form submission, checks that the data is valid, and
    sends the form data in a formatted message to the email specified in conf.py
    """

    def __init__(self, rater):
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.rater = rater
        self.error = None
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                                     autoescape=True)
        # When the browser is pointed at the root of the website, call
        # on_form_page
        self.url_map = Map([Rule('/', endpoint='form_page')])

    # Renders a webpage based on a template
    def render_template(self, template_name, status, **context):
        t = self.jinja_env.get_template(template_name)
        return Response(t.render(context), mimetype='text/html', status=status)

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
        msg_send = MIMEText(str(msg))
        s = smtplib.SMTP('localhost')
        try:
            s.sendmail('theform', EMAIL, msg_send.as_string())
            s.quit()
        except:
            s.quit()

    # Renders form if form was previously empty, the successfully emailed page
    # if not
    def on_form_page(self, request):
        self.error = None
        self.rater.increment_rate()
        message = None
        error_number = 0
        if request.method == 'POST':
            if not is_valid_email(request):
                self.error = 'Invalid Email'
                message = None
                error_number = 1
            elif not validate_name(request):
                self.error = 'Invalid Name'
                message = None
                error_number = 2
            elif (not is_hidden_field_empty(request)
                  or not is_valid_token(request)):
                self.error = 'Improper Form Submission'
                message = None
                error_number = 3
            elif self.rater.is_rate_violation():
                self.error = 'Too Many Requests'
                message = None
                error_number = 4
            else:
                message = create_msg(request)
                if message:
                    self.send_email(message)
                    redirect_url = request.form['redirect']
                    return werkzeug.utils.redirect(redirect_url, code=302)
            error_url = create_error_url(error_number, self.error, request)
            return werkzeug.utils.redirect(error_url, code=302)
        # Renders test form on localhost
        return self.render_template('index.html',
                                    error=self.error,
                                    url=message,
                                    status=200)



class RateLimiter(object):
    """Track number of form submissions per second

    __init__
    set_time_diff
    increment_rate
    reset_rate
    is_rate_violation
    """

    def __init__(self):
        self.rate = 0
        self.start_time = datetime.now()
        self.time_diff = 0

    def set_time_diff(self):
        # Sets time_diff in seconds
        time_d = datetime.now() - self.start_time
        self.time_diff = time_d.seconds

    def increment_rate(self):
        self.rate += 1;

    def reset_rate(self):
        # Reset rate to initial values
        self.rate = 0
        self.start_time = datetime.now()
        self.time_diff = 0

    def is_rate_violation(self):
        # False if rate does not violate CEILING in 1 second (no violation)
        # and True otherwise (violation)
        self.set_time_diff()
        if self.time_diff < 1 and self.rate > CEILING:
            return True
        elif self.time_diff > 1:
            self.reset_rate()
        return False

# Global RateLimiter object


# Standalone/helper functions
def create_app(with_static=True):
    rater = RateLimiter()
    app = Forms(rater)
    if with_static:
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/static':  os.path.join(os.path.dirname(__file__), 'static')
        })
    return app

# Creates the message to be sent in the email
def create_msg(request):
    message = dict()
    if request.method == 'POST':
        for key in request.form:
            message[key] = request.form[key]
        if message:
            return message
        return None
    return None

def is_valid_email(request):
    valid_email = validate_email(request.form['email'],
                                 check_mx=True,
                                 verify=True)
    if valid_email:
        return valid_email
    return False

def validate_name(request):
    name = request.form['name']
    if name.strip():
        return True
    return False

def is_hidden_field_empty(request):
    if request.form['hidden'] == "":
        return True
    return False

def is_valid_token(request):
    if request.form['tokn'] == TOKN:
        return True
    return False

# Construct error message and append to redirect url
def create_error_url(error_number, message, request):
    values = [('error', str(error_number)), ('message', message)]
    query = urllib.urlencode(values)
    return request.form['redirect'] + '?' + query




# Application logic
if __name__ == '__main__':
    from werkzeug.serving import run_simple
    # Creates the app
    app = create_app()
    # Starts the listener
    run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
