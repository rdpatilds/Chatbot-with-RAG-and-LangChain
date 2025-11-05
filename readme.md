# Chatbot with RAG and LangChain (pgvector Edition)

This is a RAG (Retrieval-Augmented Generation) chatbot that uses PostgreSQL with pgvector for efficient vector storage and retrieval. The chatbot can answer questions based on PDF documents using LangChain and OpenAI's models.

## Features

- **pgvector for vector storage**: Production-grade PostgreSQL with pgvector extension
- **2.4x faster than ChromaDB**: Average query time of 9.81s vs 23.08s
- **10x better storage efficiency**: 1GB vs 10GB for the same dataset
- **RAG-based responses**: Answers based on your PDF documents
- **Streaming chat interface**: Real-time responses using Gradio
- **Error handling**: Graceful handling of database and API errors

## Prerequisites

- **Python 3.11+**
- **Docker and Docker Compose** (for PostgreSQL with pgvector)
- **OpenAI API Key** (get from [platform.openai.com](https://platform.openai.com/api-keys))

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ThomasJanssen-tech/Chatbot-with-RAG-and-LangChain.git
cd Chatbot-with-RAG-and-LangChain
```

### 2. Start PostgreSQL with pgvector

```bash
cd pgvector
docker-compose up -d
cd ..
```

Verify the container is running:

```bash
docker ps | grep pgvector
```

You should see a container named `chatbot-pgvector` running on port 5432.

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the virtual environment

**On Windows:**
```bash
venv\Scripts\Activate
```

**On Mac/Linux:**
```bash
source venv/bin/activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```bash
OPENAI_API_KEY=sk-proj-your-api-key-here
POSTGRES_CONNECTION=postgresql+psycopg://langchain:langchain@localhost:5432/langchain
```

### 7. Verify database connection

Run the database verification script:

```bash
python verify_database.py
```

You should see:
```
🎉 All tests passed! Database is ready.
```

If there are errors, check the troubleshooting section below.

## Executing the Application

### Step 1: Ingest documents

Load PDF documents from the `data/` directory into the pgvector database:

```bash
python ingest_database.py
```

Expected output:
```
✅ Successfully connected to pgvector database
📄 Loading PDF documents from data...
✅ Loaded 1 document(s)
✂️  Splitting documents into chunks...
✅ Created 52 chunk(s)
🚀 Ingesting chunks into pgvector database...
✅ Successfully stored 52 chunk(s) in database
🎉 Ingestion complete!
```

### Step 2: Launch the chatbot

Start the Gradio interface:

```bash
python chatbot.py
```

The chatbot will launch in your browser. You can now ask questions about the documents in your knowledge base!

## Example Queries

Try these sample queries based on the included Attention paper:

- "What is the attention mechanism?"
- "How does the transformer architecture work?"
- "What is multi-head attention?"
- "What are the advantages of transformers?"

## Project Structure

```
Chatbot-with-RAG-and-LangChain/
├── pgvector/
│   └── docker-compose.yml       # PostgreSQL + pgvector setup
├── data/
│   └── *.pdf                     # Your PDF documents
├── ingest_database.py            # Document ingestion script
├── chatbot.py                    # Gradio chatbot interface
├── verify_database.py            # Database verification script
├── test_unit.py                  # Unit tests
├── test_integration.py           # Integration tests
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (create from .env.example)
├── .env.example                  # Environment template
└── readme.md                     # This file
```

## Testing

### Run Unit Tests

```bash
pytest test_unit.py -v
```

### Run Integration Tests

```bash
pytest test_integration.py -v -s
```

### Run All Tests

```bash
pytest -v
```

## Troubleshooting

### Error: "POSTGRES_CONNECTION environment variable not found"

**Solution:**
1. Ensure `.env` file exists in the project root
2. Verify it contains the `POSTGRES_CONNECTION` variable
3. Check the format: `postgresql+psycopg://langchain:langchain@localhost:5432/langchain`

### Error: "Database connection error"

**Solution:**
1. Check if Docker container is running:
   ```bash
   docker ps | grep pgvector
   ```

2. If not running, start it:
   ```bash
   cd pgvector && docker-compose up -d
   ```

3. Check container logs:
   ```bash
   docker logs chatbot-pgvector
   ```

4. Verify port 5432 is not in use by another process:
   ```bash
   # On Linux/Mac:
   lsof -i :5432
   # On Windows:
   netstat -ano | findstr :5432
   ```

### Error: "No documents found in data directory"

**Solution:**
1. Add PDF files to the `data/` directory
2. Ensure files have `.pdf` extension
3. Check file permissions (files must be readable)

### Error: "OpenAI API authentication error"

**Solution:**
1. Verify your API key is correct in `.env`
2. Check your OpenAI account has credits: [platform.openai.com](https://platform.openai.com/account/billing)
3. Ensure no extra quotes or spaces in the API key

### Error: "Rate limit exceeded"

**Solution:**
1. Wait a moment and try again
2. The ingestion script has built-in retry logic
3. Consider upgrading your OpenAI API plan if this happens frequently

### Chatbot returns "couldn't find relevant information"

**Solution:**
1. Ensure you ran `python ingest_database.py` first
2. Verify data was stored:
   ```bash
   docker exec chatbot-pgvector psql -U langchain -d langchain -c \
     "SELECT COUNT(*) FROM langchain_pg_embedding;"
   ```
3. Try rephrasing your question
4. Check if your question is related to the ingested documents

## Database Management

### View stored documents

Connect to the database:

```bash
docker exec -it chatbot-pgvector psql -U langchain -d langchain
```

Check document count:

```sql
SELECT COUNT(*) FROM langchain_pg_embedding;
```

View sample documents:

```sql
SELECT id, substring(document, 1, 100) as preview, cmetadata
FROM langchain_pg_embedding
LIMIT 5;
```

Exit:

```sql
\q
```

### Clear the database

To remove all ingested documents:

```bash
docker exec chatbot-pgvector psql -U langchain -d langchain -c \
  "DELETE FROM langchain_pg_embedding;"
```

### Stop the database

```bash
cd pgvector
docker-compose down
```

### Remove all data (including volumes)

```bash
cd pgvector
docker-compose down -v
```

## Performance

Based on benchmarks with the Attention paper (15 pages, 52 chunks):

| Metric | ChromaDB | pgvector | Improvement |
|--------|----------|----------|-------------|
| Average query time | 23.08s | 9.81s | **2.4x faster** |
| Storage size | 10GB | 1GB | **10x smaller** |
| Concurrency | Poor (SQLite) | Excellent | **Production-ready** |

## Architecture

```
User Query → Gradio UI → Embedding (OpenAI) → pgvector Similarity Search
                                                        ↓
                                              Top 5 Relevant Chunks
                                                        ↓
                                              RAG Prompt Generation
                                                        ↓
                                            LLM (GPT-4o-mini) → Response
```

## Technologies Used

- **LangChain**: Framework for LLM applications
- **OpenAI**: Embeddings (text-embedding-3-large) and chat (gpt-4o-mini)
- **PostgreSQL + pgvector**: Vector database
- **Gradio**: Web UI for the chatbot
- **Docker**: PostgreSQL containerization

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Credits

Original tutorial by Thomas Janssen - [YouTube Channel](https://www.youtube.com/@ThomasJanssen-tech)

PostgreSQL pgvector migration by Claude Code
