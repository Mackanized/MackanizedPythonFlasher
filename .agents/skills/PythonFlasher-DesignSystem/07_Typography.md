# PythonFlasher Design System

# 07 — Typography System

Version
1.0

Status
Engineering Specification

Related Documents

- 03 — Design Language
- 04 — Interaction System
- 06 — Color System
- 08 — Layout System
- 09 — Component Library

---

# Purpose

Typography is the primary method of communicating information in PythonFlasher.

More than 90% of the application consists of text, numbers, hexadecimal values, diagnostic messages, calibration names, memory addresses and telemetry.

Typography therefore exists to optimize comprehension, not visual expression.

This document defines the complete typography system for the application.

---

# Design Goals

The typography system must

• maximize readability

• reduce visual fatigue

• improve scan speed

• create predictable hierarchy

• optimize numeric readability

• support long engineering sessions

• scale correctly on High DPI displays

• support localization

Typography should never draw attention to itself.

The interface should feel calm and effortless to read.

---

# Typography Philosophy

PythonFlasher follows one simple rule.

**Hierarchy is created primarily through weight, spacing and position—not dramatic changes in size.**

Large differences in font size create visual noise.

Professional software should feel measured and restrained.

---

# Font Stack

## Primary UI Font

Segoe UI Variable

Preferred Platform

Windows 11+

---

## Fallback

Segoe UI

---

## Secondary

Inter

Used only when Segoe UI Variable is unavailable.

---

## Monospaced Font

Cascadia Mono

Fallback

Consolas

JetBrains Mono

Used for

Memory addresses

Hexadecimal values

Binary data

CAN identifiers

UDS services

Diagnostic payloads

Calibration offsets

Console output

Logs

Never use proportional fonts for technical values.

---

# Font Characteristics

The primary typeface should provide

Excellent hinting

High readability

Wide Unicode coverage

Tabular figures

Clear distinction between

0 / O

1 / l / I

5 / S

8 / B

This is critical for engineering software.

---

# Type Scale

The application uses a restrained type scale.

| Token        | Size  | Weight   | Usage              |
| ------------ | ----- | -------- | ------------------ |
| Display      | 32 px | Semibold | Splash, About      |
| PageTitle    | 28 px | Semibold | Workspace title    |
| SectionTitle | 22 px | Semibold | Major sections     |
| PanelTitle   | 18 px | Semibold | Inspector panels   |
| CardTitle    | 16 px | Semibold | Cards              |
| BodyLarge    | 15 px | Regular  | Main content       |
| Body         | 14 px | Regular  | Standard UI        |
| Caption      | 12 px | Regular  | Metadata           |
| Technical    | 12 px | Medium   | Tables             |
| Micro        | 11 px | Regular  | Secondary metadata |

---

# Font Weights

Regular

Primary body text

Medium

Numeric values

Semibold

Hierarchy

Bold

Critical emphasis only

Avoid excessive bold text.

Weight should communicate importance.

---

# Line Heights

Readable interfaces depend more on line height than font size.

| Text Style | Line Height |
| ---------- | ----------- |
| Display    | 40 px       |
| Page       | 36 px       |
| Section    | 30 px       |
| Panel      | 26 px       |
| Body       | 22 px       |
| Caption    | 18 px       |
| Technical  | 18 px       |

Never use automatic line spacing.

---

# Paragraph Width

Long text should remain readable.

Recommended maximum

70–80 characters

Documentation panes may exceed this where necessary.

---

# Alignment Rules

Default alignment

Left

Numeric values

Right

Memory addresses

Right

Hexadecimal values

Left inside monospaced columns

Tables

Headers left

Numbers right

Status values aligned vertically

Consistency improves scan speed.

---

# Numeric Typography

Engineering software is driven by numbers.

Numeric values should always use

Tabular figures

Right alignment

Consistent decimal precision

Examples

```
13.82 V
13.79 V
13.76 V
```

Not

```
13.8
13.82
13.821
```

Decimals should remain predictable.

---

# Decimal Precision

Battery voltage

2 decimals

Temperature

1 decimal

Pressure

1 decimal

RPM

Whole numbers

Speed

Whole numbers

Progress

Whole numbers

Percentages

Whole numbers unless precision is meaningful.

---

# Monospaced Content

Always use Cascadia Mono for

```
0x7E0

0x18DAF110

34 56 7A 89

AA BB CC DD

SID 27

Security Access

Flash Address

0x001A4300
```

Never mix proportional fonts with hexadecimal content.

---

# Hexadecimal Formatting

Uppercase hexadecimal.

Examples

```
0x0001AF20

0x7E0

0x18DAF110
```

Avoid lowercase.

Maintain fixed-width alignment.

---

# Tables

Tables should prioritize readability over density.

Headers

Medium weight

Body

Regular

Numbers

Right aligned

Identifiers

Monospaced

Selected rows

Increase weight slightly rather than changing font size.

---

# Status Indicators

Status values should remain visually stable.

Example

```
Voltage

13.84 V

Transfer

2.48 MB/s

Frames

18,441

ETA

00:01:42
```

Avoid jitter by using tabular figures.

---

# Error Messages

Hierarchy

Title

Description

Recovery

Technical Details

Example

```
Security Access Failed

The ECU rejected the supplied security key.

Verify the selected algorithm.

Retry after cycling ignition.

Details

NRC 0x35

Invalid Key
```

Never present a wall of text.

---

# Log Output

Logs use

Monospaced typography

Fixed row height

Timestamp alignment

Severity indicators

Example

```
12:44:31.124

TX

27 01

Security Access

12:44:31.136

RX

67 01

Seed Received
```

Logs should scan vertically.

---

# Truncation

Prefer

Middle truncation

For

Long file paths

Calibration names

Memory addresses

VIN comparisons

Example

```
C:\Projects\...\Stage2.bin
```

Avoid hiding important suffixes.

---

# Localization

Typography must support

English

German

Swedish

French

Italian

Spanish

Polish

Japanese

Chinese

Future RTL languages

Layouts should tolerate text expansion of at least 30%.

---

# Accessibility

Minimum body text

14 px

Support scaling up to 200%.

Avoid condensed fonts.

Maintain readable line spacing after scaling.

---

# DPI Scaling

Support

100%

125%

150%

175%

200%

250%

300%

No clipping.

No overlapping text.

No pixel snapping artifacts.

---

# High Frequency Data

Rapidly changing values should

Animate smoothly

Avoid width changes

Maintain alignment

Use tabular figures

Examples

Voltage

RPM

Progress

Transfer speed

Frame count

ETA

---

# Typography Tokens

```
Font.Display

Font.PageTitle

Font.Section

Font.Panel

Font.Body

Font.Caption

Font.Technical

Font.Mono

Weight.Regular

Weight.Medium

Weight.Semibold

Weight.Bold
```

No hardcoded font sizes.

All typography originates from tokens.

---

# Anti-Patterns

Never

Mix multiple font families

Use decorative fonts

Center-align body text

Use proportional fonts for hexadecimal data

Use inconsistent decimal precision

Overuse bold

Use italics for emphasis

Use tiny metadata text

Display all-uppercase paragraphs

Reduce contrast for important values

---

# Typography Review Checklist

Every screen should satisfy

✓ Hierarchy is obvious

✓ Numeric values align correctly

✓ Technical values use monospaced fonts

✓ Hexadecimal values remain readable

✓ Tables scan vertically

✓ Typography scales correctly

✓ Accessibility requirements are met

✓ Localization does not break layouts

✓ No hardcoded font sizes

✓ Reading feels effortless during long sessions

---

# Final Principle

Typography should never compete for attention.

Its purpose is to make engineering information immediately understandable.

When users can effortlessly scan a calibration table, identify a memory address, compare hexadecimal values, or monitor live telemetry without conscious effort, the typography system has achieved its purpose.

In PythonFlasher, typography is not decoration.

It is an engineering instrument.
