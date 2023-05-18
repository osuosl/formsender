from request_handler import create_app
import conf

if conf.SENTRY_URI:
    import sentry_sdk

    application = Sentry(
        create_app(),
        sentry_sdk.init(
            dsn=conf.SENTRY_URI
        )
    )

else:
    application = create_app()