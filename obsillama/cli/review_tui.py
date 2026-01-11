"""
ObsIllama - Review TUI (Text User Interface)

Interface interactive pour réviser les catégories avec Textual.
"""

import logging
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    DataTable,
    Static,
    Button,
    Input,
    TextArea,
    Label,
    Select,
    ListView,
    ListItem,
)
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual import events

from obsillama.models.category import Category, ReviewStatus
from obsillama.storage.category_store import CategoryStore

logger = logging.getLogger(__name__)


# =============================================================================
# Main Review App
# =============================================================================

class ReviewApp(App):
    """
    Application Textual pour la révision des catégories.
    """

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        height: 100%;
    }

    #categories-panel {
        width: 60%;
        border: solid $primary;
        margin: 1;
    }

    #details-panel {
        width: 40%;
        border: solid $accent;
        margin: 1;
    }

    .category-row {
        padding: 0 1;
    }

    .status-pending {
        color: $warning;
    }

    .status-approved {
        color: $success;
    }

    .status-rejected {
        color: $error;
    }

    .status-modified {
        color: $accent;
    }

    #stats-box {
        background: $boost;
        padding: 1;
        margin: 1;
        border: solid $primary;
    }

    .detail-label {
        color: $text-muted;
        margin-top: 1;
    }

    .detail-value {
        background: $panel;
        padding: 1;
        margin-bottom: 1;
    }

    #button-bar {
        height: 3;
        background: $panel;
        padding: 0 1;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quitter", priority=True),
        Binding("s", "save", "Sauvegarder", priority=True),
        Binding("a", "approve", "Approuver (A)"),
        Binding("r", "reject", "Rejeter (R)"),
        Binding("e", "edit", "Éditer (E)"),
        Binding("m", "merge", "Fusionner (M)"),
        Binding("n", "notes", "Voir Notes (N)"),
        Binding("f", "filter", "Filtrer (F)"),
    ]

    def __init__(self, categories: List[Category], store: CategoryStore):
        super().__init__()
        self.categories = categories
        self.store = store
        self.selected_category: Optional[Category] = None
        self.filter_status: Optional[str] = None
        self.modified = False

    def compose(self) -> ComposeResult:
        """Compose l'interface."""
        yield Header()

        with Container(id="main-container"):
            with Horizontal():
                # Panel gauche : Liste des catégories
                with Vertical(id="categories-panel"):
                    yield Static("📋 Catégories", classes="panel-title")
                    yield Static(self._get_stats_text(), id="stats-box")
                    yield DataTable(id="categories-table")

                # Panel droit : Détails de la catégorie
                with Vertical(id="details-panel"):
                    yield Static("📝 Détails", classes="panel-title")
                    yield ScrollableContainer(id="details-content")

            # Barre de boutons
            with Horizontal(id="button-bar"):
                yield Button("Approuver [A]", id="btn-approve", variant="success")
                yield Button("Rejeter [R]", id="btn-reject", variant="error")
                yield Button("Éditer [E]", id="btn-edit", variant="primary")
                yield Button("Fusionner [M]", id="btn-merge", variant="warning")
                yield Button("Sauvegarder [S]", id="btn-save", variant="primary")

        yield Footer()

    def on_mount(self) -> None:
        """Initialise l'interface au montage."""
        self._populate_table()
        self._update_details()

    def _get_stats_text(self) -> str:
        """Génère le texte des statistiques."""
        total = len(self.categories)
        approved = len([c for c in self.categories if c.is_approved()])
        pending = len([c for c in self.categories if c.needs_review()])
        rejected = len([c for c in self.categories if c.review_status == ReviewStatus.REJECTED])

        return (
            f"Total: {total} | "
            f"[green]Approuvées: {approved}[/green] | "
            f"[yellow]En attente: {pending}[/yellow] | "
            f"[red]Rejetées: {rejected}[/red]"
        )

    def _populate_table(self) -> None:
        """Remplit le tableau des catégories."""
        table = self.query_one("#categories-table", DataTable)
        table.clear(columns=True)

        # Colonnes
        table.add_columns("ID", "Nom", "Notes", "Confiance", "Statut")

        # Filtrer si nécessaire
        categories_to_show = self.categories
        if self.filter_status:
            categories_to_show = [
                c for c in self.categories
                if c.review_status.value == self.filter_status
            ]

        # Lignes
        for cat in categories_to_show:
            status_class = f"status-{cat.review_status.value}"

            # Formater le statut avec emoji
            status_emoji = {
                "pending": "⏳",
                "approved": "✅",
                "rejected": "❌",
                "modified": "✏️",
            }
            status_text = f"{status_emoji.get(cat.review_status.value, '•')} {cat.review_status.value}"

            table.add_row(
                cat.id[:12],
                cat.name,
                str(cat.note_count),
                f"{cat.avg_confidence:.2f}",
                status_text,
                key=cat.id,
            )

        # Sélectionner la première ligne
        if table.row_count > 0:
            table.move_cursor(row=0)

    def _update_details(self, category: Optional[Category] = None) -> None:
        """Met à jour le panel de détails."""
        if category is None and self.selected_category is None:
            return

        if category:
            self.selected_category = category

        cat = self.selected_category
        if not cat:
            return

        # Générer le contenu HTML
        details_html = f"""
[bold]ID:[/bold] {cat.id}

[bold]Nom:[/bold]
{cat.name}

[bold]Description:[/bold]
{cat.description or '(aucune description)'}

[bold]Tag:[/bold]
{cat.tag_name}

[bold]Hiérarchie:[/bold]
• Niveau: {cat.level}
• Parent: {cat.parent_id or '(racine)'}
• Enfants: {len(cat.children_ids)}

[bold]Métadonnées sémantiques:[/bold]
• Keywords: {', '.join(cat.keywords[:5]) if cat.keywords else '(aucun)'}
• Terms: {', '.join(cat.representative_terms[:5]) if cat.representative_terms else '(aucun)'}

[bold]Statistiques:[/bold]
• Notes assignées: {cat.note_count}
• Confiance moy: {cat.avg_confidence:.2%}
• Cohérence: {cat.coherence_score:.2%}
• Distinctivité: {cat.distinctiveness_score:.2%}

[bold]Review:[/bold]
• Statut: {cat.review_status.value}
• Reviewé par: {cat.reviewed_by or '(non reviewé)'}
• Date: {cat.reviewed_at.strftime('%Y-%m-%d %H:%M') if cat.reviewed_at else '(non reviewé)'}

[bold]Suggestions:[/bold]
• Fusions suggérées: {len(cat.merge_suggestions)}
• Division suggérée: {'Oui' if cat.split_suggested else 'Non'}

[bold]Métadonnées:[/bold]
• Créé le: {cat.created_at.strftime('%Y-%m-%d %H:%M')}
• Créé par: {cat.created_by}
• Version: {cat.version}
        """

        # Mettre à jour le contenu
        container = self.query_one("#details-content", ScrollableContainer)
        container.remove_children()
        container.mount(Static(details_html.strip(), classes="detail-value"))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Gère la sélection d'une ligne dans le tableau."""
        # Récupérer la catégorie correspondante
        category_id = event.row_key
        category = next((c for c in self.categories if c.id == category_id), None)

        if category:
            self._update_details(category)

    # =========================================================================
    # Actions
    # =========================================================================

    def action_approve(self) -> None:
        """Approuve la catégorie sélectionnée."""
        if not self.selected_category:
            self.notify("Aucune catégorie sélectionnée", severity="warning")
            return

        self.selected_category.approve(reviewer="user")
        self.modified = True
        self._populate_table()
        self._update_details()
        self.notify(f"✅ {self.selected_category.name} approuvée", severity="information")

    def action_reject(self) -> None:
        """Rejette la catégorie sélectionnée."""
        if not self.selected_category:
            self.notify("Aucune catégorie sélectionnée", severity="warning")
            return

        self.selected_category.reject(reviewer="user")
        self.modified = True
        self._populate_table()
        self._update_details()
        self.notify(f"❌ {self.selected_category.name} rejetée", severity="information")

    def action_edit(self) -> None:
        """Ouvre la fenêtre d'édition."""
        if not self.selected_category:
            self.notify("Aucune catégorie sélectionnée", severity="warning")
            return

        # TODO: Implémenter l'écran d'édition
        self.notify("Édition : Bientôt disponible", severity="information")

    def action_merge(self) -> None:
        """Ouvre la fenêtre de fusion."""
        if not self.selected_category:
            self.notify("Aucune catégorie sélectionnée", severity="warning")
            return

        # TODO: Implémenter l'écran de fusion
        self.notify("Fusion : Bientôt disponible", severity="information")

    def action_notes(self) -> None:
        """Affiche les notes assignées à la catégorie."""
        if not self.selected_category:
            self.notify("Aucune catégorie sélectionnée", severity="warning")
            return

        # Charger les assignations
        notes = self.store.get_notes_for_category(self.selected_category.id)

        if not notes:
            self.notify("Aucune note assignée", severity="information")
            return

        # TODO: Afficher dans une fenêtre modale
        self.notify(f"{len(notes)} notes assignées", severity="information")

    def action_filter(self) -> None:
        """Filtre les catégories par statut."""
        # TODO: Implémenter un sélecteur de filtre
        self.notify("Filtrage : Bientôt disponible", severity="information")

    def action_save(self) -> None:
        """Sauvegarde les modifications."""
        if not self.modified:
            self.notify("Aucune modification à sauvegarder", severity="information")
            return

        try:
            self.store.save_taxonomy(self.categories)
            self.modified = False
            self.notify("✅ Modifications sauvegardées", severity="information")
        except Exception as e:
            logger.error(f"Erreur sauvegarde : {e}")
            self.notify(f"❌ Erreur : {e}", severity="error")

    def action_quit(self) -> None:
        """Quitte l'application."""
        if self.modified:
            # TODO: Demander confirmation
            self.notify("⚠️  Modifications non sauvegardées", severity="warning")

        self.exit()


# =============================================================================
# Edit Screen (TODO)
# =============================================================================

class EditCategoryScreen(ModalScreen):
    """Écran modal pour éditer une catégorie."""

    def __init__(self, category: Category):
        super().__init__()
        self.category = category

    def compose(self) -> ComposeResult:
        """Compose l'interface d'édition."""
        with Container():
            yield Static(f"Édition : {self.category.name}")
            yield Input(placeholder="Nom", value=self.category.name)
            yield TextArea(self.category.description or "", language="markdown")
            yield Input(placeholder="Tag", value=self.category.tag_name)
            with Horizontal():
                yield Button("Sauvegarder", variant="success")
                yield Button("Annuler", variant="error")


# =============================================================================
# Merge Screen (TODO)
# =============================================================================

class MergeCategoriesScreen(ModalScreen):
    """Écran modal pour fusionner des catégories."""

    def __init__(self, category: Category, all_categories: List[Category]):
        super().__init__()
        self.category = category
        self.all_categories = all_categories

    def compose(self) -> ComposeResult:
        """Compose l'interface de fusion."""
        with Container():
            yield Static(f"Fusionner avec : {self.category.name}")
            # TODO: Liste de sélection multiple
            with Horizontal():
                yield Button("Fusionner", variant="success")
                yield Button("Annuler", variant="error")
