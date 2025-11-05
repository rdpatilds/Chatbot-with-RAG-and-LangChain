from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_postgres import PGVector
from uuid import uuid4
import os
import sys
from tenacity import retry, stop_after_attempt, wait_exponential
from psycopg import OperationalError

# import the .env file
from dotenv import load_dotenv
load_dotenv()

# configuration
DATA_PATH = r"data"
POSTGRES_CONNECTION = os.getenv("POSTGRES_CONNECTION")

# Validate environment variable
if not POSTGRES_CONNECTION:
    print("❌ Error: POSTGRES_CONNECTION environment variable not found")
    print("   Please ensure .env file exists and contains POSTGRES_CONNECTION")
    sys.exit(1)

# initiate the embeddings model
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large")

# initiate the vector store
try:
    vector_store = PGVector(
        embeddings=embeddings_model,
        collection_name="example_collection",
        connection=POSTGRES_CONNECTION,
        use_jsonb=True,
    )
    print("✅ Successfully connected to pgvector database")
except OperationalError as e:
    print(f"❌ Database connection error: {e}")
    print("   Troubleshooting steps:")
    print("   1. Check if Docker container is running: docker ps | grep pgvector")
    print("   2. Start container: cd pgvector && docker-compose up -d")
    print("   3. Verify connection string in .env file")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error connecting to database: {e}")
    sys.exit(1)

# loading the PDF document
print(f"\n📄 Loading PDF documents from {DATA_PATH}...")
loader = PyPDFDirectoryLoader(DATA_PATH)

try:
    raw_documents = loader.load()
    print(f"✅ Loaded {len(raw_documents)} document(s)")
except Exception as e:
    print(f"❌ Error loading documents: {e}")
    sys.exit(1)

if len(raw_documents) == 0:
    print("❌ No documents found in data directory")
    print(f"   Please add PDF files to: {DATA_PATH}/")
    sys.exit(1)

# splitting the document
print(f"\n✂️  Splitting documents into chunks...")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=100,
    length_function=len,
    is_separator_regex=False,
)

# creating the chunks
chunks = text_splitter.split_documents(raw_documents)
print(f"✅ Created {len(chunks)} chunk(s)")

# creating unique ID's
print(f"\n🔑 Generating unique IDs for chunks...")
uuids = [str(uuid4()) for _ in range(len(chunks))]

# adding chunks to vector store with retry logic for API rate limits
print(f"\n🚀 Ingesting chunks into pgvector database...")
print(f"   (This may take a minute depending on the number of chunks)")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def add_documents_with_retry():
    """Add documents with retry logic for rate limits."""
    return vector_store.add_documents(documents=chunks, ids=uuids)

try:
    add_documents_with_retry()
    print(f"✅ Successfully stored {len(chunks)} chunk(s) in database")
    print(f"\n🎉 Ingestion complete!")
    print(f"\n📊 Summary:")
    print(f"   - Documents loaded: {len(raw_documents)}")
    print(f"   - Chunks created: {len(chunks)}")
    print(f"   - Collection name: example_collection")
    print(f"\n💡 Next step: Run 'python chatbot.py' to start the chatbot")
except Exception as e:
    print(f"\n❌ Error during ingestion: {e}")
    print(f"   Error type: {type(e).__name__}")
    if "rate_limit" in str(e).lower():
        print("   This looks like an OpenAI API rate limit error.")
        print("   Please wait a moment and try again.")
    sys.exit(1)