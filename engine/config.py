"""Every tunable number in one place (SPEC 5).

The Methodology page shows these values as assumptions, so keep the comments
plain English.
"""

# Scenarios: projected return = momentum - lambda * (skill exposure - average exposure)
SCENARIOS = {
    "moderate": {"label": "Moderate AI disruption", "lambda": 0.10},
    "fast": {"label": "Fast AI disruption", "lambda": 0.30},
}
DEFAULT_SCENARIO = "moderate"

# Forecast windows
EPSILON_POSTS = 0.5             # "half a post": added to every share before taking logs (relative to the average thread size)
SMOOTHING_MONTHS = 3            # rolling mean before fitting trends
MOMENTUM_WINDOW_MONTHS = 12     # momentum = trend over the last 12 months
VOLATILITY_WINDOW_MONTHS = 24   # volatility = swing over the last 24 months
INTERVAL_Z = 1.28               # 80% interval around momentum
TREND_THRESHOLD = 0.05          # +/-5% a year separates rising / stable / declining
THIN_DATA_MIN_MEAN_COUNT = 3    # fewer posts than this per month on average -> "thin data"
MIN_HISTORY_MONTHS = 3          # fewer months than this -> no trend is estimated; label stays "stable"

# Portfolio
COVARIANCE_SHRINKAGE = 0.5      # pull the covariance halfway toward its diagonal for stability
RISK_AVERSION = {"low": 6.0, "medium": 3.0, "high": 1.0}  # gamma in readiness = growth - gamma/2 * vol^2

# Matching and planning
SDG_TILT_ALPHA = 0.15           # how much a shared SDG lifts a role's rank
PATHWAY_MATCH_BETA = 1.0        # weight of match gain vs readiness gain when choosing courses
TOP_N_ROLES = 5

# SDG lens
BASELINE_SKILL_SDG = 4          # every skill supports SDG 4 (target 4.4: relevant skills for decent jobs)
ROLE_SDG_MIN_WEIGHT = 2         # a skill inherits a role's SDGs when the role weights it at least this much
