"""AWS Costs connector stub.

API URL : https://ce.us-east-1.amazonaws.com/ (Cost Explorer)
Auth     : IAM credentials
Env vars : AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
Category : dev
"""

from brain.connectors.base import BaseConnector


class AWSCostsConnector(BaseConnector):
    name = "aws_costs"
    description = "Daily spend, service breakdown, and cost anomalies from AWS"
    category = "dev"
    required_env = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"]

    async def fetch(self, params: dict | None = None) -> dict:
        raise NotImplementedError("TODO: implement AWS Cost Explorer API integration")

    def briefing_summary(self, data: dict) -> str:
        return "Not implemented"

    async def health_check(self) -> dict:
        return {"healthy": False, "message": "Not implemented"}
