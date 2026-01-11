#!/usr/bin/env python3
"""
Script de test pour vérifier les helpers CLI Rich.
"""

import time
from obsillama.utils.progress import (
    print_success,
    print_error,
    print_warning,
    print_info,
    print_header,
    print_stats,
    print_summary,
    print_table,
    create_progress,
    track_progress,
    format_size,
    format_duration,
    format_percentage,
)


def test_messages():
    """Test les messages formatés"""
    print_header("Test des messages formatés")
    print_success("Opération réussie !")
    print_error("Une erreur est survenue")
    print_warning("Attention à cela")
    print_info("Information utile")
    print()


def test_stats():
    """Test l'affichage de statistiques"""
    print_header("Test des statistiques")
    print_stats(
        {
            "Total notes": "800",
            "Categories": "20",
            "Coverage": "95%",
            "Embeddings": "768",
        },
        title="Vault Statistics",
    )
    print()


def test_table():
    """Test l'affichage de tableaux"""
    print_header("Test des tableaux")
    print_table(
        title="Top Categories",
        columns=[
            {"name": "Category", "style": "cyan"},
            {"name": "Notes", "justify": "right", "style": "green"},
            {"name": "Confidence", "justify": "right", "style": "yellow"},
        ],
        rows=[
            ["Technology", "150", "0.95"],
            ["Personal", "80", "0.87"],
            ["Projects", "120", "0.92"],
        ],
    )
    print()


def test_summary():
    """Test l'affichage de résumés"""
    print_header("Test des résumés")
    print_summary(
        title="✓ Phase 4.1 Terminée",
        items=[
            "Point d'entrée __main__.py créé",
            "Groupe Click principal configuré",
            "Helpers Rich implémentés",
            "Logging avec RichHandler configuré",
        ],
        border_style="green",
    )
    print()


def test_progress():
    """Test les progress bars"""
    print_header("Test des progress bars")

    # Test 1: Simple progress
    print_info("Test 1: Simple progress tracking")
    items = list(range(50))
    for _ in track_progress(items, "Processing items"):
        time.sleep(0.02)
    print()

    # Test 2: Progress avec contexte
    print_info("Test 2: Progress avec contexte managé")
    with create_progress("Complex task") as progress:
        task1 = progress.add_task("[cyan]Scanning notes...", total=100)
        task2 = progress.add_task("[green]Generating embeddings...", total=80)

        for i in range(100):
            progress.update(task1, advance=1)
            if i % 2 == 0 and i < 80:
                progress.update(task2, advance=1)
            time.sleep(0.02)
    print()


def test_formatters():
    """Test les formatters"""
    print_header("Test des formatters")
    print(f"Size: {format_size(1536789)}")
    print(f"Duration: {format_duration(3725)}")
    print(f"Percentage: {format_percentage(0.8765)}")
    print()


if __name__ == "__main__":
    print_header("🦙 ObsIllama - Test des helpers CLI")

    test_messages()
    test_stats()
    test_table()
    test_summary()
    test_formatters()
    test_progress()

    print_header("✓ Tous les tests terminés")
