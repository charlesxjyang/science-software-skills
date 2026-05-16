# py4DSTEM Evaluation Prompts

Use these prompts to compare baseline agent behavior with and without the
`skills/py4dstem/SKILL.md` context. Score whether the answer uses py4DSTEM
objects/workflows, verifies datacube axes/calibration, and avoids treating
4D-STEM as a generic 4D NumPy array.

## Prompt 1: Virtual Bright/Dark Field Images

I have a 4D-STEM HDF5 file and want to make virtual bright-field and annular
dark-field images. Write Python and include checks before trusting the result.

Expected skill-driven behavior:

- Uses `py4DSTEM.read()` and locates a `DataCube`.
- Prints datacube shape and identifies scan/detector axes.
- Shows mean diffraction pattern before choosing detector geometry.
- Uses py4DSTEM virtual image methods rather than summing arbitrary array axes.
- Records beam center, radii, masks, and calibration assumptions.

## Prompt 2: Bragg Disk Detection

Write a py4DSTEM workflow to detect Bragg disks across a datacube and save the
result for strain mapping. What should I tune?

Expected skill-driven behavior:

- Uses py4DSTEM Bragg disk detection APIs.
- Explains probe/template choice, thresholds, masks, and peak overlays.
- Warns not to copy tutorial thresholds blindly.
- Mentions calibration/distortion checks before quantitative strain.

## Prompt 3: Ptychography Import Fails

I copied a py4DSTEM ptychography tutorial and the phase-retrieval class import
fails. What should I check?

Expected skill-driven behavior:

- Checks installed py4DSTEM version.
- Mentions the v0.14 and v0.14.9 API/class-name boundaries.
- Directs the user to current docs/tutorials before rewriting the algorithm.
