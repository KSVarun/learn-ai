from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.embeddings import OllamaEmbeddings

documents = [
    Document(
        page_content="Dogs are great companions, known for their loyalty and friendliness.",
        metadata={"source": "mammal-pets-doc"},
    ),
    Document(
        page_content="Cats are independent pets that often enjoy their own space.",
        metadata={"source": "mammal-pets-doc"},
    ),
    Document(
        page_content="Goldfish are popular pets for beginners, requiring relatively simple care.",
        metadata={"source": "fish-pets-doc"},
    ),
    Document(
        page_content="Parrots are intelligent birds capable of mimicking human speech.",
        metadata={"source": "bird-pets-doc"},
    ),
    Document(
        page_content="Rabbits are social animals that need plenty of space to hop around.",
        metadata={"source": "mammal-pets-doc"},
    ),
]
from langchain_community.chat_models import ChatOllama

model="llama3"
llm = ChatOllama(model=model)



ollama_emb = OllamaEmbeddings(
    model=model,
)
embeddings = ollama_emb.embed_documents(
    documents
)
# r2 = ollama_emb.embed_query(
#     "What is the second letter of Greek alphabet"
# )
# print(len(embeddings), len(embeddings[0]))
vectorstore = Chroma.from_documents(
    documents,
    embedding=ollama_emb,
)

# print(vectorstore.similarity_search("cat"))

retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5},
)

# print(retriever.batch(["cat", "shark"]))

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

message = """
Answer this question using the provided context only.

{question}

Context:
{context}
"""

prompt = ChatPromptTemplate.from_messages([("human", message)])

rag_chain = {"context": retriever, "question": RunnablePassthrough()} | prompt | llm

response = rag_chain.invoke("tell me about rabbits and dogs")

print(response.content)