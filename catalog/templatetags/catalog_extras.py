"""Custom template tags/filters for the catalog."""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def stars(value):
    """Render a 0–5 rating as a precise, accessible star bar.

    Two stacked rows of ★: a grey "empty" row and a gold "full" row clipped to
    the fractional width, so 4.5 shows exactly four-and-a-half gold stars.
    Returns an empty-state span when ``value`` is None/blank.
    """
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return mark_safe('<span class="stars stars--empty" aria-hidden="true">★★★★★</span>')

    pct = max(0.0, min(100.0, rating / 5.0 * 100.0))
    return mark_safe(
        f'<span class="stars" role="img" aria-label="Rated {rating:.1f} out of 5">'
        f'<span class="stars-bg">★★★★★</span>'
        f'<span class="stars-fg" style="width:{pct:.1f}%">★★★★★</span>'
        f"</span>"
    )
