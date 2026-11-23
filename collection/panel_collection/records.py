"""Build the shared series record from scraped fields (contract in ARCHITECTURE.md)."""

import hashlib
import re
import unicodedata
from datetime import date

ID_MAX_LENGTH = 128  # retrieval/solr.mjs seriesIdPattern

# Publishers append the edition when the same story also exists as a novel, an omnibus or
# a digital serial. Dropping it gives every edition of a series the same title and ID.
_EDITION = r"(?:the\s+)?(?:manga|manhwa|manhua|comics?|webtoon|serial|v-scroll|omnibus|hardcover|series)"
_EDITION_SUFFIX = re.compile(rf"\s*(?:[(\[]{_EDITION}(?:[\s/]+{_EDITION})*[)\]]|\s+serial)\s*$", re.IGNORECASE)
_NOVEL_TITLE = re.compile(r"[(\[][^)\]]*\bnovels?[)\]]", re.IGNORECASE)

# Source spelling (lowercase) -> shared genre names. Unlisted genres keep the source spelling.
_GENRES = {
    "action-adventure": ("Action", "Adventure"),
    "action and adventure": ("Action", "Adventure"),
    "crime and mystery": ("Crime", "Mystery"),
    "slice-of-life": ("Slice of Life",),
    "lgbtq": ("LGBTQ+",),
    "lgbt+ topics": ("LGBTQ+",),
    "boys love": ("Boys' Love",),
    "isekai / another world": ("Isekai",),
    "historical fiction": ("Historical",),
    "period piece": ("Historical",),
    "cats": ("Animals",),
    "dogs": ("Animals",),
}
# Source tags that describe the format, audience or licence rather than the story.
_NOT_GENRES = {
    "anime tie-in",
    "art book",
    "based on a video game",
    "book tie-in",
    "classic novels",
    "color",
    "digital exclusive",
    "encyclopedia/guides",
    "english original",
    "light novels",
    "manhua",
    "manhwa",
    "media tie-ins",
    "movie tie-in",
    "novel",
    "shojo / josei",
    "special interest",
    "video game related",
    "video game tie-in",
    "webcomics",
    "webtoons",
}


def clean_text(value):
    """Collapse whitespace runs; None becomes an empty string."""
    return " ".join((value or "").split())


def series_title(raw):
    """Clean a scraped title and drop a trailing edition marker such as "(Manga)"."""
    return _EDITION_SUFFIX.sub("", clean_text(raw))


def is_novel_title(title):
    return bool(_NOVEL_TITLE.search(title))


def slugify(text):
    """Lowercase URL slug accepted by the index importer; stable for a given text."""
    # Accents and apostrophes vanish ("Pokémon" -> pokemon, "Journey’s" -> journeys), "+" and
    # "&" are spelled out ("Citrus+" is not "Citrus"), and every other non-alphanumeric run,
    # such as the dot in "Skip・Beat!", separates words.
    decomposed = unicodedata.normalize("NFKD", text).lower().replace("+", " plus ").replace("&", " and ")
    letters = "".join(char for char in decomposed if not unicodedata.combining(char) and char not in "'’‘`")
    slug = re.sub(r"[^a-z0-9]+", "-", letters).strip("-")
    if slug and len(slug) <= ID_MAX_LENGTH:
        return slug
    digest = hashlib.sha1(text.encode()).hexdigest()[:12]
    if not slug:
        return f"series-{digest}"
    return f"{slug[: ID_MAX_LENGTH - 13].rstrip('-')}-{digest}"


def unique(values):
    """Cleaned, non-empty values in first-seen order, compared case-insensitively."""
    seen = set()
    result = []
    for value in values:
        text = clean_text(value)
        if text and text.casefold() not in seen:
            seen.add(text.casefold())
            result.append(text)
    return result


def join_names(names):
    """["A", "B", "C"] -> "A, B and C", the creator format of the shared record."""
    names = unique(names)
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def normalize_genres(raw_genres):
    genres = set()
    for raw in unique(raw_genres):
        key = raw.lower()
        if key not in _NOT_GENRES:
            genres.update(_GENRES.get(key, (raw,)))
    return sorted(genres)


def first_year(text):
    """Earliest plausible four-digit year in a copyright line, or None."""
    years = [int(year) for year in re.findall(r"(?<!\d)(?:19|20)\d\d(?!\d)", text or "")]
    years = [year for year in years if 1900 <= year <= date.today().year]
    return min(years, default=None)


def series_record(*, title, source_url, publisher, aliases=(), creators=(), description="", genres=(), debut_year=None):
    """One normalized series record. `title` must already be cleaned and non-empty."""
    return {
        "id": slugify(title),
        "title": title,
        "aliases": [alias for alias in unique(aliases) if alias.casefold() != title.casefold()],
        "creator": join_names(creators),
        "description": clean_text(description),
        "genres": normalize_genres(genres),
        "publisher": publisher,
        "debut_year": debut_year,
        "source_urls": [source_url],
    }
