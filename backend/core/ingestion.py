import tempfile
import os
from fastapi import UploadFile
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector

from .config import settings

def get_vectorstore():
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = PGVector(
        embeddings=embeddings,
        collection_name="urbanistica_docs",
        connection=settings.POSTGRES_URL,
        use_jsonb=True
    )
    return vectorstore

async def process_and_ingest_file(upload: UploadFile, metadata: dict):
    # Save UploadFile to a temporary file for loader
    suffix = ".pdf" if upload.filename.endswith(".pdf") else ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await upload.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Load document
        if suffix == ".pdf":
            # Using PDFPlumber as the dependency is in requirements.txt
            from langchain_community.document_loaders import PDFPlumberLoader
            from langchain_core.documents import Document
            
            loader = PDFPlumberLoader(tmp_path)
            docs = loader.load()
            
            # Check for scanned PDF (no text found)
            testo_unito = "".join([d.page_content for d in docs]).strip()
            if not testo_unito:
                try:
                    from pdf2image import convert_from_path
                    import pytesseract
                    
                    # Convert PDF pages to images for OCR
                    pages = convert_from_path(tmp_path, 200) # 200 dpi is a good balance
                    ocr_docs = []
                    for i, page in enumerate(pages):
                        text = pytesseract.image_to_string(page, lang="ita")
                        if text.strip():
                            ocr_docs.append(Document(page_content=text, metadata={"page_metadata": str(i)}))
                    
                    if ocr_docs:
                        docs = ocr_docs
                except Exception as e:
                    print(f"OCR Fallback fallito per {tmp_path}. Requisiti di sistema (Tesseract/Poppler) mancanti? Errore: {e}")
        else:
            loader = TextLoader(tmp_path)
            docs = loader.load()
            
        # Add our custom metadata to each document page loaded
        for doc in docs:
            # We enforce string values for ChromaDB metadata
            doc.metadata.update({k: str(v) for k, v in metadata.items()})

        # Chunk the text
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        splits = text_splitter.split_documents(docs)

        # Ingest to ChromaDB
        vectorstore = get_vectorstore()
        vectorstore.add_documents(documents=splits)
        
        return True

    finally:
        os.remove(tmp_path)
