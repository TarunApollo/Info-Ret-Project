from pathlib import Path

import scrapy


class SampleCatalogSpider(scrapy.Spider):
    """Read the in-repo fixture without making any external requests."""

    name = "panel_sample"
    start_urls = [(Path(__file__).resolve().parents[2] / "fixtures" / "manga.html").as_uri()]
    custom_settings = {"ROBOTSTXT_OBEY": False}

    def parse(self, response):
        for series in response.css("article[data-id]"):
            year = series.attrib.get("data-year")
            yield {
                "id": series.attrib["data-id"],
                "title": series.css("h2::text").get(),
                "aliases": series.css(".alias::text").getall(),
                "creator": series.css(".creator::text").get(),
                "description": series.css(".description::text").get(),
                "genres": series.css(".genre::text").getall(),
                "publisher": series.css(".publisher::text").get(),
                "debut_year": int(year) if year else None,
                "source_urls": series.css("a.source::attr(href)").getall(),
            }
