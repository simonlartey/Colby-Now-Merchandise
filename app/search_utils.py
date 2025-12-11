import numpy as np
from sentence_transformers import SentenceTransformer
import pickle

# Singleton model instance
_model = None


def get_model():
    """
    Returns the singleton instance of the SentenceTransformer model.
    """
    global _model
    if _model is None:
        # 'all-MiniLM-L6-v2' is a good balance of speed and quality
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def generate_embedding(text):
    """
    Generates a dense vector embedding for the given text.
    Returns a numpy array (or list) suitable for storage.
    """
    if not text:
        return None
    model = get_model()
    # dimensions: 384
    embedding = model.encode(text)
    return embedding


def cosine_similarity(vec_a, vec_b):
    """
    Computes cosine similarity between two vectors.
    """
    if vec_a is None or vec_b is None:
        return 0.0

    # Ensure they are numpy arrays
    a = np.array(vec_a)
    b = np.array(vec_b)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return np.dot(a, b) / (norm_a * norm_b)
