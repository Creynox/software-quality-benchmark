"""Independent reference arithmetic, with no BLE service or database imports.

Calculates values only. Conformity, units, provenance and release remain separate
reviewed contracts; these functions cannot establish a normative PASS.
"""
from decimal import Decimal, InvalidOperation


def number(value):
    if value is None or isinstance(value, bool):
        raise ValueError('Missing/invalid measurement')
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('Invalid measurement') from None
    if not result.is_finite() or result < 0:
        raise ValueError('Measurement must be finite and nonnegative')
    return result


def percent(part, total):
    part, total = number(part), number(total)
    if total <= 0 or part > total:
        raise ValueError('Invalid part/total mass or height')
    return part / total * Decimal(100)


def sand_equivalent(repetitions):
    """Mean of the two individual ratios, not the ratio of mean heights."""
    if len(repetitions) != 2:
        raise ValueError('Reference requires two actual repetitions')
    return sum((percent(r['sand_height'], r['suspension_height']) for r in repetitions),
               Decimal(0)) / Decimal(2)


def pooled_particle_shape(fractions):
    """For one measured combined fraction; not STS sieve-weighted mixture index."""
    if not fractions:
        raise ValueError('Missing actual fractions')
    total, poor = Decimal(0), Decimal(0)
    for row in fractions:
        percent(row['poor_g'], row['total_g'])
        total += number(row['total_g'])
        poor += number(row['poor_g'])
    return percent(poor, total)
