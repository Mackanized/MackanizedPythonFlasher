# PythonFlasher Engineering Standards

# 15 — Anti-Patterns

Version
1.0

Status
Engineering Specification

Applies To

- UI Design
- UX Design
- HMI
- Architecture
- Engineering
- Performance
- Accessibility
- Plugins
- Reviews

Related Documents

- Product Principles
- Design Language
- Interaction System
- HMI
- Telemetry
- Architecture
- Engineering Standards
- Performance
- Quality Assurance

---

# Purpose

This document describes implementation patterns that are **not permitted** within PythonFlasher.

Anti-patterns exist because they repeatedly reduce quality, increase maintenance cost, or negatively affect operator confidence.

Whenever possible, avoid introducing them.

---

# Philosophy

Good engineering is not only about choosing good solutions.

It is equally about refusing poor ones.

Every anti-pattern documented here has one characteristic:

It has already caused problems in professional software.

---

# UI Anti-Patterns

## Decorative UI

Do not add UI elements that have no functional value.

Examples

- glowing borders
- decorative gradients
- random shadows
- glass effects
- unnecessary animations
- oversized icons

PythonFlasher is engineering software.

Every pixel must communicate something.

---

## Inconsistent Spacing

Avoid manually selecting spacing values.

Wrong

17 px

21 px

13 px

Correct

Use spacing tokens.

---

## Misaligned Components

Do not align visually by eye.

Always use layout systems.

Misalignment reduces perceived quality immediately.

---

## Icon-Only Interfaces

Icons alone are insufficient.

Critical actions require text.

Example

Wrong

💾

Correct

💾 Write ECU

---

## Multiple Visual Languages

Never mix

Material

Fluent

Bootstrap

Windows 7

Custom styles

One visual language only.

---

# UX Anti-Patterns

## Hidden Actions

Users should never search for important functionality.

Frequently used actions remain visible.

---

## Confirmation Spam

Avoid dialogs asking

"Are you sure?"

Instead explain

What will happen

Why

Risk

Recovery

---

## Dead Ends

Every screen should provide a clear next action.

Avoid workflows that terminate unexpectedly.

---

## Surprise Navigation

Never change the user's location unexpectedly.

Context must remain stable.

---

## Excessive Modal Dialogs

Do not interrupt workflows unnecessarily.

Prefer

Inline validation

Panels

Inspectors

Notifications

---

# HMI Anti-Patterns

## Hidden System Status

Users must always know

Connection

Voltage

Progress

Current operation

Communication health

Never hide critical state.

---

## Silent Failure

Never fail without explanation.

Every failure should answer

What happened?

Why?

How can I recover?

---

## Blinking Warnings

Avoid flashing alerts.

Persistent warnings are more effective.

Blinking quickly becomes ignored.

---

## Color Only Communication

Never rely solely on red.

Always combine

Text

Icons

Labels

Severity

---

## Dangerous Default Actions

Never make destructive actions the default choice.

Safety always wins over convenience.

---

# Performance Anti-Patterns

## Blocking the UI Thread

Never

Read files

Calculate checksums

Communicate with hardware

Parse A2Ls

Update databases

on the UI thread.

---

## Full View Rebuilds

Avoid rebuilding

Tables

Trees

Graphs

Memory maps

when only a small portion changes.

Prefer incremental updates.

---

## Excessive Polling

Polling wastes resources.

Prefer

Signals

Events

Subscriptions

---

## Over Animation

Animation should explain.

Not entertain.

Never animate continuously.

---

## Startup Bloat

Avoid loading

All plugins

All icons

Entire databases

Unused calibration data

during startup.

Load only what is required.

---

# Architecture Anti-Patterns

## God Classes

Avoid classes responsible for everything.

Examples

ApplicationManager

GlobalManager

MegaController

Large classes hide poor architecture.

---

## God Objects

Avoid global mutable objects shared everywhere.

Explicit dependencies are easier to reason about.

---

## Circular Dependencies

Modules should never depend on each other.

Dependency direction remains consistent.

---

## Business Logic in UI

Never calculate

Checksums

Protocol logic

Validation

Security

inside widgets.

---

## Utility Dumping

Avoid creating

Helpers.py

Utils.py

Common.py

Misc.py

Instead place functionality where it logically belongs.

---

## Copy and Paste Development

Duplicate code is technical debt.

Extract reusable abstractions instead.

---

# Threading Anti-Patterns

Never

Update widgets from workers

Share mutable state

Ignore thread affinity

Block worker shutdown

Spin waiting

Use busy loops

Leak threads

---

# Logging Anti-Patterns

Avoid

Logging every method

Logging without context

Logging secrets

Logging passwords

Logging binary payloads unnecessarily

Logs should explain workflows.

Not drown them.

---

# Telemetry Anti-Patterns

Avoid

Rapidly changing layouts

Constant flickering

Random precision

Decorative gauges

Unexplained values

Telemetry should reduce uncertainty.

---

# Accessibility Anti-Patterns

Never

Use color alone

Remove keyboard support

Disable focus indicators

Ignore screen readers

Animate excessively

Hardcode font sizes

Accessibility is mandatory.

---

# Plugin Anti-Patterns

Plugins should never

Modify host internals

Patch private APIs

Leak resources

Ignore version compatibility

Crash the host application

Plugins must remain isolated.

---

# Error Handling Anti-Patterns

Never

Ignore exceptions

Catch everything

Hide errors

Display raw tracebacks

Continue after unrecoverable failures

Every failure should be explicit.

---

# Design System Anti-Patterns

Never create

One-off colors

One-off buttons

One-off dialogs

One-off typography

One-off spacing

Everything belongs to the Design System.

---

# Engineering Anti-Patterns

Avoid

Premature optimization

Premature abstraction

Over-engineering

Magic numbers

Magic strings

Hidden configuration

Undocumented behavior

Choose clarity first.

---

# Review Anti-Patterns

Never approve code because

"It works."

Review

Maintainability

Architecture

Readability

Performance

Accessibility

Quality

Functionality is only one aspect.

---

# Common Smells

The following usually indicate deeper problems.

Functions over 100 lines

Classes over 1000 lines

Nested if statements

Boolean parameter chains

Repeated validation

Duplicate layouts

Large switch statements

Hidden globals

Repeated comments explaining confusing code

Treat these as investigation triggers.

---

# Refactoring Triggers

Immediately consider refactoring when

The same code appears three times

Developers fear changing a class

Tests become difficult

Review comments repeat

Performance degrades

Bugs recur in one area

Large merge conflicts become common

---

# Decision Checklist

Before introducing any solution ask

Can this reuse an existing component?

Is there a simpler implementation?

Does it increase consistency?

Does it increase cognitive load?

Will another engineer understand this next year?

Would this survive a code review at Microsoft, JetBrains, Bosch or Vector?

If the answer is no, redesign it.

---

# Final Principle

Anti-patterns are not merely coding mistakes.

They are recurring design and engineering decisions that slowly erode product quality.

PythonFlasher should evolve by accumulating well-designed systems—not accumulated compromises.

Every avoided anti-pattern preserves the consistency, reliability, and professionalism expected from OEM-grade engineering software.
