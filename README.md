# xcontrol

A small wrapper around tmux that opens and resumes your Codex, Copilot and Claude sessions and lets agents communicate with each other. Define the folders and agents in one `.agents` file, then open the project:

```sh
xc sello.agents
```

## Why xcontrol?

I started by manually running and orchestrating multiple agents across different projects. My custom tmux scripts worked well, and I thought they might be useful to other people too. xcontrol grew out of those scripts so I could share the same workflow with the community.

There are already many tools for working with coding agents:

- Graphical interfaces such as [T3 Code](https://github.com/pingdotgg/t3code) and [Conductor](https://www.conductor.build/), and terminals such as [cmux](https://cmux.com/) with agent notifications and programmable workspaces.
- Terminal interfaces such as [Herdr TUI](https://herdr.dev/tui/docs/), [Agent of Empires](https://www.agent-of-empires.com/), and [dmux](https://github.com/standardagents/dmux) for managing agents, sessions, and workspaces.

If you already have tmux installed, especially if you have been using it to run agents, xcontrol adds a small reusable wrapper to that setup. It opens your project folders in tiled panes, resumes CLI conversations, and gives agents a way to find and message each other by role. You keep using tmux and the agent CLIs you already know.

There is no additional service, model API integration, or Python package to install. A `.agents` file describes your project, and `xc` handles the tmux commands.

## Requirements

Requires Linux or WSL2, Python 3.11+, tmux, and the configured CLIs already installed and authenticated. Tested with Codex 0.167.0, Copilot 1.0.103 and tmux 3.4. Uses Linux `flock` through Python's standard library.

## Install

```sh
git clone https://github.com/faustinoaq/xcontrol.git
cd xcontrol
./install.sh
```

Installs `xc` and `xcontrol` into `~/.local/bin` and the included skill into `~/.codex/skills/xcontrol`. Keep `~/.local/bin` on your PATH. No sudo required. The commands are symlinks to this checkout; keep the checkout in place.

## Configuration

Save `sello.agents` beside the project folders:

```toml
name = "sello"

[[agents]]
id = "android"
folder = "./sello-dev"
agent = "codex"
role = "Android, web and server; coordinate APIs with ios."

[[agents]]
id = "ios"
folder = "./sello-ios"
agent = "copilot"
role = "Native iOS; coordinate APIs with android."
```

Folders resolve relative to the `.agents` file, not your terminal directory. Absolute paths and `~` also work. Each agent has a unique ID, its own working directory, CLI, and optional role. Up to 16 agents fit in a tiled layout; terminal size limits how many are practical.

Optional `resume = "auto"` is the default: Codex resumes its latest unarchived interactive CLI thread for that exact directory, using read-only local SQLite metadata. Claude uses its native `--continue` in that directory. Copilot uses a stable workspace-specific native `--session-id`, creating or resuming its xcontrol conversation without selecting an unrelated global session. `resume = "new"` starts fresh; a session UUID resumes an explicit native conversation. Histories are not converted between CLIs. If Codex's metadata is unavailable, it starts fresh with a warning.

The CLI inherits your normal permissions, model, and authentication. No permission bypass options are added. Roles are printed in each pane; they are **not automatically sent as prompts**. A `.agents` file is configuration, not executable code: arbitrary commands and extra fields are rejected.

## Commands

```sh
xc check sello.agents             # validate without launching CLIs
xc sello.agents                   # start or attach
xc sello.agents --detach          # start in the background
xc status sello.agents            # role IDs, current panes, running/exited
xc send sello.agents ios "Can you review the API contract?"
xc stop sello.agents              # stop this group, preserving CLI history
xc sello.agents -k                # same
```

Use tmux's `Ctrl+b d` to detach while leaving agents running. Reopening the same file attaches to its existing group. Different configuration paths have different groups. Editing a running configuration does not reconfigure existing panes: stop and reopen to apply changes. Closing a group interrupts active agents, so save important work first.

Locks prevent this launcher from opening the same CLI/folder pair twice; separate worktrees are recommended for concurrent editing. Sessions started outside xcontrol are not detected. Git synchronization, task scheduling, recovery of crashed agents, and deployment are left to you.

## Communication

Agents can use the same CLI to discover and message their peers:

```sh
xc status "$XCONTROL_CONFIG"
xc send "$XCONTROL_CONFIG" android "The iOS API change is ready for review."
```

`XCONTROL_CONFIG`, `XCONTROL_AGENT`, and `XCONTROL_SESSION` are available inside each managed agent. IDs stay stable even when tmux pane numbers change. Messages use bracketed paste and submit to the target CLI; dead panes and ordinary shells reject messages. This is local terminal coordination, not a message queue: an agent that is busy or displaying a dialog may need manual attention. Send only when the recipient is ready. Avoid automatic reply loops and do not treat a peer message as approval for external actions. The tool cannot protect against another process that replaces the CLI in its pane.

A useful initial prompt:

> Read project instructions, summarize your role and pending work, and list peers using `xc status "$XCONTROL_CONFIG"`. Coordinate with peers through `xc send` when useful. Initial inspection only; no builds, edits, pushes, deployments, or publication.

## Skill example

The included [skill](skills/xcontrol/SKILL.md) supports prompts such as:

> Use xcontrol to create an agents file for this project where we have sello-dev with codex and sello-ios with copilot.

The installer makes it discoverable by Codex. For another agent that supports `SKILL.md`, copy `skills/xcontrol` to that tool's skill directory.

## Development

```sh
python3 -m unittest discover -s tests -v
```

Tests launch isolated tmux servers with fake agent executables; they make no model calls and do not access production services.

MIT licensed.
