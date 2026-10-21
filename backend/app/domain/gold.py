"""Hand-labeled synthetic fixtures.

Rules used when the grades were assigned (not derived from the scorer):

- 3: obvious primary role; the stated skills cover that role's mandatory set
  at a working level, aliases allowed as the same skill.
- 2: close variant or plausible next step with at least one clear gap.
- 1: some transferable skill, but the role is a stretch.
- 0: almost no transferable overlap with the stated skills.

These grades are judgments about the synthetic ontology. They are not evidence
from employees, applicants, or hiring outcomes.

Dataset version lives in ``app.domain.constants.DATASET_VERSION``. Expanding
fixtures must not be tuned to invent a graph ranking win over overlap.
"""

from __future__ import annotations

GOLD_PROFILES: list[dict[str, object]] = [
    {
        "id": "synonym_specialist",
        "skills": [
            ("PostgreSQL", 4, "Postgres"),
            ("JavaScript", 4, "js"),
            ("Excel", 3, "ms excel"),
            ("Git", 3, "Git"),
        ],
        "labels": {
            "Backend Engineer": 3,
            "Full Stack Engineer": 2,
            "Frontend Engineer": 2,
            "Data Analyst": 1,
            "Analytics Engineer": 1,
            "QA Engineer": 0,
            "Security Analyst": 0,
            "UX Designer": 0,
        },
    },
    {
        "id": "data_analyst_demo",
        "skills": [
            ("SQL", 4, "SQL"),
            ("Excel", 5, "Excel"),
            ("Python", 3, "Python"),
            ("pandas", 3, "pandas"),
            ("Statistics", 4, "Statistics"),
            ("Tableau", 4, "Tableau"),
            ("Data Visualization", 4, "Data Visualization"),
            ("A/B Testing", 3, "A/B Testing"),
            ("Git", 2, "Git"),
            ("PostgreSQL", 3, "Postgres"),
            ("Stakeholder Communication", 3, "Stakeholder Communication"),
            ("Requirements Gathering", 3, "Requirements Gathering"),
            ("Jupyter", 2, "Jupyter"),
            ("Data Quality", 2, "Data Quality"),
        ],
        "labels": {
            "Data Analyst": 3,
            "Senior Data Analyst": 2,
            "BI Developer": 2,
            "Analytics Engineer": 2,
            "Analytics Manager": 1,
            "Data Engineer": 1,
            "Data Scientist": 1,
            "Product Manager": 1,
            "ML Engineer": 0,
            "Frontend Engineer": 0,
            "QA Engineer": 0,
            "DevOps Engineer": 0,
        },
    },
    {
        "id": "qa_manual",
        "skills": [
            ("Manual Testing", 4, "Manual Testing"),
            ("Test Planning", 4, "Test Planning"),
            ("Bug Reporting", 4, "Bug Reporting"),
            ("API Testing", 2, "API Testing"),
        ],
        "labels": {
            "QA Engineer": 3,
            "QA Lead": 2,
            "Automation Engineer": 1,
            "SDET": 1,
            "Backend Engineer": 0,
            "Frontend Engineer": 0,
            "Data Analyst": 0,
            "Security Analyst": 0,
        },
    },
    {
        "id": "automation_ready",
        "skills": [
            ("Manual Testing", 3, "Manual Testing"),
            ("Test Automation", 4, "Test Automation"),
            ("Selenium", 4, "Selenium"),
            ("JavaScript", 3, "JavaScript"),
            ("API Testing", 4, "API Testing"),
            ("Git", 3, "Git"),
            ("Pytest", 3, "Pytest"),
        ],
        "labels": {
            "Automation Engineer": 3,
            "SDET": 3,
            "QA Engineer": 2,
            "QA Lead": 1,
            "Frontend Engineer": 1,
            "Backend Engineer": 1,
            "Data Analyst": 0,
            "DevOps Engineer": 0,
        },
    },
    {
        "id": "cloud_admin",
        "skills": [
            ("Linux", 4, "Linux"),
            ("Bash", 4, "Bash"),
            ("Docker", 3, "Docker"),
            ("AWS", 3, "AWS"),
            ("Monitoring", 3, "Monitoring"),
            ("Git", 3, "Git"),
        ],
        "labels": {
            "DevOps Engineer": 3,
            "Site Reliability Engineer": 2,
            "Platform Engineer": 2,
            "Backend Engineer": 1,
            "Security Analyst": 1,
            "Data Engineer": 1,
            "Data Analyst": 0,
            "UX Designer": 0,
            "Product Manager": 0,
        },
    },
    {
        "id": "alias_heavy",
        "scenario": "alias-heavy",
        "skills": [
            ("PostgreSQL", 4, "Postgres"),
            ("JavaScript", 4, "js"),
            ("Excel", 3, "ms excel"),
            ("Power BI", 3, "powerbi"),
            ("scikit-learn", 3, "sklearn"),
            ("Git", 3, "git"),
        ],
        "labels": {
            "Backend Engineer": 3,
            "Full Stack Engineer": 2,
            "BI Developer": 2,
            "Data Analyst": 1,
            "Data Scientist": 1,
            "QA Engineer": 0,
            "UX Designer": 0,
            "Product Manager": 0,
        },
    },
    {
        "id": "cold_start",
        "scenario": "cold-start",
        "skills": [
            ("Excel", 2, "Excel"),
            ("Git", 1, "Git"),
        ],
        "labels": {
            "Data Analyst": 1,
            "QA Engineer": 0,
            "Backend Engineer": 0,
            "Frontend Engineer": 0,
            "DevOps Engineer": 0,
            "Product Manager": 0,
            "UX Designer": 0,
            "Security Analyst": 0,
        },
    },
    {
        "id": "missing_mandatory_gap",
        "scenario": "missing-mandatory",
        "skills": [
            ("SQL", 4, "SQL"),
            ("Python", 4, "Python"),
            ("Git", 3, "Git"),
            ("pandas", 3, "pandas"),
        ],
        "labels": {
            "Analytics Engineer": 2,
            "Data Analyst": 2,
            "Data Engineer": 1,
            "Backend Engineer": 1,
            "ML Engineer": 0,
            "QA Engineer": 0,
            "UX Designer": 0,
            "Product Manager": 0,
        },
    },
    {
        "id": "misleading_related",
        "scenario": "misleading-related",
        "skills": [
            ("SQL", 5, "SQL"),
            ("PostgreSQL", 4, "Postgres"),
            ("Git", 3, "Git"),
        ],
        "labels": {
            "Data Analyst": 2,
            "Backend Engineer": 2,
            "Analytics Engineer": 1,
            "Data Engineer": 1,
            "QA Engineer": 0,
            "UX Designer": 0,
            "Product Manager": 0,
            "Security Analyst": 0,
        },
    },
    {
        "id": "multi_role_ambiguous",
        "scenario": "multi-role",
        "skills": [
            ("Manual Testing", 4, "Manual Testing"),
            ("Test Planning", 4, "Test Planning"),
            ("Bug Reporting", 4, "Bug Reporting"),
            ("Test Automation", 4, "Test Automation"),
            ("Selenium", 4, "Selenium"),
            ("JavaScript", 3, "JavaScript"),
            ("API Testing", 4, "API Testing"),
            ("Git", 3, "Git"),
            ("Pytest", 3, "Pytest"),
        ],
        "labels": {
            "QA Engineer": 3,
            "Automation Engineer": 3,
            "SDET": 3,
            "QA Lead": 2,
            "Frontend Engineer": 1,
            "Backend Engineer": 0,
            "Data Analyst": 0,
            "DevOps Engineer": 0,
        },
    },
]
