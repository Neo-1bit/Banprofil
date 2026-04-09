from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdaptiveWindowStep:
    """
    Ett steg i adaptiv utökning av sökfönster.

    Parameters
    ----------
    buffer_m : float
        Aktiv buffert i meter.
    candidate_count : int
        Antal kandidater i fönstret.
    """

    buffer_m: float
    candidate_count: int


@dataclass(frozen=True, slots=True)
class AdaptiveWindowPlan:
    """
    Plan för adaptiv fönsterutökning.

    Parameters
    ----------
    initial_buffer_m : float
        Startbuffert.
    max_buffer_m : float
        Maxbuffert.
    growth_factor : float
        Multiplikativ tillväxt per steg.
    steps : list[AdaptiveWindowStep]
        Registrerade steg.
    """

    initial_buffer_m: float
    max_buffer_m: float
    growth_factor: float
    steps: list[AdaptiveWindowStep]


def build_adaptive_plan(
    candidate_counts: list[int],
    initial_buffer_m: float = 1500.0,
    max_buffer_m: float = 20000.0,
    growth_factor: float = 2.0,
) -> AdaptiveWindowPlan:
    """
    Bygger en enkel plan för adaptiv utökning av sökfönster.

    Parameters
    ----------
    candidate_counts : list[int]
        Antal kandidater som observerats per steg.
    initial_buffer_m : float, optional
        Startbuffert i meter.
    max_buffer_m : float, optional
        Maxbuffert i meter.
    growth_factor : float, optional
        Multiplikativ tillväxt per steg.

    Returns
    -------
    AdaptiveWindowPlan
        Plan för vidare sökning.
    """
    steps: list[AdaptiveWindowStep] = []
    buffer_m = initial_buffer_m
    for candidate_count in candidate_counts:
        steps.append(AdaptiveWindowStep(buffer_m=buffer_m, candidate_count=candidate_count))
        buffer_m = min(max_buffer_m, buffer_m * growth_factor)
    return AdaptiveWindowPlan(
        initial_buffer_m=initial_buffer_m,
        max_buffer_m=max_buffer_m,
        growth_factor=growth_factor,
        steps=steps,
    )
