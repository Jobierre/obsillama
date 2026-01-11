"""
ObsIllama - Point d'entrée principal du CLI.

Ce module permet d'exécuter ObsIllama avec : python -m obsillama
"""

from obsillama.cli.commands import cli


def main():
    """Point d'entrée principal de l'application."""
    cli(auto_envvar_prefix="OBSILLAMA")


if __name__ == "__main__":
    main()
