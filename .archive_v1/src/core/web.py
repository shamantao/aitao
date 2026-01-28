import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
# Import du nouveau système de log
try:
    from src.core.logger import get_logger
except ImportError:
    import logging
    def get_logger(name, log_filename=None): return logging.getLogger(name)

logger = get_logger("web_search", "web_search.log")

# Tentative d'import Tavily
try:
    from tavily import TavilyClient
    HAS_TAVILY = True
    logger.info("✅ Tavily Library imported successfully")
except ImportError:
    HAS_TAVILY = False
    logger.warning("⚠️ Tavily Library NOT found")

def format_source_output(results, source_type="Web"):
    """
    Formate les résultats pour l'injection dans le contexte LLM.
    Style PERPLEXITY : [1] Titre - URL
    """
    if not results:
        return f"Aucun résultat trouvé ({source_type})."
        
    summary = f"Sources ({source_type}):\n"
    for i, r in enumerate(results, 1):
        summary += f"[{i}] {r['title']}\n"
        summary += f"    URL: {r['href']}\n"
        summary += f"    Contenu: {r['body']}\n\n"
    return summary

def search_tavily(query: str, max_results=5):
    """Recherche via l'API Tavily (Optimisé pour LLM)."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        logger.warning("⚠️ SKIPPING TAVILY: No API Key found in env")
        return None
        
    try:
        logger.info(f"🌍 Starting Tavily Search for: '{query}'")
        client = TavilyClient(api_key=api_key)
        response = client.search(query, search_depth="basic", max_results=max_results)
        
        # Mapping format commun
        results = []
        raw_results = response.get("results", [])
        logger.info(f"✅ Tavily success: Found {len(raw_results)} results")
        
        for r in raw_results:
            results.append({
                "title": r.get("title"),
                "href": r.get("url"),
                "body": r.get("content")
            })
        return results
    except Exception as e:
        logger.error(f"❌ Tavily Error: {str(e)}")
        return None

def search_ddg_html(query: str, max_results=10) -> list:
    """
    Fallback Manuel : Scrape html.duckduckgo.com.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://duckduckgo.com/"
    }
    
    encoded_query = quote_plus(query)
    # kl=fr-fr force la région France
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}&kl=fr-fr"
    
    logger.info(f"🌍 Fallback DDG HTML: GET {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        logger.info(f"DDG HTTP Status: {resp.status_code}")
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"⚠️ Erreur Request DDG: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    
    for result in soup.find_all("div", class_="result"):
        try:
            title_tag = result.find("a", class_="result__a")
            if not title_tag:
                continue
                
            title = title_tag.get_text(strip=True)
            href = title_tag.get("href")
            
            snippet_tag = result.find("a", class_="result__snippet")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            
            if href and title:
                results.append({"title": title, "href": href, "body": snippet})
                
            if len(results) >= max_results:
                break
        except Exception:
            continue
            
    logger.info(f"✅ DDG success: Parsed {len(results)} results")
    return results

def web_search_struct(query: str, max_results=10) -> list:
    """Retourne la liste brute des résultats (titre, href, body)."""
    results = None
    
    # 1. Tavily
    if HAS_TAVILY:
        results = search_tavily(query, max_results=max_results)
        if results:
            return results
        else:
            logger.info("⚠️ Tavily returned no results or failed, falling back to DDG")
            
    # 2. Fallback DDG
    if not results:
        results = search_ddg_html(query, max_results=max_results)
    
    return results

def web_search(query: str, max_results=10) -> str:
    """
    Stratégie Hybride (Retourne STR formaté pour rétrocompatibilité).
    """
    results = web_search_struct(query, max_results)
    if results:
        return format_source_output(results, source_type="Web Search")
            
    return "Aucun résultat trouvé sur le web."
