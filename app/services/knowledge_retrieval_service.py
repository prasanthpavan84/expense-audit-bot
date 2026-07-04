import os
import json
import math
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.services.base_service import BaseService

class KnowledgeRetrievalService(BaseService):
    """Business service providing semantic RAG-based search against corporate knowledge bases."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.policy_data = {}
        self.chunks: List[str] = []
        self.embeddings: List[List[float]] = []
        self._load_and_chunk_policy()

    def _load_and_chunk_policy(self):
        """Load standard company policy json and split it into readable text chunks."""
        config_dir = Path(__file__).resolve().parent.parent / "config"
        fallback_file = config_dir / "policy_v1.json"
        
        if not fallback_file.exists():
            fallback_file = Path(__file__).resolve().parent.parent.parent / "app" / "company_policy.json"

        if fallback_file.exists():
            try:
                with open(fallback_file, "r", encoding="utf-8") as f:
                    self.policy_data = json.load(f)
            except Exception:
                pass

        # Build chunks from policy_data keys/values
        self.chunks.clear()
        if self.policy_data:
            # 1. Add limits
            limits = self.policy_data.get("category_limits", {})
            for cat, limit_info in limits.items():
                self.chunks.append(f"The standard corporate expense spending limit for {cat} is {limit_info.get('limit')} {limit_info.get('currency', 'USD')} per transaction.")
            
            # 2. Add INR limits
            inr_limits = self.policy_data.get("inr_limits", {})
            for cat, val in inr_limits.items():
                self.chunks.append(f"The Indian Rupee (INR) limit for {cat} is {val} INR.")

            # 3. Add restricted vendors
            restricted = self.policy_data.get("restricted_vendors", [])
            if restricted:
                self.chunks.append(f"Restricted vendor types where spending is strictly prohibited include: {', '.join(restricted)}.")

            # 4. Add multipliers
            mults = self.policy_data.get("role_multipliers", {})
            for role, factor in mults.items():
                self.chunks.append(f"The approval limit multiplier factor for employee role '{role}' is {factor}x.")
        else:
            # Hardcoded fallbacks if no file
            self.chunks = [
                "The corporate expense limit for Meals is $50 USD (₹3,000 INR) per transaction.",
                "The Hotel and accommodation limit is $150 USD (₹12,000 INR) per night.",
                "The corporate limit for Software purchases and licenses is $100 USD (₹6,000 INR).",
                "Restricted vendors include casino, gambling, liquor, pubs, and bar venues.",
                "Role multipliers: Intern gets 0.5x, Associate gets 1.0x, Manager gets 1.5x, Executive gets 3.0x."
            ]

    def _build_index(self):
        """Embed all chunks using Gemini API (if key present), else rely on keyword search."""
        self.embeddings = []
        if not self.api_key:
            return

        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            
            # Batch embed contents
            response = client.models.embed_content(
                model="text-embedding-004",
                contents=self.chunks
            )
            
            if response and response.embeddings:
                for emb in response.embeddings:
                    self.embeddings.append(emb.values)
        except Exception:
            # Fallback: empty embeddings, falls back to keyword intersection
            self.embeddings = []

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude_v1 = math.sqrt(sum(a * a for a in v1))
        magnitude_v2 = math.sqrt(sum(b * b for b in v2))
        if magnitude_v1 == 0 or magnitude_v2 == 0:
            return 0.0
        return dot_product / (magnitude_v1 * magnitude_v2)

    def retrieve(self, query: str, top_k: int = 2) -> List[str]:
        """Retrieve the top-k most semantically relevant policy chunks for a query."""
        if not query:
            return []

        # Lazy embed index
        if self.api_key and not self.embeddings:
            self._build_index()

        # Try semantic embedding similarity search
        if self.api_key and self.embeddings:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                response = client.models.embed_content(
                    model="text-embedding-004",
                    contents=query
                )
                if response and response.embeddings:
                    query_vector = response.embeddings[0].values
                    scored_chunks = []
                    for idx, chunk_vector in enumerate(self.embeddings):
                        sim = self._cosine_similarity(query_vector, chunk_vector)
                        scored_chunks.append((sim, self.chunks[idx]))
                    # Sort descending
                    scored_chunks.sort(key=lambda x: x[0], reverse=True)
                    return [chunk for sim, chunk in scored_chunks[:top_k]]
            except Exception:
                pass

        # Fallback: Keyword intersection matching
        query_words = set(re.sub(r"[^\w\s]", "", query.lower()).split())
        scored_chunks = []
        for chunk in self.chunks:
            chunk_words = set(re.sub(r"[^\w\s]", "", chunk.lower()).split())
            intersection = query_words.intersection(chunk_words)
            scored_chunks.append((len(intersection), chunk))
            
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [chunk for score, chunk in scored_chunks[:top_k]]
