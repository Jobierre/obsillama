"""
ObsIllama - Review Command

Commande CLI pour réviser et gérer les catégories générées par l'IA.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from obsillama.storage.category_store import CategoryStore
from obsillama.models.category import ReviewStatus
from obsillama.utils.yaml_exporter import (
    export_categories_to_yaml,
    import_categories_from_yaml,
    merge_categories,
    validate_yaml_file,
)
from obsillama.utils.progress import (
    print_step,
    print_panel,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_stats,
    print_table,
    confirm,
)

logger = logging.getLogger(__name__)
console = Console()


# =============================================================================
# Review Command
# =============================================================================

@click.command()
@click.option(
    "--export",
    "-e",
    "export_file",
    type=click.Path(),
    help="Exporter les catégories vers un fichier YAML",
)
@click.option(
    "--import",
    "-i",
    "import_file",
    type=click.Path(exists=True),
    help="Importer les catégories depuis un fichier YAML édité",
)
@click.option(
    "--interactive",
    is_flag=True,
    help="Lancer l'interface interactive (TUI avec Textual)",
)
@click.option(
    "--with-assignments",
    is_flag=True,
    help="Inclure les assignations de notes dans l'export",
)
@click.pass_context
def review(
    ctx,
    export_file: Optional[str],
    import_file: Optional[str],
    interactive: bool,
    with_assignments: bool,
):
    """
    Réviser et gérer les catégories générées par l'IA.

    Cette commande offre trois modes d'utilisation :

    \b
    1. MODE EXPORT (--export FILE)
       - Exporte les catégories vers un fichier YAML
       - Vous pouvez ensuite éditer le fichier manuellement
       - Exemple : obsillama review --export categories.yaml

    \b
    2. MODE IMPORT (--import FILE)
       - Importe les catégories depuis un fichier YAML édité
       - Applique les modifications et fusions demandées
       - Exemple : obsillama review --import categories.yaml

    \b
    3. MODE INTERACTIF (--interactive ou par défaut)
       - Interface textuelle interactive (TUI)
       - Édition en temps réel des catégories
       - Navigation par clavier
       - Exemple : obsillama review --interactive
    """
    logger.info("Commande review démarrée")

    # Déterminer le mode
    if export_file:
        _run_export_mode(export_file, with_assignments)
    elif import_file:
        _run_import_mode(import_file)
    elif interactive:
        _run_interactive_mode(ctx)
    else:
        # Mode interactif par défaut
        _run_interactive_mode(ctx)


# =============================================================================
# Export Mode
# =============================================================================

def _run_export_mode(export_file: str, with_assignments: bool):
    """
    Exporte les catégories vers un fichier YAML.

    Args:
        export_file: Chemin du fichier de sortie
        with_assignments: Inclure les assignations
    """
    print_panel(
        "Export des catégories vers un fichier YAML éditable.",
        title="🔍 Mode Export",
        border_style="cyan",
    )

    try:
        # Étape 1 : Charger les catégories
        print_step(1, 3, "Chargement de la taxonomie")
        store = CategoryStore()
        categories = store.load_taxonomy()

        if not categories:
            print_warning("Aucune catégorie trouvée. Exécutez 'obsillama analyze' d'abord.")
            sys.exit(0)

        print_info(f"  → {len(categories)} catégories chargées")

        # Étape 2 : Charger les assignations (si demandé)
        assignments = None
        if with_assignments:
            print_step(2, 3, "Chargement des assignations")
            assignments = store.load_assignments()
            total_notes = sum(len(v) for v in assignments.values())
            print_info(f"  → {total_notes} assignations chargées")
        else:
            print_step(2, 3, "Pas d'assignations (utilisez --with-assignments)")

        # Étape 3 : Export YAML
        print_step(3, 3, "Export vers YAML")
        output_path = Path(export_file)

        # Vérifier si le fichier existe
        if output_path.exists():
            if not confirm(f"Le fichier {output_path} existe déjà. Écraser ?"):
                print_warning("Export annulé")
                sys.exit(0)

        export_categories_to_yaml(
            categories=categories,
            output_file=output_path,
            include_assignments=with_assignments,
            assignments=assignments,
        )

        print_success(f"✓ Export réussi : {output_path}")

        # Statistiques
        stats_data = {
            "Catégories exportées": len(categories),
            "Catégories approuvées": len([c for c in categories if c.is_approved()]),
            "Catégories en attente": len([c for c in categories if c.needs_review()]),
        }

        if with_assignments and assignments:
            stats_data["Assignations incluses"] = sum(len(v) for v in assignments.values())

        print_stats(stats_data, title="📊 Statistiques")

        # Instructions
        print_panel(
            "📝 Prochaines étapes",
            f"""
1. Éditez le fichier : {output_path}
2. Modifiez les catégories selon vos besoins :
   - Changer name, description, keywords
   - Approuver : review_status: approved
   - Rejeter : review_status: rejected
   - Fusionner : ajouter les IDs dans merge_with
3. Importez les modifications :
   obsillama review --import {output_path}
            """.strip(),
            border_style="green",
        )

    except Exception as e:
        logger.error(f"Erreur export : {e}", exc_info=True)
        print_error(f"Erreur lors de l'export : {e}")
        sys.exit(1)


# =============================================================================
# Import Mode
# =============================================================================

def _run_import_mode(import_file: str):
    """
    Importe les catégories depuis un fichier YAML édité.

    Args:
        import_file: Chemin du fichier YAML
    """
    print_panel(
        "📥 Mode Import",
        "Import des catégories depuis un fichier YAML édité.",
        border_style="cyan",
    )

    try:
        input_path = Path(import_file)

        # Étape 1 : Validation du fichier
        print_step(1, 4, "Validation du fichier YAML")
        is_valid, errors = validate_yaml_file(input_path)

        if not is_valid:
            print_error("Le fichier YAML contient des erreurs :")
            for err in errors:
                console.print(f"  ❌ {err}", style="red")
            sys.exit(1)

        print_success("✓ Fichier YAML valide")

        # Étape 2 : Import du YAML
        print_step(2, 4, "Import des catégories")
        categories, merge_requests = import_categories_from_yaml(input_path)

        print_info(f"  → {len(categories)} catégories importées")

        if merge_requests:
            print_info(f"  → {len(merge_requests)} demandes de fusion détectées")

        # Étape 3 : Traiter les fusions
        if merge_requests:
            print_step(3, 4, "Traitement des fusions")

            # Afficher les fusions
            console.print("\n🔗 Fusions demandées :", style="bold yellow")
            for target_id, source_ids in merge_requests.items():
                target = next((c for c in categories if c.id == target_id), None)
                if target:
                    console.print(f"  • {target.name} ← {len(source_ids)} catégorie(s)")

            if confirm("\nAppliquer ces fusions ?"):
                categories = merge_categories(categories, merge_requests)
                print_success(f"✓ Fusions appliquées : {len(categories)} catégories restantes")
            else:
                print_warning("Fusions annulées")
        else:
            print_step(3, 4, "Pas de fusions demandées")

        # Étape 4 : Sauvegarde
        print_step(4, 4, "Sauvegarde de la taxonomie")

        store = CategoryStore()
        store.save_taxonomy(categories)

        print_success("✓ Taxonomie mise à jour")

        # Statistiques
        approved = len([c for c in categories if c.is_approved()])
        pending = len([c for c in categories if c.needs_review()])
        rejected = len([c for c in categories if c.review_status == ReviewStatus.REJECTED])

        stats_data = {
            "Total catégories": len(categories),
            "Approuvées": approved,
            "En attente": pending,
            "Rejetées": rejected,
        }

        print_stats(stats_data, title="📊 Résumé")

        # Afficher les catégories modifiées
        modified = [c for c in categories if c.review_status == ReviewStatus.MODIFIED]
        if modified:
            console.print("\n✏️  Catégories modifiées :", style="bold blue")
            for cat in modified[:5]:
                console.print(f"  • {cat.name}")

            if len(modified) > 5:
                console.print(f"  ... et {len(modified) - 5} autres")

        # Prochaines étapes
        print_panel(
            "🎯 Prochaines étapes",
            """
1. Pour appliquer les catégories aux notes :
   obsillama apply --dry-run  (prévisualisation)
   obsillama apply            (application)

2. Pour continuer la review :
   obsillama review --interactive
            """.strip(),
            border_style="green",
        )

    except Exception as e:
        logger.error(f"Erreur import : {e}", exc_info=True)
        print_error(f"Erreur lors de l'import : {e}")
        sys.exit(1)


# =============================================================================
# Interactive Mode
# =============================================================================

def _run_interactive_mode(ctx):
    """
    Lance l'interface interactive (TUI avec Textual).

    Args:
        ctx: Contexte Click
    """
    print_panel(
        "🎨 Mode Interactif",
        "Lancement de l'interface interactive...",
        border_style="cyan",
    )

    try:
        # Vérifier que les catégories existent
        store = CategoryStore()
        categories = store.load_taxonomy()

        if not categories:
            print_warning("Aucune catégorie trouvée.")
            print_info("Exécutez d'abord : obsillama analyze")
            sys.exit(0)

        print_info(f"Chargement de {len(categories)} catégories...")

        # Import dynamique de Textual (pour ne pas ralentir les autres modes)
        try:
            from obsillama.cli.review_tui import ReviewApp
        except ImportError:
            print_error("Textual n'est pas installé ou ReviewApp non trouvée")
            print_info("Installation : pip install textual")
            sys.exit(1)

        # Lancer l'app Textual
        app = ReviewApp(categories=categories, store=store)
        app.run()

    except KeyboardInterrupt:
        print_warning("\nInterruption utilisateur")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Erreur mode interactif : {e}", exc_info=True)
        print_error(f"Erreur lors de l'affichage interactif : {e}")
        sys.exit(1)
