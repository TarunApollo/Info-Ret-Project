import re

import scrapy

from panel_collection.records import clean_text, is_novel_title, series_record, series_title

_AJAX = {"X-Requested-With": "XMLHttpRequest"}
# Credits that name the people who made the story; translators and letterers are left out.
_CREATOR_ROLE = re.compile(r"author|artist|creat|illustrat|adapt", re.IGNORECASE)
_VOLUME_NUMBER = re.compile(r"\bVol(?:ume|\.)?\s*(\d+)", re.IGNORECASE)


class YenPressSpider(scrapy.Spider):
    """Yen Press: paged series lists, a series page, then its first volume for genres."""

    name = "yenpress"
    allowed_domains = ["yenpress.com"]
    # "comics" holds the Ize Press manhwa and original graphic novels.
    start_urls = [
        "https://yenpress.com/category/manga/all/series",
        "https://yenpress.com/category/comics/all/series",
    ]

    def parse(self, response):
        yield from response.follow_all(css='a[href^="/series/"]', callback=self.parse_series)
        more = response.css("a.show-more::attr(data-url)").get()
        if more:
            yield response.follow(more, callback=self.parse, headers=_AJAX)

    def parse_series(self, response):
        title = series_title(response.css("h1.heading::text").get())
        if not title:
            self.logger.warning("No series title on %s", response.url)
            return
        if is_novel_title(title):
            self.crawler.stats.inc_value("yenpress/skipped_prose")
            return

        series = {
            "title": title,
            "source_url": response.url,
            "creators": self._creators(response),
            # Blurb of the featured volume; replaced by the first volume's when one is found.
            "description": self._blurb(response),
        }
        yield from self._follow_volumes(response, response.css("#volumes-list"), series, [])

    def parse_more_volumes(self, response, series, volumes):
        yield from self._follow_volumes(response, response, series, volumes)

    def _follow_volumes(self, response, listing, series, volumes):
        """Collect the volume links in `listing`; long series continue on AJAX pages."""
        for link in listing.css('a[href^="/titles/"]'):
            name = clean_text(link.css("p span::text").get())
            if name:
                volumes.append((name, link.attrib["href"]))
        more = listing.css("a.show-more::attr(data-url)").get()
        if more:
            yield response.follow(
                more,
                callback=self.parse_more_volumes,
                headers=_AJAX,
                cb_kwargs={"series": series, "volumes": volumes},
            )
        elif volumes:
            yield response.follow(self._first_volume(volumes), callback=self.parse_volume, cb_kwargs={"series": series})
        else:
            yield self._record(series)

    def parse_volume(self, response, series):
        genres = [clean_text(genre) for genre in response.css(".detail-labels.desktop-only a::text").getall()]
        if "Art Book" in genres:
            self.crawler.stats.inc_value("yenpress/skipped_art_book")
            return
        series["genres"] = genres
        # Some series pages omit the credits that their volume pages carry.
        series["creators"] = series["creators"] or self._creators(response)
        series["description"] = self._blurb(response) or series["description"]
        yield self._record(series)

    @staticmethod
    def _creators(response):
        return [
            credit.css("span::text").get()
            for credit in response.css(".story-details.desktop-only p")
            if _CREATOR_ROLE.search(credit.xpath("text()").get(""))
        ]

    @staticmethod
    def _first_volume(volumes):
        def number(volume):
            match = _VOLUME_NUMBER.search(volume[0])
            return int(match.group(1)) if match else float("inf")

        # Volumes are listed newest first, so unnumbered lists fall back to the last entry.
        return min(reversed(volumes), key=number)[1]

    @staticmethod
    def _blurb(response):
        return " ".join(response.css(".content-heading-txt")[:1].css("p.paragraph ::text").getall())

    @staticmethod
    def _record(series):
        return series_record(publisher="Yen Press", **series)
