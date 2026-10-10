# FIN-DOM Engine Rules

Source of truth for the simulation engine (`engine/`). Code and tests must follow this document. All constants live in `engine/params.py`.

**Honest scope.** This is a transparent, rule-based contagion simulator on synthetic, fictional data. It contains no trained GNN, no causal inference and no real-time data. The loss rate, shock scale and weights are modelling choices, not estimates from real financial data.

## 1. Data

Money is in billions (bn) of a fictional currency.

**`data/entities.csv`** columns: `entity_id`, `name`, `type`, `region`, `total_assets_bn`, `capital_buffer_bn`

**`data/exposures.csv`** columns: `exposure_id`, `creditor_id`, `debtor_id`, `exposure_bn`, `exposure_type`

A row `X001,E02,E01,28,Bond holding` means: creditor E02 is exposed to debtor E01 for 28bn. If E01 gets into trouble, E02 loses part of that 28bn. Losses flow from debtor to creditor.

Leverage is **calculated, never stored**: `leverage = total_assets_bn / capital_buffer_bn`.

### Validation rules (implemented in `engine/data_loader.py`)

| # | Entities rule |
|---|---|
| E1 | All required columns present |
| E2 | No missing values |
| E3 | `entity_id` unique |
| E4 | `name` unique (case-insensitive, whitespace trimmed) |
| E5 | `type` in: Bank, Insurer, Fund, Corporate, Sovereign |
| E6 | `region` in: Americas, Europe, Asia-Pacific |
| E7 | Assets and buffer are numeric |
| E8 | `total_assets_bn` > 0 |
| E9 | `capital_buffer_bn` > 0 and < `total_assets_bn` |

| # | Exposures rule |
|---|---|
| X1 | All required columns present |
| X2 | No missing values |
| X3 | `exposure_id` unique |
| X4 | `creditor_id` and `debtor_id` exist in entities |
| X5 | Creditor and debtor differ (no self-links) |
| X6 | Each (creditor, debtor) pair appears at most once |
| X7 | `exposure_bn` numeric and > 0 |
| X8 | `exposure_bn` < the creditor's `total_assets_bn` |
| X9 | `exposure_type` in: Interbank loan, Bond holding, Derivative, Equity stake, Insurance claim, Credit line |

The loader reports every problem at once, with the CSV line number (header = line 1), and returns both tables sorted by id so that CSV row order can never change a result.

## 2. Parameters

| Name | Value | Meaning |
|---|---|---|
| `LOSS_RATE` | 0.6 | Share of an exposure lost at full debtor stress |
| `SHOCK_SCALE` | 1.5 | Converts severity into the source's starting stress |
| `STABLE_MAX` | 0.25 | Below this, status is Stable |
| `FAILED_MIN` | 1.0 | At or above this, status is Failed |
| `MAX_ROUNDS` | 10 | Safety cap on the cascade |
| `CONVERGENCE_TOL` | 1e-6 | Stop when no stress changes by more than this |
| `SCORE_WEIGHTS` | 0.4 / 0.4 / 0.2 | Leverage / exposure-to-capital / interconnectedness |

## 3. Cascade calculation

Symbols: `B_i` = capital buffer of entity *i*; `E_ij` = exposure of creditor *i* to debtor *j*; `s_i(t)` = stress of entity *i* at the end of round *t*, always between 0 and 1.

**Round 0 (the shock).** Only the source entity is hit.

- `s_source(0) = min(1, severity * SHOCK_SCALE)`
- `L0 = s_source(0) * B_source`
- Every other entity starts at stress 0.
- With `SHOCK_SCALE = 1.5`, the source fails when severity >= 0.667.

**Round t >= 1 (propagation).** Every entity is updated **simultaneously**, using only the previous round's stress values. Results therefore do not depend on row order.

1. For each creditor *i*: `total_loss_i(t) = L0_i + sum over debtors j of [ LOSS_RATE * E_ij * s_j(t-1) ]`. (`L0_i` is non-zero only for the source.)
2. `s_i(t) = min(1, total_loss_i(t) / B_i)`
3. Stop when no stress changed by more than `CONVERGENCE_TOL`, or when `MAX_ROUNDS` is reached (the app shows a note if the cap was hit).

Stress never decreases and is capped at 1, so the cascade always settles, including with cycles of mutual exposure.

## 4. Preventing duplicate losses and reconciling the ledger

Each round **recomputes** an entity's total loss from its debtors' current stress. It never adds a new loss on top of the previous round's loss, so a loss on a link is counted once.

The **loss ledger** records only the *new* part of each loss:

`ledger loss on link (i, j) in round t = LOSS_RATE * E_ij * ( s_j(t-1) - s_j(t-2) )`, with `s(-1) = 0`.

If the debtor's stress did not change, the loss is 0 and no row is written. Ledger rows for one creditor therefore sum to its total loss.

- **Round 0 row:** one row records the shock (creditor = source, debtor = `SHOCK`, loss = `L0`).
- **Ledger columns:** `round`, `creditor_id`, `debtor_id`, `exposure_bn`, `debtor_stress`, `stress_increase`, `loss_bn`. `debtor_stress` is the debtor's stress at the end of round *t-1*; `stress_increase` is the change in it that produced this loss.
- **Reconciliation:** `min(1, (L0 + sum of ledger losses) / B)` equals each entity's final stress.

## 5. Status thresholds

Status depends only on final stress `s`.

| Status | Condition |
|---|---|
| Stable | `s < 0.25` |
| Stressed | `0.25 <= s < 1.0` |
| Failed | `s = 1.0` (total loss >= buffer) |

Stress is capped with `min(1, ...)`, so "Failed" is an exact test for `s == 1.0`. `first_round_affected` is the first round in which the entity's status is no longer Stable.

## 6. Scores

**Baseline risk score (0-100).** Three components, each rescaled to 0-1 across all entities (the exact rescaling method is confirmed when task A3 is implemented):

- Leverage: `total_assets_bn / capital_buffer_bn`
- Exposure-to-capital: total outgoing exposure / `capital_buffer_bn`
- Interconnectedness: number of links, incoming plus outgoing

`baseline_score = 100 * (0.4 * leverage + 0.4 * exposure_to_capital + 0.2 * interconnectedness)`

**Scenario score.** `scenario_score = baseline_score + (100 - baseline_score) * final_stress`

- Stress 0 gives the baseline score; stress 1 (Failed) gives exactly 100.
- The score never goes below the baseline or above 100, and it rises steadily with stress.
- Status and score are two views of the same event. Status says how badly an entity was hit in this scenario; the score says how fragile it is overall, adjusted for the scenario. A fragile entity with small stress can score higher than a sturdy one that is Stressed. This is intended.

**KPIs.** *Entities hit* = Stressed + Failed (including the source). *Total loss* = sum of `final_stress * B_i`, the loss absorbed by buffers.

## 7. Worked example (becomes a unit test in task A4)

Severity 70%, `LOSS_RATE = 0.6`.

| Entity | Buffer | Exposures |
|---|---|---|
| Meridian (E01, source) | 63 | none |
| Harbor (E02) | 36 | 28 to Meridian |
| Northwind (E03) | 14 | 10 to Meridian, 20 to Harbor |

| Round | What happens | Resulting stress |
|---|---|---|
| 0 | `min(1, 0.7 * 1.5) = 1.0`, so Meridian fails | Meridian = 1.00 |
| 1 | Harbor loses 0.6 * 28 * 1.0 = 16.8, so 16.8 / 36. Northwind loses 0.6 * 10 * 1.0 = 6.0, so 6 / 14. | Harbor = 0.467, Northwind = 0.429 |
| 2 | Northwind also loses 0.6 * 20 * 0.467 = 5.6 from Harbor. The Meridian loss is recomputed as 6.0, not re-added; its ledger row for round 2 is 0.6 * 10 * (1.0 - 1.0) = 0. Total 11.6 / 14. | Northwind = 0.829 |
| 3 | No stress changed, so stop. | Final: Meridian Failed, Harbor Stressed (0.47), Northwind Stressed (0.83) |

## 8. Required tests (tasks A3-A6)

- The worked example above, with exact numbers.
- Shuffling CSV row order gives identical results.
- The ledger reconciles with final stress.
- Every Failed entity has scenario score exactly 100.
- Scenario score is never below baseline and never above 100.
- Higher severity never reduces any entity's stress.
- Severity 0 causes no spread.
- A source with no links affects only itself.
- The cascade stops within `MAX_ROUNDS`.
- Invalid CSVs are rejected.

## 9. Known simplifications

No fire sales, recoveries or central-bank interventions. Losses beyond a failed entity's buffer are not passed on. Loss rate and shock scale are modelling choices, not estimates from real data.
