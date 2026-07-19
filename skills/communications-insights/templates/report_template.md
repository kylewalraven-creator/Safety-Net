<!-- Communications Insights — Markdown report template.
     Tokens are {{like_this}}. Blocks between <!-- REPEAT x --> and <!-- /REPEAT x --> repeat
     per item. The generator fills tokens, expands REPEAT blocks, and drops empty optional
     sections. Keep the "DRAFT — human review required" labels verbatim. -->

# Communications Insights — {{display_name}}

**Generated:** {{generated_at}}  ·  **Run type:** {{run_type}}  ·  **Backfill complete:** {{backfill_complete}}
**Data scope:** your own Slack messages + your own Gmail mailbox (nobody else's)
**History covered:** {{history_start}} → {{history_end}}  ·  **This run processed:** {{window_start}} → {{window_end}}
**Volume this run:** {{slack_msg_count}} Slack messages · {{gmail_thread_count}} email threads  (cumulative: {{cumulative_slack}} / {{cumulative_gmail}})
**Personalization:** role — {{role}}; goals — {{goals_inline}}

> **Analysis + drafts only.** Nothing here was sent and no action was taken on your accounts.
> Items marked **DRAFT — human review required** are yours to edit and send (or not).

---

## Executive summary

{{exec_summary}}

**At a glance**

| Dimension | Read | Trend vs. last run |
|---|---|---|
<!-- REPEAT glance -->
| {{dimension}} | {{read}} | {{trend_arrow}} |
<!-- /REPEAT glance -->

---

## 1. What you're doing well

<!-- REPEAT strength -->
### {{strength_title}}
- **Observation:** {{observation}}
- **Why it matters for your goals:** {{why}}
- **Confidence:** {{confidence}}
- **Evidence:** {{evidence_refs}}   <!-- ≤2 refs: permalink/subject + timestamp -->
<!-- /REPEAT strength -->

## 2. Areas to improve

<!-- REPEAT improvement -->
### {{improvement_title}}
- **Observation:** {{observation}}
- **Suggested change:** {{suggested_change}}
- **Impact / Effort:** {{impact}} / {{effort}}
- **Confidence:** {{confidence}}
- **Evidence:** {{evidence_refs}}
<!-- /REPEAT improvement -->

## 3. Opportunities to automate

<!-- REPEAT automation -->
### {{automation_title}} — _{{type}}_
- **Pattern noticed:** {{pattern}}
- **Proposed automation (draft):** {{proposal}}
- **Impact / Effort:** {{impact}} / {{effort}}
- **Human review required:** {{human_review_required}}
- **Evidence:** {{evidence_refs}}
<!-- /REPEAT automation -->

## 4. Suggested next actions

<!-- REPEAT action -->
- **[{{priority}}]** {{action}} — _{{rationale}}_ {{draft_badge}}
<!-- /REPEAT action -->

---

## Draft recommendations (ready to edit — never sent)

<!-- REPEAT draft -->
### {{draft_title}} · **DRAFT — human review required**

> {{draft_body}}

_Addresses:_ {{linked_opportunity}}  ·  _You would send this via:_ {{destination}} (the skill will not)
<!-- /REPEAT draft -->

---

## Trends over time

{{trends_prose}}

| Metric | {{period_1}} | {{period_2}} | {{period_3}} | {{period_now}} |
|---|---|---|---|---|
<!-- REPEAT trend_row -->
| {{metric_name}} | {{v1}} | {{v2}} | {{v3}} | {{v_now}} |
<!-- /REPEAT trend_row -->

<!-- The HTML artifact renders these rows as CSS bars. -->

---

## Insufficient evidence / not assessed

{{insufficient_list}}

## Methodology & data scope

- **Sources:** your own Slack messages (`from:you`) and your Gmail mailbox (your sent mail + threads you're in).
- **Granularity:** hybrid — aggregate rollups from your saved insight store + targeted live drill-down for the cited examples above.
- **Grounding:** every observation is tied to a real message reference; unverifiable claims were dropped.
- **Personalization used:** {{profile_echo}}

## Privacy note

- This report can contain more detail than your saved store. Treat it as **personal** and review before sharing.
- Your saved store keeps only redacted, derived findings + a few reference links — **never raw message text**.
- **To purge everything:** delete `{{store_path}}` and the `reports/` folder in your private space.
