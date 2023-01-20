This directory holds data for manually-picked events.

Files
=====
-   events.json <br>
    Encodes an array of objects, each describing an event to modify, add, or delete.
    For example:

        [{
            "id": 81068910,
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

    -   For event modification, specify `id` and one or more other fields to change.
        If `image` is present, all its fields should be present.
    -   For event deletion, specify only `id` or `title`.
    -   For event addition, specify all fields except `id`, and possibly `image` and `desc`.
