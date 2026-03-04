# Load all necessary packages

import pandas as pd
import os
from typing import List, Dict
from pathlib import Path
from openai import AzureOpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, TextLoader, PyPDFDirectoryLoader
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent, create_react_agent, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool
from dotenv import load_dotenv
import time
from tqdm import tqdm
from pathlib import Path
import streamlit as st

load_dotenv()  # no-op on Streamlit Cloud; loads .env locally


# ── Secret helper ──────────────────────────────────────────────────────────────
def get_secret(key: str) -> str:
    """Read from st.secrets (Streamlit Cloud) or environment variables (local)."""
    try:
        return st.secrets[key]
    except (FileNotFoundError, KeyError):
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Secret '{key}' not found in st.secrets or environment variables.")
        return value


class DeepResearchAgent:
    SYSTEM_PROMPT = """You are a Senior Development Cooperation Analyst specializing in evidence-based project design and institutional learning. You work for a ministry planning new sustainable development projects globally, and your role is to extract actionable, non-obvious lessons from past project documentation.

    CORE MISSION:
    Extract specific, contextual insights from past development cooperation projects that can meaningfully inform the critical review of new project proposals. Your insights must go beyond generic development wisdom to reveal nuanced patterns, context-specific success factors, and overlooked risks.

    RESEARCH PROTOCOL:

    1. INITIAL EXPLORATION (Use deep_search):
    - Cast a wide net to understand the landscape of similar projects
    - Identify patterns across multiple projects, countries, and sectors
    - Look for both successes AND failures - failures often teach more

    2. DEEP DIVE (Use search_documents or diverse_search):
    - Investigate specific mechanisms: WHY did something work or fail?
    - Identify contextual factors: political economy, timing, stakeholder dynamics
    - Look for implementation details, not just outcomes
    - Search for quantitative data, timelines, budget allocations

    3. CRITICAL SYNTHESIS:
    - Compare contradictory findings across different projects
    - Identify conditions under which similar approaches succeeded or failed
    - Distinguish correlation from causation
    - Note what the documents DON'T say (gaps in reporting, avoided topics)

    QUALITY STANDARDS FOR INSIGHTS:

    ✅ GOOD INSIGHTS (Aim for these):
    - "In 3 water projects in Sub-Saharan Africa (Tanzania 2018, Kenya 2019, Uganda 2020), community ownership was only sustained when local government budget allocations for maintenance were secured BEFORE project handover. Projects that relied on community fees alone saw 65% infrastructure failure within 2 years." [Source: X, Page Y]

    - "Agricultural training programs in South Asia showed 40% higher adoption rates when conducted by local farmer-trainers rather than external consultants, BUT only in communities with existing farmer cooperatives. In communities without cooperatives, external trainers performed better." [Source: X, Page Y]

    ❌ POOR INSIGHTS (Avoid these):
    - "Stakeholder engagement is important for project success"
    - "Local ownership matters"
    - "Context is crucial"
    - "Monitoring and evaluation should be robust"

    INSIGHT CHARACTERISTICS YOU MUST AIM FOR:

    1. **Specificity**: Include numbers, timeframes, locations, project names
    2. **Conditionality**: "X worked when Y was true, but failed when Z"
    3. **Mechanisms**: Explain HOW and WHY, not just WHAT
    4. **Actionability**: Clear implications for proposal reviewers
    5. **Evidence-based**: Always cite specific sources with page numbers
    6. **Non-obvious**: Would surprise an experienced development practitioner

    ANALYTICAL FRAMEWORK - Always consider:

    - **Design Phase**: What assumptions proved wrong? What baseline data was missing?
    - **Implementation**: What institutional bottlenecks emerged? Which partnerships worked?
    - **Sustainability**: What happened after project end? What cost structures proved unrealistic?
    - **Context**: Political economy factors, timing, cultural dynamics, institutional capacity
    - **Scale**: What worked at pilot but failed at scale? Or vice versa?
    - **Unintended Consequences**: Negative spillovers, market distortions, dependency creation

   SEARCH STRATEGY:

    Phase 1 - LANDSCAPE MAPPING:
    - Use deep_search to understand the topic broadly
    - Use compare_projects if looking at different regions/approaches

    Phase 2 - CRITICAL ANALYSIS:
    - Use find_failure_cases to understand what went wrong
    - Use find_longterm_outcomes to check sustainability

    Phase 3 - EVIDENCE GATHERING:
    - Use analyze_context_factors to understand WHY
    - Use find_implementation_details to understand HOW

    Phase 4 - RISK ASSESSMENT:
    - Use identify_risk_patterns to flag concerns for new proposals

    Phase 5 - TARGETED FOLLOW-UP:
    - Use search_documents for specific clarifications

    OUTPUT FORMAT:

    Structure your response as:

    **Key Findings:**
    [3-5 specific, actionable insights with full citations]

    **Critical Success Factors:**
    [What conditions needed to be in place - be specific about sequence, timing, institutional requirements]

    **Common Failure Modes:**
    [What went wrong and why - include early warning signs]

    **Red Flags for Proposal Review:**
    [Specific things to look for in new proposals based on past failures]

    **Evidence Gaps:**
    [What information you couldn't find that would be valuable]

    ** Citation section:**
    [Include a ### Sources section. Format each source as:
    [n] Titel (Erscheinungsdatum) | Filename | Page X
    Use ONLY values returned by the search tools. Never include URLs.]


    CRITICAL GUIDELINES:
    - Prioritize project evaluations, mid-term reviews, and lessons-learned documents
    - Value negative findings as much as positive ones
    - If you find contradictory evidence, present both sides with context
    - Distinguish between project outputs (delivered) and outcomes (sustained change)
    - Be skeptical of self-reported success without independent verification
    - Always consider the political economy: Who benefited? Who lost? What power dynamics existed?
    - Flag when sample sizes are small or evidence is thin
    - Note when "success" was measured too early (before sustainability could be assessed)

    EVIDENCE DISCIPLINE:
    - If your search results contain no relevant evidence for a claim, you MUST write: 'No evidence found in available documents for this claim.'
    - Never bridge evidence gaps with general development knowledge
    - If fewer than 2 sources support a finding, explicitly flag it as: '[Single source — treat with caution]'
    - Never extrapolate from one country/sector to another without explicitly stating you are doing so and flagging it as an inference, not a finding
    
    HARD LIMITS:
    - Use a maximum of 4 search tool calls per research question
    - After 3 tool calls, assess whether you have sufficient evidence to synthesize
    - If yes: stop searching and write your final answer immediately
    - If no: use 1 more targeted tool call, then synthesize regardless
    - Never use more than 4 tool calls — always reserve the final step for synthesis
    - Stop immediately when your last 2 searches returned similar information

    CITATION RULES (strictly enforced):
    - Only cite sources that appeared in your search tool results
    - Use the exact filename and page number returned by the tools
    - Never invent, guess, or supplement with sources from your training knowledge
    - If the document name is unclear, write: [Source: <filename>, Page: <page>]
    - Never include URLs unless they were explicitly present in the retrieved text
    - If evidence is insufficient, state: 'Insufficient evidence found in available documents

    TONE:
    Professional, analytical, constructively critical. Do not use abbreviations. Always write out abbreviations in full. You serve the ministry's learning mission, not project advocacy. Your job is to prevent repeating past mistakes and amplify proven approaches."""

    def __init__(self, persist_directory: str = "./chroma_db", documents_path: str = None):
        """
        Initialize the deep research agent.
        Automatically connects to remote Azure ChromaDB if CHROMA_HOST secret is set,
        otherwise falls back to local ChromaDB.
        """

        api_key = get_secret("OPENAI_AZURE_API_KEY")

        # Using GPT-5
        self.llm = ChatOpenAI(
            model    = "gpt-5",
            base_url = "https://bootcampai.openai.azure.com/openai/v1/",
            temperature = 0,
            api_key  = api_key
        )

        embeddings = OpenAIEmbeddings(
            model    = "text-embedding-3-large",
            base_url = "https://bootcampai.openai.azure.com/openai/v1/",
            api_key  = api_key
        )

        # ── Decide: remote Azure ChromaDB or local ChromaDB ───────────────────
        chroma_host = None
        try:
            chroma_host = get_secret("CHROMA_HOST")
        except ValueError:
            pass  # No CHROMA_HOST set → use local

        if chroma_host:
            # ── REMOTE (Streamlit Cloud → Azure Container Instance) ───────────
            import chromadb

            print(f"🔌 Connecting to remote ChromaDB at {chroma_host}...")

            remote_client = chromadb.HttpClient(
                host = chroma_host,
                port = int(get_secret("CHROMA_PORT")),
            )

            collections = remote_client.list_collections()
            if not collections:
                raise RuntimeError(
                    "ChromaDB is running but has no collections. "
                    "Was the migration completed successfully?"
                )

            collection_name = collections[0].name
            print(f"   ✓ Connected — using collection: '{collection_name}'")

            self.vectorstore = Chroma(
                client             = remote_client,
                collection_name    = collection_name,
                embedding_function = embeddings,
            )

        else:
            # ── LOCAL (running on your machine) ───────────────────────────────
            if os.path.exists(persist_directory):
                print(f"✓ Found local vector store at {persist_directory}")
                self.vectorstore = Chroma(
                    persist_directory  = persist_directory,
                    embedding_function = embeddings,
                )
                print("✓ Vector store loaded successfully!\n")
            else:
                if documents_path is None:
                    raise ValueError(
                        f"Vector store not found at {persist_directory} and no documents_path provided. "
                        "Please provide documents_path to create the vector store."
                    )
                print(f"Vector store not found. Creating new one from {documents_path}...")
                vector_store_creator = VectorStoreCreator(
                    documents_path    = documents_path,
                    persist_directory = persist_directory,
                )
                self.vectorstore = vector_store_creator.vectorstore
                print("✓ Vector store created!\n")

        # Create tools and agent
        self.tools          = self._create_tools()
        self.agent_executor = self._create_agent()

    def _format_results(self, docs: List, prefix: str = "RESULTS") -> str:
        """Format search results consistently."""
        if not docs:
            return "No relevant documents found."
            
        results = [f"=== {prefix} ===\n",
                  "⚠️ ONLY cite sources listed below. Do not add external sources.\n"]
        for i, doc in enumerate(docs, 1):
            source   = doc.metadata.get('source', 'Unknown')
            filename = os.path.basename(source)
            page     = doc.metadata.get('page', 'N/A')
            results.append(
                f"\n[CITABLE SOURCE {i}]\n"
                f"  Filename: {filename}\n"
                f"  Page: {page}\n"
                f"  Content: {doc.page_content}\n"
                f"  ⚠️ No URL available for this source.\n"
            )
        return "\n".join(results)

    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent."""
        
        def search_documents(query: str) -> str:
            docs = self.vectorstore.similarity_search(query, k=8)
            return self._format_results(docs, prefix="SEARCH RESULT")
        
        def deep_search(query: str) -> str:
            """Perform a deep search by generating multiple query variations."""
            variations_prompt = f"""Given this research question: "{query}"

            Generate 6 search queries to gather comprehensive information.
            IMPORTANT: Your document database contains documents in English, German, and French.
            Generate 2 queries in English, 2 in German, and 2 in French covering different aspects.

            Format as a numbered list:
            1. [English query 1]
            2. [English query 2]
            3. [German query 1]
            4. [German query 2]
            5. [French query 1]
            6. [French query 2]"""
            
            response = self.llm.invoke(variations_prompt)
            queries  = [line.split('. ', 1)[1] for line in response.content.split('\n') 
                       if line.strip() and line[0].isdigit()]
            
            all_queries = [query] + queries[:6]
            
            all_results = {}
            for q in all_queries:
                docs = self.vectorstore.similarity_search(q, k=8)
                for doc in docs:
                    all_results[doc.page_content] = doc
            
            return self._format_results(list(all_results.values())[:15], prefix="DEEP SEARCH RESULTS")
        
        def compare_projects(query: str) -> str:
            """Compare similar projects across different contexts."""
            comparison_prompt = f"""Given this comparison request: "{query}"

            Generate 4 search queries to compare projects effectively:
            1. A query for the first group/context
            2. A query for the second group/context  
            3. A query for common challenges across both
            4. A query for divergent outcomes/approaches

            Format as:
            1. [query 1]
            2. [query 2]
            3. [query 3]
            4. [query 4]"""

            response = self.llm.invoke(comparison_prompt)
            queries  = [line.split('. ', 1)[1] for line in response.content.split('\n') 
                       if line.strip() and line[0].isdigit()]
            
            all_results = {}
            for q in queries[:4]:
                docs = self.vectorstore.similarity_search(q, k=8)
                for doc in docs:
                    all_results[doc.page_content] = doc
            
            return self._format_results(list(all_results.values())[:15], prefix="COMPARATIVE ANALYSIS")

        def find_failure_cases(query: str) -> str:
            """Specifically search for project failures and negative outcomes."""
            failure_keywords = [
                f"{query} failure discontinued abandoned",
                f"{query} challenges problems obstacles",
                f"{query} Herausforderungen Probleme gescheitert abgebrochen",
                f"{query} Nachhaltigkeit Risiken Schwierigkeiten",
                f"{query} défis problèmes échec abandonné",
                f"{query} durabilité risques difficultés",
            ]
            
            all_results = {}
            for fail_query in failure_keywords:
                docs = self.vectorstore.similarity_search(fail_query, k=8)
                for doc in docs:
                    content_lower = doc.page_content.lower()
                    if any(term in content_lower for term in 
                          ['fail', 'challenge', 'problem', 'difficult', 'unsustainable', 
                           'abandon', 'discontinue', 'not work', 'ineffective']):
                        all_results[doc.page_content] = doc
            
            return self._format_results(list(all_results.values())[:12], prefix="FAILURE CASES")

        def find_longterm_outcomes(query: str) -> str:
            """Search for long-term sustainability outcomes and post-project results."""
            temporal_queries = [
                f"{query} post-project sustainability long-term outcomes",
                f"{query} after completion follow-up years later",
                f"{query} maintained discontinued abandoned funding"
            ]
            
            all_results = {}
            for temp_query in temporal_queries:
                docs = self.vectorstore.similarity_search(temp_query, k=8)
                for doc in docs:
                    all_results[doc.page_content] = doc
            
            return self._format_results(list(all_results.values())[:15], prefix="LONG-TERM OUTCOMES")

        def analyze_context_factors(query: str) -> str:
            """Search for political economy, institutional capacity, and cultural factors."""
            context_queries = [
                f"{query} political economy stakeholders",
                f"{query} institutional capacity governance",
                f"{query} cultural social norms",
                f"{query} enabling environment constraints",
                f"{query} local context conditions"
            ]
            
            all_results = {}
            for ctx_query in context_queries:
                docs = self.vectorstore.similarity_search(ctx_query, k=8)
                for doc in docs:
                    all_results[doc.page_content] = doc
            
            return self._format_results(list(all_results.values())[:15], prefix="CONTEXTUAL FACTORS")

        def identify_risk_patterns(query: str) -> str:
            """Find early warning signs and red flags from past projects."""
            risk_queries = [
                f"{query} risks delays bottlenecks obstacles",
                f"{query} assumptions proved wrong underestimated",
                f"{query} early warning signs indicators red flags"
            ]
            
            all_results = {}
            for risk_query in risk_queries:
                docs = self.vectorstore.similarity_search(risk_query, k=8)
                for doc in docs:
                    all_results[doc.page_content] = doc
            
            return self._format_results(list(all_results.values())[:15], prefix="RISK PATTERNS & RED FLAGS")

        def find_implementation_details(query: str) -> str:
            """Search for HOW things were implemented: partnerships, management, training."""
            implementation_queries = [
                f"{query} implementation approach partnership coordination",
                f"{query} procurement management training capacity building",
                f"{query} monitoring supervision quality control staffing"
            ]

            all_results = {}
            for impl_query in implementation_queries:
                docs = self.vectorstore.similarity_search(impl_query, k=8)
                for doc in docs:
                    all_results[doc.page_content] = doc
            
            return self._format_results(list(all_results.values())[:15], prefix="IMPLEMENTATION DETAILS")

        return [
            Tool(name="search_documents",         func=search_documents,         description="Quick search for specific information or follow-up queries."),
            Tool(name="deep_search",               func=deep_search,               description="Comprehensive multi-angle search. Use first for new topics."),
            Tool(name="compare_projects",          func=compare_projects,          description="Compare similar projects across contexts to identify patterns and context-specific factors."),
            Tool(name="find_failure_cases",        func=find_failure_cases,        description="Find project failures, challenges, and negative outcomes. Critical for learning what to avoid."),
            Tool(name="find_longterm_outcomes",    func=find_longterm_outcomes,    description="Find post-project sustainability and long-term results. Essential for true impact assessment."),
            Tool(name="analyze_context_factors",   func=analyze_context_factors,   description="Find political economy, institutional, and cultural factors that influenced outcomes."),
            Tool(name="identify_risk_patterns",    func=identify_risk_patterns,    description="Identify early warning signs and red flags from past projects."),
            Tool(name="find_implementation_details", func=find_implementation_details, description="Find HOW things were implemented: partnerships, training, management approaches."),
        ]

    def _create_agent(self) -> AgentExecutor:
        """Create the research agent."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_tools_agent(
            llm    = self.llm,
            tools  = self.tools,
            prompt = prompt
        )
        
        return AgentExecutor(
            agent                  = agent,
            tools                  = self.tools,
            verbose                = False,
            max_iterations         = 8,
            return_intermediate_steps = True,
            early_stopping_method  = "generate"
        )

    def _validate_citations(self, response: str) -> str:
        import re
        urls = re.findall(r'https?://\S+', response)
        if urls:
            cleaned = re.sub(r'\s*https?://\S+', '', response)
            warning = (
                "\n\n---\n"
                "⚠️ Note: URL references were removed from this response. "
                "All citations refer exclusively to documents in the GIZ project database. "
                f"({len(urls)} URL(s) suppressed)"
            )
            return cleaned + warning
        return response

    def research(self, question: str) -> Dict:
        result = self.agent_executor.invoke({"input": question})
        result["output"] = self._validate_citations(result["output"])
        return result