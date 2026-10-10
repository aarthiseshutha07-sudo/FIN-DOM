"""Model constants for the FIN-DOM engine.

Every number that shapes the simulation lives here, so there is exactly one
place to look (and one place to change) when someone asks "where does that
value come from?". The values and their meaning are defined in
docs/ENGINE_RULES.md. These are MODELLING CHOICES, not estimates from real
financial data.
"""

# --- Cascade rules -----------------------------------------------------------

# Share of an exposure that is lost when the debtor is at full stress (1.0).
LOSS_RATE = 0.6

# Converts shock severity (0-1) into the source entity's starting stress:
#   source stress = min(1, severity * SHOCK_SCALE)
SHOCK_SCALE = 1.5

# Safety cap on the number of propagation rounds.
MAX_ROUNDS = 10

# The cascade stops when no entity's stress changed by more than this amount.
CONVERGENCE_TOL = 1e-6

# --- Status thresholds (applied to final stress) -----------------------------

# stress <  STABLE_MAX                 -> "Stable"
# STABLE_MAX <= stress < FAILED_MIN    -> "Stressed"
# stress >= FAILED_MIN (i.e. == 1.0)   -> "Failed"
STABLE_MAX = 0.25
FAILED_MIN = 1.0

STATUS_STABLE = "Stable"
STATUS_STRESSED = "Stressed"
STATUS_FAILED = "Failed"

# --- Baseline risk score weights (must add up to 1.0) ------------------------

SCORE_WEIGHTS = {
    "leverage": 0.4,               # total assets / capital buffer
    "exposure_to_capital": 0.4,    # outgoing exposure / capital buffer
    "interconnectedness": 0.2,     # number of links, incoming + outgoing
}

# --- Allowed category values (used by the CSV validator) ---------------------

ENTITY_TYPES = ["Bank", "Insurer", "Fund", "Corporate", "Sovereign"]

REGIONS = ["Americas", "Europe", "Asia-Pacific"]

EXPOSURE_TYPES = [
    "Interbank loan",
    "Bond holding",
    "Derivative",
    "Equity stake",
    "Insurance claim",
    "Credit line",
]
