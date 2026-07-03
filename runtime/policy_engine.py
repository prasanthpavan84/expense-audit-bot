"""runtime/policy_engine.py

Placeholder policy engine that can be extended to enforce business rules.
"""

class PolicyEngine:
    """Simple policy engine.

    Currently only logs policies; extend with real validation logic.
    """
    def __init__(self):
        self.policies = []

    def add_policy(self, policy_callable):
        """Add a policy function that receives a request dict and returns bool.
        """
        self.policies.append(policy_callable)

    def evaluate(self, request):
        """Run all policies against the request; return True if all pass.
        """
        return all(policy(request) for policy in self.policies)
