#!/bin/sh
# The backend puts page titles, descriptions and structured data into this HTML shell for search engines.
mkdir -p /shell && cp /srv/index.html /shell/index.html
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
