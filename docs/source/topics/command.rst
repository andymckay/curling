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
* --data-binary: binary data to be sent, cannot be used with --data.
  When this option is used, Content-Disposition and Content-Type headers are
  automatically set.
* -X or --request: the verb to be sent, e.g.: curling -X POST to send a POST
* -i or --include: include the HTTP response headers in the output (legacy
  only)
* -l or --legacy: use the old style command (see below)

The --data and --data-binary options can be the special value '@-', in which
case the data is read from stdin.

Legacy
======

The legacy command just uses the requests library to make requests, not the
actual curling library. Since that's rather daft, I hope to remove that soon.

Config
======

This is not available in the legacy code. Curling will use the full curling api
from the command line and look for a config file:

* called ``.curling`` and located in your current directory
* called ``.curling`` and located in your home directory

It will assume the file is JSON and try and load it. Then it will look up
values based on the domain you are trying to access. If ``key`` and ``secret``
are present, it will enable oAuth for that URL using those values. The value
``realm`` is optional. Example
config::

   {
     "marketplace-dev.allizom.org": {
       "key": "mkt:some:key",
       "secret": "yup",
       "realm": "optional.realm"
     }
   }

Output
======

If the response is JSON then the output is pretty printed and syntax
highlighted.

If it's HTML and less than 500 characters the output is just displayed in
stdout. If it's any other format then the data is saved to a file and
automatically opened in a browser (useful for verbose Django error pages).
