"""
Database verification script for pgvector setup.

This script tests the PostgreSQL connection and verifies that pgvector
is properly configured and working.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def print_test_header(test_name):
    """Print formatted test header."""
    print(f"\n{'='*60}")
    print(f"  {test_name}")
    print(f"{'='*60}")

def print_result(test_name, success, message=""):
    """Print test result with emoji."""
    status = "✅" if success else "❌"
    print(f"{status} Test {test_name}: {'PASSED' if success else 'FAILED'}")
    if message:
        print(f"   {message}")

def main():
    """Run all database verification tests."""
    print("\n🔍 Testing pgvector database connection...\n")

    all_tests_passed = True

    # Test 1: Environment Variables
    print_test_header("Test 1: Environment Variables")
    postgres_connection = os.getenv("POSTGRES_CONNECTION")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not postgres_connection:
        print_result("1.1", False, "POSTGRES_CONNECTION environment variable not found")
        all_tests_passed = False
        print("\n❌ Critical error: Cannot proceed without database connection string")
        print("   Please ensure .env file exists and contains POSTGRES_CONNECTION")
        return 1
    else:
        print_result("1.1", True, f"POSTGRES_CONNECTION: {postgres_connection[:30]}...")

    if not openai_key:
        print_result("1.2", False, "OPENAI_API_KEY environment variable not found")
        all_tests_passed = False
    else:
        print_result("1.2", True, f"OPENAI_API_KEY: {openai_key[:20]}...")

    # Test 2: Import Required Packages
    print_test_header("Test 2: Import Required Packages")
    try:
        from langchain_postgres import PGVector
        from langchain_openai import OpenAIEmbeddings
        import psycopg
        print_result("2.1", True, "Successfully imported langchain_postgres and dependencies")
    except ImportError as e:
        print_result("2.1", False, f"Import error: {e}")
        all_tests_passed = False
        print("\n❌ Please install required packages: pip install langchain-postgres psycopg[binary,pool]")
        return 1

    # Test 3: Database Connection
    print_test_header("Test 3: Database Connection")
    try:
        # Try to establish a connection using psycopg
        from psycopg import connect

        # Parse connection string to psycopg format
        conn_str = postgres_connection.replace("postgresql+psycopg://", "postgresql://")

        with connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()
                print_result("3.1", True, f"PostgreSQL version: {version[0][:50]}...")
    except Exception as e:
        print_result("3.1", False, f"Connection error: {e}")
        all_tests_passed = False
        print("\n❌ Could not connect to PostgreSQL")
        print("   Troubleshooting steps:")
        print("   1. Check if Docker container is running: docker ps | grep pgvector")
        print("   2. Start container if needed: cd pgvector && docker-compose up -d")
        print("   3. Verify connection string in .env file")
        return 1

    # Test 4: pgvector Extension
    print_test_header("Test 4: pgvector Extension")
    try:
        with connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
                result = cur.fetchone()
                if result:
                    print_result("4.1", True, f"pgvector extension version: {result[0]}")
                else:
                    print_result("4.1", False, "pgvector extension not found")
                    all_tests_passed = False
                    print("   Run: CREATE EXTENSION vector; in PostgreSQL")
                    return 1
    except Exception as e:
        print_result("4.1", False, f"Error checking extension: {e}")
        all_tests_passed = False
        return 1

    # Test 5: Vector Store Creation
    print_test_header("Test 5: Vector Store Creation")
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name="test_verification_collection",
            connection=postgres_connection,
            use_jsonb=True,
        )
        print_result("5.1", True, "Successfully created PGVector store")

        # Test 6: Sample Vector Operation
        print_test_header("Test 6: Sample Vector Operation")

        # Add a test document
        from langchain_core.documents import Document
        test_doc = Document(
            page_content="This is a test document for verification.",
            metadata={"source": "verification_test"}
        )

        vector_store.add_documents([test_doc], ids=["test_id_verification"])
        print_result("6.1", True, "Successfully added test document")

        # Try a similarity search
        results = vector_store.similarity_search("test document", k=1)
        if results and len(results) > 0:
            print_result("6.2", True, f"Successfully retrieved {len(results)} document(s)")
        else:
            print_result("6.2", False, "No results returned from similarity search")
            all_tests_passed = False

        # Cleanup: Delete test collection
        print_test_header("Test 7: Cleanup")
        try:
            vector_store.delete_collection()
            print_result("7.1", True, "Successfully deleted test collection")
        except Exception as e:
            print_result("7.1", False, f"Cleanup warning: {e}")
            # Not a critical failure

    except Exception as e:
        print_result("5.1/6", False, f"Error: {e}")
        all_tests_passed = False
        print("\n❌ Vector store operations failed")
        print(f"   Error details: {type(e).__name__}: {str(e)}")
        return 1

    # Final Summary
    print("\n" + "="*60)
    if all_tests_passed:
        print("🎉 All tests passed! Database is ready.")
        print("="*60)
        print("\nYou can now:")
        print("  1. Run: python ingest_database.py")
        print("  2. Run: python chatbot.py")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
