resource "aws_instance" "foo" {
    name = "foo"
    value = 1
    value2 = 2

}

resource "aws_instance" "bar" {
    name = "bar"

    value = 1
    value2 = 2

    propertylist {
        value = 2
    }

}

resource "aws_elb" "buzz" {
    name = "buzz"

    value = 1

}
