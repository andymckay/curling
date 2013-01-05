.. _command:

Command
-------

Curling comes with a command line that mirrors curl and curlish, just with
a lot less arguments::

        curling http://slumber.in/api/v1/
        {
                "note": {
                        "list_endpoint": "/api/v1/note/",
                        "schema": "/api/v1/note/schema/"
                }
        }

Arguments
=========

All requests are formatted as JSON before being sent to the server and the
Content-Type is set to `application/json` so you don't have to set it. Other
options:

* -h or --help: show help
* -d or --data: data to be sent, must be valid JSON
* -X or --request: the verb to be sent, e.g.: curling -X POST to send a POST
* -i or --include: include the HTTP response headers in the output

Output
======

If the response is JSON then the output is pretty printed and syntax
highlighted.

If it's HTML and less than 500 characters the output is just displayed in
stdout. If it's any other format then the data is saved to a file and
automatically opened in a browser (useful for verbose Django error pages).
