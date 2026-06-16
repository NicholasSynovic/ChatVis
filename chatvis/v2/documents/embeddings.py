"""FAISS-backed embedding index over the ParaView operations corpus.

Side effects on import: downloads/loads the MiniLM sentence-transformer,
builds the FAISS index in memory, writes ``paraview_operations_faiss.index``
and ``metadata_lookup.pkl`` to the current working directory, then reads them
back. The write/read round-trip is preserved as upstream (redundant but
behavior-preserving).
"""

import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from chatvis.v2.documents.corpus import operations_json

# Load a smaller Sentence Transformer model for efficiency
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


# Function to generate embeddings safely (one by one)
def get_embedding(text):
    return model.encode(text, convert_to_numpy=True).astype(np.float32)


# Initialize FAISS index
d = model.get_sentence_embedding_dimension()  # Get correct embedding dimension
index = faiss.IndexFlatL2(d)  # Use L2 distance metric for FAISS

# Generate and add embeddings for each operation
metadata_lookup = []
for op in operations_json:
    text = op["name"] + " " + op["description"] + " " + op["code_snippet"]
    embedding = get_embedding(text).reshape(1, -1)  # Reshape for FAISS
    index.add(embedding)
    metadata_lookup.append(op)  # Store the original entry

# Save the FAISS index to disk
faiss.write_index(index, "paraview_operations_faiss.index")

with open("metadata_lookup.pkl", "wb") as f:
    pickle.dump(metadata_lookup, f)
print("All ParaView operations stored in FAISS database.")

# Load FAISS index (ensure it exists)
index = faiss.read_index("paraview_operations_faiss.index")
with open("metadata_lookup.pkl", "rb") as f:
    metadata_lookup = pickle.load(f)


# Search similar operations
def search_similar_operation(query_text, top_k=5):
    # Generate query embedding
    query_embedding = get_embedding(query_text).reshape(1, -1)

    # Ensure there are enough vectors in the FAISS index before searching
    total_vectors = index.ntotal
    if total_vectors == 0:
        print("Error: FAISS index is empty! No vectors found.")
        return []

    # Get nearest neighbors from FAISS
    top_k = min(top_k, total_vectors)  # Ensure we don't exceed available entries
    distances, indices = index.search(query_embedding, top_k)

    matches = []
    for idx in indices[0]:  # I is shape (1, k)
        match = metadata_lookup[idx]
        matches.append(match)

    return matches
