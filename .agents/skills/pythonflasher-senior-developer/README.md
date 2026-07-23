# PythonFlasher Senior Developer Skill

A reusable OpenCode Agent Skill for developing, reviewing, testing, and improving the PythonFlasher ECU diagnostic and flashing project.

## Included

- `SKILL.md` contains the complete skill, persona, architecture rules, development workflow, safety requirements, review format, and testing strategy.
- This `README.md` contains installation and activation instructions.

## Install for one project

Copy the complete `pythonflasher-senior-developer` folder into:

```text
<your-project>/.opencode/skills/pythonflasher-senior-developer/
```

Expected result:

```text
<your-project>/
└── .opencode/
    └── skills/
        └── pythonflasher-senior-developer/
            ├── SKILL.md
            └── README.md
```

## Install globally

Copy the folder into:

```text
~/.config/opencode/skills/pythonflasher-senior-developer/
```

## Example usage

```text
Use pythonflasher-senior-developer to perform a deep architecture, safety,
stability, and performance review of this repository.
```

```text
Use pythonflasher-senior-developer to implement a production-grade J2534
adapter while preserving the existing Kvaser integration.
```

```text
Use pythonflasher-senior-developer to audit the EDC16C39 flashing workflow
against the supplied CAN traces and firmware files.
```

## Notes

The skill is designed to be evidence-driven. ECU-specific addresses, security algorithms, routines, checksums, and programming behavior must not be treated as verified unless supported by documentation, traces, known-answer tests, or bench validation.
