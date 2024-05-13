resource "aws_s3_bucket" "s3_event_data" {
  bucket        = "bucket-event-data-${local.name_alias}"
  force_destroy = var.is_development
}

resource "aws_s3_bucket" "s3_backup_data" {
  bucket        = "bucket-backup-data-${local.name_alias}"
  force_destroy = var.is_development
}
