project_id           = "serverless-ejguidon-dev"
region               = "europe-west1"
api_id               = "picasso-api"
gateway_id           = "picasso-gw-dev"
api_config_id_prefix = "v"
openapi_spec_path    = "specs/openapi.yaml"

labels = {
  environment = "dev"
  app         = "picasso"
}

functions = {
  "hello-http" = {
    entry_point = "hello_http"
    source_dir  = "/home/mballot/Documents/tek4/Serverless-guidon/serverless/hello-python"
    runtime     = "python311"
  }
  "ping-http" = {
    entry_point = "ping_http"
    source_dir  = "/home/mballot/Documents/tek4/Serverless-guidon/serverless/ping-python"
    runtime     = "python311"
  }
}





