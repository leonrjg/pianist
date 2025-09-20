
-- Drop existing tables if they exist
DROP TABLE IF EXISTS habittracker;
DROP TABLE IF EXISTS log;
DROP TABLE IF EXISTS habit;

-- Create tables matching the Peewee models

-- Habit table - Core entities with scheduling information
CREATE TABLE habit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    schedule VARCHAR(50) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    started_at DATETIME NOT NULL,
    inactivity_threshold INTEGER DEFAULT 120,
    allocated_time INTEGER  -- In seconds, nullable
);

-- Log table - Session records with timing data
CREATE TABLE log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id INTEGER NOT NULL,
    start DATETIME NOT NULL,
    end DATETIME,  -- Nullable for ongoing sessions
    started_by VARCHAR(50),
    ended_by VARCHAR(50),
    idle_time INTEGER DEFAULT 0,  -- In seconds
    FOREIGN KEY (habit_id) REFERENCES habit(id)
);

-- HabitTracker table - Junction table for habit-tracker associations
CREATE TABLE habittracker (
    habit_id INTEGER NOT NULL,
    tracker VARCHAR(50) NOT NULL,
    config TEXT,  -- JSON configuration
    is_enabled BOOLEAN DEFAULT 1,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (habit_id, tracker),
    FOREIGN KEY (habit_id) REFERENCES habit(id)
);

-- Insert test habits with varied schedules and configurations
INSERT INTO habit (id, name, schedule, created_at, updated_at, started_at, inactivity_threshold, allocated_time) VALUES
-- Daily habits
(1, 'piano', 'daily', '2024-08-15 08:00:00', '2024-08-15 08:00:00', '2024-08-15 08:00:00', 15, 0),
(2, 'emails', 'daily', '2024-08-16 06:00:00', '2024-08-16 06:00:00', '2024-08-16 06:00:00', 10, 0),

-- Weekly habits
(3, 'focus', 'weekly', '2024-08-17 09:00:00', '2024-08-17 09:00:00', '2024-08-17 09:00:00', 10, 0),
(4, 'language_study', 'weekly', '2024-08-18 14:00:00', '2024-08-18 14:00:00', '2024-08-18 14:00:00', 20, 0),

-- Monthly habit
(5, 'budgeting', 'monthly', '2024-08-01 19:00:00', '2024-08-01 19:00:00', '2024-08-01 19:00:00', 15, 0),

-- Hourly habit for intensive testing
(6, 'posture_check', 'hourly', '2024-09-13 09:00:00', '2024-09-13 09:00:00', '2024-09-13 09:00:00', 10, 5), -- 5 min allocated

-- Exponential habit
(7, 'chess', 'exponential_3', '2024-08-20 10:00:00', '2024-08-20 10:00:00', '2024-08-20 10:00:00', 10, 0);

-- Insert habit trackers
INSERT INTO habittracker (habit_id, tracker, config, is_enabled, created_at) VALUES

-- Email writing with IO tracking only
(5, 'io', '{}', 1, '2024-08-16 06:00:00'),

-- Chess with window and IO tracking
(7, 'window', '{"keywords": ["Chess.com"]}', 1, '2024-08-20 10:00:00');
(7, 'io', '{}', 1, '2024-08-17 09:00:00'),

-- Generate 4 weeks of realistic log data (from 2024-08-15 to 2024-09-14)
-- This creates varied patterns to test streaks, gaps, and analytics

-- Piano Practice (daily) - Strong streak with some gaps
INSERT INTO log (habit_id, start, end, started_by, ended_by, idle_time) VALUES
-- Week 1 (Aug 15-21) - Perfect week
(1, '2024-08-15 07:30:00', '2024-08-15 08:15:00', 'user', NULL, 300), -- 45min with 5min idle
(1, '2024-08-16 07:45:00', '2024-08-16 08:20:00', 'user', 'WindowTracker', 180), -- 35min with 3min idle
(1, '2024-08-17 08:00:00', '2024-08-17 08:35:00', 'user', NULL, 0), -- 35min no idle
(1, '2024-08-18 07:30:00', '2024-08-18 08:10:00', 'user', NULL, 120), -- 40min with 2min idle
(1, '2024-08-19 08:15:00', '2024-08-19 08:45:00', 'user', NULL, 0), -- 30min no idle
(1, '2024-08-20 07:45:00', '2024-08-20 08:25:00', 'user', 'IOTracker', 240), -- 40min with 4min idle
(1, '2024-08-21 08:00:00', '2024-08-21 08:30:00', 'user', NULL, 60), -- 30min with 1min idle

-- Week 2 (Aug 22-28) - Missed 2 days
(1, '2024-08-22 07:30:00', '2024-08-22 08:00:00', 'user', 'user', 0), -- 30min
-- Skip Aug 23-24
(1, '2024-08-25 08:30:00', '2024-08-25 09:15:00', 'user', 'user', 420), -- 45min with 7min idle (makeup session)
(1, '2024-08-26 07:45:00', '2024-08-26 08:20:00', 'user', 'user', 180), -- 35min
(1, '2024-08-27 08:00:00', '2024-08-27 08:35:00', 'user', 'inactivity', 120), -- 35min
(1, '2024-08-28 07:30:00', '2024-08-28 08:15:00', 'user', 'user', 300), -- 45min

-- Week 3 (Aug 29 - Sep 4) - Good consistency
(1, '2024-08-29 08:00:00', '2024-08-29 08:25:00', 'user', 'user', 0), -- 25min
(1, '2024-08-30 07:45:00', '2024-08-30 08:30:00', 'user', 'user', 360), -- 45min with 6min idle
(1, '2024-08-31 08:15:00', '2024-08-31 08:45:00', 'user', 'user', 120), -- 30min
(1, '2024-09-01 07:30:00', '2024-09-01 08:20:00', 'user', 'inactivity', 240), -- 50min with 4min idle
(1, '2024-09-02 08:00:00', '2024-09-02 08:40:00', 'user', 'user', 180), -- 40min
(1, '2024-09-03 07:45:00', '2024-09-03 08:25:00', 'user', 'user', 60), -- 40min
(1, '2024-09-04 08:30:00', '2024-09-04 09:00:00', 'user', 'user', 0), -- 30min

-- Week 4 (Sep 5-11) - Recent streak
(1, '2024-09-05 07:30:00', '2024-09-05 08:15:00', 'user', 'user', 300), -- 45min
(1, '2024-09-06 08:00:00', '2024-09-06 08:35:00', 'user', 'user', 180), -- 35min
(1, '2024-09-07 07:45:00', '2024-09-07 08:20:00', 'user', 'inactivity', 120), -- 35min
(1, '2024-09-08 08:15:00', '2024-09-08 08:50:00', 'user', 'user', 240), -- 35min
(1, '2024-09-09 07:30:00', '2024-09-09 08:10:00', 'user', 'user', 60), -- 40min
(1, '2024-09-10 08:00:00', '2024-09-10 08:45:00', 'user', 'user', 360), -- 45min
(1, '2024-09-11 07:45:00', '2024-09-11 08:25:00', 'user', 'user', 180), -- 40min

-- Current week partial (Sep 12-14)
(1, '2024-09-12 08:00:00', '2024-09-12 08:30:00', 'user', 'user', 0), -- 30min
(1, '2024-09-13 07:30:00', '2024-09-13 08:15:00', 'user', 'user', 240); -- 45min

-- Morning Meditation (daily) - More sporadic pattern
INSERT INTO log (habit_id, start, end, started_by, ended_by, idle_time) VALUES
-- Week 1 - Good start
(2, '2024-08-16 06:00:00', '2024-08-16 06:15:00', 'user', 'user', 0), -- 15min
(2, '2024-08-17 06:15:00', '2024-08-17 06:35:00', 'user', 'user', 60), -- 20min
-- Skip Aug 18
(2, '2024-08-19 06:30:00', '2024-08-19 06:45:00', 'user', 'user', 0), -- 15min
(2, '2024-08-20 06:00:00', '2024-08-20 06:20:00', 'user', 'inactivity', 120), -- 20min
(2, '2024-08-21 06:15:00', '2024-08-21 06:25:00', 'user', 'user', 0), -- 10min

-- Week 2 - Inconsistent
(2, '2024-08-22 06:30:00', '2024-08-22 06:50:00', 'user', 'user', 180), -- 20min
-- Skip Aug 23-25
(2, '2024-08-26 06:00:00', '2024-08-26 06:12:00', 'user', 'user', 0), -- 12min
(2, '2024-08-27 06:45:00', '2024-08-27 07:00:00', 'user', 'user', 60), -- 15min

-- Week 3 - Better consistency
(2, '2024-08-29 06:15:00', '2024-08-29 06:35:00', 'user', 'user', 120), -- 20min
(2, '2024-08-30 06:00:00', '2024-08-30 06:18:00', 'user', 'user', 0), -- 18min
(2, '2024-08-31 06:30:00', '2024-08-31 06:42:00', 'user', 'inactivity', 60), -- 12min
(2, '2024-09-01 06:15:00', '2024-09-01 06:30:00', 'user', 'user', 0), -- 15min
(2, '2024-09-02 06:00:00', '2024-09-02 06:25:00', 'user', 'user', 180), -- 25min

-- Week 4 - Current streak
(2, '2024-09-05 06:30:00', '2024-09-05 06:45:00', 'user', 'user', 0), -- 15min
(2, '2024-09-06 06:00:00', '2024-09-06 06:20:00', 'user', 'user', 120), -- 20min
(2, '2024-09-07 06:15:00', '2024-09-07 06:28:00', 'user', 'user', 0), -- 13min
(2, '2024-09-08 06:30:00', '2024-09-08 06:50:00', 'user', 'user', 240), -- 20min
(2, '2024-09-09 06:00:00', '2024-09-09 06:16:00', 'user', 'user', 60), -- 16min
(2, '2024-09-10 06:15:00', '2024-09-10 06:35:00', 'user', 'user', 120), -- 20min
(2, '2024-09-11 06:30:00', '2024-09-11 06:42:00', 'user', 'user', 0), -- 12min
(2, '2024-09-12 06:00:00', '2024-09-12 06:18:00', 'user', 'user', 60); -- 18min

-- Deep Work Session (weekly) - Saturday sessions
INSERT INTO log (habit_id, start, end, started_by, ended_by, idle_time) VALUES
-- Week 1
(3, '2024-08-17 09:00:00', '2024-08-17 11:45:00', 'user', 'user', 900), -- 2h 45m with 15min idle
-- Week 2
(3, '2024-08-24 10:30:00', '2024-08-24 12:15:00', 'user', 'inactivity', 300), -- 1h 45m with 5min idle
-- Skip Week 3 (Aug 31)
-- Week 4
(3, '2024-09-07 09:15:00', '2024-09-07 12:30:00', 'user', 'user', 1200), -- 3h 15m with 20min idle
-- Current week
(3, '2024-09-14 08:45:00', '2024-09-14 11:00:00', 'user', 'user', 600); -- 2h 15m with 10min idle

-- Language Study (weekly) - Sunday sessions
INSERT INTO log (habit_id, start, end, started_by, ended_by, idle_time) VALUES
-- Week 1
(4, '2024-08-18 14:00:00', '2024-08-18 15:30:00', 'user', 'user', 300), -- 1h 30m with 5min idle
-- Week 2
(4, '2024-08-25 15:00:00', '2024-08-25 16:15:00', 'user', 'user', 180), -- 1h 15m with 3min idle
-- Week 3
(4, '2024-09-01 14:30:00', '2024-09-01 15:45:00', 'user', 'inactivity', 240), -- 1h 15m with 4min idle
-- Week 4
(4, '2024-09-08 13:45:00', '2024-09-08 15:20:00', 'user', 'user', 420); -- 1h 35m with 7min idle

-- Financial Review (monthly) - First Saturday of month
INSERT INTO log (habit_id, start, end, started_by, ended_by, idle_time) VALUES
-- August session
(5, '2024-08-03 19:00:00', '2024-08-03 21:15:00', 'user', 'user', 600), -- 2h 15m with 10min idle
-- September session
(5, '2024-09-07 18:30:00', '2024-09-07 20:45:00', 'user', 'user', 480); -- 2h 15m with 8min idle

-- Posture Check (hourly) - Recent addition with limited data
INSERT INTO log (habit_id, start, end, started_by, ended_by, idle_time) VALUES
-- Just yesterday and today for testing hourly schedule
(6, '2024-09-13 09:00:00', '2024-09-13 09:05:00', 'user', 'user', 0), -- 5min
(6, '2024-09-13 10:15:00', '2024-09-13 10:18:00', 'user', 'user', 0), -- 3min
(6, '2024-09-13 11:30:00', '2024-09-13 11:37:00', 'user', 'inactivity', 60), -- 7min with 1min idle
(6, '2024-09-13 14:45:00', '2024-09-13 14:50:00', 'user', 'user', 0), -- 5min
(6, '2024-09-13 16:00:00', '2024-09-13 16:04:00', 'user', 'user', 0), -- 4min
-- Today
(6, '2024-09-14 09:30:00', '2024-09-14 09:35:00', 'user', 'user', 0), -- 5min
(6, '2024-09-14 11:15:00', '2024-09-14 11:22:00', 'user', 'user', 30); -- 7min with 30s idle

-- Skill Challenge (exponential_3) - Growing intervals
INSERT INTO log (habit_id, start, end, started_by, ended_by, idle_time) VALUES
-- Day 1
(7, '2024-08-20 10:00:00', '2024-08-20 10:50:00', 'user', 'user', 240), -- 50min with 4min idle
-- Day 4 (3 days later)
(7, '2024-08-23 15:30:00', '2024-08-23 16:25:00', 'user', 'user', 180), -- 55min with 3min idle
-- Day 13 (9 days later)
(7, '2024-09-01 11:00:00', '2024-09-01 12:10:00', 'user', 'inactivity', 360); -- 1h 10m with 6min idle

-- Create indexes for better query performance
CREATE INDEX idx_log_habit_start ON log(habit_id, start);
CREATE INDEX idx_log_habit_end ON log(habit_id, end);
CREATE INDEX idx_habit_schedule ON habit(schedule);
