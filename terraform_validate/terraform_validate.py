import hcl
import os
import re
import warnings
import json
import operator as op

from .list_checker import ListChecker

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

    def _check_prop(self, result, errors, name, property, prop_value):
        attr_name = "{0}.{1}".format(property.resource_name, property.property_name)
        if name in prop_value.keys():
            p = TerraformProperty( property.resource_type, attr_name, name, prop_value[name])
            result.properties.append(p)
        elif self._error_on_missing_property:
            msg = "[{0}.{1}] should have property: '{2}'".format(property.resource_type, attr_name, name)
            errors.append(msg)

    def property(self, name):
        errors = []
        result = TerraformPropertyList(self.validator, self._error_on_missing_property)
        for property in self.properties:
            if isinstance(property.property_value, list):
                for prop in property.property_value:
                    self._check_prop(result, errors, name, property, prop)
            else:
                self._check_prop(result, errors, name, property, property.property_value)

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))
        return result

    def should_equal(self, expected):
        errors = []
        for property in self.properties:
            actual = self.validator.substitute_variable_values_in_string(property.property_value)

            expected = self.int2str(expected)
            actual = self.int2str(actual)
            expected = self.bool2str(expected)
            actual = self.bool2str(actual)

            if actual != expected:
                msg = "[{0}] should be '{1}'. Is: '{2}'".format(property.dotted(), expected, actual)
                errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_not_equal(self, expected):
        errors = []
        for property in self.properties:
            actual = self.validator.substitute_variable_values_in_string(property.property_value)
            actual = self.int2str(actual)
            expected = self.int2str(expected)
            expected = self.bool2str(expected)
            actual = self.bool2str(actual)

            if actual == expected:
                msg = "[{0}] should not be '{1}'. Is: '{2}'".format(property.dotted(), expected, actual)
                errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def list_should_contain(self, values_list):
        errors = []

        if type(values_list) is not list:
            values_list = [values_list]

        for property in self.properties:

            actual = self.validator.substitute_variable_values_in_string(property.property_value)
            values_missing = []
            for value in values_list:
                if value not in actual:
                    values_missing.append(value)

            if len(values_missing) > 0:
                if type(actual) is list:
                    actual = [str(x) for x in actual]  # fix 2.6/7
                msg = "[{0}] '{1}' should contain '{2}'.".format(property.dotted(), actual, values_missing)
                errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def list_should_not_contain(self, values_list):
        errors = []

        if type(values_list) is not list:
            values_list = [values_list]

        for property in self.properties:

            actual = self.validator.substitute_variable_values_in_string(
                property.property_value)
            values_missing = []
            for value in values_list:
                if value in actual:
                    values_missing.append(value)

            if len(values_missing) > 0:
                if type(actual) is list:
                    actual = [str(x) for x in actual]  # fix 2.6/7
                msg = "[{0}] '{1}' should not contain '{2}'.".format(property.dotted(),actual, values_missing)
                errors.append(msg)

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_have_properties(self, properties_list):
        errors = []

        if type(properties_list) is not list:
            properties_list = [properties_list]

        for property in self.properties:
            property_names = property.property_value.keys()
            for required_property_name in properties_list:
                if required_property_name not in property_names:
                    msg = "[{0}] should have property: '{1}'".format(property.dotted(), required_property_name)
                    errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_not_have_properties(self, properties_list):
        errors = []

        if type(properties_list) is not list:
            properties_list = [properties_list]

        for property in self.properties:
            property_names = property.property_value.keys()
            for excluded_property_name in properties_list:
                if excluded_property_name in property_names:
                    msg = "[{0}] should not have property: '{1}'".format(property.dotted(), excluded_property_name)
                    errors.append(msg)

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def find_property(self, regex):
        list = TerraformPropertyList(self.validator, self._error_on_missing_property)
        for property in self.properties:
            for nested_property in property.property_value:
                if self.validator.matches_regex_pattern(nested_property, regex):
                    name = "{0}.{1}".format(property.resource_name, property.property_name)
                    p = TerraformProperty(property.resource_type, name, nested_property, property.property_value[nested_property])
                    list.properties.append(p)
        return list

    def should_match_regex(self, regex):
        errors = []
        for property in self.properties:
            actual = self.validator.substitute_variable_values_in_string(
                property.property_value)
            if not self.validator.matches_regex_pattern(actual, regex):
                name = "{0}.{1}".format(property.resource_name, property.property_name)
                msg = "[{0}.{1}] should match regex '{2}'".format(property.resource_type, name, regex)
                errors.append(msg)

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_contain_valid_json(self):
        errors = []
        for property in self.properties:
            actual = self.validator.substitute_variable_values_in_string(
                property.property_value)
            try:
                json.loads(actual)
            except json.JSONDecodeError as e:
                msg = "[{0}] is not valid json: {1}".format( property.dotted(), e)
                errors.append(msg)

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

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


class TerraformResource:

    def __init__(self, type, name, config):
        self.type = type
        self.name = name
        self.config = config

    def dotted(self):
        return "{0}.{1}".format(self.type, self.name)


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
                    self.resource_list.append(TerraformResource(
                        resource_type, resource, resources[resource_type][resource]))

        self.resource_types = resource_types
        self.validator = validator

    def property(self, property_name):
        errors = []
        list = TerraformPropertyList(self.validator, self._error_on_missing_property)
        if len(self.resource_list) > 0:
            for resource in self.resource_list:
                if property_name in resource.config.keys():
                    list.properties.append(TerraformProperty(
                        resource.type, resource.name, property_name, resource.config[property_name]))
                elif self._error_on_missing_property:
                    msg = "[{0}.{1}] should have property: '{2}'".format(resource.type, resource.name, property_name)
                    errors.append(msg)

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

        return list

    def find_property(self, regex):
        list = TerraformPropertyList(self.validator, self._error_on_missing_property)
        if len(self.resource_list) > 0:
            for resource in self.resource_list:
                for property in resource.config:
                    if self.validator.matches_regex_pattern(property, regex):
                        list.properties.append(TerraformProperty(resource.type,
                                                                 resource.name,
                                                                 property,
                                                                 resource.config[property]))
        return list

    def with_property(self, property_name, regex):
        list = TerraformResourceList(self.validator, self.resource_types, {}, self._error_on_missing_property)

        if len(self.resource_list) > 0:
            for resource in self.resource_list:
                for property in resource.config:
                    if(property == property_name):
                        tf_property = TerraformProperty(
                            resource.type, resource.name, property_name, resource.config[property_name])
                        actual = self.validator.substitute_variable_values_in_string(
                            tf_property.property_value)
                        if self.validator.matches_regex_pattern(actual, regex):
                            list.resource_list.append(resource)

        return list

    def should_have_properties(self, properties_list):
        errors = []

        if type(properties_list) is not list:
            properties_list = [properties_list]

        if len(self.resource_list) > 0:
            for resource in self.resource_list:
                property_names = resource.config.keys()
                for required_property_name in properties_list:
                    if required_property_name not in property_names:
                        errors.append(
                            "[{0}.{1}] should have property: '{2}'".format(resource.type,
                                                                           resource.name,
                                                                           required_property_name))
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
                        errors.append(
                            "[{0}.{1}] should not have property: '{2}'".format(resource.type,
                                                                               resource.name,
                                                                               excluded_property_name))
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def name(self):
        return ListChecker(self.resource_list, 'name', op.attrgetter('name'))


class TerraformVariable:

    def __init__(self, validator, name, value):
        self.validator = validator
        self.name = name
        self.value = value

    def default_value_exists(self):
        errors = []
        if self.value == None:
            errors.append(
                "Variable '{0}' should have a default value".format(self.name))

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def default_value_equals(self, expected):
        errors = []

        if self.value != expected:
            errors.append("Variable '{0}' should have a default value of {1}. Is: {2}".format(self.name,
                                                                                              expected,
                                                                                              self.value))
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def default_value_matches_regex(self, regex):
        errors = []
        if not self.validator.matches_regex_pattern(self.value, regex):
            errors.append("Variable '{0}' should have a default value that matches regex '{1}'. Is: {2}".format(
                self.name, regex, self.value))

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
                "There is no Terraform variable '{0}'".format(variable))
        if 'default' not in self.terraform_config['variable'][variable].keys():
            return None
        return self.terraform_config['variable'][variable]['default']

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
                                    "The interpolation function '{0}' has not been implemented in Terraform Validator yet. Suggest you run disable_variable_expansion().".format(function))
                        s = s.replace("${" + variable + "}",
                                      variable_default_value)
        return s

    def list_terraform_variables_in_string(self, s):
        return re.findall('\\${(.*?)}', str(s))

    def convert_to_list(self, nested_resources):
        if not type(nested_resources) == list:
            nested_resources = [nested_resources]
        return nested_resources
