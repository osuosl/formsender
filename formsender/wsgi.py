from request_handler import create_app
import conf

if conf.SENTRY_URI:
    import sentry_sdk
    from sentry_sdk import capture_exception

    sentry_sdk.init(dsn=conf.SENTRY_URI)
    application = create_app()

    # intentional error for testing
    try:
        division_by_zero = 1 / 0
    except Exception as e:
        capture_exception(e)

else:
    application = create_app()
