import inspect
import re

__unittest = True

class IdentityGetter:
    def __call__(self, obj):
        return obj


class StaticLabeler:
    def __init__(self, value):
        self.value = value

    def __call__(self, _):
        return self.value


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


class ListChecker:
    def __init__(self, objects, getter=IdentityGetter(), actual_labeler=repr):
        self._objects = objects
        self._getter = getter
        self._actual_labeler = actual_labeler

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
                errors.append("[{0}] {1} should contain {2}".format(obj.dotted(), self._actual_labeler(actual), repr(missing)))
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
                errors.append("[{0}] {1} should not contain {2}".format(obj.dotted(), self._actual_labeler(actual), repr(found)))
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))


class ValueChecker:
    def __init__(self, objects, getter=IdentityGetter, actual_labeler=repr):
        self._objects = objects
        self._getter = getter
        self._actual_labeler = actual_labeler

    def should_equal(self, expected):
        errors = []
        for obj in self._objects:
            actual = self._getter(obj)
            if actual != expected:
                msg = "[{0}] should equal {1}, but got {2}".format(obj.dotted(), repr(expected), self._actual_labeler(actual))
                errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_not_equal(self, expected):
        errors = []
        for obj in self._objects:
            actual = self._getter(obj)
            if actual == expected:
                msg = "[{0}] should not be {1}, but it is".format(obj.dotted(), repr(expected))
                errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_match(self, regex):
        errors = []
        for obj in self._objects:
            actual = self._getter(obj)
            if re.match(regex, actual) is None:
                msg = "[{0}] should match {1}, but got {2}".format(obj.dotted(), repr(regex), self._actual_labeler(actual))
                errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_not_match(self, regex):
        errors = []
        for obj in self._objects:
            actual = self._getter(obj)
            if re.match(regex, actual) is not None:
                msg = "[{0}] should not match {1}, but got {2}".format(obj.dotted(), repr(regex), self._actual_labeler(actual))
                errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))
