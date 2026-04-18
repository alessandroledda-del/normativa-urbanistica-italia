import argparse
import asyncio
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Sys path injection para root imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ingestion import process_and_ingest_file

class MemoryUploadFile:
    """Mock for FastAPI UploadFile to pass directly into our ingestion pipeline."""
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.content = content
        
    async def read(self):
        return self.content

async def scrape_and_ingest(url: str, commune: str, province: str, region: str):
    print(f"[*] Inizio scraping dell'albo/portale: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"[!] Errore connessione URL: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=True)
    
    # Keywords tipiche per Norme Tecniche di Attuazione
    keywords = ["nta", "norme", "tecniche", "regolamento", "edilizio", "attauzione", "variante"]
    
    pdf_links = []
    for link in links:
        href = link['href']
        text = link.get_text().lower()
        if href.lower().endswith(".pdf") or "pdf" in href.lower() or "download" in href.lower():
            if any(kw in text for kw in keywords) or any(kw in href.lower() for kw in keywords):
                full_url = urljoin(url, href)
                if full_url not in pdf_links:
                    pdf_links.append(full_url)
    
    if not pdf_links:
        print("[*] Nessun documento PDF pertinente trovato nella pagina base.")
        return
        
    print(f"[*] Trovati {len(pdf_links)} documenti potenzialmente pertinenti. Inizio download...")
    
    metadata = {
        "level": "comunale",
        "region": region,
        "province": province,
        "commune": commune
    }
    
    for pdf_url in pdf_links:
        print(f"   -> Scarico {pdf_url} ...")
        try:
            pdf_resp = requests.get(pdf_url, timeout=20)
            pdf_bytes = pdf_resp.content
            
            # Extract basic filename from URL or use a generic one
            filename = pdf_url.split("/")[-1]
            if not filename.endswith(".pdf"):
                filename += ".pdf"
            
            mock_file = MemoryUploadFile(filename, pdf_bytes)
            
            print(f"   -> Avvio Ingestion (Metadata: {commune})...")
            await process_and_ingest_file(mock_file, metadata)
            print("   [OK] Inserito nel VectorStore con successo!")
            
        except Exception as e:
            print(f"   [!] Errore processando {pdf_url}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Scraper per Normative Urbanistiche (PGT/NTA)")
    parser.add_argument("url", help="L'URL della pagina web da scansionare (es. Albo Pretorio o Trasparenza)")
    parser.add_argument("--commune", required=True, help="Nome del comune a cui assegnare le delibere")
    parser.add_argument("--province", required=True, help="Provincia del comune")
    parser.add_argument("--region", required=True, help="Regione del comune")
    
    args = parser.parse_args()
    
    # Esegue l'async loop
    asyncio.run(scrape_and_ingest(args.url, args.commune, args.province, args.region))
