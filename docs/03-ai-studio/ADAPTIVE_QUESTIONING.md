# Adaptive Consultation & Questioning Engine — ENG-02

## Objective

In a live physical consultation, obtain the **minimum sufficient decision-critical information** to recommend suitable options, while preserving professional authority and avoiding static long-form questionnaires. User inputs may be spoken (only when opt-in voice handling exists), typed by specialist, or chosen as on-screen answers.

## Decision loop

```text
Recognize service/intent → load Service Question Profile → assemble existing evidence
  → enumerate decision-critical unknowns → rank candidate questions by expected impact
  → ask one concise question → parse answer with source=USER_REPORTED
  → detect constraint conflict → update structured profile → reconsider ranking
  → stop when sufficient for current stage or show bounded recommendation with unknowns
```

## Question rank dimensions

1. Safety and feasibility necessity.
2. Whether answer can eliminate/reorder candidate look options.
3. Whether information is truly missing rather than present in prior statements/authorized record.
4. User burden and consultation time.
5. Value of question relative to next step (initial style vs technical planning).

Do **not** invent probability/utility percentages. A qualitative policy is acceptable until empirically evaluated. Early suggestions can be shown before all optional questions are answered. Never proceed past required professional/safety checks based on question caps.

## Example men's haircut profile

| Variable | Example question | Why |
|---|---|---|
| daily_style | «معمولاً چه مدل‌هایی را بیشتر استفاده می‌کنی؟» | Target direction |
| daily_styling_time | «روزانه چقدر برای رسیدگی وقت داری؟» | Maintenance fit |
| heat_tool_tolerance | «ترجیح می‌دهی بدون سشوار هم مرتب باشد؟» | Technique burden |
| product_tolerance | «هر روز از واکس/پماد استفاده می‌کنی؟» | Routine feasibility |
| side_length | «کناره‌ها خیلی کوتاه بشوند یا ملایم؟» | Exclusion constraint |
| cut_frequency | «هر چند هفته برای اصلاح مراجعه می‌کنی؟» | Grow-out expectations |
| professional_observations | Specialist records growth patterns, texture, visibility | Visual/real-world truth |

Question sets vary across Hair Color, Makeup, Nails, Beard, Keratin, Extensions, Bridal and Skin Advisory. Their required evidence differs and all are separately versioned in a `QuestionProfileRegistry`.

## JSON contract (illustrative)

```json
{
  "service_id": "MEN_HAIRCUT",
  "profile_version": "1.0.0",
  "question_id": "Q-STYLING-TIME",
  "decision_variable": "daily_styling_minutes",
  "question_text_fa": "روزانه چقدر برای حالت‌دادن به موهات وقت داری؟",
  "priority_class": "DECISION_CRITICAL",
  "answer": {"value": 5, "source": "USER_REPORTED"},
  "can_continue_with_unknown": true
}
```

## Stop conditions

- Continue to recommendation when service and all essential decision variables for the current recommendation stage are known or explicitly marked unknown with bounded effects.
- Stop asking optional questions when marginal benefit is low or user requests a preliminary result.
- Do not skip **critical technical safety evidence** for executing a procedure; defer approval instead.
- Resume after interruptions without repeating already-answered questions; replay from session checkpoints.

## Evaluation

Tests: no duplicate questions, correct service-specific ordering, normalized answers, follow-up to contradictory preferences, no bias or appearance judgment, reasonable question count in observed specialist pilot, uncertainty honesty, full branch coverage, later professional finding overrides inference.
