# Load all necessary packages

import pandas as pd
import os
from typing import List, Dict
from pathlib import Path
from openai import AzureOpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings, AzureOpenAIEmbeddings
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

# Load enviroment variable
load_dotenv()

# Load file paths to pdfs
file_path =r"C:\Users\yannik_sassmann\Documents\YASA\Fortbildungen\Data_Science_Bootcamp\Final_Project\Ironhack_Capstone_Project\pdfs\giz"
documents_path=r"C:\Users\yannik_sassmann\Documents\YASA\Fortbildungen\Data_Science_Bootcamp\Final_Project\Ironhack_Capstone_Project\pdfs\giz"

# Create batch sizing to stay within rate limits in Azure
class RateLimitedAzureOpenAIEmbeddings(AzureOpenAIEmbeddings):
    """Azure OpenAI Embeddings with rate limiting."""
    
    def __init__(self, requests_per_minute: int = 400, **kwargs):
        super().__init__(**kwargs)
        self.requests_per_minute = requests_per_minute
        self.min_seconds_between_requests = 60.0 / requests_per_minute
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_seconds_between_requests:
            sleep_time = self.min_seconds_between_requests - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents with rate limiting."""
        self._rate_limit()
        return super().embed_documents(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed query with rate limiting."""
        self._rate_limit()
        return super().embed_query(text)
    

# Create chroma vector db
class VectorStoreCreator:
    """Creates and persists a vector store from PDF documents."""

    def __init__(self, documents_path: str, persist_directory: str = "./chroma_db"):
        """
        Initialize the vector store creator.
        
        Args:
            documents_path: Path to a directory containing PDF files
            persist_directory: Where to store the vector database
        """
        # Using text-embedding-3-large for better quality embeddings
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large",
                                           base_url="https://bootcampai.openai.azure.com/openai/v1/",
                                           api_key=os.environ["OPENAI_AZURE_API_KEY"])
        
        self.persist_directory = persist_directory

        # Load and process documents
        self.vectorstore = self._setup_vectorstore(documents_path)

    def _setup_vectorstore(self, documents_path: str):
        """Load PDF documents and create vector store with batching."""
        print(f"\n{'='*80}")
        print("LOADING PDF DOCUMENTS")
        print(f"{'='*80}")
        print(f"Path: {documents_path}")
        
        path = Path(documents_path)
        
        if path.is_dir():
            print(f"Loading PDFs from directory...")
            documents = self._load_pdfs_from_directory(documents_path)
        elif path.is_file() and str(path).lower().endswith('.pdf'):
            print(f"Loading single PDF...")
            documents = self._load_single_pdf(documents_path)
        else:
            print(f"Trying glob pattern...")
            documents = self._load_pdfs_from_pattern(documents_path)
        
        print(f"\n✓ Total pages loaded: {len(documents)}")
        
        if len(documents) == 0:
            raise ValueError("No PDF documents loaded!")
        
        # Split documents into chunks
        print("\nSplitting documents into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=300,
            length_function=len,
        )
        chunks = text_splitter.split_documents(documents)
        
        print(f"✓ Created {len(chunks)} chunks")
        
        # Create vector store with batching
        print("\nCreating vector embeddings with rate limiting...")
        print(f"Processing {len(chunks)} chunks in batches...")
        print("This will take approximately {:.1f} minutes".format(len(chunks) / 370 + 1))
        
        vectorstore = self._create_vectorstore_with_batching(chunks)
        
        print("✓ Vector store created successfully!\n")
        return vectorstore
    
    def _create_vectorstore_with_batching(self, chunks: List[Document], batch_size: int = 100):
        """Create vector store by processing chunks in batches to avoid rate limits."""
        
        # Check if vectorstore already exists
        if os.path.exists(self.persist_directory):
            print(f"Loading existing vector store from {self.persist_directory}")
            vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
            print("✓ Loaded existing vector store")
            return vectorstore
        
        # Create new vectorstore with batching
        vectorstore = None
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        
        print(f"\nProcessing {total_batches} batches of {batch_size} chunks each...")
        
        for i in tqdm(range(0, len(chunks), batch_size), desc="Creating embeddings"):
            batch = chunks[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            try:
                if vectorstore is None:
                    # Create initial vectorstore
                    print(f"\nBatch {batch_num}/{total_batches}: Creating initial vector store...")
                    vectorstore = Chroma.from_documents(
                        documents=batch,
                        embedding=self.embeddings,
                        persist_directory=self.persist_directory
                    )
                else:
                    # Add to existing vectorstore
                    print(f"\nBatch {batch_num}/{total_batches}: Adding to vector store...")
                    vectorstore.add_documents(batch)
                
                # Small delay between batches to be extra safe
                if i + batch_size < len(chunks):
                    time.sleep(1)
                    
            except Exception as e:
                if "RateLimitReached" in str(e):
                    print(f"\nRate limit hit at batch {batch_num}. Waiting 60 seconds...")
                    time.sleep(60)
                    # Retry this batch
                    if vectorstore is None:
                        vectorstore = Chroma.from_documents(
                            documents=batch,
                            embedding=self.embeddings,
                            persist_directory=self.persist_directory
                        )
                    else:
                        vectorstore.add_documents(batch)
                else:
                    raise e
        
        return vectorstore
    
    def _load_single_pdf(self, pdf_path: str) -> List[Document]:
        """Load a single PDF file."""
        try:
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()
            print(f"  ✓ Loaded: {os.path.basename(pdf_path)} ({len(documents)} pages)")
            return documents
        except Exception as e:
            print(f"  ✗ Failed to load {pdf_path}: {e}")
            return []
    
    def _load_pdfs_from_directory(self, directory_path: str) -> List[Document]:
        """Load all PDF files from a directory."""
        return self._load_pdfs_manually(directory_path)
    
    def _load_pdfs_manually(self, directory_path: str) -> List[Document]:
        """Manually load all PDFs from directory."""
        documents = []
        
        pdf_files = []
        for file in os.listdir(directory_path):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(directory_path, file))
        
        print(f"Found {len(pdf_files)} PDF files\n")
        
        for i, pdf_file in enumerate(pdf_files, 1):
            try:
                print(f"[{i}/{len(pdf_files)}] Loading {os.path.basename(pdf_file)}...", end=" ")
                loader = PyPDFLoader(pdf_file)
                docs = loader.load()
                documents.extend(docs)
                print(f"✓ ({len(docs)} pages)")
            except Exception as e:
                print(f"✗ Error: {str(e)[:50]}")
        
        return documents
    
    def _load_pdfs_from_pattern(self, pattern: str) -> List[Document]:
        """Load PDFs matching a glob pattern."""
        pdf_files = glob.glob(pattern, recursive=True)
        documents = []
        
        print(f"Found {len(pdf_files)} files matching pattern")
        
        for pdf_file in pdf_files:
            if pdf_file.lower().endswith('.pdf'):
                docs = self._load_single_pdf(pdf_file)
                documents.extend(docs)
        
        return documents
    
    # Create the vector store
if __name__ == "__main__":
    print("Starting vector store creation...")
    vector_store_creator = VectorStoreCreator(
        documents_path=documents_path,
        persist_directory="./chroma_db"
    )
    print("Done! Vector store is ready.")
