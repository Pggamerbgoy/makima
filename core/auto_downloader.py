import os
import urllib.parse
from pathlib import Path
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.pipelines.files import FilesPipeline
import logging

class MakimaFilesPipeline(FilesPipeline):
    """Custom FilesPipeline to store files nicely."""
    def file_path(self, request, response=None, info=None, *, item=None):
        original_path = super().file_path(request, response, info, item=item)
        ext = os.path.splitext(original_path)[1]
        
        # Sometimes Scrapy fails to extract an extension if it's hidden behind query params
        if not ext and response:
            content_type = response.headers.get(b'Content-Type', b'').decode('utf-8').lower()
            if 'pdf' in content_type: ext = '.pdf'
            elif 'jpeg' in content_type or 'jpg' in content_type: ext = '.jpg'
            elif 'png' in content_type: ext = '.png'
            elif 'zip' in content_type: ext = '.zip'
            elif 'exe' in content_type: ext = '.exe'
            elif 'json' in content_type: ext = '.json'
        
        if not ext and item and 'expected_ext' in item:
            ext = f".{item['expected_ext']}"

        if item and 'filename' in item:
            return f"{item['filename']}{ext}"
        return original_path

class DownloadSpider(scrapy.Spider):
    name = "download_spider"

    def __init__(self, query="", file_type="", *args, **kwargs):
        super(DownloadSpider, self).__init__(*args, **kwargs)
        self.query = query
        self.file_type = file_type.lower()
        self.downloaded_count = 0

    def start_requests(self):
        # We search DDG HTML for exact filetypes if requested
        search_q = self.query
        if self.file_type and self.file_type not in search_q.lower():
            if self.file_type in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']:
                search_q += f" ext:{self.file_type}"
            else:
                search_q += f" {self.file_type}"

        url = "https://html.duckduckgo.com/html/"
        yield scrapy.FormRequest(
            url=url,
            formdata={"q": search_q},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0"},
            callback=self.parse_search
        )

    def parse_search(self, response):
        results = response.css('a.result__url::attr(href)').getall()
        
        valid_urls = []
        for raw_url in results:
            # Decode DDG tracking URLs
            if 'uddg=' in raw_url:
                parsed = urllib.parse.urlparse(raw_url)
                params = urllib.parse.parse_qs(parsed.query)
                if 'uddg' in params:
                    actual_url = params['uddg'][0]
                    valid_urls.append(actual_url)
            else:
                if raw_url.startswith('http'):
                    valid_urls.append(raw_url)

        # Yield items for the FilesPipeline
        MAX_URLS = 3 # Download top 3 to be safe
        for i, target_url in enumerate(valid_urls[:MAX_URLS]):
            safe_name = "".join(c if c.isalnum() else "_" for c in self.query)
            yield {
                'file_urls': [target_url],
                'filename': f"{safe_name}_{i+1}"
            }

def download_files_sync(query: str, category: str, file_type: str, download_dir: str):
    """
    Run Scrapy download pipeline synchronously.
    Saves to the specified download_dir.
    """
    logging.getLogger('scrapy').propagate = False
    
    process = CrawlerProcess(settings={
        "LOG_LEVEL": "ERROR",
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0",
        "ITEM_PIPELINES": {'core.auto_downloader.MakimaFilesPipeline': 1},
        "FILES_STORE": download_dir,
        "MEDIA_ALLOW_REDIRECTS": True,
        "DOWNLOAD_TIMEOUT": 15,
        "ROBOTSTXT_OBEY": False
    })
    
    process.crawl(DownloadSpider, query=query, file_type=file_type)
    process.start()
