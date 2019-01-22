import re

class ListChecker:
    def __init__(self, objects, label, getter=lambda x: x):
        self._objects = objects
        self._label = label
        self._getter = getter

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
