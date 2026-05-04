
SYSTEM_PROMPT = """
You are a local AI advisor for a venture studio.
You help create templates, summaries, checklists, and advisory drafts for startups.
You may use founder startup documents as reference experience, but you must not copy confidential or proprietary details directly.
Extract general patterns, frameworks, and best practices.
When advising a new company, tailor your answer to the company profile provided by the user.
Always provide structured, practical output.
If the retrieved context does not support an answer, say what is missing.
For legal, regulatory, financial, HR, medical, tax, or investment-related topics, provide educational and draft guidance only and recommend expert review.
"""

GRAPHRAG_PRIVACY_GUARD = """
You are working with redacted proprietary parent-company knowledge.
Never reconstruct or guess hidden names, values, clauses, amounts, or identifiers.
Use knowledge only to extract generalized patterns and reusable business guidance.
Do not copy original wording from source documents.
If evidence is weak, say what is missing.
For legal, regulatory, financial, HR, medical, tax, or investment-related topics, provide educational draft guidance only and recommend expert review.
"""

GRAPHRAG_OUTPUT_FORMAT = """
Please structure your response using these sections:
## Summary
## Relevant Generalized Knowledge
## Recommended Approach for the New Company
## Draft / Checklist / Advisory Output
## Assumptions
## Risks and Expert Review Needed
## Sources Used
"""


def build_prompt(company_profile: dict, user_query: str, retrieved_docs: list) -> str:
    """Build a guarded prompt combining system prompt, company profile, and retrieved docs."""
    parts = [SYSTEM_PROMPT]
    parts.append("\n## Company Profile:\n")
    for k, v in company_profile.items():
        parts.append(f"- {k}: {v}\n")
    parts.append("\n## User Query:\n")
    parts.append(user_query + "\n")
    parts.append("\n## Retrieved Context (summaries):\n")
    if retrieved_docs:
        for d in retrieved_docs:
            parts.append(f"- Source: {d.get('path', 'unknown')}\n")
            snippet = d.get("text", "")[:800].replace("\n", " ") if d.get("text") else ""
            parts.append(f"  {snippet}\n---\n")
    else:
        parts.append("No relevant local documents were found.\n")

    parts.append(
        "\nPlease follow the output structure:\n"
        "## Summary\n## Recommended Approach\n## Draft / Template / Analysis\n"
        "## Key Assumptions\n## Risks or Review Needed\n## Sources Used\n"
    )
    return "\n".join(parts)


def build_graphrag_prompt(company_profile: dict, user_query: str, compact_context: str) -> str:
    """Build a GraphRAG prompt with privacy guard, profile, context, and output format."""
    profile_str = "\n".join(f"- {k}: {v}" for k, v in company_profile.items())
    # Truncate profile if necessary
    from config import MAX_COMPANY_PROFILE_CHARS
    profile_str = profile_str[:MAX_COMPANY_PROFILE_CHARS]

    prompt = (
        GRAPHRAG_PRIVACY_GUARD.strip()
        + "\n\n## Company Profile:\n"
        + profile_str
        + "\n\n## User Query:\n"
        + user_query
        + "\n\n## Retrieved Knowledge Context:\n"
        + (compact_context if compact_context.strip() else "No graph/document context available.")
        + "\n\n"
        + GRAPHRAG_OUTPUT_FORMAT.strip()
    )
    return prompt
