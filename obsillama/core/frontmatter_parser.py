"""
ObsIllama - Frontmatter Parser

Ce module gère le parsing du frontmatter YAML dans les notes Obsidian.
Il extrait les métadonnées, le contenu, les tags, et les backlinks.
"""

import re
import logging
from typing import Dict, Any, Tuple, List, Optional

import frontmatter

# Configuration du logger
logger = logging.getLogger(__name__)


# ============================================================================
# Fonctions de parsing du frontmatter
# ============================================================================


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse le frontmatter YAML d'une note Obsidian.

    Cette fonction extrait les métadonnées YAML du frontmatter et le contenu
    markdown sans le frontmatter. Elle gère les cas où le frontmatter est
    absent ou malformé.

    Args:
        content: Le contenu brut de la note (avec frontmatter éventuel)

    Returns:
        Tuple[Dict, str]: (métadonnées du frontmatter, contenu sans frontmatter)

    Examples:
        >>> metadata, content = parse_frontmatter("---\\ntitle: Test\\n---\\nContenu")
        >>> metadata
        {'title': 'Test'}
        >>> content
        'Contenu'
    """
    if not content or not content.strip():
        logger.debug("Contenu vide, retour de valeurs par défaut")
        return {}, ""

    try:
        # Vérifier si le frontmatter existe
        if not frontmatter.checks(content):
            logger.debug("Pas de frontmatter détecté")
            return {}, content.strip()

        # Parser le frontmatter
        post = frontmatter.loads(content)

        metadata = dict(post.metadata) if post.metadata else {}
        clean_content = post.content.strip()

        logger.debug(
            f"Frontmatter parsé: {len(metadata)} champs, "
            f"contenu: {len(clean_content)} caractères"
        )

        return metadata, clean_content

    except Exception as e:
        logger.warning(
            f"Erreur lors du parsing du frontmatter: {e}. "
            f"Retour du contenu brut sans frontmatter."
        )
        # En cas d'erreur, retourner le contenu tel quel
        return {}, content.strip()


def extract_tags_from_frontmatter(frontmatter_dict: Dict[str, Any]) -> List[str]:
    """
    Extrait les tags du frontmatter.

    Les tags peuvent être dans plusieurs formats:
    - tags: ["tag1", "tag2"]
    - tags: "tag1, tag2"
    - tag: "single-tag"

    Args:
        frontmatter_dict: Le dictionnaire du frontmatter

    Returns:
        List[str]: Liste des tags extraits (normalisés)

    Examples:
        >>> extract_tags_from_frontmatter({"tags": ["tech", "ai"]})
        ['tech', 'ai']
        >>> extract_tags_from_frontmatter({"tags": "tech, ai"})
        ['tech', 'ai']
    """
    tags = []

    # Chercher dans "tags" (pluriel)
    if "tags" in frontmatter_dict:
        tags_value = frontmatter_dict["tags"]

        if isinstance(tags_value, list):
            tags.extend(tags_value)
        elif isinstance(tags_value, str):
            # Séparer par virgule ou espace
            tags.extend([t.strip() for t in tags_value.replace(",", " ").split()])

    # Chercher dans "tag" (singulier)
    if "tag" in frontmatter_dict:
        tag_value = frontmatter_dict["tag"]

        if isinstance(tag_value, str):
            tags.append(tag_value.strip())
        elif isinstance(tag_value, list):
            tags.extend(tag_value)

    # Normaliser les tags (lowercase, sans #)
    normalized_tags = [tag.lower().strip().lstrip("#") for tag in tags if tag]

    # Dédupliquer
    return list(set(normalized_tags))


def extract_inline_tags(content: str) -> List[str]:
    """
    Extrait les tags inline (#tag) du contenu markdown.

    Les tags inline sont des mots précédés de # dans le contenu.
    Ne pas confondre avec les headings (# Titre avec espace).

    Args:
        content: Le contenu markdown

    Returns:
        List[str]: Liste des tags inline extraits (sans #)

    Examples:
        >>> extract_inline_tags("Ceci est un #test avec #python")
        ['test', 'python']
        >>> extract_inline_tags("# Titre\\n\\nContenu avec #tag")
        ['tag']
    """
    if not content:
        return []

    # Pattern pour les tags inline: #mot (sans espace après le #)
    # Exclure les headings qui ont un espace ou une nouvelle ligne après #
    # Un tag est: # suivi directement de lettres/chiffres (pas d'espace)
    pattern = r"#([\w\-]+)"

    # Trouver tous les matches potentiels
    all_matches = re.findall(pattern, content)

    # Filtrer les headings (lignes qui commencent par #+ suivi d'espace)
    # On vérifie dans le contenu original si c'est un heading
    heading_pattern = r"^#{1,6}\s+(.+)$"
    heading_texts = re.findall(heading_pattern, content, re.MULTILINE)

    # Extraire les mots des headings pour les exclure
    heading_words = set()
    for heading_text in heading_texts:
        # Prendre le premier mot du heading (souvent c'est ce qui pourrait matcher)
        first_word = heading_text.split()[0] if heading_text.split() else ""
        if first_word:
            heading_words.add(first_word.lower())

    # Filtrer les matches qui ne sont pas des headings
    matches = [m for m in all_matches if m.lower() not in heading_words]

    # Normaliser et dédupliquer
    tags = [tag.lower().strip() for tag in matches if tag]
    return list(set(tags))


def extract_backlinks(content: str) -> List[str]:
    """
    Extrait les backlinks ([[note]]) du contenu markdown.

    Les backlinks sont les liens internes Obsidian au format [[note]].
    Supporte aussi les alias [[note|alias]].

    Args:
        content: Le contenu markdown

    Returns:
        List[str]: Liste des noms de notes liées (sans [[]])

    Examples:
        >>> extract_backlinks("Voir [[Note 1]] et [[Note 2|alias]]")
        ['Note 1', 'Note 2']
    """
    if not content:
        return []

    # Pattern pour les backlinks: [[...]]
    # Supporte les alias: [[note|alias]] -> extraire "note"
    pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"

    matches = re.findall(pattern, content)

    # Nettoyer et dédupliquer
    backlinks = [link.strip() for link in matches if link.strip()]
    return list(set(backlinks))


def extract_external_links(content: str) -> List[str]:
    """
    Extrait les liens externes (URLs) du contenu markdown.

    Détecte les URLs http/https dans le contenu.

    Args:
        content: Le contenu markdown

    Returns:
        List[str]: Liste des URLs trouvées

    Examples:
        >>> extract_external_links("Voir https://example.com")
        ['https://example.com']
    """
    if not content:
        return []

    # Pattern pour les URLs
    pattern = r"https?://[^\s\)]+(?:\([^\)]*\))?[^\s\)]*"

    matches = re.findall(pattern, content)

    # Dédupliquer
    return list(set(matches))


def extract_title(
    frontmatter_dict: Dict[str, Any], content: str, fallback_filename: str
) -> str:
    """
    Extrait le titre de la note.

    Ordre de priorité:
    1. frontmatter["title"]
    2. Premier H1 (# Titre) dans le contenu
    3. Nom du fichier (sans extension)

    Args:
        frontmatter_dict: Le dictionnaire du frontmatter
        content: Le contenu markdown
        fallback_filename: Nom du fichier (sans extension) en fallback

    Returns:
        str: Le titre de la note

    Examples:
        >>> extract_title({"title": "Mon Titre"}, "# Autre", "fichier")
        'Mon Titre'
        >>> extract_title({}, "# Mon Titre", "fichier")
        'Mon Titre'
        >>> extract_title({}, "Contenu", "fichier")
        'fichier'
    """
    # 1. Depuis le frontmatter
    if "title" in frontmatter_dict and frontmatter_dict["title"]:
        return str(frontmatter_dict["title"]).strip()

    # 2. Depuis le premier H1
    if content:
        # Chercher le premier H1 (# Titre)
        h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()

    # 3. Fallback sur le nom du fichier
    return fallback_filename


def count_words(content: str) -> int:
    """
    Compte le nombre de mots dans le contenu.

    Args:
        content: Le contenu markdown

    Returns:
        int: Nombre de mots

    Examples:
        >>> count_words("Ceci est un test")
        4
    """
    if not content:
        return 0

    # Enlever les caractères markdown spéciaux
    clean_content = re.sub(r"[#\*\[\]\(\)]+", " ", content)

    # Compter les mots (séparés par des espaces)
    words = clean_content.split()
    return len(words)


def count_headings(content: str) -> int:
    """
    Compte le nombre de headings (# Titre) dans le contenu.

    Args:
        content: Le contenu markdown

    Returns:
        int: Nombre de headings

    Examples:
        >>> count_headings("# H1\\n## H2\\n### H3")
        3
    """
    if not content:
        return 0

    # Pattern pour les headings (# au début de ligne)
    pattern = r"^#+\s+.+$"
    matches = re.findall(pattern, content, re.MULTILINE)
    return len(matches)


def is_daily_note(filename: str, frontmatter_dict: Dict[str, Any]) -> bool:
    """
    Détecte si la note est une daily note.

    Une daily note est détectée par:
    - Un nom de fichier au format date (YYYY-MM-DD, DD-MM-YYYY, etc.)
    - Un tag "daily-note" ou "journal" dans le frontmatter

    Args:
        filename: Nom du fichier (sans extension)
        frontmatter_dict: Le dictionnaire du frontmatter

    Returns:
        bool: True si c'est une daily note

    Examples:
        >>> is_daily_note("2026-01-09", {})
        True
        >>> is_daily_note("Note", {"tags": ["daily-note"]})
        True
        >>> is_daily_note("Regular Note", {})
        False
    """
    # Vérifier le format date dans le nom
    date_patterns = [
        r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
        r"^\d{2}-\d{2}-\d{4}$",  # DD-MM-YYYY
        r"^\d{4}\d{2}\d{2}$",  # YYYYMMDD
    ]

    for pattern in date_patterns:
        if re.match(pattern, filename):
            return True

    # Vérifier les tags dans le frontmatter
    tags = extract_tags_from_frontmatter(frontmatter_dict)
    daily_keywords = ["daily-note", "daily", "journal", "dailynote"]

    for tag in tags:
        if tag.lower() in daily_keywords:
            return True

    return False


# ============================================================================
# Fonction principale de parsing
# ============================================================================


def parse_note_content(content: str, filename: str) -> Dict[str, Any]:
    """
    Parse complètement le contenu d'une note Obsidian.

    Cette fonction combine toutes les autres fonctions de parsing pour extraire:
    - Frontmatter YAML
    - Titre
    - Tags (frontmatter + inline)
    - Backlinks et liens externes
    - Statistiques (word_count, etc.)

    Args:
        content: Le contenu brut de la note
        filename: Le nom du fichier (sans extension)

    Returns:
        Dict[str, Any]: Dictionnaire contenant toutes les données extraites

    Example:
        >>> result = parse_note_content("---\\ntitle: Test\\n---\\nContenu", "test")
        >>> result['title']
        'Test'
    """
    # Parser le frontmatter
    frontmatter_dict, clean_content = parse_frontmatter(content)

    # Extraire le titre
    title = extract_title(frontmatter_dict, clean_content, filename)

    # Extraire les tags
    frontmatter_tags = extract_tags_from_frontmatter(frontmatter_dict)
    inline_tags = extract_inline_tags(clean_content)
    all_tags = list(set(frontmatter_tags + inline_tags))

    # Extraire les liens
    backlinks = extract_backlinks(clean_content)
    external_links = extract_external_links(clean_content)

    # Calculer les statistiques
    word_count = count_words(clean_content)
    char_count = len(clean_content)
    heading_count = count_headings(clean_content)

    # Détecter daily note
    is_daily = is_daily_note(filename, frontmatter_dict)

    return {
        "title": title,
        "content": clean_content,
        "raw_content": content,
        "frontmatter": frontmatter_dict,
        "tags": all_tags,
        "frontmatter_tags": frontmatter_tags,
        "inline_tags": inline_tags,
        "backlinks": backlinks,
        "external_links": external_links,
        "word_count": word_count,
        "char_count": char_count,
        "heading_count": heading_count,
        "is_daily_note": is_daily,
    }
