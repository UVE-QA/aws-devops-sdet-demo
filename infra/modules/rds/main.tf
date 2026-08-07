# RDS module: private PostgreSQL 16 instance. The master password is generated
# (random_password) and stored in Secrets Manager (ADR-0005); it never appears
# in tfvars, outputs, or plaintext env. The DB is private (publicly_accessible
# = false) and reachable only from the ECS app SG on 5432. For repeatable
# teardown (ADR-0011): skip_final_snapshot, backup_retention_period = 0, and the
# secret's recovery_window_in_days = 0.

resource "aws_db_subnet_group" "this" {
  name       = "${var.name_prefix}-db-subnet-group"
  subnet_ids = var.private_db_subnet_ids

  tags = {
    Name = "${var.name_prefix}-db-subnet-group"
  }
}

resource "aws_security_group" "rds" {
  name        = "${var.name_prefix}-rds-sg"
  description = "RDS SG: allow 5432 only from the ECS app SG; all egress."
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from ECS app SG only"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.ecs_app_security_group_id]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-rds-sg"
  }
}

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_instance" "this" {
  identifier     = "${var.name_prefix}-db"
  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage = var.allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  multi_az            = false
  deletion_protection = false

  # Repeatable teardown (ADR-0011): no leftover snapshot or backups across cycles.
  skip_final_snapshot     = true
  backup_retention_period = 0
  apply_immediately       = true

  tags = {
    Name = "${var.name_prefix}-db"
  }
}

# Connection details stored as a JSON secret; ECS reads it via secrets valueFrom.
resource "aws_secretsmanager_secret" "db" {
  name = "${var.name_prefix}-db-credentials"

  # recovery_window 0 frees the name immediately so the next apply after a
  # destroy does not hit "already scheduled for deletion" (ADR-0011).
  recovery_window_in_days = 0

  tags = {
    Name = "${var.name_prefix}-db-credentials"
  }
}

locals {
  # An instance that is still `creating` HAS NO ENDPOINT ADDRESS, and a null in
  # a string template is a hard error Terraform raises while evaluating the
  # configuration - during a DESTROY as much as during an apply.
  #
  # That state used to be unreachable: an apply waits for the instance, so the
  # address was always there by the time anything read it. Since ADR-0038 a
  # teardown IMPORTS an instance a cancelled apply left behind, and on
  # 2026-08-07 it imported one that was three minutes old. The adoption
  # succeeded, and the destroy then died evaluating this line - the failure
  # moved rather than went away.
  #
  # `jsonencode` accepts null happily, so `host` below needs nothing. Only the
  # template does.
  db_address = aws_db_instance.this.address != null ? aws_db_instance.this.address : ""
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db.result
    host     = aws_db_instance.this.address
    port     = 5432
    dbname   = var.db_name
    url      = "postgresql+psycopg2://${var.db_username}:${random_password.db.result}@${local.db_address}:5432/${var.db_name}"
  })
}
