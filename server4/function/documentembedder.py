import pandas as pd
import torch
from sentence_transformers import SentenceTransformer

class DocumentEmbedder:
    def __init__(self, model_name='all-mpnet-base-v2', device='mps'):
        
        self.model = SentenceTransformer(model_name)
        self.device = device
        self.df = None
        self.document_embeddings_dict = None

    def load_documents(self, df):
        
        self.df = df

    def encode_documents(self):
        
        if self.df is None:
            raise ValueError("Documents not loaded. Please call load_documents() first.")

        self.document_embeddings_dict = {}
        
        for col in self.df.columns:
            docs = self.df[col].tolist()
            embeddings = self.model.encode(docs, show_progress_bar=True, device=self.device)
            self.document_embeddings_dict[col] = embeddings

    def get_embeddings(self):
        
        if self.document_embeddings_dict is None:
            raise ValueError("Document embeddings not computed. Please call encode_documents() first.")
        return self.document_embeddings_dict