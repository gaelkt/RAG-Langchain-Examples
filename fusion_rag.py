# from dataclasses import dataclass
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import os
import openai 
from dotenv import load_dotenv
from langchain.load import dumps, loads


load_dotenv()
openai.api_key = os.environ['OPENAI_API_KEY']

# database local path
CHROMA_PATH = "./chroma"

PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""


def reciprocal_rank_fusion(results: list[list], k=60):
    """ Reciprocal_rank_fusion that takes multiple lists of ranked documents
        and an optional parameter k used in the RRF formula """

    # Initialize a dictionary to hold fused scores for each unique document
    fused_scores = {}

    # Iterate through each list of ranked documents
    for docs in results:
        # Iterate through each document in the list, with its rank (position in the list)
        for rank, doc in enumerate(docs):
            # Convert the document to a string format to use as a key (assumes documents can be serialized to JSON)
            doc_str = dumps(doc)
            # If the document is not yet in the fused_scores dictionary, add it with an initial score of 0
            if doc_str not in fused_scores:
                fused_scores[doc_str] = 0
            # Retrieve the current score of the document, if any
            previous_score = fused_scores[doc_str]
            # Update the score of the document using the RRF formula: 1 / (rank + k)
            fused_scores[doc_str] += 1 / (rank + k)

    # Sort the documents based on their fused scores in descending order to get the final reranked results
    reranked_results = [
        (loads(doc), score)
        for doc, score in sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    ]

    # Return the reranked results as a list of tuples, each containing the document and its fused score
    return reranked_results

def rag_fusion_final_rag_chain():


    # Prepare the DB.
    embedding_function = OpenAIEmbeddings()
    vectorstore = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    retriever = vectorstore.as_retriever()
    
    
    
    # Multiple query different perspectives
    template = """You are a helpful assistant that generates multiple search queries based on a single input query. \n
Generate multiple search queries related to: {question} \n
Output (4 queries)
    """
    
    prompt_rag_fusion = ChatPromptTemplate.from_template(template)
    
    from langchain_core.output_parsers import StrOutputParser
    
    llm_rag_fusion = ChatOpenAI(temperature=0)

    generate_queries = (
    prompt_rag_fusion
    | llm_rag_fusion
    | StrOutputParser()
    | (lambda x: x.split("\n"))
)
    
    retrieval_rag_fusion = generate_queries | retriever.map() | reciprocal_rank_fusion
    
    return retrieval_rag_fusion
    

