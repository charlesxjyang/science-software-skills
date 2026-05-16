# pymatgen Evaluation Prompts

Use these prompts to compare baseline agent behavior with and without the
`skills/pymatgen/SKILL.md` context. Score whether the answer uses pymatgen
domain objects, respects Materials Project API conventions, and avoids
hand-rolled materials parsing.

## Prompt 1: Phase Stability From Materials Project Entries

Write Python that gets Li-Fe-P-O entries from Materials Project, builds a phase
diagram, and reports the energy above hull for LiFePO4. Include the checks I
should record for reproducibility.

Expected skill-driven behavior:

- Uses `pymatgen.ext.matproj.MPRester` or explicitly justifies `mp-api`.
- Uses `get_entries_in_chemsys` or equivalent entry retrieval, not raw JSON
  scraping.
- Builds `PhaseDiagram(entries)` and reports `eV/atom` hull energy.
- Mentions API key configuration, entry compatibility/database provenance, and
  material IDs.
- Does not mix arbitrary DFT total energies into the MP hull without
  compatibility processing.

## Prompt 2: Cleanly Read And Inspect A CIF

I downloaded a CIF from a database and want to convert it to a POSCAR. Write
Python that reads it, checks for common problems, and writes a POSCAR.

Expected skill-driven behavior:

- Uses `Structure.from_file()` or pymatgen I/O, not manual CIF parsing.
- Checks formula, site count, lattice, occupancies/disorder, warnings, and short
  distances or duplicate sites.
- Writes using pymatgen's VASP I/O helpers.
- Does not silently discard partial occupancy or oxidation-state information.

## Prompt 3: Convert Structure To ASE For A Calculator

I have a pymatgen `Structure` from Materials Project and want to run an ASE
calculator on it. Show the conversion and the validation checks.

Expected skill-driven behavior:

- Uses `pymatgen.io.ase.AseAtomsAdaptor`.
- Compares atom count, species order, cell, and PBC after conversion.
- Notes that site properties, oxidation states, magnetic moments, and selective
  dynamics may need explicit handling.
- Attaches the calculator on the ASE side, not inside pymatgen.
