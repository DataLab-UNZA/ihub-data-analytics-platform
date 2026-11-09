# Prompts for free Claude

Copy a prompt into a Claude chat **after uploading the context pack** (see Step 5 of [`STUDENT_GUIDE.md`](STUDENT_GUIDE.md)). Each prompt asks Claude for short answers and numbered options, to save messages. Where a prompt says "pasted below", paste that text on the lines after the prompt in the same message.

Start a new chat for each issue.

---

## Prompt 1: start (always first)

```
I am a student on the iHub Data Analytics Platform team. I have uploaded the context pack. Read all of it, including "How to use this pack", and follow those instructions for the rest of this chat. Reply in no more than six lines: what the project is, where it is on the roadmap, and the four steps of our workflow (issue, branch, pull request, deploy). Then ask me which issue I am working on.
```

## Prompt 2: plan an issue (no code yet)

```
I am working on the GitHub issue pasted below. Do not write code yet. Reply with: (1) the files you will create or change, with their paths; (2) the test that proves it works, if code changes; (3) any decision we must make, as 2 to 4 numbered options with your recommendation; (4) the branch name to use. Wait for my answer.

```

## Prompt 3: implement

```
Go ahead with the plan we agreed. Give me each file in full, with its path above it. Then list, in order, the exact commands I must run to check it (ruff format, ruff check, pytest, and anything else needed). Do not explain things I did not ask about.
```

## Prompt 4: fix a failing check

```
I ran the checks and got the output pasted below. Tell me in one sentence what is wrong, then give me the corrected file(s) in full, with their paths. If the error shows that you need a file you have not seen, ask me for it instead of guessing.

```

## Prompt 5: write the pull request

```
Write my pull request using our template: a title (imperative, British English, under 70 characters), "What this PR does" (two sentences at most), "Why" with "Closes #" and the issue number from our chat, and "How it was checked" listing only what I actually ran. Also give me a one-line commit message. Do not mention Claude anywhere.
```

## Prompt 6: review a teammate's pull request

```
Review the pull request diff pasted below against our conventions in the context pack (layers, naming, type hints, docstrings, tests without live APIs, no SQL in pages, no secrets, British English). List at most five points, most important first, each with the file and line and a suggested fix. End with one line: "Approve" or "Request changes", and why.

```

## Prompt 7: explain code

```
Explain the code pasted below to me as a final-year computing student: what it does, how it fits our pipeline (connectors, raw, staging, intermediate, marts, app), and one thing I could easily break when changing it. Keep it under 200 words.

```

## Prompt 8: running out of messages

```
My usage is running out. Write the email I should send to Lighton Phiri (lighton.phiri@unza.ac.zm) with the subject "iHub: please run on Max": the issue, the branch name I gave you, what is done, and the exact next prompt to run, ready to paste. Keep it under 150 words.
```
