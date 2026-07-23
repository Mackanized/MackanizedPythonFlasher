# PythonFlasher Design System

# 09 — Screen Specifications

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

---

# Purpose

This document defines every primary workspace within PythonFlasher.

Each screen specification describes

- Purpose
- Users
- Primary tasks
- Required information
- Layout
- Components
- Navigation
- Keyboard interaction
- Performance expectations
- Acceptance criteria

Screens are task-oriented.

Users should never navigate because of application structure.

They navigate because their engineering task changes.

---

# Application Structure

```
PythonFlasher

├── Dashboard
├── Connection Manager
├── Vehicle Workspace
├── ECU Identification
├── Diagnostics
├── Live Data
├── Calibration Explorer
├── Calibration Editor
├── Memory Explorer
├── Read ECU
├── Write ECU
├── Recovery
├── Security Access
├── CAN Trace
├── UDS Console
├── Flash History
├── Project Manager
├── Device Manager
├── Settings
├── Help
└── About
```

Every screen belongs to a logical engineering workflow.

---

# Screen Architecture

Every workspace follows the same structure.

```
Window Header

↓

Toolbar

↓

Workspace

↓

Inspector

↓

Status Bar
```

Users should never need to relearn layouts.

---

# Dashboard

## Purpose

Provide immediate operational awareness.

Not a marketing dashboard.

Not analytics.

A starting point for engineering work.

---

## Contains

Recent projects

Connected adapter

Recent vehicles

Recent ECUs

Recent flash history

Warnings

Software updates

Quick actions

---

## Quick Actions

Connect Adapter

Read ECU

Write ECU

Open Project

Recover ECU

Diagnostics

---

# Connection Manager

## Purpose

Manage physical communication.

---

## Displays

Available adapters

Connection status

Firmware version

Supported protocols

Driver status

Voltage

Bus speed

Connection log

---

## Actions

Connect

Disconnect

Refresh

Configure

Diagnostics

Firmware Update

---

# Vehicle Workspace

## Purpose

Represent the currently connected vehicle.

---

## Displays

VIN

Model

Platform

Engine

Transmission

Mileage

Battery voltage

Detected ECUs

Gateway topology

---

# ECU Identification

## Purpose

Identify every connected controller.

---

## Displays

Address

Name

Hardware Number

Software Number

Calibration

Bootloader

Supplier

Flash Memory

EEPROM

Protocol

Security Level

---

Supports

Sorting

Filtering

Search

Export

---

# Diagnostics

## Purpose

Read and manage Diagnostic Trouble Codes.

---

## Displays

Active DTCs

Stored DTCs

Pending DTCs

Freeze Frame

Descriptions

Severity

Status

Manufacturer information

---

## Actions

Read

Clear

Export

Print

Copy

---

# Live Data

## Purpose

Real-time telemetry.

---

Supports

Tables

Graphs

Gauges

Logging

Recording

Filtering

Search

Favorites

---

Common Signals

RPM

Boost

Fuel Pressure

Coolant Temperature

Throttle

Lambda

Battery Voltage

Torque

Rail Pressure

---

# Calibration Explorer

## Purpose

Browse all calibration objects.

---

Displays

Folders

Maps

Scalars

Curves

Switches

Functions

Categories

Search

Favorites

History

---

# Calibration Editor

## Purpose

Edit calibration data safely.

---

Supports

2D

3D

Hex

Table

Difference View

Overlay

Undo

Redo

Bookmarks

History

Validation

---

# Memory Explorer

## Purpose

Visualize ECU memory.

---

Displays

Flash

EEPROM

RAM

Checksum

Segments

Boot

Calibration

Code

Supports

Zoom

Selection

Bookmarks

Export

Hex view

---

# Read ECU

## Purpose

Safely acquire ECU contents.

---

Workflow

Prepare

↓

Connect

↓

Security Access

↓

Read

↓

Verify

↓

Save

↓

Complete

---

Displays

Progress

Address

Voltage

Transfer speed

ETA

Retries

Current service

---

# Write ECU

## Purpose

Safely program ECU.

---

Workflow

Validate

↓

Backup

↓

Unlock

↓

Erase

↓

Program

↓

Verify

↓

Checksum

↓

Complete

---

Shows

Risk level

Voltage

Progress

Current block

Remaining time

Recovery guidance

---

# Recovery

## Purpose

Recover interrupted programming.

---

Supports

Boot Mode

Recovery Flash

Restore Backup

Emergency Programming

Communication Diagnostics

---

Displays

Recovery progress

Boot state

Detected ECU

Recovery log

---

# Security Access

## Purpose

Perform authenticated ECU operations.

---

Displays

Security level

Current session

Seed

Key status

Algorithm

Attempts

---

Supports

Read Seed

Calculate Key

Unlock

Relock

History

---

# CAN Trace

## Purpose

Capture and inspect network traffic.

---

Supports

Filtering

Search

Pause

Bookmarks

Export

Highlighting

Timestamp precision

---

Displays

Timestamp

Identifier

Direction

Length

Payload

Decoded signal

Raw payload

---

# UDS Console

## Purpose

Manual diagnostic communication.

---

Supports

Service selection

Raw commands

Saved requests

History

Macros

Response decoding

Copy

Export

---

# Flash History

## Purpose

Provide complete audit trail.

---

Displays

Date

Vehicle

VIN

Calibration

Operator

Duration

Checksum

Verification

Result

---

Supports

Search

Filtering

Export

Compare

---

# Project Manager

## Purpose

Manage engineering projects.

---

Displays

Projects

Vehicles

Files

History

Backups

Calibration versions

Notes

---

Supports

Versioning

Search

Tagging

Favorites

---

# Device Manager

## Purpose

Manage hardware.

---

Displays

Connected adapters

Firmware

Licensing

Drivers

Health

Supported protocols

---

# Settings

Organized into categories.

General

Appearance

Workspace

Diagnostics

Adapters

Logging

Performance

Accessibility

Advanced

Developer

---

# Help

Contains

Documentation

Keyboard shortcuts

Tutorials

Release notes

Support

Logs

Diagnostic package

---

# About

Displays

Version

Build

Git commit

License

Dependencies

Credits

Support information

---

# Shared Screen Requirements

Every screen must provide

Consistent toolbar

Persistent status bar

Keyboard navigation

Search where appropriate

Context menu

Undo where possible

Help entry

Accessible labels

High DPI support

---

# Screen Performance Targets

Workspace load

<300 ms

Workspace switch

<180 ms

Table rendering

<100 ms

Graph updates

60 FPS

Dialogs

<180 ms

Toolbar response

<50 ms

---

# Screen Persistence

Remember

Splitter positions

Dock layout

Window size

Filters

Sorting

Open tabs

Zoom

Inspector width

Last project

---

# Accessibility

Every screen supports

Keyboard navigation

Screen readers

High contrast

Reduced motion

200% DPI

Logical focus order

No information communicated solely through color

---

# Screen Review Checklist

Every screen must answer

✓ Is the primary task immediately obvious?

✓ Is the main action visible without scrolling?

✓ Does the screen preserve workflow context?

✓ Does it minimize cursor movement?

✓ Does it expose keyboard shortcuts?

✓ Does it scale from Full HD to 4K?

✓ Does it remain usable after hours of continuous work?

✓ Does it support accessibility requirements?

✓ Does it reinforce operator confidence?

---

# Future Screens

Future additions should integrate without changing the application's navigation model.

Examples

Bench Mode

J2534 Analyzer

Seed-Key Analyzer

Firmware Comparison

Bootloader Explorer

A2L Explorer

OLS Converter

Calibration Validator

Scripting

Plugin Marketplace

Remote Diagnostics

---

# Final Principle

Every screen exists to complete a professional engineering task.

Screens are not destinations.

They are workspaces.

Users should transition naturally between them without losing context, focus, or confidence.

The application should feel like a single, coherent engineering environment rather than a collection of separate tools.
