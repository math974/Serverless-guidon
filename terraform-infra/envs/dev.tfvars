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

# Les services dans services/ sont déployés comme Cloud Run, pas comme Cloud Functions
# Utilisez les scripts de déploiement existants (deploy-proxy.sh, deploy-registrar.sh, etc.)
# functions = {}





