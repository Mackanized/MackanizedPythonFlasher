# PythonFlasher Design System

# 06 — Color System

Version 1.0

Status
Engineering Specification

Related Documents

• Desktop Design Language

• Interaction System

• Motion System

• Component Library

---

# Purpose

This document defines every color used within PythonFlasher.

Unlike a branding guide, this specification defines semantic meaning rather than visual appearance.

Users should never think

"This button is blue."

Instead they should instinctively understand

"This operation is safe."

"This ECU is connected."

"This flash operation is active."

"This warning requires attention."

Color exists to reduce cognitive effort.

Never for decoration.

---

# Design Philosophy

Professional engineering software should remain visually calm.

The application spends hours on screen.

Bright colors create fatigue.

Constant contrast creates fatigue.

Excessive saturation creates fatigue.

PythonFlasher therefore uses a restrained neutral palette with semantic accents that appear only when meaningful.

Most of the interface should be neutral.

Color should draw attention—not compete for it.

---

# The Color Hierarchy

Colors exist in layers.

Level 1

Neutral Foundation

Level 2

Interactive Controls

Level 3

Semantic States

Level 4

Critical Attention

Most of the interface should never exceed Level 1.

---

# Design Goals

The color system should

Reduce fatigue

Improve recognition

Increase confidence

Highlight important changes

Improve readability

Support accessibility

Scale to light and dark themes

Support workshops with varying lighting conditions

---

# Semantic Color Philosophy

PythonFlasher never uses colors as decoration.

Every color has one meaning.

Every meaning has one color.

No exceptions.

---

# Neutral Colors

Purpose

Workspace

Panels

Tables

Dialogs

Cards

Navigation

Backgrounds

Neutral colors should dominate approximately 90–95% of the interface.

---

## Tokens

Surface

SurfaceElevated

SurfaceContainer

SurfaceHover

SurfacePressed

SurfaceSelected

SurfaceDisabled

SurfaceOverlay

Canvas

Workspace

Panel

Card

Dialog

Border

Divider

---

# Accent Color

Accent represents

Focus

Selection

Primary interaction

Navigation

Never use Accent for warnings or success.

Accent should never indicate danger.

---

## Tokens

Accent

AccentHover

AccentPressed

AccentSoft

AccentBorder

AccentFocus

AccentBackground

---

# Success

Represents

Successful operation

Completed flash

Connected ECU

Verified checksum

Valid calibration

Successful backup

Successful communication

Never use Success for buttons.

---

## Tokens

Success

SuccessSoft

SuccessBackground

SuccessBorder

SuccessText

---

# Warning

Represents

Low voltage

Potential incompatibility

Calibration mismatch

Firmware warning

Communication retries

Conditions requiring attention

Warnings should encourage action without causing panic.

---

## Tokens

Warning

WarningSoft

WarningBackground

WarningBorder

WarningText

---

# Danger

Represents

Erase operations

Write operations

Programming interruption

Critical communication failure

Permanent data loss

Danger should appear rarely.

If everything is red

nothing is important.

---

## Tokens

Danger

DangerSoft

DangerBackground

DangerBorder

DangerText

---

# Information

Represents

Read-only status

Telemetry

Background tasks

Hints

Documentation

Information should remain calm.

---

## Tokens

Info

InfoSoft

InfoBackground

InfoBorder

---

# Selection

Represents

Current row

Current ECU

Selected memory region

Focused navigation item

Selected file

Never confuse selection with active operations.

---

## Tokens

Selection

SelectionHover

SelectionBorder

SelectionBackground

---

# Disabled

Represents

Unavailable functionality

Missing connection

Unsupported feature

Never use low contrast that becomes unreadable.

Disabled controls must remain understandable.

---

## Tokens

Disabled

DisabledBorder

DisabledText

DisabledBackground

---

# Error Colors

Errors should communicate urgency without overwhelming users.

Display

Reason

Impact

Recovery

Errors are not simply red.

They are structured.

---

# Voltage Colors

Voltage deserves its own semantic scale.

Normal

Green

Acceptable

Neutral

Low

Amber

Critical

Red

Programming should visually reinforce battery health continuously.

---

# Flash Progress Colors

Preparing

Blue

Unlocking

Purple

Reading

Cyan

Verifying

Teal

Writing

Orange

Completed

Green

Failed

Red

Users should immediately understand the current phase.

---

# Memory Visualization

Memory maps use consistent semantic colors.

Unused

Neutral

Readable

Blue

Writing

Orange

Verified

Green

Protected

Purple

Error

Red

Never rely solely on color.

Use icons and labels.

---

# CAN Traffic

Receive

Blue

Transmit

Green

Warning

Amber

Error

Red

Filtered

Grey

Maintain consistency with diagnostics.

---

# Charts

Charts should use restrained colors.

Avoid rainbow palettes.

Maximum

Six simultaneous colors.

Prefer

Neutral baseline

Single accent

Semantic highlights

---

# Contrast Requirements

Minimum

WCAG AA

Target

WCAG AAA wherever practical.

Critical information must remain readable in sunlight and dark workshops.

---

# Dark Theme

Dark theme is the primary experience.

Objectives

Reduce eye fatigue

Improve contrast

Avoid OLED bloom

Avoid deep black

Preferred surfaces

Charcoal

Graphite

Slate

Avoid

Pure black

High saturation

Bright borders

---

# Light Theme

Light theme is optional.

Maintain identical semantic meanings.

Never invert color semantics.

---

# Workshop Mode

Workshop mode increases contrast.

Larger text

Higher contrast

Reduced transparency

Reduced gradients

Enhanced warnings

Designed for

Bright garages

Outdoor work

Laptop use in daylight

---

# Accessibility

Never depend solely on color.

Every semantic state also uses

Icons

Labels

Typography

Patterns where appropriate

Support

Protanopia

Deuteranopia

Tritanopia

Reduced contrast sensitivity

---

# Color Usage Rules

Primary Button

Accent

Danger Button

Danger

Connection

Success

Flash Progress

Semantic Stage

Errors

Danger

Navigation

Neutral

Selection

Accent

Cards

Neutral

Dialogs

Neutral

---

# Anti-Patterns

Never

Use gradients for decoration

Color every card

Color every table row

Use multiple accent colors

Mix semantic meanings

Use saturated backgrounds

Color entire screens

Flash colors continuously

Blink warnings

Use neon colors

Use red as branding

---

# Acceptance Criteria

Every new UI element must satisfy

✓ Uses semantic tokens

✓ Never hardcoded colors

✓ Supports dark theme

✓ Supports light theme

✓ Meets accessibility contrast

✓ Semantic meaning remains consistent

✓ Never relies solely on color

✓ Uses appropriate interaction states

✓ Supports reduced motion mode

✓ Passes color blindness testing

---

# Future Expansion

The Color System should support

Custom themes

OEM themes

Workshop themes

High Contrast

Reduced Blue Light

User personalization

without changing semantic meaning.

---

# Final Principle

Color is a language.

Every color communicates.

Every communication has meaning.

If a color does not improve understanding, remove it.

PythonFlasher should feel calm, professional and engineered—not colorful.

The software should earn attention through clarity, not decoration.
