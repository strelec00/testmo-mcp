import os
from typing import Any

TESTMO_URL = os.environ.get("TESTMO_URL", "").rstrip("/")
TESTMO_API_KEY = os.environ.get("TESTMO_API_KEY", "")
REQUEST_TIMEOUT = 30.0
UPLOAD_TIMEOUT = 300.0
RATE_LIMIT_DELAY = 0.5
MAX_CASES_PER_REQUEST = 100

# Instance-specific field value mappings.
# Update these to match your Testmo instance. Fetch a few existing cases
# via the API or inspect browser DevTools to discover your IDs.
FIELD_MAPPINGS: dict[str, Any] = {
    "custom_priority": {
        "Critical": 52,
        "High": 1,
        "Medium": 2,
        "Low": 3,
    },
    "custom_type": {
        "Performance": 57,
        "Functional": 59,
        "Usability": 53,
        "Acceptance": 64,
        "Compatibility": 61,
        "Security": 55,
        "Other": 58,
    },
    "custom_creator": {
        "AI Generated": 51,
    },
    "configurations": {
        "Admin Portal": 4,
        "IOS & Android": 5,
        "Insti Web": 10,
    },
    "template_id": {
        "BDD/Gherkin": 4,
        "Steps Table": 1,
    },
    "state_id": {
        "Draft": 1,
        "Review": 2,
        "Approved": 3,
        "Active": 4,
        "Deprecated": 5,
    },
    "status_id": {
        "Incomplete": 1,
        "Complete": 2,
    },
    "result_status_id": {
        "Untested": 1,
        "Passed": 2,
        "Failed": 3,
        "Retest": 4,
        "Blocked": 5,
        "Skipped": 6,
    },
    "automation_run_status": {
        "Success": 2,
        "Failure": 3,
        "Running": 4,
    },
    "custom_issues_tags_and_configurations_added": {
        "Yes": 66,
        "No": 67,
    },
    "tags": {
        "domain": [
            "assets-crypto",
            "assets-noncrypto",
            "services-usergrowth",
            "services-platform",
            "wealth-hnwi",
        ],
        "tier-type": ["ui-verification", "e2e", "negative"],
        "scope": ["regression", "smoke", "sanity"],
        "risk": ["risk-financial", "risk-security", "risk-compliance"],
    },
    "defaults": {
        "template_id": 4,
        "state_id": 1,
        "status_id": 2,
        "custom_priority": 2,
        "custom_type": 59,
        "custom_creator": 51,
        "custom_issues_tags_and_configurations_added": 66,
    },
}
