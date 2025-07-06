"""
Document Indexer Module for Private Document Q&A System.
Handles document processing, text extraction, and indexing using LlamaIndex.
"""

import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger

# LlamaIndex imports
from llama_index import (
    VectorStoreIndex, 
    SimpleDirectoryReader, 
    Document,
    StorageContext,
    load_index_from_storage
)
from llama_index.vector_stores import ChromaVectorStore
from llama_index.storage.storage_context import StorageContext
from llama_index.embeddings import OpenAIEmbedding
from llama_index.llms import OpenAI

# Local imports
from config.settings import Config
from utils.file_handlers import FileProcessor


class DocumentIndexer:
    """
    Handles document indexing and management using LlamaIndex.
    
    This class provides functionality to:
    - Process and index various document formats
    - Store documents in a vector database
    - Manage document metadata
    - Retrieve and update document indices
    """
    
    def __init__(self, config: Config):
        """
        Initialize the DocumentIndexer with configuration.
        
        Args:
            config: Application configuration object
        """
        self.config = config
        self.llm = OpenAI(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL,
            temperature=0.1
        )
        self.embed_model = OpenAIEmbedding(
            api_key=config.OPENAI_API_KEY,
            model_name=config.EMBEDDING_MODEL
        )
        self.file_processor = FileProcessor(config)
        self.index = None
        self.storage_context = None
        self._initialize_storage()
    
    def _initialize_storage(self) -> None:
        """Initialize the storage context and load existing index if available."""
        try:
            # Create index directory if it doesn't exist
            self.config.INDEX_DIR.mkdir(exist_ok=True)
            
            # Initialize ChromaDB vector store
            import chromadb
            chroma_client = chromadb.PersistentClient(
                path=str(self.config.INDEX_DIR)
            )
            chroma_collection = chroma_client.get_or_create_collection("documents")
            
            # Create storage context
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            self.storage_context = StorageContext.from_defaults(
                vector_store=vector_store
            )
            
            # Try to load existing index
            try:
                self.index = load_index_from_storage(
                    storage_context=self.storage_context,
                    llm=self.llm,
                    embed_model=self.embed_model
                )
                logger.info("Loaded existing document index")
            except Exception as e:
                logger.info(f"No existing index found, will create new one: {e}")
                self.index = None
                
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")
            raise
    
    def index_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Index a single document file.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary containing indexing results and metadata
        """
        try:
            # Validate file
            if not self._validate_file(file_path):
                raise ValueError(f"Invalid file: {file_path}")
            
            # Generate document hash for tracking
            doc_hash = self._generate_file_hash(file_path)
            
            # Extract text from document
            text_content = self.file_processor.extract_text(file_path)
            if not text_content.strip():
                raise ValueError(f"No text content found in {file_path}")
            
            # Create LlamaIndex Document
            doc = Document(
                text=text_content,
                metadata={
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "file_size": file_path.stat().st_size,
                    "file_hash": doc_hash,
                    "indexed_at": datetime.now().isoformat(),
                    "file_type": file_path.suffix.lower()
                }
            )
            
            # Create or update index
            if self.index is None:
                # Create new index
                self.index = VectorStoreIndex.from_documents(
                    [doc],
                    storage_context=self.storage_context,
                    llm=self.llm,
                    embed_model=self.embed_model
                )
                logger.info(f"Created new index with document: {file_path.name}")
            else:
                # Insert document into existing index
                self.index.insert(doc)
                logger.info(f"Added document to existing index: {file_path.name}")
            
            # Persist index
            self.index.storage_context.persist()
            
            return {
                "success": True,
                "file_name": file_path.name,
                "file_hash": doc_hash,
                "file_size": file_path.stat().st_size,
                "indexed_at": datetime.now().isoformat(),
                "message": f"Successfully indexed {file_path.name}"
            }
            
        except Exception as e:
            logger.error(f"Failed to index document {file_path}: {e}")
            return {
                "success": False,
                "file_name": file_path.name,
                "error": str(e)
            }
    
    def index_directory(self, directory_path: Path) -> List[Dict[str, Any]]:
        """
        Index all documents in a directory.
        
        Args:
            directory_path: Path to the directory containing documents
            
        Returns:
            List of indexing results for each document
        """
        results = []
        
        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory_path}")
        
        # Get all files with allowed extensions
        allowed_extensions = {f".{ext}" for ext in self.config.ALLOWED_EXTENSIONS}
        files = [
            f for f in directory_path.iterdir() 
            if f.is_file() and f.suffix.lower() in allowed_extensions
        ]
        
        logger.info(f"Found {len(files)} files to index in {directory_path}")
        
        for file_path in files:
            result = self.index_document(file_path)
            results.append(result)
            
            if result["success"]:
                logger.info(f"Indexed: {file_path.name}")
            else:
                logger.error(f"Failed to index: {file_path.name} - {result.get('error')}")
        
        return results
    
    def query_index(self, question: str, **kwargs) -> str:
        """
        Query the document index with a question.
        
        Args:
            question: The question to ask
            **kwargs: Additional query parameters
            
        Returns:
            Answer to the question based on indexed documents
        """
        if self.index is None:
            raise ValueError("No documents have been indexed yet")
        
        try:
            # Create query engine
            query_engine = self.index.as_query_engine(
                llm=self.llm,
                similarity_top_k=kwargs.get('similarity_top_k', 3),
                response_mode=kwargs.get('response_mode', 'compact')
            )
            
            # Execute query
            response = query_engine.query(question)
            
            logger.info(f"Query executed successfully: {question[:50]}...")
            return str(response)
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current index.
        
        Returns:
            Dictionary containing index statistics
        """
        if self.index is None:
            return {
                "total_documents": 0,
                "index_exists": False,
                "storage_path": str(self.config.INDEX_DIR)
            }
        
        try:
            # Get document count from vector store
            vector_store = self.index.vector_store
            if hasattr(vector_store, 'client'):
                collection = vector_store.client.get_collection("documents")
                count = collection.count()
            else:
                count = "Unknown"
            
            return {
                "total_documents": count,
                "index_exists": True,
                "storage_path": str(self.config.INDEX_DIR),
                "embedding_model": self.config.EMBEDDING_MODEL,
                "llm_model": self.config.OPENAI_MODEL
            }
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {
                "total_documents": "Error",
                "index_exists": True,
                "error": str(e)
            }
    
    def _validate_file(self, file_path: Path) -> bool:
        """
        Validate if a file can be processed.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is valid, False otherwise
        """
        # Check if file exists
        if not file_path.exists():
            return False
        
        # Check file size
        if file_path.stat().st_size > self.config.MAX_FILE_SIZE:
            return False
        
        # Check file extension
        allowed_extensions = {f".{ext}" for ext in self.config.ALLOWED_EXTENSIONS}
        if file_path.suffix.lower() not in allowed_extensions:
            return False
        
        return True
    
    def _generate_file_hash(self, file_path: Path) -> str:
        """
        Generate a hash for file tracking.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA256 hash of the file
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def clear_index(self) -> bool:
        """
        Clear the entire document index.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove index files
            import shutil
            if self.config.INDEX_DIR.exists():
                shutil.rmtree(self.config.INDEX_DIR)
                self.config.INDEX_DIR.mkdir(exist_ok=True)
            
            # Reset index
            self.index = None
            self._initialize_storage()
            
            logger.info("Document index cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            return False 