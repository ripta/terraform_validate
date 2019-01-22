import inspect
import re


class MaybeErrors:
    def __init__(self):
        self._errors = []

    def append(self, v):
        self._errors.append(v)

    def appendf(self, fmt, *args):
        self._errors.append(fmt.format(*args))

    def assertEmpty(self):
        if len(self._errors) > 0:
            raise AssertionError("\n".join(sorted(self._errors)))

    def empty(self):
        return len(self._errors) <= 0


def with_checkers_from(delegate):
    def inner(cls, name, value):
        def newinner(self, *args, **kwargs):
            lc = ListChecker(self.properties, delegate.__name__, self.validator.substitute_variable_in_property)
            return getattr(delegate, name)(lc, *args, **kwargs)
        return newinner

    def wrapper(cls):
        for name, value in inspect.getmembers(delegate, predicate=inspect.isroutine):
            if not name.startswith('should_'):
                continue
            setattr(cls, name, inner(cls, name, value))
        return cls
    return wrapper


class ListChecker:
    def __init__(self, objects, label, getter=lambda x: x):
        self._objects = objects
        self._label = label
        self._getter = getter

    def should_contain(self, expected_list):
        if not isinstance(expected_list, list):
            expected_list = [expected_list]

        errors = []
        for obj in self._objects:
            actual = self._getter(obj)
            if not isinstance(actual, list):
                errors.append("[{0}] must be a list, but got {1}".format(obj.dotted(), type(actual)))
                continue
            missing = []
            for expected in expected_list:
                if expected not in actual:
                    missing.append(expected)
            if len(missing) > 0:
                errors.append("[{0}] {1} should contain {2}".format(obj.dotted(), repr(actual), repr(missing)))
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_not_contain(self, missing_list):
        if not isinstance(missing_list, list):
            missing_list = [missing_list]

        errors = []
        for obj in self._objects:
            actual = self._getter(obj)
            if not isinstance(actual, list):
                errors.append("[{0}] must be a list, but got {1}".format(obj.dotted(), type(actual)))
                continue
            found = []
            for missing in missing_list:
                if missing in actual:
                    found.append(missing)
            if len(found) > 0:
                errors.append("[{0}] {1} should not contain {2}".format(obj.dotted(), repr(actual), repr(found)))
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_equal(self, expected):
        errors = []
        for obj in self._objects:
            actual = self._getter(obj)
            if actual != expected:
                msg = "[{0}] {1} should equal '{2}', but got '{3}'".format(obj.dotted(), self._label, expected, actual)
                errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_match(self, regex):
        errors = []
        for obj in self._objects:
            actual = self._getter(obj)
            if re.match(regex, actual) is None:
                msg = "[{0}] {1} should match '{2}', but got '{3}'".format(obj.dotted(), self._label, regex, actual)
                errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))
