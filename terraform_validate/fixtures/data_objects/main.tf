resource "aws_sns_topic_policy" "example" {
  policy = "${data.aws_iam_policy_document.sns-owner-policy.json}"
}
