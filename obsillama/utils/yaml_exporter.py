"""
ObsIllama - YAML Exporter/Importer pour Catégories

Ce module gère l'export/import des catégories au format YAML pour permettre
l'édition manuelle par l'utilisateur.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from obsillama.models.category import Category, ReviewStatus

logger = logging.getLogger(__name__)


# =============================================================================
# YAML Configuration
# =============================================================================

def get_yaml_handler() -> YAML:
    """
    Crée un handler YAML avec la configuration appropriée.

    Returns:
        Handler YAML configuré
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 4096  # Pas de wrapping
    yaml.indent(mapping=2, sequence=2, offset=0)
    return yaml


# =============================================================================
# Export to YAML
# =============================================================================

def export_categories_to_yaml(
    categories: List[Category],
    output_file: Path,
    include_assignments: bool = False,
    assignments: Dict[str, List[tuple]] = None,
) -> None:
    """
    Exporte les catégories vers un fichier YAML éditable.

    Args:
        categories: Liste des catégories à exporter
        output_file: Fichier de sortie
        include_assignments: Inclure les assignations de notes
        assignments: Dict {category_id: [(note_id, confidence)]}
    """
    logger.info(f"Export de {len(categories)} catégories vers {output_file}")

    yaml = get_yaml_handler()

    # Préparer la structure
    data = CommentedMap()

    # Métadonnées
    data['metadata'] = {
        'exported_at': datetime.now().isoformat(),
        'category_count': len(categories),
        'format_version': '1.0',
    }

    # Instructions pour l'utilisateur
    data.yaml_set_comment_before_after_key(
        'categories',
        before='\nInstructions:\n'
               '  - Vous pouvez éditer les champs: name, description, tag_name, keywords\n'
               '  - Pour approuver une catégorie: review_status: approved\n'
               '  - Pour rejeter une catégorie: review_status: rejected\n'
               '  - Pour fusionner des catégories: ajoutez leur ID dans merge_with\n'
               '  - Ne modifiez pas les champs: id, created_at, version\n',
    )

    # Catégories
    categories_list = []

    for category in categories:
        # Créer un dict éditable
        cat_data = CommentedMap()

        # Champs obligatoires
        cat_data['id'] = category.id
        cat_data['name'] = category.name
        cat_data['description'] = category.description
        cat_data['tag_name'] = category.tag_name

        # Hiérarchie
        if category.parent_id:
            cat_data['parent_id'] = category.parent_id
        cat_data['level'] = category.level

        if category.children_ids:
            cat_data['children_ids'] = category.children_ids

        # Métadonnées sémantiques
        if category.keywords:
            cat_data['keywords'] = category.keywords

        if category.representative_terms:
            cat_data['representative_terms'] = category.representative_terms

        # Statistiques (lecture seule)
        cat_data['statistics'] = {
            'note_count': category.note_count,
            'avg_confidence': round(category.avg_confidence, 3),
            'coherence_score': round(category.coherence_score, 3),
            'distinctiveness_score': round(category.distinctiveness_score, 3),
        }

        # Review
        cat_data['review_status'] = category.review_status.value

        if category.reviewed_by:
            cat_data['reviewed_by'] = category.reviewed_by

        if category.reviewed_at:
            cat_data['reviewed_at'] = category.reviewed_at.isoformat()

        # Suggestions
        if category.merge_suggestions:
            cat_data['merge_suggestions'] = category.merge_suggestions

        if category.split_suggested:
            cat_data['split_suggested'] = category.split_suggested

        # Champ pour fusion manuelle
        cat_data['merge_with'] = None
        cat_data.yaml_set_comment_before_after_key(
            'merge_with',
            before='Ajoutez les IDs des catégories à fusionner avec celle-ci',
        )

        # Visualisation
        if category.color:
            cat_data['color'] = category.color

        if category.icon:
            cat_data['icon'] = category.icon

        # Assignations (optionnel)
        if include_assignments and assignments:
            notes_for_cat = assignments.get(category.id, [])
            if notes_for_cat:
                cat_data['assigned_notes'] = [
                    {
                        'note_id': note_id,
                        'confidence': round(conf, 3)
                    }
                    for note_id, conf in notes_for_cat[:10]  # Max 10 pour lisibilité
                ]

                if len(notes_for_cat) > 10:
                    cat_data.yaml_add_eol_comment(
                        f'{len(notes_for_cat) - 10} autres notes...',
                        'assigned_notes'
                    )

        # Métadonnées (lecture seule)
        cat_data['_metadata'] = {
            'created_at': category.created_at.isoformat(),
            'created_by': category.created_by,
            'version': category.version,
        }

        categories_list.append(cat_data)

    data['categories'] = categories_list

    # Sauvegarder
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f)

        logger.info(f"✓ Export réussi : {output_file}")

    except Exception as e:
        logger.error(f"Erreur export YAML : {e}")
        raise


# =============================================================================
# Import from YAML
# =============================================================================

def import_categories_from_yaml(
    input_file: Path,
) -> tuple[List[Category], Dict[str, List[str]]]:
    """
    Importe les catégories depuis un fichier YAML édité.

    Args:
        input_file: Fichier YAML à importer

    Returns:
        Tuple (categories, merge_requests)
        - categories: Liste des catégories mises à jour
        - merge_requests: Dict {target_id: [source_ids]} pour les fusions
    """
    logger.info(f"Import des catégories depuis {input_file}")

    if not input_file.exists():
        raise FileNotFoundError(f"Fichier introuvable : {input_file}")

    yaml = get_yaml_handler()

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = yaml.load(f)

        categories_data = data.get('categories', [])
        logger.info(f"  → {len(categories_data)} catégories trouvées")

        categories = []
        merge_requests = {}

        for cat_data in categories_data:
            # Reconstruire la catégorie
            category = _rebuild_category_from_yaml(cat_data)
            categories.append(category)

            # Vérifier les demandes de fusion
            merge_with = cat_data.get('merge_with')
            if merge_with:
                if isinstance(merge_with, str):
                    merge_with = [merge_with]

                if merge_with:
                    merge_requests[category.id] = merge_with
                    logger.info(
                        f"  → Fusion demandée : {category.name} ← "
                        f"{', '.join(merge_with)}"
                    )

        logger.info(f"✓ Import réussi : {len(categories)} catégories")
        if merge_requests:
            logger.info(f"  → {len(merge_requests)} demandes de fusion")

        return categories, merge_requests

    except Exception as e:
        logger.error(f"Erreur import YAML : {e}")
        raise


def _rebuild_category_from_yaml(cat_data: Dict[str, Any]) -> Category:
    """
    Reconstruit un objet Category depuis les données YAML.

    Args:
        cat_data: Dictionnaire de données YAML

    Returns:
        Instance de Category
    """
    # Champs obligatoires
    category_dict = {
        'id': cat_data['id'],
        'name': cat_data['name'],
        'description': cat_data.get('description', ''),
        'tag_name': cat_data['tag_name'],
    }

    # Hiérarchie
    if 'parent_id' in cat_data:
        category_dict['parent_id'] = cat_data['parent_id']

    category_dict['level'] = cat_data.get('level', 0)
    category_dict['children_ids'] = cat_data.get('children_ids', [])

    # Métadonnées sémantiques
    category_dict['keywords'] = cat_data.get('keywords', [])
    category_dict['representative_terms'] = cat_data.get('representative_terms', [])

    # Statistiques
    stats = cat_data.get('statistics', {})
    category_dict['note_count'] = stats.get('note_count', 0)
    category_dict['avg_confidence'] = stats.get('avg_confidence', 0.0)
    category_dict['coherence_score'] = stats.get('coherence_score', 0.0)
    category_dict['distinctiveness_score'] = stats.get('distinctiveness_score', 0.0)

    # Review status
    review_status_str = cat_data.get('review_status', 'pending')
    category_dict['review_status'] = ReviewStatus(review_status_str)

    if 'reviewed_by' in cat_data:
        category_dict['reviewed_by'] = cat_data['reviewed_by']

    if 'reviewed_at' in cat_data:
        category_dict['reviewed_at'] = datetime.fromisoformat(cat_data['reviewed_at'])

    # Suggestions
    category_dict['merge_suggestions'] = cat_data.get('merge_suggestions', [])
    category_dict['split_suggested'] = cat_data.get('split_suggested', False)

    # Visualisation
    if 'color' in cat_data:
        category_dict['color'] = cat_data['color']

    if 'icon' in cat_data:
        category_dict['icon'] = cat_data['icon']

    # Métadonnées
    metadata = cat_data.get('_metadata', {})

    if 'created_at' in metadata:
        category_dict['created_at'] = datetime.fromisoformat(metadata['created_at'])

    category_dict['created_by'] = metadata.get('created_by', 'graphrag')
    category_dict['version'] = metadata.get('version', 1)

    # Communauté source
    if 'community_id' in cat_data:
        category_dict['community_id'] = cat_data['community_id']

    # Créer l'instance
    return Category(**category_dict)


# =============================================================================
# Merge Categories
# =============================================================================

def merge_categories(
    categories: List[Category],
    merge_requests: Dict[str, List[str]],
) -> List[Category]:
    """
    Fusionne les catégories selon les demandes de l'utilisateur.

    Args:
        categories: Liste des catégories
        merge_requests: Dict {target_id: [source_ids]}

    Returns:
        Liste des catégories après fusion
    """
    logger.info(f"Fusion de {len(merge_requests)} catégories")

    # Index des catégories
    categories_dict = {cat.id: cat for cat in categories}

    # IDs des catégories à supprimer
    to_remove = set()

    for target_id, source_ids in merge_requests.items():
        if target_id not in categories_dict:
            logger.warning(f"Catégorie cible introuvable : {target_id}")
            continue

        target = categories_dict[target_id]

        # Fusionner chaque source
        for source_id in source_ids:
            if source_id not in categories_dict:
                logger.warning(f"Catégorie source introuvable : {source_id}")
                continue

            source = categories_dict[source_id]

            # Fusionner les keywords (déduplication)
            target.keywords = list(set(target.keywords + source.keywords))
            target.representative_terms = list(
                set(target.representative_terms + source.representative_terms)
            )

            # Fusionner les statistiques
            total_notes = target.note_count + source.note_count
            if total_notes > 0:
                target.avg_confidence = (
                    target.avg_confidence * target.note_count +
                    source.avg_confidence * source.note_count
                ) / total_notes
                target.note_count = total_notes

            # Marquer pour suppression
            to_remove.add(source_id)

            logger.info(f"  → Fusionné : {source.name} → {target.name}")

    # Filtrer les catégories supprimées
    merged_categories = [
        cat for cat in categories
        if cat.id not in to_remove
    ]

    logger.info(f"✓ Fusion terminée : {len(merged_categories)} catégories restantes")

    return merged_categories


# =============================================================================
# Validation
# =============================================================================

def validate_yaml_file(input_file: Path) -> tuple[bool, List[str]]:
    """
    Valide un fichier YAML de catégories.

    Args:
        input_file: Fichier YAML à valider

    Returns:
        Tuple (is_valid, errors)
    """
    errors = []

    if not input_file.exists():
        return False, [f"Fichier introuvable : {input_file}"]

    yaml = get_yaml_handler()

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = yaml.load(f)

        # Vérifier la structure
        if 'categories' not in data:
            errors.append("Clé 'categories' manquante")

        categories_data = data.get('categories', [])

        if not isinstance(categories_data, list):
            errors.append("'categories' doit être une liste")
            return False, errors

        # Valider chaque catégorie
        for i, cat_data in enumerate(categories_data):
            # Champs obligatoires
            required_fields = ['id', 'name', 'tag_name']
            for field in required_fields:
                if field not in cat_data:
                    errors.append(f"Catégorie {i}: champ '{field}' manquant")

            # ReviewStatus valide
            review_status = cat_data.get('review_status')
            if review_status and review_status not in ['pending', 'approved', 'rejected', 'modified']:
                errors.append(
                    f"Catégorie {i} ({cat_data.get('name', '?')}): "
                    f"review_status invalide : {review_status}"
                )

        if errors:
            return False, errors

        return True, []

    except Exception as e:
        return False, [f"Erreur parsing YAML : {e}"]
