#!/bin/bash
set -e

sed -i -e "s|base: .*,|base: '/chrona/',|" vite.config.ts
sed -i -e "s|SERVER_DATA_URL = .*|SERVER_DATA_URL = (new URL(window.location.href)).origin + '/chrona/data/'|" \
	-e "s|SERVER_IMG_PATH = .*|SERVER_IMG_PATH = '/img/chrona/'|" src/lib.ts
sed -i -e 's|DB_FILE = .*|DB_FILE = "/usr/local/www/db/chrona.db"|' backend/chrona.py

# Copy contents of cal.py into chrona.py
TEMP_FILE=_temp
sed -n -e '0,/^# ==/ {/^# ==/d; p}' backend/chrona.py > $TEMP_FILE # Copy chrona.py content before first section
sed -n -e '/^# ===/,$ p' backend/hist_data/cal.py >> $TEMP_FILE # Copy cal.py content at/after first section
echo >> $TEMP_FILE
sed -n -e '/^# ==/,$ p' backend/chrona.py >> $TEMP_FILE # Copy chrona.py content at/after first section
mv $TEMP_FILE backend/chrona.py

# Remove chrona.py's import of cal.py
sed -i -e '/^from hist_data.cal import/d' backend/chrona.py
