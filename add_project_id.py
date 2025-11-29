#!/usr/bin/env python3
"""Script temporaire pour ajouter PROJECT_ID à toutes les fonctions dans les tfvars"""

import re

# Liste des fonctions Cloud Functions (pas les service accounts)
FUNCTIONS = [
    "proxy",
    "auth-service",
    "user-manager",
    "discord-registrar",
    "canvas-service",
    "processor-base",
    "processor-stats",
    "processor-colors",
    "processor-draw",
    "processor-pixel-info",
    "processor-snapshot",
    "processor-canvas-state"
]

PROJECT_ID_BLOCK = """      {
        key     = "PROJECT_ID"
        secret  = "PROJECT_ID"
        version = "latest"
      },
"""

def add_project_id_to_file(filepath):
    """Ajoute PROJECT_ID en premier dans chaque secret_env de chaque fonction"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    for func_name in FUNCTIONS:
        # Pattern pour trouver le bloc secret_env de cette fonction
        # On cherche "fonction_name" = { ... secret_env = [ ...
        pattern = rf'("{func_name}"\s*=\s*\{{[^}}]*?secret_env\s*=\s*\[)\s*(\{{)'
        
        def replace_func(match):
            # Si PROJECT_ID est déjà présent, ne rien faire
            func_block_start = match.start()
            # Chercher la fin du bloc secret_env
            bracket_count = 1
            pos = match.end()
            while pos < len(content) and bracket_count > 0:
                if content[pos] == '[':
                    bracket_count += 1
                elif content[pos] == ']':
                    bracket_count -= 1
                pos += 1
            
            func_block = content[func_block_start:pos]
            if 'PROJECT_ID' in func_block:
                return match.group(0)  # Déjà présent, ne pas modifier
            
            # Ajouter PROJECT_ID au début
            return match.group(1) + '\n' + PROJECT_ID_BLOCK + '      ' + match.group(2)
        
        content = re.sub(pattern, replace_func, content)
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✅ Mis à jour: {filepath}")
        return True
    else:
        print(f"ℹ️  Aucune modification nécessaire: {filepath}")
        return False

if __name__ == "__main__":
    files = [
        "terraform-infra/envs/prod.tfvars",
        "terraform-infra/envs/stage.tfvars",
        "terraform-infra/envs/dev.tfvars"
    ]
    
    for filepath in files:
        add_project_id_to_file(filepath)

