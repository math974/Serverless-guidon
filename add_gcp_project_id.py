#!/usr/bin/env python3
"""Ajoute GCP_PROJECT_ID à toutes les fonctions dans stage.tfvars et dev.tfvars"""

import re

GCP_PROJECT_ID_BLOCK = """      {
        key     = "GCP_PROJECT_ID"
        secret  = "GCP_PROJECT_ID"
        version = "latest"
      },
"""

def add_gcp_project_id(filepath):
    """Ajoute GCP_PROJECT_ID en premier dans chaque bloc secret_env"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    
    # Trouver tous les blocs secret_env = [ ... ]
    # et ajouter GCP_PROJECT_ID au début si absent
    
    def replace_secret_env(match):
        full_block = match.group(0)
        
        # Si GCP_PROJECT_ID est déjà présent, ne rien changer
        if 'GCP_PROJECT_ID' in full_block:
            return full_block
        
        # Sinon, ajouter GCP_PROJECT_ID après "secret_env = ["
        # Pattern: secret_env = [\n      {
        parts = full_block.split('secret_env = [', 1)
        if len(parts) == 2:
            before = parts[0] + 'secret_env = ['
            after = parts[1]
            # Ajouter GCP_PROJECT_ID avant le premier "{"
            after = '\n' + GCP_PROJECT_ID_BLOCK + after.lstrip('\n')
            return before + after
        return full_block
    
    # Pattern pour capturer un bloc complet de fonction
    # Capturer de "nom_fonction" = { jusqu'au } qui ferme
    pattern = r'"[^"]*"\s*=\s*\{[^}]*secret_env\s*=\s*\[[^\]]*\]'
    
    # Approche plus simple : remplacer "secret_env = [\n      {" par "secret_env = [\nGCP_PROJECT_ID_BLOCK\n      {"
    pattern = r'(secret_env\s*=\s*\[)\s*\n(\s*\{)'
    
    def replacer(m):
        full = m.group(0)
        # Vérifier si GCP_PROJECT_ID suit dans les 200 prochains caractères
        start_pos = m.start()
        end_search = min(start_pos + 300, len(content))
        block_to_check = content[start_pos:end_search]
        
        if 'GCP_PROJECT_ID' in block_to_check:
            return full  # Déjà présent
        
        # Ajouter GCP_PROJECT_ID
        return m.group(1) + '\n' + GCP_PROJECT_ID_BLOCK + m.group(2)
    
    content = re.sub(pattern, replacer, content)
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✅ Modifié: {filepath}")
        return True
    else:
        print(f"ℹ️  Pas de modification: {filepath}")
        return False

if __name__ == '__main__':
    for f in ['terraform-infra/envs/stage.tfvars', 'terraform-infra/envs/dev.tfvars']:
        add_gcp_project_id(f)

