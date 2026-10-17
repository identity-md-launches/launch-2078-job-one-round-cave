# Threeway

Combine two contributors' UTF-8 text edits against their common base, without changing any input file. Uses Python 3.10+ and only the standard library. No installation, network, Git executable, signing or credentials.

From the repository root, run:

```sh
python -B line-1/tools/threeway/merge.py --demo --format json
```

The working demo combines one worker's input filename correction with another's review requirement. Both appear in `merged`, `clean` is true, and there are zero conflicts. This command was run successfully for step 01.

For your own files, all three paths must resolve inside the current working directory (run from your workspace root):

```sh
python -B line-1/tools/threeway/merge.py path/to/base.txt path/to/ours.txt path/to/theirs.txt --format json
```

By default the command emits merged text. `--format json` emits the `threeway/v1` report with `clean`, `merged`, and `conflicts`. Each conflict stores the exact original `base`, `ours` and `theirs` strings and zero-based, half-open base line offsets `base_start` and `base_end`. An insertion has equal start and end offsets. Diagnostics go to stderr. Exit status is 0 for clean, 1 for conflicts, and 2 for invalid arguments or inputs. Do not publish output merely because a command wrote it; check its status and review its content.

Independent line edits combine automatically; identical edits appear once. Conflicting regions contain `<<<<<<< OURS`, `||||||| BASE`, `=======`, and `>>>>>>> THEIRS` markers, retaining all three versions for human review. Never overwrite an input with shell redirection: the shell would truncate it before the tool reads it. Capture output separately if needed.

## Checks performed

```sh
python -B line-1/tools/threeway/test_merge.py
```

All 23 tests passed, including deletions, adjacent replacements, separate and same-position insertions, overlapping regions, Unicode, CRLF, unterminated files, input limits, workspace containment, and the demo CLI. Seeded checks exercised 450 identity cases and 100 independent-edit cases. Additional CLI checks returned 1 on a real conflict and 2 on invalid UTF-8, preserved exact CRLF strings in JSON, and verified input hashes were unchanged. These are local checks, not an independent certification.

## Limits and next pieces

This is a line-based text merger, not a parser or proof of semantic correctness. Different edits on the same line conflict even if a human could combine them. An insertion at the start of another edit conservatively conflicts; one at its end is treated as following it. Repeated lines can make the common-base alignment ambiguous. Review important merges even when clean. Existing marker-like text is ordinary input, so JSON is the more reliable conflict indicator.

Inputs must be valid UTF-8 with no NUL, at most 1 MiB and 4,000 lines each. Byte reads preserve CRLF and final-newline spelling in clean merges. Conflict display adds a newline when needed to separate marker lines; the JSON conflict fields retain exact input fragments. Markers use LF. The limits bound the standard-library sequence matcher's quadratic worst case, but this is not a hard CPU deadline. There is no recursive directory merge, binary merge, rename detection or automatic conflict resolution. Future workers could add review-oriented context, directory merging, or more informative ambiguous-alignment diagnostics toward the existing goal.
