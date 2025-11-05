"""
Unit tests for pgvector-based RAG chatbot.

Run with: pytest test_unit.py -v
"""

import os
import pytest
from dotenv import load_dotenv


class TestEnvironmentVariables:
    """Test environment variable configuration."""

    def test_env_variables_loaded(self):
        """Test that required environment variables are present."""
        load_dotenv()
        openai_key = os.getenv("OPENAI_API_KEY")
        postgres_conn = os.getenv("POSTGRES_CONNECTION")

        assert openai_key is not None, "OPENAI_API_KEY not found in environment"
        assert postgres_conn is not None, "POSTGRES_CONNECTION not found in environment"
        assert "postgresql+psycopg" in postgres_conn, "Invalid PostgreSQL connection string format"


class TestDatabaseConnection:
    """Test database connectivity."""

    def test_database_connection(self):
        """Test that we can connect to PostgreSQL with pgvector."""
        load_dotenv()
        from langchain_postgres import PGVector
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        connection = os.getenv("POSTGRES_CONNECTION")

        try:
            vector_store = PGVector(
                embeddings=embeddings,
                collection_name="test_unit_collection",
                connection=connection,
                use_jsonb=True,
            )
            assert vector_store is not None
            # Cleanup
            vector_store.delete_collection()
        except Exception as e:
            pytest.fail(f"Database connection failed: {e}")


class TestEmbeddingModel:
    """Test embedding model initialization."""

    def test_embedding_model(self):
        """Test that OpenAI embeddings model can be initialized."""
        load_dotenv()
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        assert embeddings is not None

        # Test embedding generation
        test_text = "This is a test"
        embedding = embeddings.embed_query(test_text)
        assert len(embedding) == 3072, f"Expected 3072 dimensions, got {len(embedding)}"


class TestTextSplitting:
    """Test text splitting functionality."""

    def test_text_splitting(self):
        """Test that RecursiveCharacterTextSplitter works as expected."""
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_core.documents import Document

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=100,
            length_function=len,
        )

        # Create test document with 1000 characters
        test_doc = Document(
            page_content="A" * 1000,
            metadata={"source": "test"}
        )

        chunks = splitter.split_documents([test_doc])

        # Verify chunks were created
        assert len(chunks) > 1, "Should create multiple chunks from long document"
        # Verify chunk size constraint
        assert all(len(chunk.page_content) <= 300 for chunk in chunks), "Chunks exceed max size"


class TestRetrieverConfiguration:
    """Test retriever configuration."""

    def test_retriever_configuration(self):
        """Test that retriever is configured correctly."""
        load_dotenv()
        from langchain_postgres import PGVector
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        connection = os.getenv("POSTGRES_CONNECTION")

        try:
            vector_store = PGVector(
                embeddings=embeddings,
                collection_name="test_retriever_collection",
                connection=connection,
                use_jsonb=True,
            )

            retriever = vector_store.as_retriever(search_kwargs={'k': 5})

            assert retriever is not None
            assert retriever.search_kwargs['k'] == 5

            # Cleanup
            vector_store.delete_collection()
        except Exception as e:
            pytest.fail(f"Retriever configuration failed: {e}")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
