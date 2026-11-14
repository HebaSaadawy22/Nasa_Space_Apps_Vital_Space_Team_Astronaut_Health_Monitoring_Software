# Vital Space — Machine Learning Technical Report

## 1. Project Overview

Vital Space is a prototype astronaut health-monitoring platform designed to analyze simulated health readings and identify statistically unusual changes.

The Machine Learning subsystem supports batch and incremental prediction, astronaut-specific feature engineering, and an experimental operational review-assessment engine.

## 2. Dataset

The project uses synthetic demonstration data, not real NASA medical records.

| Property | Value |
|---|---|
| Raw records | 180 |
| ML-ready records | 162 |
| Astronauts | 6 |
| Recorded days | 30 per astronaut |
| Raw columns | 19 |
| ML-ready columns | 29 |
| Initial insufficient-history records | 18 |

The first three readings per astronaut are excluded from model scoring because the three-reading historical baseline is unavailable.

## 3. Data Processing

The preprocessing pipeline includes:

- Missing-value and duplicate checks
- Technical range validation
- UTC timestamp normalization
- Astronaut-specific chronological ordering
- Rolling historical averages
- Reading-to-reading changes
- Personal baseline deviations

Rolling features are calculated from previous observations only, preventing future-reading leakage under the tested processing assumptions.

## 4. Primary ML Model

**Algorithm:** Isolation Forest  
**Feature count:** 19  
**Method:** Unsupervised anomaly detection

Initial chronological training:

- Training: mission days 4–23, 120 readings
- Testing: mission days 24–30, 42 readings
- Training anomalies flagged: 10
- Testing anomalies flagged: 0

These counts represent statistical model decisions, not verified medical conditions.

## 5. Model Comparison

Experimental split:

- Training: days 4–18, 90 readings
- Validation: days 19–23, 30 readings

Isolation Forest flagged 2 of 30 original validation readings. Local Outlier Factor flagged 5 of 30.

LOF exhibited stronger responses in several synthetic perturbation scenarios, but also generated more baseline flags.

There are no ground-truth clinical labels sufficient to establish which model is medically superior.

**Decision:** Retain Isolation Forest as the provisional primary model.

## 6. Feature Experiments

Three feature groups were compared:

| Group | Features | Original validation flags |
|---|---:|---:|
| Baseline | 19 | 2/30 |
| All Environment | 23 | 10/30 |
| Selected Environment | 21 | 6/30 |

Environmental features increased some responses, particularly for simulated radiation changes, but they also changed the baseline alert frequency.

**Decision:** Retain the existing 19-feature model contract pending stronger evidence.

## 7. Threshold Analysis

The original decision threshold is 0.0 for the inverted Isolation Forest decision-function score.

| Threshold configuration | Validation flags |
|---|---:|
| Sensitive | 4/30 |
| Model default | 2/30 |
| Moderate | 2/30 |
| Conservative | 2/30 |
| Very conservative | 1/30 |

A more sensitive threshold increased detection of some modified readings but also increased the overall validation flag rate.

**Decision:** Retain the original model decision threshold provisionally.

## 8. Risk Assessment

The project includes an experimental review-assessment engine with the following levels:

- `low`: No configured review signal was identified.
- `moderate`: ML anomaly or a configured moderate-level rule signal.
- `high`: A configured high-level external rule signal.
- `unknown`: Insufficient or unavailable assessment information.

These levels express operational review priority, not validated medical risk.

## 9. Health Rules

A configurable rules engine supports independent metric-based review signals.

Rules must be explicitly provided to the prediction service. No medically approved astronaut-specific thresholds are currently supplied.

## 10. Software Components

| Module | Responsibility |
|---|---|
| features.py | Feature engineering |
| train.py | Model training |
| predict.py | Offline inference |
| evaluate.py | Synthetic sensitivity evaluation |
| compare_models.py | Model comparison |
| feature_experiments.py | Feature-set comparison |
| threshold_analysis.py | Decision-threshold exploration |
| validation.py | Input validation |
| risk.py | Review assessment |
| health_rules.py | Configurable rule evaluation |
| service.py | Batch inference interface |
| streaming.py | Incremental inference and local history |

## 11. Verification

The existing implementation passed 35 automated tests before the final end-to-end tests were added.

These tests cover feature calculations, input validation, batch/streaming model equivalence, persistence, risk assessment, and health-rule evaluation.

Final end-to-end test results must be recorded separately after execution.

## 12. Limitations and Outstanding Work

- Synthetic data only
- Small sample size
- No clinical ground-truth labels
- No independent untouched clinical validation dataset
- No approved astronaut-specific health-rule thresholds
- No clinical risk-model validation
- No Kafka integration yet
- No production-grade delivery guarantees
- Persistent prediction-result idempotency remains incomplete

The existing validation periods have been examined repeatedly, so the experiments are exploratory rather than independent final performance assessments.

## 13. Conclusion

Vital Space has a functional prototype Machine Learning subsystem for astronaut-specific statistical anomaly detection and configurable operational review assessment.

Its current readiness is **prototype integration**, not medical or production deployment. Additional validation and system-level integration are required before operational use.