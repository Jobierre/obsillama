"""
ObsIllama - Commande init

Cette commande initialise un nouveau projet ObsIllama de manière interactive.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

import click
import httpx
from ruamel.yaml import YAML

from obsillama.cli.commands import pass_context, ObsillamaContext
from obsillama.utils.progress import (
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_step,
    print_summary,
    print_panel,
    prompt,
    confirm,
    console,
)


def check_ollama_connection(base_url: str) -> bool:
    """
    Vérifie si Ollama est accessible à l'URL donnée.

    Args:
        base_url: URL de base d'Ollama

    Returns:
        True si la connexion réussit, False sinon
    """
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


def get_ollama_models(base_url: str) -> Optional[List[Dict[str, Any]]]:
    """
    Récupère la liste des modèles disponibles sur Ollama.

    Args:
        base_url: URL de base d'Ollama

    Returns:
        Liste des modèles ou None si erreur
    """
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            return data.get("models", [])
        return None
    except Exception:
        return None


def create_config_yaml(
    vault_path: str,
    ollama_url: str,
    generation_model: str,
    embedding_model: str,
    output_path: Path = Path("config/config.yaml"),
) -> None:
    """
    Crée le fichier config.yaml avec les paramètres fournis.

    Args:
        vault_path: Chemin vers le vault Obsidian
        ollama_url: URL de l'API Ollama
        generation_model: Modèle de génération
        embedding_model: Modèle d'embedding
        output_path: Chemin de sortie du fichier
    """
    config = {
        "vault": {
            "path": str(Path(vault_path).absolute()),
            "backup_path": ".obsillama_backups",
            "exclude_folders": [".obsidian", ".trash", "Templates"],
        },
        "ollama": {
            "base_url": ollama_url,
            "models": {
                "generation": generation_model,
                "embedding": embedding_model,
            },
            "params": {
                "temperature": 0.3,
                "max_tokens": 2000,
                "top_p": 0.9,
            },
        },
        "graphrag": {
            "community_algorithm": "leiden",
            "resolution": 1.0,
            "min_community_size": 3,
            "entity_types": [
                "technology",
                "concept",
                "tool",
                "person",
                "organization",
                "project",
                "methodology",
            ],
        },
        "categorization": {
            "target_count": 20,
            "min_notes_per_category": 5,
            "thresholds": {
                "assignment_confidence": 0.7,
                "merge_similarity": 0.85,
                "subcategory_threshold": 20,
            },
            "tag_prefix": "AI-Category-",
            "language": "fr",
        },
        "incremental": {
            "enabled": True,
            "check_interval_days": 7,
            "auto_ameliorate": False,
            "recluster_threshold": 100,
        },
        "frontmatter": {
            "preserve_structure": True,
            "preserve_comments": True,
            "fields_to_add": [
                "ai_categories",
                "ai_confidence",
                "ai_processed_date",
                "ai_version",
            ],
            "backup_before_write": True,
            "dry_run_default": False,
        },
        "lancedb": {
            "path": "data/lancedb",
            "index_type": "IVF_PQ",
            "index_params": {
                "num_partitions": 32,
                "num_sub_vectors": 16,
            },
            "embedding_dim": 768,
        },
        "processing": {
            "num_workers": 4,
            "embedding_batch_size": 32,
            "note_batch_size": 50,
            "sampling": {
                "strategy": "stratified",
                "percentage": 15,
            },
        },
        "logging": {
            "level": "INFO",
            "file": "logs/obsillama.log",
            "rotation": {
                "max_size_mb": 10,
                "backup_count": 5,
            },
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "console": True,
        },
        "metadata": {
            "config_version": "0.1.0",
            "created_at": datetime.now().strftime("%Y-%m-%d"),
        },
    }

    # Créer le dossier config si nécessaire
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Écrire le fichier YAML
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=2, offset=2)

    with open(output_path, "w", encoding="utf-8") as f:
        # Écrire le header
        f.write("# ObsIllama - Configuration principale\n")
        f.write("# =====================================\n")
        f.write(f"# Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Écrire la config
        yaml.dump(config, f)


def create_directories() -> List[Path]:
    """
    Crée les dossiers nécessaires pour ObsIllama.

    Returns:
        Liste des chemins créés
    """
    directories = [
        Path("config"),
        Path("data/lancedb"),
        Path("data/categories"),
        Path("data/cache"),
        Path("logs"),
    ]

    created = []
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        if directory.exists():
            created.append(directory)

    return created


@click.command()
@click.option(
    "--vault",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Chemin vers le vault Obsidian",
)
@click.option(
    "--ollama-url",
    default="http://localhost:11434",
    help="URL de l'API Ollama",
)
@click.option(
    "--generation-model",
    default="mistral",
    help="Modèle Ollama pour la génération",
)
@click.option(
    "--embedding-model",
    default="nomic-embed-text",
    help="Modèle Ollama pour les embeddings",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    help="Mode non-interactif (utilise les valeurs par défaut)",
)
@pass_context
def init(
    ctx: ObsillamaContext,
    vault: Optional[Path],
    ollama_url: str,
    generation_model: str,
    embedding_model: str,
    non_interactive: bool,
):
    """
    Initialise un nouveau projet ObsIllama.

    Cette commande configure votre environnement ObsIllama en :
      • Vérifiant l'accès au vault Obsidian
      • Testant la connexion à Ollama
      • Créant le fichier config.yaml
      • Créant les dossiers nécessaires

    \b
    Exemple :
      obsillama init --vault "/path/to/vault"
    """
    print_header("🦙 ObsIllama - Initialisation")

    print_panel(
        "Bienvenue dans ObsIllama !\n\n"
        "Cette commande va vous guider dans la configuration initiale.\n"
        "Vous aurez besoin de :\n"
        "  • Un vault Obsidian existant\n"
        "  • Ollama installé et en cours d'exécution",
        title="Prérequis",
        border_style="cyan",
    )

    console.print()

    # Vérifier si config existe déjà
    if Path("config/config.yaml").exists() and not non_interactive:
        print_warning("Un fichier config.yaml existe déjà.")
        if not confirm("Voulez-vous le remplacer ?", default=False):
            print_info("Initialisation annulée.")
            sys.exit(0)

    # ========================================================================
    # Étape 1 : Vault Obsidian
    # ========================================================================
    print_step(1, 5, "Configuration du vault Obsidian")

    if vault is None and not non_interactive:
        vault_input = prompt(
            "Chemin vers votre vault Obsidian",
            default="~/Documents/Obsidian",
        )
        vault = Path(vault_input).expanduser()
    elif vault is None:
        print_error("Le chemin du vault est requis en mode non-interactif.")
        sys.exit(1)

    # Valider le vault
    if not vault.exists():
        print_error(f"Le chemin n'existe pas : {vault}")
        sys.exit(1)

    if not vault.is_dir():
        print_error(f"Le chemin n'est pas un dossier : {vault}")
        sys.exit(1)

    print_success(f"Vault trouvé : {vault}")
    console.print()

    # ========================================================================
    # Étape 2 : Connexion Ollama
    # ========================================================================
    print_step(2, 5, "Test de connexion à Ollama")

    if not non_interactive:
        ollama_url = prompt(
            "URL de l'API Ollama",
            default=ollama_url,
        )

    print_info(f"Test de connexion à {ollama_url}...")

    if not check_ollama_connection(ollama_url):
        print_error(
            f"Impossible de se connecter à Ollama sur {ollama_url}\n"
            "Assurez-vous qu'Ollama est installé et en cours d'exécution.\n"
            "Installation : https://ollama.ai"
        )
        sys.exit(1)

    print_success("Connexion à Ollama réussie !")
    console.print()

    # ========================================================================
    # Étape 3 : Sélection des modèles
    # ========================================================================
    print_step(3, 5, "Configuration des modèles Ollama")

    # Récupérer les modèles disponibles
    print_info("Récupération de la liste des modèles...")
    models = get_ollama_models(ollama_url)

    if models:
        print_success(f"{len(models)} modèle(s) trouvé(s)")

        # Afficher les modèles disponibles
        if ctx.verbose:
            print_info("Modèles disponibles :")
            for model in models[:10]:  # Limiter à 10 pour ne pas surcharger
                console.print(f"  • {model.get('name', 'Unknown')}")
            if len(models) > 10:
                console.print(f"  ... et {len(models) - 10} autres")
            console.print()

        # Vérifier si les modèles par défaut sont disponibles
        model_names = [m.get("name", "").split(":")[0] for m in models]

        if not non_interactive:
            # Demander le modèle de génération
            if generation_model not in model_names:
                print_warning(
                    f"Le modèle '{generation_model}' n'est pas installé."
                )
                generation_model = prompt(
                    "Modèle de génération",
                    default="mistral",
                )

            # Demander le modèle d'embedding
            if embedding_model not in model_names:
                print_warning(
                    f"Le modèle '{embedding_model}' n'est pas installé."
                )
                embedding_model = prompt(
                    "Modèle d'embedding",
                    default="nomic-embed-text",
                )
    else:
        print_warning("Impossible de récupérer la liste des modèles.")
        if not non_interactive:
            generation_model = prompt(
                "Modèle de génération",
                default=generation_model,
            )
            embedding_model = prompt(
                "Modèle d'embedding",
                default=embedding_model,
            )

    print_info(f"Modèle de génération : {generation_model}")
    print_info(f"Modèle d'embedding : {embedding_model}")
    console.print()

    # ========================================================================
    # Étape 4 : Création de config.yaml
    # ========================================================================
    print_step(4, 5, "Création du fichier config.yaml")

    try:
        create_config_yaml(
            vault_path=str(vault),
            ollama_url=ollama_url,
            generation_model=generation_model,
            embedding_model=embedding_model,
        )
        print_success("Fichier config.yaml créé avec succès")
    except Exception as e:
        print_error(f"Erreur lors de la création du config.yaml : {e}")
        sys.exit(1)

    console.print()

    # ========================================================================
    # Étape 5 : Création des dossiers
    # ========================================================================
    print_step(5, 5, "Création des dossiers du projet")

    try:
        directories = create_directories()
        print_success(f"{len(directories)} dossier(s) créé(s)")

        if ctx.verbose:
            for directory in directories:
                console.print(f"  • {directory}/")
    except Exception as e:
        print_error(f"Erreur lors de la création des dossiers : {e}")
        sys.exit(1)

    console.print()

    # ========================================================================
    # Résumé
    # ========================================================================
    print_header("✓ Initialisation terminée")

    print_summary(
        title="Configuration",
        items=[
            f"Vault : {vault}",
            f"Ollama : {ollama_url}",
            f"Modèle de génération : {generation_model}",
            f"Modèle d'embedding : {embedding_model}",
            f"Config : config/config.yaml",
        ],
        border_style="green",
    )

    console.print()

    print_panel(
        "ObsIllama est maintenant configuré !\n\n"
        "Prochaines étapes :\n"
        "  1. obsillama scan          # Scanner votre vault\n"
        "  2. obsillama analyze       # Analyser et catégoriser\n"
        "  3. obsillama review        # Réviser les catégories\n"
        "  4. obsillama embed         # Générer les embeddings\n"
        "  5. obsillama apply         # Appliquer au vault",
        title="🚀 Démarrage",
        border_style="cyan",
    )
