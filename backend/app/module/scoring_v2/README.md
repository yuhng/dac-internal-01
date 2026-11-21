# Scoring v2

Scores one structured CV against one job description (JD) and returns a 0–100 overall score.

The score has two independent parts:

| Part | What it measures | How | Weight |
|------|------------------|-----|--------|
| **Skill score** | Does the CV explicitly mention the skills the JD asks for? | Deterministic string matching | 40% |
| **Relevance score** | Does the CV's work/project experience fit the role? | LLM judge (TypeSafe JEV) on a 3-level rubric | 60% |

They are kept apart on purpose: the relevance judge never sees the `technical_skills` section and is told not to reward skill-name matches, so the same keyword is never counted twice.

## Pipeline

```
POST /scoring/analyze                       backend/app/api/scoring.py
  │  { jd: str, document: ResumeDocument }
  │
  ├─ extract_jd(jd_text, job_id)            extract_jd.py        (OpenAI)
  │     → JobDescription { skills[name, importance, source_quote], review_status }
  │
  └─ score_application(document, jd)        overall_score.py
        │
        ├─ prepare_evidence(document)       prepare_evidence.py  (no LLM)
        │     → bullets, skill_sources, skill_mentions
        │
        ├─ score_skills(evidence, jd)       score_skills.py      (no LLM)
        │     → coverage per importance group
        │
        ├─ score_relevance(document, jd)    score_relevance.py   (TypeSafe JEV)
        │     → jev_score_100
        │
        └─ calculate_overall_score(...)     overall_score.py
              → skill_score_100, relevance_score_100, overall_score_100, method, provisional
```

## Step 1 — Extract skills from the JD (`extract_jd.py`)

An OpenAI model reads the JD and returns each explicitly requested technical skill with:

- `name` — exactly as written in the JD (no expanding "LLMs" into "Large Language Models")
- `importance` — `required`, `preferred` or `unspecified`, only when the wording supports it
- `source_quote` — an exact excerpt of the JD that contains the skill

`build_jd()` turns this into a `JobDescription`, whose validator in [schema.py](../../schema/schema.py) checks that every `source_quote` really is in the JD text and contains the skill name, and that no skill appears twice. If validation fails, it raises `ValueError` (→ HTTP 422); there is no retry.

If the model returns warnings or no skills, the JD is marked `review_status = "needs_review"`.

## Step 2 — Collect CV evidence (`prepare_evidence.py`)

`prepare_evidence()` walks the CV sections and builds the text that skills are allowed to match against:

- **`work_experience` / `project_experience`**: each non-empty line of an entry becomes one bullet (`<entry_id>:bullet:001`, …).
- **`technical_skills`**: each line becomes a source (`<section_id>:line:001`, …). Lines starting with `Certification(s):` are skipped.

`clean_line()` strips bullet markers, numbering and invisible characters and collapses whitespace.

Skill names are normalised through the `SKILLS` alias table, e.g. `Postgres` → `PostgreSQL`, `sklearn` → `scikit-learn`. `skill_mentions()` matches them as whole words, case-insensitively (so `Java` won't match inside `JavaScript`, and `C` won't match `C#`).

## Step 3 — Skill score (`score_skills.py` + `overall_score.py`)

For each JD skill, `score_skills()` searches every evidence source for that skill (its JD name plus known aliases). A skill is **matched** if it appears at least once. Each result keeps the evidence IDs and text so the UI can show *where* it was found.

Coverage is then computed per importance group:

```python
percent = 100 * matched / requested      # None if the group is empty
```

`calculate_overall_score()` combines the groups with fixed weights, **ignoring empty groups and re-normalising** the rest:

```python
weights = {"required": 0.60, "preferred": 0.25, "unspecified": 0.15}

available = [(weights[g], coverage[g]["percent"]) for g in weights if coverage[g]["requested"] > 0]
skill_score = sum(w * p for w, p in available) / sum(w for w, _ in available)
```

So a JD that lists only required skills gets a skill score equal to its required coverage; it is not capped at 60.

## Step 4 — Relevance score (`score_relevance.py`)

`score_relevance()` sends every CV section **except `technical_skills`** (as JSON) plus the raw JD text to TypeSafe JEV, which scores it against this rubric:

| Level | Label |
|-------|-------|
| 0 | No Fit — little to no relevant experience |
| 1 | Potential Fit — partially relevant, notable gaps |
| 2 | Good Fit — strong alignment |

JEV returns a probability for each level. The score is the expected level:

```python
jev_score     = Σ level × probability        # 0.0 – 2.0
jev_score_100 = jev_score / 2 * 100          # 0 – 100
```

`validate_answer()` rejects the response unless the probabilities sum to 1 (±0.01), the score agrees with them (±0.02), everything is in range, and the rubric legend matches. `jev_confidence` is reported but not used in the score.

## Step 5 — Overall score (`overall_score.py`)

```python
if relevance_score is None:        overall = None                                   # method = None
elif skill_score is not None:      overall = 0.40 * skill_score + 0.60 * relevance_score
                                                                                    # method = "weighted_skills_and_relevance"
else:                              overall = relevance_score                        # method = "relevance_only"
```

| Situation | `overall_score_100` | `method` |
|-----------|---------------------|----------|
| Both scores available | 40% skills + 60% relevance | `weighted_skills_and_relevance` |
| JD has no extractable skills | relevance only | `relevance_only` |
| Relevance unavailable | `None` (a skills-only score is just keyword counting) | `None` |

All three scores are rounded to 2 decimals **at output only**; the overall uses the unrounded skill score.

Before combining, it checks both inputs refer to the same `job_id`, `document_id` and `document_version`.

### `provisional`

The result is flagged `provisional: true` when any of these hold:

- the CV's `review_status` is not `approved`
- the JD's `review_status` is not `approved` (JDs from the API are always `pending` or `needs_review`)
- the method is `relevance_only`

Treat a provisional score as indicative, not final.

## Worked example

**JD skills** (from step 1):

| Skill | Importance | In CV? |
|-------|-----------|--------|
| Python | required | ✅ |
| SQL | required | ✅ |
| Airflow | required | ✅ (as "Apache Airflow") |
| Kubernetes | required | ❌ |
| dbt | preferred | ✅ |
| Terraform | preferred | ❌ |

**Skill score**

```
required  = 3/4 = 75.00%
preferred = 1/2 = 50.00%
unspecified: none → excluded

skill = (0.60 × 75 + 0.25 × 50) / (0.60 + 0.25)
      = (45 + 12.5) / 0.85
      = 67.65
```

**Relevance score** — JEV returns probabilities `{0: 0.1, 1: 0.3, 2: 0.6}`:

```
jev_score     = 0×0.1 + 1×0.3 + 2×0.6 = 1.5
jev_score_100 = 1.5 / 2 × 100         = 75.00
```

**Overall**

```
overall = 0.40 × 67.647 + 0.60 × 75
        = 27.06 + 45.00
        = 72.06
```

```json
{
  "skill_score_100": 67.65,
  "relevance_score_100": 75.0,
  "overall_score_100": 72.06,
  "method": "weighted_skills_and_relevance",
  "provisional": true
}
```

## Known limits

- Skill matching only checks that a skill is **mentioned**: it does not assess proficiency, recency, or negation ("no Python experience" still matches).
- Skills missing from the `SKILLS` alias table only match their exact JD spelling.
- Each non-empty CV line is treated as one bullet, so poor OCR line grouping affects evidence IDs.
- "Python **or** R" style alternatives are scored as separate skills; the JD gets a warning for manual review.
- `jev_confidence` reflects how concentrated JEV's probabilities are, not measured accuracy.
