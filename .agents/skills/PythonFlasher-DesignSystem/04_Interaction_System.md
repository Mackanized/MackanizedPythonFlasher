# PythonFlasher Design System

# 04 — Interaction System

Version 1.0

Status: Engineering Specification

Authors:
Product Design
Human Factors Engineering
UX Engineering

---

# Purpose

This document defines every interaction pattern used throughout PythonFlasher.

Unlike the Design Language, which defines visual appearance, the Interaction System defines behavior.

Every button.

Every click.

Every keyboard shortcut.

Every dialog.

Every animation.

Every notification.

Every workflow.

Must follow the interaction rules defined here.

Consistency is mandatory.

---

# Interaction Philosophy

PythonFlasher should feel invisible.

The user should never think

"How do I use this?"

Instead they should think

"I'm already working."

Professional software minimizes interaction cost.

Interaction cost consists of

• Number of clicks

• Cognitive effort

• Cursor movement

• Waiting

• Decision making

• Navigation depth

Every design decision should reduce one or more of these.

---

# The Five Interaction Principles

## 1. Immediate Feedback

Every interaction acknowledges user input.

Target latency

Mouse Hover

<16ms

Button Press

<50ms

Keyboard Shortcut

<50ms

Navigation

<150ms

Long-running Task

Immediate acknowledgement

No action should ever feel ignored.

---

## 2. Predictability

The same interaction always produces the same result.

Buttons never change behavior unexpectedly.

Keyboard shortcuts remain consistent.

Context menus remain structured.

Dialogs appear in familiar locations.

Users should build muscle memory.

---

## 3. Progressive Disclosure

Complexity appears only when requested.

Default

Simple

Advanced

Professional

Expert

Developer

Every level builds upon the previous one.

Nothing important is hidden.

Nothing advanced is forced.

---

## 4. Continuous Context

Users should never lose awareness of

Current ECU

Current vehicle

Connection

Operation

Progress

Voltage

Status

Current workspace

Switching screens must never remove critical information.

---

## 5. Confidence

Every interaction should increase confidence.

Never uncertainty.

Never ambiguity.

Never silence.

---

# Navigation Model

PythonFlasher uses persistent navigation.

Preferred

Navigation Rail

Sidebar

Context Toolbar

Workspace Tabs

Inspector Panel

Avoid

Hamburger menus

Nested dialogs

Wizard chains

Hidden controls

Floating windows

---

# Navigation Rules

The current location must always be obvious.

Primary navigation never changes position.

Frequently used functions require one click.

Navigation depth should never exceed three levels.

---

# Mouse Interaction

Hover

Reveal affordance

Never hidden functionality

Single Click

Selection

Activation

Double Click

Open details

Expand

Edit

Right Click

Context-specific actions only

Never duplicate the toolbar entirely.

---

# Keyboard Interaction

Keyboard support is mandatory.

Examples

Ctrl+O

Open

Ctrl+S

Save

Ctrl+Shift+B

Backup

Ctrl+R

Read ECU

Ctrl+W

Write ECU

Ctrl+L

Logs

F5

Refresh

F11

Fullscreen

Esc

Cancel operation (where safe)

Tab

Move focus

Shift+Tab

Previous focus

Space

Activate

Enter

Confirm

---

# Focus System

Keyboard focus must always be visible.

Focused controls

2px accent outline

No hidden focus states.

Never rely on color only.

---

# Cursor Behavior

Busy operations

Busy cursor only when interaction is blocked.

Background operations

Normal cursor.

Avoid unnecessary wait cursors.

---

# Workspace Philosophy

PythonFlasher is task-oriented.

Users work inside workspaces.

Connection

Diagnostics

Reading

Writing

Analysis

Logging

Settings

Each workspace remembers

Layout

Scroll position

Selections

Filters

---

# Multi-Tasking

Users should be able to

Monitor logs while flashing

View telemetry while reading

Inspect CAN traffic during diagnostics

Compare files while connected

Use dockable panels.

Never force screen switching.

---

# Selection Model

Selected items remain selected until changed.

Selection should survive

Sorting

Filtering

Refresh

Navigation where appropriate.

---

# Long Running Operations

Every operation immediately transitions into

Preparing

Executing

Verifying

Completing

Finished

Every stage has visible feedback.

---

# Progress Requirements

Every operation must display

Progress

Current stage

Transfer speed

ETA

Voltage

Memory address

Retries

Current service

No generic loading indicators.

---

# Cancellation

Users may cancel only when safe.

Unsafe operations

Display explanation

Explain consequences

Offer recovery

Never abruptly terminate ECU programming.

---

# Confirmation Dialogs

Only ask for confirmation when

Data loss

Programming

Erase

Delete

Overwrite

Dangerous actions

Never ask

"Are you sure?"

Instead explain

What

Why

Impact

Recovery

Example

Write Calibration

Vehicle

Saab 9-3 Aero

Calibration

Stage2.bin

Duration

4 minutes

Backup exists

Yes

---

# Notifications

Notification Categories

Information

Success

Warning

Error

Background completion

Notifications should

Appear

Explain

Disappear

Critical warnings persist.

---

# Search

Search should exist wherever data exceeds ten items.

Support

Instant filtering

Keyboard focus

Highlight matches

Recent searches

---

# Tables

Tables support

Sorting

Filtering

Column resize

Copy

Export

Search

Sticky header

Keyboard navigation

Context menu

---

# Context Menus

Context menus contain

Relevant actions only.

Maximum

8 actions

Group destructive actions separately.

---

# Drag and Drop

Supported where appropriate

Calibration files

Layouts

Dock panels

Logs

Memory regions

Never use drag and drop as the only workflow.

---

# Undo

Every reversible action should support undo.

Examples

Layout

Filters

Selections

Preferences

Irreversible operations

Programming

Erase

Security Access

Require confirmation instead.

---

# Error Recovery

Every failure should answer

What happened?

Why?

Impact?

Recovery?

Relevant logs?

Documentation?

Support?

---

# Background Tasks

Background tasks remain visible.

Use

Task Center

Status Bar

Progress Card

Never hide running tasks.

---

# Empty States

Every empty state answers

Why?

What now?

How?

Example

No Adapter Connected

Connect a supported J2534 or Kvaser interface.

[Connect]

---

# Accessibility

All interactions must support

Keyboard

Screen readers

Reduced motion

High contrast

Large hit targets

Touch where applicable

---

# Performance Targets

Hover

16ms

Button Response

50ms

Navigation

150ms

Workspace Switch

180ms

Dialog

180ms

Table Scroll

60 FPS

Telemetry Updates

Continuous

Animation

60 FPS

---

# Anti-Patterns

Never

Block the UI

Hide progress

Hide errors

Require unnecessary clicks

Open unnecessary dialogs

Interrupt workflow

Force mouse-only interaction

Depend solely on color

Use infinite spinners

Hide keyboard shortcuts

---

# Review Checklist

Every interaction should answer

Is feedback immediate?

Is the action predictable?

Can it be completed with fewer clicks?

Is keyboard navigation supported?

Is accessibility maintained?

Does it improve confidence?

Does it interrupt workflow?

Would a professional use this all day?

If the answer to any question is "no", redesign the interaction.

---

# Final Principle

The user should never need to think about the interface.

Every interaction should feel obvious.

Every action should feel immediate.

Every workflow should feel natural.

The software should disappear.

Only the engineering should remain.
