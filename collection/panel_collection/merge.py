"""Merge per-source spider exports into one catalog and report on its quality.

Usage: python -m panel_collection.merge -o data/catalog.json SOURCE.json [SOURCE.json ...]

Sources are merged in the order given: on conflicting single-valued fields, earlier files win.
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from panel_collection.records import ID_MAX_LENGTH, slugify, unique

_NAME_WORD = re.compile(r"[^\W\d_]{2,}")
_FILTER_FIELDS = ("genres", "publisher", "debut_year")


def creator_words(record):
    return set(_NAME_WORD.findall(record["creator"].casefold())) - {"and"}


def same_series(words, other_words):
    """Records sharing a title are one series unless both name creators with nothing in common."""
    return not words or not other_words or bool(words & other_words)


def merge_into(target, record):
    """Fold `record` into `target`, which comes from an earlier source."""
    target["aliases"] = [
        alias
        for alias in unique([*target["aliases"], record["title"], *record["aliases"]])
        if alias.casefold() != target["title"].casefold()
    ]
    for field in ("creator", "description", "publisher"):
        target[field] = target[field] or record[field]
    target["genres"] = sorted({*target["genres"], *record["genres"]})
    years = [year for year in (target["debut_year"], record["debut_year"]) if year is not None]
    target["debut_year"] = min(years, default=None)
    target["source_urls"] = list(dict.fromkeys([*target["source_urls"], *record["source_urls"]]))


def merge_catalog(records):
    """Return (catalog, merged, split).

    `merged` lists catalog records built from several source records. `split` lists records
    that share a title with a different series and therefore received a publisher-suffixed ID.
    """
    by_id = defaultdict(list)  # title slug -> [(record, creator words, source record count)]
    for record in records:
        words = creator_words(record)
        for entry in by_id[record["id"]]:
            if same_series(entry[1], words):
                merge_into(entry[0], record)
                entry[1] |= words
                entry[2] += 1
                break
        else:
            by_id[record["id"]].append([dict(record), words, 1])

    catalog, merged, split = {}, [], []
    for base_id, entries in by_id.items():
        for position, (record, _, count) in enumerate(entries):
            if position:
                record["id"] = _free_id(base_id, record["publisher"], {*catalog, *by_id})
                split.append(record)
            if count > 1:
                merged.append(record)
            catalog[record["id"]] = record
    return sorted(catalog.values(), key=lambda record: record["id"]), merged, split


def _free_id(base_id, publisher, taken):
    suffix = slugify(publisher) if publisher else "other"
    number = 1
    while True:
        tail = f"-{suffix}" if number == 1 else f"-{suffix}-{number}"
        candidate = base_id[: ID_MAX_LENGTH - len(tail)].rstrip("-") + tail
        if candidate not in taken:
            return candidate
        number += 1


def filled(record, field):
    return record[field] not in ("", [], None)


def report(sources, catalog, merged, split):
    lines = ["Records per source file"]
    lines += [f"  {len(records):5}  {path}" for path, records in sources]
    lines.append(f"  {sum(len(records) for _, records in sources):5}  total in, {len(catalog)} in the merged catalog")

    lines.append(f"\nDuplicate titles merged into one record: {len(merged)}")
    lines += [f"  {record['id']}: {', '.join(record['source_urls'])}" for record in merged]
    lines.append(f"\nSame title, different creators, kept apart: {len(split)}")
    lines += [f"  {record['id']}: {record['title']} ({record['creator']})" for record in split]

    publishers = Counter(record["publisher"] or "(none)" for record in catalog)
    fields = ("creator", "description", *_FILTER_FIELDS)
    lines.append("\nField coverage, percent of records with a value")
    lines.append(f"  {'publisher':28}{'records':>8}" + "".join(f"{field:>13}" for field in fields))
    for name in [*sorted(publishers), None]:
        group = [record for record in catalog if name is None or (record["publisher"] or "(none)") == name]
        shares = "".join(f"{100 * sum(filled(r, f) for r in group) / len(group):12.1f}%" for f in fields)
        lines.append(f"  {name or 'all':28}{len(group):8}{shares}")

    genres = Counter(genre for record in catalog for genre in record["genres"])
    lines.append(f"\nGenres: {len(genres)} distinct")
    lines.append("  " + ", ".join(f"{genre} {count}" for genre, count in genres.most_common()))
    decades = Counter(record["debut_year"] // 10 * 10 for record in catalog if record["debut_year"] is not None)
    lines.append("\nDebut decades")
    lines.append("  " + ", ".join(f"{decade}s {count}" for decade, count in sorted(decades.items())))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("sources", nargs="+", type=Path, help="spider exports, highest priority first")
    parser.add_argument("-o", "--output", required=True, type=Path, help="merged catalog to write")
    args = parser.parse_args()

    sources = [(path, json.loads(path.read_text(encoding="utf-8"))) for path in args.sources]
    catalog, merged, split = merge_catalog(record for _, records in sources for record in records)

    # One record per line keeps catalog diffs readable.
    rows = ",\n".join(json.dumps(record, ensure_ascii=False) for record in catalog)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"[\n{rows}\n]\n", encoding="utf-8")
    print(report(sources, catalog, merged, split))


if __name__ == "__main__":
    main()
