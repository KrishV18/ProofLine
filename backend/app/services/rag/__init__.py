"""RAG (Retrieval-Augmented Generation) Subsystem for ProofLine.

Responsibility:
    This package serves as the core foundation for knowledge ingestion,
    document chunking, semantic embedding generation, vector/keyword retrieval,
    and retrieval evaluation for brand governance and review checking.

Submodules:
    - document_parser: Parses unstructured/semi-structured brand guidelines and knowledge files.
    - chunking: Splits parsed documents into semantically coherent, bounded chunks.
    - embeddings: Handles embedding model client integration for generating vector embeddings.
    - ingestion: Orchestrates parsing, chunking, embedding, and indexing into the storage layer.
    - retrieval: Searches and retrieves relevant guideline/fact context to ground LLM reviews.
    - evaluation: Evaluates retrieval quality (precision, recall, MRR) against ground truth datasets.

Note:
    All components in this package are currently foundational scaffolds and provisional
    interfaces. Core implementations depend on finalized contracts with Krish (Database)
    and Kalash (LLM Review Subsystem).
"""

__all__ = [
    "document_parser",
    "chunking",
    "embeddings",
    "ingestion",
    "retrieval",
    "evaluation",
]

