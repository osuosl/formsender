#!/bin/sh
exec gunicorn \
  -u nobody \
  -g nobody \
  --access-logfile '-' \
  --error-logfile '-' \
  --log-file "-" \
  --forwarded-allow-ips="140.211.9.50,140.211.9.52,140.211.9.53" \
  -w 4 \
  -b 0.0.0.0:5000 \
  'request_handler:create_app()'
