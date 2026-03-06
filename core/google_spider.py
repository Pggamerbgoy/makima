import json
import urllib.parse
import scrapy
from scrapy.crawler import CrawlerProcess

class DDGLiteSpider(scrapy.Spider):
    name = "ddg_lite"
    
    def __init__(self, query="", output_file="search_results.json", *args, **kwargs):
        super(DDGLiteSpider, self).__init__(*args, **kwargs)
        self.query = query
        self.output_file = output_file
        self.results = []
        
    def start_requests(self):
        url = "https://lite.duckduckgo.com/lite/"
        # DuckDuckGo Lite uses a POST request for the search
        yield scrapy.FormRequest(
            url=url,
            formdata={"q": self.query},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0"},
            callback=self.parse
        )

    def parse(self, response):
        # Extract snippets from the result table
        snippets = response.css('td.result-snippet')
        for s in snippets:
            clean = " ".join(s.css('::text').getall()).replace('  ', ' ').strip()
            if clean:
                self.results.append(clean)
                
    def close(self, reason):
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results[:5], f)

if __name__ == "__main__":
    import sys
    import logging
    # Suppress verbose scrapy output
    logging.getLogger('scrapy').propagate = False
    
    query = sys.argv[1] if len(sys.argv) > 1 else "python 3.12 release date"
    output = sys.argv[2] if len(sys.argv) > 2 else "search_results.json"
    
    process = CrawlerProcess(settings={
        "LOG_LEVEL": "ERROR",
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0"
    })
    process.crawl(DDGLiteSpider, query=query, output_file=output)
    process.start()
