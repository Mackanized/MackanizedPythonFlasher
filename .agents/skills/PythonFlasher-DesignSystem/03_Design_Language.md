# PythonFlasher Design System

# 03 — Desktop Design Language

Version 1.0

Status: Living Specification

---

# Purpose

This document defines the visual language of PythonFlasher.

It establishes the rules governing the application's appearance, spatial organization, interaction patterns, visual hierarchy, information density, and overall user experience.

It is not a style guide.

It is a complete desktop design language.

Every future component, screen and feature should conform to this specification.

---

# Design Vision

PythonFlasher should feel like professional desktop software released in 2026.

Not 2022.

Not 2018 with Dark Mode.

Not a Bootstrap dashboard.

Not an Electron application.

Not a mobile application stretched onto a desktop.

Instead the application should feel like software built by an OEM engineering team that has spent years refining productivity.

---

# Product Identity

The application should communicate

Precision

Engineering

Reliability

Performance

Calmness

Transparency

Confidence

Nothing should feel decorative.

Nothing should feel accidental.

Nothing should resemble a generic UI kit.

---

# Design Inspiration

PythonFlasher draws inspiration from the interaction quality—not the appearance—of:

• Windows 11
• Windows App SDK
• Visual Studio 2026
• JetBrains Rider
• ETAS INCA
• Vector CANoe
• Volvo VIDA
• Bosch ESI Tronic
• Siemens TIA Portal
• Unreal Engine Editor
• Adobe Lightroom Desktop
• DaVinci Resolve
• Figma Desktop

The goal is not imitation.

The goal is extracting the best interaction patterns.

---

# The Design Pillars

Every screen should satisfy five pillars.

## Clarity

Users immediately understand

Where they are

What is connected

What is happening

What happens next

---

## Density

Professional users prefer information.

Do not confuse empty space with simplicity.

Whitespace should improve readability.

Not reduce capability.

---

## Rhythm

Spacing should feel mathematical.

Nothing should feel randomly positioned.

Margins

Padding

Typography

Cards

Tables

Toolbars

Everything aligns to the same spacing system.

---

## Motion

Motion explains state.

Never decoration.

---

## Confidence

Every interaction reinforces trust.

---

# Visual Personality

PythonFlasher should feel

Professional

Industrial

Premium

Engineered

Intentional

Focused

Quiet

Stable

It should never feel

Playful

Consumer

Minimalist for its own sake

Flashy

Marketing driven

AI generated

Template based

---

# Information Architecture

Information always has hierarchy.

Priority 1

Current ECU

Current Operation

Progress

Connection

Voltage

Errors

Priority 2

Telemetry

Transfer Speed

Memory Address

Session

Retries

Priority 3

Vehicle Metadata

Calibration

Protocol

Hardware

Priority 4

Developer Diagnostics

Raw UDS

CAN Frames

ISO-TP

---

# Desktop Philosophy

PythonFlasher embraces desktop computing.

Large workspaces

Resizable layouts

Keyboard shortcuts

Dockable panels

Persistent workspaces

Multiple monitors

Context menus

Rich tables

Professional workflows

Do not optimize for tablets.

Do not optimize for phones.

---

# Window Layout

Recommended structure

+------------------------------------------------------+
Toolbar
+------------------------------------------------------+

Navigation Rail

Workspace

Inspector Panel

+------------------------------------------------------+

Persistent Status Bar

Every major screen follows the same structure.

---

# Navigation

Always visible.

Never hidden.

Preferred

Navigation Rail

Sidebar

Tabbed Workspace

Context Toolbar

Avoid

Hamburger menus

Deep navigation

Hidden actions

Floating toolbars

---

# Spatial System

Everything follows an 8-point spacing grid.

Spacing Tokens

4

8

12

16

24

32

40

48

64

96

No arbitrary spacing values.

---

# Corner Radius

Buttons

8 px

Cards

12 px

Dialogs

16 px

Menus

8 px

Progress

6 px

Consistency is mandatory.

---

# Elevation

Use subtle depth.

Never exaggerated shadows.

Levels

0

Canvas

1

Cards

2

Floating panels

3

Dialogs

4

Critical overlays

Elevation should communicate hierarchy.

Not aesthetics.

---

# Borders

Borders should be subtle.

Avoid heavy outlines.

Primary separator

1 px

Cards

1 px

Focus

2 px

Error

2 px

---

# Surface Hierarchy

Level 0

Main workspace

Level 1

Cards

Level 2

Inspector

Level 3

Dialogs

Level 4

Critical alerts

Surface hierarchy should be immediately understandable.

---

# Design Tokens

Every visual value must originate from tokens.

Spacing

Radius

Elevation

Typography

Animation

Border

Color

Opacity

Never hardcode visual values.

---

# Color Philosophy

Color communicates meaning.

Not branding.

Semantic colors

Neutral

Accent

Success

Warning

Danger

Information

Selection

Disabled

Muted

Never use color purely for decoration.

---

# Typography

Primary

Segoe UI Variable

Fallback

Segoe UI

Inter

Hierarchy

28

Page title

22

Workspace title

18

Section title

16

Card title

14

Body

12

Metadata

11

Technical values

Use weight—not size—for emphasis.

---

# Iconography

Single icon library.

Fluent Icons

Outlined

Simple

Consistent

Sizes

16

20

24

32

No mixed icon styles.

---

# Buttons

Primary

High emphasis

One per screen

Secondary

Common actions

Tertiary

Low emphasis

Danger

Red

Destructive actions

Never place two primary buttons beside each other.

---

# Tables

Professional software lives in tables.

Requirements

Resizable columns

Sorting

Filtering

Search

Copy

Export

Column chooser

Sticky headers

Virtualization

60 FPS scrolling

---

# Cards

Cards organize information.

Not decorate it.

Every card contains

Title

Primary value

Metadata

Status

Optional actions

Cards should never become dashboards.

---

# Empty States

Every empty screen explains

Why nothing exists

What to do next

Recommended action

Example

No ECU Connected

Connect a supported adapter to begin.

[Connect]

---

# Loading States

Never show

Loading...

Instead show

Reading Calibration

Current Address

Transfer Speed

Remaining Time

Progress

Voltage

Retries

Every loading state should communicate useful information.

---

# Error States

Never

Unknown Error

Instead

What happened

Why

Impact

Recovery

Relevant logs

Support links

---

# Notifications

Notification Types

Information

Success

Warning

Error

Background completion

Notifications should expire intelligently.

Critical notifications remain visible.

---

# Motion

Every animation must answer

Why does this exist?

Recommended durations

Hover

120 ms

Button

80 ms

Navigation

180 ms

Dialog

180 ms

Toast

220 ms

Panel

180 ms

Avoid

Bounce

Elastic

Overshoot

Infinite animations

---

# Live Telemetry

Values should never "jump."

Animate transitions.

Examples

Voltage

Transfer Speed

Frame Counter

ETA

Progress

Temperature

Every update should feel continuous.

---

# Visual Density

Support three modes.

Comfortable

Normal

Compact

Workshop

Workshop mode increases

Button size

Spacing

Contrast

Touch targets

---

# Accessibility

Support

Reduced Motion

High Contrast

Large Fonts

Keyboard Navigation

Screen Readers

Color Blind Safe Palettes

Every feature must remain usable without relying on color.

---

# Anti Patterns

Never imitate

Bootstrap

Material Dashboard

Tailwind Admin Templates

Qt Designer defaults

Generic Figma templates

AI-generated landing pages

Overuse

Gradients

Glass

Neumorphism

Huge shadows

Massive cards

Decorative icons

Avoid unnecessary whitespace.

Professional software values information density.

---

# Definition of Quality

A high-quality interface feels inevitable.

Nothing calls attention to itself.

Users instinctively know

where to click

what is happening

what will happen next

The interface disappears.

The engineering remains.

---

# Acceptance Criteria

Every new screen shall satisfy:

✓ Consistent layout

✓ Consistent spacing

✓ Semantic colors only

✓ Uses design tokens

✓ Meets accessibility requirements

✓ Supports keyboard navigation

✓ Professional information hierarchy

✓ Live telemetry where applicable

✓ Motion follows Motion System

✓ Feels like premium 2026 desktop software

If any requirement fails, the design is incomplete.

---

# Final Statement

PythonFlasher should never look like a Python application.

It should never resemble a web application.

It should feel like software developed by an experienced OEM engineering team where every interaction has been refined over years of daily professional use.

Users should immediately trust it.

After a few minutes, they should stop noticing it altogether.
