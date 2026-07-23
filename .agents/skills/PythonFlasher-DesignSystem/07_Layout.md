# PythonFlasher Design System

# 07 — Layout System

Version 1.0

Status
Engineering Specification

Related Documents

- 03 — Design Language
- 04 — Interaction System
- 06 — Color System
- 08 — Typography System
- 09 — Component Library

---

# Purpose

This document defines the structural layout system used throughout PythonFlasher.

It establishes how information is organized, how users navigate between workspaces, how components are aligned, and how screens adapt to different resolutions.

The layout system is built around one goal:

**Reduce cognitive load through consistent spatial organization.**

A user should never have to search for common controls.

---

# Layout Philosophy

PythonFlasher is not a dashboard.

It is not a website.

It is not a mobile application.

It is an engineering workstation.

Professional users work for hours.

They build spatial memory.

The interface must remain stable.

Changing layouts unnecessarily destroys efficiency.

---

# Core Principles

## Stable

Primary navigation never moves.

Toolbars remain in the same position.

Status information remains persistent.

Panels open predictably.

---

## Predictable

Users should know where to find information before looking.

Navigation should never require exploration.

---

## Dense

Professional users value information density.

Density must improve productivity rather than create clutter.

Whitespace exists to improve scanning—not to imitate consumer applications.

---

## Modular

Each functional area is self-contained.

Examples

Connection

Diagnostics

Calibration

Flashing

Memory

Logging

Settings

Modules can evolve independently while preserving layout consistency.

---

# Primary Window Structure

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Window Title / Session Indicator / Vehicle / Connection                     │
├──────────────────────────────────────────────────────────────────────────────┤
│ Global Toolbar                                                              │
├──────────────┬──────────────────────────────────────────────┬───────────────┤
│ Navigation   │                                              │ Inspector     │
│ Rail         │             Main Workspace                   │ Panel         │
│              │                                              │               │
│              │                                              │               │
├──────────────┴──────────────────────────────────────────────┴───────────────┤
│ Persistent Status Bar                                                       │
└──────────────────────────────────────────────────────────────────────────────┘
```

Every major workspace follows this structure.

---

# Layout Zones

## Zone 1 — Title Area

Contains

Application title

Workspace title

Vehicle

ECU

Connection indicator

Session state

This area never scrolls.

---

## Zone 2 — Global Toolbar

Contains

Primary actions

Connection

Read

Write

Stop

Search

Settings

Toolbar height remains consistent across every workspace.

---

## Zone 3 — Navigation Rail

Persistent.

Contains only primary modules.

Example

```
Connect

Vehicle

Diagnostics

Read ECU

Write ECU

Calibration

Memory

Live Data

Logs

Settings
```

Never hide primary navigation behind menus.

---

## Zone 4 — Main Workspace

The largest area.

Reserved exclusively for task execution.

No floating advertisements.

No decorative widgets.

No unnecessary dashboards.

---

## Zone 5 — Inspector Panel

Context-sensitive.

Displays

Properties

Metadata

Selected object details

Warnings

History

Quick actions

Inspector width should be user-resizable.

---

## Zone 6 — Status Bar

Always visible.

Contains

Battery voltage

CAN status

Adapter

Transfer speed

CPU usage

Background tasks

Notifications

Current operation

The status bar never disappears.

---

# Workspace Model

Every module owns its own workspace.

Examples

Diagnostics Workspace

Calibration Workspace

Flash Workspace

Memory Workspace

Vehicle Workspace

Users should never feel that they are leaving the application.

Only changing context.

---

# Grid System

PythonFlasher uses an **8-point spacing system**.

Allowed spacing tokens

```
4
8
12
16
24
32
40
48
64
80
96
128
```

Arbitrary spacing values are prohibited.

---

# Alignment Rules

Every element aligns to the grid.

Left edges align.

Titles align.

Buttons align.

Tables align.

Forms align.

No visual drift.

---

# Margins

Standard page margin

24 px

Compact pages

16 px

Wide workspaces

32 px

Never reduce margins simply to fit more content.

Instead redesign the content.

---

# Padding

Cards

16 px

Dialogs

24 px

Panels

16 px

Inspector

16 px

Tables

8–12 px

Toolbar

12 px

---

# Column System

Desktop layouts use flexible columns.

Recommended

```
Navigation

220–260 px

Workspace

Flexible

Inspector

320–420 px
```

Users may resize panels.

Minimum widths should prevent layout collapse.

---

# Responsive Behaviour

PythonFlasher is desktop-first.

Layouts adapt for

1920×1080

2560×1440

3440×1440

3840×2160

Multiple monitors

Do not design for phones.

---

# Docking

Panels may be

Docked

Undocked

Collapsed

Pinned

Auto-hidden

Users control their workspace.

Layouts persist between sessions.

---

# Tabs

Tabs represent workspaces.

Tabs never represent navigation hierarchy.

Maximum visible tabs

10

Overflow handled gracefully.

---

# Cards

Cards group related information.

Cards never replace proper layout.

Avoid dashboard-style "everything is a card."

Cards should contain

Title

Primary content

Optional metadata

Actions

---

# Forms

Forms follow a single-column layout whenever practical.

Label

Input

Helper text

Validation

Alignment remains consistent.

---

# Tables

Tables are first-class citizens.

Support

Sorting

Filtering

Search

Pinned columns

Column chooser

Resize

Export

Copy

Virtual scrolling

---

# Split Views

Split layouts are encouraged.

Examples

Calibration + Hex View

CAN Trace + Decoder

Memory Map + Inspector

Live Data + Graph

Users should not need to switch screens unnecessarily.

---

# Dialog Layout

Dialogs contain

Title

Description

Content

Primary action

Secondary action

Danger action

Buttons remain in predictable positions.

---

# Empty Space

Whitespace has purpose.

Whitespace should

Separate concepts

Improve scanning

Reduce fatigue

Whitespace should never exist simply to make the UI appear modern.

---

# Information Density

Support three density modes.

## Comfortable

Training

Touch

Presentation

---

## Standard

Default

Recommended

---

## Compact

Engineering

Large datasets

Power users

Density affects

Padding

Row height

Toolbar height

Table spacing

Never reduce readability.

---

# Multi-Monitor Support

The application should support

Detached windows

Floating inspectors

Dedicated logging screens

Calibration on one monitor

Live telemetry on another

Workspace layouts persist.

---

# Window Persistence

Remember

Window size

Monitor

Dock positions

Splitter positions

Expanded panels

Selected tabs

Density mode

Theme

Users should resume work exactly where they left off.

---

# Performance Requirements

Layout operations should feel instant.

Target

Resize

<16 ms

Dock panel

<100 ms

Tab switch

<150 ms

Workspace switch

<180 ms

Splitter movement

60 FPS

---

# Accessibility

Support

Keyboard navigation

Logical tab order

Large hit targets

High contrast

Screen readers

Minimum zoom 200%

Layouts remain usable without overlap.

---

# Anti-Patterns

Never

Center important workflows

Use oversized hero sections

Waste vertical space

Hide actions in overflow menus

Require excessive scrolling

Place destructive actions beside primary actions

Change layouts between workspaces

Use floating action buttons

Imitate web dashboards

Design primarily for screenshots

---

# Layout Review Checklist

Every screen must answer

✓ Is the primary action immediately visible?

✓ Can users identify their current context?

✓ Does navigation remain stable?

✓ Is information grouped logically?

✓ Is whitespace purposeful?

✓ Are layouts aligned to the grid?

✓ Does the screen scale from Full HD to 4K?

✓ Can experienced users work efficiently?

✓ Does the layout reduce cursor travel?

✓ Does the screen feel like professional desktop software?

---

# Final Principle

The best layout is one users stop noticing.

After weeks of use, an experienced engineer should instinctively know where every tool, panel, status indicator, and action resides.

Spatial consistency creates confidence.

Confidence creates speed.

Speed creates trust.

A layout that users must consciously think about is a layout that has failed.
