# Instructions for Deployment on an Apache server (version 2.4) on Ubuntu (22.04.1 LTS)

1.  Set up the server environment
    -   If Python3 and jsonpickle aren't installed, this can be done using
        `apt-get update; apt-get install python3 python3-jsonpickle`.
    -   Install `mod_wsgi` by running `apt-get install libapache2-mod-wsgi-py3`. This is an Apache module for WSGI.
        It's for running `backend/chrona.py` to serve tree-of-life data, and is used instead of CGI to avoid
        starting a new process for each request.
1.  Change some constants (automated by `prebuild.sh`)
    -   In `src/vite.config.js`: Set `base` to the URL path where Chrona will be accessible (eg: `'/chrona'`)
    -   In `src/lib.ts`:
        -   Set `SERVER_DATA_URL` to the URL where `backend/chrona.py` will be served
            (eg: `'https://terryt.dev/chrona/data'`)
        -   Set `SERVER_IMG_PATH` to the URL path where images will be served (eg: `'/img/chrona'`).
            If you place it within the `base` directory, you'll need to remember to move it when deploying
            a newer production build.
    -   In `backend/chrona.py`: Set `DB_FILE` to where the database will be placed (eg: `'/usr/local/www/db/chrona.db'`)
1.  Generate the client-side production build <br>
    Run `npm run build`. This generates a directory `dist/`.
1.  Copy files to the server (using ssh, sftp, or otherwise)
    1.  Copy `dist/` into Apache's document root, into the directory where Chrona will be served.
        The created directory should match up with the `base` value above (eg: `/var/www/terryt.dev/chrona/`).
    1.  Copy over `backend/chrona.py`. The location should be accessible by Apache (eg: `/usr/local/www/wsgi-scripts/`).
        Remember to set ownership and permissions as needed.
    1.  Copy over `backend/hist_data/data.db`. The result should be denoted by the `DB_FILE` value above.
    1.  Copy over the images in `backend/hist_data/img/`. There are a lot of them, so compressing them
        before transfer is advisable (eg: `tar czf imgs.tar.gz backend/hist_data/img/`). The location should
        match up with the `SERVER_IMG_PATH` value above (eg: `/var/www/terryt.dev/img/chrona/`).
    1.  Edit the site's config file to serve chrona.py. The file path will likely be something like
        `/etc/apache2/sites-available/terryt.dev-le-ssl.conf`, and the edit should add lines like the following,
        likely within a `<VirtualHost>` section:
        
            WSGIScriptAlias /chrona/data /usr/local/www/wsgi-scripts/chrona.py
            <Directory /usr/local/www/wsgi-scripts>
                Require all granted
            </Directory>
        
        The first `WSGIScriptAlias` parameter should match the URL path in `SERVER_URL`, and the second should
        be the location of chrona.py. The `<Directory>` lines enable access for that location.
