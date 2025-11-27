# Configuration Files

Ce dossier contient les fichiers de configuration pour l'infrastructure et l'observabilité du projet.

## 📊 Cloud Monitoring Dashboards

### `cloud-observability-dashboard.json`

Vue personnalisée “Cloud Observability Overview” (module C7) qui regroupe Cloud Run, Pub/Sub, logs structurés et liens OAuth2.

**Déploiement / mise à jour**
```bash
# Créer
gcloud monitoring dashboards create \
  --project=serverless-ejguidon-dev \
  --config-from-file=configs/cloud-observability-dashboard.json

# Mettre à jour (utilise l'ID retourné par la création)
gcloud monitoring dashboards update \
  projects/471152872810/dashboards/3a7e5dcf-e820-4cdc-aef7-70d6f34d40ee \
  --config-from-file=configs/cloud-observability-dashboard.json
```

**Widgets inclus**

| Widget | Description | Source |
|--------|-------------|--------|
| 📈 Requêtes Cloud Run | req/min par service | `run.googleapis.com/request_count` |
| ⏱️ Latence P95 | Percentile 95 par service | `run.googleapis.com/request_latencies` |
| 🔴 Taux d'erreur | Ratio 5xx / total | `run.googleapis.com/request_count` |
| 💻/💾 Santé CPU & RAM | CPU/RAM de tous les services | `run.googleapis.com/container/*` |
| 📦 Instances Cloud Run | Instance count agrégé | `run.googleapis.com/container/instance_count` |
| 👤 User Manager OAuth2 | Trafic spécifique au service auth | `run.googleapis.com/request_count` |
| 📝/⚠️ Logs ERROR & WARNING | Logs structurés Cloud Logging | `resource.type=cloud_run_revision` |
| 🔎 Logs corrélés | Filtre `jsonPayload.correlation_id` | Cloud Logging |
| 📡 Quick links | Liens vers Logs, Trace, alerting, OAuth | Markdown |
| 📬 Pub/Sub backlog | `num_undelivered_messages` par subscription | `pubsub.googleapis.com/subscription` |
| 📥 Pub/Sub ACK vs reçus | `ack_message_count` vs `receive_message_count` | `pubsub.googleapis.com/subscription` |

### Ancien dashboard V1

`cloud-monitoring-dashboard-v1.json` reste disponible pour référence historique (script `scripts/deploy-dashboard.sh`), mais la vue principale recommandée est désormais `cloud-observability-dashboard.json`.

### Modifier / supprimer un dashboard

- Interface : ouvrir le dashboard → **Edit** → modifier → **Save**.
- CLI : `gcloud monitoring dashboards update <ID> --config-from-file=<fichier>`.
- Suppression : `gcloud monitoring dashboards delete <ID> --project=serverless-ejguidon-dev`.

## 🚨 Alerting

Les politiques d’alerte Cloud Monitoring sont décrites en JSON :

| Fichier | Description |
|---------|-------------|
| `alert-policy-high-error-rate.json` | Ratio 5xx > 5 % (Cloud Run) |
| `alert-policy-latency.json` | Latence P95 > 2 s |
| `alert-policy-uptime.json` | Échec de l’uptime check `user-manager-health` |
| `alert-policy-pubsub-backlog.json` | Backlog Pub/Sub > 100 messages pendant 2 min |

**Déploiement**
```bash
gcloud alpha monitoring policies create \
  --project=serverless-ejguidon-dev \
  --policy-from-file=configs/alert-policy-*.json
```

Les notifications sont envoyées sur le canal e-mail `lucas.arnassalom@epitech.eu`. Utilise `gcloud beta monitoring channels list` pour récupérer l’ID si besoin.

## 🔗 Autres fichiers de configuration

### `openapi2-run.yaml`

Spécification OpenAPI pour la configuration de l'API Gateway.

---

## 📚 Ressources

- [Cloud Monitoring Documentation](https://cloud.google.com/monitoring/docs)
- [Dashboard Configuration Reference](https://cloud.google.com/monitoring/api/ref_v3/rest/v1/projects.dashboards)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Cloud Trace Documentation](https://cloud.google.com/trace/docs)




