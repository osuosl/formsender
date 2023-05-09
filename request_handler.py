"""
WSGI Application

This application listens for a form. When a form is submitted, this application
takes the information submitted, formats it into a python dictionary, then
emails it to a specified email
"""

import os
import sys
import werkzeug
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import hashlib
from urllib.parse import urlencode
from urllib.request import urlopen
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.shared_data import SharedDataMiddleware
from jinja2 import Environment, FileSystemLoader
from validate_email import validate_email
from datetime import datetime
import logging
import logging.handlers
import conf
import time
import json
import rt.rest2
import requests.auth


class Forms:
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
        self.url_map = Map([
            Rule('/', endpoint='form_page'),
            Rule('/server-status', endpoint='server_status'),
            ])
        self.logger = logger

    def dispatch_request(self, request):
        """Evaluates request to decide what happens"""
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, 'on_' + endpoint)(request, **values)
        except HTTPException as error:
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

    def on_server_status(self, request):
        """
        Returns an OK on a GET. This is to support health checks by any
        monitoring software on this application
        """
        if request.method == 'GET':
            return Response('OK', status=200)

        # Do not process anything else
        return Response('', status=400)

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
        elif (not (is_hidden_field_empty(request) and
                   is_valid_token(request)) or
                not (is_valid_fields_to_join(request))):
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
        elif not is_valid_recaptcha(request):
            self.error = 'Invalid Recaptcha'
            error_number = 6
            invalid_option = 'name'
        else:
            # If nothing above is true, there is no error
            return False
        # There is an error if it got this far
        self.logger.warning('formsender: received %s: %s from %s',
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
            self.logger.debug('formsender: name is: %s', message['name'])
            self.logger.debug('formsender: sending email from: %s',
                              message['email'])
            # The following are optional fields, so first check that they exist
            # in the message
            if 'send_to' in message and message['send_to']:
                self.logger.debug('formsender: sending email to: %s',
                                  message['send_to'])
            # Should log full request
            self.logger.debug('formsender message: %s', message)

            send_ticket(format_message(message), set_mail_subject(message),
                        send_to_address(message), message['email'])
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


class Controller:
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
        init_hash.update((str(submission)).encode())
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
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

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
                                 check_mx=False,  # DNS resolution is not reliable
                                 verify=False)  # disabling RCPT is occasionally used to fight spam
    if valid_email:
        return valid_email
    return False


def is_valid_recaptcha(request):
    """
    Check that recaptcha responce is valid
    by sending a POST request to google's servers
    """

    recaptchaURL = 'https://www.google.com/recaptcha/api/siteverify'
    recaptcha_response = request.form['g-recaptcha-response']
    secret_key = conf.RECAPTCHA_SECRET
    URLParams = urlencode({
        'secret':    secret_key,
        'response':  recaptcha_response,
        'remote_ip': request.remote_addr,
    })

    google_response   = urlopen(recaptchaURL, URLParams.encode('utf-8')).read()
    recaptcha_result  = json.loads(google_response)
    recaptcha_success = recaptcha_result.get('success', None)

    return recaptcha_success


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


def is_valid_fields_to_join(request):
    """
    Make sure that if request has 'fields_to_join' field, that the specified
    fields to join exist
    """
    if 'fields_to_join' in request.form:
        for field in request.form['fields_to_join'].split(','):
            if field not in request.form and field != 'date':
                return False
    return True


def create_error_url(error_number, message, request):
    """Construct error message and append to redirect url"""
    values = [('error', str(error_number)), ('message', message)]
    query = six.moves.urllib.parse.urlencode(values)
    return request.form['redirect'] + '?' + query


def strip_query(url):
    """Remove query string from a url"""
    return url.split('?', 1)[0]


def format_message(msg):
    """Formats a dict (msg) into a nice-looking string"""
    # Ignore these fields when writing to formatted message
    hidden_fields = ['redirect', 'last_name', 'token', 'op',
                     'name', 'email', 'mail_subject', 'send_to',
                     'fields_to_join_name', 'support', 'ibm_power',
                     'mail_subject_prefix', 'mail_subject_key',
                     'g-recaptcha-response']
    # Contact information goes at the top
    f_message = ("Contact:\n--------\n"
                 "NAME:   {}\nEMAIL:   {}\n"
                 "\nInformation:\n------------\n"
                 .format(msg['name'], msg['email']))

    # If fields_to_join_name specified, add the key, data to the dictionary
    # Otherwise, create fields_to_join key, data and add to dictionary
    if 'fields_to_join' in msg:
        # handle fields_to_join
        fields_to_join = msg['fields_to_join'].split(',')  # list of fields
        joined_data = (':'.join(str(int(time.time())) if field == 'date' else msg[field] for field in fields_to_join))

        # If the fields to join name is specified, and the name does not exist
        # as a key in current msg dictionary
        if 'fields_to_join_name' in msg and msg['fields_to_join_name'] not in msg:
            msg[str(msg['fields_to_join_name'])] = joined_data
        else:
            msg['Fields To Join'] = joined_data
        msg.pop('fields_to_join', None)

    # Create another dictionary that has lowercase title as key and original
    # title as value
    titles = {}
    for key in msg:
        titles[key.lower()] = key

    # Write each formatted key in title case and corresponding message to
    # f_message, each key and message is separated by two lines.
    for key in sorted(titles):
        if key not in hidden_fields:
            f_message += \
                ('{}:\n{}\n\n'.format(convert_key_to_title(titles[key]),
                                        msg[titles[key]]))

    return f_message


def convert_key_to_title(snake_case_key):
    """Replace underscores with spaces and convert to title case"""
    return snake_case_key.replace('_', ' ').title()


def set_mail_subject(message):
    """
    Returns a string to be used as a subject in an email, format:

    message['mail_subject_prefix']: message[message['mail_subject_key']
        or
    message['mail_subject_prefix']
        or
    message[message['mail_subject_key']]
        or the default
    'Form Submission'
    """
    mail_subject = ''
    # If mail_subject_prefix exists in the message dict and has content, add
    # it to the mail_subject string. Then check if mail_subject_key also exists
    # and points to valid data and append if necessary.
    if 'mail_subject_prefix' in message and message['mail_subject_prefix']:
        mail_subject += message['mail_subject_prefix']
        if ('mail_subject_key' in message and
                message['mail_subject_key'] and
                message['mail_subject_key'] in message and
                message[message['mail_subject_key']]):
            mail_subject += ": {}".format(message[message['mail_subject_key']])

    # If mail_subject_key is in the message and the field it points to exists,
    # add it to the mail_subject. It is ok if it is an empty string, because
    # it will just be ignored
    elif ('mail_subject_key' in message and
            message['mail_subject_key'] in message):
        mail_subject += message[message['mail_subject_key']]

    # Otherwise mail_subject if it has something or the default
    return mail_subject if mail_subject else 'Form Submission'

def send_to_address(message):
    """
    Returns a string to be used as the address the email is being sent to

    Default is 'support@osuosl.org'
    """
    # If a send to address is included in html form, return its assoc. string
    if 'send_to' in message and message['send_to']:
        return message['send_to']
    # Otherwise, return default
    return 'OSLSupport'


def send_ticket(msg, subject, send_to_queue='General', mail_from='noreply@osuosl.org'):
    """Creates ticket and sends to RT"""
    # Creates connection to REST
    tracker = rt.rest2.Rt(conf.URL, token=conf.RT_TOKEN)
    # Create ticket and send to RT
    tracker.create_ticket(queue=send_to_queue,
                          subject=subject,
                          content=msg,
                          Requestor=mail_from
                         )


# Start application
if __name__ == '__main__':
    from werkzeug.serving import run_simple
    # Creates the app
    app = create_app()
    # Starts the listener
    run_simple(conf.HOST, conf.PORT, app, use_debugger=True, use_reloader=True)
