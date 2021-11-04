# `bmk3.yaml` Reference

The following top-level dictionaries are recognized:

   - `import`: A list of files to import into the current script
   - `variables`: A dictionary of variables and their values
   - `templates`: A dictionary of rules and their templates

## `import`

A list of files to import into their current script.

```
import:
    - ../bmk3.yaml
```

Useful to import a set of common rules (see `fragment` below) as well
as common variables. Imports are done before variables in the current
`bmk3.yaml` are read, so imported variables are overwritten by
variables in the current `bmk3.yaml`.

## `variables`

This is a dictionary of variable names to values. Each variable name
_must_ follow Python identifier syntax. A variable whose value is a
list is treated as a _domain_, so if you want a variable to have a
list value, you must specify it as a nested list:

```
binary:
   - 'true'
   - 'false'
listval:
   - [1, 2, 3]
```

Variables specified in a file can be over-ridden by specifying new
values on the command line.

## `templates`

A dictionary of rules and their properties (also a dictionary). The
following properties are recognized:

  - `fragment`: A boolean value which if true will prevent this rule
      from being expanded.
  - `cmds`: A Python `format`-style string that will be expanded.

### Special variables in templates

The following variables are pre-defined for use:

  - `templates[rulename]`, inserts the contents of
    `templates[rulename]` into the string. All such insertions are
    done _before_ variable expansion.
  - `TempFile.attrname`, expands to the name of a temporary file. All
    references to the same attribute of `TempFile` return the same
    name.

