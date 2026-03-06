"""
agents/web_agent.py
Web search and page fetching for Makima.
"""

import logging
import webbrowser

logger = logging.getLogger("Makima.WebAgent")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


class WebAgent:

    SEARCH_URL = "https://www.google.com/search?q="
    DDGS_URL = "https://api.duckduckgo.com/"

    def __init__(self, ai):
        self.ai = ai

    def search(self, query: str) -> str:
        """Fetch search results and synthesize answer using AI, avoiding browser popups."""
        if not REQUESTS_AVAILABLE or not BS4_AVAILABLE:
            # Fallback: open browser if libraries are missing
            url = self.SEARCH_URL + query.replace(" ", "+")
            webbrowser.open(url)
            return f"Opened Google search for '{query}' in your browser (missing requests/bs4 text scraping)."

        # Try API first for quick facts
        try:
            resp = requests.get(
                self.DDGS_URL,
                params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1},
                timeout=5,
                headers={"User-Agent": "Makima/1.0"},
            )
            data = resp.json()
            result = data.get("AbstractText") or data.get("Answer")
            if result and len(result) > 20:
                return result
        except Exception as e:
            logger.debug(f"DDG API error: {e}")

        # Deep Search via Scrapy Spider
        try:
            import subprocess
            import tempfile
            import os
            import json
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                out_path = tmp.name
                
            spider_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "google_spider.py")
            
            # Prevent cmd window flash on Windows
            creationflags = 0
            if os.name == 'nt':
                creationflags = subprocess.CREATE_NO_WINDOW
                
            subprocess.run(["python", spider_path, query, out_path], capture_output=True, timeout=15, creationflags=creationflags)
            
            snippets = []
            if os.path.exists(out_path):
                try:
                    with open(out_path, "r", encoding="utf-8") as f:
                        snippets = json.load(f)
                except Exception:
                    pass
                os.remove(out_path)
            
            if not snippets:
                url = self.SEARCH_URL + query.replace(" ", "+")
                webbrowser.open(url)
                return f"I couldn't scrape results with Scrapy, so I opened Chrome for: {query}"

            # Synthesize answer with AI
            context = "\n".join(f"- {s}" for s in snippets[:3])
            prompt = (
                f"Please concisely summarize the answer to my query based on these search results.\n"
                f"Query: '{query}'\n"
                f"Search Results:\n{context}"
            )

            if self.ai:
                summary_result = self.ai.chat(prompt)
                summary = summary_result[0] if isinstance(summary_result, tuple) else str(summary_result)
                
                # Local models might ignore prompt and just greet the user. Detect this.
                lower_sum = summary.lower()
                if "darling" in lower_sum or "listening" in lower_sum or len(summary) < 30 or "help you" in lower_sum:
                    return f"Search Results:\n1. {snippets[0]}\n2. {snippets[1] if len(snippets)>1 else ''}"
                
                return summary
            
        except Exception as e:
            logger.error(f"Search Scrapy scraping failed: {e}")
            url = self.SEARCH_URL + query.replace(" ", "+")
            webbrowser.open(url)
            return f"Scrapy failed, opening browser instead. Error: {e}"

    def fetch_summary(self, url: str) -> str:
        """Fetch a page and summarize it with AI."""
        if not REQUESTS_AVAILABLE or not BS4_AVAILABLE:
            return "requests/beautifulsoup4 not installed. Can't fetch pages."
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            # Get main text content
            paragraphs = soup.find_all("p")
            text = " ".join(p.get_text() for p in paragraphs[:10])
            text = text[:2000]

            prompt = (
                "Summarize the following web page content in 3 concise sentences. "
                "Focus on the main ideas only.\n\n"
                f"{text}"
            )

            # Prefer a plain-text generation API when available (AIHandler)
            if hasattr(self.ai, "generate_response"):
                try:
                    return self.ai.generate_response(
                        system_prompt="You are a summarization assistant.",
                        user_message=prompt,
                        temperature=0.2,
                    )
                except Exception:
                    pass

            result = self.ai.chat(prompt)
            # AIHandler.chat → (reply, emotion); legacy backends may return str
            if isinstance(result, tuple) and len(result) >= 1:
                return result[0]
            return str(result)
        except Exception as e:
            return f"Couldn't fetch that page: {e}"
