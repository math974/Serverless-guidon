project_id           = "serverless-guidon"
region               = "europe-west1"
api_id               = "guidon-api"
gateway_id           = "guidon-gw-prod"
api_config_id_prefix = "v"
openapi_spec_path    = "specs/openapi.yaml"

labels = {
  environment = "prod"
  app         = "guidon"
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
  "discord-registrar" = {
    entry_point = "registrar_handler"
    source_dir  = "../services/discord-registrar"
    runtime     = "python311"
  }
  "canvas-service" = {
    entry_point = "canvas_service"
    source_dir  = "../services/canvas-service"
    runtime     = "python311"
  }
  "processor-base" = {
    entry_point = "processor_base_handler"
    source_dir  = "../services/processor-base"
    runtime     = "python311"
  }
  "processor-stats" = {
    entry_point = "processor_stats_handler"
    source_dir  = "../services/processor-stats"
    runtime     = "python311"
  }
  "processor-colors" = {
    entry_point = "processor_colors_handler"
    source_dir  = "../services/processor-colors"
    runtime     = "python311"
  }
  "processor-draw" = {
    entry_point = "processor_draw_handler"
    source_dir  = "../services/processor-draw"
    runtime     = "python311"
  }
  "processor-pixel-info" = {
    entry_point = "processor_pixel_info_handler"
    source_dir  = "../services/processor-pixel-info"
    runtime     = "python311"
  }
  "processor-snapshot" = {
    entry_point = "processor_snapshot_handler"
    source_dir  = "../services/processor-snapshot"
    runtime     = "python311"
  }
  "processor-canvas-state" = {
    entry_point = "processor_canvas_state_handler"
    source_dir  = "../services/processor-canvas-state"
    runtime     = "python311"
  }
}

