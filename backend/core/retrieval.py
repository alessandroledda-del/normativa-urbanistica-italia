from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from .config import settings
from .ingestion import get_vectorstore

def retrieve_answer(question: str):
    """
    RAG retrieval pipeline with Web Search augmentation.
    """
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.0,
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    # 1. Recupera documenti dal DB locale
    local_docs = retriever.invoke(question)
    
    # 2. Cerca sul Web tramite DuckDuckGo
    web_docs = []
    try:
        ddg = DuckDuckGoSearchAPIWrapper(region="it-it", max_results=3)
        results = ddg.results(f"normativa urbanistica {question}", max_results=3)
        for r in results:
            doc = Document(
                page_content=r["snippet"],
                metadata={"level": "internet", "source": r["link"], "title": r["title"]}
            )
            web_docs.append(doc)
    except Exception as e:
        print("Errore ricerca web:", e)
        
    # Unisce le fonti
    all_docs = local_docs + web_docs
    
    # Prepara il contesto per il prompt
    context_text = "\n\n".join([f"FONTE: {d.metadata.get('level', 'sconosciuto')} - {d.page_content}" for d in all_docs])

    system_prompt = (
        "Sei un assistente esperto in normativa urbanistica italiana. "
        "Usa i seguenti frammenti di contesto (provenienti dal database o da ricerche internet recenti) per rispondere. "
        "Specifica sempre se la risposta deriva da una legge nazionale, regionale, comunale, o da internet. "
        "Se non sai la risposta, dillo chiaramente."
        "\n\nCONTESTO:\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    
    chain = prompt | llm
    response = chain.invoke({"context": context_text, "input": question})
    
    answer = response.content
    
    # Formattazione per il frontend
    sources = []
    for doc in all_docs:
        sources.append({
            "page_content": doc.page_content,
            "metadata": doc.metadata
        })
            
    return answer, sources
