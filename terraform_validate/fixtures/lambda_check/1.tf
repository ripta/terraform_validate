resource "aws_s3_bucket" "foobar" {
    bucket = "foobar-123456"
    acl    = "private"

    logging {
        target_bucket = "my-s3-logging"
        target_prefix = "arbitrary-value/"
    }
}

resource "aws_s3_bucket" "helloworld" {
    bucket = "helloworld-123456"
    acl    = "private"

    logging {
        target_bucket = "my-s3-logging"
        target_prefix = "arbitrary-value/"
    }
}
