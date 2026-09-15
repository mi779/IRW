from services.sm2 import sm2_update


def test_first_review_quality_4():
    result = sm2_update(quality=4, prev_ease=2.5, prev_interval=0, prev_repetitions=0)
    assert result.interval_days == 1
    assert result.repetitions == 1
    assert result.due_offset_days == 1
    # EF for quality=4: 2.5 + (0.1 - 1*(0.08 + 1*0.02)) = 2.5 + (0.1 - 0.1) = 2.5
    assert result.ease_factor == 2.5


def test_second_review_quality_4():
    result = sm2_update(quality=4, prev_ease=2.5, prev_interval=1, prev_repetitions=1)
    assert result.interval_days == 6
    assert result.repetitions == 2
    assert result.due_offset_days == 6


def test_third_review_quality_4():
    result = sm2_update(quality=4, prev_ease=2.5, prev_interval=6, prev_repetitions=2)
    assert result.interval_days == 15  # round(6 * 2.5) = 15
    assert result.repetitions == 3
    assert result.due_offset_days == 15


def test_wrong_answer_resets():
    result = sm2_update(quality=2, prev_ease=2.5, prev_interval=15, prev_repetitions=3)
    assert result.repetitions == 0
    assert result.interval_days == 1
    assert result.due_offset_days == 1
    # EF for quality=2: max(1.3, 2.5 + (0.1 - 3*(0.08 + 3*0.02)))
    # = max(1.3, 2.5 + (0.1 - 3*0.14)) = max(1.3, 2.5 - 0.32) = max(1.3, 2.18) = 2.18
    assert result.ease_factor == 2.18
