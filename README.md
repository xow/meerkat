Simple tool to help you peer review moodle code faster. Comes in both MDK and bash varieties!

## Installation

1. Install mdk, if you haven't already
2. Go to the directory in which MDK is installed
3. `git remote add xow git@github.com:xow/mdk.git`
4. `git fetch xow`
5. `git checkout -b meerkat xow/meerkat`
6. Go to your moodle instance. Code away


## How to use

To run all the tests that are most relevant to your patch, type:

`mdk meerkat -t -r`

To just run unit tests or behat acceptance tests, type:

```
mdk meerkat --behat -r
mdk meerkat --unit -r
```

If you want to list the relevant tests instead of running them, use a `-l` flag instead of `-r`.


To automatically check coding style and documentation, use:

`mdk meerkat -s`

It will only review lines you wrote.

Meerkat by default determines "your changes" as the difference between your current branch and master. To compare with another branch (such as MOODLE_28_STABLE), use -b or --branch. This is compatible with both
the syntax checker and the unit tests.

`mdk meerkat -b MOODLE_28_STABLE -r -t`
