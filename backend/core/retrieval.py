from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools.retriever import create_retriever_tool
from langchain_core.tools import tool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

from .config import settings
from .ingestion import get_vectorstore
from .oneri import calcola_oneri
from typing import List, Dict

@tool
def tool_calcola_oneri(codice_istat: str, destinazione_uso: str, tipo_intervento: str, volume_mc: float = 0.0, superficie_mq: float = 0.0) -> str:
    """Usa questo tool per calcolare e stimare gli oneri di urbanizzazione edilizia in Italia fornendo il codice_istat e dettagli volumetrici."""
    return calcola_oneri(codice_istat, destinazione_uso, tipo_intervento, volume_mc, superficie_mq)

def retrieve_answer(question: str, use_internet: bool = False, filters: dict = None, chat_history: List[Dict] = None):
    """
    Agentic Workflow pipeline per AI Urbanistica.
    """
    if filters is None:
        filters = {}
    if chat_history is None:
        chat_history = []

    vectorstore = get_vectorstore()
    
    search_kwargs = {"k": 4}
    if filters:
        search_kwargs["filter"] = filters

    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)
    
    # 1. Tool Retriever
    retriever_tool = create_retriever_tool(
        retriever,
        name="ricerca_normativa_urbanistica",
        description="Cerca nel database locale informazioni sulle normative urbanistiche (PGT, NTA, leggi regionali, nazionali, oneri)."
    )

    tools = [retriever_tool, tool_calcola_oneri]

    # 2. Web Search Tool (opzionale)
    if use_internet:
        @tool
        def tool_ricerca_web(query: str) -> str:
            """Cerca su internet chiarimenti normativi legali recenti o sentenze urbanistiche."""
            try:
                ddg = DuckDuckGoSearchAPIWrapper(region="it-it", max_results=3)
                results = ddg.results(f"normativa urbanistica sentenze {query}", max_results=3)
                return "\n\n".join([f"Titolo: {r['title']}\nFonte: {r['link']}\nTesto: {r['snippet']}" for r in results])
            except Exception as e:
                return f"Errore ricerca web: {str(e)}"
        tools.append(tool_ricerca_web)

    llm = ChatGroq(
        model="llama3-70b-8192",
        temperature=0.0,
        api_key=settings.GROQ_API_KEY
    )
    
    system_prompt = (
        "Sei un assistente esperto in normativa urbanistica italiana (PGT, DPR 380, NTA e oneri). "
        "Usa i tools a disposizione (ricerca_normativa_urbanistica, tool_calcola_oneri, ed eventualmente tool_ricerca_web) per rispondere con precisione tecnica. "
        "Quando usi il tool per il calcolo oneri ed esegui stime economiche, riassumi chiaramente il risultato in euro. Specifica sempre le fonti normative.\n"
        "Se ti viene chiesto di una specifica 'regione', 'provincia' o 'comune', usa quegli estremi per cercare con precisione."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, return_intermediate_steps=True)
    
    langchain_history = []
    for msg in chat_history:
        if msg.get("role") == "user":
            langchain_history.append(HumanMessage(content=msg.get("content")))
        elif msg.get("role") == "assistant" or msg.get("role") == "system":
            langchain_history.append(AIMessage(content=msg.get("content")))

    response = agent_executor.invoke({
        "input": question,
        "chat_history": langchain_history
    })
    
    answer = response["output"]
    
    # Formatting sources per compatibilità Frontend
    sources = []
    if "intermediate_steps" in response:
        for action, observation in response["intermediate_steps"]:
            if action.tool == "ricerca_normativa_urbanistica":
                sources.append({
                    "page_content": str(observation)[:500] + "...",
                    "metadata": {"source": "database_vettoriale", "tool": action.tool}
                })
            elif action.tool == "tool_ricerca_web":
                sources.append({
                    "page_content": str(observation)[:500] + "...",
                    "metadata": {"source": "internet", "tool": action.tool}
                })
            elif action.tool == "tool_calcola_oneri":
                sources.append({
                    "page_content": str(observation)[:500] + "..." if len(str(observation)) > 500 else str(observation),
                    "metadata": {"source": "calcolatore_oneri_sql", "tool": action.tool}
                })
                
    return answer, sources
