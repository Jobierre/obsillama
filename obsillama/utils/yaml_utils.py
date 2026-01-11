"""
ObsIllama - YAML Utilities

Ce module fournit des fonctions utilitaires pour manipuler et valider le YAML
des frontmatter dans les notes Obsidian.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError

# Configuration du logger
logger = logging.getLogger(__name__)


def validate_frontmatter(frontmatter: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Valide un dictionnaire de frontmatter.

    Vérifie que:
    - Le frontmatter est un dictionnaire valide
    - Les clés sont des strings
    - Les valeurs sont de types supportés (str, int, float, list, dict, bool)

    Args:
        frontmatter: Le dictionnaire de frontmatter à valider

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)

    Examples:
        >>> validate_frontmatter({"title": "Test", "tags": ["a", "b"]})
        (True, None)
        >>> validate_frontmatter({"title": lambda x: x})
        (False, "Valeur non supportée pour la clé 'title': <lambda>")
    """
    if not isinstance(frontmatter, dict):
        return False, "Le frontmatter doit être un dictionnaire"

    # Types supportés dans le frontmatter
    SUPPORTED_TYPES = (str, int, float, bool, list, dict, type(None))

    for key, value in frontmatter.items():
        # Vérifier que les clés sont des strings
        if not isinstance(key, str):
            return False, f"Clé invalide (doit être string): {key}"

        # Vérifier que les valeurs sont de types supportés
        if not isinstance(value, SUPPORTED_TYPES):
            return False, f"Valeur non supportée pour la clé '{key}': {type(value).__name__}"

        # Si c'est une liste, vérifier les éléments
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, SUPPORTED_TYPES):
                    return (
                        False,
                        f"Élément de liste non supporté dans '{key}': {type(item).__name__}"
                    )

    return True, None


def normalize_tags(tags: Any) -> List[str]:
    """
    Normalise les tags en une liste de strings.

    Gère les cas:
    - tags: ["tag1", "tag2"] → ["tag1", "tag2"]
    - tags: "tag1, tag2" → ["tag1", "tag2"]
    - tags: "tag1" → ["tag1"]
    - tags: None → []

    Args:
        tags: Valeur du champ tags (peut être string, list, ou None)

    Returns:
        List[str]: Liste normalisée de tags (dédupliqués, triés)

    Examples:
        >>> normalize_tags(["python", "ai", "python"])
        ['ai', 'python']
        >>> normalize_tags("python, ai, docker")
        ['ai', 'docker', 'python']
        >>> normalize_tags(None)
        []
    """
    if tags is None:
        return []

    # Si c'est déjà une liste
    if isinstance(tags, list):
        # Convertir en strings et nettoyer
        tag_list = [str(tag).strip() for tag in tags if tag]
    # Si c'est une string
    elif isinstance(tags, str):
        # Séparer par virgule ou espace
        tag_list = [t.strip() for t in tags.replace(",", " ").split() if t.strip()]
    else:
        logger.warning(f"Type de tags non supporté: {type(tags)}")
        return []

    # Dédupliquer et trier
    return sorted(set(tag_list))


def merge_tags(existing_tags: Any, new_tags: List[str]) -> List[str]:
    """
    Fusionne les tags existants avec de nouveaux tags.

    Args:
        existing_tags: Tags existants (peut être string, list, ou None)
        new_tags: Nouveaux tags à ajouter

    Returns:
        List[str]: Liste fusionnée de tags (dédupliqués, triés)

    Examples:
        >>> merge_tags(["python", "ai"], ["docker", "ai"])
        ['ai', 'docker', 'python']
        >>> merge_tags("python, ai", ["docker"])
        ['ai', 'docker', 'python']
    """
    # Normaliser les tags existants
    existing_normalized = normalize_tags(existing_tags)

    # Normaliser les nouveaux tags
    new_normalized = normalize_tags(new_tags)

    # Fusionner et dédupliquer
    all_tags = set(existing_normalized + new_normalized)

    return sorted(all_tags)


def extract_ai_tags(tags: List[str]) -> List[str]:
    """
    Extrait uniquement les tags AI-Category-* d'une liste.

    Args:
        tags: Liste de tags

    Returns:
        List[str]: Liste des tags AI uniquement

    Examples:
        >>> extract_ai_tags(["python", "AI-Category-dev", "AI-Category-ml"])
        ['AI-Category-dev', 'AI-Category-ml']
    """
    return [tag for tag in tags if tag.startswith("AI-Category-")]


def remove_ai_tags(tags: List[str]) -> List[str]:
    """
    Supprime les tags AI-Category-* d'une liste.

    Args:
        tags: Liste de tags

    Returns:
        List[str]: Liste des tags sans les tags AI

    Examples:
        >>> remove_ai_tags(["python", "AI-Category-dev", "docker"])
        ['python', 'docker']
    """
    return [tag for tag in tags if not tag.startswith("AI-Category-")]


def has_ai_metadata(frontmatter: Dict[str, Any]) -> bool:
    """
    Vérifie si le frontmatter contient des métadonnées AI.

    Recherche:
    - Tags AI-Category-*
    - Champ ai_categories
    - Champ ai_confidence
    - Champ ai_processed_date

    Args:
        frontmatter: Dictionnaire de frontmatter

    Returns:
        bool: True si des métadonnées AI sont présentes

    Examples:
        >>> has_ai_metadata({"tags": ["AI-Category-dev"], "ai_confidence": 0.8})
        True
        >>> has_ai_metadata({"tags": ["python"], "title": "Test"})
        False
    """
    # Vérifier les champs AI directs
    ai_fields = ["ai_categories", "ai_confidence", "ai_processed_date"]
    if any(field in frontmatter for field in ai_fields):
        return True

    # Vérifier les tags AI
    tags = frontmatter.get("tags", [])
    normalized_tags = normalize_tags(tags)
    ai_tags = extract_ai_tags(normalized_tags)

    return len(ai_tags) > 0


def compare_frontmatter(
    old_frontmatter: Dict[str, Any],
    new_frontmatter: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compare deux frontmatter et retourne les différences.

    Args:
        old_frontmatter: Frontmatter original
        new_frontmatter: Frontmatter modifié

    Returns:
        Dict[str, Any]: Dictionnaire des changements
            {
                "added": {key: value},
                "modified": {key: (old_value, new_value)},
                "removed": {key: old_value}
            }

    Examples:
        >>> old = {"title": "Test", "tags": ["a"]}
        >>> new = {"title": "Updated", "tags": ["a", "b"], "ai_confidence": 0.8}
        >>> diff = compare_frontmatter(old, new)
        >>> diff["modified"]["title"]
        ('Test', 'Updated')
        >>> diff["added"]["ai_confidence"]
        0.8
    """
    added = {}
    modified = {}
    removed = {}

    # Clés dans le nouveau frontmatter
    new_keys = set(new_frontmatter.keys())
    old_keys = set(old_frontmatter.keys())

    # Clés ajoutées
    for key in new_keys - old_keys:
        added[key] = new_frontmatter[key]

    # Clés supprimées
    for key in old_keys - new_keys:
        removed[key] = old_frontmatter[key]

    # Clés modifiées
    for key in new_keys & old_keys:
        old_val = old_frontmatter[key]
        new_val = new_frontmatter[key]

        if old_val != new_val:
            modified[key] = (old_val, new_val)

    return {
        "added": added,
        "modified": modified,
        "removed": removed
    }


def format_frontmatter_diff(diff: Dict[str, Any]) -> str:
    """
    Formate un diff de frontmatter pour affichage lisible.

    Args:
        diff: Dictionnaire de différences (sortie de compare_frontmatter)

    Returns:
        str: Diff formaté en texte lisible

    Examples:
        >>> diff = {"added": {"ai_confidence": 0.8}, "modified": {"title": ("Old", "New")}}
        >>> print(format_frontmatter_diff(diff))
        + ai_confidence: 0.8
        ~ title: Old → New
    """
    lines = []

    # Ajouts
    for key, value in diff.get("added", {}).items():
        lines.append(f"+ {key}: {value}")

    # Modifications
    for key, (old_val, new_val) in diff.get("modified", {}).items():
        lines.append(f"~ {key}: {old_val} → {new_val}")

    # Suppressions
    for key, value in diff.get("removed", {}).items():
        lines.append(f"- {key}: {value}")

    return "\n".join(lines) if lines else "(Aucun changement)"


def get_frontmatter_stats(frontmatter: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcule des statistiques sur un frontmatter.

    Args:
        frontmatter: Dictionnaire de frontmatter

    Returns:
        Dict[str, Any]: Statistiques
            {
                "field_count": int,
                "has_ai_metadata": bool,
                "tag_count": int,
                "ai_tag_count": int
            }

    Examples:
        >>> stats = get_frontmatter_stats({"title": "Test", "tags": ["a", "AI-Category-b"]})
        >>> stats["tag_count"]
        2
        >>> stats["ai_tag_count"]
        1
    """
    tags = normalize_tags(frontmatter.get("tags", []))
    ai_tags = extract_ai_tags(tags)

    return {
        "field_count": len(frontmatter),
        "has_ai_metadata": has_ai_metadata(frontmatter),
        "tag_count": len(tags),
        "ai_tag_count": len(ai_tags)
    }


def sanitize_frontmatter_value(value: Any) -> Any:
    """
    Nettoie une valeur de frontmatter pour sérialisation YAML.

    Gère:
    - Conversion de types non supportés
    - Nettoyage de strings (trim, etc.)
    - Validation de listes et dicts

    Args:
        value: Valeur à nettoyer

    Returns:
        Any: Valeur nettoyée et safe pour YAML

    Examples:
        >>> sanitize_frontmatter_value("  test  ")
        'test'
        >>> sanitize_frontmatter_value(["  a  ", "  b  "])
        ['a', 'b']
    """
    if value is None:
        return None

    # String: trim
    if isinstance(value, str):
        return value.strip()

    # List: sanitize chaque élément
    if isinstance(value, list):
        return [sanitize_frontmatter_value(item) for item in value]

    # Dict: sanitize chaque valeur
    if isinstance(value, dict):
        return {k: sanitize_frontmatter_value(v) for k, v in value.items()}

    # Autres types: retourner tel quel
    return value
