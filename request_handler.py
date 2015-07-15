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
from conf import EMAIL, TOKN, CEILING
from validate_email import validate_email
from datetime import datetime

#WSGI Application
class Forms(object):

    def __init__(self):
        global rater
        rater.increment_rate()
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.error = None
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                                     autoescape=True)
        self.url_map = Map([Rule('/', endpoint='form_page')])

    def render_template(self, template_name, status, **context):
        t = self.jinja_env.get_template(template_name)
        return Response(t.render(context), mimetype='text/html', status=status)

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, 'on_' + endpoint)(request, **values)
        except HTTPException, e:
            return e

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def send_email(self, msg):
        msg_send = MIMEText(str(msg))
        s = smtplib.SMTP('localhost')
        try:
            s.sendmail('theform', EMAIL, msg_send.as_string())
            s.quit()
        except:
            s.quit()

    def on_form_page(self, request):
        global rater
        self.error = None
        message = None
        status = 200
        if request.method == 'POST':
            if not is_valid_email(request):
                self.error = 'Invalid Email'
                message = None
                status = 400
            elif not validate_name(request):
                self.error = 'Invalid Name'
                message = None
                status = 401
            elif not is_hidden_field_empty(request) or not is_valid_token(request):
                self.error = 'Improper Form Submission'
                message = None
                status = 402
            elif rater.is_rate_violation():
                self.error = 'Too Many Requests'
                message = None
                status = 429
            else:
                message = create_msg(request)
                if message:
                    self.send_email(message)
                    return self.render_template('submitted.html',
                                                error=self.error,
                                                url=message,
                                                status=status)
        return self.render_template('index.html',
                                    error=self.error,
                                    url=message, status=status)


class RateLimiter(object):

    def __init__(self):
        self.rate = 0
        self.start_time = datetime.now()
        self.time_diff = 0

    def set_time_diff(self):
        time_d = datetime.now() - self.start_time
        self.time_diff = time_d.seconds

    def increment_rate(self):
        self.rate += 1;

    def reset_rate(self):
        self.rate = 0
        self.start_time = datetime.now()
        self.time_diff = 0

    def is_rate_violation(self):
        """
        False if rate does not violate CEILING in 1 second (no violation)
        and True otherwise (violation)
        """
        self.set_time_diff()
        if self.time_diff < 1 and self.rate > CEILING:
            self.reset_rate()
            return True
        elif self.time_diff > 1:
            self.reset_rate()
        return False

rater = RateLimiter();

# Standalone/helper functions
def create_app(with_static=True):
    app = Forms()
    if with_static:
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/static':  os.path.join(os.path.dirname(__file__), 'static')
        })
    return app

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


# Application logic
if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = create_app()
    run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
