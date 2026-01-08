"""
ObsIllama - Système d'organisation intelligente de notes Obsidian avec GraphRAG et Ollama

Ce fichier setup.py est conservé pour la compatibilité avec les outils anciens.
La configuration principale se trouve dans pyproject.toml.
"""

from setuptools import setup, find_packages

# La configuration est maintenant dans pyproject.toml
# Ce fichier permet la compatibilité avec les outils plus anciens
# et l'installation en mode développement: pip install -e .

setup(
    name="obsillama",
    packages=find_packages(exclude=["tests", "docs"]),
)
