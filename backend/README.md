# Files
-   `hist_data/`: Holds scripts for generating the history database and images
-   `chrona.py`: WSGI script that serves data from the history database
-   `server.py`: Basic dev server that serves the WSGI script and image files
-   `tests/`: Holds unit testing scripts <br>
    Running all tests: `python -m unittest discover -s tests` <br>
    Running a particular test: `python -m unittest tests/test_script1.py` <br>
    Getting code coverage info (uses python package 'coverage'): <br>
    1. `coverage run -m unittest discover -s tests`
    2. `coverage report -m > report.txt`
