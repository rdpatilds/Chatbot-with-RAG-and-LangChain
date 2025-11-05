from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
import gradio as gr
import os
import sys
import time
from psycopg import OperationalError

# import the .env file
from dotenv import load_dotenv
load_dotenv()

# configuration
POSTGRES_CONNECTION = os.getenv("POSTGRES_CONNECTION")

# Validate environment variable
if not POSTGRES_CONNECTION:
    print("❌ Error: POSTGRES_CONNECTION environment variable not found")
    print("   Please ensure .env file exists and contains POSTGRES_CONNECTION")
    sys.exit(1)

embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large")

# initiate the model
llm = ChatOpenAI(temperature=0.5, model='gpt-4o-mini')

# connect to pgvector database
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
    print("\n   Troubleshooting steps:")
    print("   1. Check if Docker container is running: docker ps | grep pgvector")
    print("   2. Start container: cd pgvector && docker-compose up -d")
    print("   3. Verify connection string in .env file")
    print("   4. Run verification script: python verify_database.py")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error connecting to database: {e}")
    sys.exit(1)

# Set up the vectorstore to be the retriever
num_results = 5
retriever = vector_store.as_retriever(search_kwargs={'k': num_results})

# call this function for every message added to the chatbot
def stream_response(message, history):
    """
    Stream response from the chatbot with RAG.

    Args:
        message: User's input message
        history: Conversation history

    Yields:
        Partial responses from the LLM
    """
    try:
        # retrieve the relevant chunks based on the question asked
        start_time = time.time()
        docs = retriever.invoke(message)
        retrieval_time = time.time() - start_time

        print(f"\n🔍 Retrieved {len(docs)} chunk(s) in {retrieval_time:.2f}s")

        # Handle empty retrieval results
        if not docs or len(docs) == 0:
            yield "I couldn't find any relevant information in my knowledge base to answer that question. Could you rephrase or ask something else?"
            return

        # add all the chunks to 'knowledge'
        knowledge = ""
        for doc in docs:
            knowledge += doc.page_content + "\n\n"

        # make the call to the LLM (including prompt)
        if message is not None:
            partial_message = ""

            # Fixed typos: "assistent" -> "assistant", "povided" -> "provided"
            rag_prompt = f"""
            You are an assistant which answers questions based on knowledge which is provided to you.
            While answering, you don't use your internal knowledge,
            but solely the information in the "The knowledge" section.
            You don't mention anything to the user about the provided knowledge.

            The question: {message}

            Conversation history: {history}

            The knowledge: {knowledge}

            """

            print(rag_prompt)

            # stream the response to the Gradio App
            try:
                for response in llm.stream(rag_prompt):
                    partial_message += response.content
                    yield partial_message
            except Exception as e:
                error_msg = f"An error occurred while generating the response: {str(e)}"
                print(f"❌ LLM streaming error: {e}")
                yield error_msg

    except OperationalError as e:
        error_msg = "Database connection error. Please check that the PostgreSQL container is running."
        print(f"❌ Database error during retrieval: {e}")
        yield error_msg
    except Exception as e:
        error_msg = f"An error occurred while processing your question: {str(e)}"
        print(f"❌ Error in stream_response: {type(e).__name__}: {e}")
        yield error_msg

# initiate the Gradio app
chatbot = gr.ChatInterface(stream_response, textbox=gr.Textbox(placeholder="Send to the LLM...",
    container=False,
    autoscroll=True,
    scale=7),
)

# launch the Gradio app
print("\n🚀 Launching Gradio chatbot interface...")
print("💡 The chatbot will use pgvector for document retrieval")
chatbot.launch(share=True)