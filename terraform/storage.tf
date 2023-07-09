resource "aws_s3_bucket" "s3_bucket" {
  bucket = "bucket-${local.name_alias}"
}

resource "aws_s3_bucket" "s3_bucket_test" {
  bucket = "bucket-v2-${local.name_alias}"
}

resource "aws_redshift_cluster" "example" {
  cluster_identifier = "tf-redshift-cluster"
  database_name      = "mydb"
  master_username    = "exampleuser"
  master_password    = "Mustbe8characters"
  node_type          = "dc1.large"
  cluster_type       = "single-node"
}

resource "aws_redshift_subnet_group" "my_redshift_subnet_group" {
 name       = "redshift-subnet-group-${local.name_alias}"
 subnet_ids = ["${aws_subnet.my_public_subnet.id}", "${aws_subnet.my_private_subnet.id}"]

    tags = {
    environment = "dev"
    Name = "redshift-subnet-group"
    }

}

resource "aws_redshift_cluster" "redshift_cluster" {
  cluster_identifier  = "redshift-cluster-${local.name_alias}"
  database_name       = "test"
  master_username     = "username1"
  master_password     = "Password1"
  node_type           = "dc2.large"
  cluster_type        = "single-node"
  skip_final_snapshot = true
  vpc_security_group_ids = ["${aws_security_group.my_security_group.id}"]
  cluster_subnet_group_name = "${aws_redshift_subnet_group.my_redshift_subnet_group.id}"
}