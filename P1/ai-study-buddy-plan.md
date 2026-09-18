# AI Study Buddy — Personalized Learning Agent
## Project Plan

---

## Top-Level Overview

**Goal:** Build a modular, single-session Streamlit web application that lets students upload
their study material (PDF or TXT) and interact with IBM watsonx.ai (Granite models) across
fourteen learning features — from chatbot doubt-solving and adaptive quizzes to multiplayer
sessions, mind-maps, and a voice mode.

**Primary LLM:** `ibm/granite-3-8b-instruct` via the `ibm-watsonx-ai` Python SDK
(`ModelInference.chat()` and `ModelInference.generate_text()`).

**Retrieval strategy:** Keyword/TF-IDF chunk retrieval (no vector DB for v1). Documents are
split into `Chunk` objects tagged with page number and section heading. Every LLM prompt that
must be grounded injects the top-k matching chunks as context.

**State strategy:** All user state (uploaded docs, quiz history, XP, schedule) lives in
Streamlit `st.session_state` — no database, no login, single-browser-session lifetime.

**Build order:** Five incremental phases so each phase is independently releasable.

---

## Architecture Diagram (text representation)

```
UI Layer (Streamlit multi-page app)
    |
    +-- pages/
    |       01_Upload.py
    |       02_Explain.py
    |       03_Chatbot.py
    |       04_ReverseLearning.py
    |       05_StoryComic.py
    |       06_Quiz.py
    |       07_WeakSpots.py
    |       08_Schedule.py
    |       09_MindMap.py
    |       10_Multiplayer.py
    |       11_ExamPattern.py
    |       12_StudyTwin.py
    |       13_VoiceMode.py
    |
Core Modules (src/)
    |
    +-- document_ingestion.py   -- upload, parse, chunk, retrieve
    +-- watsonx_client.py       -- wraps ibm_watsonx_ai SDK
    +-- session_state.py        -- initialise / access session_state keys
    +-- models.py               -- dataclasses: Document, Chunk, UserProfile, etc.
    |
Feature Modules (src/features/)
    |
    +-- explanation.py
    +-- chatbot.py
    +-- reverse_learning.py
    +-- story_generator.py
    +-- quiz_engine.py
    +-- weak_spot_analyzer.py
    +-- spaced_repetition.py
    +-- mind_map.py
    +-- multiplayer_quiz.py
    +-- exam_pattern.py
    +-- study_twin.py
    +-- voice_mode.py
```

---

## Data Models (`src/models.py`)

### `Chunk`
| Field            | Type   | Notes                                    |
|------------------|--------|------------------------------------------|
| chunk_id         | str    | UUID                                     |
| doc_id           | str    | Parent document UUID                     |
| page_number      | int    | 0 for TXT files                          |
| section_heading  | str    | Detected heading or "Unknown"            |
| content          | str    | Raw text of this chunk                   |

### `Document`
| Field           | Type         | Notes                          |
|-----------------|--------------|--------------------------------|
| doc_id          | str          | UUID                           |
| file_name       | str          |                                |
| file_type       | str          | "pdf" or "txt"                 |
| raw_text        | str          | Full extracted text            |
| chunks          | List[Chunk]  | After chunking                 |
| content_hash    | str          | MD5 — for duplicate detection  |
| upload_timestamp| datetime     |                                |

### `QuizAttempt`
| Field          | Type   | Notes                              |
|----------------|--------|------------------------------------|
| question_id    | str    | UUID                               |
| question_text  | str    |                                    |
| difficulty     | str    | "easy" / "medium" / "hard"         |
| options        | list   | For MCQ                            |
| correct_answer | str    |                                    |
| user_answer    | str    |                                    |
| is_correct     | bool   |                                    |
| topic          | str    | Extracted topic label              |
| timestamp      | datetime |                                  |

### `UserProfile`
| Field             | Type                   | Notes                        |
|-------------------|------------------------|------------------------------|
| user_id           | str                    | Random UUID per session      |
| quiz_history      | List[QuizAttempt]      |                              |
| weak_topics       | List[str]              |                              |
| xp_points         | int                    | Starts at 0                  |
| current_streak    | int                    | Resets on wrong answer       |
| revision_schedule | Dict[str, List[str]]   | date_str -> list of topics   |

### `QuizRoom`
| Field        | Type           | Notes                                 |
|--------------|----------------|---------------------------------------|
| room_code    | str            | 6-char alphanumeric                   |
| host_id      | str            |                                       |
| participants | List[str]      | user_ids                              |
| questions    | List[dict]     | Pre-generated question dicts          |
| answers      | Dict[str,list] | user_id -> list of QuizAttempts       |
| leaderboard  | Dict[str,int]  | user_id -> score                      |
| status       | str            | "waiting" / "active" / "finished"     |

---

## Custom Exceptions (`src/exceptions.py`)

- `UnsupportedFileTypeError`
- `FileTooLargeError`
- `EmptyDocumentError`
- `DuplicateDocumentError`
- `OutOfScopeQueryError`
- `NoCitationFoundError`
- `WatsonxAPIError`
- `RoomNotFoundError`
- `RoomFullError`
- `QuizNotStartedError`
- `STTFailureError`
- `ChunkingFailureError`
- `InsufficientExplanationError`  -- Reverse Learning input < 30 words

---

## Sub-Tasks

---

### Sub-Task 1 — Project Scaffold and Core Shared Layer

**Status:** [ ] pending

**Intent:**
Set up the project folder structure, install dependencies, and build the three shared modules
that every feature depends on: `models.py`, `exceptions.py`, `session_state.py`, and
`watsonx_client.py`. No feature code is written yet.

**Expected Outcomes:**
- `requirements.txt` lists all dependencies
- `src/models.py` contains all dataclasses
- `src/exceptions.py` contains all custom exceptions
- `src/session_state.py` exposes `init_session()` which pre-populates all required keys
- `src/watsonx_client.py` wraps `ModelInference` with `generate_text()` and `chat()` and
  raises `WatsonxAPIError` on failure
- `.env.example` documents required env vars: `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`,
  `WATSONX_URL`

**Todo List:**
1. Create folder structure: `src/`, `src/features/`, `pages/`, `tests/`
2. Write `requirements.txt` with: `streamlit`, `ibm-watsonx-ai`, `pymupdf` (for PDF),
   `networkx`, `matplotlib`, `python-dotenv`, `pytest`
3. Write `src/models.py` with all dataclasses (Document, Chunk, QuizAttempt, UserProfile,
   QuizRoom)
4. Write `src/exceptions.py` with all custom exception classes
5. Write `src/session_state.py` with `init_session()` — must be called once on every page load
6. Write `src/watsonx_client.py`:
   - `WatsonxClient.__init__()` reads env vars, instantiates `ModelInference`
   - `generate_text(prompt, params)` wraps SDK call, catches SDK exceptions, raises
     `WatsonxAPIError`
   - `chat(messages, params)` wraps `ModelInference.chat()`
   - Default model: `ibm/granite-3-8b-instruct`
7. Write `app.py` — Streamlit entry point with sidebar navigation

**Relevant Context:**
- watsonx.ai SDK: `from ibm_watsonx_ai import APIClient, Credentials` and
  `from ibm_watsonx_ai.foundation_models import ModelInference`
- Credentials pattern from IBM docs:
  `Credentials(url=..., api_key=...)` then `APIClient(credentials)`
- Use `python-dotenv` to load `.env` at startup

---

### Sub-Task 2 — Document Ingestion Module

**Status:** [ ] pending

**Intent:**
Build `src/document_ingestion.py` — the module that accepts file uploads, validates them,
extracts text, detects sections, splits into chunks, deduplicates, and retrieves relevant
chunks for a given query.

**Expected Outcomes:**
- `upload_and_parse(file) -> Document` validates type/size, extracts text, chunks it, detects
  duplicates, stores in `session_state.documents`
- `extract_text_from_pdf(file_bytes) -> str` uses PyMuPDF (`fitz`)
- `extract_text_from_txt(file_bytes) -> str`
- `chunk_document(doc: Document) -> List[Chunk]` splits by heading pattern first; falls back
  to 500-word fixed windows if no headings found
- `detect_content_hash(raw_text: str) -> str` returns MD5 hex
- `retrieve_relevant_chunks(query: str, doc_id: str, top_k=3) -> List[Chunk]` simple
  TF-IDF-style keyword overlap scoring
- Raises: `UnsupportedFileTypeError`, `FileTooLargeError`, `EmptyDocumentError`,
  `DuplicateDocumentError`, `ChunkingFailureError`

**Todo List:**
1. Implement `extract_text_from_pdf()` using `fitz.open()`; detect scanned-only PDFs
   (zero extracted chars) and raise `EmptyDocumentError` with an OCR hint message
2. Implement `extract_text_from_txt()` — decode bytes as UTF-8, strip whitespace
3. Implement `detect_content_hash()`
4. Implement `chunk_document()`:
   - Try regex heading detection (e.g., lines in ALL-CAPS or starting with `Chapter`/`Section`)
   - Fall back to 500-word sliding windows
   - Tag each chunk with `page_number` and `section_heading`
5. Implement `retrieve_relevant_chunks()` using word-intersection scoring
6. Implement `upload_and_parse()` as the public entry point that calls all of the above

**Relevant Context:**
- PyMuPDF: `fitz.open(stream=bytes, filetype="pdf")` then `page.get_text()`
- Max file size: 10 MB (10 * 1024 * 1024 bytes)
- Allowed types: `.pdf`, `.txt`
- Edge case: if file is uploaded twice, compare `content_hash` and raise
  `DuplicateDocumentError`
- Edge case: flat TXT files with no headings must still produce valid chunks

---

### Sub-Task 3 — Upload Page and Explanation Feature

**Status:** [ ] pending

**Intent:**
Build the first two user-facing pages: `pages/01_Upload.py` and `pages/02_Explain.py`.
This proves the end-to-end pipeline from file upload through LLM response works.

**Expected Outcomes:**
- Upload page: Streamlit file uploader, success/error feedback, shows list of uploaded docs
- Explanation page: dropdown of uploaded docs + topic text input + persona selector (Grandma,
  Cricket Commentator, Movie Dialogue, Professor, ELI5); calls watsonx and displays result
- `src/features/explanation.py` contains `explain_topic(topic, persona, chunks) -> str`
  which builds a grounded prompt and calls `WatsonxClient.chat()`

**Todo List:**
1. Write `pages/01_Upload.py`:
   - `st.file_uploader()` accepting pdf and txt
   - Call `upload_and_parse()`; show success or catch and display custom exception messages
   - Show table of currently uploaded documents in `session_state`
2. Write `src/features/explanation.py`:
   - `PERSONA_PROMPTS` dict mapping each persona name to a system-prompt snippet
   - `explain_topic(topic, persona, chunks) -> str`:
     - Retrieve relevant chunks for the topic
     - Build a system prompt with persona instruction + grounding context
     - Call `WatsonxClient.chat()`
3. Write `pages/02_Explain.py`:
   - Selectbox for uploaded document
   - Text input for topic
   - Selectbox for persona
   - Call `explain_topic()` and render output in a styled `st.markdown` block
   - Guard: if no documents uploaded, show info message and stop

**Relevant Context:**
- Persona injection example system message: "You are a grandma explaining things to your
  grandchild. Use simple words and homely analogies. Answer ONLY from the provided notes."
- Always append: "Answer ONLY from the provided context. Do not make up information."
- Watsonx chat message format: `[{"role":"system","content":...},{"role":"user","content":...}]`

---

### Sub-Task 4 — Chatbot with RAG and Citations

**Status:** [ ] pending

**Intent:**
Build the doubt-solving chatbot (`pages/03_Chatbot.py` + `src/features/chatbot.py`) that
maintains multi-turn conversation history and enforces the grounding + citation business rule.

**Expected Outcomes:**
- Multi-turn chat UI with `st.chat_message` components
- Every AI response ends with a **Sources:** line citing `page N` or `Section: heading`
- If no relevant chunk is found, bot replies: "This question is outside my notes. Please ask
  something from your uploaded material." (raises / handles `OutOfScopeQueryError` internally)
- Chat history is stored in `session_state.chat_history` as a list of message dicts

**Todo List:**
1. Write `src/features/chatbot.py`:
   - `build_rag_context(chunks: List[Chunk]) -> str` formats chunks with page/section labels
   - `answer_doubt(query, doc_id, chat_history) -> tuple[str, List[Chunk]]`:
     - Retrieve top-3 chunks with `retrieve_relevant_chunks()`
     - If best chunk has zero keyword overlap, raise `OutOfScopeQueryError`
     - Build messages list: system prompt (grounding) + past turns + current user query
     - Call `WatsonxClient.chat()`
     - Return (answer_text, source_chunks)
   - `format_citation(chunks: List[Chunk]) -> str` returns formatted Sources string
2. Write `pages/03_Chatbot.py`:
   - Render existing `chat_history` with `st.chat_message`
   - Text input for new question; on submit call `answer_doubt()`
   - Append user + assistant messages to `chat_history`
   - Show `OutOfScopeQueryError` as a warning, not a crash
   - Guard: require at least one document uploaded

**Relevant Context:**
- Citation format: "**Sources:** Page 3 | Section: Photosynthesis"
- System prompt must say: "You MUST cite the page number and section of every claim."
- `OutOfScopeQueryError` is a soft error — display warning in chat, do not halt the app

---

### Sub-Task 5 — Reverse Learning (Feynman Mode)

**Status:** [ ] pending

**Intent:**
Build `pages/04_ReverseLearning.py` + `src/features/reverse_learning.py`. The student types
their explanation of a concept; the LLM identifies gaps and asks at least two follow-up
questions before producing a gap summary.

**Expected Outcomes:**
- Text area where student writes their explanation (min 30 words enforced)
- LLM responds with 2+ targeted gap-questions before the session ends
- After student answers both questions, shows a "Knowledge Gap Report"
- `InsufficientExplanationError` raised if input < 30 words

**Todo List:**
1. Write `src/features/reverse_learning.py`:
   - `evaluate_explanation(user_text, topic, chunks) -> dict`:
     - Build a prompt instructing the LLM to act as a tutor, read the context, and identify
       what the student's explanation is missing
     - Return structured dict: `{gaps: [...], follow_up_questions: [str, str, ...]}`
   - `check_minimum_length(text: str)` raises `InsufficientExplanationError` if < 30 words
   - `generate_gap_report(gaps: list, answers: list) -> str` produces a final markdown summary
2. Write `pages/04_ReverseLearning.py`:
   - State machine in `session_state`: `rl_stage` = "input" | "questioning" | "report"
   - Stage "input": text area + submit; validate length; call `evaluate_explanation()`
   - Stage "questioning": show questions one at a time; collect answers
   - Stage "report": call `generate_gap_report()` and display

**Relevant Context:**
- Prompt instruction: "The student has explained the concept below. Read the reference notes.
  Find at least 2 important concepts that are missing or incorrect. Ask follow-up questions."
- Business rule BR-04: minimum 2 follow-up questions before giving a report
- Edge case: if student's explanation is copied verbatim from notes, add a prompt check and
  reply: "Please explain in your own words."

---

### Sub-Task 6 — Story / Comic Generator

**Status:** [ ] pending

**Intent:**
Build `pages/05_StoryComic.py` + `src/features/story_generator.py`. Transforms a chapter or
topic into either a short story or a comic-panel-style narrative, grounded in the notes.

**Expected Outcomes:**
- User selects chapter/topic and output format (Short Story vs Comic Script)
- LLM produces a creative but factually grounded narrative
- Output includes a disclaimer: "Based on your notes. Verify facts before exam."

**Todo List:**
1. Write `src/features/story_generator.py`:
   - `generate_story(topic, style, chunks) -> str` where `style` is "story" or "comic"
   - System prompt instructs LLM to use only the provided notes as source material
   - Appends standard disclaimer to output
2. Write `pages/05_StoryComic.py`:
   - Topic input + format toggle
   - Spinner while generating
   - Render output with `st.markdown`

**Relevant Context:**
- Comic style prompt hint: "Format the output as numbered panels. Each panel has a one-line
  scene description and one character's dialogue."
- Story style prompt hint: "Write a short narrative story (under 400 words) that teaches the
  concept. Every fact must come from the provided notes."

---

### Sub-Task 7 — Adaptive Quiz Engine

**Status:** [ ] pending

**Intent:**
Build `pages/06_Quiz.py` + `src/features/quiz_engine.py`. The quiz generates questions from
uploaded notes, evaluates answers, adjusts difficulty in real-time, awards XP, and records
every attempt to `UserProfile.quiz_history`.

**Expected Outcomes:**
- Generates 5-question MCQ rounds from uploaded content
- Starts at "easy"; moves to "medium" after 3 correct in a row; moves to "hard" after 3 more
- Returns to "medium" after 2 consecutive wrong answers; back to "easy" after 2 more
- Awards 10 XP per correct answer; streak bonus (+5 XP) after 3+ consecutive correct answers
- All attempts stored in `session_state.profile.quiz_history`

**Todo List:**
1. Write `src/features/quiz_engine.py`:
   - `generate_questions(chunks, difficulty, n=5) -> List[dict]`:
     - Prompt LLM to produce MCQ questions at the specified difficulty level from the chunks
     - Parse LLM output into structured question dicts
   - `evaluate_answer(question: dict, user_answer: str) -> bool`
   - `adjust_difficulty(current: str, recent_results: List[bool]) -> str`:
     - Apply the 3-correct / 2-wrong threshold rules
   - `award_xp(is_correct: bool, streak: int) -> int`
   - `record_attempt(attempt: QuizAttempt)` appends to `session_state.profile.quiz_history`
2. Write `pages/06_Quiz.py`:
   - Session state: `quiz_questions`, `quiz_index`, `quiz_difficulty`, `recent_results`
   - Render current question as radio buttons
   - On submit: evaluate, award XP, adjust difficulty, advance index
   - Show score summary at end of round with XP earned

**Relevant Context:**
- LLM prompt for question generation: "Generate {n} multiple-choice questions at {difficulty}
  level from the following notes. Format each as: Q: ... A) ... B) ... C) ... D) ... Answer: ..."
- Parse answer with regex to extract option letter
- Edge case EC-06: if already at "hard" and still 100%, stay at "hard" and rotate topics

---

### Sub-Task 8 — Weak-Spot Analyzer and Spaced Repetition Scheduler

**Status:** [ ] pending

**Intent:**
Build `src/features/weak_spot_analyzer.py`, `src/features/spaced_repetition.py`, and their
pages. The analyzer reads quiz history to identify struggling topics; the scheduler produces
a revision calendar using a simplified SM-2 algorithm.

**Expected Outcomes:**
- `pages/07_WeakSpots.py`: horizontal bar chart showing % correct per topic
- Topics below 60% accuracy flagged as "weak" and stored in `profile.weak_topics`
- `pages/08_Schedule.py`: calendar-style table showing which topic to revise each day for
  the next 7–14 days

**Todo List:**
1. Write `src/features/weak_spot_analyzer.py`:
   - `analyze(quiz_history) -> Dict[str, float]` returns topic -> accuracy % map
   - `get_weak_topics(accuracy_map, threshold=0.6) -> List[str]`
   - `generate_report(accuracy_map) -> dict` for rendering
2. Write `src/features/spaced_repetition.py`:
   - `compute_schedule(weak_topics, start_date) -> Dict[str, List[str]]`:
     - Day 1: all weak topics
     - Day 3: topics below 50%
     - Day 7: all weak topics again
     - Day 14: final review of persistent weak topics
   - `update_on_quiz_result(profile, attempt)` recalculates weak topics after each quiz
3. Write `pages/07_WeakSpots.py`: bar chart via `matplotlib` + styled table
4. Write `pages/08_Schedule.py`: tabular schedule display; show "nothing today" if no weak
   topics found

**Relevant Context:**
- Edge case: if quiz history is empty, show placeholder: "Complete at least one quiz to see
  your weak spots."
- Weak topic threshold: < 60% correct across at least 3 attempts on that topic

---

### Sub-Task 9 — Mind-Map / Knowledge Graph

**Status:** [ ] pending

**Intent:**
Build `src/features/mind_map.py` and `pages/09_MindMap.py`. The LLM extracts topic
relationships from the uploaded notes; `networkx` + `matplotlib` renders a static image.

**Expected Outcomes:**
- LLM returns a list of `(concept_A, relationship, concept_B)` triples
- A directed graph is built from the triples and saved as a PNG
- PNG is displayed in Streamlit with `st.image()`
- If the graph has fewer than 3 nodes, show a warning that the content is too short

**Todo List:**
1. Write `src/features/mind_map.py`:
   - `extract_topic_relations(chunks) -> List[tuple]`:
     - Prompt LLM: "Extract all concept relationships from the notes as triples:
       (Concept A, relationship, Concept B). Return one triple per line."
     - Parse lines into `(A, rel, B)` tuples
   - `build_graph(triples) -> nx.DiGraph` using `networkx`
   - `render_graph(G: nx.DiGraph) -> bytes` returns PNG bytes via `matplotlib`
2. Write `pages/09_MindMap.py`:
   - Selectbox for document
   - "Generate Mind Map" button with spinner
   - Display PNG via `st.image()`
   - Edge case: if < 3 nodes, show `st.warning()`

**Relevant Context:**
- `nx.spring_layout()` for graph positioning
- Edge labels from the `relationship` part of each triple
- Keep node labels short — truncate to 20 characters if needed

---

### Sub-Task 10 — Multiplayer Quiz (Turn-Based)

**Status:** [ ] pending

**Intent:**
Build `src/features/multiplayer_quiz.py` and `pages/10_Multiplayer.py`. Turn-based: the host
creates a room, participants join using a room code, everyone answers questions sequentially,
and the leaderboard updates after each round.

**Expected Outcomes:**
- Host can create a room; system generates a 6-char room code stored in `session_state.rooms`
- At least 2 participants must join before the quiz starts (BR-05)
- Each participant answers questions in their own turn
- Leaderboard shows ranking by score with XP and streaks
- Room status transitions: "waiting" → "active" → "finished"

**Todo List:**
1. Write `src/features/multiplayer_quiz.py`:
   - `create_room(host_id, questions) -> QuizRoom`
   - `join_room(room_code, user_id) -> QuizRoom`:
     - Raises `RoomNotFoundError` or `RoomFullError` (max 10 participants)
   - `submit_answer(room_code, user_id, question_idx, answer) -> int` returns XP delta
   - `get_leaderboard(room_code) -> List[tuple]` sorted by score desc
   - `start_quiz(room_code)` validates min 2 participants; raises `QuizNotStartedError` if not
2. Write `pages/10_Multiplayer.py`:
   - Tab 1 "Host": create room, generate questions from uploaded notes, show room code
   - Tab 2 "Join": enter room code, join, wait for host to start
   - Active quiz: show question, radio buttons, submit; advance to next question
   - Leaderboard panel that updates after each participant's turn

**Relevant Context:**
- `session_state.rooms` is a dict: `{room_code: QuizRoom}`
- Room code generation: `random.choices(string.ascii_uppercase + string.digits, k=6)`
- Turn tracking: `QuizRoom.current_turn_index` tracks whose turn it is
- Edge case EC-07: if host closes the page, mark room status as "finished"

---

### Sub-Task 11 — Exam Pattern Predictor and Study Twin

**Status:** [ ] pending

**Intent:**
Build two analysis features: exam pattern prediction (from past paper uploads) and the Study
Twin persona (how a top student would approach a topic).

**Expected Outcomes:**
- `pages/11_ExamPattern.py`: accepts 1+ past paper uploads; LLM identifies frequently tested
  topics and question types; displays frequency table
- Warning shown if fewer than 2 papers are uploaded (MR-08)
- `pages/12_StudyTwin.py`: user selects a topic; LLM generates a "topper" persona walkthrough

**Todo List:**
1. Write `src/features/exam_pattern.py`:
   - `analyze_papers(paper_chunks: List[List[Chunk]]) -> dict`:
     - Prompt LLM to identify topic frequency and question types across all papers
     - Return `{topic: {count: int, question_types: [str]}}`
   - `generate_frequency_table(analysis: dict) -> str` formats as markdown table
2. Write `src/features/study_twin.py`:
   - `generate_study_twin(topic, chunks) -> str`:
     - Persona prompt: "You are a student who always scores 100%. Explain how you would master
       this topic step by step, including memory tricks, key formulas, and likely exam questions."
3. Write `pages/11_ExamPattern.py`: file uploader for past papers + frequency table display
4. Write `pages/12_StudyTwin.py`: topic input + styled "Study Twin" response card

**Relevant Context:**
- Past paper upload reuses `document_ingestion.upload_and_parse()` — no new parsing logic
- Warning text: "For reliable predictions, upload at least 2-3 past papers."
- Study Twin output should be clearly labelled as a model persona, not real student data

---

### Sub-Task 12 — Voice Mode

**Status:** [ ] pending

**Intent:**
Build `pages/13_VoiceMode.py` + `src/features/voice_mode.py`. Users record a voice question;
the app sends audio to a cloud STT API, passes the transcript to the chatbot, then reads
the answer back with a TTS API. Degrades gracefully to typed input if STT fails.

**Expected Outcomes:**
- Audio recorder widget in Streamlit
- STT transcription shown to user before sending to chatbot (so they can correct it)
- Chatbot answer displayed and read aloud via TTS
- `STTFailureError` caught gracefully — UI falls back to text input

**Todo List:**
1. Write `src/features/voice_mode.py`:
   - `transcribe_audio(audio_bytes: bytes) -> str`:
     - Calls cloud STT API (IBM Watson Speech-to-Text or equivalent)
     - Raises `STTFailureError` if response is empty or API fails
   - `synthesize_speech(text: str) -> bytes`:
     - Calls cloud TTS API
     - Returns audio bytes for playback
2. Write `pages/13_VoiceMode.py`:
   - Use `streamlit-audiorecorder` or `st.file_uploader` for audio input
   - Call `transcribe_audio()`; display transcript in editable text area
   - On confirm: pass transcript to `chatbot.answer_doubt()`
   - Auto-play TTS response with `st.audio()`
   - Catch `STTFailureError` and show text input fallback

**Relevant Context:**
- Graceful degradation (BR-10): if STT fails, show: "Voice recognition failed. Please type
  your question below."
- TTS only speaks the first 500 characters of a response to keep audio clips short
- Audio upload max: 60 seconds, WAV or MP3 format only

---

### Sub-Task 13 — Input Validation, Error Handling, and Tests

**Status:** [ ] pending

**Intent:**
Harden all input paths with consistent validation, ensure all custom exceptions surface as
friendly Streamlit messages (not tracebacks), and write basic unit tests for core logic.

**Expected Outcomes:**
- All file uploads enforce type + size check via a shared `validate_upload()` utility
- All pages wrap feature calls in try/except blocks that map exceptions to `st.error()` or
  `st.warning()` messages
- `tests/` folder with unit tests for: chunk scoring, difficulty adjustment, XP calculation,
  spaced repetition schedule, quiz answer evaluation

**Todo List:**
1. Write `src/validation.py`:
   - `validate_upload(file)`: checks extension and size; raises appropriate exception
   - `validate_text_input(text, min_words=0, max_chars=1000)`: raises `ValueError` with message
2. Add try/except wrapper to every page that calls a feature module
3. Write `tests/test_quiz_engine.py`: test `adjust_difficulty()` and `award_xp()`
4. Write `tests/test_document_ingestion.py`: test `chunk_document()` and
   `retrieve_relevant_chunks()`
5. Write `tests/test_spaced_repetition.py`: test `compute_schedule()` output structure

**Relevant Context:**
- Streamlit error display: `st.error("message")` for hard errors, `st.warning("message")` for
  soft warnings
- Tests use `pytest` and do NOT call the real watsonx API — use mocking for `WatsonxClient`

---

## Input Validation Summary

| Input                    | Rule                                                    | Exception                   |
|--------------------------|---------------------------------------------------------|-----------------------------|
| File upload              | .pdf or .txt only; max 10 MB                           | UnsupportedFileTypeError / FileTooLargeError |
| Doubt / question text    | Non-empty; max 1000 chars                              | ValueError                  |
| Reverse learning input   | Minimum 30 words                                       | InsufficientExplanationError|
| Persona selection        | Must be from fixed allowlist                           | ValueError                  |
| Quiz answer              | Must be selected before submit button is active        | (UI-enforced)               |
| Room code                | Exactly 6 alphanumeric characters                      | RoomNotFoundError           |
| Audio input              | WAV or MP3; max 60 seconds                             | STTFailureError             |
| Past paper count         | Warn if < 2 papers for exam prediction                 | (soft warning only)         |

---

## Business Rules Summary

| ID    | Rule                                                                                       |
|-------|--------------------------------------------------------------------------------------------|
| BR-01 | Chatbot answers ONLY from uploaded content                                                |
| BR-02 | Every chatbot answer MUST cite page number or section                                     |
| BR-03 | Quiz always starts at "easy" per session                                                  |
| BR-04 | Reverse Learning: minimum 2 follow-up questions before gap report                        |
| BR-05 | Multiplayer quiz cannot start with fewer than 2 participants                              |
| BR-06 | XP only awarded within the time limit (turn-based: before submitting next question)       |
| BR-07 | Spaced repetition schedule recalculated whenever weak topics change                      |
| BR-08 | Story/comic generator must stay grounded in uploaded notes                                |
| BR-09 | Uploads restricted to PDF and TXT only                                                    |
| BR-10 | Voice mode falls back to typed input if STT fails                                         |

---

## Edge Cases Summary

| ID    | Scenario                                        | Handling                                          |
|-------|-------------------------------------------------|---------------------------------------------------|
| EC-01 | Question asked before upload                    | Guard on every page; show info message            |
| EC-02 | PDF is scanned images only                      | EmptyDocumentError with OCR hint                  |
| EC-03 | Two equally relevant chunks                     | Return both; cite both                            |
| EC-04 | Question in different language than notes       | Note mismatch; answer may be unreliable           |
| EC-05 | Reverse learning input copied verbatim          | Similarity check; prompt for own words            |
| EC-06 | Already at Hard difficulty, 100% score          | Stay at Hard; rotate topics                       |
| EC-07 | Multiplayer host disconnects                    | Room marked "finished"; participants notified     |
| EC-08 | Only one past paper uploaded                    | Soft warning; still attempt prediction            |
| EC-09 | Noisy audio input                               | Low-confidence flag; offer re-record or type      |
| EC-10 | Document has no headings                        | Fall back to 500-word fixed chunks                |
| EC-11 | Story contradicts notes                         | Disclaimer appended to output                     |
| EC-12 | Duplicate file uploaded                         | DuplicateDocumentError; skip re-processing        |

---

## Incremental Phase Delivery Order

| Phase | Sub-Tasks          | Deliverable                                       |
|-------|--------------------|---------------------------------------------------|
| 1     | ST-1, ST-2, ST-3   | Working upload + explanation + chatbot            |
| 2     | ST-4, ST-5, ST-6   | Reverse learning + story + basic quiz             |
| 3     | ST-7, ST-8         | Adaptive quiz + weak spots + schedule             |
| 4     | ST-9, ST-10        | Mind map + multiplayer quiz                       |
| 5     | ST-11, ST-12, ST-13| Exam pattern + study twin + voice + tests         |

---

## Open Decisions (Resolved)

| Decision              | Choice                                                |
|-----------------------|-------------------------------------------------------|
| Persistence           | Single-session (st.session_state) only               |
| Multiplayer mode      | Turn-based (no WebSocket needed)                      |
| Voice STT/TTS         | Cloud API (IBM Watson Speech or equivalent)           |
| Primary LLM           | ibm/granite-3-8b-instruct                             |
| Mind-map renderer     | networkx + matplotlib (static PNG)                    |
