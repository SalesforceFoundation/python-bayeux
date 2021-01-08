python-bayeux
==========================

A bayeux client for python.  Built on gevent and requests.

As of version 1.0.0, code using this library must do

```
from gevent import monkey
monkey.patch_all()
```

or some other choice of patch_* functions to prepare gevent before importing this library.

Python 3 is officially supported.


Tests
-----

To run tests, install py.test and pytest-cov in your virtualenv and

$ py.test -rw -rs --cov=src/python_bayeux/ --cov-report html:coverage

View test coverage results at ``./coverage``.


Credits
-------

- `modern-package-template`_
- `requests`_
- `gevent`_
- `py.test`_
- `pytest-cov`_

.. _`modern-package-template`: http://pypi.python.org/pypi/modern-package-template
.. _`requests`: https://pypi.python.org/pypi/requests
.. _`gevent`: http://www.gevent.org/
.. _`py.test`: http://doc.pytest.org/en/latest/index.html
.. _`pytest-cov`: https://pypi.python.org/pypi/pytest-cov
