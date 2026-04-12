import pandas as pd
import torch
from sentence_transformers import SentenceTransformer

class DocumentEmbedder:
    def __init__(self, model_name='all-mpnet-base-v2', device='mps'):
        # 初始化模型和设备
        self.model = SentenceTransformer(model_name)
        self.device = device
        self.df = None
        self.document_embeddings_dict = None

    def load_documents(self, df):
        """
        假设用户传入的 df 的所有列都为字符串类型，不需要额外检测。
        """
        self.df = df

    def encode_documents(self):
        """
        对 DataFrame 的所有列进行编码。
        返回 {column_name: embeddings} 字典，embeddings 为二维数组（N行 x 特征维度）。
        """
        if self.df is None:
            raise ValueError("Documents not loaded. Please call load_documents() first.")

        self.document_embeddings_dict = {}
        # 对 DataFrame 的每一列进行编码
        for col in self.df.columns:
            docs = self.df[col].tolist()
            embeddings = self.model.encode(docs, show_progress_bar=True, device=self.device)
            self.document_embeddings_dict[col] = embeddings

    def get_embeddings(self):
        """
        获取已编码的嵌入结果。
        """
        if self.document_embeddings_dict is None:
            raise ValueError("Document embeddings not computed. Please call encode_documents() first.")
        return self.document_embeddings_dict