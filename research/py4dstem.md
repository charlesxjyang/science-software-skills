# py4DSTEM Skill Evidence Notes

This note records the evidence used for `skills/py4dstem/SKILL.md`; it is not
runtime skill content.

## Sources Reviewed

- Official docs:
  https://py4dstem.readthedocs.io/
- Tutorial repository:
  https://github.com/py4dstem/py4DSTEM_tutorials
- Source repository:
  https://github.com/py4dstem/py4DSTEM
- v0.14 transition documentation:
  https://py4dstem.readthedocs.io/en/latest/changelog.html
- v0.14.9 release note about phase-retrieval class names:
  https://github.com/py4dstem/py4DSTEM/releases
- First steps example:
  https://py4dstem.readthedocs.io/en/latest/examples/first_steps.html
- Virtual imaging example:
  https://py4dstem.readthedocs.io/en/latest/examples/virtual_imaging.html
- Bragg disk detection example:
  https://py4dstem.readthedocs.io/en/latest/examples/bragg_disk_detection.html
- API reference:
  https://py4dstem.readthedocs.io/en/latest/api.html
- py4DSTEM paper:
  https://doi.org/10.1017/S1431927621000477

## Extracted Workflow

The docs/tutorials emphasize:

1. Inspect HDF5 trees with `print_h5_tree()` and load a target `DataCube` with
   `read(..., datapath=...)`, or use `import_file()` for non-native formats.
2. Inspect datacube shape, calibration, mean diffraction pattern, and example
   scan-position diffraction patterns.
3. Build virtual images/diffraction with explicit detector geometry.
4. For Bragg workflows, select a probe/template and tune detection parameters
   from the actual data.
5. Apply calibration/distortion corrections before quantitative strain,
   orientation, COM/DPC, or phase-retrieval outputs.

## Docs-Derived Gotchas

- v0.14 is a major API/workflow boundary; old notebooks should not be copied
  directly into v0.14+ environments.
- v0.14.9 renamed/refactored phase-retrieval class names, so ptychography import
  failures may be version issues rather than missing packages.
- Datacube shape and axis order are not incidental. Agents should name scan and
  diffraction axes before slicing or reshaping.
- Virtual detector geometry and Bragg detection thresholds are dataset-specific.
  Tutorial constants should be treated as examples only.

## Open Follow-Ups

- Validate example code against a local py4DSTEM install and sample dataset.
- Test prompts for virtual imaging, Bragg disk detection, and phase-retrieval
  import/version troubleshooting once Claude auth is available.
