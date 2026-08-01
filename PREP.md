# Prep — JotPsych Stage 2

Not part of the deliverable. Delete this file before you share the repo.

---

## Tonight (90 minutes, then stop)

- [ ] `pip install -r requirements.txt`
- [ ] `cp .env.example .env`, fill it in
- [ ] **`python tools/check_smtp.py`** → run until it says SENT, then check the
      inbox with your own eyes. Gmail app passwords are the #1 day-of time sink.
- [ ] **`python tools/check_llm.py`** → confirms key works *and* has credit
- [ ] `python run.py` → should block 3, suppress 2, reject 2 at intake
- [ ] `python run.py --send` → confirm 3 emails actually land
- [ ] Push to a **public** repo. Open the link in a private window. No sign-in
      wall, no permission request. Access failures are called "a serious mark
      against you."
- [ ] Confirm the email address you applied with
- [ ] `./reset.sh` so tomorrow's evidence starts clean

Then close the laptop. Do not pre-write content — you don't know the brief.

---

## The clock

| Time | Do | Done when |
|---|---|---|
| 0:00–0:20 | Read brief. Pick the answer. Write one paragraph: what goes in, what comes out. | You have stopped deciding. |
| 0:20–1:20 | Rewrite `config.py` for the actual brief. Get the loop green. | One real email is in your inbox. |
| 1:20–1:50 | Refusal rules for this brief. Seed bad rows into the CSV. | `logs/rejects.log` is non-empty. |
| 1:50–2:15 | Confirm learning loop works on the LLM path. | Run 2 shows fewer blocks than run 1. |
| 2:15–2:35 | Install cron, let it fire, commit `logs/cron.log`. Rewrite README bracket parts. | `crontab -l` shows it. |
| 2:35–2:55 | **Three runs.** Commit `out/`, `quarantine/`, logs, `state.json`. | Evidence is in the repo. |
| 2:55–3:00 | Push. Test link cold. Paste stamp line into the email. | Sent. |

**Hard rule: if the loop isn't green at 1:20, stop improving and start
connecting.** A closed ugly loop beats an open beautiful one — the rubric says
so explicitly, twice.

---

## Where the rubric actually pays

Most people build the generator and run out of time. The generator is one of
five rows. Cheap points, in order of value per minute:

1. `REVIEW_QUEUE.md` — moves *Human time* to the top box. Already built.
2. Non-empty `logs/rejects.log` — *Quality control* asks you to **show what it
   caught**. Requires seeding bad rows. Already built.
3. Rejection rate falling across runs — *Learning*. Requires running it 3×.
   Protect that time.
4. Refusal rules as opinion — *The read* top box is literally "built into what
   the machine refuses to send."

---

## Traps, verbatim from the brief

- **Don't build a tracker.** "A machine that tracks cohorts, logs which
  clinician got which message, or flags who has gone dormant records the work
  instead of doing it."
- **Screen output is not an action.** It must leave the process.
- **A hardcoded list is not intake.** It must read a file.
- **One layer built beautifully = scored as a prototype.**
- **Spend a tenth of your time choosing.** That's 18 minutes.

---

## If something breaks

- **LLM down / out of credit** → the fallback template keeps the loop closed.
  Say "LLM path degraded, loop intact" in the README. Do not let it stop you.
- **SMTP fails at 2:40** → `FileSender` still runs. The loop still closes on a
  written artifact. Note it honestly and move on.
- **Behind at 2:00** → cut the learning loop first, then cron (replace with a
  one-line `while true; do ... sleep; done` script, which the brief explicitly
  accepts as a trigger). Never cut the QC gate — it carries two rubric rows.

---

## The read, in one line each

- Prescribers (MD/DO/PMHNP): volume, 15-minute slots, CPT/ICD-10 accuracy.
- Therapists (PhD/PsyD/LCSW/LMFT/LPC): narrative notes, evening paperwork,
  more privacy-protective, more AI-skeptical.
- The thing that loses them both: implying the software does the clinical
  thinking.
