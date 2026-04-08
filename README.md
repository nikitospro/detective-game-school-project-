# AI Detective Lab

AI Detective Lab is a small educational detective game built with Python, Flask, and Ollama.

The idea is simple: the player becomes a detective, questions suspects, studies clues, writes notes, and then makes a final accusation. The important part is that the story logic is not generated randomly by AI. The case itself is fixed in code, while the local language model is used only to make the experience feel more alive: dialogue, clue commentary, short narrative text, and the final report.

That makes the project a good classroom demo:

- it feels interactive;
- it looks more impressive than a plain script;
- it is still predictable and explainable;
- it does not let the LLM invent a completely different story.

## What this project can do

- let the player choose a case;
- show suspects and basic case information;
- run suspect interrogations in chat format;
- analyze clues with AI-generated explanations;
- keep personal notes during the investigation;
- highlight contradictions between evidence and testimonies;
- show suspicion indicators;
- support several difficulty levels;
- evaluate the final accusation;
- generate a detective rank at the end;
- keep working in fallback mode if Ollama is unavailable.

## Why the architecture is hybrid

This is one of the most important ideas in the project.

The LLM does not control the truth of the story.

Instead:

- `cases.py` contains the real structure of each case;
- `game_logic.py` decides what is correct, what is suspicious, and how the accusation is scored;
- `ollama_client.py` only helps present the experience in a more human way.

So if the model is slow, unavailable, or behaves strangely, the application still does not lose the actual logic of the case.

## Project structure

```text
app.py
cases.py
game_logic.py
ollama_client.py
utils.py
requirements.txt
README.md
templates/
  base.html
  index.html
static/
  style.css
data/
  sessions/
```

## Code explanation

This section explains what each file does in normal language.

### `app.py`

This is the Flask entry point.

It creates the web app, handles routes, reads form data from the interface, loads the current session state, and sends everything to the game engine.

In other words:

- the browser talks to `app.py`;
- `app.py` talks to the game logic;
- the result is rendered back into the HTML template.

Important responsibilities:

- selecting a case;
- selecting a suspect or clue;
- sending interrogation questions;
- saving notes;
- generating a summary;
- checking the final accusation.

### `cases.py`

This file contains the detective world itself.

It defines data classes such as:

- `Suspect`
- `Clue`
- `Contradiction`
- `Solution`
- `CaseFile`

It also stores the actual cases used in the game.

That means if you want to create a new story, this is the main place where you would add:

- a new victim;
- new suspects;
- new clues;
- the correct culprit;
- the real logical explanation.

### `game_logic.py`

This is the brain of the project.

If `app.py` is the web shell, then `game_logic.py` is the actual detective system.

It is responsible for:

- creating a new investigation state;
- switching cases;
- tracking which suspect is active;
- saving what clues the player has viewed;
- unlocking contradictions;
- calculating suspicion levels;
- evaluating the final accusation;
- assigning a score and detective rank.

This file is especially important because it keeps the game deterministic. The player can talk to characters freely, but the real answer still comes from this logic layer.

### `ollama_client.py`

This file is the local AI wrapper.

It uses the Python `ollama` package to talk to a local Ollama installation. The app does not send data to an external cloud API.

It handles:

- dialogue generation for suspects;
- clue explanations;
- short narrative text;
- the final report;
- timeouts and errors;
- fallback responses if the model fails;
- protection against empty or broken AI output.

It also uses strong prompts so the model stays inside the case boundaries and does not invent new facts.

### `utils.py`

This file contains helper tools used across the project.

Examples:

- text normalization for scoring;
- stable seeding for more consistent model output;
- JSON session storage;
- detective rank calculation;
- safety helpers for text handling.

It is the “supporting toolbox” of the application.

### `templates/base.html` and `templates/index.html`

These files define the interface.

`base.html` is the general page skeleton.  
`index.html` is the main detective dashboard.

The page includes:

- a header;
- case controls;
- the case overview;
- suspect cards;
- the interrogation panel;
- clue analysis;
- notes;
- accusation form;
- result panel.

### `static/style.css`

This is the styling for the interface.

It gives the project its detective-board feeling: cards, panels, labels, spacing, responsive layout, and a more polished classroom-demo look.

## How data flows through the app

The overall flow looks like this:

1. The user opens the Flask page.
2. `app.py` loads the saved session state.
3. The request is passed into `GameEngine` from `game_logic.py`.
4. If AI text is needed, `game_logic.py` calls `ollama_client.py`.
5. The result is returned to the template.
6. The browser shows the updated investigation board.

For the final accusation:

1. the player chooses a suspect;
2. writes a motive;
3. writes supporting evidence;
4. `game_logic.py` compares that input with the real solution from `cases.py`;
5. the app computes a score, missed clues, reasoning quality, and final rank.

## Requirements

- Python 3.10 or newer
- Ollama installed locally
- a local Ollama model, for example `llama3.1:8b`, `mistral`, or `qwen2.5`

## Installation

### 1. Create a virtual environment

```bash
python -m venv venv
```

### 2. Activate it

Linux/macOS:

```bash
source venv/bin/activate
```

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Installing Ollama

The official Ollama download page is:

`https://ollama.com/download`

On Linux you can also install it with the official script:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

After installation, make sure Ollama is running locally.

## Downloading a model

Example:

```bash
ollama pull llama3.1:8b
```

You can also try:

```bash
ollama pull mistral
ollama pull qwen2.5
```

## Running the app

### 1. Make sure Ollama is running

You can quickly check it with:

```bash
ollama list
```

### 2. Optionally choose a default model

Linux/macOS:

```bash
export OLLAMA_MODEL=llama3.1:8b
```

Windows PowerShell:

```powershell
$env:OLLAMA_MODEL="llama3.1:8b"
```

### 3. Start the Flask application

```bash
python app.py
```

### 4. Open it in the browser

```text
http://127.0.0.1:5000
```

## Useful environment variables

- `OLLAMA_MODEL` sets the default model
- `OLLAMA_HOST` sets a custom local Ollama host if you are not using the default local setup
- `OLLAMA_TIMEOUT` sets the request timeout in seconds
- `FLASK_SECRET_KEY` sets the Flask session secret

## How to play

1. Choose a case.
2. Pick a difficulty level.
3. Open suspects and question them.
4. Study clues and compare them with testimonies.
5. Write your own notes.
6. Look for contradictions.
7. Make a final accusation.
8. Read the final evaluation and report.

## Difficulty levels

- `Кадет` gives more help and includes a softer summary hint.
- `Следователь` is the standard mode.
- `Эксперт` reveals contradictions later and hides precise suspicion percentages.

## What happens if Ollama fails

The app does not crash.

Instead:

- it switches to deterministic fallback responses;
- it warns the user that reserve mode is being used;
- the investigation logic still stays valid.

This is useful in a classroom, because even if the model is unavailable, the demo still works.

## Common problems

### Ollama is not responding

Check:

```bash
ollama list
```

If that does not work, Ollama is probably not running.

### The model is missing

Download it manually:

```bash
ollama pull llama3.1:8b
```

### The app starts, but AI responses fall back

This usually means one of these:

- Ollama is not running;
- the selected model is not installed;
- the model is too slow for the chosen timeout;
- the local model returned an unusable response, so the safety wrapper switched to fallback mode.

### Port `5000` is busy

Change the port in `app.py` or stop the other process using `127.0.0.1:5000`.

### The investigation reset

Session files are stored in `data/sessions/`.  
If those files are removed, the game starts from the beginning again.

## Classroom demo idea

If you want to show this project in class, a nice flow is:

1. open the case and explain the story;
2. question one suspect;
3. open one clue and show the AI explanation;
4. point out that the truth still comes from the predefined case logic;
5. make a final accusation and compare the result with the real solution.

## Final note

This project is intentionally small enough to understand, but structured enough to feel like a real application.

If you want to extend it, the easiest next steps are:

- add more cases in `cases.py`;
- improve scoring rules in `game_logic.py`;
- refine prompts in `ollama_client.py`;
- redesign the interface in `templates/` and `static/style.css`.
