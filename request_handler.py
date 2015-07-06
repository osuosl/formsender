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

#WSGI Application
class Forms(object):

    def __init__(self):
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                                     autoescape=True)
        self.url_map = Map([Rule('/', endpoint='form_page')])

    def render_template(self, template_name, **context):
        t = self.jinja_env.get_template(template_name)
        return Response(t.render(context), mimetype='text/html')

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
            return True
        except:
            s.quit()
            return False

    def on_form_page(self, request):
        error = None
        message = create_msg(request)
        if message:
            self.send_email(message)
            return self.render_template('submitted.html', error=error, url=message)
        return self.render_template('index.html', error=error, url=message)


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


# Application logic
if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = create_app()
    run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
