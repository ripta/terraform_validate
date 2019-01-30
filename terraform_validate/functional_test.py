import terraform_validate as t
import re
import os
import sys

if sys.version_info < (2, 7):
    # pylint: disable=E0401
    import unittest2 as unittest
else:
    # pylint: disable=E0401
    import unittest


class TestValidatorFunctional(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(os.path.dirname(os.path.realpath(__file__)))

    def error_list_format_exact(self, error_list):
        if type(error_list) is not list:
            error_list = [error_list]
        regex = "\n".join(map(re.escape, error_list))
        return "^{0}$".format(regex)

    def error_list_format_prefix(self, error_list):
        if type(error_list) is not list:
            error_list = [error_list]
        regex = "\n".join(map(re.escape, error_list))
        return "^{0}".format(regex)

    def test_empty(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/empty"))
        validator.resources('aws_instance').property('value').should_equal(1)

    def test_resource(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        validator.resources('aws_instance').property('value').should_equal(1)
        expected_error = self.error_list_format_exact([
            "[aws_instance.bar.value] should equal '2', but got '1'",
            "[aws_instance.foo.value] should equal '2', but got '1'"
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('value').should_equal(2)

    def test_resource_by_name(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        expected_error = self.error_list_format_exact([
            "[aws_instance.bar] should have property 'value3'",
        ])
        # does not raise error for aws_instance.foo.value3
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').find_name('bar').must_have_property('value3').should_equal(3)

    def test_nested_resource(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/nested_resource"))
        validator.resources('aws_instance').property('nested_resource').property('value').should_equal(1)
        expected_error = self.error_list_format_exact("[aws_instance.foo.nested_resource.value] should equal '2', but got '1'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('nested_resource').property('value').should_equal(2)

    def test_resource_not_equals(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        validator.resources('aws_instance').property('value').should_not_equal(0)
        expected_error = self.error_list_format_exact([
            "[aws_instance.bar.value] should not be '1', but it is",
            "[aws_instance.foo.value] should not be '1', but it is"
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('value').should_not_equal(1)

    def test_nested_resource_not_equals(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/nested_resource"))
        validator.resources('aws_instance').property('nested_resource').property('value').should_not_equal(0)
        expected_error = self.error_list_format_exact("[aws_instance.foo.nested_resource.value] should not be '1', but it is")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('nested_resource').property('value').should_not_equal(1)

    def test_resource_required_properties_with_list_input(self):
        required_properties = ['value', 'value2']
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        validator.resources('aws_instance').must_have_property(required_properties)
        required_properties = ['value', 'value2', 'abc123', 'def456']
        expected_error = self.error_list_format_exact([
            "[aws_instance.bar] should have property 'abc123'",
            "[aws_instance.bar] should have property 'def456'",
            "[aws_instance.foo] should have property 'abc123'",
            "[aws_instance.foo] should have property 'def456'"
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').must_have_property(required_properties)

    def test_resource_required_properties_with_string_input(self):
        required_property = 'value'
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        validator.resources('aws_instance').must_have_property(required_property)

    def test_resource_excluded_properties_with_list_input(self):
        excluded_properties = ['value', 'value2']
        non_excluded_properties = ['value3', 'value4']
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        validator.resources('aws_instance').must_not_have_property(non_excluded_properties)
        expected_error = self.error_list_format_exact([
            "[aws_instance.bar] should not have property 'value'",
            "[aws_instance.bar] should not have property 'value2'",
            "[aws_instance.foo] should not have property 'value'",
            "[aws_instance.foo] should not have property 'value2'"
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').must_not_have_property(excluded_properties)

    def test_resource_excluded_properties_with_string_input(self):
        excluded_property = 'value'
        non_excluded_property = 'value3'
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        validator.resources('aws_instance').must_not_have_property(non_excluded_property)
        expected_error = self.error_list_format_exact([
            "[aws_instance.bar] should not have property 'value'",
            "[aws_instance.foo] should not have property 'value'"
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').must_not_have_property(excluded_property)

    def test_nested_resource_required_properties_with_list_input(self):
        required_properties = ['value', 'value2']
        validator = t.Validator(os.path.join(self.path, "fixtures/nested_resource"))
        validator.resources('aws_instance').property('nested_resource').must_have_property(required_properties)
        required_properties = ['value', 'value2', 'abc123', 'def456']
        expected_error = self.error_list_format_exact([
            "[aws_instance.foo.nested_resource] should have property 'abc123'",
            "[aws_instance.foo.nested_resource] should have property 'def456'",
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('nested_resource').must_have_property(required_properties)

    def test_nested_resource_required_properties_with_string_input(self):
        required_property = 'value'
        validator = t.Validator(os.path.join(self.path, "fixtures/nested_resource"))
        validator.resources('aws_instance').property('nested_resource').must_have_property(required_property)
        required_property = 'def456'
        expected_error = self.error_list_format_exact([
            "[aws_instance.foo.nested_resource] should have property 'def456'"
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('nested_resource').must_have_property(required_property)

    def test_nested_resource_excluded_properties_with_list_input(self):
        excluded_properties = ['value', 'value2']
        non_excluded_properties = ['value3', 'value4']
        validator = t.Validator(os.path.join(self.path, "fixtures/nested_resource"))
        validator.resources('aws_instance').property('nested_resource').must_not_have_property(non_excluded_properties)
        expected_error = self.error_list_format_exact([
            "[aws_instance.foo.nested_resource] should not have property 'value'",
            "[aws_instance.foo.nested_resource] should not have property 'value2'",
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('nested_resource').must_not_have_property(excluded_properties)

    def test_nested_resource_excluded_properties_with_string_input(self):
        excluded_property = 'value'
        non_excluded_property = 'value3'
        validator = t.Validator(os.path.join(self.path, "fixtures/nested_resource"))
        validator.resources('aws_instance').property('nested_resource').must_not_have_property(non_excluded_property)
        expected_error = self.error_list_format_exact([
            "[aws_instance.foo.nested_resource] should not have property 'value'"
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('nested_resource').must_not_have_property(excluded_property)

    def test_resource_property_value_matches_regex(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        validator.resources('aws_instance').property('value').should_match('[0-9]')
        expected_error = self.error_list_format_exact([
            "[aws_instance.bar.value] should match '[a-z]', but got '1'",
            "[aws_instance.foo.value] should match '[a-z]', but got '1'"
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('value').should_match('[a-z]')

    def test_resource_property_name_does_not_match_regex(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        validator.resources('aws_instance').property('name').should_not_match('[0-9]')
        expected_error = self.error_list_format_exact([
            "[aws_instance.foo.name] should not match 'fo', but got 'foo'",
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('name').should_not_match('fo')

    def test_nested_resource_property_value_matches_regex(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/nested_resource"))
        validator.resources('aws_instance').property('nested_resource').property('value').should_match('[0-9]')
        expected_error = self.error_list_format_exact("[aws_instance.foo.nested_resource.value] should match '[a-z]', but got '1'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property(
                'nested_resource').property('value').should_match('[a-z]')

    def test_resource_property_invalid_json(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/invalid_json"))
        expected_error = self.error_list_format_prefix("[aws_s3_bucket.invalidjson.policy] is not valid json:")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_s3_bucket').property('policy').should_contain_valid_json()

    def test_variable_substitution(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/variable_substitution"))
        validator.enable_variable_expansion()
        validator.resources('aws_instance').property('value').should_equal(1)
        expected_error = self.error_list_format_exact("[aws_instance.foo.value] should equal '2', but got '1'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('value').should_equal(2)
        validator.disable_variable_expansion()
        validator.resources('aws_instance').property('value').should_equal('${var.test_variable}')

    def test_missing_variable_substitution(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/missing_variable"))
        validator.enable_variable_expansion()
        expected_error = self.error_list_format_exact("There is no Terraform variable 'missing'")
        with self.assertRaisesRegex(t.TerraformVariableException, expected_error):
            validator.resources('aws_instance').property('value').should_equal(1)

    # def test_missing_required_nested_resource_fails(self):
    #     validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
    #     self.assertRaises(AssertionError,validator.resources('aws_instance').property('tags').property('encrypted').should_equal(1))

    def test_properties_on_nonexistant_resource_type(self):
        required_properties = ['value', 'value2']
        validator = t.Validator(os.path.join(self.path, "fixtures/missing_variable"))
        validator.resources('aws_rds_instance').property('nested_resource').must_have_property(required_properties)

    def test_searching_for_property_on_nonexistant_nested_resource(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        expected_error = self.error_list_format_exact(
            [
                "[aws_instance.bar] should have property 'tags'",
                "[aws_instance.foo] should have property 'tags'"
            ]
        )
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').must_have_property('tags').property('tagname').should_equal(1)

    def test_searching_for_missing_property_allowed(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        expected_error = self.error_list_format_exact(
            [
                "[aws_instance.bar] should have property 'tags'",
                "[aws_instance.foo] should have property 'tags'"
            ]
        )
        validator.resources('aws_instance').property('tags').property('tagname').should_equal(1)
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').must_have_property('tags').property('tagname').should_equal(1)
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').must_have_property('tags').property('tagname').should_equal(1)
        validator.resources('aws_instance').property('tags').property('tagname').should_equal(1)

    def test_searching_for_missing_subproperty(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        expected_error = self.error_list_format_exact("[aws_instance.bar.propertylist] should have property 'value2'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('propertylist').must_have_property('value2').should_equal(2)

    def test_searching_for_unmissing_property(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        validator.resources('aws_instance').property('propertylist').property('value2').should_equal(2)

    def test_searching_for_property_value_using_regex(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/regex_variables"))
        validator.resources('aws_instance').find_property('^CPM_Service_[A-Za-z]+$').should_equal(1)
        expected_error = self.error_list_format_exact("[aws_instance.foo.CPM_Service_wibble] should equal '2', but got '1'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').find_property('^CPM_Service_[A-Za-z]+$').should_equal(2)

    def test_searching_for_nested_property_value_using_regex(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/regex_nested_variables"))
        validator.resources('aws_instance').property('tags').find_property('^CPM_Service_[A-Za-z]+$').should_equal(1)
        expected_error = self.error_list_format_exact("[aws_instance.foo.tags.CPM_Service_wibble] should equal '2', but got '1'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('tags').find_property(
                '^CPM_Service_[A-Za-z]+$').should_equal(2)

    def test_resource_type_list(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/resource"))
        validator.resources(['aws_instance', 'aws_elb']).property('value').should_equal(1)
        expected_error = self.error_list_format_exact([
            "[aws_elb.buzz.value] should equal '2', but got '1'",
            "[aws_instance.bar.value] should equal '2', but got '1'",
            "[aws_instance.foo.value] should equal '2', but got '1'"
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources(['aws_instance', 'aws_elb']).property('value').should_equal(2)

    def test_nested_resource_type_list(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/nested_resource"))
        validator.resources(['aws_instance', 'aws_elb']).property('tags').property('value').should_equal(1)
        expected_error = self.error_list_format_exact([
            "[aws_elb.foo.tags.value] should equal '2', but got '1'",
            "[aws_instance.foo.tags.value] should equal '2', but got '1'"
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources(['aws_instance', 'aws_elb']).property('tags').property('value').should_equal(2)

    def test_invalid_terraform_syntax(self):
        self.assertRaises(t.TerraformSyntaxException, t.Validator, os.path.join(self.path, "fixtures/invalid_syntax"))

    def test_multiple_variable_substitutions(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/multiple_variables"))
        validator.enable_variable_expansion()
        validator.resources('aws_instance').property('value').should_equal(12)
        expected_error = self.error_list_format_exact("[aws_instance.foo.value] should equal '21', but got '12'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('value').should_equal(21)

    def test_nested_multiple_variable_substitutions(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/multiple_variables"))
        validator.enable_variable_expansion()
        validator.resources('aws_instance').property('value_block').property('value').should_equal(21)
        expected_error = self.error_list_format_exact("[aws_instance.foo.value_block.value] should equal '12', but got '21'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('value_block').property('value').should_equal(12)

    def test_variable_expansion(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/variable_expansion"))
        validator.resources('aws_instance').property('value').should_equal('${var.bar}')
        expected_error = self.error_list_format_exact("[aws_instance.foo.value] should equal '${bar.var}', but got '${var.bar}'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').property('value').should_equal('${bar.var}')

    def test_resource_name_matches_regex(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/resource_name"))
        validator.resources('aws_foo').name().should_match('^[a-z0-9_]*$')
        expected_error = self.error_list_format_exact("[aws_instance.TEST_RESOURCE] should match '^[a-z0-9_]*$', but got 'TEST_RESOURCE'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').name().should_match('^[a-z0-9_]*$')

    def test_resource_name_does_not_match_regex(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/resource_name"))
        validator.resources('aws_foo').name().should_not_match('^TEST_')
        expected_error = self.error_list_format_exact("[aws_instance.TEST_RESOURCE] should not match '^TEST_', but got 'TEST_RESOURCE'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_instance').name().should_not_match('^TEST_')

    def test_variable_has_default_value(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/default_variable"))
        expected_error = self.error_list_format_exact("Variable 'bar' should have a default value")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.variable('bar').default_value_exists()

    def test_variable_default_value_equals(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/default_variable"))
        expected_error = self.error_list_format_exact("Variable 'bar' should have a default value 2, but it is None")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.variable('bar').default_value_equals(2)
        validator.variable('bar').default_value_equals(None)

    def test_variable_default_value_matches_regex(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/default_variable"))
        expected_error = self.error_list_format_exact(
            "Variable 'bizz' should have a default value that matches regex '^123', but it is 'abc'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.variable('bizz').default_value_matches_regex('^123')

    def test_no_exceptions_raised_when_no_resources_present(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/no_resources"))
        validator.resources('aws_instance').property('value').should_equal(1)

    def test_lowercase_formatting_in_variable_substitution(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/lower_format_variable"))
        validator.enable_variable_expansion()

        validator.resources('aws_instance').property('value').should_equal('abc')
        validator.resources('aws_instance2').property('value').should_equal('abcDEF')

    def test_parsing_variable_with_unimplemented_interpolation_function(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/unimplemented_interpolation"))
        validator.enable_variable_expansion()
        self.assertRaises(t.TerraformUnimplementedInterpolationException,
                          validator.resources('aws_instance').property('value').should_equal, 'abc')

    def test_boolean_equal(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/boolean_compare"))
        values = [True, "true", "True"]

        for i in range(1, 5):
            for value in values:
                validator.resources("aws_db_instance").property("storage_encrypted{0}".format(i)).should_equal(value)

    def test_list_should_contain(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/list_variable"))
        validator.resources("datadog_monitor").property("tags").should_contain(['baz:biz'])
        expected_error = self.error_list_format_exact([
            "[datadog_monitor.bar.tags] ['baz:biz', 'foo:bar'] should contain ['too:biz']",
            "[datadog_monitor.foo.tags] ['baz:biz'] should contain ['too:biz']"
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources("datadog_monitor").property("tags").should_contain('too:biz')

    def test_list_should_not_contain(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/list_variable"))
        validator.resources("datadog_monitor").property("tags").should_not_contain(['foo:baz'])
        validator.resources("datadog_monitor").property("tags").should_not_contain('foo:baz')
        expected_error = self.error_list_format_exact(
            "[datadog_monitor.bar.tags] ['baz:biz', 'foo:bar'] should not contain ['foo:bar']")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources("datadog_monitor").property("tags").should_not_contain('foo:bar')

    def test_property_list_scenario(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/list_property"))
        validator.resources("aws_autoscaling_group").property(
            "tag").property('propagate_at_launch').should_equal("True")
        validator.resources("aws_autoscaling_group").property("tag").property('propagate_at_launch').should_equal(True)

    def test_encryption_scenario(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/enforce_encrypted"))
        validator.resources("aws_db_instance_valid").property("storage_encrypted").should_equal("True")
        validator.resources("aws_db_instance_valid").property("storage_encrypted").should_equal(True)
        validator.resources("aws_db_instance_invalid").must_have_property("storage_encrypted")

        expected_error = self.error_list_format_exact(
            "[aws_db_instance_invalid.foo2.storage_encrypted] should equal 'True', but got 'False'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources("aws_db_instance_invalid").must_have_property("storage_encrypted").should_equal("True")
        expected_error = self.error_list_format_exact(
            "[aws_db_instance_invalid2.foo3] should have property 'storage_encrypted'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources("aws_db_instance_invalid2").must_have_property("storage_encrypted")

        validator.resources("aws_instance_valid").property(
            'ebs_block_device').property("encrypted").should_equal("True")
        validator.resources("aws_instance_valid").property('ebs_block_device').property("encrypted").should_equal(True)

        expected_error = self.error_list_format_exact("[aws_instance_invalid.bizz2] should have property 'encrypted'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources("aws_instance_invalid").must_have_property("encrypted")

        expected_error = self.error_list_format_exact(
            "[aws_instance_invalid.bizz2.ebs_block_device.encrypted] should equal 'True', but got 'False'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources("aws_instance_invalid").property(
                'ebs_block_device').property("encrypted").should_equal("True")

        expected_error = self.error_list_format_exact(
            "[aws_instance_invalid2.bizz3] should have property 'storage_encrypted'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources("aws_instance_invalid2").must_have_property("storage_encrypted")

        expected_error = self.error_list_format_exact(
            "[aws_instance_invalid2.bizz3.ebs_block_device] should have property 'encrypted'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources("aws_instance_invalid2").property('ebs_block_device').must_have_property("encrypted")

        validator.resources("aws_ebs_volume_valid").property("encrypted").should_equal("True")
        validator.resources("aws_ebs_volume_valid").property("encrypted").should_equal(True)
        validator.resources("aws_ebs_volume_invalid").must_have_property("encrypted")

        expected_error = self.error_list_format_exact("[aws_ebs_volume_invalid.bar2.encrypted] should equal 'True', but got 'False'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources("aws_ebs_volume_invalid").must_have_property("encrypted").should_equal("True")

        expected_error = self.error_list_format_exact("[aws_ebs_volume_invalid2.bar3] should have property 'encrypted'")
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources("aws_ebs_volume_invalid2").must_have_property("encrypted")
            validator.resources("aws_ebs_volume_invalid2").property("encrypted")

    def test_with_property(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/with_property"))

        expected_error = self.error_list_format_prefix("[aws_s3_bucket.private_bucket.policy] is not valid json:")

        private_buckets = validator.resources("aws_s3_bucket").with_property("acl", "private")

        with self.assertRaisesRegex(AssertionError, expected_error):
            private_buckets.property("policy").should_contain_valid_json()

    def test_with_nested_property(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/with_property"))

        expected_error = self.error_list_format_prefix("[aws_s3_bucket.tagged_bucket.policy] is not valid json:")

        tagged_buckets = validator.resources("aws_s3_bucket").with_property("tags", ".*'CustomTag':.*'CustomValue'.*")

        with self.assertRaisesRegex(AssertionError, expected_error):
            tagged_buckets.property("policy").should_contain_valid_json()

    def test_resource_with_multiple_similar_properties(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/multiple_similar_properties"))
        expected_error = self.error_list_format_exact("[aws_instance.test.ebs_block_device] should have property 'volume_type'")
        devices = validator.resources("aws_instance").property(['root_block_device', 'ebs_block_device'])
        with self.assertRaisesRegex(AssertionError, expected_error):
            devices.must_have_property('volume_type').should_equal('gp2')

    def test_resource_with_multiple_similar_subproperties(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/multiple_similar_properties"))
        expected_error = self.error_list_format_exact([
            "[thing.main.rules.ingress.cidr_blocks] ['0.0.0.0/0'] should not contain ['0.0.0.0/0']",
            "[thing.main.rules.ingress.cidr_blocks] ['0.0.0.0/0'] should not contain ['0.0.0.0/0']",
        ])
        rules = validator.resources("thing").property('rules').property(['ingress', 'egress'])
        with self.assertRaisesRegex(AssertionError, expected_error):
            rules.must_have_property('cidr_blocks').should_not_contain('0.0.0.0/0')

    def test_resource_with_data_objects(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/data_objects"))
        validator.data('aws_caller_identity').find_name('^current$')

        expected_error = self.error_list_format_exact([
            "[aws_sns_topic_policy.example.policy.statement] should have property 'foo-bar'",
            "[aws_sns_topic_policy.example.policy.statement] should have property 'foo-bar'",
        ])
        validator.enable_variable_expansion()
        j = validator.resources('aws_sns_topic_policy').must_have_property('policy').should_contain_valid_json()
        with self.assertRaisesRegex(AssertionError, expected_error):
            j.property('statement').must_have_property('foo-bar')

    def match_bucket(self, obj):
        expected = obj.subproperty('bucket').property_value + '/'
        actual = obj.subproperty('logging').subproperty('target_prefix').property_value
        msg = "[{0}] should equal {1}, but got {2}".format(obj.dotted(), repr(expected), repr(actual))
        return (actual == expected, msg)

    def test_lambda_check(self):
        validator = t.Validator(os.path.join(self.path, "fixtures/lambda_check"))
        validator.resources('aws_s3_bucket').property('logging').property('target_bucket').should_equal('my-s3-logging')

        expected_error = self.error_list_format_exact([
            "[aws_s3_bucket.foobar] should equal 'foobar-123456/', but got 'arbitrary-value/'",
            "[aws_s3_bucket.helloworld] should equal 'helloworld-123456/', but got 'arbitrary-value/'",
        ])
        with self.assertRaisesRegex(AssertionError, expected_error):
            validator.resources('aws_s3_bucket').should(self.match_bucket)
