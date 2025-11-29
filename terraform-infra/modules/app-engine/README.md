# Module Terraform App Engine

Ce module déploie une application web Python sur Google App Engine Standard.

## Fonctionnalités

- ✅ Déploiement automatisé sur App Engine Standard
- ✅ Génération dynamique du fichier `app.yaml` avec templating
- ✅ Upload du code source dans un bucket GCS
- ✅ Configuration des variables d'environnement
- ✅ Scaling automatique configurable
- ✅ Support de Python 3.10/3.11

## Utilisation

```hcl
module "app_engine" {
  source = "./modules/app-engine"

  project_id              = "my-project-id"
  location_id             = "europe-west"
  region                  = "europe-west1"
  service_name            = "default"
  runtime                 = "python310"
  entrypoint              = "gunicorn -b :$PORT main:app"
  source_dir              = "../web-frontend"
  app_yaml_template_path  = "../web-frontend/app.yaml.tpl"
  min_instances           = 0
  max_instances           = 10

  env_variables = {
    GATEWAY_URL = "https://api-gateway.example.com"
  }

  labels = {
    environment = "prod"
    app         = "web-frontend"
  }
}
```

## Template app.yaml

Créez un fichier `app.yaml.tpl` dans votre répertoire source :

```yaml
runtime: python310
entrypoint: gunicorn -b :$PORT --timeout 60 --workers 2 main:app

env_variables:
  GATEWAY_URL: ${GATEWAY_URL}
```

## Variables

| Nom | Description | Type | Défaut |
|-----|-------------|------|--------|
| `project_id` | ID du projet GCP | `string` | - |
| `location_id` | Localisation App Engine (ex: europe-west) | `string` | - |
| `region` | Région pour le bucket source | `string` | - |
| `service_name` | Nom du service | `string` | `"default"` |
| `runtime` | Runtime Python | `string` | `"python310"` |
| `entrypoint` | Commande d'entrée | `string` | - |
| `source_dir` | Répertoire source de l'app | `string` | - |
| `app_yaml_template_path` | Chemin vers app.yaml.tpl | `string` | - |
| `env_variables` | Variables d'environnement | `map(string)` | `{}` |
| `min_instances` | Nombre min d'instances | `number` | `0` |
| `max_instances` | Nombre max d'instances | `number` | `10` |
| `delete_service_on_destroy` | Supprimer le service lors du destroy | `bool` | `false` |

## Outputs

| Nom | Description |
|-----|-------------|
| `app_id` | ID de l'application |
| `default_hostname` | Hostname de l'application |
| `app_url` | URL complète de l'application |
| `service_name` | Nom du service déployé |
| `version_id` | ID de la version déployée |

## Notes importantes

- **Location ID** : Une fois définie, la location d'une app App Engine ne peut pas être changée
- **Service "default"** : Le premier service doit s'appeler "default"
- **Scaling** : Le scaling automatique nécessite au moins 2 instances configurées
- **Code source** : Le code source est archivé et uploadé dans un bucket GCS automatiquement

## Dépendances

Ce module crée automatiquement :
- L'application App Engine (si elle n'existe pas)
- Un bucket GCS pour stocker le code source
- Les versions du service App Engine

## Exemple de structure de répertoire

```
web-frontend/
├── app.yaml.tpl      # Template avec variables
├── main.py           # Point d'entrée Flask/Gunicorn
├── requirements.txt  # Dépendances Python
├── css/
├── js/
└── template/
```

