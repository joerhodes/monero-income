# monero-income

A command-line tool that builds weekly and monthly income reports from a
Monero wallet, valuing each payout at its historical USD price.

## Intro

This is a spec-driven development (SDD) rewrite of one of my existing
projects. The rewrite has two goals:

- Try out [GitHub Spec Kit](https://github.com/github/spec-kit) for SDD,
  from constitution through implementation.
- Deliver a few items from the original project's roadmap: price
  finalization for recent days, and default row limits on the weekly and
  monthly tables.

The original version remains the reference implementation. This rewrite
is expected to produce matching reports for the same data.

## Status

Not yet usable. See `.specify/` and `specs/` for the spec work in progress.
