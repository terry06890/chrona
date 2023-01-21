#!/usr/bin/python3

"""
Runs a basic dev server that serves a WSGI script and image files
"""

from typing import Iterable
import os
from wsgiref import simple_server, util
import mimetypes
from histplorer import application

import argparse
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.parse_args()

def wrappingApp(environ: dict[str, str], start_response) -> Iterable[bytes]:
	""" WSGI handler that uses 'application', but also serves image files """
	urlPath = environ['PATH_INFO']
	if urlPath.startswith('/data/'):
		return application(environ, start_response) # Run WSGI script
	elif urlPath.startswith('/hist_data/img/'): # Serve image file
		imgPath = os.path.join(os.getcwd(), urlPath[1:])
		if os.path.exists(imgPath):
			imgType = mimetypes.guess_type(imgPath)[0]
			start_response('200 OK', [('Content-type', imgType)])
			return util.FileWrapper(open(imgPath, 'rb'))
		else:
			start_response('404 Not Found', [('Content-type', 'text/plain')])
			return [b'No image found']
	else:
		start_response('404 Not Found', [('Content-type', 'text/plain')])
		return [b'Unrecognised path']

# Start server
with simple_server.make_server('', 8000, wrappingApp) as httpd:
    print('Serving HTTP on port 8000...')
    httpd.serve_forever()
