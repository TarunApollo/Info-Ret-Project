import re
from datetime import date

import scrapy

from panel_collection.records import clean_text, series_record, series_title

_MANGA_PRODUCT = re.compile(r"^(/manga-books/manga/([^/]+)/product/\d+)")
_VOLUME_SUFFIX = re.compile(r"-volume-\d.*$")
_VOLUME_NUMBER = re.compile(r",?\s+Vol(?:ume|\.)\s*\d+.*$")
# The volume page's detail row that reads "Story and Art by ...".
_CREDIT_ROW = 'string(//div[contains(@class, "mar-b-md")][strong[contains(normalize-space(), " by")]])'
_CLAUSE = re.compile(r"\s*[,;]\s*")
_ROLE = re.compile(r"^(?:.*\s)?by\s+|^[^:]*:\s*", re.IGNORECASE)
_SOURCE_NOTE = re.compile(r"based on|with the\b", re.IGNORECASE)
_NAME_SEPARATOR = re.compile(r"\s*(?:&|\band\b|\bwith\b)\s*")


def credit_names(credit):
    """"Story by A, Art by B & C; Based on the novel by D" -> ["A", "B", "C", "D"]."""
    names = []
    for clause in _CLAUSE.split(credit):
        role = _ROLE.match(clause)
        if role:
            clause = clause[role.end() :]
        elif _SOURCE_NOTE.match(clause):
            continue  # "Based on Bram Stoker’s Dracula" credits a work, not a person
        # A clause without a role continues the previous list: "By A, B and C".
        names += _NAME_SEPARATOR.split(clause)
    return names


class VizSpider(scrapy.Spider):
    """VIZ Media: release calendar -> one volume per series -> series page.

    robots.txt disallows the paged series lists ("/*/more"), so series are discovered
    through the monthly release calendar, which links every volume VIZ has published.
    """

    name = "viz"
    allowed_domains = ["www.viz.com"]
    # robots.txt asks for a 2 s crawl delay, but www.viz.com answered 429 once a crawl passed
    # about 10 requests in 30 s. A fixed 3.25 s stays under that; retries outlast the window.
    custom_settings = {
        "DOWNLOAD_DELAY": 3.25,
        "DOWNLOAD_DELAY_JITTER": 0,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "RETRY_TIMES": 10,
    }
    months_ahead = 6  # announced releases

    def __init__(self, first_year=2002, **kwargs):
        """`-a first_year=2024` shortens a test crawl; the calendar is empty before 2003."""
        super().__init__(**kwargs)
        self.first_year = int(first_year)
        self.seen_series_slugs = set()

    async def start(self):
        today = date.today()
        last = today.year * 12 + today.month - 1 + self.months_ahead
        for index in range(self.first_year * 12, last + 1):
            # Oldest month first and ahead of volume pages, so the volume fetched for a
            # series is its earliest release.
            yield scrapy.Request(
                f"https://www.viz.com/calendar/{index // 12}/{index % 12 + 1}", priority=last - index + 1
            )

    def parse(self, response):
        for href in response.css('article a[href*="/product/"]::attr(href)').getall():
            match = _MANGA_PRODUCT.match(href)
            if not match:
                continue  # anime, novels, art books
            # Every volume links to its series, so one volume per series is enough.
            slug = _VOLUME_SUFFIX.sub("", match.group(2))
            if slug not in self.seen_series_slugs:
                self.seen_series_slugs.add(slug)
                yield response.follow(match.group(1), callback=self.parse_product)

    def parse_product(self, response):
        credit = clean_text(response.xpath(_CREDIT_ROW).get())
        blurb = " ".join(response.css("div.row.pad-b-xl div.text-spacing p ::text").getall())
        series = response.xpath('//strong[normalize-space()="Series"]/following-sibling::a/@href').get()
        if series:
            # Some series pages carry no credit or description; the volume page then supplies them.
            yield response.follow(
                series, callback=self.parse_series, cb_kwargs={"volume_credit": credit, "volume_blurb": blurb}
            )
            return

        # A series without a series page is described by its volume page alone.
        heading = clean_text(response.xpath('string(//h2[contains(@class, "type-lg")])').get())
        title = series_title(_VOLUME_NUMBER.sub("", heading))
        if not title:
            self.logger.warning("No volume title on %s", response.url)
            return
        self.crawler.stats.inc_value("viz/series_from_volume_page")
        yield series_record(
            title=title,
            source_url=response.url,
            publisher="VIZ Media",
            creators=credit_names(credit),
            description=blurb,
        )

    def parse_series(self, response, volume_credit, volume_blurb):
        intro = response.css("#series-intro")
        title = series_title(intro.css("#page_title::text").get())
        if not title:
            self.logger.warning("No series title on %s", response.url)
            return
        credit = clean_text(intro.css("div.type-rg > span.disp-bl--bm::text").get()) or volume_credit
        tagline = intro.css("#page_title + p::text").get("")
        more_about = clean_text(" ".join(intro.css("#series-intro-jump p ::text").getall()))
        yield series_record(
            title=title,
            source_url=response.url,
            publisher="VIZ Media",
            creators=credit_names(credit),
            description=f"{tagline} {more_about or volume_blurb}",
            # The highlighted first label is the imprint; the others are genres.
            genres=intro.css("div.flex--lg > div:first-child a:not(.bg-yellow)::text").getall(),
        )
