#!/bin/bash
set -e

# Deploy Cloud Monitoring Dashboard
# This script creates or updates the observability dashboard in Google Cloud Monitoring

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID="${GCP_PROJECT_ID:-serverless-ejguidon-dev}"
DASHBOARD_CONFIG="${SCRIPT_DIR}/../configs/cloud-monitoring-dashboard-v1.json"

echo "📊 Déploiement du Dashboard Cloud Monitoring..."
echo ""
echo "Projet: ${PROJECT_ID}"
echo "Config: ${DASHBOARD_CONFIG}"
echo ""

# Vérifier que le fichier de config existe
if [ ! -f "${DASHBOARD_CONFIG}" ]; then
    echo "❌ Erreur: Fichier de configuration introuvable: ${DASHBOARD_CONFIG}"
    exit 1
fi

# Vérifier que gcloud est configuré
if ! command -v gcloud &> /dev/null; then
    echo "❌ Erreur: gcloud CLI n'est pas installé"
    echo "Installation: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Vérifier l'authentification
echo "🔐 Vérification de l'authentification GCP..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "❌ Erreur: Vous n'êtes pas authentifié sur GCP"
    echo "Exécutez: gcloud auth login"
    exit 1
fi

# Activer l'API Cloud Monitoring (si pas déjà fait)
echo "🔧 Vérification de l'API Cloud Monitoring..."
gcloud services enable monitoring.googleapis.com \
    --project="${PROJECT_ID}" \
    2>/dev/null || true

# Créer le dashboard
echo ""
echo "📤 Création du dashboard..."
DASHBOARD_ID=$(gcloud monitoring dashboards create \
    --config-from-file="${DASHBOARD_CONFIG}" \
    --project="${PROJECT_ID}" \
    --format="value(name)" 2>&1)

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ✅ ✅ Dashboard déployé avec succès ! ✅ ✅ ✅"
    echo ""
    echo "📊 Nom du dashboard: Discord Bot - Observability Dashboard V1"
    echo "🆔 Dashboard ID: ${DASHBOARD_ID}"
    echo ""
    echo "🔗 Accédez à votre dashboard ici:"
    echo "   https://console.cloud.google.com/monitoring/dashboards/custom/${DASHBOARD_ID}?project=${PROJECT_ID}"
    echo ""
    echo "💡 Tips:"
    echo "   • Ajoutez ce lien en favori dans votre navigateur"
    echo "   • Sur mobile: ajoutez-le à l'écran d'accueil"
    echo "   • Le dashboard se met à jour automatiquement avec les données en temps réel"
    echo ""
else
    echo ""
    echo "❌ Erreur lors de la création du dashboard"
    echo ""
    echo "Le dashboard existe peut-être déjà. Vérifiez ici:"
    echo "   https://console.cloud.google.com/monitoring/dashboards?project=${PROJECT_ID}"
    echo ""
    echo "Pour mettre à jour un dashboard existant, utilisez:"
    echo "   gcloud monitoring dashboards update <DASHBOARD_ID> --config-from-file=${DASHBOARD_CONFIG}"
    echo ""
    exit 1
fi




