# Semi-Standard Young Tableaux Extension

## Scenario

You now have a working reference implementation that:

- Parses Young diagram shapes (`tableaux.py`)
- Represents Standard Young Tableaux (`tableaux.py`)
- Generates and counts all Standard Young Tableaux for a given shape (`count.py`)
- Exposes a CLI for counting and listing tableaux (`cli.py`)

Your task is to extend this project so that it can **count Semi-Standard Young Tableaux (SSYT)** for a given shape and alphabet size. Semi-standard tableaux differ from standard ones in two important ways:

1. Entries need only be weakly increasing along rows (left → right) and strictly increasing down columns (top → bottom).
2. Values are drawn from a bounded alphabet `{1, …, k}` where `k` is provided by the caller; entries may repeat as long as they obey the row/column rules.

You should reuse the existing data structures where it makes sense, but you will likely need new helpers to handle the relaxed ordering and the external alphabet bound.

## Requirements

- Implement a `SemiStandardYoungTableau` class that extends `StandardYoungTableau` to support the relaxed row-wise ordering.
- Introduce an API `count_semi_standard_young_tableaux(shape, alphabet_size)` that returns the number of SSYTs of the given shape over the alphabet `{1, …, alphabet_size}`.
- Prefer an **iterative (generator/backtracking)** approach similar to the standard implementation so that the counting logic can be adapted for inspection or listing later.
- Ensure row and column ordering constraints match the SSYT definition (weak rows, strict columns).
- Update the CLI to accept an optional `--semi-standard/-ss` defining the alphabet size. When provided, the CLI should count SSYTs; when omitted it should behave as it does today.
- Add unit tests that cover:
  - Basic SSYT counts for small shapes where you can enumerate the tableaux manually
  - Edge cases (alphabet size 1, shapes of height 1, etc.)
  - CLI behaviour when the flag is supplied.

## Suggested Approach

1. Extract shared traversal helpers (e.g. shape parsing, coordinate enumeration) into reusable functions if needed.
2. Implement a generator `generate_semi_standard_young_tableaux(shape, alphabet_size)` that mirrors the standard version but honours the relaxed row constraint and bounded alphabet.
3. Build the counting helper on top of that generator.
4. Extend the CLI parser and printing logic to support the new mode.
5. Write new tests under `tasks/young_tableaux/tests/` and update existing ones if necessary.

Deliverables should include code, tests, and any adjustments to documentation or usage instructions so future students understand how to run the SSYT counting logic.
