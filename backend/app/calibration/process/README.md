# Process Calibration Profiles

This directory contains replaceable process-effect calibration artifacts.

- `public_proxy_v0.json` keeps the original public/proxy behavior.
- `synthetic_calibrated_example_v0.json` is a calibrated-mode synthetic example for integration tests.

For measured process data, add a new JSON profile with:

- `artifact_id`
- `model_mode`
- `dataset_id`
- `model_version`
- `sample_count`
- `stage_weights`
- `scale_factors`
- `effect_coefficients`

Select it from `process_parameters.calibration_artifact_id` and set:

- `process_parameters.calculation_mode = "calibrated"`
- `process_parameters.calibration_status = "calibrated"`
- `process_parameters.source_type = "internal_measurement"`
