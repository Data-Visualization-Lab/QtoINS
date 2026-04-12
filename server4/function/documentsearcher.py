import torch
from sentence_transformers import SentenceTransformer, util

class DocumentSearcher:
    def __init__(self, model_name='all-mpnet-base-v2', device='mps'):
        self.model = SentenceTransformer(model_name)
        self.device = device
        self.documents = None
        self.document_embeddings = None

    def set_documents(self, documents):
        self.documents = documents

    def encode_documents(self):
        if self.documents is None:
            raise ValueError("Documents not set. Please call set_documents() first.")
        self.document_embeddings = self.model.encode(self.documents, show_progress_bar=True, device=self.device)

    def set_document_embeddings(self, documents, embeddings):
        if len(documents) != len(embeddings):
            raise ValueError("The number of documents and embeddings must match.")
        
        self.documents = documents
        if not isinstance(embeddings, torch.Tensor):
            embeddings = torch.tensor(embeddings, dtype=torch.float32)
        self.document_embeddings = embeddings

    def search(self, query):
        if self.document_embeddings is None:
            raise ValueError("Document embeddings not set. Please call encode_documents() or set_document_embeddings() first.")

        query_embedding = self.model.encode(query, device=self.device)
        similarities = util.cos_sim(query_embedding, self.document_embeddings)

        sorted_values, sorted_indices = torch.sort(similarities, dim=1, descending=True)
        sorted_indices = sorted_indices.squeeze(0)

        
        seen_docs = set()
        unique_sorted_documents = []

        for idx in sorted_indices:
            doc = self.documents[idx]
            if doc not in seen_docs:
                seen_docs.add(doc)
                unique_sorted_documents.append(doc)

        return unique_sorted_documents

