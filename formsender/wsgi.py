from request_handler import create_app
import conf

if conf.RAVEN_URI:
    from raven import Client
    from raven.middleware import Sentry

    application = Sentry(
        create_app(),
        Client(conf.RAVEN_URI)
    )

else:
    application = create_app()
