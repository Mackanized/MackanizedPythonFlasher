# PythonFlasher Design System

# 11 — Telemetry System

Version
1.0

Status
Engineering Specification

Related Documents

- 02 — Product Principles
- 03 — Design Language
- 04 — Interaction System
- 06 — Color System
- 07 — Typography System
- 08 — Component Library
- 10 — Human–Machine Interface (HMI)

---

# Purpose

This document defines how operational telemetry is collected, presented, updated, and prioritized throughout PythonFlasher.

Telemetry provides continuous awareness of system state.

It is not intended to entertain.

It is not decorative.

Its purpose is to help users make safe, informed engineering decisions.

---

# Definition

Telemetry is any continuously changing information that describes the state of the application, connected hardware, vehicle, ECU, or communication channel.

Examples include

- Battery voltage
- Programming progress
- CAN bus traffic
- Transfer speed
- Security level
- ECU session
- Current flash address
- Memory region
- Retry count
- Connection latency

Telemetry should always answer one question:

**"What is happening right now?"**

---

# Design Goals

Telemetry should

- improve operator confidence
- reduce uncertainty
- support troubleshooting
- reveal trends
- provide early warning
- remain readable during long sessions
- avoid unnecessary distraction

---

# Telemetry Hierarchy

Telemetry is divided into four priority levels.

## Level 1 — Safety Critical

Displayed at all times while connected.

Includes

Battery Voltage

Programming State

Connection Status

Current Operation

Current ECU

Communication Errors

Security Session

These values are persistent.

They never disappear.

---

## Level 2 — Operational

Displayed during relevant workflows.

Includes

Transfer Speed

Elapsed Time

Remaining Time

Current Address

Current Block

Verification Progress

Retry Count

Current Service

These values are visible whenever an operation is active.

---

## Level 3 — Diagnostic

Displayed in diagnostics and advanced workspaces.

Includes

CAN Frames

UDS Services

Bus Utilization

Latency

Message Counters

Dropped Frames

Protocol Information

These values support investigation rather than routine operation.

---

## Level 4 — Developer

Hidden by default.

Available in Developer Mode.

Includes

Raw Payloads

Decoded Frames

Timing Measurements

Internal Queues

Memory Allocation

Debug Counters

Trace Events

---

# Persistent Status Bar

The status bar provides continuous awareness.

Recommended layout

```
Adapter | Protocol | ECU | Voltage | Session | Speed | Background Tasks | Time
```

The order never changes.

---

# Battery Voltage

Battery voltage is considered a first-class safety indicator.

Display

Current value

Trend

Warning threshold

Critical threshold

Visual example

```
13.92 V

Stable
```

Voltage should update smoothly without visual jitter.

---

# Connection Status

Always visible while hardware is connected.

States

Disconnected

Connecting

Connected

Busy

Recovering

Error

Do not rely on color alone.

Use text and iconography.

---

# Programming Progress

Programming progress should include

Overall percentage

Current stage

Current block

Memory address

Transfer speed

Elapsed time

Remaining time

Retries

Verification status

Example

```
Programming

62%

Block

128 / 203

Address

0x001B4A00

Speed

2.41 MB/s

ETA

00:01:18
```

---

# Timeline View

Long-running operations use a timeline.

```
Prepare

✓

↓

Connect

✓

↓

Unlock

✓

↓

Erase

✓

↓

Program

●

↓

Verify

○

↓

Complete

○
```

Completed stages remain visible.

---

# Live Metrics

Numeric values should

Update smoothly

Avoid width changes

Maintain alignment

Use tabular figures

Never flicker.

---

# Trend Indicators

Where appropriate, telemetry should indicate direction.

Examples

Battery

↑ Rising

→ Stable

↓ Falling

Transfer Speed

↑ Increasing

↓ Decreasing

CPU Usage

Trend line

Small trend indicators reduce interpretation effort.

---

# Graphs

Graphs are appropriate for

RPM

Pressure

Temperature

Boost

Lambda

Voltage over time

Requirements

60 FPS rendering

Zoom

Pan

Pause

Export

Cursor inspection

---

# Gauges

Use gauges sparingly.

Appropriate

Battery Voltage

Fuel Pressure

Boost

Inappropriate

Progress

Memory Address

Retry Count

Tables often communicate engineering values more effectively.

---

# CAN Bus Telemetry

Display

Bus Load

RX Rate

TX Rate

Frame Count

Dropped Frames

Error Frames

Latency

Filters

Users should be able to identify communication problems immediately.

---

# UDS Telemetry

Display

Current Service

Response Time

Negative Responses

Retries

Session

Security Level

Sequence Number

Raw and decoded representations should be available.

---

# Memory Telemetry

During reading or programming display

Memory Region

Address

Current Block

Bytes Written

Checksum Progress

Verification Progress

Users should always understand where the operation is occurring.

---

# Background Tasks

Background operations remain visible.

Display

Task Name

Progress

Status

Completion

Errors

Never hide active background work.

---

# Logging Integration

Telemetry integrates with logs.

Users should be able to navigate from

Metric

↓

Related Log Entry

↓

Detailed Diagnostics

Context should never be lost.

---

# Refresh Rates

Recommended update frequencies

Battery Voltage

2 Hz

Transfer Speed

5 Hz

Progress

10 Hz

CAN Counters

10 Hz

Graphs

30–60 Hz

Status Indicators

On Change

Avoid excessive refresh rates that create visual noise.

---

# Data Smoothing

Rapidly changing values may be smoothed where appropriate.

Suitable

Voltage

Transfer Speed

CPU Usage

Not suitable

Error Count

Security State

Programming Stage

Users must never be misled.

---

# Historical Data

Allow users to review

Voltage history

Programming history

Performance metrics

Connection quality

Flash duration

Verification results

Historical information supports troubleshooting.

---

# Alerts

Telemetry generates alerts based on thresholds.

Examples

Battery < 12.0 V

Programming speed unusually low

Retry count increasing

Communication timeout

High bus load

Alerts should explain

Current condition

Impact

Recommended action

---

# Accessibility

Telemetry must support

High contrast

Screen readers

Keyboard navigation

Reduced motion

Color-independent communication

Critical values must remain readable under all supported themes.

---

# Performance Requirements

Status updates

<100 ms latency

Graph rendering

60 FPS

Telemetry panel updates

Smooth

Memory usage

Stable during long sessions

No dropped frames caused by UI rendering.

---

# Review Checklist

Every telemetry element should answer

✓ Does it improve operator awareness?

✓ Is it actionable?

✓ Is it readable at a glance?

✓ Does it avoid unnecessary noise?

✓ Is it updated at an appropriate frequency?

✓ Does it remain stable visually?

✓ Does it support accessibility?

✓ Can it assist troubleshooting?

✓ Does it reinforce confidence?

---

# Anti-Patterns

Never

Animate values excessively

Blink telemetry continuously

Hide critical metrics

Display inconsistent precision

Change layout as values update

Use decorative gauges unnecessarily

Refresh faster than users can interpret

Present unexplained technical values

Depend solely on color for status

---

# Future Expansion

The telemetry system is designed to support

- Multiple simultaneous ECUs
- Ethernet diagnostics (DoIP)
- Remote programming
- Cloud synchronization
- Hardware oscilloscopes
- External sensors
- Plugin-defined telemetry
- User-configurable dashboards

without changing the underlying hierarchy or interaction model.

---

# Final Principle

Telemetry exists to replace uncertainty with understanding.

Every value shown on screen should help the operator answer one of three questions:

- Is the system healthy?
- Is the operation progressing as expected?
- Do I need to take action?

If a telemetry element cannot answer one of those questions, it should not be displayed.

PythonFlasher should communicate continuously, calmly, and accurately—allowing engineers to focus on the vehicle while the software quietly reports everything that matters.
