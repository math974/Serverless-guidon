# Module Firestore

Ce module crée et gère une database Firestore avec les protections de sécurité appropriées.

## 🔒 Protections de sécurité

### 1. Protection contre la suppression (Multiple niveaux)

- **GCP Native**: `delete_protection_state = "DELETE_PROTECTION_ENABLED"`
- **Terraform**: `lifecycle { prevent_destroy = true }`
- Ces protections empêchent toute suppression accidentelle de la database

### 2. Accès restreint

- ❌ **Pas d'accès public** - Firestore n'a pas d'endpoint HTTP public
- ✅ **Accès uniquement via service accounts** - Seuls les service accounts autorisés peuvent accéder
- ✅ **IAM granulaire** - Contrôle via rôles IAM (`datastore.user`, `datastore.viewer`)

### 3. Immuabilité

Le module configure `ignore_changes` sur :
- `type` - Le type de database ne peut pas être changé après création
- `location_id` - La location ne peut pas être changée

## 📖 Utilisation

### Première création

```hcl
module "firestore" {
  source = "./modules/firestore"

  project_id    = "my-project"
  database_id   = "(default)"
  location_id   = "europe-west1"
  database_type = "FIRESTORE_NATIVE"
  
  function_service_accounts = [
    "my-project@appspot.gserviceaccount.com"
  ]
}
```

### Si la database existe déjà

Si une database Firestore existe déjà dans votre projet :

```bash
# Importer la database existante dans le state Terraform
terraform import module.firestore.google_firestore_database.database projects/PROJECT_ID/databases/(default)
```

## ⚠️ Limitations importantes

1. **Une seule database (default) par projet** - Vous ne pouvez créer qu'une database `(default)` par projet GCP
2. **Pas de suppression** - Même avec `terraform destroy`, la database ne sera pas supprimée grâce à `prevent_destroy`
3. **Type immuable** - Vous ne pouvez pas changer entre FIRESTORE_NATIVE et DATASTORE_MODE
4. **Location immuable** - Vous ne pouvez pas déplacer la database

## 🎯 Rôles IAM

- **`roles/datastore.owner`** - Admin complet (création DB, gestion IAM)
- **`roles/datastore.user`** - Lecture + Écriture (pour les Cloud Functions)
- **`roles/datastore.viewer`** - Lecture seule

## 🔧 Pour désactiver les protections (déconseillé)

Si vous devez absolument supprimer la database :

1. Retirer `prevent_destroy` du `lifecycle` block
2. Exécuter `terraform apply`
3. Désactiver la protection dans GCP Console
4. Exécuter `terraform destroy`

**⚠️ Attention : Cette opération est irréversible et supprimera toutes les données !**

