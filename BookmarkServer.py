#!/usr/bin/env python3
#
# A *bookmark server* or URI shortener that maintains a mapping (dictionary)
# between short names and long URIs, checking that each new URI added to the
# mapping actually works (i.e. returns a 200 OK).
#
# This server is intended to serve three kinds of requests:
#
#   * A GET request to the / (root) path.  The server returns a form allowing
#     the user to submit a new name/URI pairing.  The form also includes a
#     listing of all the known pairings.
#   * A POST request containing "longuri" and "shortname" fields.  The server
#     checks that the URI is valid (by requesting it), and if so, stores the
#     mapping from shortname to longuri in its dictionary.  The server then
#     redirects back to the root path.
#   * A GET request whose path contains a short name.  The server looks up
#     that short name in its dictionary and redirects to the corresponding
#     long URI.

import os
import threading
from socketserver import ThreadingMixIn
import http.server
import requests
from urllib.parse import unquote, parse_qs


class ThreadHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    "This is an HTTPServer that supports thread-based concurrency."
    pass


memory = {}

form = '''<!DOCTYPE html>
<title>Bookmark Server</title>
<form method="POST">
    <label>Long URI:
        <input name="longuri">
    </label>
    <br>
    <label>Short name:
        <input name="shortname">
    </label>
    <br>
    <button type="submit">Save it!</button>
</form>
<p>URIs I know about:
<pre>
{}
</pre>
'''


def CheckURI(uri, timeout=5):
    '''Check whether this URI is reachable, i.e. does it return a 200 OK?

    This function returns True if a GET request to uri returns a 200 OK, and
    False if that GET request returns any other response, or doesn't return
    (i.e. times out).
    '''
    # 1. Write this function.  Delete the following line.
    try:
        r = requests.get(url=uri, timeout=2.0)
    except requests.exceptions.MissingSchema:
        return False
    else:
        return r.status_code == 200


class Shortener(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # A GET request will either be for / (the root path) or for /some-name.
        # Strip off the / and we have either empty string or a name.
        name = unquote(self.path[1:])

        if name:
            if name in memory:
                print('Redirect: ln 87')
                # 2. Send a 303 redirect to the long URI in memory[name].
                self.send_response(303)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.send_header('Location', memory[name])
                self.end_headers()
            else:
                print('Unknown name: ln 94')
                # We don't know that name! Send a 404 error.
                self.send_response(404)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write("I don't know '{}'.".format(name).encode())
        else:
            print('Root path: ln 101')
            # Root path. Send the form.
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            # List the known associations in the form.
            known = "\n".join("{} : {}".format(key, memory[key])
                              for key in sorted(memory.keys()))
            self.wfile.write(form.format(known).encode())

    def do_POST(self):
        # Decode the form data.
        length = int(self.headers.get('Content-length', 0))
        body = self.rfile.read(length).decode()
        params = parse_qs(body)

        # Check that the user submitted the form fields.
        expected_params = ["longuri", "shortname"]
        missing_params = [p for p in expected_params if p not in params]
        if missing_params:
            # 3. Serve a 400 error with a useful message.
            msg = (
                "Required parameters missing: {}"
            ).format(', '.join('"' + x + '"' for x in missing_params))
            self.send_error(400, msg)

        longuri = params["longuri"][0]
        shortname = params["shortname"][0]

        if CheckURI(longuri):
            # This URI is good!  Remember it under the specified name.
            memory[shortname] = longuri

            # 4. Serve a redirect to the root page (the form).
            self.send_response(303)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Location', '/')
            self.end_headers()
        else:
            # Didn't successfully fetch the long URI.

            # 5. Send a 404 error with a useful message.
            self.send_error(404, "Bad URI provided: {}".format(longuri))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000)) # Use 8000 if PORT not found
    server_address = ('', port)
    httpd = ThreadHTTPServer(server_address, Shortener)
    httpd.serve_forever()
