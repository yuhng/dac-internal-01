# Scoring module

Compares a CV with a job description and returns a match score with the evidence behind it.

Code: `src/mycareerai/module/scoring/`, `src/mycareerai/api/scoring.py`  
Tests: `tests/module/scoring/`

The score comes from rules, so the same text gives the same result. Scores can shift by a small amount over time for a CV with a current role, because its experience runs to today.

## How it works

```text
job.py        Split the job description into must-have and preferred requirements
 │
match.py      Grade each requirement against the CV and keep the supporting line
 │
score.py      Turn the grades into a fit score, and rate the CV separately
 │
engine.py     Add confidence and recommendations, and build the response
```

`POST /api/scoring/analyze` takes `title`, `company`, `jd` and `cv` as text. A job description with no recognised skills returns 422 rather than a made-up score.

### Requirements

| Rule | Result |
| --- | --- |
| Under a required heading, or the job description has no headings | Must-have |
| Under a preferred or responsibilities heading, or before the first heading | Preferred |
| Wording such as `is a plus` | Preferred |
| Soft skill | Always preferred, as few CVs state these outright |
| `Tableau or Power BI` | One requirement that either skill satisfies |
| No known skill, under a required or preferred heading | Kept as free text, and needs a model to assess |

### Evidence

| Tier | Credit | Meaning |
| --- | --- | --- |
| `demonstrated` | 1.0 | In a work or project line |
| `implied` | 0.8 | A model found a similar work or project line |
| `listed` | 0.6 | Elsewhere in the CV, usually the Skills section |
| `related` | 0.4 | A similar skill, from `related` in `hard_skills.yaml` |
| `partial` | Varies | Some of the required years, or a lower qualification (0.5) |
| `missing` | 0 | Not found |
| `unassessed` | None | Left out of the score |

### Score

Must-have skills count for 65%, preferred skills 15%, experience 15% and education 5%. Categories with no requirements are left out and the rest are scaled up.

A must-have with no credit limits the score to 79. Must-have skill coverage under 50% limits it to 59.

Impact and structure are returned in `quality` and do not affect the match score.

All weights, credits and limits are starting values. They have not been validated, and `docs/ApplyAssist-Architecture-Reference.md` still lists evaluation data as an open decision.

## Adding a sentence model

Semantic matching is built but off. To turn it on:

1. Implement `Encoder` from `encoder.py`.
2. Set `IMPLIED_SIMILARITY` and `RELATED_SIMILARITY` in `match.py` against labelled pairs. The current values are placeholders.
3. Pass the encoder to `analyze` in `api/scoring.py`.

A semantic match can't exceed `related` if the CV line names a different tool from the requirement.

## Limitations

- **Coverage:** only skills in the term lists are recognised, so most jobs outside data and software are rejected or poorly covered.
- **Certifications:** these are not scored.
- **Years:** a requirement such as `3 years of React` is checked against total experience, not time using React.
- **Education:** the field of study is not checked.
- **OCR:** scoring only receives text, so it can't lower confidence for OCR errors.
