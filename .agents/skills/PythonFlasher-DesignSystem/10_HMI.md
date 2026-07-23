# PythonFlasher Design System

# 10 — Human–Machine Interface (HMI)

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
- 09 — Screen Specifications

---

# Purpose

This document defines the Human–Machine Interface (HMI) principles governing PythonFlasher.

Unlike visual design guidelines, HMI focuses on the relationship between the operator and the system.

The objective is to

- reduce operational mistakes
- increase operator confidence
- improve situational awareness
- reduce cognitive workload
- improve recovery from failures
- support safe ECU programming

The interface itself is considered a safety mechanism.

---

# HMI Philosophy

PythonFlasher should behave like professional industrial equipment.

Every interaction should answer three questions before the user asks them.

**Where am I?**

**What is happening?**

**What should I do next?**

Uncertainty is considered a usability defect.

---

# Human Factors Principles

PythonFlasher adopts established human factors principles commonly used in aviation, industrial automation and automotive diagnostic tools.

Core principles include

- Recognition over recall
- Visibility of system status
- Progressive disclosure
- Error prevention
- Error recovery
- Consistency
- Low cognitive load
- Predictable interaction
- Immediate feedback
- Stable spatial organization

These principles apply to every workflow.

---

# Situational Awareness

Operators should always know the current state of the system.

The following information should remain continuously available whenever an ECU is connected.

- Vehicle
- VIN
- ECU name
- ECU address
- Current session
- Security level
- Adapter
- Protocol
- Bus status
- Battery voltage
- Current operation
- Progress
- Connection health

Users should never navigate to another screen to determine operational state.

---

# Operational Modes

PythonFlasher supports multiple modes of operation.

## View Mode

Read-only.

No changes permitted.

Safe for demonstrations and inspections.

---

## Diagnostics Mode

Read and clear DTCs.

Read live data.

Read ECU information.

Programming unavailable.

---

## Calibration Mode

View and edit calibration data.

No programming until validation succeeds.

---

## Programming Mode

High-risk.

Programming operations enabled.

Safety checks become mandatory.

---

## Recovery Mode

Dedicated recovery workspace.

Minimal distractions.

Recovery guidance always visible.

---

## Developer Mode

Advanced diagnostics.

Raw communication.

Protocol inspection.

Internal tools.

Clearly separated from normal workflows.

---

# Cognitive Load

The interface should never force operators to remember information.

Instead it should continuously present relevant context.

Avoid

Remembering addresses

Remembering security levels

Remembering voltage limits

Remembering workflow stages

Display them instead.

---

# Workflow Visibility

Every long-running workflow should expose each stage.

Example

```
Prepare

↓

Connect

↓

Read ECU Information

↓

Security Access

↓

Erase Flash

↓

Program

↓

Verify

↓

Checksum

↓

Complete
```

The current stage should always be highlighted.

Completed stages remain visible.

---

# Operator Confidence

Confidence is increased through continuous feedback.

Programming should continuously display

Battery voltage

Elapsed time

Remaining time

Current address

Transfer speed

Current block

Retry count

Communication status

Verification status

Users should never wonder if the application is still working.

---

# Error Prevention

The best error is the one that never occurs.

The interface should prevent

Writing the wrong file

Programming the wrong ECU

Programming unsupported firmware

Unsafe battery voltage

Loss of communication

Accidental erase

Unsafe recovery attempts

Prevent errors before they occur.

---

# Validation Gates

High-risk operations require validation.

Example

```
Vehicle detected

↓

ECU identified

↓

Calibration verified

↓

Compatibility confirmed

↓

Voltage acceptable

↓

Backup available

↓

Programming enabled
```

Programming should not begin if mandatory validation fails.

---

# Confirmation Philosophy

Confirmation dialogs are reserved for irreversible actions.

Do not ask

"Are you sure?"

Instead explain

What will happen

Estimated duration

Potential risks

Recovery options

Backup availability

Example

```
Write Calibration

Vehicle

Saab 9-3 Aero

ECU

Bosch ME9.6.1

Calibration

Stage2.bin

Estimated Time

3 min 48 sec

Battery

13.92 V

Backup

Available

[Write ECU]

[Cancel]
```

---

# Safety States

Every operation exists in one of five states.

Idle

Preparing

Running

Paused

Completed

Failed

Transitions between states should always be visible.

---

# Communication Awareness

The user should continuously understand communication quality.

Display

Bus load

Retries

Timeouts

Dropped frames

Connection quality

Protocol

Latency

Communication problems should never appear suddenly.

---

# Live Telemetry

Critical telemetry remains persistent.

Examples

Battery voltage

Current draw (if available)

Transfer speed

Memory address

Flash block

Temperature (if available)

Retries

Current UDS service

---

# Alarm Hierarchy

Alerts are prioritized.

Level 1

Information

No action required.

---

Level 2

Warning

Action recommended.

Programming may continue.

---

Level 3

Critical

Programming should pause or stop safely.

Immediate operator attention required.

---

# Error Recovery

Failures should immediately answer

What happened?

Why?

Can programming continue?

What should I do next?

What logs are available?

Every failure should include actionable recovery guidance.

---

# Visual Stability

Layouts should remain stable.

Avoid

Moving controls

Changing navigation

Unexpected dialogs

Jumping progress bars

Changing button locations

Muscle memory is a safety feature.

---

# Attention Management

The interface controls operator attention.

Primary attention

Current operation

Secondary attention

Telemetry

Background attention

Logs

Notifications

Never compete for attention unnecessarily.

---

# Color in Safety

Color reinforces—not replaces—information.

Critical states include

Icon

Label

Description

Recommended action

Never rely solely on red.

---

# Motion in Safety

Motion communicates change.

Never urgency.

Avoid

Blinking

Flashing

Rapid movement

Use subtle emphasis.

Persistent warnings outperform distracting animations.

---

# Multi-Monitor Operation

Support professional workshop environments.

Recommended layouts

Monitor 1

Programming

Monitor 2

Logs

Monitor 3

CAN trace

Window layouts persist.

---

# Recovery Workflows

Recovery screens should reduce cognitive load.

Hide unnecessary controls.

Focus on

Current state

Recovery steps

Progress

Logs

Recovery options

---

# Accessibility

HMI principles apply equally to accessibility.

Support

Keyboard-only workflows

Reduced motion

High contrast

Screen readers

Large fonts

Color-independent communication

---

# Performance Expectations

Every interaction should reinforce confidence.

Target response times

Hover

<16 ms

Button

<50 ms

Workspace switch

<180 ms

Progress updates

Continuous

Telemetry refresh

Smooth and stable

The interface must never appear frozen during ECU operations.

---

# HMI Review Checklist

Every workflow should answer

✓ Is the current state always visible?

✓ Is the next action obvious?

✓ Are dangerous operations protected?

✓ Is enough context available without navigation?

✓ Can mistakes be prevented?

✓ Can failures be recovered?

✓ Does the interface reduce cognitive effort?

✓ Does the layout remain spatially stable?

✓ Is operator confidence continuously reinforced?

✓ Would this workflow be suitable for daily professional use?

---

# HMI Anti-Patterns

Never

Hide critical telemetry

Require memorization

Display generic error messages

Interrupt programming with unnecessary dialogs

Move controls between screens

Depend solely on color

Animate warnings excessively

Hide communication failures

Require unnecessary confirmations

Force users to search for operational status

---

# Guiding Principle

PythonFlasher is not merely software.

It is the primary interface between an engineer and a safety-critical electronic control unit.

Every interaction should increase understanding.

Every workflow should reduce uncertainty.

Every screen should reinforce confidence.

The best HMI is one that quietly supports the operator, allowing them to focus entirely on the engineering task while the software continuously communicates the information needed to make safe, informed decisions.
