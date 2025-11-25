project_id           = "serverless-staging-478911"
region               = "europe-west1"
api_id               = "picasso-api"
gateway_id           = "picasso-gw-stage"
api_config_id_prefix = "v"
openapi_spec_path    = "specs/openapi-template.yaml"

labels = {
  environment = "stage"
  app         = "picasso"
}

functions = {
  "proxy" = {
    entry_point = "proxy_handler"
    source_dir  = "../services/proxy"
    runtime     = "python311"
  }
  "auth-service" = {
    entry_point = "auth_handler"
    source_dir  = "../services/auth-service"
    runtime     = "python311"
  }
  "user-manager" = {
    entry_point = "user_management_handler"
    source_dir  = "../services/user-manager"
    runtime     = "python311"
  }
  "web-frontend" = {
    entry_point = "web_app"
    source_dir  = "../services/web-frontend"
    runtime     = "python311"
  }
  "discord-registrar" = {
    entry_point = "registrar_handler"
    source_dir  = "../services/discord-registrar"
    runtime     = "python311"
  }
}





