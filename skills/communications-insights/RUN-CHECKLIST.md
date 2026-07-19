# Run Checklist — Communications Insights

A self-serve skill that reviews **your own** Slack messages and **your own** Gmail, then gives you
a grounded report: what you're doing well, where to improve, what to automate, and suggested next
steps. It produces one Markdown file and one HTML file. **It never sends anything** — every
recommendation is a draft you review.

Runs entirely on **your** accounts. It cannot see anyone else's messages, and your saved findings
stay private to you.

---

## Before you start (one-time, ~2 min)

- [ ] You're signed in to Claude with the skill available.
- [ ] Connect the three connectors it uses (each authorizes **your** account only):
  - [ ] **Slack** — so it can read messages you wrote
  - [ ] **Gmail** — so it can read your mailbox (your sent mail + threads you're in)
  - [ ] **Google Drive** — so it can save your private insight store + reports
- [ ] No config files, API keys, or admin help needed. If a connector isn't authorized, the skill
      will tell you exactly which one to connect.

---

## Run it

- [ ] Start the skill (e.g., ask for a "communications insights" run, or invoke it by name).
- [ ] **Confirm the data-use notice** it shows (what it reads, what it saves, that nothing is sent).
- [ ] **Answer the short personalization prompt** (reused automatically next time):
  - [ ] Your **role**
  - [ ] Your top **2–4 goals** (the report is judged against these)
  - [ ] **Preferences** (tone, brevity, channels you care about)
  - [ ] **Context** (team, current priorities)
  - [ ] **Constraints** (channels to exclude, extra terms to redact, "don't save reference links", etc.)
- [ ] Let it run:
  - **First run = full backfill** of your whole history. This can take a while and may pause and
    **resume across sessions** — that's expected. It reports a "% complete."
  - **Later runs = incremental** (only what's new) and are fast; they also show trends vs. prior runs.

---

## Review the output

- [ ] Open the two deliverables (also saved to `Comms Insights (private)/reports/` in your Drive):
  - [ ] `comms-insights_<date>.md` (Markdown)
  - [ ] `comms-insights_<date>.html` (open in a browser; self-contained, prints cleanly)
- [ ] Read the four sections: **doing well · improve · automate · next actions**.
- [ ] Review anything badged **DRAFT — human review required**. Edit and send it yourself if you
      want it — the skill will not send or act on your behalf.
- [ ] Spot-check a couple of citations (each claim links to a real message). Tell the skill if any
      look wrong so it can drop them.
- [ ] (Optional) Give each section a 1–5 usefulness rating when prompted — it's stored to show
      whether the insights improve over time.

---

## Keep it useful over time

- [ ] Re-run whenever you want a refresh (e.g., weekly). It only processes what's new and updates
      the trend lines.
- [ ] Update your goals/constraints anytime you're prompted — the analysis follows them.

---

## Your data & privacy

- [ ] **Scope:** only your own Slack messages and your own Gmail. No one else's data is read, and
      your report/store are private to you.
- [ ] **What's saved:** only redacted, high-level findings + a few reference links — **never raw
      message text**. Saved in your private Drive folder, keyed to you.
- [ ] **Sharing:** the report may contain more detail than the saved store; review before sharing.
- [ ] **To erase everything:** delete the `Comms Insights (private)` folder in your Drive (the store
      and all reports). The next run simply starts a fresh backfill.

---

## If something goes wrong

- **"Connect a connector" message** → authorize the named connector, then re-run.
- **Backfill stopped partway** → just run it again; it resumes from where it left off.
- **A section says "insufficient evidence"** → there wasn't enough grounded data; it won't guess.
- **A citation looks wrong** → flag it; the skill drops unverifiable claims.
