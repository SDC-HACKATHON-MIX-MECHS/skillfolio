"""Every tunable number in one place (SPEC 5).

The Methodology page shows these values as assumptions, so keep the comments
plain English.
"""

# Scenarios, applied to the yearly growth in log space:
#   delta = lambda * (skill exposure - average exposure);  projected growth = e^(damped log growth - delta) - 1
# A skill 0.1 more exposed than average has its yearly growth factor (1 + r) multiplied by about 0.95 (moderate) or 0.86 (fast).
# These weights are assumptions, not estimates from data: today's job posts show no link between exposure and growth.
SCENARIOS = {
    "moderate": {"label": "Moderate AI disruption", "lambda": 0.5},
    "fast": {"label": "Fast AI disruption", "lambda": 1.5},
}
DEFAULT_SCENARIO = "moderate"

# Forecast windows
EPSILON_POSTS = 0.5             # "half a post": added to every share before taking logs (relative to the average thread size)
SMOOTHING_MONTHS = 3            # rolling mean before fitting trends
MOMENTUM_WINDOW_MONTHS = 12     # momentum = trend over the last 12 months
VOLATILITY_WINDOW_MONTHS = 24   # volatility = swing over the last 24 months
INTERVAL_Z = 1.28               # 80% interval around momentum
SE_INFLATION = 1.9              # trend uncertainty is multiplied by this: the trend is fitted to a 3-month rolling average, so neighbouring points move together and the plain standard error is ~1.9x too small (simulation, Poisson counts: nominal 80% band covered ~50%)
TREND_THRESHOLD = 0.05          # +/-5% a year separates rising / stable / declining
THIN_DATA_MIN_MEAN_COUNT = 3    # fewer posts than this per month on average -> "thin data"
MIN_HISTORY_MONTHS = 3          # fewer months than this -> no trend is estimated; label stays "stable"

# Damping noisy trends (shrinkage toward the all-skill average, SPEC 5.1)
SHRINK_MIN_SKILLS = 5           # need at least this many well-observed skills to estimate the average and spread; else no damping
SE_FLOOR = 0.05                 # when estimating the spread, trend uncertainties below this (annual log units) count as this
TAU_FLOOR = 0.10                # skills are assumed to differ in true yearly log growth by at least this much (so we never flatten everything)

# Portfolio
COVARIANCE_SHRINKAGE = 0.5      # pull the covariance halfway toward its diagonal for stability
RISK_AVERSION = {"low": 0.75, "medium": 0.375, "high": 0.125}  # gamma in readiness = growth - gamma/2 * vol^2 (SPEC 6/3/1 scaled by 1/8, calibrated on the 2026-10-20 snapshot)
THIN_GROWTH_CAP = 0.05          # a thin-data skill counts for at most +/-5% a year in portfolio growth (the "stable" band)

# Matching and planning
SDG_TILT_ALPHA = 0.15           # how much a shared SDG lifts a role's rank
PATHWAY_MATCH_BETA = 1.0        # weight of match gain vs readiness gain when choosing courses
BUDGET_TOLERANCE = 1e-9         # a course that fits the hours (or RM) budget up to this much counts as fitting: 0.9h + 0.8h fits 1.7h although the float sum is 1.7000000000000002
MIN_COURSE_HOURS = 0.01         # a course must take at least this long (36 seconds), so "gain per hour" cannot overflow to infinity
TOP_N_ROLES = 5

# SDG lens
BASELINE_SKILL_SDG = 4          # every skill supports SDG 4 (target 4.4: relevant skills for decent jobs)
ROLE_SDG_MIN_WEIGHT = 2         # a skill inherits a role's SDGs when the role weights it at least this much
