resource "aws_api_gateway_rest_api" "my_rest_api" {
  name = "my_rest_api-${local.name_alias}"
}
