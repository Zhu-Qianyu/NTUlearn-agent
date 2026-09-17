# Recordings (Kaltura)

Use this only after lecture PDFs are in the work folder. Prefer **captions / transcripts**, never a full video download.

## Find the gallery

1. `ntl_search_course_content` for `Media Gallery`, `Kaltura`, `Course Gallery`, `Lecture Recording`.
2. Open the LTI content item. Placement id is usually in the Ultra page HTML (`bltiPlacementId` / `_1327_1` class of ids).
3. Launch sequence (cookie already on the machine, do not print it):
   - GET the content item
   - POST the LTI 1.3 form to `ntulearnv1.ntu.edu.sg`
   - land on `.../hosted/index/course-gallery`

## Captions

Kaltura gallery is JS-rendered. If HTTP HTML has no `entryId` list:

1. Use the Cursor browser **after the user is already logged into NTULearn**.
2. Open the course gallery, collect entry titles + weeks.
3. For each lecture before the quiz date, fetch `SUBTITLES` / caption assets.
4. Save UTF-8 transcripts as `transcripts/weekN.txt`.
5. If a week has **no SUBTITLES**, write `transcripts/weekN_STATUS.txt` (`no captions`) and move on. Do not stall the handbook.

## How transcripts are used

- Quote the lecturer when they mark a quiz item ("it will be in the quiz").
- Those items become `callout` blocks in `outline.json`.
- Software walk-throughs (AnyLogic, Excel clicks, MATLAB GUI) stay out unless the announcement says the quiz is a software test.
