#!/bin/bash
set -e

sed -i -e "s|base: .*,|base: '/chrona/',|" vite.config.ts
sed -i -e "s|SERVER_DATA_URL = .*|SERVER_DATA_URL = (new URL(window.location.href)).origin + '/chrona/data/'|" \
	-e "s|SERVER_IMG_PATH = .*|SERVER_IMG_PATH = '/img/chrona/'|" src/lib.ts
sed -i -e 's|DB_FILE = .*|DB_FILE = "/usr/local/www/db/chrona.db"|' backend/chrona.py
