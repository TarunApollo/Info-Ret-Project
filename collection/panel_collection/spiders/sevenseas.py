import re

import scrapy

from panel_collection.records import clean_text, first_year, is_novel_title, series_record, series_title

_PROSE_FORMAT = re.compile(r"novel|audio|guide", re.IGNORECASE)


class SevenSeasSpider(scrapy.Spider):
    """Seven Seas Entertainment: one alphabetical series list, one page per series."""

    name = "sevenseas"
    allowed_domains = ["sevenseasentertainment.com"]
    start_urls = ["https://sevenseasentertainment.com/series-list/"]

    def parse(self, response):
        yield from response.follow_all(css='tr#volumes a[href*="/series/"]', callback=self.parse_series)

    def parse_series(self, response):
        content = response.css("#content")
        # <h2 class="topper">Series<span>:</span> Title</h2>
        title = series_title(content.xpath('.//h2[@class="topper"]/span/following-sibling::text()').get())
        if not title:
            self.logger.warning("No series title on %s", response.url)
            return

        # The list also holds light novels, audiobooks and art books. Each volume states its format.
        formats = content.css(".series-volume").re(r"<b>Format:</b>\s*([^<]+)")
        if is_novel_title(title) or (formats and all(_PROSE_FORMAT.search(fmt) for fmt in formats)):
            self.crawler.stats.inc_value("sevenseas/skipped_prose")
            return
        creators = content.css('#series-meta a[href*="/creator/"]::text').getall()
        genres = content.css('#series-meta a[rel="tag"]::text').getall()
        if not creators and not genres:
            self.crawler.stats.inc_value("sevenseas/skipped_not_a_series")  # e.g. the out-of-print archive
            return

        yield series_record(
            title=title,
            source_url=response.url,
            publisher="Seven Seas Entertainment",
            # "原題 | Romanized title"
            aliases=clean_text(content.css("#originaltitle::text").get()).split("|"),
            creators=creators,
            description=" ".join(
                clean_text(paragraph.xpath("string()").get())
                for paragraph in content.css(".series-description .entry p")
            ),
            genres=genres,
            debut_year=first_year(" ".join(content.css("#copyright ::text").getall())),
        )
