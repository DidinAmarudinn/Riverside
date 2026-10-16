"""Parameters of the forecast and reorder method. Chosen from the method, never tuned to a target number."""
from __future__ import annotations

HORIZON_DAYS = 14                 # ARIMA_PLUS horizon (build plan 7.3)
BACKTEST_TRAIN_DAYS = 76          # train up to day 76, predict the next 14 days (7.8)
LATE_TRAIN_DAYS = 83              # stress test: cutoff while stockouts are still going on ...
LATE_HORIZON_DAYS = 7             # ... scored over the 7 days of true demand that remain

# --- ask rate estimate (7.2): estimated from the training data only, never read from the generator's config ---
ASK_WINDOW_DAYS = 28              # in-stock days within +-28 days, same weekday, give the expected demand
ASK_MIN_EXPECTED_UNITS = 30.0     # a category needs this many expected unmet units, else the pooled estimate is used
ASK_MIN_SIGNALS = 6
ASK_FLOOR, ASK_CEIL = 0.05, 1.0   # keeps 1/ask_rate finite and sensible

# --- reorder formula (7.5): max(0, forecast(lead + review) + safety - on_hand - on_order) ---
LEAD_TIME_DAYS = 1                # same as the supplier lead time in the simulator's stock policy
REVIEW_PERIOD_DAYS = 6            # order covers one week: lead 1 + review 6 = 7 days (matches forecast_*_7d)
COVER_DAYS = LEAD_TIME_DAYS + REVIEW_PERIOD_DAYS
SERVICE_Z = 1.645                 # 95% cycle service level
INTERVAL_CONFIDENCE = 0.90        # prediction interval asked from ML.FORECAST ...
INTERVAL_Z = 1.645                # ... whose half-width / INTERVAL_Z gives the daily standard deviation
ON_ORDER = 0                      # open purchase orders are not tracked in the data

# --- risk flags (7.6) ---
OVERSTOCK_DAYS = 14               # on_hand above this many days of forecast ...
OVERSTOCK_DAYS_PERISHABLE = 5     # ... or this many for perishables (shelf life <= PERISHABLE_SHELF_DAYS)
PERISHABLE_SHELF_DAYS = 30
OVERSTOCK_MIN_UNITS = 10          # ignore tiny stocks of slow movers
SPIKE_MIN_SIGNALS = 5             # unmet_spike: this many unmet signals in 7 days ...
SPIKE_RATIO = 2.0                 # ... and at least this times the 7 days before

# --- sensitivity (7.8): B re-run with the estimated ask rate shifted by these factors ---
SENSITIVITY_FACTORS = {"b_rate_x0_5": 0.5, "b_rate_x1_5": 1.5}
