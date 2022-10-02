This directory holds files used to generate the history database data.db.

# Database Tables
-   `events` <br>
    Format:
        `id INT PRIMARY KEY, title TEXT UNIQUE, start INT, start_upper INT, end INT, end_upper INT, fmt INT, ctg TEXT`
        <br>
    Each row has a Wikidata ID, Wikipedia title, start and end dates, and an event category.
    -   `start*` and `end*` specify start and end dates.
        `start_upper`, `end`, and `end_upper`, are optional.
        If `start_upper` is present, it and `start` denote an uncertain range of start times.
        Similarly for 'end' and 'end_upper'.
    -   `fmt` indicates format info for `start`, `start_upper`, `end`, and `end_upper`.
        -   If 1, they denote a Julian date (with 0.5 removed to align with midnight).
            This allows simple comparison of events with day-level precision, but only goes back to 4713 BCE.
        -   If 2, same as 1, but dates are preferably displayed using the Gregorian calendar, not the Julian calendar.
            For example, William Shakespeare's birth appears 'preferably Julian', but Samuel Johnson's does not.
        -   If 3, same as 1, but 'end' and 'end_upper' are 'preferably Gregorian'.
            For example, Galileo Galilei's birth date appears 'preferably Julian', but his death date does not.
        -   If 0, they denote a number of years CE (if positive) or BCE (if negative).
-   `pop`: <br>
    Format: `id INT PRIMARY KEY, pop INT` <br>
    Associates each event with a popularity measure (currently an average monthly viewcount)

# Generating the Database

## Environment
Some of the scripts use third-party packages:
-   `jdcal`: For date conversion
-   `indexed_bzip2`: For parallelised bzip2 processing.
-   `mwxml`, `mwparserfromhell`: For parsing Wikipedia dumps.
-   `requests`: For downloading data.

## Generate Event Data
1.  Obtain a Wikidata JSON dump in wikidata/, as specified in it's README.
1.  Run `gen_events_data.py`, which creates `data.db`, and adds the `events` table.

## Generate Popularity Data
1.  Obtain 'page view files' in enwiki/, as specified in it's README.
1.  Run `gen_pop_data.py`, which adds the `pop` table, using data in enwiki/ and the `events` table.

## Generate Image Data and Popularity Data
1.  In enwiki/, run `gen_img_data.py` which looks at pages in the dump that match entries in `events`,
    looks for infobox image names, and stores them in an image database.
    Uses popularity data in enwiki/ to find the top N events in each event category.
1.  In enwiki/, run `download_img_license_info.py`, which downloads licensing info for found
    images, and adds them to the image database.
1.  In enwiki/, run `download_imgs.py`, which downloads images into enwiki/imgs/.
1.  Run

## Generate Description Data
1.  Obtain an enwiki dump in enwiki/, as specified in the README.
1.  In enwiki/, run `gen_dump_index.db.py`, which generates a database for indexing the dump.
1.  In enwiki/, run `gen_desc_data.py`, which extracts page descriptions into a database.
1.  Run 
