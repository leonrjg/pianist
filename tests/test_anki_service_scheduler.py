import logging
from datetime import datetime

import pytest

from core.integrations.anki_service import AnkiConnectError, AnkiService


@pytest.fixture(autouse=True)
def reset_anki_service_state(monkeypatch):
    AnkiService._card_cache.clear()
    AnkiService._shown_card_ids.clear()
    AnkiService.clear_deck_config_cache()
    monkeypatch.setattr(AnkiService, "_get_field_extraction_strategy", lambda *args: ([], []))
    monkeypatch.setattr(AnkiService, "_process_latex", lambda text: text)
    monkeypatch.setattr(AnkiService, "_resolve_media_paths", lambda text: text)
    yield
    AnkiService._card_cache.clear()
    AnkiService._shown_card_ids.clear()
    AnkiService.clear_deck_config_cache()


def _card(card_id, *, deck="Default", queue=2, card_type=2, due=0, interval=1, ord_=0):
    return {
        "cardId": card_id,
        "deckName": deck,
        "question": f"front {card_id}",
        "answer": f"back {card_id}",
        "modelName": "Basic",
        "fields": {},
        "ord": ord_,
        "type": card_type,
        "queue": queue,
        "due": due,
        "interval": interval,
        "note": card_id + 1000,
    }


def test_submit_rating_prepares_due_order_then_calls_answer_cards(monkeypatch):
    calls = []

    def fake_invoke(action, params=None):
        calls.append((action, params))
        if action == "setSpecificValueOfCard":
            return [True]
        if action == "answerCards":
            return [True]
        raise AssertionError(f"unexpected action: {action}")

    monkeypatch.setattr(AnkiService, "_invoke", fake_invoke)

    assert AnkiService.submit_rating(123, 3) is True
    assert calls == [
        ("setSpecificValueOfCard", {
            "card": 123,
            "keys": ["due"],
            "newValues": [0],
            "warning_check": True,
        }),
        ("answerCards", {"answers": [{"cardId": 123, "ease": 3}]}),
    ]


def test_submit_rating_failure_does_not_try_to_fetch_another_card(monkeypatch):
    calls = []

    def fake_invoke(action, params=None):
        calls.append((action, params))
        if action == "setSpecificValueOfCard":
            return [True]
        if action == "answerCards":
            return [False]
        raise AssertionError(f"unexpected action: {action}")

    monkeypatch.setattr(AnkiService, "_invoke", fake_invoke)

    with pytest.raises(AnkiConnectError):
        AnkiService.submit_rating(123, 3)

    assert [action for action, _ in calls] == ["setSpecificValueOfCard", "answerCards"]


def test_get_card_prefers_due_cards_and_does_not_query_new_when_due_exists(monkeypatch):
    calls = []
    cards = {1: _card(1, due=5), 2: _card(2, card_type=0, queue=0, due=1)}

    def fake_invoke(action, params=None):
        calls.append((action, params))
        if action == "findCards":
            assert "is:due" in params["query"]
            return [1]
        if action == "cardsInfo":
            return [cards[card_id] for card_id in params["cards"]]
        if action == "getDeckConfig":
            return {"reviewOrder": 0}
        raise AssertionError(f"unexpected action: {action}")

    monkeypatch.setattr(AnkiService, "_invoke", fake_invoke)

    card = AnkiService.get_card("Default", reminder_id="reminder-1")

    assert card.card_id == 1
    assert "is:new" not in " ".join(params["query"] for action, params in calls if action == "findCards")


def test_get_card_does_not_fallback_to_all_unsuspended_cards(monkeypatch):
    queries = []

    def fake_invoke(action, params=None):
        if action == "findCards":
            queries.append(params["query"])
            return []
        raise AssertionError(f"unexpected action: {action}")

    monkeypatch.setattr(AnkiService, "_invoke", fake_invoke)

    with pytest.raises(AnkiConnectError, match="finished deck 'Default' for today"):
        AnkiService.get_card("Default")

    assert queries == [
        'deck:"Default" is:due -is:suspended',
        'deck:"Default" is:new -is:suspended',
    ]


def test_due_selection_orders_learning_before_review_then_due(monkeypatch):
    cards = {
        1: _card(1, queue=2, card_type=2, due=0),
        2: _card(2, queue=1, card_type=1, due=99),
        3: _card(3, queue=2, card_type=2, due=-1),
    }

    def fake_invoke(action, params=None):
        if action == "findCards":
            return [1, 2, 3]
        if action == "cardsInfo":
            return [cards[card_id] for card_id in params["cards"]]
        if action == "getDeckConfig":
            return {"reviewOrder": 0}
        raise AssertionError(f"unexpected action: {action}")

    monkeypatch.setattr(AnkiService, "_invoke", fake_invoke)

    card = AnkiService.get_card("Default")

    assert card.card_id == 2


def test_all_shown_due_cards_fall_through_to_new(monkeypatch, caplog):
    calls = []
    AnkiService._shown_card_ids.add(1)
    caplog.set_level("INFO")
    cards = {2: _card(2, queue=0, card_type=0, due=99)}

    def fake_invoke(action, params=None):
        calls.append((action, params))
        if action == "findCards":
            if "is:due" in params["query"]:
                return [1]
            if "is:new" in params["query"]:
                return [2]
        if action == "cardsInfo":
            return [cards[card_id] for card_id in params["cards"]]
        if action == "getDeckConfig":
            return {"newSortOrder": 1, "newGatherPriority": 1}
        raise AssertionError(f"unexpected action: {action}")

    monkeypatch.setattr(AnkiService, "_invoke", fake_invoke)

    card = AnkiService.get_card("Default")

    assert card.card_id == 2
    assert [params["query"] for action, params in calls if action == "findCards"] == [
        'deck:"Default" is:due -is:suspended',
        'deck:"Default" is:new -is:suspended',
    ]
    assert "already displayed" in caplog.text


def test_all_shown_due_and_new_cards_raise(monkeypatch, caplog):
    AnkiService._shown_card_ids.update({1, 2})
    caplog.set_level("INFO")

    def fake_invoke(action, params=None):
        if action == "findCards":
            if "is:due" in params["query"]:
                return [1]
            if "is:new" in params["query"]:
                return [2]
        raise AssertionError(f"unexpected action: {action}")

    monkeypatch.setattr(AnkiService, "_invoke", fake_invoke)

    with pytest.raises(AnkiConnectError, match="finished deck 'Default' for today"):
        AnkiService.get_card("Default")

    assert "All due Anki candidates" in caplog.text
    assert "All new Anki candidates" in caplog.text


def test_new_selection_uses_new_sort_order_from_deck_config(monkeypatch):
    cards = {
        1: _card(1, queue=0, card_type=0, due=1, ord_=1),
        2: _card(2, queue=0, card_type=0, due=99, ord_=0),
    }

    def fake_invoke(action, params=None):
        if action == "findCards":
            if "is:due" in params["query"]:
                return []
            if "is:new" in params["query"]:
                return [1, 2]
        if action == "cardsInfo":
            return [cards[card_id] for card_id in params["cards"]]
        if action == "getDeckConfig":
            return {"newSortOrder": 0, "newGatherPriority": 1}
        raise AssertionError(f"unexpected action: {action}")

    monkeypatch.setattr(AnkiService, "_invoke", fake_invoke)

    card = AnkiService.get_card("Default")

    assert card.card_id == 2


def test_next_review_summary_formats_intraday_learning_minutes(monkeypatch):
    now = datetime(2026, 5, 9, 10, 0, 0)
    due_at = datetime(2026, 5, 9, 10, 10, 0)

    monkeypatch.setattr(
        AnkiService,
        "_invoke",
        lambda action, params=None: [{
            "cardId": 123,
            "queue": 1,
            "due": int(due_at.timestamp()),
            "interval": 0,
        }]
    )

    summary = AnkiService.get_next_review_summary(123, now=now)

    assert summary.label == "in 10 min"
    assert summary.due_at == due_at
    assert summary.due_date == due_at.date()
    assert summary.is_intraday


def test_next_review_summary_formats_intraday_learning_tomorrow(monkeypatch):
    now = datetime(2026, 5, 9, 23, 55, 0)
    due_at = datetime(2026, 5, 10, 0, 5, 0)

    monkeypatch.setattr(
        AnkiService,
        "_invoke",
        lambda action, params=None: [{
            "cardId": 123,
            "queue": 1,
            "due": int(due_at.timestamp()),
            "interval": 0,
        }]
    )

    summary = AnkiService.get_next_review_summary(123, now=now)

    assert summary.label == "tomorrow at 00:05"
    assert summary.due_at == due_at
    assert summary.is_intraday


def test_next_review_summary_formats_review_interval(monkeypatch):
    now = datetime(2026, 5, 9, 10, 0, 0)

    monkeypatch.setattr(
        AnkiService,
        "_invoke",
        lambda action, params=None: [{
            "cardId": 123,
            "queue": 2,
            "due": 654,
            "interval": 4,
        }]
    )

    summary = AnkiService.get_next_review_summary(123, now=now)

    assert summary.label == "May 13"
    assert summary.due_date.isoformat() == "2026-05-13"
    assert not summary.is_intraday


def test_next_review_summary_formats_tomorrow_review(monkeypatch):
    now = datetime(2026, 5, 9, 10, 0, 0)

    monkeypatch.setattr(
        AnkiService,
        "_invoke",
        lambda action, params=None: [{
            "cardId": 123,
            "queue": 2,
            "due": 651,
            "interval": 1,
        }]
    )

    summary = AnkiService.get_next_review_summary(123, now=now)

    assert summary.label == "tomorrow"
    assert summary.due_date.isoformat() == "2026-05-10"


def test_next_review_summary_logs_exceptions(monkeypatch, caplog):
    def fake_invoke(action, params=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(AnkiService, "_invoke", fake_invoke)
    caplog.set_level(logging.ERROR)

    assert AnkiService.get_next_review_summary(123) is None
    assert "Could not determine next Anki review for card 123" in caplog.text
