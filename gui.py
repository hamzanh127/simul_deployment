"""
Interface Desktop Tkinter pour tester l'agent IA.

Ce fichier cree une application graphique autonome.

Important :
- ce fichier ne modifie pas l'API FastAPI ;
- ce fichier ne cree aucun endpoint ;
- ce fichier consomme uniquement les endpoints existants avec `requests` ;
- ce fichier peut etre lance directement avec :

    python gui.py

Objectif pedagogique :
Comprendre comment une interface Desktop peut servir d'outil de test pour une
API IA exposee avec FastAPI, LangGraph, LangChain et Groq.
"""

from __future__ import annotations

import json
import queue
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from tkinter import ttk
from typing import Any

import requests


# =============================================================================
# Donnees de configuration UI
# =============================================================================


@dataclass(frozen=True)
class ModeConfig:
    """
    Decrit un mode d'appel API.

    Pourquoi utiliser une dataclass ?
    - elle regroupe proprement les informations d'un mode ;
    - elle rend le code plus lisible ;
    - elle evite de disperser endpoint, titre et exemple dans plusieurs listes.
    """

    label: str
    endpoint: str
    example: dict[str, Any]
    help_text: str


class AppModes:
    """
    Centralise les modes disponibles dans l'application.

    Chaque mode correspond a un endpoint FastAPI deja existant.
    Le GUI ne cree pas ces endpoints : il les appelle seulement.
    """

    REALTIME = "Real-Time"
    BATCH = "Batch"
    EVENT = "Event-Driven"
    STREAMING = "Streaming"

    CONFIGS: dict[str, ModeConfig] = {
        REALTIME: ModeConfig(
            label=REALTIME,
            endpoint="/realtime",
            example={"text": "Le serveur PostgreSQL ne repond plus."},
            help_text="Un seul incident est envoye a l'API.",
        ),
        BATCH: ModeConfig(
            label=BATCH,
            endpoint="/batch",
            example={"items": ["CPU a 100%", "Erreur 500", "Redis indisponible"]},
            help_text="Plusieurs incidents sont envoyes en une seule requete.",
        ),
        EVENT: ModeConfig(
            label=EVENT,
            endpoint="/event",
            example={
                "event_type": "monitoring.alert",
                "severity": "critical",
                "service": "postgresql",
                "message": "Database Down",
            },
            help_text="Un evenement externe simule un webhook ou une alerte.",
        ),
        STREAMING: ModeConfig(
            label=STREAMING,
            endpoint="/streaming",
            example={"text": "Le deploiement Kubernetes echoue."},
            help_text="Le resultat est recu progressivement en streaming.",
        ),
    }


# =============================================================================
# Client API
# =============================================================================


class APIClient:
    """
    Responsable de toute la communication HTTP avec FastAPI.

    Cette classe isole `requests` du reste de l'interface.
    Ainsi, les widgets Tkinter ne connaissent pas les details HTTP.
    """

    def __init__(self, base_url: str, timeout: int = 60) -> None:
        """
        Initialise le client API.

        Args:
            base_url:
                URL racine de l'API FastAPI.
                Exemple : http://127.0.0.1:8001

            timeout:
                Timeout en secondes pour chaque requete HTTP.
        """

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def update_base_url(self, base_url: str) -> None:
        """
        Met a jour l'URL de l'API.

        L'utilisateur peut modifier l'URL dans l'interface.
        Cette methode evite de recreer tout l'objet APIClient.
        """

        self.base_url = base_url.rstrip("/")

    def check_health(self) -> tuple[bool, str]:
        """
        Teste si l'API est joignable.

        Le GUI appelle cette methode toutes les 5 secondes.
        Elle envoie un GET /, car cet endpoint existe deja dans l'API.
        """

        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            return response.ok, f"HTTP {response.status_code}"
        except requests.RequestException as exc:
            return False, str(exc)

    def post_json(self, endpoint: str, payload: dict[str, Any]) -> tuple[int, float, Any]:
        """
        Envoie une requete POST JSON a l'API.

        Args:
            endpoint:
                Chemin de l'endpoint, par exemple `/realtime`.

            payload:
                Corps JSON envoye a FastAPI.

        Returns:
            Tuple contenant :
            - status HTTP ;
            - temps de reponse en secondes ;
            - JSON de reponse si possible, sinon texte brut.
        """

        url = f"{self.base_url}{endpoint}"
        start = time.perf_counter()
        response = requests.post(url, json=payload, timeout=self.timeout)
        elapsed = time.perf_counter() - start

        try:
            data: Any = response.json()
        except ValueError:
            data = response.text

        return response.status_code, elapsed, data

    def post_stream(self, endpoint: str, payload: dict[str, Any]) -> tuple[int, float, list[Any]]:
        """
        Envoie une requete POST en mode streaming.

        L'endpoint `/streaming` retourne des lignes JSON successives.
        `requests.post(..., stream=True)` permet de lire ces lignes au fur et a
        mesure avec `iter_lines()`.
        """

        url = f"{self.base_url}{endpoint}"
        start = time.perf_counter()
        events: list[Any] = []

        with requests.post(
            url,
            json=payload,
            timeout=self.timeout,
            stream=True,
        ) as response:
            status_code = response.status_code

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    events.append({"raw": line})

        elapsed = time.perf_counter() - start
        return status_code, elapsed, events


# =============================================================================
# Adaptation des payloads
# =============================================================================


class PayloadBuilder:
    """
    Transforme le contenu de la zone de saisie en payload API.

    Le GUI propose des exemples simples, par exemple :

        {"text": "Le serveur PostgreSQL ne repond plus."}

    Si l'API attend un schema plus structure, cette classe adapte le payload sans
    modifier l'API FastAPI.
    """

    @staticmethod
    def parse_text(raw_text: str) -> dict[str, Any]:
        """
        Convertit le texte saisi par l'utilisateur en dictionnaire Python.

        La zone centrale contient du JSON.
        Cette methode verifie que le JSON est valide avant d'appeler l'API.
        """

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON invalide : {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError("Le contenu doit etre un objet JSON.")

        return data

    @staticmethod
    def build(mode: str, raw_payload: dict[str, Any]) -> dict[str, Any]:
        """
        Construit le payload final envoye a l'API.

        Cette methode garde le GUI pratique pour la demo :
        - l'utilisateur peut saisir `{"text": "..."}`
        - le GUI peut convertir cela vers le schema attendu par l'API.
        """

        if mode in (AppModes.REALTIME, AppModes.STREAMING):
            return PayloadBuilder._single_incident_payload(raw_payload, source="gui")

        if mode == AppModes.BATCH:
            return PayloadBuilder._batch_payload(raw_payload)

        if mode == AppModes.EVENT:
            return raw_payload

        return raw_payload

    @staticmethod
    def _single_incident_payload(raw_payload: dict[str, Any], source: str) -> dict[str, str]:
        """
        Adapte un incident simple vers le schema `IncidentRequest`.

        Si l'utilisateur saisit deja `title`, `description`, `severity`,
        `source`, on conserve ces valeurs.

        Si l'utilisateur saisit seulement `text`, on construit un incident
        structure.
        """

        if {"title", "description", "severity", "source"}.issubset(raw_payload):
            return {
                "title": str(raw_payload["title"]),
                "description": str(raw_payload["description"]),
                "severity": str(raw_payload["severity"]),
                "source": str(raw_payload["source"]),
            }

        text = str(raw_payload.get("text", raw_payload))
        return {
            "title": text[:80],
            "description": text,
            "severity": str(raw_payload.get("severity", "unknown")),
            "source": str(raw_payload.get("source", source)),
        }

    @staticmethod
    def _batch_payload(raw_payload: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
        """
        Adapte le mode batch.

        L'exemple demande :

            {"items": ["CPU a 100%", "Erreur 500"]}

        L'API peut attendre une liste d'incidents structures.
        Cette methode transforme chaque ligne/chaine en objet incident.
        """

        items = raw_payload.get("items", [])

        if not isinstance(items, list):
            raise ValueError("Le champ `items` doit etre une liste.")

        normalized_items: list[dict[str, str]] = []
        for item in items:
            if isinstance(item, dict):
                normalized_items.append(
                    PayloadBuilder._single_incident_payload(item, source="gui-batch")
                )
            else:
                text = str(item)
                normalized_items.append(
                    {
                        "title": text[:80],
                        "description": text,
                        "severity": "unknown",
                        "source": "gui-batch",
                    }
                )

        return {"items": normalized_items}


# =============================================================================
# Widgets specialises
# =============================================================================


class JsonText(ttk.Frame):
    """
    Widget compose d'un Text Tkinter avec scrollbar.

    Tkinter ne fournit pas directement une zone JSON coloree.
    Cette classe ajoute une coloration simple avec des tags.
    """

    def __init__(self, parent: tk.Widget, readonly: bool = False) -> None:
        """
        Cree une zone de texte JSON.

        Args:
            parent:
                Widget parent.

            readonly:
                Si True, l'utilisateur ne peut pas modifier le texte.
        """

        super().__init__(parent)
        self.readonly = readonly

        # Text est le widget Tkinter standard pour du texte multi-ligne.
        self.text = tk.Text(
            self,
            wrap="word",
            undo=True,
            font=("Consolas", 10),
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#d0d7de",
        )

        # Scrollbar verticale pour naviguer dans les longs JSON.
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)

        self.text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._configure_tags()
        if self.readonly:
            self.text.configure(state="disabled")

    def _configure_tags(self) -> None:
        """
        Configure les couleurs utilisees pour la coloration JSON.

        Les tags sont appliques ensuite par `highlight_json()`.
        """

        self.text.tag_configure("json_key", foreground="#0b5cad")
        self.text.tag_configure("json_string", foreground="#116329")
        self.text.tag_configure("json_number", foreground="#953800")
        self.text.tag_configure("json_bool", foreground="#8250df")
        self.text.tag_configure("json_null", foreground="#6e7781")

    def set_text(self, value: str) -> None:
        """
        Remplace tout le contenu de la zone.

        Si la zone est readonly, on l'active temporairement pour modifier son
        contenu, puis on la remet en lecture seule.
        """

        if self.readonly:
            self.text.configure(state="normal")

        self.text.delete("1.0", "end")
        self.text.insert("1.0", value)
        self.highlight_json()

        if self.readonly:
            self.text.configure(state="disabled")

    def get_text(self) -> str:
        """
        Retourne le texte actuellement saisi.
        """

        return self.text.get("1.0", "end").strip()

    def clear(self) -> None:
        """
        Efface le contenu.
        """

        self.set_text("")

    def highlight_json(self) -> None:
        """
        Applique une coloration JSON simple.

        Ce n'est pas un parseur complet, mais cela suffit pour distinguer :
        - cles ;
        - chaines ;
        - nombres ;
        - booleens ;
        - null.
        """

        if self.readonly:
            self.text.configure(state="normal")

        for tag in ("json_key", "json_string", "json_number", "json_bool", "json_null"):
            self.text.tag_remove(tag, "1.0", "end")

        content = self.text.get("1.0", "end-1c")
        self._highlight_strings(content)
        self._highlight_literals(content)

        if self.readonly:
            self.text.configure(state="disabled")

    def _highlight_strings(self, content: str) -> None:
        """
        Colore les chaines JSON.

        Une chaine suivie par `:` est consideree comme une cle.
        """

        index = 0
        while index < len(content):
            if content[index] != '"':
                index += 1
                continue

            start = index
            index += 1
            escaped = False

            while index < len(content):
                char = content[index]
                if char == "\\" and not escaped:
                    escaped = True
                    index += 1
                    continue
                if char == '"' and not escaped:
                    break
                escaped = False
                index += 1

            end = min(index + 1, len(content))
            after = content[end:].lstrip()
            tag = "json_key" if after.startswith(":") else "json_string"

            self.text.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")
            index = end

    def _highlight_literals(self, content: str) -> None:
        """
        Colore quelques litteraux JSON simples.
        """

        for literal, tag in (
            ("true", "json_bool"),
            ("false", "json_bool"),
            ("null", "json_null"),
        ):
            start = "1.0"
            while True:
                pos = self.text.search(literal, start, stopindex="end")
                if not pos:
                    break
                end = f"{pos}+{len(literal)}c"
                self.text.tag_add(tag, pos, end)
                start = end


class HistoryPanel(ttk.Frame):
    """
    Panneau historique des appels API.

    Il conserve les 20 derniers appels avec :
    - date ;
    - endpoint ;
    - temps ;
    - succes.
    """

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)

        columns = ("date", "endpoint", "time", "success")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=6)

        self.tree.heading("date", text="Date")
        self.tree.heading("endpoint", text="Endpoint")
        self.tree.heading("time", text="Temps")
        self.tree.heading("success", text="Succes")

        self.tree.column("date", width=180, anchor="w")
        self.tree.column("endpoint", width=160, anchor="w")
        self.tree.column("time", width=100, anchor="center")
        self.tree.column("success", width=100, anchor="center")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def add_entry(self, endpoint: str, elapsed: float, success: bool) -> None:
        """
        Ajoute un appel dans l'historique.

        Si plus de 20 appels sont presents, le plus ancien est supprime.
        """

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.tree.insert(
            "",
            "end",
            values=(now, endpoint, f"{elapsed:.2f}s", "Oui" if success else "Non"),
        )

        children = self.tree.get_children()
        while len(children) > 20:
            self.tree.delete(children[0])
            children = self.tree.get_children()


class LogsPanel(ttk.Frame):
    """
    Panneau de logs.

    Il affiche les evenements importants :
    - connexion API ;
    - erreurs ;
    - reponses ;
    - temps de reponse.
    """

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)

        self.text = tk.Text(
            self,
            wrap="word",
            height=6,
            font=("Consolas", 9),
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#d0d7de",
        )
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set, state="disabled")

        self.text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def log(self, message: str) -> None:
        """
        Ajoute une ligne de log horodatee.
        """

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.text.configure(state="normal")
        self.text.insert("end", f"[{timestamp}] {message}\n")
        self.text.see("end")
        self.text.configure(state="disabled")


class StatusBar(ttk.Frame):
    """
    Barre de statut en bas de l'application.

    Elle affiche l'etat de connexion a l'API.
    """

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)

        self.status_var = tk.StringVar(value="API Deconnectee")
        self.label = ttk.Label(self, textvariable=self.status_var, anchor="w")
        self.label.pack(side="left", fill="x", expand=True, padx=8, pady=4)

    def set_connected(self, detail: str) -> None:
        """
        Affiche que l'API est connectee.
        """

        self.status_var.set(f"API Connectee - {detail}")

    def set_disconnected(self, detail: str) -> None:
        """
        Affiche que l'API est deconnectee.
        """

        self.status_var.set(f"API Deconnectee - {detail}")


# =============================================================================
# Application principale
# =============================================================================


class AgentTesterApp(tk.Tk):
    """
    Fenetre principale de l'application Tkinter.

    Cette classe orchestre :
    - les widgets ;
    - les appels API ;
    - l'historique ;
    - les logs ;
    - la surveillance automatique de l'API.
    """

    def __init__(self) -> None:
        """
        Cree la fenetre principale et initialise l'application.
        """

        super().__init__()

        self.title("AI Agent Desktop Tester")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        self.mode_var = tk.StringVar(value=AppModes.REALTIME)
        self.api_url_var = tk.StringVar(value="http://127.0.0.1:8001")
        self.http_status_var = tk.StringVar(value="Status HTTP : -")
        self.response_time_var = tk.StringVar(value="Temps : -")

        self.client = APIClient(self.api_url_var.get())
        self.worker_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

        self._configure_style()
        self._create_menu()
        self._create_layout()
        self._bind_events()

        self.load_example()
        self._poll_worker_queue()
        self._schedule_health_check()

    def _configure_style(self) -> None:
        """
        Configure le theme ttk.

        `ttk` fournit des widgets plus modernes que les widgets Tk classiques.
        Le theme `clam` est souvent plus propre et plus configurable.
        """

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f6f8fa")
        style.configure("Header.TFrame", background="#0f172a")
        style.configure("Header.TLabel", background="#0f172a", foreground="white")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("TButton", padding=6)
        style.configure("Accent.TButton", padding=6)
        style.configure("TLabelframe", background="#f6f8fa")
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))

    def _create_menu(self) -> None:
        """
        Cree la barre de menu.

        Une barre de menu donne un aspect professionnel et permet d'ajouter des
        actions globales comme quitter, effacer ou afficher des informations.
        """

        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Charger Exemple", command=self.load_example)
        file_menu.add_command(label="Sauvegarder Resultat", command=self.save_result)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.destroy)

        tools_menu = tk.Menu(menu_bar, tearoff=False)
        tools_menu.add_command(label="Visualiser Workflow", command=self.open_workflow_image)
        tools_menu.add_command(label="Tester Connexion API", command=self.check_health_once)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="A propos", command=self.show_about)

        menu_bar.add_cascade(label="Fichier", menu=file_menu)
        menu_bar.add_cascade(label="Outils", menu=tools_menu)
        menu_bar.add_cascade(label="Aide", menu=help_menu)

        self.config(menu=menu_bar)

    def _create_layout(self) -> None:
        """
        Cree toute la disposition graphique.

        La fenetre est organisee en trois zones principales :
        - en haut : titre et URL API ;
        - au centre : modes, saisie, resultats ;
        - en bas : historique, logs, barre de statut.
        """

        self._create_header()
        self._create_main_panes()
        self._create_bottom_panels()
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=3, column=0, sticky="ew")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)

    def _create_header(self) -> None:
        """
        Cree le bandeau superieur.

        Il contient :
        - un logo IA sous forme d'emoji ;
        - un titre ;
        - le champ URL de l'API.
        """

        header = ttk.Frame(self, style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        logo = ttk.Label(header, text="🤖", font=("Segoe UI Emoji", 28), style="Header.TLabel")
        logo.grid(row=0, column=0, rowspan=2, padx=(16, 8), pady=10)

        title = ttk.Label(
            header,
            text="AI Agent Desktop Tester",
            font=("Segoe UI", 18, "bold"),
            style="Header.TLabel",
        )
        title.grid(row=0, column=1, sticky="w", pady=(10, 0))

        subtitle = ttk.Label(
            header,
            text="Client Tkinter pour tester FastAPI, LangGraph, LangChain et Groq",
            style="Header.TLabel",
        )
        subtitle.grid(row=1, column=1, sticky="w", pady=(0, 10))

        url_frame = ttk.Frame(header, style="Header.TFrame")
        url_frame.grid(row=0, column=2, rowspan=2, sticky="e", padx=16)

        url_label = ttk.Label(url_frame, text="API URL", style="Header.TLabel")
        url_label.grid(row=0, column=0, sticky="w")

        self.url_entry = ttk.Entry(url_frame, textvariable=self.api_url_var, width=34)
        self.url_entry.grid(row=1, column=0, sticky="ew")

    def _create_main_panes(self) -> None:
        """
        Cree les trois panneaux principaux :
        - gauche : choix du mode et boutons ;
        - centre : saisie ;
        - droite : resultat JSON.
        """

        main = ttk.Panedwindow(self, orient="horizontal")
        main.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        left = ttk.Frame(main, padding=10)
        center = ttk.Frame(main, padding=10)
        right = ttk.Frame(main, padding=10)

        main.add(left, weight=1)
        main.add(center, weight=3)
        main.add(right, weight=3)

        self._create_left_panel(left)
        self._create_center_panel(center)
        self._create_right_panel(right)

    def _create_left_panel(self, parent: ttk.Frame) -> None:
        """
        Cree le panneau gauche.

        Il contient les radio buttons de mode et les boutons d'action.
        """

        mode_box = ttk.LabelFrame(parent, text="Mode de test", padding=10)
        mode_box.pack(fill="x")

        for mode in AppModes.CONFIGS:
            radio = ttk.Radiobutton(
                mode_box,
                text=mode,
                value=mode,
                variable=self.mode_var,
                command=self.on_mode_changed,
            )
            radio.pack(anchor="w", pady=4)

        self.mode_help = ttk.Label(parent, text="", wraplength=220, justify="left")
        self.mode_help.pack(fill="x", pady=(12, 8))

        actions = ttk.LabelFrame(parent, text="Actions", padding=10)
        actions.pack(fill="x", pady=(10, 0))

        ttk.Button(actions, text="Envoyer", command=self.send_request).pack(fill="x", pady=3)
        ttk.Button(actions, text="Effacer", command=self.clear_all).pack(fill="x", pady=3)
        ttk.Button(actions, text="Copier Resultat", command=self.copy_result).pack(fill="x", pady=3)
        ttk.Button(actions, text="Sauvegarder Resultat (.json)", command=self.save_result).pack(
            fill="x", pady=3
        )
        ttk.Button(actions, text="Charger Exemple", command=self.load_example).pack(fill="x", pady=3)
        ttk.Button(actions, text="Visualiser Workflow", command=self.open_workflow_image).pack(
            fill="x", pady=3
        )

    def _create_center_panel(self, parent: ttk.Frame) -> None:
        """
        Cree le panneau central.

        Il contient la zone de saisie JSON envoyee a l'API.
        """

        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        ttk.Label(parent, text="Zone de saisie", style="Title.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        self.input_text = JsonText(parent, readonly=False)
        self.input_text.grid(row=1, column=0, sticky="nsew")

    def _create_right_panel(self, parent: ttk.Frame) -> None:
        """
        Cree le panneau droit.

        Il contient le status HTTP, le temps de reponse et le JSON formate.
        """

        parent.rowconfigure(2, weight=1)
        parent.columnconfigure(0, weight=1)

        ttk.Label(parent, text="Resultat JSON", style="Title.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        meta = ttk.Frame(parent)
        meta.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        meta.columnconfigure(1, weight=1)

        ttk.Label(meta, textvariable=self.http_status_var).grid(row=0, column=0, sticky="w")
        ttk.Label(meta, textvariable=self.response_time_var).grid(row=0, column=1, sticky="e")

        self.result_text = JsonText(parent, readonly=True)
        self.result_text.grid(row=2, column=0, sticky="nsew")

    def _create_bottom_panels(self) -> None:
        """
        Cree les panneaux Historique et Logs.

        `ttk.Notebook` permet d'avoir plusieurs onglets dans un meme espace.
        """

        notebook = ttk.Notebook(self)
        notebook.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.history_panel = HistoryPanel(notebook)
        self.logs_panel = LogsPanel(notebook)

        notebook.add(self.history_panel, text="Historique")
        notebook.add(self.logs_panel, text="Logs")

    def _bind_events(self) -> None:
        """
        Connecte certains evenements UI aux methodes Python.
        """

        self.api_url_var.trace_add("write", self._on_api_url_changed)
        self.on_mode_changed()

    def _on_api_url_changed(self, *_: Any) -> None:
        """
        Met a jour le client API quand l'utilisateur change l'URL.
        """

        self.client.update_base_url(self.api_url_var.get())

    def on_mode_changed(self) -> None:
        """
        Met a jour le texte d'aide quand l'utilisateur change de mode.
        """

        config = AppModes.CONFIGS[self.mode_var.get()]
        self.mode_help.configure(text=f"{config.endpoint}\n{config.help_text}")

    def load_example(self) -> None:
        """
        Charge automatiquement l'exemple JSON du mode selectionne.
        """

        config = AppModes.CONFIGS[self.mode_var.get()]
        example = json.dumps(config.example, indent=2, ensure_ascii=False)
        self.input_text.set_text(example)
        self.logs_panel.log(f"Exemple charge pour {config.label}")

    def clear_all(self) -> None:
        """
        Efface la saisie, le resultat et les metadonnees de reponse.
        """

        self.input_text.clear()
        self.result_text.clear()
        self.http_status_var.set("Status HTTP : -")
        self.response_time_var.set("Temps : -")
        self.logs_panel.log("Interface effacee")

    def send_request(self) -> None:
        """
        Lance l'appel API correspondant au mode selectionne.

        L'appel reseau est fait dans un thread separe pour ne pas bloquer
        l'interface Tkinter.
        """

        mode = self.mode_var.get()
        config = AppModes.CONFIGS[mode]

        try:
            raw_payload = PayloadBuilder.parse_text(self.input_text.get_text())
            payload = PayloadBuilder.build(mode, raw_payload)
        except ValueError as exc:
            messagebox.showerror("Erreur JSON", str(exc))
            self.logs_panel.log(f"Erreur JSON : {exc}")
            return

        self.logs_panel.log(f"Envoi vers {config.endpoint}")
        self.http_status_var.set("Status HTTP : en cours...")
        self.response_time_var.set("Temps : en cours...")

        thread = threading.Thread(
            target=self._send_request_worker,
            args=(mode, config.endpoint, payload),
            daemon=True,
        )
        thread.start()

    def _send_request_worker(self, mode: str, endpoint: str, payload: dict[str, Any]) -> None:
        """
        Execute l'appel HTTP dans un thread secondaire.

        Tkinter doit rester pilote par le thread principal.
        Le worker place donc le resultat dans une queue, puis le thread principal
        met a jour l'interface.
        """

        try:
            if mode == AppModes.STREAMING:
                status_code, elapsed, data = self.client.post_stream(endpoint, payload)
            else:
                status_code, elapsed, data = self.client.post_json(endpoint, payload)

            self.worker_queue.put(("api_result", (endpoint, status_code, elapsed, data)))

        except requests.RequestException as exc:
            self.worker_queue.put(("api_error", (endpoint, str(exc))))
        except Exception as exc:  # noqa: BLE001 - affichage pedagogique dans le GUI
            self.worker_queue.put(("api_error", (endpoint, str(exc))))

    def _poll_worker_queue(self) -> None:
        """
        Lit regulierement les resultats produits par les threads.

        Cette methode est appelee par `after`, le mecanisme Tkinter pour planifier
        une action dans le futur.
        """

        try:
            while True:
                event_type, payload = self.worker_queue.get_nowait()

                if event_type == "api_result":
                    self._handle_api_result(*payload)
                elif event_type == "api_error":
                    self._handle_api_error(*payload)
                elif event_type == "health":
                    self._handle_health_result(*payload)

        except queue.Empty:
            pass

        self.after(100, self._poll_worker_queue)

    def _handle_api_result(
        self,
        endpoint: str,
        status_code: int,
        elapsed: float,
        data: Any,
    ) -> None:
        """
        Affiche une reponse API reussie ou echouee.
        """

        success = 200 <= status_code < 300
        formatted = json.dumps(data, indent=2, ensure_ascii=False)

        self.http_status_var.set(f"Status HTTP : {status_code}")
        self.response_time_var.set(f"Temps : {elapsed:.2f}s")
        self.result_text.set_text(formatted)
        self.history_panel.add_entry(endpoint, elapsed, success)
        self.logs_panel.log(f"Reponse {status_code} depuis {endpoint} en {elapsed:.2f}s")

    def _handle_api_error(self, endpoint: str, error: str) -> None:
        """
        Affiche une erreur de connexion ou d'execution.
        """

        self.http_status_var.set("Status HTTP : erreur")
        self.response_time_var.set("Temps : -")
        self.result_text.set_text(json.dumps({"error": error}, indent=2, ensure_ascii=False))
        self.history_panel.add_entry(endpoint, 0.0, False)
        self.logs_panel.log(f"Erreur sur {endpoint} : {error}")

    def copy_result(self) -> None:
        """
        Copie le resultat JSON dans le presse-papiers.
        """

        result = self.result_text.get_text()
        if not result:
            messagebox.showinfo("Copie", "Aucun resultat a copier.")
            return

        self.clipboard_clear()
        self.clipboard_append(result)
        self.logs_panel.log("Resultat copie dans le presse-papiers")

    def save_result(self) -> None:
        """
        Sauvegarde le resultat dans un fichier `.json`.
        """

        result = self.result_text.get_text()
        if not result:
            messagebox.showinfo("Sauvegarde", "Aucun resultat a sauvegarder.")
            return

        path = filedialog.asksaveasfilename(
            title="Sauvegarder le resultat",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return

        Path(path).write_text(result, encoding="utf-8")
        self.logs_panel.log(f"Resultat sauvegarde : {path}")

    def open_workflow_image(self) -> None:
        """
        Ouvre l'image `langgraph_workflow.png` si elle existe.

        Bonus demande :
        - si l'image existe, l'ouvrir automatiquement ;
        - sinon afficher "Workflow non genere."
        """

        image_path = Path("langgraph_workflow.png")
        if not image_path.exists():
            messagebox.showinfo("Workflow", "Workflow non genere.")
            self.logs_panel.log("Workflow non genere : langgraph_workflow.png introuvable")
            return

        try:
            # Sous Windows, `startfile` ouvre le fichier avec l'application par
            # defaut. Tkinter reste ainsi simple et portable pour ce contexte.
            import os

            os.startfile(image_path)  # type: ignore[attr-defined]
            self.logs_panel.log(f"Ouverture du workflow : {image_path}")
        except Exception as exc:  # noqa: BLE001 - message utilisateur
            messagebox.showerror("Workflow", f"Impossible d'ouvrir l'image : {exc}")
            self.logs_panel.log(f"Erreur ouverture workflow : {exc}")

    def check_health_once(self) -> None:
        """
        Lance un test de connexion API immediat.
        """

        thread = threading.Thread(target=self._health_worker, daemon=True)
        thread.start()

    def _schedule_health_check(self) -> None:
        """
        Planifie le test automatique de l'API toutes les 5 secondes.
        """

        self.check_health_once()
        self.after(5000, self._schedule_health_check)

    def _health_worker(self) -> None:
        """
        Execute le test de connexion dans un thread secondaire.
        """

        connected, detail = self.client.check_health()
        self.worker_queue.put(("health", (connected, detail)))

    def _handle_health_result(self, connected: bool, detail: str) -> None:
        """
        Met a jour la barre de statut apres un test de connexion.
        """

        if connected:
            self.status_bar.set_connected(detail)
            self.logs_panel.log(f"Connexion API OK : {detail}")
        else:
            self.status_bar.set_disconnected(detail)
            self.logs_panel.log(f"API deconnectee : {detail}")

    def show_about(self) -> None:
        """
        Affiche une fenetre A propos.
        """

        messagebox.showinfo(
            "A propos",
            "AI Agent Desktop Tester\n\n"
            "Interface Tkinter pour tester une API FastAPI/LangGraph/Groq.",
        )


def main() -> None:
    """
    Point d'entree du programme desktop.

    Tkinter utilise une boucle d'evenements appelee `mainloop`.
    Tant que cette boucle tourne, la fenetre reste ouverte et reactive.
    """

    app = AgentTesterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
