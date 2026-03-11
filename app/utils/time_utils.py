

from datetime import date, datetime, time
from typing import Optional

import pytz

from app.config import settings

# ── Timezone ─────────────────────────────────────────────────────────────────
GOMA_TZ = pytz.timezone(settings.TIMEZONE)  # driven by settings.TIMEZONE


def now_goma() -> datetime:
    """Return the current datetime in Goma, DRC timezone."""
    return datetime.now(GOMA_TZ)


def today_goma() -> date:
    """Return today's date in Goma, DRC timezone."""
    return now_goma().date()


def to_goma(dt: datetime) -> datetime:
    """Convert any aware datetime to Goma timezone."""
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(GOMA_TZ)


def parse_hikvision_time(time_str: str) -> Optional[datetime]:
    """
    Parse a Hikvision ISO-8601 timestamp and return a Goma-aware datetime.

    ── Quirk terminaux Hikvision ──────────────────────────────────────────
    La majorité des terminaux Hikvision envoient l'heure murale locale
    (celle visible sur l'écran, correctement réglée sur l'heure de Goma)
    mais accompagnée de l'offset d'usine « +08:00 » (fuseau Pékin) sans
    jamais le corriger, même si le fuseau du terminal a été changé.

    Exemple : l'employé scanne à 10h30 heure de Goma.
      - Le terminal affiche  : 10:29:56
      - La trame ISO envoyée : 2026-03-09T10:29:56+08:00  ← offset FAUX
      - Heure réelle Goma    : 10:29:56+02:00             ← ce que l'on veut

    Stratégie (DEVICE_SENDS_LOCAL_TIME = True, défaut) :
      On extrait les 19 premiers caractères (YYYY-MM-DDTHH:MM:SS) et on
      localise ce datetime naïf dans le fuseau Goma — l'offset reçu est
      ignoré.  Ceci fonctionne quel que soit l'offset envoyé (+08:00, Z,
      +00:00, absent…).

    Stratégie alternative (DEVICE_SENDS_LOCAL_TIME = False) :
      L'offset est respecté et le résultat est converti en Goma.
      À activer uniquement si le terminal est configuré sur le bon fuseau.
    ── ────────────────────────────────────────────────────────────────────
    """
    if not time_str:
        return None
    try:
        if settings.DEVICE_SENDS_LOCAL_TIME:
            # Stratégie recommandée : ignorer l'offset, heure = heure murale Goma
            naive_dt = datetime.fromisoformat(time_str[:19])
            return GOMA_TZ.localize(naive_dt)
        else:
            # Stratégie fidèle à l'offset : utile si le terminal est bien configuré
            aware_str = time_str.replace("Z", "+00:00")
            if "+" in aware_str[10:] or aware_str.endswith("+00:00"):
                dt = datetime.fromisoformat(aware_str)
            else:
                # Pas d'offset du tout → on suppose heure locale Goma
                dt = GOMA_TZ.localize(datetime.fromisoformat(aware_str))
            return dt.astimezone(GOMA_TZ)
    except (ValueError, TypeError):
        return None


# ── Business-rule thresholds ─────────────────────────────────────────────────
# Arrival
_ON_TIME_CUTOFF: time = time(8, 0, 0)      # ≤ 08:00:00  → PRESENT
_LATE_CUTOFF: time = time(8, 20, 0)        # ≤ 08:19:59  → LATE  / ≥ 08:20 → REFUSED
_AUTO_ABSENT_AT: time = time(8, 21, 0)     # Scheduler fires at 08:21

# Departure
_VALID_DEPARTURE: time = time(16, 0, 0)    # < 16:00 ignored; ≥ 16:00 valid


def determine_arrival_status(arrival_time: time) -> str:
    """
    Map an arrival clock-time to an attendance status.

    ≤ 08:00  → "PRESENT"
    08:01–08:19 → "LATE"
    ≥ 08:20  → "REFUSED"
    """
    if arrival_time <= _ON_TIME_CUTOFF:
        return "PRESENT"
    if arrival_time < _LATE_CUTOFF:
        return "LATE"
    return "REFUSED"


def is_valid_departure(departure_time: time) -> bool:
    """Return True only if the departure clock-time is ≥ 16:00."""
    return departure_time >= _VALID_DEPARTURE
