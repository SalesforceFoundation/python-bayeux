python-bayeux
==========================

A bayeux client for python.  Built on gevent and requests.

As of version 1.0.0, code using this library must do

```python
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

- [modern-package-template](http://pypi.python.org/pypi/modern-package-template)
- [requests](https://pypi.python.org/pypi/requests)
- [gevent](http://www.gevent.org/)
- [py.test](http://doc.pytest.org/en/latest/index.html)
- [pytest-cov](https://pypi.python.org/pypi/pytest-cov)
