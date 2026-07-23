# PythonFlasher Engineering Standards

# 13 — Engineering Standards

Version
1.0

Status
Engineering Specification

Applies To

- PythonFlasher
- Plugins
- Internal Libraries
- Test Projects
- Build Pipeline
- Developer Tooling

Related Documents

- 02 — Product Principles
- 03 — Design Language
- 04 — Interaction System
- 08 — Component Library
- 10 — HMI
- 11 — Telemetry
- 12 — PyQt5 Architecture
- 14 — Performance

---

# Purpose

This document defines the engineering standards governing the implementation of PythonFlasher.

Its purpose is to ensure

- consistency
- maintainability
- scalability
- readability
- reliability
- performance
- safety

These standards are mandatory.

Individual preference does not override project consistency.

---

# Engineering Philosophy

PythonFlasher is engineered for longevity.

The codebase should remain understandable after

- five years
- hundreds of pull requests
- multiple contributors
- major architectural evolution

Engineering decisions should optimize long-term maintainability over short-term convenience.

---

# Core Principles

Every contribution should improve at least one of the following.

- Simplicity
- Readability
- Testability
- Reusability
- Reliability
- Performance
- Safety

If it improves none of them, reconsider the design.

---

# Definition of Done

A feature is complete only when it satisfies all of the following.

✓ Functional requirements implemented

✓ Unit tests added

✓ Integration tests pass

✓ UI follows Design System

✓ Accessibility verified

✓ Performance budget maintained

✓ Logging added where appropriate

✓ Error handling implemented

✓ Documentation updated

✓ Code review approved

Code that merely "works" is not complete.

---

# Project Structure

Organize the solution by responsibility rather than technology.

Example

```
pythonflasher/

    application/

    domain/

    infrastructure/

    presentation/

    shared/

    plugins/

    resources/

    tests/

    tools/
```

Avoid feature scattering.

---

# Module Responsibilities

Each module should have one reason to change.

Examples

Presentation

Rendering

Application

Workflow orchestration

Domain

Business rules

Infrastructure

External systems

Shared

Reusable utilities

Do not mix responsibilities.

---

# Naming Conventions

Names should describe intent.

Good

```
FlashSession

CalibrationValidator

ReadMemoryTask

VehicleRepository

ProtocolDecoder
```

Avoid

```
Helper

Manager

Util

Stuff

Thing

Misc
```

Generic names hide responsibility.

---

# Class Design

Classes should

Be cohesive

Have one responsibility

Expose a clear public API

Hide implementation details

Avoid classes exceeding approximately 500 lines unless justified.

Large classes are usually architectural warnings.

---

# Functions

Functions should

Have one purpose

Return predictable results

Avoid side effects

Remain easy to test

Prefer early returns over deep nesting.

---

# File Size

Recommended

Class

<500 lines

Function

<60 lines

Complex functions should be decomposed.

These are guidelines, not absolute limits.

---

# Dependencies

Dependencies flow inward.

```
Presentation

↓

Application

↓

Domain

↓

Infrastructure
```

The Domain layer depends on nothing above it.

Circular dependencies are prohibited.

---

# State Management

State should be

Explicit

Observable

Minimal

Avoid

Hidden globals

Implicit state

Duplicated state

Mutable shared state

---

# Error Handling

Every error should be

Expected

Classified

Logged

Recoverable where possible

Errors should never be silently ignored.

---

# Exception Policy

Raise exceptions for exceptional situations.

Do not use exceptions for normal control flow.

Wrap infrastructure exceptions before exposing them to higher layers.

Never present raw stack traces to end users.

---

# Logging Standards

Log meaningful events.

Examples

Connection established

Protocol changed

Flash started

Flash completed

Recovery initiated

Validation failed

Avoid logging every trivial operation.

---

# Log Levels

TRACE

Protocol internals

DEBUG

Developer diagnostics

INFO

Normal workflow

WARNING

Recoverable issue

ERROR

Operation failed

CRITICAL

Potential data loss

Choose the lowest appropriate severity.

---

# Threading Standards

UI thread

Rendering only

Worker threads

Communication

Parsing

Checksum

File operations

Telemetry

Never manipulate widgets from worker threads.

---

# Asynchronous Operations

Long-running tasks must

Report progress

Support cancellation where safe

Return structured results

Handle timeouts gracefully

Never block the event loop.

---

# Commands

User actions are represented as commands.

Examples

ConnectAdapterCommand

ReadECUCommand

WriteCalibrationCommand

ValidateFileCommand

Benefits

Centralized logging

Undo support

Testing

Consistency

---

# Validation

Validate early.

Validate often.

Examples

Input

File compatibility

Protocol support

Voltage

Security level

Memory ranges

Programming should never begin if mandatory validation fails.

---

# Configuration

Configuration should be

Versioned

Documented

Validated

Migratable

Never hardcode environment-specific values.

---

# Resource Management

Always release

Files

Sockets

CAN handles

Threads

Timers

Temporary files

Connections

Resource leaks are treated as defects.

---

# Memory Management

Avoid

Duplicate datasets

Unbounded caches

Long-lived temporary objects

Repeated allocations inside loops

Monitor memory usage during long sessions.

---

# Performance Standards

Respect documented performance budgets.

Every feature should be profiled when it

Processes large datasets

Updates frequently

Runs continuously

Introduces new rendering paths

Performance regressions require investigation before merging.

---

# Testing Strategy

Required test levels

Unit Tests

Application logic

Integration Tests

Workflow orchestration

Protocol Tests

Communication

UI Tests

Critical workflows

Performance Tests

Benchmarks

Long-Running Tests

Memory stability

Testing is part of implementation.

---

# Documentation

Every public module should include

Purpose

Responsibilities

Dependencies

Extension points

Complex algorithms require architectural documentation.

Do not rely on comments to explain poor design.

---

# Code Reviews

Every pull request should answer

Why is this needed?

Why is this implementation correct?

What alternatives were considered?

How was it tested?

Does it follow the Design System?

Does it maintain architectural boundaries?

Reviews improve the codebase—not just the current feature.

---

# Security

Never trust external input.

Validate

Files

Protocol data

Network responses

Plugin inputs

Configuration

Logs should never expose secrets or sensitive credentials.

---

# Plugin Standards

Plugins must

Use documented interfaces

Remain isolated

Fail safely

Avoid blocking the host

Declare capabilities

Support version compatibility

A faulty plugin must never destabilize the application.

---

# Build Quality

The build should be

Repeatable

Deterministic

Automated

Warnings should be investigated.

New warnings should not be introduced without justification.

---

# Dependency Management

Third-party dependencies must

Have a clear purpose

Be actively maintained

Be compatible with project licensing

Be reviewed periodically

Avoid introducing dependencies for trivial functionality.

---

# Accessibility Standards

Engineering features must preserve

Keyboard navigation

Accessible names

High contrast

Reduced motion

Localization support

Accessibility regressions are functional defects.

---

# Continuous Improvement

Refactoring is encouraged when it

Improves readability

Reduces duplication

Simplifies architecture

Improves performance

Improves testing

Large refactors should preserve observable behavior.

---

# Anti-Patterns

Never

Mix UI and business logic

Create circular dependencies

Hide state

Ignore exceptions

Duplicate validation

Copy and paste implementations

Hardcode UI values

Use global mutable state

Block the UI thread

Bypass architectural boundaries

Introduce "temporary" hacks without tracking them

---

# Engineering Review Checklist

Every contribution should satisfy

✓ Single responsibility

✓ Clear naming

✓ Appropriate abstraction

✓ Layer boundaries respected

✓ Test coverage included

✓ Logging implemented

✓ Performance maintained

✓ Accessibility preserved

✓ Documentation updated

✓ Design System compliance verified

---

# Final Principle

Engineering quality is not measured by clever code.

It is measured by code that remains understandable, reliable, and maintainable years after it was written.

Every contributor is responsible not only for delivering new functionality, but also for preserving the integrity of the architecture.

PythonFlasher should evolve continuously while maintaining the consistency, reliability, and craftsmanship expected of professional engineering software.
