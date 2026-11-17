# xcontrol

A small wrapper around tmux that opens and resumes your Codex, Copilot and Claude sessions and lets agents communicate with each other. Define the folders and agents in one `.agents` file, then open the project:

```sh
xc myapp.agents
```

## Why xcontrol?

I started by manually running and orchestrating multiple agents across different projects. My custom tmux scripts worked well, and I thought they might be useful to other people too. xcontrol grew out of those scripts so I could share the same workflow with the community.

There are already popular tools for this workflow, including [T3 Code](https://github.com/pingdotgg/t3code), [Herdr](https://herdr.dev/), and [Vibe Kanban](https://github.com/BloopAI/vibe-kanban). Terminal workspaces such as [Zellij](https://zellij.dev/) and [WezTerm](https://wezterm.org/) are also widely used. The [related tools](#related-tools) section lists these and other established options.

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

Save `myapp.agents` beside the project folders:

```text
workspace/
├── myapp.agents
├── myapp-android/
├── myapp-ios/
└── myapp-server/
```

```toml
name = "myapp"

[[agents]]
id = "android"
folder = "./myapp-android"
agent = "codex"
role = "Android app; coordinate API contracts with server."

[[agents]]
id = "ios"
folder = "./myapp-ios"
agent = "copilot"
role = "Native iOS app; coordinate API contracts with server."

[[agents]]
id = "server"
folder = "./myapp-server"
agent = "codex"
role = "Backend services and shared APIs; coordinate changes with android and ios."
```

Folders resolve relative to the `.agents` file, not your terminal directory. Absolute paths and `~` also work. Each agent has a unique ID, its own working directory, CLI, and optional role. Up to 16 agents fit in a tiled layout; terminal size limits how many are practical.

Optional `resume = "auto"` is the default: Codex resumes its latest unarchived interactive CLI thread for that exact directory, using read-only local SQLite metadata. Claude uses its native `--continue` in that directory. Copilot uses a stable workspace-specific native `--session-id`, creating or resuming its xcontrol conversation without selecting an unrelated global session. `resume = "new"` starts fresh; a session UUID resumes an explicit native conversation. Histories are not converted between CLIs. If Codex's metadata is unavailable, it starts fresh with a warning.

The CLI inherits your normal permissions, model, and authentication. No permission bypass options are added. Roles are printed in each pane; they are **not automatically sent as prompts**. A `.agents` file is configuration, not executable code: arbitrary commands and extra fields are rejected.

## Commands

```sh
xc check myapp.agents             # validate without launching CLIs
xc myapp.agents                   # start or attach
xc myapp.agents --detach          # start in the background
xc status myapp.agents            # role IDs, current panes, running/exited
xc send myapp.agents ios "Can you review the API contract?"
xc stop myapp.agents              # stop this group, preserving CLI history
xc myapp.agents -k                # same
```

Use tmux's `Ctrl+b d` to detach while leaving agents running. Reopening the same file attaches to its existing group. Different configuration paths have different groups. Editing a running configuration does not reconfigure existing panes: stop and reopen to apply changes. Closing a group interrupts active agents, so save important work first.

Locks prevent this launcher from opening the same CLI/folder pair twice; separate worktrees are recommended for concurrent editing. Sessions started outside xcontrol are not detected. Git synchronization, task scheduling, recovery of crashed agents, and deployment are left to you.

## Communication

Agents can use the same CLI to discover and message their peers:

```sh
xc status "$XCONTROL_CONFIG"
xc send "$XCONTROL_CONFIG" server "Can you confirm the API contract for Android and iOS?"
```

`XCONTROL_CONFIG`, `XCONTROL_AGENT`, and `XCONTROL_SESSION` are available inside each managed agent. IDs stay stable even when tmux pane numbers change. Messages use bracketed paste and submit to the target CLI; dead panes and ordinary shells reject messages. This is local terminal coordination, not a message queue: an agent that is busy or displaying a dialog may need manual attention. Send only when the recipient is ready. Avoid automatic reply loops and do not treat a peer message as approval for external actions. The tool cannot protect against another process that replaces the CLI in its pane.

A useful initial prompt:

> Read project instructions, summarize your role and pending work, and list peers using `xc status "$XCONTROL_CONFIG"`. Coordinate with peers through `xc send` when useful. Initial inspection only; no builds, edits, pushes, deployments, or publication.

## Skill example

The included [skill](skills/xcontrol/SKILL.md) supports prompts such as:

> Use xcontrol to create an agents file for this project with myapp-android using Codex, myapp-ios using Copilot, and myapp-server using Codex.

The installer makes it discoverable by Codex. For another agent that supports `SKILL.md`, copy `skills/xcontrol` to that tool's skill directory.

## Related tools

There are many ways to run multiple coding agents. These projects include graphical interfaces, terminal workspaces, and agent managers. Their scope varies; the table identifies what each one provides.

Approximate GitHub stars, checked on November 17, 2026. Sorted by star count among the projects listed here. Stars indicate repository popularity, not active usage or a feature ranking, and the counts will change.

| Tool | What it provides | GitHub stars |
| --- | --- | ---: |
| [T3 Code](https://github.com/pingdotgg/t3code) | A graphical interface for working with coding agents | 63.9K |
| [Herdr](https://github.com/herdrdev/herdr) | An agent-aware terminal runtime and workspace manager | 51.6K |
| [tmux](https://github.com/tmux/tmux) | Persistent terminal sessions and panes; xcontrol uses it underneath | 50.5K |
| [Zellij](https://github.com/zellij-org/zellij) | A terminal workspace and multiplexer | 36.1K |
| [WezTerm](https://github.com/wezterm/wezterm) | A terminal emulator with multiplexing | 29.6K |
| [cmux](https://github.com/manaflow-ai/cmux) | A macOS terminal with workspaces and agent notifications | 28.8K |
| [Vibe Kanban](https://github.com/BloopAI/vibe-kanban) | A board-based interface for organizing coding agent work | 28.7K |
| [Claude Squad](https://github.com/smtg-ai/claude-squad) | A terminal manager for multiple coding agents | 8.8K |
| [Agent of Empires](https://github.com/agent-of-empires/agent-of-empires) | A tmux-based agent manager with terminal and web interfaces | 4.6K |
| [workmux](https://github.com/raine/workmux) | Git worktrees and tmux windows for parallel agent tasks | 3.1K |
| [dmux](https://github.com/standardagents/dmux) | A multiplexer for coding agents and Git worktrees | 1.8K |
| [Agent Deck](https://github.com/asheshgoplani/agent-deck) | A terminal session manager for coding agents | 1.3K |

Each project link points to the repository used for its star count. Additional UI options include [Conductor](https://www.conductor.build/) and [Rex](https://www.superlogical.com/rex/).

xcontrol fits a simple existing setup: tmux is already installed, your agent CLIs are authenticated, and you want to reopen a project's sessions and let agents communicate through a small wrapper.

## Development

```sh
python3 -m unittest discover -s tests -v
```

Tests launch isolated tmux servers with fake agent executables; they make no model calls and do not access production services.

MIT licensed.
