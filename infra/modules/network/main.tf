# Network module: VPC with 2 public subnets (app/ALB) and 2 private DB subnets
# (RDS), an Internet Gateway, and a public route table. NO NAT Gateway (ADR-0006):
# the Fargate task runs in a public subnet with a public IP and egresses via the
# IGW. Private subnets host RDS only and have no internet route.

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  az_names = slice(data.aws_availability_zones.available.names, 0, 2)
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.name_prefix}-vpc"
  }
}

# Every VPC ships a default security group that allows all traffic between its
# members. Nothing here uses it - the ALB, the task and the database each get
# their own - so it is an open group that exists by accident. Declaring it with
# no rules revokes them all.
#
# This resource ADOPTS an object AWS creates and cannot delete: `terraform
# destroy` drops it from state and leaves the (now empty) group with the VPC,
# which is then deleted with the VPC. It adds nothing to the teardown path.
resource "aws_default_security_group" "this" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name = "${var.name_prefix}-default-sg-revoked"
  }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name = "${var.name_prefix}-igw"
  }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = local.az_names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.name_prefix}-public-${local.az_names[count.index]}"
    Tier = "public"
  }
}

resource "aws_subnet" "private_db" {
  count             = 2
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_db_subnet_cidrs[count.index]
  availability_zone = local.az_names[count.index]

  tags = {
    Name = "${var.name_prefix}-private-db-${local.az_names[count.index]}"
    Tier = "private-db"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = {
    Name = "${var.name_prefix}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
