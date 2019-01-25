resource "aws_instance" "test" {
  root_block_device {
    volume_type = "gp2"
    volume_size = 50
  }

  ebs_block_device {
    volume_size = 200
  }
}

resource "thing" "main" {
  rules {
    ingress {
      protocol = "icmp"
      cidr_blocks = ["0.0.0.0/0"]
    }
    ingress {
      protocol = "udp"
      cidr_blocks = ["0.0.0.0/0"]
    }
    egress {
      protocol = "udp"
      cidr_blocks = ["10.0.0.0/8"]
    }
  }
}
