import hcl
import os
import re
import warnings
import json
import operator as op

from .list_checker import ListChecker, ValueChecker


class Base:

    def __init__(self, error_on_missing_property=None):
        self._error_on_missing_property = error_on_missing_property

    def may_have_property(self):
        self._error_on_missing_property = None
        return self

    def must_have_property(self):
        self._error_on_missing_property = True
        return self

    def must_not_have_property(self):
        self._error_on_missing_property = False
        return self


class TerraformSyntaxException(Exception):
    pass


class TerraformVariableException(Exception):
    pass


class TerraformUnimplementedInterpolationException(Exception):
    pass


class TerraformVariableParser:

    def __init__(self, string):
        self.string = string
        self.functions = []
        self.variable = ""
        self.state = 0
        self.index = 0

    def parse(self):
        while self.index < len(self.string):
            if self.state == 0:
                if self.string[self.index:self.index+3] == "var":
                    self.index += 3
                    self.state = 1
                else:
                    self.state = 3
                    temp_function = ""
            if self.state == 1:
                temp_var = ""
                while True:
                    self.index += 1
                    if self.index == len(self.string) or self.string[self.index] == ")":
                        self.variable = temp_var
                        self.state = 2
                        break
                    else:
                        temp_var += self.string[self.index]
            if self.state == 2:
                self.index += 1
            if self.state == 3:
                if self.string[self.index] == "(":
                    self.state = 0
                    self.functions.append(temp_function)
                else:
                    temp_function += self.string[self.index]
                self.index += 1


class TerraformPropertyList(Base):

    def __init__(self, validator, error_on_missing_property):
        super().__init__(error_on_missing_property)
        self.properties = []
        self.validator = validator

    def _check_prop(self, result, errors, name, p, prop_value):
        if name in prop_value.keys():
            result.properties.append(p.subproperty(name, prop_value[name]))
        elif self._error_on_missing_property:
            msg = "[{0}] should have property {1}".format(p.dotted(), repr(name))
            errors.append(msg)

    def property(self, name):
        errors = []
        result = TerraformPropertyList(self.validator, self._error_on_missing_property)
        for p in self.properties:
            if isinstance(p.property_value, list):
                for prop in p.property_value:
                    self._check_prop(result, errors, name, p, prop)
            else:
                self._check_prop(result, errors, name, p, p.property_value)

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))
        return result

    def transform(self, prop):
        v = self.validator.substitute_variable_in_property(prop)
        return self.any2str(v)

    def should_equal(self, expected):
        vc = ValueChecker(self.properties, getter=self.transform)
        return vc.should_equal(self.any2str(expected))

    def should_not_equal(self, expected):
        errors = []
        for p in self.properties:
            actual = self.transform(p)
            expected = self.any2str(expected)
            if actual == expected:
                msg = "[{0}] should not be {1}, but it is".format(p.dotted(), repr(expected))
                errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_contain(self, expected_list):
        lc = ListChecker(self.properties, self.validator.substitute_variable_in_property)
        return lc.should_contain(expected_list)

    def should_not_contain(self, missing_list):
        lc = ListChecker(self.properties, self.validator.substitute_variable_in_property)
        return lc.should_not_contain(missing_list)

    def should_have_properties(self, properties_list):
        if type(properties_list) is not list:
            properties_list = [properties_list]

        errors = []
        for p in self.properties:
            property_names = p.property_value.keys()
            for required_property_name in properties_list:
                if required_property_name not in property_names:
                    msg = "[{0}] should have property {1}".format(p.dotted(), repr(required_property_name))
                    errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_not_have_properties(self, properties_list):
        if type(properties_list) is not list:
            properties_list = [properties_list]

        errors = []
        for p in self.properties:
            property_names = p.property_value.keys()
            for excluded_property_name in properties_list:
                if excluded_property_name in property_names:
                    msg = "[{0}] should not have property {1}".format(p.dotted(), repr(excluded_property_name))
                    errors.append(msg)

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def find_property(self, regex):
        pl = TerraformPropertyList(self.validator, self._error_on_missing_property)
        for p in self.properties:
            for nest in p.property_value:
                if self.validator.matches_regex_pattern(nest, regex):
                    pl.properties.append(p.subproperty(nest))
        return pl

    def should_match_regex(self, regex):
        errors = []
        for p in self.properties:
            actual = self.validator.substitute_variable_in_property(p)
            if not self.validator.matches_regex_pattern(actual, regex):
                msg = "[{0}] should match regex {1}".format(p.dotted(), repr(regex))
                errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_contain_valid_json(self):
        errors = []
        for p in self.properties:
            actual = self.validator.substitute_variable_in_property(p)
            try:
                json.loads(actual)
            except json.JSONDecodeError as e:
                msg = "[{0}] is not valid json: {1}".format(p.dotted(), e)
                errors.append(msg)

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def any2str(self, v):
        return self.bool2str(self.int2str(v))

    def bool2str(self, bool):
        if str(bool).lower() in ["true"]:
            return "True"
        if str(bool).lower() in ["false"]:
            return "False"
        return bool

    def int2str(self, property_value):
        if type(property_value) is int:
            property_value = str(property_value)
        return property_value


class TerraformProperty:

    def __init__(self, resource_type, resource_name, property_name, property_value):
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.property_name = property_name
        self.property_value = property_value

    def dotted(self):
        return "{0}.{1}.{2}".format(self.resource_type, self.resource_name, self.property_name)

    def get_property_value(self, validator):
        return validator.substitute_variable_values_in_string(self.property_value)

    def name(self):
        return self.property_name

    def subproperty(self, name, value=None):
        curname = "{0}.{1}".format(self.resource_name, self.property_name)
        if value is None:
            value = self.property_value[name]
        return TerraformProperty(self.resource_type, curname, name, value)


class TerraformResource:

    def __init__(self, resource_type, resource_name, config):
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.config = config

    def dotted(self):
        return "{0}.{1}".format(self.resource_type, self.resource_name)

    def name(self):
        return self.resource_name

    def subproperty(self, name):
        return TerraformProperty(self.resource_type, self.resource_name, name, self.config[name])


class TerraformResourceList(Base):

    def __init__(self, validator, resource_types, resources, error_on_missing_property):
        super().__init__(error_on_missing_property)
        self.resource_list = []

        if type(resource_types) is not list:
            all_resource_types = list(resources.keys())
            regex = resource_types
            resource_types = []
            for resource_type in all_resource_types:
                if validator.matches_regex_pattern(resource_type, regex):
                    resource_types.append(resource_type)

        for resource_type in resource_types:
            if resource_type in resources.keys():
                for resource in resources[resource_type]:
                    self.resource_list.append(TerraformResource(resource_type, resource, resources[resource_type][resource]))

        self.resource_types = resource_types
        self.validator = validator

    def property(self, property_name):
        errors = []
        pl = TerraformPropertyList(self.validator, self._error_on_missing_property)
        if len(self.resource_list) > 0:
            for resource in self.resource_list:
                print("XX {0}".format(resource.resource_name))
                if property_name in resource.config.keys():
                    pl.properties.append(resource.subproperty(property_name))
                elif self._error_on_missing_property:
                    msg = "[{0}] should have property {1}".format(resource.dotted(), repr(property_name))
                    errors.append(msg)

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

        return pl

    def find_name(self, regex):
        resources = {}
        for r in self.resource_list:
            if re.match(regex, r.resource_name):
                if r.resource_type not in resources:
                    resources[r.resource_type] = {}
                resources[r.resource_type][r.resource_name] = r.config
        return TerraformResourceList(self.validator, self.resource_types, resources, self._error_on_missing_property)

    def find_property(self, regex):
        pl = TerraformPropertyList(self.validator, self._error_on_missing_property)
        if len(self.resource_list) > 0:
            for resource in self.resource_list:
                for p in resource.config:
                    if self.validator.matches_regex_pattern(p, regex):
                        pl.properties.append(resource.subproperty(p))
        return pl

    def with_property(self, property_name, regex):
        pl = TerraformResourceList(self.validator, self.resource_types, {}, self._error_on_missing_property)

        if len(self.resource_list) > 0:
            for resource in self.resource_list:
                for p in resource.config:
                    if p == property_name:
                        tf_property = resource.subproperty(property_name)
                        actual = self.validator.substitute_variable_in_property(tf_property)
                        if self.validator.matches_regex_pattern(actual, regex):
                            pl.resource_list.append(resource)

        return pl

    def should_have_properties(self, properties_list):
        errors = []

        if type(properties_list) is not list:
            properties_list = [properties_list]

        if len(self.resource_list) > 0:
            for resource in self.resource_list:
                property_names = resource.config.keys()
                for required_property_name in properties_list:
                    if required_property_name not in property_names:
                        msg = "[{0}] should have property {1}".format(resource.dotted(), repr(required_property_name))
                        errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_not_have_properties(self, properties_list):
        errors = []

        if type(properties_list) is not list:
            properties_list = [properties_list]

        if len(self.resource_list) > 0:
            for resource in self.resource_list:
                property_names = resource.config.keys()
                for excluded_property_name in properties_list:
                    if excluded_property_name in property_names:
                        msg = "[{0}] should not have property {1}".format(resource.dotted(), repr(excluded_property_name))
                        errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def name(self):
        return ValueChecker(self.resource_list, getter=op.attrgetter('resource_name'))


class TerraformVariable:

    def __init__(self, validator, name, value):
        self.validator = validator
        self.name = name
        self.value = value

    def default_value_exists(self):
        errors = []
        if self.value == None:
            errors.append("Variable {0} should have a default value".format(repr(self.name)))

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def default_value_equals(self, expected):
        errors = []

        if self.value != expected:
            errors.append("Variable {0} should have a default value {1}, but it is {2}".format(repr(self.name),
                                                                                              repr(expected),
                                                                                              repr(self.value)))
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def default_value_matches_regex(self, regex):
        errors = []
        if not self.validator.matches_regex_pattern(self.value, regex):
            errors.append("Variable {0} should have a default value that matches regex {1}, but it is {2}".format(
                repr(self.name), repr(regex), repr(self.value)))

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))


class Validator(Base):

    def __init__(self, path=None):
        super().__init__(None)
        self.variable_expand = False
        if type(path) is not dict:
            if path is not None:
                self.terraform_config = self.parse_terraform_directory(path)
        else:
            self.terraform_config = path

    def resources(self, type):
        if 'resource' not in self.terraform_config.keys():
            resources = {}
        else:
            resources = self.terraform_config['resource']
        return TerraformResourceList(self, type, resources, self._error_on_missing_property)

    def variable(self, name):
        return TerraformVariable(self, name, self.get_terraform_variable_value(name))

    def enable_variable_expansion(self):
        self.variable_expand = True

    def disable_variable_expansion(self):
        self.variable_expand = False

    def parse_terraform_directory(self, path):
        terraform_string = ""
        for directory, _, files in os.walk(path):
            for file in files:
                if (file.endswith(".tf")):
                    with open(os.path.join(directory, file)) as fp:
                        new_terraform = fp.read()
                        try:
                            hcl.loads(new_terraform)
                        except ValueError as e:
                            raise TerraformSyntaxException("Invalid terraform configuration in {0}\n{1}".format(
                                os.path.join(directory, file), e))
                        terraform_string += new_terraform
        terraform = hcl.loads(terraform_string)
        return terraform

    def get_terraform_resources(self, name, resources):
        if name not in resources.keys():
            return []
        return self.convert_to_list(resources[name])

    def matches_regex_pattern(self, variable, regex):
        return not (self.get_regex_matches(regex, variable) is None)

    def get_regex_matches(self, regex, variable):
        if regex[-1:] != "$":
            regex = regex + "$"

        if regex[0] != "^":
            regex = "^" + regex

        variable = str(variable)
        if '\n' in variable:
            return re.match(regex, variable, re.DOTALL)
        return re.match(regex, variable)

    def get_terraform_variable_value(self, variable):
        if ('variable' not in self.terraform_config.keys()) or (variable not in self.terraform_config['variable'].keys()):
            raise TerraformVariableException(
                "There is no Terraform variable {0}".format(repr(variable)))
        if 'default' not in self.terraform_config['variable'][variable].keys():
            return None
        return self.terraform_config['variable'][variable]['default']

    def substitute_variable_in_property(self, p):
        return self.substitute_variable_values_in_string(p.property_value)

    def substitute_variable_values_in_string(self, s):
        if self.variable_expand:
            if not isinstance(s, dict):
                for variable in self.list_terraform_variables_in_string(s):
                    a = TerraformVariableParser(variable)
                    a.parse()
                    variable_default_value = self.get_terraform_variable_value(
                        a.variable)
                    if variable_default_value != None:
                        for function in a.functions:
                            if function == "lower":
                                variable_default_value = variable_default_value.lower()
                            elif function == "upper":
                                variable_default_value = variable_default_value.upper()
                            else:
                                raise TerraformUnimplementedInterpolationException(
                                    "The interpolation function {0} has not been implemented in Terraform Validator yet. Suggest you run disable_variable_expansion().".format(repr(function)))
                        s = s.replace("${" + variable + "}",
                                      variable_default_value)
        return s

    def list_terraform_variables_in_string(self, s):
        return re.findall('\\${(.*?)}', str(s))

    def convert_to_list(self, nested_resources):
        if not type(nested_resources) == list:
            nested_resources = [nested_resources]
        return nested_resources
