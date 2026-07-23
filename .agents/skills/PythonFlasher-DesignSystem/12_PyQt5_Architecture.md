# PythonFlasher Design System

# 12 — PyQt5 Architecture

Version
1.0

Status
Engineering Specification

Related Documents

- 02 — Product Principles
- 03 — Design Language
- 04 — Interaction System
- 08 — Component Library
- 09 — Screen Specifications
- 10 — Human–Machine Interface (HMI)
- 11 — Telemetry System

---

# Purpose

This document defines the architectural principles for implementing PythonFlasher using PyQt5.

The objective is to create a desktop application that is

- modular
- testable
- maintainable
- performant
- scalable
- accessible
- resilient

The architecture should support years of development without requiring fundamental restructuring.

---

# Architectural Goals

The architecture should

- separate presentation from business logic
- isolate hardware communication
- support multiple communication backends
- allow plugins and future expansion
- simplify testing
- maximize responsiveness
- minimize coupling

---

# Core Principles

## Separation of Concerns

Each layer has a single responsibility.

The UI never communicates directly with hardware.

The flashing engine never updates widgets.

The protocol layer never manipulates layouts.

Every layer communicates through clearly defined interfaces.

---

## Composition Over Inheritance

Favor small reusable components over deep inheritance trees.

Build complex views by composing independent widgets.

Avoid monolithic base classes.

---

## Explicit State

Application state should always be explicit.

Avoid hidden globals.

Avoid singleton-driven workflows where practical.

Every screen should receive the state it needs.

---

## Immutable Domain Objects

Domain models should be treated as immutable whenever practical.

Updates create new state rather than mutating shared objects unexpectedly.

This simplifies debugging and improves predictability.

---

# High-Level Architecture

```
+---------------------------------------------------------+
|                    PythonFlasher                        |
+---------------------------------------------------------+
|                    Presentation Layer                   |
|---------------------------------------------------------|
| Main Window                                             |
| Workspaces                                              |
| Dialogs                                                 |
| Widgets                                                 |
| View Models                                             |
+---------------------------------------------------------+
|                  Application Layer                      |
|---------------------------------------------------------|
| Commands                                                |
| Services                                                |
| Navigation                                               |
| State Management                                        |
| Validation                                               |
+---------------------------------------------------------+
|                    Domain Layer                         |
|---------------------------------------------------------|
| ECU Models                                              |
| Calibration Models                                      |
| Vehicle Models                                          |
| Flash Models                                            |
| Diagnostics Models                                      |
+---------------------------------------------------------+
|                 Infrastructure Layer                    |
|---------------------------------------------------------|
| J2534                                                   |
| Kvaser                                                  |
| SocketCAN                                               |
| DoIP                                                    |
| File System                                             |
| Logging                                                 |
| Settings                                                |
+---------------------------------------------------------+
```

---

# Layer Responsibilities

## Presentation Layer

Responsible for

Rendering

Input

Accessibility

Layout

Navigation

Animation

Theme

Never

Protocol logic

Checksum calculations

Security algorithms

Communication

---

## Application Layer

Coordinates workflows.

Examples

Read ECU

Write ECU

Backup

Recovery

Validation

Session changes

This layer orchestrates.

It does not implement hardware protocols.

---

## Domain Layer

Contains business rules.

Examples

Calibration

Flash memory

Security access

Checksum

Memory regions

Vehicles

ECUs

Protocols

Independent from PyQt.

Independent from widgets.

---

## Infrastructure Layer

Responsible for

Hardware

Drivers

CAN

USB

File I/O

Logging

Configuration

Networking

External libraries

Everything outside the application's core logic belongs here.

---

# Main Window

The MainWindow owns

Navigation

Workspace manager

Dock manager

Status bar

Global toolbar

Theme manager

It should not implement application logic.

---

# Workspace Architecture

Each workspace is self-contained.

Example

```
ReadECUWorkspace

├── Toolbar

├── Progress Panel

├── Telemetry Panel

├── Log Panel

├── Inspector
```

Workspaces communicate through shared services rather than direct references.

---

# Widget Philosophy

Widgets should be

Small

Reusable

Focused

Independent

Avoid creating large widgets with multiple responsibilities.

---

# Model-View Strategy

Follow Qt's Model/View architecture whenever possible.

Use

QAbstractItemModel

QSortFilterProxyModel

QTableView

QTreeView

QListView

Avoid convenience widgets for large datasets.

---

# View Models

Each workspace owns a ViewModel.

Responsibilities

Expose observable state

Validate user input

Coordinate commands

Translate domain models into presentation models

Never manipulate widgets directly from domain logic.

---

# State Management

Application state should be centralized.

Examples

Current vehicle

Current ECU

Current project

Connected adapter

Workspace layout

Theme

User preferences

Avoid duplicated state.

---

# Signals and Slots

Signals communicate state changes.

Slots react to events.

Guidelines

Signals should describe what happened.

Examples

```
ecuConnected

flashStarted

progressUpdated

voltageChanged

diagnosticsCompleted
```

Avoid generic names like

updated()

changed()

event()

---

# Threading

The UI thread remains dedicated to rendering.

Background threads perform

CAN communication

File operations

Checksum calculations

Logging

Parsing

Compression

Never block the UI thread.

---

# Background Tasks

All long-running operations use task objects.

Example

```
ReadTask

FlashTask

RecoveryTask

ChecksumTask

ImportTask
```

Tasks expose

Progress

Status

Cancellation

Completion

Errors

---

# Dependency Injection

Prefer constructor injection.

Avoid service lookups from widgets.

Dependencies remain explicit.

Improves testing.

---

# Commands

Every user action becomes a command.

Examples

ConnectAdapterCommand

ReadECUCommand

WriteFlashCommand

BackupCommand

ValidateCalibrationCommand

Commands simplify undo, logging and testing.

---

# Validation

Validation occurs before execution.

Examples

Voltage

Compatibility

File integrity

Security level

Protocol support

Programming never begins if validation fails.

---

# Error Handling

Errors propagate upward.

Infrastructure

↓

Application

↓

Presentation

Presentation decides how to communicate with the user.

Never display raw exceptions.

---

# Logging

Logging occurs at every layer.

Infrastructure

Driver events

Application

Workflow events

Domain

Business events

Presentation

UI events

Logs should include correlation identifiers for long-running workflows.

---

# Navigation

Navigation changes workspaces.

It never owns workflow logic.

Workspaces remain independent.

---

# Persistence

Persist

Window geometry

Dock layout

Workspace state

Recent files

Recent vehicles

Theme

Density

User preferences

Persistence should be transparent.

---

# Styling

All styling originates from the design system.

Avoid inline styles.

Centralize

Colors

Spacing

Typography

Icons

Animations

Use reusable theme definitions.

---

# Performance

Target startup

<2 seconds

Workspace switch

<180 ms

Table rendering

<100 ms

Dock operations

60 FPS

Scrolling

60 FPS

Avoid unnecessary widget creation.

Virtualize large datasets.

---

# Testing

Architecture should support

Unit tests

Integration tests

UI automation

Protocol simulation

Mock adapters

Mock ECUs

Dependency inversion simplifies testing.

---

# Plugin Architecture

Support future extensions.

Possible plugins

Protocols

ECU definitions

Importers

Exporters

Telemetry providers

Visualizations

Analysis tools

Plugins communicate through stable interfaces.

---

# Accessibility

Architecture must support

Accessible names

Keyboard navigation

Screen readers

High contrast

Reduced motion

Localization

Accessibility is part of the framework—not an afterthought.

---

# Review Checklist

Every new feature should satisfy

✓ Clear layer ownership

✓ No UI business logic

✓ Reusable widgets

✓ Centralized state

✓ Thread-safe operations

✓ Testable components

✓ Consistent navigation

✓ No duplicated code

✓ Design system compliance

✓ Responsive under load

---

# Anti-Patterns

Never

Call hardware directly from widgets

Perform blocking operations in the UI thread

Share mutable global state

Create circular dependencies

Embed business rules in dialogs

Duplicate validation logic

Hardcode styles

Manipulate widgets from worker threads

Bypass the command layer

Ignore Qt's Model/View architecture

---

# Future Evolution

The architecture should support future migration to

- PySide6
- Qt 6
- Additional protocol stacks
- Remote diagnostics
- Cloud synchronization
- Distributed processing
- Plugin marketplace

without requiring fundamental redesign.

---

# Final Principle

The architecture should make the correct implementation the easiest implementation.

Developers should naturally build new functionality by composing existing services, models, and components rather than introducing one-off solutions.

A well-designed architecture is largely invisible to the user, but it is felt every day through responsiveness, reliability, consistency, and ease of maintenance.

PythonFlasher should not only look like professional engineering software—it should be engineered like it.
