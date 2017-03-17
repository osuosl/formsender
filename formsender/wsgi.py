from request_handler import create_app

if RAVEN_URI:
    from raven import Client
    from raven.middleware import Sentry

    application = Sentry(
        create_app(),
        Client(RAVEN_URI)
    )

else:
    application = create_app()
