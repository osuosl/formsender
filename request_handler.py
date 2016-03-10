"""
WSGI Application

This application listens for a form. When a form is submitted, this application
takes the information submitted, formats it into a python dictionary, then
emails it to a specified email
"""

import os
import smtplib
import werkzeug
import urllib
import hashlib
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException
from werkzeug.wsgi import SharedDataMiddleware
from jinja2 import Environment, FileSystemLoader
from email.mime.text import MIMEText
from validate_email import validate_email
from datetime import datetime
import logging
import logging.handlers
import conf


class Forms(object):
    """
    This class listens for a form submission, checks that the data is valid, and
    sends the form data in a formatted message to the email specified in conf.py
    """
    def __init__(self, controller, logger):
        # Sets up the path to the template files
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.controller = controller
        self.error = None
        # Creates jinja template environment
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                                     autoescape=True)
        # When the browser is pointed at the root of the website, call
        # on_form_page
        self.url_map = Map([Rule('/', endpoint='form_page')])
        self.logger = logger

    def dispatch_request(self, request):
        """Evaluates request to decide what happens"""
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, 'on_' + endpoint)(request, **values)
        except HTTPException, error:
            self.logger.error('formsender: %s', error)
            return error

    def wsgi_app(self, environ, start_response):
        """
        Starts wsgi_app by creating a Request and Response based on the Request
        """
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def on_form_page(self, request):
        """
        Checks for valid form data, calls send_email, returns a redirect
        """
        # Increment rate because we received a request
        self.controller.increment_rate()
        self.error = None
        error_number = self.are_fields_invalid(request)
        if request.method == 'POST' and error_number:
            # Error was found
            return self.handle_error(request, error_number)
        elif request.method == 'POST':
            # No errors
            return self.handle_no_error(request)
        else:
            # Renders error message locally if sent GET request
            self.logger.error('formsender: server received unhandled GET '
                              'request, expected POST request')
            return self.error_redirect()

    def are_fields_invalid(self, request):
        """
        If a field in the request is invalid, sets the error message and returns
        the error number, returns False if fields are valid
        """
        # Sends request to each error function and returns first error it sees
        if not is_valid_email(request):
            self.error = 'Invalid Email'
            error_number = 1
            invalid_option = 'email'
        elif not validate_name(request):
            self.error = 'Invalid Name'
            error_number = 2
            invalid_option = 'name'
        elif (not is_hidden_field_empty(request) or
              not is_valid_token(request)):
            self.error = 'Improper Form Submission'
            error_number = 3
            invalid_option = 'name'
        elif self.controller.is_rate_violation():
            self.error = 'Too Many Requests'
            error_number = 4
            invalid_option = 'name'
        elif self.controller.is_duplicate(create_msg(request)):
            self.error = 'Duplicate Request'
            error_number = 5
            invalid_option = 'name'
        else:
            # If nothing above is true, there is no error
            return False
        # There is an error if it got this far
        self.logger.warn('formsender: received %s: %s from %s',
                         self.error,
                         request.form[invalid_option],
                         request.form['email'])
        return error_number

    def handle_no_error(self, request):
        """
        Creates a message and sends an email with no error, then redirects to
        provided redirect url
        """
        message = create_msg(request)
        if message:
            self.logger.info('formsender: sending email from: %s',
                             message['email'])
            send_email(format_message(message), set_mail_subject(message),
                       send_to_address(message), set_mail_from(message))
            redirect_url = message['redirect']
            return werkzeug.utils.redirect(redirect_url, code=302)
        else:
            return self.error_redirect()

    def handle_error(self, request, error_number):
        """Creates error url and redirects with error query"""
        error_url = create_error_url(error_number, self.error, request)
        return werkzeug.utils.redirect(error_url, code=302)

    def error_redirect(self):
        """Renders local error html file"""
        self.logger.error('formsender: POST request was empty')
        template = self.jinja_env.get_template('error.html')
        return Response(template.render(), mimetype='text/html', status=400)


class Controller(object):
    """
    Track number of form submissions per second

    __init__
    set_time_diff
    increment_rate
    reset_rate
    is_rate_violation
    """
    def __init__(self):
        # Rate variables
        self.rate = 0
        self.time_diff = 0
        self.start_time = datetime.now()
        # Duplicate-submission check variables
        self.time_diff_hash = 0
        self.start_time_hash = datetime.now()
        self.hash_list = []

    def set_time_diff(self, begin_time):
        """Returns time difference between begin_time and now in seconds"""
        time_d = datetime.now() - begin_time
        return time_d.seconds

    # Rate methods
    def increment_rate(self):
        """Increments self.rate by 1"""
        self.rate += 1

    def reset_rate(self):
        """Reset rate to initial values"""
        self.rate = 0
        self.start_time = datetime.now()
        self.time_diff = 0

    def is_rate_violation(self):
        """
        Returns False if rate doesn't violate CEILING in 1 second (no violation)
        and True otherwise (violation)
        """
        self.time_diff = self.set_time_diff(self.start_time)
        if self.time_diff < 1 and self.rate > conf.CEILING:
            return True
        elif self.time_diff > 1:
            self.reset_rate()
        return False

    # Duplicate-submission check methods
    def is_duplicate(self, submission):
        """Calculates a hash from a submission and adds it to the hash list"""
        # Create a hexidecmal hash of the submission using sha512
        init_hash = hashlib.sha512()
        init_hash.update(str(submission))
        sub_hash = init_hash.hexdigest()
        # If the time difference is under the limit in settings, check for a
        # duplicate hash in hash_list
        if self.check_time_diff_hash():
            return self.check_for_duplicate_hash(sub_hash)
        # If the time difference is greater than the limit in settings, there is
        # no duplicate since hash_list was reset in check_time_diff_hash
        return False

    def check_time_diff_hash(self):
        """
        Checks time_diff_hash for a value greater than DUPL_CHECK_LIM from
        conf.py
        """
        self.time_diff_hash = self.set_time_diff(self.start_time_hash)
        # If time difference is greater than DUPLICATE_CHECK_TIME, reset the
        # hash list and time variables
        if self.time_diff_hash > (conf.DUPLICATE_CHECK_TIME):  # from conf.py
            self.reset_hash()
            return False
        return True

    def reset_hash(self):
        """Resets hash_list and hash_times"""
        self.hash_list = []
        self.time_diff_hash = 0
        self.start_time_hash = datetime.now()

    def check_for_duplicate_hash(self, sub_hash):
        """
        Checks for a duplicate hash in hash_list
        Returns True if there is a duplicate and False otherwise
        """
        if sub_hash in self.hash_list:
            return True
        # If there is no duplicate, add hash to the list and return False
        self.hash_list.append(sub_hash)
        return False


# Standalone/helper functions
def create_app(with_static=True):
    """
    Initializes Controller (controller) and Forms (app) objects, pass
    controller to app to keep track of number of submissions per minute
    """
    # Initiate a logger
    logger = logging.getLogger('formsender')
    handler = logging.handlers.SysLogHandler(address=conf.LOG_ADDR)
    formatter = logging.Formatter('%(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Initiate rate/duplicate controller and application
    controller = Controller()
    app = Forms(controller, logger)
    if with_static:
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/static':  os.path.join(os.path.dirname(__file__), 'static')
        })
    return app


def create_msg(request):
    """Creates the message to be sent in the email"""
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


def is_valid_email(request):
    """
    Check that email server exists at request.form['email']
    return the email if it is valid, False if not
    """
    valid_email = validate_email(request.form['email'],
                                 check_mx=True,
                                 verify=True)
    if valid_email:
        return valid_email
    return False


def validate_name(request):
    """
    Make sure request has a 'name' field with more than just spaces return
    stripped name if true, False if not
    """
    name = request.form['name']
    if name.strip():
        return True
    return False


def is_hidden_field_empty(request):
    """Make sure hidden 'last_name' field is empty, return True or False"""
    if request.form['last_name'] == "":
        return True
    return False


def is_valid_token(request):
    """Make sure request's 'token' field matches TOKEN in conf.py"""
    if request.form['token'] == conf.TOKEN:
        return True
    return False


def create_error_url(error_number, message, request):
    """Construct error message and append to redirect url"""
    values = [('error', str(error_number)), ('message', message)]
    query = urllib.urlencode(values)
    return request.form['redirect'] + '?' + query


def strip_query(url):
    """Remove query string from a url"""
    return url.split('?', 1)[0]


def format_message(msg):
    """Formats a dict (msg) into a nice-looking string"""
    # Ignore these fields when writing to formatted message
    hidden_fields = ['redirect', 'last_name', 'token', 'op',
                     'name', 'email', 'mail_subject', 'send_to']
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


def convert_key_to_title(snake_case_key):
    """Replace underscores with spaces and convert to title case"""
    return snake_case_key.replace('_', ' ').title()


def set_mail_subject(message):
    """
    Returns a string to be used as a subject in an email
    Default is 'Form Submission'
    """
    # If key exists in the message dict and has content return the content
    if 'mail_subject' in message and message['mail_subject']:
        return message['mail_subject']
    # Otherwise return default
    return 'Form Submission'


def set_mail_from(message):
    """
    Returns a string to be used to fill the 'from' field of and email
    If no from address is provided in the html form, return 'from_default'
    """
    # If a from address is included in html form, return it
    if 'mail_from' in message and message['mail_from']:
        return message['mail_from']
    # Otherwise, return from_default
    return 'from_default'


def send_to_address(message):
    """
    Returns a string to be used as the address the email is being sent to

    Default is 'support@osuosl.org'
    """
    # If a send to address is included in html form, return its assoc. string
    if 'send_to' in message and message['send_to']:
        return message['send_to']
    # Otherwise, return default
    return 'default'


def send_email(msg, subject, send_to_email='default',
               mail_from='from_default'):
    """Sets up and sends the email"""
    # Format the message and set the subject
    msg_send = MIMEText(str(msg))
    msg_send['Subject'] = subject
    msg_send['To'] = conf.EMAIL[send_to_email]

    # Sets up a temporary mail server to send from
    smtp = smtplib.SMTP(conf.SMTP_HOST)
    # Attempts to send the mail to EMAIL, with the message formatted as a string
    try:
        if (mail_from != 'from_default'):
            smtp.sendmail(mail_from,
                          conf.EMAIL[send_to_email],
                          msg_send.as_string())
            smtp.quit()
        else:
            smtp.sendmail(conf.FROM['from_default'],
                          conf.EMAIL[send_to_email],
                          msg_send.as_string())
            smtp.quit()
    except RuntimeError:
        smtp.quit()


# Start application
if __name__ == '__main__':
    from werkzeug.serving import run_simple
    # Creates the app
    app = create_app()
    # Starts the listener
    run_simple(conf.HOST, conf.PORT, app, use_debugger=True, use_reloader=True)
