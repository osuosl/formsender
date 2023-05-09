#!/bin/sh
exec gunicorn \
  -u nobody \
  -g nobody \
  --access-logfile '-' \
  --error-logfile '-' \
  --log-file "-" \
  -w 4 \
  -b 0.0.0.0:5000 \
  'request_handler:create_app()'
