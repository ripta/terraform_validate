resource "aws_instance" "test" {
  root_block_device {
    volume_type = "gp2"
    volume_size = 50
  }

  ebs_block_device {
    volume_size = 200
  }
}
