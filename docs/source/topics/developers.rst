==========
Developers
==========

Run The Tests
-------------

To hack on Curling, set up a dev environment::

    pip install -r requirements/tests.txt
    pip install -r requirements/docs.txt

Run the test suite::

    nosetests

Build The Docs
--------------

::

    make -C docs/ html
    open docs/build/html/index.html
