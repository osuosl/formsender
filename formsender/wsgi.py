from request_handler import create_app
import conf

if hasattr('conf', 'SENTRY_URI'):
    import sentry_sdk
    from sentry_sdk import capture_exception

    sentry_sdk.init(dsn=conf.SENTRY_URI)
    application = create_app()

else:
    application = create_app()
