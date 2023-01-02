This directory holds data for additional manually-picked events.

Files
=====
-   events.json <br>
    Encodes an array of objects, each describing an event to add.
    For example:

        [{
            "title": "COVID-19 Pandemic",
            "start": 2458919,
            "start_upper": null,
            "end": null,
            "end_upper": null,
            "fmt": 2,
            "ctg": "event",
            "image": {
                "file": "covid.jpg",
                "url": "https://en.wikipedia.org/wiki/File:Covid-19_SP_-_UTI_V._Nova_Cachoeirinha.jpg",
                "license": "cc-by-sa 4.0",
                "artist": "Gustavo Basso",
                "credit": ""
            },
            "desc": "Global pandemic caused by the virus SARS-CoV-2",
            "pop": 100
        }]

    The `image.file` field should name an image file in this directory.
    Other fields correspond to those in the `events`, `images`, `descs`, and `pop` tables (see `../README.md`).
