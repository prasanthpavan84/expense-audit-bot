import pytest
from app.services.policy_service import PolicyService
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService

def test_employee_role_multiplier():
    # Role "Manager" is USA-based by fallback (1.5x multiplier). Meals limit = 50 * 1.5 = 75 USD.
    service = PolicyService()
    expense = {"merchant": "Subway", "amount": 70.0, "currency": "USD", "category": "Meals"}
    allowed, reimb, rej, violations, notes = service.evaluate(expense, role="Manager")
    
    assert allowed == 75.0
    assert reimb == 70.0
    assert rej == 0.0
    assert len(violations) == 0
    assert "Applied Grade Multiplier of 1.5x" in notes
    assert "Section 4.3" in notes

def test_country_specific_limit():
    # EMP103 is in India. Meals limit is 3000 INR.
    service = PolicyService()
    expense = {"merchant": "Subway", "amount": 2500.0, "currency": "INR", "category": "Meals"}
    allowed, reimb, rej, violations, notes = service.evaluate(expense, role="EMP103")
    
    assert allowed == 3000.0 * 1.5 # limit is 3000 * 1.5 manager multiplier = 4500
    assert reimb == 2500.0
    assert rej == 0.0
    assert "limit for India is INR" in notes

def test_citation_logging():
    # Restricted vendor Casino
    service = PolicyService()
    expense = {"merchant": "Casino Club", "amount": 100.0, "currency": "USD", "category": "Other"}
    allowed, reimb, rej, violations, notes = service.evaluate(expense, role="EMP102")
    
    assert reimb == 0.0
    assert len(violations) > 0
    assert "Citation: [Company Policy Section 3.1" in notes

def test_semantic_knowledge_retrieval():
    retriever = KnowledgeRetrievalService()
    # Semantic search with spelling variations & synonyms
    results = retriever.retrieve("food expense allowance", top_k=1)
    assert len(results) > 0
    assert "Meals" in results[0] or "spending limit" in results[0] or "spending" in results[0]
