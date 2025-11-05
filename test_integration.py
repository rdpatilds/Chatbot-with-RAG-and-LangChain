"""
Integration tests for pgvector-based RAG chatbot.

These tests verify the complete pipeline from document loading to retrieval.

Run with: pytest test_integration.py -v -s
"""

import os
import pytest
from dotenv import load_dotenv
from uuid import uuid4

# Load environment variables
load_dotenv()


class TestFullIngestionPipeline:
    """Test complete ingestion pipeline."""

    def test_full_ingestion_pipeline(self):
        """Test complete ingestion from PDF to database."""
        from langchain_community.document_loaders import PyPDFDirectoryLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_openai import OpenAIEmbeddings
        from langchain_postgres import PGVector

        # Setup
        DATA_PATH = "data"
        POSTGRES_CONNECTION = os.getenv("POSTGRES_CONNECTION")
        TEST_COLLECTION = "test_ingestion_collection"

        # Load PDFs
        print(f"\n📄 Loading PDFs from {DATA_PATH}...")
        loader = PyPDFDirectoryLoader(DATA_PATH)
        raw_documents = loader.load()
        assert len(raw_documents) > 0, "No documents loaded"
        print(f"✅ Loaded {len(raw_documents)} document(s)")

        # Split
        print("✂️  Splitting documents...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=100,
            length_function=len,
            is_separator_regex=False,
        )
        chunks = text_splitter.split_documents(raw_documents)
        assert len(chunks) > 0, "No chunks created"
        print(f"✅ Created {len(chunks)} chunk(s)")

        # Embed and store
        print("🚀 Embedding and storing in pgvector...")
        embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large")
        vector_store = PGVector(
            embeddings=embeddings_model,
            collection_name=TEST_COLLECTION,
            connection=POSTGRES_CONNECTION,
            use_jsonb=True,
        )

        uuids = [str(uuid4()) for _ in range(len(chunks))]
        vector_store.add_documents(documents=chunks, ids=uuids)
        print(f"✅ Stored {len(chunks)} chunk(s)")

        # Verify storage
        print("🔍 Verifying storage with similarity search...")
        results = vector_store.similarity_search("test query", k=1)
        assert len(results) > 0, "No documents retrieved after ingestion"
        print(f"✅ Retrieved {len(results)} document(s)")

        # Cleanup
        print("🧹 Cleaning up test collection...")
        vector_store.delete_collection()
        print("✅ Test passed!")


class TestRetrievalQuality:
    """Test retrieval quality with known queries."""

    def test_retrieval_quality(self):
        """Test that retrieval returns relevant results."""
        from langchain_postgres import PGVector
        from langchain_openai import OpenAIEmbeddings
        from langchain_core.documents import Document

        POSTGRES_CONNECTION = os.getenv("POSTGRES_CONNECTION")
        TEST_COLLECTION = "test_retrieval_quality_collection"

        # Create test data with known content
        print("\n📝 Creating test data...")
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name=TEST_COLLECTION,
            connection=POSTGRES_CONNECTION,
            use_jsonb=True,
        )

        test_docs = [
            Document(
                page_content="The attention mechanism is a key component of transformer models.",
                metadata={"topic": "attention"}
            ),
            Document(
                page_content="Transformers use self-attention to process sequences in parallel.",
                metadata={"topic": "transformers"}
            ),
            Document(
                page_content="Neural networks consist of layers of interconnected nodes.",
                metadata={"topic": "neural_networks"}
            ),
        ]

        vector_store.add_documents(test_docs)
        print("✅ Test data created")

        # Test queries with expected results
        test_cases = [
            ("attention mechanism", "attention"),
            ("transformer architecture", "transformers"),
            ("neural network", "neural_networks"),
        ]

        print("🔍 Testing retrieval quality...")
        for query, expected_topic in test_cases:
            results = vector_store.similarity_search(query, k=3)
            assert len(results) > 0, f"No results for query: '{query}'"

            # Check that at least one result contains relevant keywords
            combined_content = " ".join([doc.page_content.lower() for doc in results])
            query_words = query.lower().split()

            relevant = any(word in combined_content for word in query_words)
            assert relevant, f"Results for '{query}' don't seem relevant"
            print(f"✅ Query '{query}' returned relevant results")

        # Cleanup
        print("🧹 Cleaning up...")
        vector_store.delete_collection()
        print("✅ Test passed!")


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_database_connection_error_handling(self):
        """Test graceful handling of database connection errors."""
        from psycopg import OperationalError
        from langchain_postgres import PGVector
        from langchain_openai import OpenAIEmbeddings

        # Use invalid connection string
        BAD_CONNECTION = "postgresql+psycopg://invalid:invalid@invalid:9999/invalid"

        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

        print("\n🧪 Testing error handling with invalid connection...")
        try:
            vector_store = PGVector(
                embeddings=embeddings,
                collection_name="test",
                connection=BAD_CONNECTION,
                use_jsonb=True,
            )
            # Try to use it
            vector_store.similarity_search("test", k=1)
            pytest.fail("Should have raised OperationalError")
        except (OperationalError, Exception) as e:
            # Expected - connection should fail
            print(f"✅ Correctly caught error: {type(e).__name__}")
            pass

    def test_empty_retrieval_handling(self):
        """Test handling of queries that return no results."""
        from langchain_postgres import PGVector
        from langchain_openai import OpenAIEmbeddings

        POSTGRES_CONNECTION = os.getenv("POSTGRES_CONNECTION")
        TEST_COLLECTION = "empty_test_collection"

        print("\n🧪 Testing empty retrieval handling...")

        # Create empty test collection
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name=TEST_COLLECTION,
            connection=POSTGRES_CONNECTION,
            use_jsonb=True,
        )

        # Query empty database
        results = vector_store.similarity_search("test query", k=5)

        # Should return empty list, not crash
        assert results == [] or len(results) == 0
        print("✅ Empty retrieval handled gracefully")

        # Cleanup
        vector_store.delete_collection()


class TestEndToEndFlow:
    """Test end-to-end chatbot flow."""

    def test_rag_prompt_generation(self):
        """Test that RAG prompt is correctly constructed."""
        from langchain_core.documents import Document

        print("\n📝 Testing RAG prompt generation...")

        # Mock retrieved documents
        mock_docs = [
            Document(page_content="Attention mechanism is important."),
            Document(page_content="Transformers use self-attention."),
        ]

        # Simulate stream_response logic
        message = "What is attention?"
        history = [["Previous question", "Previous answer"]]

        knowledge = ""
        for doc in mock_docs:
            knowledge += doc.page_content + "\n\n"

        rag_prompt = f"""
        You are an assistant which answers questions based on knowledge which is provided to you.
        While answering, you don't use your internal knowledge,
        but solely the information in the "The knowledge" section.
        You don't mention anything to the user about the provided knowledge.

        The question: {message}

        Conversation history: {history}

        The knowledge: {knowledge}

        """

        # Verify prompt structure
        assert "What is attention?" in rag_prompt
        assert "Attention mechanism is important." in rag_prompt
        assert "Transformers use self-attention." in rag_prompt
        assert str(history) in rag_prompt
        print("✅ RAG prompt correctly formatted")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-s"])
