#!/usr/bin/env python3
"""
update_publications.py
======================
Fetches publications from a Google Scholar profile using the ``scholarly``
library and rewrites the publications list in ``publications.html``.

The HTML block between the markers::

    <!-- PUBLICATIONS_START -->
    ...
    <!-- PUBLICATIONS_END -->

is replaced with a freshly generated ``<ol>`` that matches the hand-written
formatting already used on the page:

  * Title linked to DOI (bold)
  * Authors, with "DT Yang" bolded via inline style
  * Italic journal name
  * Year wrapped in ``<b2>`` tags (matching the existing style)

Usage
-----
Run from the repository root::

    python scripts/update_publications.py

Or with an explicit path::

    python scripts/update_publications.py --html publications.html
"""

import argparse
import html
import re
import sys
import time

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCHOLAR_USER_ID = "VTq9cxYAAAAJ"

# The author's abbreviated name as it appears in citations.
# Used to apply the bold-weight span.
AUTHOR_HIGHLIGHT = ["Darian T. Yang", "Darian T Yang", "Darian Yang"]

# Markers that delimit the auto-generated block inside publications.html
MARKER_START = "<!-- PUBLICATIONS_START -->"
MARKER_END   = "<!-- PUBLICATIONS_END -->"

# How long to wait between Scholar requests (seconds) to avoid rate-limiting.
REQUEST_DELAY = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bold_author(author_str: str, highlight: list[str]) -> str:
    """Wrap *highlight* in the same bold-span used on the page.

    Both *author_str* and the search key are treated as already-HTML-escaped
    strings so the replacement never corrupts entity references.
    """
    for h in highlight:
        escaped = html.escape(h)
        author_str = author_str.replace(
            escaped,
            f'<span style="font-weight: 800;">{escaped}</span>',
        )
    return author_str


def _format_authors(authors: list[str], highlight: list[str]) -> str:
    """
    Turn a list of author strings into the comma-separated inline HTML
    used on the page (e.g. "AJ Guseman, LJ Rennick, …, and AM Gronenborn.").
    """
    parts = []
    for i, author in enumerate(authors):
        a = html.escape(author.strip())
        if any(h in author for h in highlight):
            a = _bold_author(a, highlight)
        last = i == len(authors) - 1
        if last and len(authors) > 1:
            parts.append("and " + a + ".")
        elif i < len(authors) - 1:
            parts.append(a + ",")
        else:
            parts.append(a + ".")
    return " ".join(parts)


def _build_li(pub: dict, highlight: list[str]) -> str:
    """
    Build one ``<li>`` element for a publication dict as returned by
    ``scholarly.fill()``.  Falls back gracefully when optional fields are
    missing.
    """
    bib     = pub.get("bib", {})
    title   = html.escape(bib.get("title", "Untitled"))
    journal = html.escape(bib.get("journal") or bib.get("venue") or "")
    year    = html.escape(str(bib.get("pub_year", "")))
    authors_raw: list[str] = bib.get("author", [])
    if isinstance(authors_raw, str):
        # scholarly sometimes returns a single string
        authors_raw = [a.strip() for a in authors_raw.split(" and ")]

    # DOI / external link
    doi_url = pub.get("pub_url") or bib.get("url") or ""
    doi_url = doi_url.strip()

    author_html = _format_authors(authors_raw, highlight)

    if doi_url:
        title_html = f'<a href="{html.escape(doi_url)}"><b>{title}</b></a>'
    else:
        title_html = f"<b>{title}</b>"

    journal_html = f"<em>{journal}</em>" if journal else ""
    year_html    = f" (<b2>{year}</b2>)" if year else ""
    suffix       = f"{journal_html}{year_html}."

    return (
        f'\t\t<li style="margin-bottom: 12px">{title_html}<br>\n'
        f"\t\t\t{author_html} {suffix}\n"
        f"\t\t</li>"
    )


def fetch_publications(user_id: str) -> list[dict]:
    """
    Retrieve all publications from a Google Scholar profile, sorted newest
    first (by ``pub_year``).
    """
    from scholarly import scholarly  # import here so the module is optional at import time

    author = scholarly.search_author_id(user_id)
    author = scholarly.fill(author, sections=["publications"])

    pubs: list[dict] = []
    for stub in author.get("publications", []):
        time.sleep(REQUEST_DELAY)
        filled = scholarly.fill(stub)
        pubs.append(filled)

    # Sort descending by year; entries without a year sort last.
    def _year(p: dict) -> int:
        return int(p.get("bib", {}).get("pub_year", 0) or 0)

    pubs.sort(key=_year, reverse=True)
    return pubs


def build_publications_block(pubs: list[dict], highlight: list[str]) -> str:
    """Return the full HTML block (between markers, inclusive)."""
    items = "\n\n".join(_build_li(p, highlight) for p in pubs)
    return (
        f"{MARKER_START}\n"
        f'<p>\n'
        f'\t<ol type="1" reversed>\n\n'
        f"{items}\n\n"
        f"\t</ol>\n"
        f"</p>\n"
        f"{MARKER_END}"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--html",
        default="publications.html",
        help="Path to publications.html (default: publications.html)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated block without modifying the file.",
    )
    args = parser.parse_args()

    print(f"Fetching publications for Scholar user: {SCHOLAR_USER_ID} …")
    pubs = fetch_publications(SCHOLAR_USER_ID)
    print(f"  Retrieved {len(pubs)} publications.")

    block = build_publications_block(pubs, AUTHOR_HIGHLIGHT)

    if args.dry_run:
        print("\n--- Generated block ---\n")
        print(block)
        return

    with open(args.html, "r", encoding="utf-8") as fh:
        original = fh.read()

    pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
        re.DOTALL,
    )
    if not pattern.search(original):
        print(
            f"ERROR: markers not found in {args.html}.\n"
            f"  Expected: {MARKER_START!r} … {MARKER_END!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    updated = pattern.sub(block, original)
    if updated == original:
        print("No changes — publications list is already up to date.")
        return

    with open(args.html, "w", encoding="utf-8") as fh:
        fh.write(updated)
    print(f"Wrote updated publications list to {args.html}.")


if __name__ == "__main__":
    main()
