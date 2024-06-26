# bmk3

The third incarnation of `bmk`, a tool to construct and execute
command-lines, mostly used for running benchmarks.

`bmk3` is incompatible with `bmk2`. It is much simpler -- performing
only the task of template expansion and executing the resulting script.

## Installation

Install `bmk3` as:

```
python3 setup.py develop --user
```

The `develop` command is recommended.

## Usage

Assuming you're in a directory containing a `bmk3.yaml` file (see
below), just run:

```
bmk3
```

to see all the possible commands and rules.

### Running Rules

To run rules, specify the rule name:

```
bmk3 rule1
```

This will execute all rules whose names start with `rule1`. Rule names
are suffixed with contents of variables.

**Glob-style patterns**: `bmk3` also supports the use of glob-style patterns to match rule
names.

```
bmk3 -g '*some*'
```

will match all rules containing `some`.  Note the use of quotes to
shield the pattern from the shell.

### Parallel Execution of Rules

You can run the rules in parallel using the `-j` option to `bmk3`.

```
bmk3 rule1 -j
```

Run all instances of `rule1` in parallel using all processors
available on the system.

The `-j` option takes a number that limits the number of processors
used. For example:

```
bmk3 -j2 rule1
```

will use only 2 processors.


## The `bmk3.yaml` File

The `bmk3.yaml` file specifies a set of _rules_ which are essentially
Python `format` templates. The variables for these rules are specified
in the YAML file itself (or on the command line). `bmk3` expands each
rule using the provided variables. Each rule is written to a shell
script and executed.

A sample `bmk3.yaml` file looks like:

```
variables:
  binary:
    - 'true'
    - 'false'
templates:
  run:
    cmds: '{binary}'

```

This specifies a (static) rule called `run`. When you run `bmk3` in
the directory containing this file, you are shown the expansions of
this rule:

```
INFO:bmk3:Loaded 1 files
*** run:true
   CmdScript(name='run:true', script='true')
*** run:false
   CmdScript(name='run:false', script='false')
INFO:bmk3:COUNT: 0, SUCCESS: 0, FAILED: 0
```

To actually execute these rules, run `bmk3 run*`, you'll see:

```
INFO:bmk3:Loaded 1 files
INFO:bmk3:**** run:true from /tmp/y
INFO:bmk3:
    true
INFO:bmk3:Running run:true at 2021-11-03 22:21:11.563502
INFO:bmk3.runner:Logging output to /tmp/tmpp0uztrdr
INFO:bmk3.runner:Logging errors to /tmp/tmphklzgvl_
INFO:root:Running bash /tmp/tmpzr2ozlux.sh in /tmp/y
INFO:root:Running bash /tmp/tmpzr2ozlux.sh succeeded
ERROR:bmk3:Running run:true SUCCEEDED
INFO:bmk3:
INFO:bmk3:
INFO:bmk3:run:true finished at 2021-11-03 22:21:11.567834
INFO:bmk3:run:true took 0.004214012995362282 s
INFO:bmk3:**** run:false from /tmp/y
INFO:bmk3:
    false
INFO:bmk3:Running run:false at 2021-11-03 22:21:11.568140
INFO:bmk3.runner:Logging output to /tmp/tmpoaanpalb
INFO:bmk3.runner:Logging errors to /tmp/tmpslr0ppju
INFO:root:Running bash /tmp/tmpgkcw2_uq.sh in /tmp/y
ERROR:bmk3.runner:Error when running "bash /tmp/tmpgkcw2_uq.sh", return code=1
ERROR:bmk3:Running run:false FAILED
INFO:bmk3:
INFO:bmk3:
INFO:bmk3:run:false finished at 2021-11-03 22:21:11.571836
INFO:bmk3:run:false took 0.0036189110251143575 s
INFO:bmk3:COUNT: 2, SUCCESS: 1, FAILED: 1
```

Note the success of `true` and the failure of `false`.

See the [`bmk3.yaml` reference](bmk3yaml-ref.md) for syntax details.

# LICENSE

SPDX-FileCopyrightText: 2021 University of Rochester

SPDX-License-Identifier: MIT


