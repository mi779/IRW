from dataclasses import dataclass


@dataclass
class SM2Result:
    ease_factor: float
    interval_days: int
    repetitions: int
    due_offset_days: int


def sm2_update(
    quality: int,
    prev_ease: float = 2.5,
    prev_interval: int = 0,
    prev_repetitions: int = 0,
) -> SM2Result:
    """SuperMemo SM-2 algorithm.

    Args:
        quality: response quality in range 0-5 (>=3 means correct).
        prev_ease: previous ease factor.
        prev_interval: previous interval in days.
        prev_repetitions: previous number of successful repetitions.

    Returns:
        SM2Result with updated ease_factor, interval_days, repetitions and
        due_offset_days (the interval used to compute the next due date).
    """
    quality = max(0, min(5, quality))

    if quality >= 3:
        # Correct response.
        repetitions = prev_repetitions + 1
        if prev_repetitions == 0:
            interval = 1
        elif prev_repetitions == 1:
            interval = 6
        else:
            interval = round(prev_interval * prev_ease)
    else:
        # Incorrect response: reset.
        repetitions = 0
        interval = 1

    # Update ease factor (only meaningful when quality >= 3, but the formula
    # is applied per the canonical SM-2 description).
    delta = (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ease = max(1.3, prev_ease + delta)

    return SM2Result(
        ease_factor=round(ease, 4),
        interval_days=interval,
        repetitions=repetitions,
        due_offset_days=interval,
    )
