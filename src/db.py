from peewee import *

db = SqliteDatabase('habits.db')

class BaseModel(Model):
    class Meta:
        database = db

def initialize_database():
    from habit.habit import Habit
    from habit.log import Log
    from habit.habit_tracker import HabitTracker
    
    db.connect()
    db.create_tables([Habit, Log, HabitTracker])


if __name__ == '__main__':
    initialize_database()