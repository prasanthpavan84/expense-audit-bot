import json
import os
from typing import List, Dict, Any, Optional

def load_database() -> List[Dict[str, Any]]:
    db_path = os.path.join(os.path.dirname(__file__), "database.json")
    if os.path.exists(db_path):
        try:
            with open(db_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_database(data: List[Dict[str, Any]]) -> None:
    db_path = os.path.join(os.path.dirname(__file__), "database.json")
    try:
        with open(db_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def add_expense_to_db(expense: Dict[str, Any]) -> None:
    db = load_database()
    # Check if duplicate id exists to avoid duplicate insertions
    if any(item.get("id") == expense.get("id") for item in db):
        return
    db.append(expense)
    save_database(db)

def execute_query(query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a structured query against database.json.
    
    query_params schema:
    {
      "action": "FILTER" | "COMPARE_DEPTS" | "SUMMARIZE_EMPLOYEE" | "EXPLAIN",
      "category": str,
      "amount_min": float,
      "amount_max": float,
      "currency": str,
      "employee_id": str,
      "department": str,
      "target_expense_id": str
    }
    """
    db = load_database()
    action = query_params.get("action", "FILTER").upper()
    
    result = {"action": action, "data": []}
    
    if action == "FILTER":
        filtered = []
        for exp in db:
            # Category match (lenient)
            if query_params.get("category"):
                cat = query_params["category"].lower()
                exp_cat = str(exp.get("category", "")).lower()
                if cat not in exp_cat:
                    continue
            
            # Currency conversion check or direct match
            curr = query_params.get("currency")
            if curr:
                exp_curr = str(exp.get("currency", "")).upper()
                if curr.upper() != exp_curr:
                    continue
                    
            # Amount min
            amt_min = query_params.get("amount_min")
            if amt_min is not None:
                exp_amt = float(exp.get("amount", 0.0))
                if exp_amt < float(amt_min):
                    continue
                    
            # Amount max
            amt_max = query_params.get("amount_max")
            if amt_max is not None:
                exp_amt = float(exp.get("amount", 0.0))
                if exp_amt > float(amt_max):
                    continue
                    
            # Employee match
            emp_id = query_params.get("employee_id")
            if emp_id:
                exp_emp = str(exp.get("employee_id", "")).upper()
                if emp_id.upper() not in exp_emp:
                    continue
                    
            # Department match
            dept = query_params.get("department")
            if dept:
                exp_dept = str(exp.get("department", "")).lower()
                if dept.lower() not in exp_dept:
                    continue
                    
            filtered.append(exp)
            
        result["data"] = filtered
        result["summary"] = {
            "total_count": len(filtered),
            "total_claimed": sum(float(e.get("amount", 0.0)) for e in filtered)
        }
        
    elif action == "COMPARE_DEPTS":
        depts = {}
        for exp in db:
            dept = exp.get("department", "Other")
            if dept not in depts:
                depts[dept] = {
                    "total_claimed": 0.0,
                    "reimbursable": 0.0,
                    "rejected": 0.0,
                    "count": 0,
                    "fraud_scores": []
                }
            
            amt = float(exp.get("amount", 0.0))
            # Direct summation (ignoring conversions or assuming normalized USD values for comparison)
            # In a real environment, we'd convert all to USD. Let's convert EUR/INR to USD for comparison:
            curr = exp.get("currency", "USD").upper()
            rate = 1.0
            if curr == "EUR":
                rate = 1.10
            elif curr == "INR":
                rate = 0.012
            elif curr == "GBP":
                rate = 1.30
                
            amt_usd = amt * rate
            
            depts[dept]["total_claimed"] += amt_usd
            depts[dept]["count"] += 1
            if exp.get("status") in ["Approved", "Approved with Exception", "Approved by Auditor"]:
                depts[dept]["reimbursable"] += amt_usd
            elif exp.get("status") == "Partially Approved":
                # For partial, assume allowed/reimbursable is capped
                depts[dept]["reimbursable"] += amt_usd * 0.7  # approximation for comparison
                depts[dept]["rejected"] += amt_usd * 0.3
            else:
                depts[dept]["rejected"] += amt_usd
                
            fraud = exp.get("fraud_score", 0)
            depts[dept]["fraud_scores"].append(fraud)
            
        comparison_list = []
        for d_name, d_data in depts.items():
            avg_fraud = sum(d_data["fraud_scores"]) / len(d_data["fraud_scores"]) if d_data["fraud_scores"] else 0.0
            comparison_list.append({
                "department": d_name,
                "total_claimed": d_data["total_claimed"],
                "reimbursable": d_data["reimbursable"],
                "rejected": d_data["rejected"],
                "claims_count": d_data["count"],
                "avg_fraud_risk": avg_fraud,
                "risk_level": "High" if avg_fraud >= 60 else "Medium" if avg_fraud >= 30 else "Low"
            })
            
        result["data"] = comparison_list
        
    elif action == "SUMMARIZE_EMPLOYEE":
        emp_id = query_params.get("employee_id", "").upper()
        emp_records = [e for e in db if str(e.get("employee_id", "")).upper() == emp_id]
        
        categories = {}
        total_claimed = 0.0
        total_reimbursable = 0.0
        fraud_scores = []
        
        for exp in emp_records:
            cat = exp.get("category", "Other")
            amt = float(exp.get("amount", 0.0))
            curr = exp.get("currency", "USD")
            
            total_claimed += amt # Note: keeping original currencies in breakdown or listing them
            if exp.get("status") in ["Approved", "Approved with Exception", "Approved by Auditor"]:
                total_reimbursable += amt
                
            categories[cat] = categories.get(cat, 0.0) + amt
            fraud_scores.append(exp.get("fraud_score", 0))
            
        result["data"] = {
            "employee_id": emp_id,
            "department": emp_records[0].get("department", "Unknown") if emp_records else "Unknown",
            "total_claims": len(emp_records),
            "total_claimed": total_claimed,
            "total_reimbursable": total_reimbursable,
            "avg_fraud_score": sum(fraud_scores) / len(fraud_scores) if fraud_scores else 0.0,
            "category_breakdown": categories,
            "records": emp_records
        }
        
    elif action == "EXPLAIN":
        target_id = query_params.get("target_expense_id")
        
        # If no explicit ID is provided, check for latest rejected expense
        matched_exp = None
        if target_id:
            for exp in db:
                if str(exp.get("id")) == str(target_id):
                    matched_exp = exp
                    break
        else:
            # Find the latest rejected record to explain
            rejected_records = [e for e in db if e.get("status") == "Rejected"]
            if rejected_records:
                matched_exp = rejected_records[-1]
            elif db:
                # Find latest record
                matched_exp = db[-1]
                
        if matched_exp:
            result["data"] = matched_exp
        else:
            result["data"] = {}
            result["error"] = "No matching expense found to explain."
            
    return result
