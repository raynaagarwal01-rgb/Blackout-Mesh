import time

from blackout_mesh.baseline import BaselineTracker


def test_anomaly_score_is_zero_before_any_update():
    tracker = BaselineTracker()
    assert tracker.anomaly_score("N1", 3.3) == 0.0


def test_stable_readings_stay_low_anomaly():
    tracker = BaselineTracker()
    now = time.time()
    # Push past the warmup window so the baseline settles.
    for i in range(50):
        tracker.update("N1", 3.3, now + tracker.warmup_s + i * 0.1)

    score = tracker.anomaly_score("N1", 3.31)
    assert score < 0.2


def test_large_deviation_triggers_high_anomaly():
    tracker = BaselineTracker()
    now = time.time()
    for i in range(50):
        tracker.update("N1", 3.3, now + tracker.warmup_s + i * 0.1)

    score = tracker.anomaly_score("N1", 0.0)
    assert score > 0.5
