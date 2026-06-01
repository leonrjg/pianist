"""
Anki integration service via AnkiConnect.

Connects to AnkiConnect API running on localhost:8765.
Requires Anki to be running with AnkiConnect add-on installed.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
import random
import re
import io
import base64
import logging
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@dataclass
class AnkiCard:
    """Represents an Anki flashcard."""
    card_id: int
    deck_name: str
    front: str
    back: str


@dataclass
class AnkiNextReview:
    """Display summary for a card's next scheduled review."""
    label: str
    due_at: Optional[datetime] = None
    due_date: Optional[date] = None
    is_intraday: bool = False


class AnkiConnectError(Exception):
    """Exception raised for AnkiConnect API errors."""
    pass


class AnkiService:
    """
    Service for Anki integration via AnkiConnect API.

    Requires:
    - Anki running in background
    - AnkiConnect add-on installed (code: 2055492159)
    """

    ANKICONNECT_URL = "http://127.0.0.1:8765"
    ANKICONNECT_VERSION = 6
    REQUEST_TIMEOUT = 5  # seconds

    _card_cache = {}  # Maps reminder_id -> AnkiCard
    _shown_card_ids: set = set()  # Card IDs currently displayed but not yet answered/dismissed
    _template_cache = {}  # Maps model_name -> template info (performance optimization)
    _deck_config_cache = {}  # Maps deck_name -> deck config (performance optimization)
    _media_dir = None  # Cached media directory path
    CANDIDATE_BATCH_SIZE = 100

    @classmethod
    def _invoke(cls, action: str, params: Optional[dict] = None) -> any:
        """
        Invoke an AnkiConnect API action.

        Args:
            action: API action name
            params: Optional parameters for the action

        Returns:
            Result from AnkiConnect API

        Raises:
            AnkiConnectError: If connection fails or API returns error
        """
        payload = {
            "action": action,
            "version": cls.ANKICONNECT_VERSION
        }
        if params:
            payload["params"] = params

        logger.debug(f"AnkiConnect request: action={action}, params={params}")

        try:
            response = requests.post(
                cls.ANKICONNECT_URL,
                json=payload,
                timeout=cls.REQUEST_TIMEOUT
            )
            response.raise_for_status()

            result = response.json()
            logger.debug(f"AnkiConnect response: {result}")

            # Check for API errors
            if len(result) != 2:
                logger.error(f"Invalid response format: {result}")
                raise AnkiConnectError("Invalid response format from AnkiConnect")
            if "error" not in result:
                logger.error(f"Response missing error field: {result}")
                raise AnkiConnectError("Response missing error field")
            if "result" not in result:
                logger.error(f"Response missing result field: {result}")
                raise AnkiConnectError("Response missing result field")
            if result["error"]:
                logger.error(f"AnkiConnect returned error: {result['error']}")
                raise AnkiConnectError(f"AnkiConnect error: {result['error']}")

            logger.debug(f"AnkiConnect success: action={action}, result={result['result']}")
            return result["result"]

        except ConnectionError as e:
            logger.error(f"Connection error to AnkiConnect: {e}")
            raise AnkiConnectError(
                "Could not connect to Anki. "
                "Please ensure Anki is running with AnkiConnect add-on installed."
            )
        except Timeout as e:
            logger.error(f"Timeout connecting to AnkiConnect: {e}")
            raise AnkiConnectError("Request to AnkiConnect timed out")
        except RequestException as e:
            logger.error(f"Request exception: {e}")
            raise AnkiConnectError(f"Request failed: {str(e)}")
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid response format exception: {e}, response: {result if 'result' in locals() else 'N/A'}")
            raise AnkiConnectError(f"Invalid response format: {str(e)}")

    @classmethod
    def _parse_template_fields(cls, template_text: str) -> List[str]:
        """
        Extract field names from an Anki template.

        Args:
            template_text: Template string with {{FieldName}} references

        Returns:
            List of field names referenced in the template
        """
        # Special Anki variables to exclude
        special_vars = {
            'FrontSide', 'Tags', 'Type', 'Deck', 'Subdeck',
            'Card', 'CardFlag', 'c', 'deck', 'subdeck', 'tags'
        }

        # Match {{...}} patterns
        pattern = r'\{\{([^{}]+)\}\}'
        matches = re.findall(pattern, template_text)

        fields = []
        for match in matches:
            # Remove modifiers (e.g., "Field:hint" -> "Field")
            field_name = match.split(':')[0].strip()

            # Remove conditional prefixes (e.g., "#Field" or "/Field" -> "Field")
            field_name = field_name.lstrip('#/')

            # Skip special variables and duplicates
            if field_name not in special_vars and field_name not in fields:
                fields.append(field_name)

        return fields

    @classmethod
    def _get_field_extraction_strategy(cls, model_name: str, card_ord: int) -> Tuple[List[str], List[str]]:
        """
        Determine which fields to extract for front and back based on card template.

        Args:
            model_name: Name of the note type
            card_ord: Card ordinal (0 for first card, 1 for second, etc.)

        Returns:
            Tuple of (front_fields, back_fields) - lists of field names
        """
        # Check cache first (performance optimization)
        cache_key = f"{model_name}:{card_ord}"
        if cache_key in cls._template_cache:
            return cls._template_cache[cache_key]

        try:
            # Get model templates
            templates = cls._invoke("modelTemplates", {"modelName": model_name})

            # Get the specific template for this card ordinal
            template_names = list(templates.keys())
            if card_ord >= len(template_names):
                raise AnkiConnectError(f"Card ordinal {card_ord} out of range for model {model_name}")

            template_name = template_names[card_ord]
            card_template = templates[template_name]

            # Parse front and back templates
            front_template = card_template.get('Front', '')
            back_template = card_template.get('Back', '')

            front_fields = cls._parse_template_fields(front_template)
            all_back_fields = cls._parse_template_fields(back_template)

            # Answer-only fields = fields in back but not in front
            back_fields = [f for f in all_back_fields if f not in front_fields]

            # Cache the result
            result = (front_fields, back_fields)
            cls._template_cache[cache_key] = result

            return result

        except Exception as e:
            # If template parsing fails, return empty lists (will trigger fallback)
            return ([], [])

    @classmethod
    def _extract_field_values(cls, fields_dict: Dict, field_names: List[str]) -> str:
        """
        Extract and concatenate values from specified fields.

        Args:
            fields_dict: Dictionary of field data from cardsInfo
            field_names: List of field names to extract

        Returns:
            Concatenated field values (preserves HTML for rendering)
        """
        values = []
        for field_name in field_names:
            if field_name in fields_dict:
                value = fields_dict[field_name].get('value', '').strip()
                if value:
                    values.append(value)

        # Join multiple fields with line breaks
        return '\n\n'.join(values) if values else ''

    # Commands to strip entirely (no content to preserve)
    _STRIP_COMMANDS = [
        r'\tiny', r'\scriptsize', r'\footnotesize', r'\small',
        r'\normalsize', r'\large', r'\Large', r'\LARGE',
        r'\huge', r'\Huge',
    ]

    # Simple string replacements: (old, new)
    _SIMPLE_REPLACEMENTS = [
        ('\\space', '\\ '),
        ('\\bmod', '\\mathrm{mod}'),
        ('\\mod', '\\mathrm{mod}'),
        ('\\lcm', '\\mathrm{lcm}'),
        ('\\lvert', '|'),
        ('\\rvert', '|'),
    ]

    # Regex replacements: (pattern, replacement)
    # Order matters — more specific patterns first
    _REGEX_REPLACEMENTS = [
        # \stackrel{\_}{X} → \overline{X} (X-bar / sample mean)
        (r'\\stackrel\{\\_\}\{([^}]+)\}', r'\\overline{\1}'),
        # \stackrel → \overset (mathtext supports overset but not stackrel)
        (r'\\stackrel', r'\\overset'),
        # \tfrac → \frac, \dbinom/\tbinom → \binom
        (r'\\tfrac', r'\\frac'),
        (r'\\[dt]binom', r'\\binom'),
        # \textbf{...} → \mathbf{...}, \textit{...} → \mathit{...}
        (r'\\textbf', r'\\mathbf'),
        (r'\\textit', r'\\mathit'),
        (r'\\emph', r'\\mathit'),
        (r'\\bm', r'\\mathbf'),
        # \xrightarrow{...} → \rightarrow, \xleftarrow{...} → \leftarrow
        (r'\\xrightarrow\{[^}]*\}', r'\\rightarrow'),
        (r'\\xleftarrow\{[^}]*\}', r'\\leftarrow'),
        # \pmod{x} → (\mathrm{mod}\ x)
        (r'\\pmod\{([^}]+)\}', r'(\\mathrm{mod}\\ \1)'),
        # \color{...}{content} → content (strip color, keep content)
        (r'\\color\{[^}]*\}\{([^}]+)\}', r'\1'),
        # \hspace{...} → thin space
        (r'\\hspace\{[^}]*\}', r'\\ '),
        # \boxed{content} → content
        (r'\\boxed\{([^}]+)\}', r'\1'),
        # \cancel{content} → content
        (r'\\cancel\{([^}]+)\}', r'\1'),
        # \underline{content} → content
        (r'\\underline\{([^}]+)\}', r'\1'),
        # \overbrace{content} / \underbrace{content} → content
        (r'\\overbrace\{([^}]+)\}', r'\1'),
        (r'\\underbrace\{([^}]+)\}', r'\1'),
        # {n \choose k} → \binom{n}{k}
        (r'\{([^}]+)\s*\\choose\s*([^}]+)\}', r'\\binom{\1}{\2}'),
        # \DeclareMathOperator{...}{...} → strip entirely
        (r'\\DeclareMathOperator\{[^}]*\}\{[^}]*\}', r''),
        # \_ (literal underscore) → hyphen as approximation (must be after \stackrel{\_} rule)
        (r'\\_', r'-'),
    ]

    @classmethod
    def _preprocess_latex_for_mathtext(cls, latex_code: str) -> str:
        """Preprocess LaTeX to be compatible with matplotlib's mathtext renderer."""
        result = latex_code
        for cmd in cls._STRIP_COMMANDS:
            result = result.replace(cmd, '')
        for old, new in cls._SIMPLE_REPLACEMENTS:
            result = result.replace(old, new)
        for pattern, replacement in cls._REGEX_REPLACEMENTS:
            result = re.sub(pattern, replacement, result)
        return result.strip()

    # Environments that should be split into rows for line-by-line rendering
    _MULTILINE_ENVS = {'array', 'align', 'aligned', 'gather', 'gathered', 'cases', 'matrix',
                       'pmatrix', 'bmatrix', 'vmatrix', 'Bmatrix', 'Vmatrix', 'eqnarray',
                       'split', 'multline'}

    @classmethod
    def _split_environment_rows(cls, latex_code: str) -> Optional[List[str]]:
        """
        Detect \\begin{env}...\\end{env} and split into individual rows.

        Returns a list of cleaned row expressions, or None if no environment found.
        """
        pattern = r'\\begin\{(\w+)\}(?:\{[^}]*\})?\s*(.*?)\s*\\end\{\1\}'
        match = re.search(pattern, latex_code, flags=re.DOTALL)
        if not match:
            return None

        env_name = match.group(1)
        if env_name not in cls._MULTILINE_ENVS:
            return None

        body = match.group(2)

        # Split on \\ (row separator in LaTeX environments)
        raw_rows = re.split(r'\\\\', body)

        rows = []
        for row in raw_rows:
            # Strip alignment markers (&) and clean up
            cleaned = row.replace('&', ' ').strip()
            # Remove \hline
            cleaned = re.sub(r'\\hline', '', cleaned)
            if cleaned:
                rows.append(cleaned)

        return rows if rows else None

    @classmethod
    def _render_latex_to_base64(cls, latex_code: str, fontsize: int = 14) -> Optional[str]:
        """
        Render LaTeX to a base64-encoded PNG image using matplotlib.

        For expressions containing \\begin/\\end environments (array, align, cases, etc.),
        splits into individual rows and renders them stacked vertically.

        Args:
            latex_code: LaTeX mathematical expression
            fontsize: Font size for rendering

        Returns:
            Base64 data URI string, or None if rendering fails
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend

            # Check for multiline environments
            rows = cls._split_environment_rows(latex_code)
            if rows:
                return cls._render_multiline_latex(rows, fontsize)

            clean_latex = cls._preprocess_latex_for_mathtext(latex_code)

            # Create figure with transparent background
            fig = plt.figure(figsize=(0.01, 0.01))
            fig.patch.set_alpha(0)

            # Render LaTeX using matplotlib's mathtext
            # mathtext supports common math without needing system LaTeX
            text = fig.text(
                0, 0,
                f'${clean_latex}$',
                fontsize=fontsize,
                color='white',  # White text for dark notification background
                usetex=False  # Use mathtext, not system LaTeX
            )

            # Get tight bounding box
            fig.canvas.draw()
            bbox = text.get_window_extent(fig.canvas.get_renderer())
            bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())

            # Expand bbox slightly for padding
            bbox_inches = bbox_inches.padded(0.1)

            # Render to PNG bytes
            buf = io.BytesIO()
            fig.savefig(
                buf,
                format='png',
                bbox_inches=bbox_inches,
                transparent=True,
                dpi=150,
                pad_inches=0
            )
            plt.close(fig)

            # Encode as base64
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')

            # Return data URI
            return f'data:image/png;base64,{img_base64}'

        except Exception as e:
            # If rendering fails, return None (will keep raw LaTeX)
            return None

    @classmethod
    def _render_multiline_latex(cls, rows: List[str], fontsize: int = 14) -> Optional[str]:
        """
        Render multiple LaTeX rows as a single stacked image.

        Each row is preprocessed and rendered as a separate mathtext line,
        then combined vertically into one PNG.

        Args:
            rows: List of LaTeX expressions (one per row)
            fontsize: Font size for rendering

        Returns:
            Base64 data URI string, or None if rendering fails
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')

            # Preprocess each row
            clean_rows = [cls._preprocess_latex_for_mathtext(r) for r in rows]
            # Filter out empty rows
            clean_rows = [r for r in clean_rows if r]
            if not clean_rows:
                return None

            # Use a large figure so all text fits, then crop via bbox_inches
            line_height_inches = fontsize * 1.6 / 72
            total_height = len(clean_rows) * line_height_inches + 0.5
            fig = plt.figure(figsize=(10, total_height))
            fig.patch.set_alpha(0)

            texts = []
            for i, row_latex in enumerate(clean_rows):
                # Position from top of figure downward using figure coordinates
                y_pos = 1.0 - (i * line_height_inches + 0.1) / total_height
                t = fig.text(
                    0.02, y_pos,
                    f'${row_latex}$',
                    fontsize=fontsize,
                    color='white',
                    usetex=False,
                    verticalalignment='top',
                )
                texts.append(t)

            # Draw to compute bounding boxes
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()

            # Compute union bounding box of all text objects
            bboxes = [t.get_window_extent(renderer) for t in texts]
            from matplotlib.transforms import Bbox
            union = Bbox.union(bboxes)
            bbox_inches = union.transformed(fig.dpi_scale_trans.inverted()).padded(0.1)

            buf = io.BytesIO()
            fig.savefig(
                buf,
                format='png',
                bbox_inches=bbox_inches,
                transparent=True,
                dpi=150,
                pad_inches=0
            )
            plt.close(fig)

            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return f'data:image/png;base64,{img_base64}'

        except Exception as e:
            logger.warning(f"Multiline LaTeX rendering failed: {e}")
            return None

    @classmethod
    def _get_media_dir(cls) -> Optional[str]:
        """
        Get the Anki media directory path, cached after first call.

        Returns:
            Absolute path to collection.media folder, or None on failure
        """
        if cls._media_dir is not None:
            return cls._media_dir
        try:
            cls._media_dir = cls._invoke("getMediaDirPath")
            return cls._media_dir
        except Exception as e:
            logger.warning(f"Could not get media dir path: {e}")
            return None

    @classmethod
    def _resolve_media_paths(cls, html_text: str) -> str:
        """
        Resolve relative image src attributes to absolute paths in Anki's media folder.

        Rewrites <img src="filename.png"> to <img src="/absolute/path/filename.png">
        for files that exist in the media directory. Skips URLs and data URIs.

        Args:
            html_text: HTML text potentially containing relative image references

        Returns:
            HTML with resolved image paths
        """
        if not html_text:
            return html_text

        import os
        media_dir = cls._get_media_dir()
        if not media_dir:
            return html_text

        def resolve_src(match):
            src = match.group(1)
            # Skip URLs and data URIs
            if src.startswith(('http://', 'https://', 'data:', '/')):
                return match.group(0)
            # Check if file exists in media folder
            abs_path = os.path.join(media_dir, src)
            if os.path.exists(abs_path):
                return match.group(0).replace(src, abs_path)
            return match.group(0)

        return re.sub(r'<img\s[^>]*src="([^"]+)"', resolve_src, html_text)

    @classmethod
    def _process_latex(cls, html_text: str) -> str:
        r"""
        Find and replace LaTeX expressions with rendered images.

        Supports delimiters: \(...\), \[...\], $...$, $$...$$

        Args:
            html_text: HTML text potentially containing LaTeX

        Returns:
            HTML with LaTeX replaced by <img> tags
        """
        if not html_text:
            return html_text

        # LaTeX delimiter patterns (in order of precedence)
        # Sizes adjusted to match notification text (12px)
        patterns = [
            (r'\\\[(.+?)\\\]', 10, 'block'),      # Display math: \[...\] - slightly larger
            (r'\$\$(.+?)\$\$', 10, 'block'),      # Display math: $$...$$ - slightly larger
            (r'\\\((.+?)\\\)', 7, 'inline'),     # Inline math: \(...\) - match text size
            (r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', 9, 'inline'),  # Inline: $...$ - match text size
        ]

        result = html_text

        for pattern, fontsize, math_type in patterns:
            def replace_latex(match):
                latex_code = match.group(1).strip()

                # Render to base64 image
                img_data_uri = cls._render_latex_to_base64(latex_code, fontsize)

                if img_data_uri:
                    # Replace with img tag
                    style = 'vertical-align: middle;' if math_type == 'inline' else 'display: block; margin: 10px auto;'
                    return f'<img src="{img_data_uri}" style="{style}" alt="{latex_code}">'
                else:
                    # Keep original if rendering failed
                    return match.group(0)

            result = re.sub(pattern, replace_latex, result, flags=re.DOTALL)

        return result

    @classmethod
    def get_card(cls, deck_name: str, reminder_id: Optional[int] = None) -> AnkiCard:
        """
        Get a card from the specified deck.

        Prioritizes cards Anki considers due. If no due cards are available,
        selects from new cards. Does not show not-due review cards.

        Args:
            deck_name: Name of the Anki deck
            reminder_id: Optional reminder ID to cache card for retrieval

        Returns:
            AnkiCard with front and back

        Raises:
            AnkiConnectError: If connection fails or deck is empty
        """
        # First show due learning/review cards. If all due candidates are
        # already displayed in this app session, fall through to new cards.
        query = f'deck:"{deck_name}" is:due -is:suspended'
        due_card_ids = cls._invoke("findCards", {"query": query})
        card_info = cls._select_due_card(deck_name, due_card_ids)

        if card_info is None:
            logger.debug("No due Anki cards found for deck '%s', checking new cards", deck_name)
            query = f'deck:"{deck_name}" is:new -is:suspended'
            new_card_ids = cls._invoke("findCards", {"query": query})
            card_info = cls._select_new_card(deck_name, new_card_ids)

        if card_info is None:
            raise AnkiConnectError(f"You've finished deck '{deck_name}' for today")

        return cls._card_from_info(card_info, reminder_id)

    @classmethod
    def _select_due_card(cls, deck_name: str, card_ids: List[int]) -> Optional[Dict[str, Any]]:
        """Select the next due candidate using Anki-like queue/review ordering."""
        if not card_ids:
            return None

        available = cls._available_card_ids(card_ids, deck_name, "due")
        if not available:
            return None

        cards_info = cls._get_candidate_cards_info(deck_name, available)
        if not cards_info:
            raise AnkiConnectError(f"Could not retrieve due card info for deck '{deck_name}'")

        config = cls._get_deck_config(deck_name)
        cards_info.sort(key=lambda card: cls._due_card_sort_key(card, config))
        return cards_info[0]

    @classmethod
    def _select_new_card(cls, deck_name: str, card_ids: List[int]) -> Optional[Dict[str, Any]]:
        """Select a new candidate using exposed deck display-order settings."""
        if not card_ids:
            return None

        available = cls._available_card_ids(card_ids, deck_name, "new")
        if not available:
            return None

        cards_info = cls._get_candidate_cards_info(deck_name, available)
        if not cards_info:
            raise AnkiConnectError(f"Could not retrieve new card info for deck '{deck_name}'")

        config = cls._get_deck_config(deck_name)
        cards_info.sort(key=lambda card: cls._new_card_sort_key(card, config))
        return cards_info[0]

    @classmethod
    def _available_card_ids(cls, card_ids: List[int], deck_name: str, candidate_type: str) -> List[int]:
        """Return candidate IDs not already displayed in this app session."""
        available = [cid for cid in card_ids if cid not in cls._shown_card_ids]
        if card_ids and not available:
            logger.info(
                "All %s Anki candidates for deck '%s' are already displayed; not showing another card",
                candidate_type,
                deck_name
            )
        return available

    @classmethod
    def _get_candidate_cards_info(cls, deck_name: str, card_ids: List[int]) -> List[Dict[str, Any]]:
        """Fetch a bounded batch of candidate card metadata."""
        candidate_ids = card_ids[:cls.CANDIDATE_BATCH_SIZE]
        cards_info = cls._invoke("cardsInfo", {"cards": candidate_ids})
        if not cards_info:
            return []
        expected = set(candidate_ids)
        return [
            card
            for card in cards_info
            if card.get("cardId") in expected
        ]

    @classmethod
    def _get_deck_config(cls, deck_name: str) -> Dict[str, Any]:
        """Fetch and cache deck config used for display-order approximations."""
        if deck_name not in cls._deck_config_cache:
            try:
                cls._deck_config_cache[deck_name] = cls._invoke("getDeckConfig", {"deck": deck_name})
            except AnkiConnectError:
                raise
            except Exception as e:
                logger.exception("Unexpected error fetching Anki deck config for '%s'", deck_name)
                raise AnkiConnectError(f"Could not retrieve deck config for '{deck_name}': {e}")
        return cls._deck_config_cache[deck_name] or {}

    @classmethod
    def _due_card_sort_key(cls, card_info: Dict[str, Any], config: Dict[str, Any]) -> Tuple:
        """
        Approximate Anki's due-card order.

        Anki gathers intraday learning, then interday learning, then review
        cards before introducing new cards. Review sort order is approximated
        from the exposed deck config where possible.
        """
        queue_priority = cls._queue_priority(card_info)
        return (queue_priority, cls._review_sort_key(card_info, config), card_info.get("cardId", 0))

    @classmethod
    def _queue_priority(cls, card_info: Dict[str, Any]) -> int:
        """Return broad Anki queue priority for due candidates."""
        queue = card_info.get("queue")
        card_type = card_info.get("type")

        if queue == 1:
            return 0  # intraday learning
        if queue == 3:
            return 1  # interday learning
        if card_type in (1, 3):
            return 1
        if queue == 2 or card_type == 2:
            return 2  # review
        return 3

    @classmethod
    def _review_sort_key(cls, card_info: Dict[str, Any], config: Dict[str, Any]) -> Tuple:
        """Approximate the configured review sort order using cardsInfo fields."""
        review_order = config.get("reviewOrder", 0)
        due = card_info.get("due", 0)
        interval = card_info.get("interval", 0)
        factor = card_info.get("factor")

        if review_order == 2:
            return (-interval, due)
        if review_order == 3 and factor is not None:
            return (factor, due)
        if review_order == 4 and factor is not None:
            return (-factor, due)
        if review_order == 5:
            return (cls._relative_overdueness(card_info), due)

        # reviewOrder 0/1 are both due-date based in Anki's UI; 1 also uses
        # deck as a tiebreaker, which matters only when subdecks are present.
        if review_order == 1:
            return (due, card_info.get("deckName", ""))
        return (due,)

    @classmethod
    def _relative_overdueness(cls, card_info: Dict[str, Any]) -> float:
        """Approximate relative overdueness from exposed due/interval fields."""
        interval = card_info.get("interval") or 0
        due = card_info.get("due") or 0
        if interval <= 0:
            return 0.0
        return -(abs(min(due, 0)) / interval)

    @classmethod
    def _new_card_sort_key(cls, card_info: Dict[str, Any], config: Dict[str, Any]) -> Tuple:
        """Approximate configured new-card gather/sort order."""
        sort_order = config.get("newSortOrder", 1)
        gather_priority = config.get("newGatherPriority", 1)
        gathered_key = cls._new_gather_key(card_info, gather_priority)
        card_type = card_info.get("ord", 0)

        if sort_order == 0:
            return (card_type, gathered_key)
        if sort_order == 2:
            return (card_type, random.random())
        if sort_order == 3:
            return (random.random(), card_type)
        if sort_order == 4:
            return (random.random(),)
        return (gathered_key,)

    @classmethod
    def _new_gather_key(cls, card_info: Dict[str, Any], gather_priority: int) -> Tuple:
        """Approximate new-card gather order from deck/order metadata."""
        due = card_info.get("due", 0)
        deck_name = card_info.get("deckName", "")
        note_id = card_info.get("note", 0)
        card_id = card_info.get("cardId", 0)

        if gather_priority == 2:
            return (due, deck_name, card_id)
        if gather_priority == 3:
            return (-due, deck_name, card_id)
        if gather_priority == 4:
            return (random.random(), note_id, card_id)
        if gather_priority == 5:
            return (random.random(), card_id)
        return (deck_name, due, card_id)

    @classmethod
    def _card_from_info(cls, card_info: Dict[str, Any], reminder_id: Optional[int] = None) -> AnkiCard:
        """Build an AnkiCard from cardsInfo output and cache it if requested."""

        # Extract front and back using template-based strategy
        model_name = card_info.get("modelName", "")
        card_ord = card_info.get("ord", 0)
        fields = card_info.get("fields", {})

        # Get field extraction strategy from templates
        front_fields, back_fields = cls._get_field_extraction_strategy(model_name, card_ord)

        # Extract field values based on template analysis
        front = cls._extract_field_values(fields, front_fields)
        back = cls._extract_field_values(fields, back_fields)

        # Fallback: If template parsing failed or returned nothing, use rendered HTML
        if not front:
            front = card_info.get("question", "")
        if not back:
            # Try to extract just the answer portion from rendered HTML
            # or fall back to showing the full answer (includes question)
            back = card_info.get("answer", "")

        # Process LaTeX: Replace LaTeX expressions with rendered images
        front = cls._process_latex(front)
        back = cls._process_latex(back)

        # Resolve media paths: Rewrite relative img src to absolute paths
        front = cls._resolve_media_paths(front)
        back = cls._resolve_media_paths(back)

        # Create AnkiCard object
        card = AnkiCard(
            card_id=card_info["cardId"],
            deck_name=card_info["deckName"],
            front=front,
            back=back
        )

        # Mark as shown so subsequent fetches skip this card until answered/dismissed
        cls._shown_card_ids.add(card.card_id)

        # Cache for later retrieval
        if reminder_id:
            cls._card_cache[reminder_id] = card

        return card

    @classmethod
    def get_cached_card(cls, reminder_id: int) -> Optional[AnkiCard]:
        """
        Get previously fetched card for a reminder.

        Args:
            reminder_id: ID of the reminder

        Returns:
            Cached AnkiCard or None if not found
        """
        return cls._card_cache.get(reminder_id)

    @classmethod
    def submit_rating(cls, card_id: int, ease: int) -> bool:
        """
        Submit rating to Anki.

        Args:
            card_id: ID of the card being rated
            ease: Rating (1=Again, 2=Hard, 3=Good, 4=Easy)

        Returns:
            True if successful

        Raises:
            AnkiConnectError: If submission fails
            ValueError: If ease is not between 1 and 4
        """
        logger.info(f"[RATING] Submitting rating for card {card_id} with ease {ease}")

        if ease not in [1, 2, 3, 4]:
            logger.error(f"[RATING] Invalid ease value: {ease}")
            raise ValueError(f"Ease must be between 1 and 4, got {ease}")

        # AnkiConnect's answerCards delegates to Anki's scheduler.answerCard(),
        # which can reject otherwise due/new cards when they are not the
        # scheduler's current top card. Move the card to the front of the due
        # order without changing its type/queue; setDueDate would convert new
        # cards to review cards and alter their learning progression.
        logger.info(f"[RATING] Moving card to front of Anki due order before answerCards...")
        cls._invoke("setSpecificValueOfCard", {
            "card": card_id,
            "keys": ["due"],
            "newValues": [0],
            "warning_check": True
        })
        logger.info(f"[RATING] Card due order prepared")

        logger.info(f"[RATING] Calling answerCards API...")
        result = cls._invoke("answerCards", {
            "answers": [{"cardId": card_id, "ease": ease}]
        })
        logger.info(f"[RATING] answerCards returned: {result}")

        # Result is a list of booleans indicating success for each card
        if result and result[0]:
            logger.info(f"[RATING] ✓ Rating submitted successfully for card {card_id}")
            return True
        else:
            logger.error(f"[RATING] ✗ Rating submission returned False for card {card_id}")
            raise AnkiConnectError(f"Failed to submit rating for card {card_id}")

    @classmethod
    def get_next_review_summary(cls, card_id: int, now: Optional[datetime] = None) -> Optional[AnkiNextReview]:
        """
        Get a display summary for the next scheduled review.

        Should be called after submit_rating to show the user when the card will next appear.

        Args:
            card_id: ID of the card
            now: Current datetime, injectable for tests

        Returns:
            Display summary, or None if it could not be determined
        """
        try:
            now = now or datetime.now()
            cards_info = cls._invoke("cardsInfo", {"cards": [card_id]})
            if not cards_info:
                return None
            card_info = cards_info[0]
            queue = card_info.get("queue")
            due = card_info.get("due")
            interval = card_info.get("interval", 0)

            if queue == 1 and due:
                due_at = datetime.fromtimestamp(due)
                return cls._intraday_next_review(due_at, now)

            if interval <= 0:
                return AnkiNextReview("later today", due_date=now.date(), is_intraday=True)

            due_date = now.date() + timedelta(days=interval)
            return AnkiNextReview(cls._format_due_date_label(due_date, now.date()), due_date=due_date)
        except Exception:
            logger.exception("Could not determine next Anki review for card %s", card_id)
            return None

    @classmethod
    def _intraday_next_review(cls, due_at: datetime, now: datetime) -> AnkiNextReview:
        """Format an intraday learning due timestamp."""
        if due_at <= now:
            return AnkiNextReview("now", due_at=due_at, due_date=due_at.date(), is_intraday=True)

        delta = due_at - now
        if due_at.date() == now.date():
            total_seconds = int(delta.total_seconds())
            if total_seconds < 90:
                label = "in 1 min"
            elif total_seconds < 3600:
                label = f"in {round(total_seconds / 60)} min"
            else:
                hours = round(total_seconds / 3600)
                label = f"in {hours} hr" if hours == 1 else f"in {hours} hrs"
            return AnkiNextReview(label, due_at=due_at, due_date=due_at.date(), is_intraday=True)

        tomorrow = now.date() + timedelta(days=1)
        if due_at.date() == tomorrow:
            label = f"tomorrow at {due_at.strftime('%H:%M')}"
        else:
            label = due_at.strftime("%b %-d at %H:%M")
        return AnkiNextReview(label, due_at=due_at, due_date=due_at.date(), is_intraday=True)

    @classmethod
    def _format_due_date_label(cls, due_date: date, today: date) -> str:
        """Format an interday due date."""
        if due_date <= today:
            return "later today"
        if due_date == today + timedelta(days=1):
            return "tomorrow"
        return due_date.strftime("%b %-d")

    @classmethod
    def get_next_due_date(cls, card_id: int) -> Optional[date]:
        """
        Backward-compatible date-only wrapper for next review information.
        """
        summary = cls.get_next_review_summary(card_id)
        return summary.due_date if summary else None

    @classmethod
    def open_in_editor(cls, card_id: int) -> None:
        """
        Open the card's note in Anki's note editor.

        Args:
            card_id: ID of the card to edit

        Raises:
            AnkiConnectError: If request fails
        """
        note_ids = cls._invoke("cardsToNotes", {"cards": [card_id]})
        if not note_ids:
            raise AnkiConnectError(f"Could not find note for card {card_id}")
        cls._invoke("guiEditNote", {"note": note_ids[0]})

    @classmethod
    def bury_card(cls, card_id: int) -> bool:
        """
        Bury a card until the next day by rescheduling it to tomorrow.

        Args:
            card_id: ID of the card to bury

        Returns:
            True if successful

        Raises:
            AnkiConnectError: If request fails
        """
        cls._invoke("setDueDate", {"cards": [card_id], "days": "1"})
        return True

    @classmethod
    def suspend_card(cls, card_id: int) -> bool:
        """
        Suspend a card indefinitely.

        Args:
            card_id: ID of the card to suspend

        Returns:
            True if successful

        Raises:
            AnkiConnectError: If request fails
        """
        cls._invoke("suspend", {"cards": [card_id]})
        return True

    @classmethod
    def mark_shown(cls, card_id: int):
        """Re-add a card to the shown set (used when undoing a rating to re-display the card)."""
        cls._shown_card_ids.add(card_id)

    @classmethod
    def recache_card(cls, reminder_id: int, card: 'AnkiCard'):
        """Restore a card to the cache and mark it as shown (used for undo)."""
        cls._card_cache[reminder_id] = card
        cls._shown_card_ids.add(card.card_id)

    @classmethod
    def clear_cache(cls, reminder_id: int):
        """
        Clear cached card for a reminder.

        Args:
            reminder_id: ID of the reminder
        """
        card = cls._card_cache.pop(reminder_id, None)
        if card:
            cls._shown_card_ids.discard(card.card_id)

    @classmethod
    def get_deck_names(cls) -> List[str]:
        """
        Get list of all deck names.

        Returns:
            List of deck names

        Raises:
            AnkiConnectError: If request fails
        """
        return cls._invoke("deckNames")

    @classmethod
    def test_connection(cls) -> bool:
        """
        Test if AnkiConnect is accessible.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            cls._invoke("deckNames")
            return True
        except AnkiConnectError:
            return False

    @classmethod
    def clear_template_cache(cls):
        """
        Clear the template cache.

        Useful if note types are modified during runtime.
        """
        cls._template_cache.clear()

    @classmethod
    def clear_deck_config_cache(cls):
        """Clear cached deck configs."""
        cls._deck_config_cache.clear()
