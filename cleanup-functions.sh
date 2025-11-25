#!/bin/bash
set -e

PROJECT_ID="serverless-staging-478911"
REGION="europe-west1"
FUNCTIONS=("auth-service" "discord-registrar" "proxy" "user-manager" "web-frontend")

echo "🧹 Nettoyage des Cloud Functions en échec..."

cd terraform-infra

# Pour chaque fonction
for func in "${FUNCTIONS[@]}"; do
    echo ""
    echo "📦 Traitement de la fonction: $func"
    
    # Supprimer la fonction de Google Cloud (si elle existe)
    echo "  ↳ Suppression de la fonction sur GCP..."
    gcloud functions delete $func \
        --region=$REGION \
        --project=$PROJECT_ID \
        --gen2 \
        --quiet 2>/dev/null || echo "  ⚠️  Fonction $func n'existe pas ou déjà supprimée sur GCP"
    
    # Retirer la fonction du state Terraform
    echo "  ↳ Retrait du state Terraform..."
    terraform state rm "module.functions[\"$func\"].google_cloudfunctions2_function.function" 2>/dev/null || echo "  ⚠️  Déjà retiré du state"
    terraform state rm "module.functions[\"$func\"].google_cloudfunctions2_function_iam_member.invoker_public" 2>/dev/null || echo "  ⚠️  IAM déjà retiré"
    
    # Nettoyer les anciennes ressources (local_file, null_resource)
    terraform state rm "module.functions[\"$func\"].local_file.minimal_main_py" 2>/dev/null || true
    terraform state rm "module.functions[\"$func\"].local_file.minimal_requirements_txt" 2>/dev/null || true
    terraform state rm "module.functions[\"$func\"].null_resource.prepare_source" 2>/dev/null || true
    terraform state rm "module.functions[\"$func\"].data.archive_file.minimal_source_zip" 2>/dev/null || true
    terraform state rm "module.functions[\"$func\"].google_storage_bucket_object.minimal_archive" 2>/dev/null || true
done

echo ""
echo "✅ Nettoyage terminé!"
echo ""
echo "Vous pouvez maintenant exécuter:"
echo "  terraform plan"
echo "  terraform apply"

