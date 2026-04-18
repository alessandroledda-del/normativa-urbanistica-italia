import argparse
import asyncio
import os
import requests
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

# Sys path injection
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ingestion import process_and_ingest_file

class MemoryUploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.content = content
        
    async def read(self):
        return self.content

async def autonomous_crawler(query: str, commune: str, province: str, region: str, max_results: int = 5):
    print(f"[*] Inizio ricerca autonoma: '{query}'")
    
    # Inizializza cercatore
    ddg = DuckDuckGoSearchAPIWrapper(region="it-it", max_results=max_results * 5) # search more to find PDFs
    try:
        # Aggiungiamo filetype pdf in modo generico (DDG supporta parzialmente le query ext:pdf)
        search_query = f"{query} ext:pdf"
        results = ddg.results(search_query, max_results=max_results * 2)
    except Exception as e:
        print(f"[!] Errore modulo di ricerca: {e}")
        return

    pdf_links = []
    for r in results:
        link = r.get("link", "")
        if link.lower().endswith(".pdf"):
            if link not in pdf_links:
                pdf_links.append(link)
                
    if not pdf_links:
        print("[!] Nessun file PDF diretto trovato per questa ricerca.")
        return

    # Limita ai max results voluti
    pdf_links = pdf_links[:max_results]
    print(f"[*] Trovati {len(pdf_links)} documenti conformi.")

    metadata = {
        "level": "comunale",
        "region": region,
        "province": province,
        "commune": commune
    }

    for pdf_url in pdf_links:
        print(f"   -> Download in corso... {pdf_url}")
        try:
            # Add user agent to prevent blocks
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-UrbanisticaBot/1.0'
            }
            pdf_resp = requests.get(pdf_url, headers=headers, timeout=20)
            pdf_resp.raise_for_status()
            
            pdf_bytes = pdf_resp.content
            
            # Extract basic filename
            filename = pdf_url.split("/")[-1].split("?")[0]
            if not filename.endswith(".pdf"):
                filename += ".pdf"
            
            mock_file = MemoryUploadFile(filename, pdf_bytes)
            
            print(f"   -> Avvio Ingestion OCR (Metadata: {commune})...")
            await process_and_ingest_file(mock_file, metadata)
            print(f"   [OK] Inserito nel VectorStore Postgres con successo!")
            
        except Exception as e:
            print(f"   [!] Errore processando {pdf_url}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-Spider che sfrutta DuckDuckGo per trovare NTA in internet.")
    parser.add_argument("--query", required=True, help="Query di ricerca. Es: 'Piano di Governo del Territorio Viterbo'")
    parser.add_argument("--commune", required=True, help="Nome del comune")
    parser.add_argument("--province", required=True, help="Provincia del comune (sigla)")
    parser.add_argument("--region", required=True, help="Regione")
    parser.add_argument("--max", type=int, default=3, help="Numero max di PDF da scaricare")
    
    args = parser.parse_args()
    
    asyncio.run(autonomous_crawler(args.query, args.commune, args.province, args.region, args.max))
