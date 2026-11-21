# Manga Search

Information Retrieval course project by Tarun, Ale, and Jeffre. See [the assignment brief](project_desc.pdf) for requirements and deadlines.

## Shared baseline

The development baseline runs from a local Scrapy fixture through Solr to Panel. It supports browsing, title search, and opening series details and source links. Use that pipeline to connect at least three crawl sources for the final prototype.

Agree on the manga record format and the search response before building the three parts. At minimum, the interface needs a stable ID, title, creator, description, and source links. Include genre, publisher, and debut year where available for filtering.

### Proposed baseline work split

| Person | Baseline work |
| --- | --- |
| Ale | `collection/` · Lead the Scrapy collection and normalize manga records with source links. |
| Tarun | `public/` · Lead UI and UX decisions, including the Panel theme and the search, browse, and series detail flows. |
| Jeffre | `retrieval/` · Set up the Solr index and search response with Tarun, and coordinate usability testing with three classmates. |

## Feature plan

We will build four features. Each teammate owns one simple feature, and all three teammates build automatic recommendations together.

### Three simple features

| Person | Feature |
| --- | --- |
| Ale | **Filtering.** Let readers narrow title-search results by at least three attributes. Start with genre, publisher, and debut decade and verify coverage in the collected records. |
| Tarun | **Result snippets.** Show up to three lines from each result with matching query terms highlighted. |
| Jeffre | **Tabular results.** Show one manga series per row with columns for title, creator, and genre. |

### One shared complex feature

**Automatic recommendations.** Suggest similar manga alongside search results and explain why the system selected them.


## Local setup and architecture

Follow the [architecture and handoff guide](ARCHITECTURE.md) to run the shared baseline, understand the folder hierarchy, and find where each feature plugs in.
