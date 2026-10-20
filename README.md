# SRGI Campus AI

A Streamlit app for students, parents and visitors: AI question answering (TF-IDF + cosine similarity),
campus navigation with walking routes, events (with an "Organise Event" form) and FAQ pages.

## Run it in VS Code

1. Install **Python 3.10 or newer** and open this folder in VS Code (`File > Open Folder`).
2. Open a terminal (`Ctrl + ~`) and create a virtual environment:
   - Windows: `python -m venv .venv` then `.venv\Scripts\activate`
   - Mac/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
3. Install the packages: `pip install -r requirements.txt`
4. Start the app: `streamlit run app.py` (or press **F5** and choose "SRGI Campus AI (Streamlit)").
5. The browser opens at http://localhost:8501

Run the commands from the project folder (the one that contains `app.py`).

## Folder guide

| Path | What it is |
|---|---|
| `app.py` | The whole app (pages, design, navigation, events) |
| `utils/ai_search.py` | The AI: TF-IDF search with spell-fixing and synonyms |
| `college_config.py` | College name, website, contacts, latitude/longitude (for the weather card) |
| `.streamlit/config.toml` | Dark theme colours (must stay inside `.streamlit/`) |
| `data/campus_faq.csv` | The 150 FAQs the AI answers from |
| `data/events.csv` | Events. Columns: date, event, venue, time, branch, organizer, description, registration, banner |
| `data/locations.csv` | Places on campus (name, block, floor, room, description, image) |
| `data/paths.csv` | Walking links between places (place_a, place_b, how_to_walk, minutes) |
| `images/` | Place photos named in `locations.csv`. Add `college_poster.jpg` for the Home hero photo |
| `videos/` | Optional `tutorial.mp4` for the Home page |
| `data/brochure.pdf` | Optional: enables the "Download Brochure" button |
| `data/announcements.csv` | Optional (title,date,color): replaces the automatic announcements |

Saving any CSV updates the app automatically (no restart needed).

## Things you should still replace

* `images/*.jpg` are **placeholder pictures**; replace them with real photos using the same file names.
* The 10 rows in `paths.csv` that say `SAMPLE -` and the `Inside ...` rows are not surveyed walking directions.
  Edit the `how_to_walk` text and `minutes` to match your campus.
* Many FAQ answers say "(sample)" or use placeholder phones/e-mails (`sit-example.edu.in`). Replace them with real details.
* `events.csv` has empty `time` and `organizer` columns; fill them in for a better event page.
* `USER_NAME` at the top of `app.py` is the name shown on the Home page.

## How to add things

* **A new place:** add a row to `locations.csv`, then add at least one row to `paths.csv` linking it to a place that
  is already connected (names must match exactly, capital letters do not matter).
* **A new FAQ:** add a row to `campus_faq.csv`. Put the words students might type in the `keywords` column.
* **Events from the form:** submitted events go to `data/event_requests.csv`. Copy approved rows into `events.csv`.
  Set `AUTO_PUBLISH_EVENTS = True` in `app.py` to publish them instantly.
hello mai name is abhijeet  singh