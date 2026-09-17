---
name: ntu-quiz-handbook
description: >-
  Builds an illustrated NTULearn quiz prep handbook (Word + PDF, 配图版) from
  upcoming exams, lecture slides, and recordings. Use when the user asks for a
  quiz 备考手册, 配图版, exam prep pack, quiz handbook, or to prepare a named quiz
  (e.g. MA6815 Quiz 1) from NTULearn.
---

# NTULearn quiz handbook (配图版)

Private tutor for **one** upcoming quiz. Ground every point in **this student's** NTULearn slides + lecture recordings. Final files: one `.docx` and one `.pdf`.

Do not invent lecture pages. Do not echo `BbRouter`. Do not commit cookies or `courses/`.

## Checklist

```
- [ ] 1. Upcoming exams
- [ ] 2. User picks the exam (skip if already named)
- [ ] 3. Scope + download slides
- [ ] 4. Recordings / captions
- [ ] 5. Knowledge outline with 出处
- [ ] 6. Slide JPEGs
- [ ] 7. outline.json → Word
- [ ] 8. PDF
```

Scripts live in this skill's `scripts/` folder. `{SKILL}` below means that directory.

## 1. Upcoming exams

If MCP `ntl_*` tools work, use them. Otherwise:

```bash
python {SKILL}/scripts/list_exams.py --until-days 120 -o /tmp/exams.json
```

Cookie missing on Windows: user logs into https://ntulearn.ntu.edu.sg in **Firefox**, or pastes `BbRouter` into `ntl-save-cookie`. Then retry. Never print the cookie.

Pull **all three**:

| Source | Tool / field | Why |
|---|---|---|
| Calendar | `ntl_get_upcoming` with `until` ~120 days | Quizzes often sit outside the default 14 days |
| Announcements | `ntl_get_announcements` | Venue, closed-book, CA weight |
| Gradebook | `ntl_get_gradebook` | `Quiz 1` / CA1 column even when calendar says "No Examination" |

**Calendar "No Examination" does not mean no quiz.** Keep announcement- and gradebook-named quizzes.

Present a numbered list:

`n. COURSE  TITLE  —  datetime  —  venue/notes`

## 2. Which exam?

If the user already named the paper (example: "6815 的 quiz1"), **do not ask**. Map it to the list and continue.

Otherwise ask once (AskQuestion or a short numbered prompt). Generate **one** handbook per request.

Work folder:

`{NTULEARN_DOWNLOAD_DIR}/{COURSE}/quiz{N}/`

Example: `F:/ntulearn/courses/MA6815/quiz1/`

## 3. Scope and slides

Read the course tree (`ntl_get_course_contents`, `ntl_search_course_content`). Prefer:

- teaching plan / course outline / assessment
- lecture PDFs for weeks **up to the quiz**
- folders the lecturer tied to this CA

Skip unless the quiz is explicitly a software test: AnyLogic, tool GUIs, lab click-paths.

Files **> 1 MB**: `ntl_download_file`, never `ntl_read_file_content`.

Index each downloaded deck:

```bash
python {SKILL}/scripts/index_pdf.py LECTURE.pdf -o ppt_index/CODE.txt
```

## 4. Recordings

See [recordings.md](recordings.md). Captions first. Missing captions → status file, continue.

## 5. Write knowledge as a tutor

Bilingual where it helps (term **EN / 中文**). Every knowledge point needs `src`.

Priority:

1. Lecturer said it will be in the quiz → `callout`
2. Definitions, formulas, decision rules that appear on slides **and** in class
3. Contrast pairs (e.g. terminating vs steady-state; EEDI vs EEXI)
4. Worked numerical templates the quiz can clone

Do **not** dump a whole textbook. Do **not** copy other students' paid notes.

`src` examples:

- `W3 课件 p12；课堂 Week 3 回放`
- `公告 2026-09-10；gradebook CA1`
- `课堂 Week 2（课件无原句）` — then **no** screenshot

## 6. Screenshots

For each point that has a real slide, pick the **page that states it**. One idea → one page. Cap ~40–55 images.

```bash
python {SKILL}/scripts/render_slides.py --pdf LECTURE.pdf --code W1 --pages 3,6,10-12 --out slide_snaps
```

Repeat per deck. `meta.json` is merged in place.

## 7. Word

Write `outline.json` in the work folder. Schema: [outline.schema.json](outline.schema.json).

Block types: `h2` `h3` `p` `src` `bullets` `formula` `table` `callout` `note` `slide`.

Cover `meta` rows: 时间, 地点/形式, 成绩占比, 范围, 明确不考, 开闭卷, 编制依据.

`howto` should tell the student how to use 出处 + 截图.

```bash
node {SKILL}/scripts/build_handbook.js outline.json
```

Output name: `{COURSE}_{Exam}_备考手册_配图版.docx` (set `out` in JSON).

If Word has the old file open, write a `_new.docx` name, do not fight `EBUSY`.

## 8. PDF

```bash
python {SKILL}/scripts/export_pdf.py HANDBOOK.docx
```

Windows uses Word COM; otherwise LibreOffice. Return **both** paths to the user.

## Stance

- Tutor, not a slide reciter.
- √ and formulas: put in `formula` (Cambria Math). Never type `Vn` for √n.
- Tables: `cantSplit` is already on slide rows; keep tables narrow (`widths` sum to 10206 DXA).
- Software labs stay out unless the exam is the software.
