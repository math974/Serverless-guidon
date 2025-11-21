# Configuration Files

Ce dossier contient les fichiers de configuration pour l'infrastructure et l'observabilité du projet.

## 📊 Cloud Monitoring Dashboard

### `cloud-monitoring-dashboard-v1.json`

Dashboard d'observabilité pour visualiser les métriques, logs et traces de l'architecture Discord Bot.

**Déploiement** :
```bash
./scripts/deploy-dashboard.sh
```

**Accès** :
```
https://console.cloud.google.com/monitoring/dashboards?project=serverless-ejguidon-dev
```

### Widgets inclus

| Widget | Description | Source |
|--------|-------------|--------|
| 📈 Requêtes par service | Trafic en req/min par service | `run.googleapis.com/request_count` |
| ⏱️ Latence P95 | Latence au 95e percentile | `run.googleapis.com/request_latencies` |
| 🔴 Taux d'erreur | Ratio d'erreurs 5xx | Ratio request_count (5xx/total) |
| 📝 Logs ERROR | Logs de sévérité ERROR | Cloud Logging |
| 🔍 Liens Cloud Trace | Accès rapide aux traces | Liens directs |
| 💻 CPU Utilization | Utilisation CPU du proxy | `run.googleapis.com/container/cpu/utilizations` |
| 💾 Memory Utilization | Utilisation mémoire du proxy | `run.googleapis.com/container/memory/utilizations` |
| 📦 Container Instances | Nombre d'instances actives | `run.googleapis.com/container/instance_count` |
| 🔎 Logs correlation_id | Logs filtrés par correlation_id | Cloud Logging |
| ⚠️ Logs WARNING | Logs de sévérité WARNING | Cloud Logging |
| ℹ️ Documentation | Informations et liens utiles | Texte Markdown |

### Métriques disponibles (V1)

**Sources de données actuelles** :
- ✅ Métriques natives Cloud Run (requêtes, latence, CPU, mémoire)
- ✅ Logs structurés JSON (severity, service, message, trace_id, correlation_id)
- ✅ Traces OpenTelemetry → Cloud Trace

**Limitations V1** :
- ❌ Pas de métriques custom par commande Discord
- ❌ Pas d'attributs de span enrichis (command_name, user_id)
- ❌ Pas de SLO/SLI configurés

### Évolutions futures (V2+)

**Phase 2** : Métriques business
```python
# Enrichir les spans avec des attributs métier
span.set_attribute("discord.command.name", command_name)
span.set_attribute("discord.user.id", user_id)
span.set_attribute("art.processing.duration_ms", duration_ms)
```

**Phase 3** : Métriques custom
```python
# Ajouter des compteurs et histogrammes
metrics.record_command(command_name, duration_ms, success=True)
```

**Phase 4** : SLO/SLI
```yaml
# Définir des objectifs de niveau de service
slos:
  - name: "discord-proxy-availability"
    goal: 0.999  # 99.9%
  - name: "discord-commands-latency"
    goal: 0.95   # 95% < 500ms
```

### Modification du dashboard

**Via l'interface graphique** :
1. Ouvrez le dashboard dans GCP Console
2. Cliquez sur "Edit dashboard"
3. Ajoutez/modifiez/supprimez des widgets
4. Cliquez sur "Save"

**Via le fichier JSON** :
1. Modifiez `cloud-monitoring-dashboard-v1.json`
2. Exportez le dashboard existant pour récupérer son ID :
   ```bash
   gcloud monitoring dashboards list --format="value(name)"
   ```
3. Mettez à jour le dashboard :
   ```bash
   gcloud monitoring dashboards update <DASHBOARD_ID> \
     --config-from-file=configs/cloud-monitoring-dashboard-v1.json
   ```

### Supprimer le dashboard

```bash
gcloud monitoring dashboards delete <DASHBOARD_ID> \
  --project=serverless-ejguidon-dev
```

## 🔗 Autres fichiers de configuration

### `openapi2-run.yaml`

Spécification OpenAPI pour la configuration de l'API Gateway.

---

## 📚 Ressources

- [Cloud Monitoring Documentation](https://cloud.google.com/monitoring/docs)
- [Dashboard Configuration Reference](https://cloud.google.com/monitoring/api/ref_v3/rest/v1/projects.dashboards)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Cloud Trace Documentation](https://cloud.google.com/trace/docs)

