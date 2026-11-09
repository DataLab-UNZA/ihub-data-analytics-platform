# Student guide: working on the iHub Data Analytics Platform

This guide is for the four student collaborators: Bruce Mainza, Mubanga Chibesa, Chilandu Phiri and Joshua Mvula. Work through **Part 1** step by step on your first day. Parts 2 to 6 explain how the project works; come back to them when you need them.

You use **Claude's free plan in the browser**. That Claude cannot see the repository or run commands, so you give it the project through the **context pack**, you copy its code into files on your own computer, and you run the commands yourself.

---

## Part 1: Day 1 checklist (do these in order)

Tick each step only when its **Done when** is true.

### Step 1. Accept your GitHub invitation

Open https://github.com/orgs/DataLab-UNZA/invitation while signed in to your own GitHub account and accept it. This makes you a member of the `ihub-deployers` team: you can push branches, open and merge pull requests, and approve deployments.

**Done when:** https://github.com/orgs/DataLab-UNZA/teams/ihub-deployers/members lists you.

### Step 2. Install the tools

You need **Git** and **uv** (uv installs Python 3.12 for you).

- Git: https://git-scm.com/downloads
- uv on Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- uv on macOS or Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

Close and reopen the terminal after installing.

**Done when:** `git --version` and `uv --version` both print a version.

### Step 3. Clone the project and run it

```bash
git clone https://github.com/DataLab-UNZA/ihub-data-analytics-platform.git
cd ihub-data-analytics-platform
uv sync --all-groups               # creates .venv with Python 3.12 and everything we use
cp .env.example .env               # Windows PowerShell: copy .env.example .env
uv run pre-commit install          # checks your code before every commit
uv run pytest                      # all tests should pass
uv run python -m ihub.ingest       # creates data/ihub.duckdb
uv run streamlit run src/ihub/app/Home.py
```

**Done when:** `pytest` reports only passes, and http://localhost:8501 shows the iHub home page. Stop the app with Ctrl+C.

### Step 4. Tell Git who you are (once per computer)

Your commits are credited to you only if your Git name and email match your row of the Team tab. Run the two lines for **your** row, inside the project folder:

| You | Commands |
|---|---|
| Bruce Mainza | `git config user.name "Bruce Mainza"`<br>`git config user.email "223556219+brucemainza@users.noreply.github.com"` |
| Mubanga Chibesa | `git config user.name "Mubanga Chibesa"`<br>`git config user.email "148569509+mubanga-chibesa@users.noreply.github.com"` |
| Chilandu Phiri | `git config user.name "Chilandu Phiri"`<br>`git config user.email "206355417+Chilandu@users.noreply.github.com"` |
| Joshua Mvula | `git config user.name "Joshua Mvula"`<br>`git config user.email "182490947+JMvula@users.noreply.github.com"` |

These are GitHub no-reply addresses: your real email never appears in the public history.

**Done when:** `git config user.email` prints your no-reply address.

### Step 5. Download the context pack and start a Claude chat

1. Download **https://github.com/DataLab-UNZA/ihub-data-analytics-platform/releases/download/context-pack/ihub-context-pack.zip**. Download it again every time you start a new chat: it is rebuilt after every merge, so it always describes the project as it is now.
2. Open https://claude.ai, start a **new chat** and upload the zip. If Claude does not accept the zip, upload **https://github.com/DataLab-UNZA/ihub-data-analytics-platform/releases/download/context-pack/context-pack.md** instead.
3. Paste **Prompt 1** from [`STUDENT_PROMPTS.md`](STUDENT_PROMPTS.md) (it is also inside the zip).

**Done when:** Claude replies with a short summary of the project and asks which issue you are working on.

### Step 6. Do your practice task

Each student takes one practice issue: https://github.com/DataLab-UNZA/ihub-data-analytics-platform/issues?q=is%3Aopen+label%3Apractice. Assign it to yourself (**Assignees → assign yourself**) so nobody else takes it.

Follow the workflow in Part 2 from start to finish: branch, work with Claude (Prompts 2 and 3), run the checks, commit, push, open a pull request, ask a teammate to review, merge.

**Done when:** your pull request is merged and the issue is closed.

### Step 7. Approve a deployment

Practise the approval even if your change did not deploy anything:

1. GitHub → **Actions** → **Deploy** → **Run workflow** → leave **ref** empty → **Run workflow**. This redeploys what is already live, so it is safe.
2. Open the new run. It shows **Waiting for review**.
3. **Review deployments** → tick **production** → **Approve and deploy**.
4. Wait for the run to turn green, then open https://ihub-app-197899767407.africa-south1.run.app.

**Done when:** the run is green and the app opens. If two of you are practising together, let one start the run and the other approve it.

When all seven steps are done, tell Lighton.

---

## Part 2: The everyday workflow

```
issue ──► branch ──► code with Claude ──► checks pass ──► commit + push ──► pull request
      ──► CI green + a teammate reviews ──► merge ──► (app changed?) approve the deploy
```

1. **Pick an issue** from https://github.com/DataLab-UNZA/ihub-data-analytics-platform/issues and assign it to yourself. Every piece of work starts from an issue.
2. **Update and branch** from the latest `main`:
   ```bash
   git switch main
   git pull
   git switch -c feature/openalex-connector     # or fix/…, docs/…
   ```
   Branch names: `feature/…` for new work, `fix/…` for bugs, `docs/…` for documentation only. Lower case, words joined by hyphens.
3. **Work with Claude** (Part 4). Save each file it gives you at the path it names.
4. **Run the checks** before every commit:
   ```bash
   uv run ruff format .           # fixes formatting
   uv run ruff check .            # must say "All checks passed!"
   uv run pytest                  # must pass
   ```
   If something fails, paste the error into your Claude chat (Prompt 4).
5. **Commit and push**:
   ```bash
   git add -A
   git commit -m "Add the OpenAlex connector"     # short, imperative, British English
   git push -u origin feature/openalex-connector
   ```
6. **Open a pull request**: GitHub shows a **Compare & pull request** button after you push. Fill in the template (Part 3). Write `Closes #12` (your issue number) so the issue closes when it merges.
7. **Review**: ask one teammate to review it (**Reviewers** on the right). Every pull request requires at least one approving teammate before it is merged. The `main` branch should enforce one approving review and the `lint-and-test` check; if GitHub still permits a merge without approval, stop and ask an organisation owner to correct the branch-protection settings. You review teammates' pull requests the same way (Prompt 6 helps).
8. **CI**: the `lint-and-test` check must be green. A red check blocks the merge; fix it on the same branch and push again.
9. **Merge** with **Merge pull request**, then delete the branch when GitHub offers.
10. **Deploy** (only if the change affects the app): see Part 5.

Rules that never change: never commit secrets (`.env` stays on your computer), data files or `.duckdb` files; never mention Claude in commits or pull requests; `main` only changes through pull requests.

---

## Part 3: Writing a good pull request

A reviewer should understand your pull request in two minutes.

- **Title:** what it does, imperative: "Add the DSpace OAI-PMH connector", not "dspace stuff".
- **What this PR does:** one or two sentences.
- **Why:** `Closes #12`.
- **How it was checked:** tick the boxes you actually did (ruff, pytest, test added, no secrets, docs updated).
- **Screenshots** for any change to a page.
- **Small:** one issue per pull request. If it grows beyond about 300 changed lines, split it.

| Weak | Good |
|---|---|
| "Update files" | "Add stg_dspace__items staging model with DOI normalisation" |
| No issue linked | "Closes #9" |
| "Tests: yes" | "Added tests/test_dspace.py using a recorded OAI-PMH response; `uv run pytest` passes (9 tests)" |

---

## Part 4: Working with free Claude

- **One task per chat.** Start a new chat for each issue, with a fresh copy of the context pack.
- **Paste the issue text** so Claude knows the acceptance criteria.
- **Paste existing files** when Claude needs them: the pack lists files and function signatures, not full code.
- **Choose by number.** Claude will give numbered options; reply with the number. It saves messages.
- **Ask for whole files** with their paths, not fragments.
- **Check before you trust.** Run the checks, read the code, and ask Claude to explain anything you do not understand (Prompt 7). You are responsible for what you commit.
- **Running out of messages?** Push your branch and email Lighton Phiri (lighton.phiri@unza.ac.zm) with the subject **"iHub: please run on Max"**, the branch name and the next prompt.

Ready-made prompts are in [`STUDENT_PROMPTS.md`](STUDENT_PROMPTS.md).

---

## Part 5: How deployment works for you

- The app is live at https://ihub-app-197899767407.africa-south1.run.app (Google Cloud Run). You never need Google Cloud access.
- **A merge that changes the app** (code, Dockerfile, settings) starts the **Deploy** workflow, which pauses with **Waiting for review**. Any member of `ihub-deployers` (Lighton and the four of you) approves it: **Actions → the waiting Deploy run → Review deployments → production → Approve and deploy**. You may approve your own.
- **A merge that only changes documentation or tests** does not start a deploy, because nothing in the app changed.
- **Before approving, check:** CI on the merge is green, the pull request was reviewed, and you know what is being deployed. After approving, open the app and check that it works.
- **If a deploy breaks the app,** tell the team at once. Rolling back is in [`DEPLOYMENT.md`](DEPLOYMENT.md#how-to-roll-back): run Deploy by hand with the previous good commit in **ref**.
- The data is refreshed every Monday at 04:00 Lusaka time by the **Pipeline** workflow. It needs no approval.

---

## Part 6: How credit works

Your contributions are counted from the Git history, so credit depends on two things: your Git name and email (Step 4), and the commit trailers.

**When you work on your own,** you are the commit **author**. Your commits appear on your GitHub profile and in the repository's contributor list.

**In mob sessions** (the team works together on Lighton's account, one Navigator at a time):

- Every prompt is logged in the Google Sheet "misc-ihub26-data_analytics_platform - Mob Programming Prompt Log", tab **Prompt Log**: session, date, Navigator, Reviewer, the exact prompt, the outcome and the commit hash.
- The **Team** tab holds each person's full name, GitHub username and commit email. The Prompt Log looks names up there and builds the trailer lines automatically (columns J and K).
- Commits are authored by Lighton and end with trailers that credit the Navigator and the Reviewer, for example:
  ```
  Co-authored-by: Bruce Mainza <223556219+brucemainza@users.noreply.github.com>
  Reviewed-by: Chilandu Phiri <206355417+Chilandu@users.noreply.github.com>
  ```
  GitHub shows co-authored commits on the co-author's profile too.
- If you pair with a teammate outside a mob session, add their `Co-authored-by` line (from the table in Step 4) at the end of your commit message, after a blank line.

**Checking credit** (Git 2.38 or later):

```bash
git shortlog -sn main                                     # commits by author
git shortlog -sn --group=trailer:co-authored-by main      # commits by co-author
git shortlog -sn --group=trailer:reviewed-by main         # reviews recorded in commits
git log --oneline --grep="Co-authored-by: Bruce Mainza"   # one person's co-authored commits
```

The people on the project are listed in [`CONTRIBUTORS.md`](../CONTRIBUTORS.md).

---

## Where things are

| You want to… | Look in |
|---|---|
| understand the project and its rules | [`CLAUDE.md`](../CLAUDE.md), [`README.md`](../README.md) |
| see what comes next | [`ROADMAP.md`](ROADMAP.md) and the issues |
| add a data source | `src/ihub/connectors/` (subclass `Connector` in `base.py`) and `config/sources.yml` |
| clean or combine data | `transform/models/` (dbt: `staging/`, `intermediate/`, `marts/research/`) |
| add a query for a page | `src/ihub/mart/` (pages never contain SQL) |
| add or change a page | `src/ihub/app/` |
| add a test | `tests/` (tests never call live APIs; use recorded responses) |
| understand a design decision | [`decisions/`](decisions/) |
| deploy, roll back or check costs | [`DEPLOYMENT.md`](DEPLOYMENT.md) |
