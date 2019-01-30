import hcl
import os
import re
import warnings
import json
import operator as op

from .list_checker import ListChecker, ValueChecker

__unittest = True

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
        self.variable_type = None
        self.state = 0
        self.index = 0

    def parse(self):
        while self.index < len(self.string):
            if self.state == 0:
                if self.string[self.index:self.index+3] == "var":
                    self.index += 3
                    self.state = 1
                    self.variable_type = "var"
                elif self.string[self.index:self.index+4] == "data":
                    self.index += 4
                    self.state = 1
                    self.variable_type = "data"
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


class TerraformPropertyList:

    def __init__(self, validator):
        self.properties = []
        self.validator = validator

    def __str__(self):
        return "<{0} {1}>".format(self.__class__.__name__, self.properties)

    def must_have_property(self, names):
        return self.property(names, True)

    def must_not_have_property(self, names):
        return self.property(names, False)

    def _check_prop(self, result, errors, names, p, prop_value, error_on_missing_property):
        for name in names:
            if name in prop_value.keys():
                if error_on_missing_property is False:
                    msg = "[{0}] should not have property {1}".format(p.dotted(), repr(name))
                    errors.append(msg)
                else:
                    result.properties.append(p.subproperty(name, prop_value[name]))
            elif error_on_missing_property is True:
                msg = "[{0}] should have property {1}".format(p.dotted(), repr(name))
                errors.append(msg)

    def property(self, names, error_on_missing_property=None):
        if not isinstance(names, list):
            names = [names]

        errors = []
        result = TerraformPropertyList(self.validator)
        for p in self.properties:
            if isinstance(p.property_value, list):
                for prop in p.property_value:
                    self._check_prop(result, errors, names, p, prop, error_on_missing_property)
            else:
                self._check_prop(result, errors, names, p, p.property_value, error_on_missing_property)

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))
        return result

    def transform(self, prop):
        v = self.validator.substitute_variable_in_property(prop)
        return self.any2str(v)

    def should(self, pred):
        vc = ValueChecker(self.properties)
        return vc.should(pred)

    def should_equal(self, expected):
        vc = ValueChecker(self.properties, getter=self.transform)
        return vc.should_equal(self.any2str(expected))

    def should_not_equal(self, expected):
        vc = ValueChecker(self.properties, getter=self.transform)
        return vc.should_not_equal(self.any2str(expected))

    def should_be_empty(self):
        errors = []
        for p in self.properties:
            actual = self.transform(p)
            if actual:
                msg = "[{0}] should be empty, but got {1}".format(p.dotted(), repr(actual))
                errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_not_be_empty(self):
        errors = []
        for p in self.properties:
            actual = self.transform(p)
            if not actual:
                msg = "[{0}] should not be empty, but it is".format(p.dotted())
                errors.append(msg)
        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))

    def should_contain(self, expected_list):
        lc = ListChecker(self.properties, self.validator.substitute_variable_in_property)
        return lc.should_contain(expected_list)

    def should_not_contain(self, missing_list):
        lc = ListChecker(self.properties, self.validator.substitute_variable_in_property)
        return lc.should_not_contain(missing_list)

    def find_property(self, regex):
        pl = TerraformPropertyList(self.validator)
        for p in self.properties:
            for nest in p.property_value:
                if self.validator.matches_regex_pattern(nest, regex):
                    pl.properties.append(p.subproperty(nest))
        return pl

    def should_match(self, regex):
        vc = ValueChecker(self.properties, getter=self.transform)
        return vc.should_match(regex)

    def should_not_match(self, regex):
        vc = ValueChecker(self.properties, getter=self.transform)
        return vc.should_not_match(regex)

    def should_contain_valid_json(self):
        pl = TerraformPropertyList(self.validator)
        errors = []
        for p in self.properties:
            actual = self.validator.substitute_variable_in_property(p)
            try:
                payload = json.loads(actual)
                pl.properties.append(TerraformProperty(p.resource_type, p.resource_name, p.property_name, payload))
            except json.JSONDecodeError as e:
                msg = "[{0}] is not valid json: {1}".format(p.dotted(), e)
                errors.append(msg)

        if len(errors) > 0:
            raise AssertionError("\n".join(sorted(errors)))
        return pl

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

    def __str__(self):
        return "<{0} {1}>".format(self.__class__.__name__, self.dotted())

    def __repr__(self):
        return "{0}({1}, {2}, {3}, {4})".format(self.__class__.__name__, self.resource_type, self.resource_name, self.property_name, self.property_value)

    def dotted(self):
        return "{0}.{1}.{2}".format(self.resource_type, self.resource_name, self.property_name)

    def get_property_value(self, validator):
        return validator.substitute_variable_values_in_string(self.property_value)

    def name(self):
        return self.property_name

    def properties(self):
        return list(self.property_value.copy().keys())

    def subproperty(self, name, value=None):
        curname = "{0}.{1}".format(self.resource_name, self.property_name)
        if value is None:
            value = self.property_value[name]
        return TerraformProperty(self.resource_type, curname, name, value)


class TerraformProperties:
    def __init__(self, objects):
        self._objects = objects

    def __iter__(self):
        yield from self._objects

    def __repr__(self):
        return "TerraformProperties({0})".format(repr(self._objects))


class TerraformResource:

    def __init__(self, resource_type, resource_name, config):
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.config = config

    def __repr__(self):
        return "TerraformResource({0}, {1}, {2})".format(repr(self.resource_type), repr(self.resource_name), repr(self.config))

    def dotted(self):
        return "{0}.{1}".format(self.resource_type, self.resource_name)

    def name(self):
        return self.resource_name

    def subproperty(self, name):
        return TerraformProperty(self.resource_type, self.resource_name, name, self.config[name])


class TerraformResourceList:

    def __init__(self, validator, resource_types, resources):
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

    def __str__(self):
        return "<{0} {1} {2}>".format(self.__class__.__name__, self.resource_types, self.resource_list)

    def may_have_property(self, names):
        return self.property(names, None)

    def must_have_property(self, names):
        return self.property(names, True)

    def must_not_have_property(self, names):
        return self.property(names, False)

    def property(self, names, error_on_missing_property=None):
        if not isinstance(names, list):
            names = [names]

        errors = []
        pl = TerraformPropertyList(self.validator)
        if len(self.resource_list) > 0:
            for resource in self.resource_list:
                for name in names:
                    if name in resource.config.keys():
                        if error_on_missing_property is False:
                            msg = "[{0}] should not have property {1}".format(resource.dotted(), repr(name))
                            errors.append(msg)
                        else:
                            pl.properties.append(resource.subproperty(name))
                    elif error_on_missing_property is True:
                        msg = "[{0}] should have property {1}".format(resource.dotted(), repr(name))
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
        return TerraformResourceList(self.validator, self.resource_types, resources)

    def find_property(self, regex):
        pl = TerraformPropertyList(self.validator)
        if len(self.resource_list) > 0:
            for resource in self.resource_list:
                for p in resource.config:
                    if self.validator.matches_regex_pattern(p, regex):
                        pl.properties.append(resource.subproperty(p))
        return pl

    def with_property(self, property_name, regex):
        pl = TerraformResourceList(self.validator, self.resource_types, {})

        if len(self.resource_list) > 0:
            for resource in self.resource_list:
                for p in resource.config:
                    if p == property_name:
                        tf_property = resource.subproperty(property_name)
                        actual = self.validator.substitute_variable_in_property(tf_property)
                        if self.validator.matches_regex_pattern(actual, regex):
                            pl.resource_list.append(resource)

        return pl

    def name(self):
        return ValueChecker(self.resource_list, getter=op.attrgetter('resource_name'))

    def should(self, pred):
        vc = ValueChecker(self.resource_list)
        return vc.should(pred)


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


class TerraformData:

    def __init__(self, data_type, name, config):
        self.data_type = data_type
        self.data_name = name
        self.config = config

    def __repr__(self):
        return "{0}({1}, {2}, {3})".format(self.__class__.__name__, self.data_type, self.data_name, self.config)

    def dotted(self):
        return "data.{0}.{1}".format(self.data_type, self.data_name)

    def json(self):
        return json.dumps(self.config)



class TerraformDataList:

    def __init__(self, validator, data_types, data):
        self.data_list = []

        if type(data_types) is not list:
            all_data_types = list(data.keys())
            regex = data_types
            data_types = []
            for data_type in all_data_types:
                if validator.matches_regex_pattern(data_type, regex):
                    data_types.append(data_type)

        for data_type in data_types:
            if data_type in data.keys():
                for datum in data[data_type]:
                    self.data_list.append(TerraformData(data_type, datum, data[data_type][datum]))

        self.data_types = data_types
        self.validator = validator

    def __str__(self):
        return "<{0} {1} {2}>".format(self.__class__.__name__, self.data_types, self.data_list)

    def find_name(self, regex):
        data = {}
        for r in self.data_list:
            if re.match(regex, r.data_name):
                if r.data_type not in data:
                    data[r.data_type] = {}
                data[r.data_type][r.data_name] = r.config
        return TerraformDataList(self.validator, self.data_types, data)

    def name(self):
        return ValueChecker(self.data_list, getter=op.attrgetter('data_name'))


class Validator:

    def __init__(self, path=None, error_on_empty=False):
        self.variable_expand = False
        if type(path) is not dict:
            if path is not None:
                self.terraform_config = self.parse_terraform_directory(path, error_on_empty)
        else:
            self.terraform_config = path

    def resources(self, types):
        if 'resource' not in self.terraform_config.keys():
            resources = {}
        else:
            resources = self.terraform_config['resource']
        return TerraformResourceList(self, types, resources)

    def data(self, types):
        if 'data' not in self.terraform_config.keys():
            data = {}
        else:
            data = self.terraform_config['data']
        return TerraformDataList(self, types, data)

    def variable(self, name):
        return TerraformVariable(self, name, self.get_terraform_variable_value('var', name))

    def enable_variable_expansion(self):
        self.variable_expand = True

    def disable_variable_expansion(self):
        self.variable_expand = False

    def parse_terraform_directory(self, path, error_on_empty=False):
        terraform_string = ""
        for directory, _, files in os.walk(path):
            for file in files:
                if (file.endswith(".tf")):
                    filepath = os.path.join(directory, file)
                    with open(filepath) as fp:
                        new_terraform = fp.read()
                        if len(new_terraform) == 0:
                            if error_on_empty:
                                raise TerraformSyntaxException("Terraform file {0} is empty".format(filepath))
                            continue
                        if new_terraform.isspace():
                            if error_on_empty:
                                raise TerraformSyntaxException("Terraform file {0} contains only spaces".format(filepath))
                            continue
                        try:
                            hcl.loads(new_terraform)
                        except ValueError as e:
                            raise TerraformSyntaxException("Invalid terraform configuration in {0}\n{1}".format(filepath, e))
                        terraform_string += new_terraform
        if not terraform_string:
            terraform_string = "{}"
        return hcl.loads(terraform_string)

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

    def get_terraform_variable_value(self, typ, variable):
        if typ == 'var':
            if ('variable' not in self.terraform_config.keys()) or (variable not in self.terraform_config['variable'].keys()):
                raise TerraformVariableException("There is no Terraform variable {0}".format(repr(variable)))
            if 'default' not in self.terraform_config['variable'][variable].keys():
                return None
            return self.terraform_config['variable'][variable]['default']
        if typ == 'data':
            if 'data' not in self.terraform_config.keys():
                raise TerraformVariableException("There is no Terraform data object {0}".format(repr(variable)))
            data_root = self.terraform_config['data']
            data_segs = variable.split('.')
            if len(data_segs) != 3:
                raise TerraformVariableException("Invalid Terraform data object reference {0}: expected in 'TYPE.NAME.PROPERTY' format with 3 segments, but found {1} segments".format(repr(variable), data_segs))
            if data_segs[0] not in data_root:
                raise TerraformVariableException("There is no Terraform data object of type {0}".format(repr(data_segs[0])))
            if data_segs[1] not in data_root[data_segs[0]]:
                raise TerraformVariableException("There is no Terraform data object with type {0} and name {1}".format(repr(data_segs[0]), repr(data_segs[1])))
            d = TerraformData(data_segs[0], data_segs[1], data_root[data_segs[0]][data_segs[1]])
            try:
                m = getattr(d, data_segs[2])
                return m()
            except AttributeError:
                raise TerraformVariableException("Terraform data object {0} does not know how to handle {1}; can the value be expanded offline?".format(repr(d.dotted()), repr(data_segs[2])))
            return None

    def substitute_variable_in_property(self, p):
        return self.substitute_variable_values_in_string(p.property_value)

    def substitute_variable_values_in_string(self, s):
        if self.variable_expand:
            if not isinstance(s, dict):
                for variable in self.list_terraform_variables_in_string(s):
                    a = TerraformVariableParser(variable)
                    a.parse()
                    variable_default_value = self.get_terraform_variable_value(a.variable_type, a.variable)
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
