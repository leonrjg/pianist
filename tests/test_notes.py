from datetime import datetime

import pytest
from peewee import SqliteDatabase

from core.habit.habit import Habit
from core.notes.service import NoteService
from core.notes.note import Note


_test_db = SqliteDatabase(':memory:')


@pytest.fixture(autouse=True)
def bind_test_db():
    models = [Habit, Note]
    with _test_db.bind_ctx(models, bind_refs=False, bind_backrefs=False):
        _test_db.connect()
        _test_db.create_tables(models)
        yield
        _test_db.drop_tables(models)
        _test_db.close()


def create_habit(name='Piano'):
    return Habit.create(
        name=name,
        schedule='daily',
        created_at=datetime(2026, 5, 1),
        updated_at=datetime(2026, 5, 1),
        started_at=datetime(2026, 5, 1),
    )


def test_habit_can_have_multiple_named_notes():
    habit = create_habit()

    default_note = NoteService.get_habit_note(habit)
    second_note = NoteService.create_habit_note(habit, title='Lesson notes')

    notes = NoteService.list_habit_notes(habit)

    assert [note.id for note in notes] == [default_note.id, second_note.id]
    assert [note.title for note in notes] == ['Default note', 'Lesson notes']


def test_global_and_habit_notes_are_listed_separately():
    habit = create_habit()
    global_note = NoteService.get_global_note()
    habit_note = NoteService.create_habit_note(habit, title='Repertoire')

    assert [note.id for note in NoteService.list_global_notes()] == [global_note.id]
    assert [note.id for note in NoteService.list_habit_notes(habit)] == [habit_note.id]


def test_soft_deleted_notes_are_excluded_from_lists():
    habit = create_habit()
    kept = NoteService.create_habit_note(habit, title='Keep')
    deleted = NoteService.create_habit_note(habit, title='Remove')
    deleted.deleted_at = datetime(2026, 5, 2)
    deleted.save()

    assert [note.id for note in NoteService.list_habit_notes(habit)] == [kept.id]
