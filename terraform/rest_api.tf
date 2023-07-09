resource "aws_api_gateway_rest_api" "my_rest_api" {
  name = "${var.rest_api_name}-${local.name_alias}"
}

/* module "api_gateway" {
  source = "./modules/api_gateway"
} */