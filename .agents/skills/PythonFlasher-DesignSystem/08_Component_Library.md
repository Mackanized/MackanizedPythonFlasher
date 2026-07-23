# PythonFlasher Design System

# 08 — Component Library

Version
1.0

Status
Engineering Specification

Related Documents

- 03 — Design Language
- 04 — Interaction System
- 06 — Color System
- 07 — Typography System
- 07 — Layout System
- 09 — Motion System

---

# Purpose

This document defines every reusable user interface component used within PythonFlasher.

No screen should introduce a unique control unless it has first been added to this library.

A component is more than a visual element.

It includes

- Purpose
- Behavior
- States
- Accessibility
- Keyboard interaction
- Motion
- Performance expectations
- Usage guidance
- Anti-patterns

Consistency is achieved by reusing components—not by recreating them.

---

# Component Philosophy

Every component must satisfy six requirements.

## Understandable

Users immediately recognize its purpose.

---

## Predictable

The component behaves consistently throughout the application.

---

## Accessible

The component remains fully usable without a mouse and meets accessibility requirements.

---

## Responsive

Visual feedback is immediate.

No interaction should feel ignored.

---

## Performant

Components remain responsive even when displaying thousands of items.

---

## Composable

Components should combine naturally with other components.

---

# Component States

Every interactive component supports the same state model.

```
Default

↓

Hover

↓

Pressed

↓

Focused

↓

Disabled

↓

Busy

↓

Success

↓

Warning

↓

Error
```

Not every component exposes every state visually, but every state should be supported conceptually.

---

# Global Interaction Rules

Every component

✓ receives keyboard focus

✓ exposes accessible names

✓ supports tooltips where appropriate

✓ supports High Contrast Mode

✓ supports Reduced Motion

✓ supports 200% DPI scaling

✓ supports localization

---

# Primary Button

## Purpose

Represents the primary action within a view.

Examples

Read ECU

Write Calibration

Connect

Backup

---

## Rules

One primary button per view.

Never place competing primary actions together.

---

## States

Default

Hover

Pressed

Focused

Disabled

Busy

Success

---

## Accessibility

Enter activates.

Space activates.

Visible focus indicator.

---

# Secondary Button

Purpose

Supporting actions.

Examples

Cancel

Browse

Refresh

Open Folder

---

Should never visually compete with the primary action.

---

# Destructive Button

Purpose

Irreversible operations.

Examples

Erase

Delete

Factory Reset

Never use for normal actions.

Requires confirmation for irreversible operations.

---

# Icon Button

Purpose

Compact contextual actions.

Examples

Copy

Pin

Expand

Detach

Refresh

Every icon button requires an accessible label.

Avoid icon-only actions when meaning is ambiguous.

---

# Toggle Button

Purpose

Enable or disable a persistent state.

Examples

Live Logging

Auto Refresh

Expert Mode

Visual state must always indicate current value.

---

# Checkbox

Purpose

Independent boolean options.

Use only when options are unrelated.

Never use checkboxes for mutually exclusive choices.

---

# Radio Button

Purpose

Single choice from a small set.

Maximum recommended options

5

More than five options should use a Combo Box or segmented control.

---

# Switch

Purpose

Immediate on/off system settings.

Examples

Dark Theme

Workshop Mode

Reduced Motion

Switches apply immediately.

No confirmation required unless safety is affected.

---

# Combo Box

Purpose

Select one item from a larger list.

Supports

Keyboard search

Filtering

Arrow navigation

Type-ahead

Large datasets should be virtualized.

---

# Search Field

Purpose

Instant filtering and lookup.

Supports

Incremental search

Clear button

Keyboard shortcuts

Search history

Highlight matches

Search should begin without requiring an explicit button whenever practical.

---

# Text Field

Purpose

Single-line input.

Supports

Validation

Placeholder text

Copy

Paste

Undo

Redo

Never use placeholder text as the only label.

---

# Numeric Input

Purpose

Engineering values.

Supports

Units

Range validation

Increment/decrement

Keyboard entry

Examples

RPM

Pressure

Voltage

Timeout

Memory offset

---

# File Picker

Purpose

Selecting calibration files.

Supports

Drag and drop

Recent files

Favorites

Validation

File preview

Remember last location.

---

# Tree View

Purpose

Hierarchical navigation.

Examples

Vehicle hierarchy

Calibration categories

Memory layout

Supports

Expand

Collapse

Search

Lazy loading

Keyboard navigation

---

# Table

Purpose

Primary data presentation.

Tables are first-class components.

Required features

Sorting

Filtering

Column resize

Column chooser

Sticky header

Context menu

Keyboard navigation

Virtual scrolling

Copy

Export

Selection persistence

Tables must remain performant with very large datasets.

---

# Property Grid

Purpose

Structured editing of ECU metadata and calibration values.

Supports

Grouping

Categories

Search

Inline editing

Validation

Reset to default

---

# Inspector Panel

Purpose

Displays contextual information about the current selection.

Should never replace primary content.

Typical content

Properties

Warnings

Metadata

History

Quick actions

---

# Card

Purpose

Group related information.

Cards should not become decorative containers.

Typical content

Title

Summary

Status

Optional actions

---

# Tabs

Purpose

Parallel workspaces.

Tabs should represent tasks—not navigation hierarchy.

Support

Reordering

Closing

Keyboard navigation

Overflow handling

---

# Toolbar

Purpose

Expose frequently used actions.

Contains

Primary actions

Separators

Search

Connection state

Quick tools

Avoid overcrowding.

---

# Navigation Rail

Purpose

Primary application navigation.

Always visible.

Never collapses automatically.

Should contain only top-level destinations.

---

# Status Bar

Purpose

Persistent operational awareness.

Always visible.

Typical content

Voltage

Connection

Protocol

Adapter

Transfer speed

Background tasks

Notifications

Time

---

# Progress Indicator

Purpose

Display operation progress.

Must include

Percentage

Current stage

ETA

Speed

Never display an indeterminate spinner if measurable progress exists.

---

# Progress Timeline

Purpose

Display multi-stage workflows.

Example

```
Prepare

↓

Connect

↓

Unlock

↓

Read

↓

Verify

↓

Complete
```

Users should immediately understand where they are.

---

# Notification

Types

Information

Success

Warning

Error

Completion

Notifications should explain

What happened

Why

What to do next

---

# Dialog

Purpose

Focused user decision.

Structure

Title

Explanation

Content

Actions

Primary action placed consistently.

Avoid nested dialogs.

---

# Wizard

Purpose

Guide infrequent, complex workflows.

Examples

First-time adapter setup

Firmware recovery

Project import

Prefer progressive disclosure over long wizards.

---

# Context Menu

Purpose

Expose contextual actions.

Maximum

Eight actions.

Destructive actions separated visually.

---

# Tooltip

Purpose

Clarify—not teach.

Tooltips explain

What

Not

How

Keep concise.

---

# Code Viewer

Purpose

Display

CAN traffic

Hexadecimal

Scripts

Logs

Requirements

Monospaced font

Syntax highlighting where appropriate

Line numbers

Copy support

Search

---

# Graph

Purpose

Live telemetry visualization.

Supports

Zoom

Pan

Pause

Export

Cursor inspection

Graphs should remain smooth at 60 FPS.

---

# Gauge

Purpose

Display critical live metrics.

Examples

Voltage

RPM

Pressure

Temperature

Use sparingly.

Tables are often superior.

---

# Memory Map

Purpose

Visualize ECU memory layout.

Supports

Selection

Zoom

Address tooltips

Status overlays

Read/write state

Checksum regions

---

# Dock Panel

Purpose

Flexible workspace organization.

Supports

Dock

Float

Auto-hide

Pin

Persistence

---

# Accessibility Requirements

Every component supports

Keyboard navigation

Screen readers

Logical tab order

Accessible names

High contrast

200% scaling

Reduced motion

Color-independent communication

---

# Performance Requirements

Hover response

<16 ms

Click response

<50 ms

Open menu

<100 ms

Dialog

<180 ms

Table scroll

60 FPS

Graph rendering

60 FPS

Memory map zoom

60 FPS

---

# Component Acceptance Checklist

Every component must answer

✓ Is its purpose obvious?

✓ Is it reusable?

✓ Does it follow the shared state model?

✓ Does it support keyboard interaction?

✓ Does it expose accessibility metadata?

✓ Does it remain performant with large datasets?

✓ Does it scale to high DPI?

✓ Does it support localization?

✓ Does it integrate with the motion system?

✓ Does it reinforce operator confidence?

---

# Anti-Patterns

Never

Invent new button styles

Duplicate existing components

Create special-case controls

Hide important actions behind hover

Use decorative cards

Depend solely on icons

Require mouse-only interaction

Create modal workflows unnecessarily

Ignore accessibility requirements

Hardcode component sizes

---

# Component Lifecycle

Every new component follows the same process.

1. Identify the problem.

2. Confirm an existing component cannot solve it.

3. Define purpose and behavior.

4. Specify states and accessibility.

5. Prototype.

6. Review against Product Principles.

7. Implement.

8. Validate performance.

9. Test with keyboard and assistive technologies.

10. Add to this library before reuse.

---

# Final Principle

Components are the vocabulary of the interface.

A small set of well-designed, highly reusable components creates a product that feels coherent, predictable, and professional.

Every component should feel familiar the first time it is used and invisible after the hundredth.

When users stop noticing individual controls and focus entirely on the engineering task at hand, the component library has fulfilled its purpose.
