import os
import urlparse
import smtplib
import werkzeug
import urllib
import re
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException
from werkzeug.wsgi import SharedDataMiddleware
from jinja2 import Environment, FileSystemLoader
from email.mime.text import MIMEText
from validate_email import validate_email
from datetime import datetime
from conf import EMAIL, TOKN, CEILING

"""
WSGI Application

This application listens to a form. When the form is submitted, this
application takes the information submitted, formats it into a python
dictiononary, then emails it to a specified email
"""
class Forms(object):
    """
    This class listens for a form submission, checks that the data is valid, and
    sends the form data in a formatted message to the email specified in conf.py
    """

    def __init__(self, rater):
        # Sets up the path to the template files
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.rater = rater
        self.error = None
        # Initiates jinja environment
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                                     autoescape=True)
        # When the browser is pointed at the root of the website, call
        # on_form_page
        self.url_map = Map([Rule('/', endpoint='form_page')])

    # Evaluates request to decide what happens
    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, 'on_' + endpoint)(request, **values)
        except HTTPException, e:
            return e

    # Starts wsgi_app by creating a Request and Response based on the Request
    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    # Sets up and sends the email
    def send_email(self, msg, email_from, subject):
        # Format the message and set the subject
        msg_send = MIMEText(str(msg))
        msg_send['Subject'] = subject
        # Sets up a temporary mail server to send from
        s = smtplib.SMTP('localhost')
        # Attempts to send the mail to EMAIL, with the message formatted as a
        # string
        try:
            s.sendmail(email_from, EMAIL, msg_send.as_string())
            s.quit()
        except:
            s.quit()

    # Checks for valid form data, calls send_email, returns a redirect
    def on_form_page(self, request):
        # Increment rate because we received a request
        self.rater.increment_rate()
        self.error = None
        error_number = 0

        if request.method == 'POST' and self.are_fields_invalid(request):
            # Error was found
            error_number = self.are_fields_invalid(request)
            return self.handle_error(request, error_number)
        elif request.method == 'POST':
            # No errors
            return self.handle_no_error(request)
        else:
            # Renders error message locally if sent GET request
            t = self.jinja_env.get_template('error.html')
            return Response(t.render(), mimetype='text/html', status=400)

    # If a field in the request is invalid, sets the error message and returns
    # the error number, returns False if fields are valid
    def are_fields_invalid(self, request):
        # Sends request to each error function and returns first error it sees
        if not is_valid_email(request):
            self.error = 'Invalid Email'
            error_number = 1
        elif not validate_name(request):
            self.error = 'Invalid Name'
            error_number = 2
        elif (not is_hidden_field_empty(request)
              or not is_valid_token(request)):
            self.error = 'Improper Form Submission'
            error_number = 3
        elif self.rater.is_rate_violation():
            self.error = 'Too Many Requests'
            error_number = 4
        else:
            # If nothing above is true, there is no error
            return False;
        # There is an error if it got this far
        return error_number

    # Creates a message and sends an email with no error, then redirects to
    # provided redirect url
    def handle_no_error(self, request):
        message = create_msg(request)
        if message:
            self.send_email(format_message(message),
                            set_mail_from(message),
                            set_mail_subject(message))
            redirect_url = message['redirect']
            return werkzeug.utils.redirect(redirect_url, code=302)

    # Creates error url and redirects with error query
    def handle_error(self, request, error_number):
        error_url = create_error_url(error_number, self.error, request)
        return werkzeug.utils.redirect(error_url, code=302)



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

    # Sets time_diff in seconds
    def set_time_diff(self):
        time_d = datetime.now() - self.start_time
        self.time_diff = time_d.seconds

    def increment_rate(self):
        self.rate += 1;

    # Reset rate to initial values
    def reset_rate(self):
        self.rate = 0
        self.start_time = datetime.now()
        self.time_diff = 0

    # Returns False if rate does not violate CEILING in 1 second (no violation)
    # and True otherwise (violation)
    def is_rate_violation(self):
        self.set_time_diff()
        if self.time_diff < 1 and self.rate > CEILING:
            return True
        elif self.time_diff > 1:
            self.reset_rate()
        return False



# Standalone/helper functions

# Initializes RateLimiter (rater) and Forms (app) objects, pass rater to app to
# keep track of number of submissions per minute
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
        # Takes the information from the request and puts it into the message
        # dict. request.form cannot be returned directly because it is a
        # multidict.
        for key in request.form:
            message[key] = request.form[key]
        # If there is a message, return it, otherwise return None
        if message:
            message['redirect'] = strip_query(message['redirect'])
            return message
        return None
    return None

# Check that email server exists at request.form['email']
# return the email if it is valid, False if not
def is_valid_email(request):
    valid_email = validate_email(request.form['email'],
                                 check_mx=True,
                                 verify=True)
    if valid_email:
        return valid_email
    return False

# Make sure request has a 'name' field with more than just spaces
# return stripped name if true, False if not
def validate_name(request):
    name = request.form['name']
    if name.strip():
        return True
    return False

# Make sure hidden 'last_name' field is empty, return True or False
def is_hidden_field_empty(request):
    if request.form['last_name'] == "":
        return True
    return False

# Make sure request's 'tokn' field matches TOKN in conf.py
def is_valid_token(request):
    if request.form['tokn'] == TOKN:
        return True
    return False

# Construct error message and append to redirect url
def create_error_url(error_number, message, request):
    values = [('error', str(error_number)), ('message', message)]
    query = urllib.urlencode(values)
    return request.form['redirect'] + '?' + query

# Remove query string from a url
def strip_query(url):
    return url.split('?', 1)[0]

# Formats a dict (msg) into a nice-looking string
def format_message(msg):
    # Ignore these fields when writing to formatted message
    hidden_fields = ['redirect', 'last_name', 'tokn', 'op',
                     'name', 'email', 'mail_subject', 'mail_from']
    # Contact information goes at the top
    f_message = ("Contact:\n--------\n"
                 "NAME:   {0}\nEMAIL:   {1}\n"
                 "\nInformation:\n------------\n"
                 .format(msg['name'], msg['email']))
    # Write each formatted key in title case and corresponding message to
    # f_message, each key and message is separated by two lines.
    for key in sorted(msg):
        if key not in hidden_fields:
            f_message += ('{0}:\n\n{1}\n\n'.format(convert_key_to_title(key),
                                                   msg[key]))
    return f_message

# Replace underscores with spaces and convert to title case
def convert_key_to_title(snake_case_key):
    return snake_case_key.replace('_', ' ').title()

# Returns a string to be used as a subject in an email
# Default is 'Form Submission'
def set_mail_subject(message):
    # If key exists in the message dict and has content return the content
    if 'mail_subject' in message and message['mail_subject']:
        return message['mail_subject']
    # Otherwise return default
    return 'Form Submission'

# Returns a string to be used in the 'from' field in an email
# Default is 'Form'
def set_mail_from(message):
    # If key exists in the message dict and has content return the content
    if 'mail_from' in message and message['mail_from']:
        return message['mail_from']
    # Otherwise return default
    return 'Form'


# Start application
if __name__ == '__main__':
    from werkzeug.serving import run_simple
    # Creates the app
    app = create_app()
    # Starts the listener
    run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
