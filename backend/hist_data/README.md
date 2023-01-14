This directory holds files used to generate the history database data.db.

# Database Tables
-   `events` <br>
    Format:
        `id INT PRIMARY KEY, title TEXT UNIQUE, start INT, start_upper INT, end INT, end_upper INT, fmt INT, ctg TEXT`
        <br>
    Each row has an ID, Wikipedia title, start and end dates, and an event category.
    -   `start*` and `end*` specify start and end dates.
        `start_upper`, `end`, and `end_upper`, are optional.
        If `start_upper` is present, it and `start` denote an uncertain range of start times.
        Similarly for 'end' and 'end_upper'.
    -   `fmt` indicates format info for `start`, `start_upper`, `end`, and `end_upper`.
        -   If 0, they denote a number of years AD (if positive) or BC (if negative).
        -   If 1, they denote a Julian date number.
            This allows simple comparison of events with day-level precision, but only goes back to 4713 BC.
        -   If 2, same as 1, but with a preference for display using the Julian calendar, not the Gregorian calendar.
            For example, William Shakespeare's birth appears 'preferably Julian', but Samuel Johnson's does not.
        -   If 3, same as 2, but where 'start' and 'start_upper' are 'preferably Julian'.
            For example, Galileo Galilei's birth date appears 'preferably Julian', but his death date does not.
-   `pop`: <br>
    Format: `id INT PRIMARY KEY, pop INT` <br>
    Associates each event with a popularity measure (currently an average monthly viewcount)
-   `dist`: <br>
    Format: `scale INT, unit INT, count INT, PRIMARY KEY (scale, unit)` <br>
    Maps scale units to counts of events in them.
-   `event_disp`: <br>
    Format: `id INT, scale INT, unit INT, PRIMARY KEY (id, scale)` <br>
    Maps events to scales+units they are 'displayable' on (used to make displayed events more uniform across time).
-   `img_dist`: <br>
    Like `dist`, but only counts events with images.
-   `img_disp`: <br>
    Like `events_disp`, but only counts events with images.
-   `images`: <br>
    Format: `id INT PRIMARY KEY, url TEXT, license TEXT, artist TEXT, credit TEXT` <br>
    Holds metadata for available images
-   `event_imgs`: <br>
    Format: `id INT PRIMARY KEY, img_id INT` <br>
    Assocates events with images
-   `descs`: <br>
    Format: `id INT PRIMARY KEY, wiki_id INT, desc TEXT` <br>
    Associates an event's enwiki title with a short description.

# Generating the Database

## Environment
Some of the scripts use third-party packages:
-   `indexed_bzip2`: For parallelised bzip2 processing
-   `mwxml`, `mwparserfromhell`: For parsing Wikipedia dumps
-   `requests`: For downloading data

## Generate Event Data
1.  Obtain a Wikidata JSON dump in wikidata/, as specified in it's README.
1.  Run `gen_events_data.py`, which creates `data.db`, and adds the `events` table.
    You might want to set WIKIDATA_FILE in the script to the dump file's name.

## Generate Popularity Data
1.  Obtain an enwiki dump and 'page view files' in enwiki/, as specified in the README.
1.  Run `gen_pop_data.py`, which adds the `pop` table, using data in enwiki/ and the `events` table.

## Generate Event Display Data, and Reduce Dataset
1.  Run `gen_disp_data.py`, which adds the `dist` and `event_disp` tables, and removes events not in `event_disp`.

## Generate Image Data and Popularity Data
1.  In enwiki/, run `gen_img_data.py` which looks at pages in the dump that match entries in `events`,
    looks for infobox image names, and stores them in an image database.
1.  In enwiki/, run `download_img_license_info.py`, which downloads licensing info for found
    images, and adds them to the image database. You should probably first change the USER_AGENT
    script variable to identify yourself to the online API (this is expected
    [best practice](https://www.mediawiki.org/wiki/API:Etiquette)).
1.  In enwiki/, run `download_imgs.py`, which downloads images into enwiki/imgs/. Setting the
    USER_AGENT variable applies here as well.
1.  Run `gen_imgs.py`, which creates resized/cropped images in img/, from images in enwiki/imgs/.
    Adds the `imgs` and `event_imgs` tables. <br>
    The output images might need additional manual changes:
    -   An input image might have no output produced, possibly due to
        data incompatibilities, memory limits, etc.
    -   An input x.gif might produce x-1.jpg, x-2.jpg, etc, instead of x.jpg.
    -   An input image might produce output with unexpected dimensions.
        This seems to happen when the image is very large, and triggers a
        decompression bomb warning.

## Generate Description Data
1.  In enwiki/, run `gen_desc_data.py`, which extracts page descriptions into a database.
1.  Run `gen_desc_data.py`, which adds the `descs` table, using data in enwiki/, and the `events` table.

## Optionally Add Extra Event Data
1.  Additional events can be described in `picked/events.json`, with images for them put
    in `picked` (see the README for details).
1.  Can run `gen_picked_data.py` to add those described events to the database.

## Generation Event Image Display Data
1. Run `gen_disp_data.py img`, which adds the `img_dist` and `img_disp` tables.
