"""
ObsIllama - Commande apply

Cette commande applique les catégories AI aux notes Obsidian en modifiant
leur frontmatter YAML.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
from rich.progress import track

from obsillama.cli.commands import pass_context, ObsillamaContext
from obsillama.core.frontmatter_writer import FrontmatterWriter
from obsillama.models.category import Category, ReviewStatus
from obsillama.models.note import Note
from obsillama.storage.lancedb_manager import LanceDBManager
from obsillama.utils.file_utils import BackupManager
from obsillama.utils.progress import (
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_step,
    print_stats,
    print_panel,
    console,
)


@click.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Mode preview : affiche les changements sans modifier les fichiers",
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Créer un backup avant modification (défaut: activé)",
)
@click.option(
    "--tags-only",
    is_flag=True,
    help="Ajouter uniquement les tags AI-Category-* (sans champs ai_*)",
)
@click.option(
    "--new-only",
    is_flag=True,
    help="Appliquer uniquement aux notes sans métadonnées AI existantes",
)
@click.option(
    "--min-confidence",
    type=float,
    default=0.6,
    help="Confidence minimale pour assigner une catégorie (défaut: 0.6)",
)
@pass_context
def apply(
    ctx: ObsillamaContext,
    dry_run: bool,
    backup: bool,
    tags_only: bool,
    new_only: bool,
    min_confidence: float,
):
    """
    Applique les catégories AI aux notes Obsidian.

    Cette commande:
    1. Charge les catégories approuvées
    2. Charge les assignations notes → catégories
    3. Crée un backup snapshot (si --backup)
    4. Modifie le frontmatter des notes avec les tags AI
    5. Affiche un résumé des modifications

    Modes:
        --dry-run : Preview des changements sans modification
        --backup : Backup automatique avant modification (recommandé)
        --tags-only : Ajoute uniquement les tags (pas les métadonnées)
        --new-only : Skip les notes déjà traitées

    Exemples:
        obsillama apply --dry-run
        obsillama apply --backup
        obsillama apply --new-only --min-confidence 0.7
        obsillama apply --tags-only --no-backup
    """
    # En-tête
    if dry_run:
        print_header("🔍 Preview - Application des Catégories (Dry Run)")
        print_warning("Mode DRY-RUN : aucune modification ne sera effectuée")
    else:
        print_header("🏷️  Application des Catégories AI aux Notes")
        print_info("Cette commande modifie le frontmatter de vos notes Obsidian")

    console.print()

    config = ctx.config

    try:
        # Étape 1/6 : Chargement des catégories approuvées
        print_step(1, 6, "Chargement des catégories approuvées")
        categories_data = load_approved_categories(config)

        if not categories_data:
            print_error("Aucune catégorie approuvée trouvée")
            print_info(
                "💡 Utilisez 'obsillama review --interactive' pour approuver des catégories"
            )
            sys.exit(1)

        print_success(
            f"{len(categories_data)} catégorie(s) approuvée(s) chargée(s)"
        )
        console.print()

        # Étape 2/6 : Chargement des assignations
        print_step(2, 6, "Chargement des assignations notes → catégories")
        assignments = load_assignments(config)

        # Filtrer par confidence minimale
        filtered_assignments = filter_by_confidence(
            assignments, min_confidence
        )

        print_success(
            f"{len(filtered_assignments)} note(s) assignée(s) "
            f"(confidence ≥ {min_confidence})"
        )
        console.print()

        # Étape 3/6 : Chargement des notes depuis LanceDB
        print_step(3, 6, "Chargement des notes depuis LanceDB")
        db_manager = LanceDBManager(
            db_path=Path(config.lancedb.path)
        )
        all_notes_dicts = db_manager.get_all_notes()

        # Convertir les dicts en objets Note
        all_notes = [Note(**note_dict) for note_dict in all_notes_dicts]

        # Créer un mapping note_id → Note
        notes_by_id = {note.id: note for note in all_notes}

        print_success(f"{len(all_notes)} note(s) chargée(s) depuis la base")
        console.print()

        # Étape 4/6 : Préparation des modifications
        print_step(4, 6, "Préparation des modifications")

        modifications = prepare_modifications(
            filtered_assignments,
            categories_data,
            notes_by_id,
            new_only,
        )

        if not modifications:
            print_warning("Aucune modification à effectuer")
            sys.exit(0)

        print_success(f"{len(modifications)} note(s) à modifier")
        console.print()

        # Afficher preview si dry-run
        if dry_run:
            show_preview(modifications, categories_data)
            print_panel(
                "Mode dry-run activé",
                "✓ Preview des changements terminée\n"
                "✓ Aucune modification effectuée\n\n"
                "💡 Exécutez sans --dry-run pour appliquer les changements",
            )
            sys.exit(0)

        # Étape 5/6 : Création du backup (si activé)
        backup_manager = None
        snapshot_id = None

        if backup:
            print_step(5, 6, "Création du backup snapshot")
            backup_manager = BackupManager()
            snapshot_id = backup_manager.create_backup_snapshot(
                description="Before apply categories"
            )
            print_success(f"Snapshot créé: {snapshot_id}")
            console.print()
        else:
            print_step(5, 6, "Backup désactivé (--no-backup)")
            print_warning("⚠️  Aucun backup ne sera créé")
            console.print()

        # Étape 6/6 : Application des modifications
        print_step(6, 6, "Application des catégories aux notes")

        writer = FrontmatterWriter()
        success_count = 0
        error_count = 0
        errors = []

        for mod_info in track(
            modifications,
            description="Application en cours...",
            console=console,
        ):
            note = mod_info["note"]
            categories = mod_info["categories"]
            confidence = mod_info["confidence"]
            file_path = Path(note.file_path)

            try:
                # Backup du fichier individuel si snapshot créé
                if backup and backup_manager and snapshot_id:
                    backup_manager.backup_file(
                        file_path,
                        snapshot_id,
                        preserve_structure=True,
                        vault_root=Path(config.vault.path),
                    )

                # Appliquer les catégories
                if tags_only:
                    # TODO: Implémenter mode tags-only
                    # Pour l'instant, on fait l'application complète
                    pass

                writer.update_frontmatter(
                    file_path,
                    categories,
                    confidence,
                    backup=False,  # Backup déjà géré par BackupManager
                )

                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append({
                    "note": note.title,
                    "error": str(e),
                })

        console.print()

        # Résumé final
        print_header("📊 Résumé de l'Application")

        stats = {
            "Notes traitées": len(modifications),
            "Succès": success_count,
            "Échecs": error_count,
            "Catégories appliquées": len(categories_data),
        }

        if backup and snapshot_id:
            stats["Backup snapshot"] = snapshot_id

        print_stats(stats)

        # Afficher les erreurs si présentes
        if errors:
            console.print()
            print_warning(f"⚠️  {error_count} erreur(s) rencontrée(s):")
            for err in errors[:5]:  # Limiter à 5 erreurs affichées
                console.print(f"  • {err['note']}: {err['error']}")
            if len(errors) > 5:
                console.print(f"  ... et {len(errors) - 5} autre(s)")

        console.print()

        # Prochaines étapes
        if success_count > 0:
            print_panel(
                "✅ Application terminée avec succès",
                "📝 Prochaines étapes:\n"
                "1. Ouvrez Obsidian et vérifiez les tags AI-Category-*\n"
                "2. Utilisez le graph view pour explorer les catégories\n"
                "3. Les métadonnées AI sont visibles dans le frontmatter\n\n"
                f"💾 Backup disponible: {snapshot_id if snapshot_id else 'N/A'}\n"
                "🔄 Restauration: obsillama restore (à implémenter)",
            )
        else:
            print_error("Aucune note n'a été modifiée avec succès")
            sys.exit(1)

    except Exception as e:
        print_error(f"Erreur inattendue: {e}")
        if ctx.verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


# ============================================================================
# Fonctions helper
# ============================================================================


def load_approved_categories(config) -> Dict[str, Category]:
    """
    Charge les catégories avec statut 'approved' depuis taxonomy.json.

    Returns:
        Dict[str, Category]: Mapping category_id → Category
    """
    # Le fichier taxonomy.json est dans data/categories/ à la racine du projet
    taxonomy_path = Path("data/categories/taxonomy.json")

    if not taxonomy_path.exists():
        return {}

    with open(taxonomy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    categories = {}

    for cat_data in data.get("categories", []):
        # Ne garder que les catégories approuvées
        if cat_data.get("review_status") == "approved":
            category = Category(**cat_data)
            categories[category.id] = category

    return categories


def load_assignments(config) -> Dict[str, List[Dict]]:
    """
    Charge les assignations notes → catégories depuis assignments.json.

    Returns:
        Dict[str, List[Dict]]: Mapping category_id → [{note_id, confidence}, ...]
    """
    # Le fichier assignments.json est dans data/categories/ à la racine du projet
    assignments_path = Path("data/categories/assignments.json")

    if not assignments_path.exists():
        return {}

    with open(assignments_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("assignments", {})


def filter_by_confidence(
    assignments: Dict[str, List[Dict]],
    min_confidence: float,
) -> Dict[str, List[Dict]]:
    """
    Filtre les assignations par confidence minimale.

    Args:
        assignments: Assignations brutes
        min_confidence: Seuil minimal de confidence

    Returns:
        Dict filtre
    """
    filtered = {}

    for category_id, note_assignments in assignments.items():
        filtered_notes = [
            assignment
            for assignment in note_assignments
            if assignment.get("confidence", 0) >= min_confidence
        ]

        if filtered_notes:
            filtered[category_id] = filtered_notes

    return filtered


def prepare_modifications(
    assignments: Dict[str, List[Dict]],
    categories: Dict[str, Category],
    notes_by_id: Dict[str, Note],
    new_only: bool,
) -> List[Dict]:
    """
    Prépare la liste des modifications à effectuer.

    Returns:
        List[Dict]: [{note, categories, confidence}, ...]
    """
    modifications = []
    note_to_categories = {}  # note_id → [(Category, confidence)]

    # Construire le mapping note → catégories
    for category_id, note_assignments in assignments.items():
        if category_id not in categories:
            continue  # Catégorie non approuvée

        category = categories[category_id]

        for assignment in note_assignments:
            note_id = assignment["note_id"]
            confidence = assignment["confidence"]

            if note_id not in note_to_categories:
                note_to_categories[note_id] = []

            note_to_categories[note_id].append((category, confidence))

    # Créer les modifications
    for note_id, cat_conf_list in note_to_categories.items():
        if note_id not in notes_by_id:
            continue  # Note non trouvée dans LanceDB

        note = notes_by_id[note_id]

        # Skip si new_only et note déjà traitée
        if new_only and has_ai_metadata(note):
            continue

        # Extraire catégories et confidence moyenne
        categories_list = [cat for cat, _ in cat_conf_list]
        avg_confidence = sum(conf for _, conf in cat_conf_list) / len(cat_conf_list)

        modifications.append({
            "note": note,
            "categories": categories_list,
            "confidence": avg_confidence,
        })

    return modifications


def has_ai_metadata(note: Note) -> bool:
    """
    Vérifie si une note a déjà des métadonnées AI.

    Args:
        note: Note à vérifier

    Returns:
        bool: True si métadonnées AI présentes
    """
    # Vérifier les tags AI
    for tag in note.tags:
        if tag.lower().startswith("ai-category-"):
            return True

    # On pourrait aussi vérifier le frontmatter si disponible
    # mais pour l'instant on se base sur les tags

    return False


def show_preview(
    modifications: List[Dict],
    categories: Dict[str, Category],
) -> None:
    """
    Affiche un preview des modifications en mode dry-run.

    Args:
        modifications: Liste des modifications
        categories: Catégories disponibles
    """
    from rich.table import Table

    table = Table(title="Preview des Modifications", show_header=True)
    table.add_column("Note", style="cyan", no_wrap=False, width=30)
    table.add_column("Catégories à Ajouter", style="green", width=40)
    table.add_column("Confidence", style="yellow", justify="right", width=12)

    # Limiter à 20 pour l'affichage
    preview_mods = modifications[:20]

    for mod_info in preview_mods:
        note = mod_info["note"]
        cats = mod_info["categories"]
        confidence = mod_info["confidence"]

        cat_names = ", ".join([cat.name for cat in cats])

        table.add_row(
            note.title[:30],
            cat_names,
            f"{confidence:.2f}",
        )

    if len(modifications) > 20:
        table.add_row(
            f"... et {len(modifications) - 20} autre(s)",
            "",
            "",
            style="dim",
        )

    console.print(table)
    console.print()
