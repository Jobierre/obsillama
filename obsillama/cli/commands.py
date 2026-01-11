"""
ObsIllama - CLI Commands

Ce module définit le groupe Click principal et configure le contexte global
pour toutes les commandes CLI.
"""

import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler

from obsillama.config.settings import Settings, get_settings


# ============================================================================
# Contexte CLI global
# ============================================================================


class ObsillamaContext:
    """
    Contexte partagé entre toutes les commandes CLI.

    Attributes:
        config: Configuration de l'application
        console: Console Rich pour l'affichage formaté
        verbose: Mode verbeux activé ou non
    """

    def __init__(self):
        self.config: Optional[Settings] = None
        self.console: Console = Console()
        self.verbose: bool = False
        self.logger: Optional[logging.Logger] = None


# Decorator pour passer le contexte ObsillamaContext aux commandes
pass_context = click.make_pass_decorator(ObsillamaContext)


# ============================================================================
# Configuration du logging
# ============================================================================


def setup_logging(logging_config, verbose: bool = False) -> logging.Logger:
    """
    Configure le système de logging avec Rich.

    Args:
        logging_config: Configuration du logging depuis Settings
        verbose: Si True, force le niveau DEBUG

    Returns:
        Logger configuré
    """
    # Déterminer le niveau de log
    log_level = "DEBUG" if verbose else logging_config.level
    level = getattr(logging, log_level)

    # Créer le dossier de logs si nécessaire
    log_file = Path(logging_config.file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Configuration des handlers
    handlers = []

    # Handler console avec Rich (si activé)
    if logging_config.console:
        console_handler = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            show_path=verbose,  # Affiche le chemin seulement en mode verbose
            markup=True,
        )
        console_handler.setLevel(level)
        handlers.append(console_handler)

    # Handler fichier
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=logging_config.rotation.max_size_mb * 1024 * 1024,
        backupCount=logging_config.rotation.backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(logging_config.format)
    file_handler.setFormatter(file_formatter)
    handlers.append(file_handler)

    # Configuration du logger root
    logging.basicConfig(
        level=level,
        format=logging_config.format,
        handlers=handlers,
    )

    # Récupérer le logger ObsIllama
    logger = logging.getLogger("obsillama")
    logger.setLevel(level)

    # Réduire la verbosité des loggers tiers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("lancedb").setLevel(logging.WARNING)

    return logger


# ============================================================================
# Groupe Click principal
# ============================================================================


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    envvar="OBSILLAMA_CONFIG_PATH",
    help="Chemin vers le fichier config.yaml (défaut: config/config.yaml)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Mode verbeux (niveau DEBUG)",
)
@click.version_option(version="0.1.0", prog_name="ObsIllama")
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], verbose: bool):
    """
    🦙 ObsIllama - Organisation intelligente de notes Obsidian

    ObsIllama utilise GraphRAG et Ollama pour catégoriser automatiquement
    vos notes Obsidian en analysant leur contenu et leurs relations.

    \b
    Workflow typique :
      1. obsillama init         # Initialiser le projet
      2. obsillama scan         # Scanner le vault
      3. obsillama analyze      # Générer les catégories
      4. obsillama review       # Réviser les catégories
      5. obsillama embed        # Générer les embeddings
      6. obsillama apply        # Appliquer au vault

    \b
    Pour plus d'aide sur une commande :
      obsillama <commande> --help
    """
    # Créer le contexte ObsIllama
    ctx.obj = ObsillamaContext()
    ctx.obj.verbose = verbose

    # Charger la configuration
    try:
        if config:
            ctx.obj.config = get_settings(config)
            if verbose:
                ctx.obj.console.print(
                    f"[green]✓[/green] Configuration chargée depuis: {config}"
                )
        else:
            # Essayer de charger depuis le chemin par défaut
            default_config = Path("config/config.yaml")
            if default_config.exists():
                ctx.obj.config = get_settings(default_config)
                if verbose:
                    ctx.obj.console.print(
                        f"[green]✓[/green] Configuration chargée depuis: {default_config}"
                    )
            else:
                # Pas de config trouvée - certaines commandes (comme init) n'en ont pas besoin
                ctx.obj.config = None
                if verbose:
                    ctx.obj.console.print(
                        "[yellow]⚠[/yellow] Aucune configuration trouvée (normal pour 'init')"
                    )

    except Exception as e:
        ctx.obj.console.print(
            f"[red]✗[/red] Erreur de chargement de la configuration: {e}",
            style="bold red",
        )
        sys.exit(1)

    # Configurer le logging si on a une config
    if ctx.obj.config:
        try:
            ctx.obj.logger = setup_logging(ctx.obj.config.logging, verbose)
            if verbose:
                ctx.obj.console.print("[green]✓[/green] Logging configuré")
        except Exception as e:
            ctx.obj.console.print(
                f"[yellow]⚠[/yellow] Erreur de configuration du logging: {e}"
            )
            # Continuer sans logging configuré
            ctx.obj.logger = logging.getLogger("obsillama")


# ============================================================================
# Import des commandes
# ============================================================================

from obsillama.cli.init import init

# Enregistrer les commandes
cli.add_command(init)

# Les prochaines commandes seront ajoutées ici :
# from obsillama.cli.scan import scan
# from obsillama.cli.analyze import analyze
# etc.
# cli.add_command(scan)
# cli.add_command(analyze)
# etc.


if __name__ == "__main__":
    cli()
