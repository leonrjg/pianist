# Anki Rating Logging Documentation

## Overview

Comprehensive logging has been added to track Anki card rating submissions. This helps diagnose intermittent "not at top of queue" and other rating errors.

## What's Being Logged

### 1. User Action (actions.py)
When user clicks a rating button:
```
[ANKI RATING] User clicked 'Good' (ease=3) for card 1234567890
[ANKI RATING] Card details: deck=!Zettelkasten::Math
[ANKI RATING] Reminder ID: 42, Reminder name: Review probability
```

### 2. Rating Submission (anki_service.py)
When `submit_rating()` is called:
```
[RATING] Submitting rating for card 1234567890 with ease 3
[RATING] Card info before rating:
  - Card ID: 1234567890
  - Deck: !Zettelkasten::Math
  - Type: 0
  - Queue: 0
  - Due: 1337
  - Interval: 7
  - Factor: 2500
  - Reps: 3
```

**Card State Fields Explained:**
- `type`: 0=new, 1=learning, 2=review, 3=relearning
- `queue`: -3=user buried, -2=sched buried, -1=suspended, 0=new, 1=learning, 2=review, 3=day learning
- `due`: Due position (for new) or due date (for review)
- `interval`: Days until next review
- `factor`: Ease factor (2500 = 250%)
- `reps`: Number of reviews

### 3. AnkiConnect API Call
```
[RATING] Calling answerCards API...
AnkiConnect request: action=answerCards, params={'answers': [{'cardId': 1234567890, 'ease': 3}]}
AnkiConnect response: {'result': [True], 'error': None}
[RATING] answerCards returned: [True]
```

### 4. Success
```
[RATING] ✓ Rating submitted successfully for card 1234567890
[ANKI RATING] ✓ submit_rating completed successfully
[ANKI RATING] Cache cleared for reminder 42
[ANKI RATING] Toast updated to show success
```

### 5. Error Cases
```
[RATING] ✗ Rating submission returned False for card 1234567890
AnkiConnect returned error: cannot answer, not at top of queue

OR

[ANKI RATING] ✗ AnkiConnectError occurred: AnkiConnect error: cannot answer, not at top of queue
[ANKI RATING] Card ID: 1234567890, Ease: 3, Label: Good
```

## How to Capture Logs

### Option 1: Terminal Output
When running from terminal, logs appear in real-time:
```bash
cd src
python main.py  # or however you run the app
```

Logs will print to console with timestamps.

### Option 2: Redirect to File
Capture all output to a file:
```bash
python main.py 2>&1 | tee anki_logs.txt
```

Or append to a log file:
```bash
python main.py >> anki_logs.txt 2>&1
```

### Option 3: IDE Console
If running from PyCharm/VS Code, logs appear in the Run/Debug console.

## When the Error Occurs

Next time you see "error rating, not at top of queue":

1. **Check the terminal/console** - logs are printed there
2. **Copy the entire log section** from `[ANKI RATING] User clicked` through `[ANKI RATING] Toast updated`
3. **Look for these key details:**
   - Card `type` and `queue` values
   - The exact error message from AnkiConnect
   - Whether it happened on first attempt or multiple attempts
   - Timing between attempts

## What to Share

When the error occurs, share:
```
=== START OF ERROR LOGS ===
[Paste everything from [ANKI RATING] User clicked... through the error]
=== END OF ERROR LOGS ===
```

This will show:
- ✓ What card state Anki reports
- ✓ Exact error message from AnkiConnect
- ✓ Full request/response details
- ✓ Context about the reminder and deck

## Example Full Log Sequence

**Successful rating:**
```
2026-02-04 15:30:42,123 - actions - INFO - [ANKI RATING] User clicked 'Good' (ease=3) for card 1748059073623
2026-02-04 15:30:42,124 - actions - INFO - [ANKI RATING] Card details: deck=!Zettelkasten::Math::Graphs
2026-02-04 15:30:42,124 - actions - INFO - [ANKI RATING] Reminder ID: 5, Reminder name: TSP Review
2026-02-04 15:30:42,125 - actions - INFO - [ANKI RATING] Calling submit_rating...
2026-02-04 15:30:42,126 - anki_service - INFO - [RATING] Submitting rating for card 1748059073623 with ease 3
2026-02-04 15:30:42,150 - anki_service - DEBUG - AnkiConnect request: action=cardsInfo, params={'cards': [1748059073623]}
2026-02-04 15:30:42,165 - anki_service - DEBUG - AnkiConnect response: {'result': [...], 'error': None}
2026-02-04 15:30:42,166 - anki_service - INFO - [RATING] Card info before rating:
2026-02-04 15:30:42,166 - anki_service - INFO -   - Card ID: 1748059073623
2026-02-04 15:30:42,166 - anki_service - INFO -   - Deck: !Zettelkasten::Math::Graphs
2026-02-04 15:30:42,166 - anki_service - INFO -   - Type: 0
2026-02-04 15:30:42,166 - anki_service - INFO -   - Queue: 0
2026-02-04 15:30:42,167 - anki_service - INFO -   - Due: 1576
2026-02-04 15:30:42,167 - anki_service - INFO -   - Interval: 0
2026-02-04 15:30:42,167 - anki_service - INFO -   - Factor: 0
2026-02-04 15:30:42,167 - anki_service - INFO -   - Reps: 0
2026-02-04 15:30:42,168 - anki_service - INFO - [RATING] Calling answerCards API...
2026-02-04 15:30:42,169 - anki_service - DEBUG - AnkiConnect request: action=answerCards, params={'answers': [{'cardId': 1748059073623, 'ease': 3}]}
2026-02-04 15:30:42,185 - anki_service - DEBUG - AnkiConnect response: {'result': [True], 'error': None}
2026-02-04 15:30:42,186 - anki_service - INFO - [RATING] answerCards returned: [True]
2026-02-04 15:30:42,186 - anki_service - INFO - [RATING] ✓ Rating submitted successfully for card 1748059073623
2026-02-04 15:30:42,187 - actions - INFO - [ANKI RATING] ✓ submit_rating completed successfully
2026-02-04 15:30:42,188 - actions - INFO - [ANKI RATING] Cache cleared for reminder 5
2026-02-04 15:30:42,189 - actions - INFO - [ANKI RATING] Toast updated to show success
```

## Interpreting the Logs

### Normal Flow
1. User clicks button → logs card and reminder info
2. Fetches card state → logs type, queue, due, interval
3. Calls answerCards → logs request
4. Gets response → logs result
5. Success → logs confirmation

### Error Flow
- Same steps 1-3
- Step 4: Response has error field set
- Logs show exact error from Anki
- Toast shows error to user

### Key Indicators

**If `queue: -1`** → Card is suspended, can't be answered
**If `queue: -2` or `-3`** → Card is buried, can't be answered
**If `type: 0` and `queue: 0`** → New card, should be answerable
**If `type: 2` and `queue: 2`** → Review card, should be answerable

**Error: "not at top of queue"** → Anki's scheduler state issue, possibly:
- Another card is currently being reviewed in Anki GUI
- Card state changed between fetch and answer
- Anki's internal queue state is inconsistent

---

**Files Modified:**
- `core/integrations/anki_service.py` - Added detailed logging to submit_rating and _invoke
- `core/reminder/actions.py` - Added logging to rating callback

**Log Levels:**
- INFO: Normal operation flow
- DEBUG: AnkiConnect request/response details
- ERROR: Failures and exceptions
- WARNING: Non-critical issues
