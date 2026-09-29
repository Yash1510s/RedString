from typing import Any, Dict, List, Tuple
from bs4 import BeautifulSoup
import httpx


class TechnologyCollector:
    """
    Passive HTTP/HTML OSINT Technology Collector.
    Inspects HTTP headers and HTML metadata to passively observe web technologies.
    """

    def __init__(self, timeout: float = 6.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _detect_from_headers(self, headers: httpx.Headers) -> List[Dict[str, str]]:
        detections = []

        # Server header
        server = headers.get("Server")
        if server:
            detections.append({
                "name": server.split("/")[0].strip(),
                "basis": f"Server HTTP header ('Server: {server}')",
            })

        # X-Powered-By header
        powered_by = headers.get("X-Powered-By")
        if powered_by:
            detections.append({
                "name": powered_by.split("/")[0].strip(),
                "basis": f"X-Powered-By HTTP header ('X-Powered-By: {powered_by}')",
            })

        # Via header
        via = headers.get("Via")
        if via:
            detections.append({
                "name": f"Proxy ({via})",
                "basis": f"Via HTTP header ('Via: {via}')",
            })

        # X-Generator header
        generator = headers.get("X-Generator")
        if generator:
            detections.append({
                "name": generator.strip(),
                "basis": f"X-Generator HTTP header ('X-Generator: {generator}')",
            })

        return detections

    def _detect_from_html(self, html_text: str) -> List[Dict[str, str]]:
        detections = []
        html_lower = html_text.lower()

        # Meta generator tag
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            meta_gen = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "generator"})
            if meta_gen and meta_gen.get("content"):
                gen_content = meta_gen["content"].strip()
                detections.append({
                    "name": gen_content,
                    "basis": f"<meta name='generator'> HTML tag ('{gen_content}')",
                })
        except Exception:
            pass

        # Technology patterns
        patterns = [
            ("/_next/", "Next.js", "HTML indicator ('/_next/' static asset path)"),
            ("/wp-content/", "WordPress", "HTML indicator ('/wp-content/' theme/plugin path)"),
            ("react", "React", "HTML/JS framework indicator ('react' reference)"),
            ("vue", "Vue.js", "HTML/JS framework indicator ('vue' reference)"),
            ("angular", "Angular", "HTML/JS framework indicator ('angular' reference)"),
            ("bootstrap", "Bootstrap", "HTML/CSS framework indicator ('bootstrap' stylesheet/class)"),
            ("tailwind", "Tailwind CSS", "HTML/CSS framework indicator ('tailwind' stylesheet/class)"),
            ("jquery", "jQuery", "HTML/JS library indicator ('jquery' script)"),
            ("shopify", "Shopify", "HTML platform indicator ('shopify' script/asset)"),
            ("cloudflare", "Cloudflare", "HTML indicator ('cloudflare' script/asset)"),
        ]

        for needle, name, basis in patterns:
            if needle in html_lower:
                # Avoid duplicate technology names
                if not any(d["name"].lower() == name.lower() for d in detections):
                    detections.append({"name": name, "basis": basis})

        return detections

    def collect(self, domain: str) -> Dict[str, Any]:
        """
        Attempts HTTPS then HTTP request to domain to extract technologies.
        """
        findings: List[Dict[str, str]] = []
        errors: Dict[str, str] = {}
        successful_url = None

        urls_to_try = [f"https://{domain}", f"http://{domain}"]

        with httpx.Client(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
            for url in urls_to_try:
                try:
                    response = client.get(url)
                    if response.status_code < 400 or response.status_code == 403:
                        successful_url = str(response.url)
                        
                        # Inspect headers
                        header_detections = self._detect_from_headers(response.headers)
                        findings.extend(header_detections)

                        # Inspect HTML
                        html_detections = self._detect_from_html(response.text)
                        for d in html_detections:
                            if not any(existing["name"].lower() == d["name"].lower() for existing in findings):
                                findings.append(d)
                        
                        break  # Stop trying fallback URLs once we get a response
                except (httpx.TimeoutException, httpx.RequestError) as e:
                    errors[url] = str(e)
                except Exception as e:
                    errors[url] = str(e)

        if not successful_url and errors:
            errors["http"] = f"Failed to connect to {domain} over HTTPS/HTTP."

        return {
            "collector": "technology_detection",
            "target": domain,
            "findings": findings,
            "errors": errors,
        }
