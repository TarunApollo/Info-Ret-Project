BOT_NAME = "panel_collection"
SPIDER_MODULES = ["panel_collection.spiders"]
NEWSPIDER_MODULE = "panel_collection.spiders"

USER_AGENT = "panel_collection (USI Information Retrieval course project)"
ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 1.0
FEED_EXPORT_ENCODING = "utf-8"
TELNETCONSOLE_ENABLED = False
REMOTE_CONTROL_ENABLED = False

# Only used with `-s HTTPCACHE_ENABLED=1` while developing a spider: never cache a
# throttled or failed response, or the retry would be answered from the cache.
HTTPCACHE_IGNORE_HTTP_CODES = [403, 408, 429, 500, 502, 503, 504]
