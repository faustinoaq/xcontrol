<p><img src="assets/logo.svg" alt="xcontrol mascot: a mint terminal creature with four arms" width="128"></p>

# xcontrol

A small wrapper around tmux that opens and resumes your CLI agent sessions, including Codex, Copilot and Claude and lets agents communicate with each other. Start with `xc .` to get help setting up a project, or define the folders and agents in one `.agents` file and open it:

```sh
xc myapp.agents
```

![xcontrol running Android, iOS, and server agents in tmux](assets/myapp-tmux.png)

A real tmux capture using the `myapp` folders with three Codex sessions. The example prompts are typed but have not been submitted. You can mix CLI agents in the same group, as shown below.

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

## Start without a config file

```sh
cd ~/code/myapp
xc .
# Or simply: xc
```

xcontrol checks installed Codex, Copilot, and Claude in that order, using the same small access probes as `agent = "auto"`. It opens one setup agent in tmux and submits a starter prompt to inspect the project, find installed CLIs, and suggest folders and roles for an `.agents` file. The prompt asks it to confirm the proposed team with you before writing the file. Custom CLIs can be added to the resulting file explicitly.

The temporary setup configuration lives under `${XDG_STATE_HOME:-~/.local/state}/xcontrol/quickstart`, outside your project. No project config is written by the launcher. Run `xc .` again to reattach; use `xc status .` or `xc stop .` to inspect or close this setup group. Stopping and reopening starts a fresh setup conversation and checks access again. For normal project work, launch the `.agents` file you create together.

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

Folders resolve relative to the `.agents` file, not your terminal directory. Absolute paths and `~` also work. Each agent has a unique ID, its own working directory, CLI executable name, and optional role and argument list. Up to 16 agents fit in a tiled layout; terminal size limits how many are practical.

Optional `resume = "auto"` is the default: Codex resumes its latest unarchived interactive CLI thread for that exact directory, using read-only local SQLite metadata. Claude uses its native `--continue` in that directory. Copilot uses a stable workspace-specific native `--session-id`, creating or resuming its xcontrol conversation without selecting an unrelated global session. `resume = "new"` starts fresh; a session UUID resumes an explicit native conversation. Histories are not converted between CLIs. If Codex's metadata is unavailable, it starts fresh with a warning.

Optional `prompt = "..."` submits an initial instruction for Codex, Copilot, or Claude when paired with `resume = "new"`. For auto selection, all candidates must be one of those three. This is separate from the displayed role.

The CLI inherits your normal permissions, model, and authentication. No permission bypass options are added. Roles are printed in each pane; they are **not automatically sent as prompts**. The `agent` field names an executable on your PATH, and optional `args` are passed as literal arguments. xcontrol does not evaluate shell syntax. Use configuration files you trust: launching an agent runs that executable with your normal account access.

## Automatic agent selection

Use `agent = "auto"` to select the first installed candidate with working model access when opening a new group:

```toml
name = "myapp"

[[agents]]
id = "server"
folder = "./myapp-server"
agent = "auto"
candidates = ["codex", "copilot", "claude"]
role = "Backend services and shared APIs."
```

The default candidate order is Codex, Copilot, then Claude. Missing and failed candidates are skipped. If none confirms access, xcontrol opens no panes. `xc availability myapp.agents` runs the same checks; **it makes small model calls**. `xc check` only validates configuration and makes no calls.

For Codex, Copilot, and Claude, xcontrol sends a tiny prompt asking for `XCONTROL_OK` through `codex exec`, `copilot -p`, or `claude -p`. It requires both a successful exit and the actual model answer. A failed probe is retried once, including authorization failures that can be temporary. Results are cached per provider for one launch, so multiple panes do not repeat the same checks. Each attempt has a 30-second timeout. Reattaching makes no calls.

Probes run in a temporary directory, outside your project folders, without resuming your work conversations. Claude and Copilot tools are disabled for the probe; Codex uses its read-only sandbox. Installed CLI configuration is trusted, including any user-configured integrations. These checks consume a little usage and may incur charges under your existing provider billing settings. They use the CLI's default model selection, without forcing a premium model or changing billing settings. A successful probe confirms access at that moment, not how much quota remains or access to every model. A failed check only skips that provider for this launch; it does not diagnose a permanent subscription problem.

Other CLIs can use a trusted custom checker in `[availability]`, which also overrides a built-in probe:

```toml
[availability]
devin = ["my-access-check", "devin"]
```

`my-access-check` is an example external command, not bundled. Place this table before your first `[[agents]]`. It must exit **0** for available, **1** for unavailable, or **2** for unknown. Other errors and timeouts count as unknown. Custom checkers run once per provider as literal arguments, from the configuration directory, with a five-second timeout and suppressed output. They are not automatically retried. Trust them as you would any program running under your account; xcontrol does not sandbox custom checkers.

Noninteractive commands for custom checkers include [Devin's `devin -p`](https://docs.devin.ai/cli/reference/commands), [Gemini's `gemini -p`](https://geminicli.com/docs/cli/headless/), and [OpenCode's `opencode run`](https://opencode.ai/docs/cli/). A checker should also validate a model answer and restrict tools appropriately; merely invoking a CLI or checking login status does not prove model access.

The chosen CLI appears in the pane title and `xc status`. Auto agents accept `resume = "auto"` or `"new"`; custom candidates start fresh. CLI-specific arguments and explicit session UUIDs require selecting that CLI explicitly. Reattaching keeps the existing selection. There is no mid-task failover or conversation transfer between providers; stop and reopen the group to select again.

## Other CLI agents, including Devin

Any interactive CLI agent on your PATH can run in a pane. Codex, Copilot, and Claude have built-in resume handling. Other agents use the executable and arguments you provide.

For example, [Devin CLI](https://docs.devin.ai/cli) starts locally with `devin`. To use it for the server, replace the server entry with:

```toml
[[agents]]
id = "server"
folder = "./myapp-server"
agent = "devin"
args = []
role = "Backend services; coordinate API contracts with android and ios."
```

Install and authenticate the CLI separately. Custom agents default to `resume = "new"`; xcontrol does not guess their session flags. To resume a conversation, set `args` to that CLI's documented resume arguments. Arguments are passed directly, without a shell, environment-variable expansion, or command substitution. Optional `args` also work with the three built-in agents.

The same `xc status` and `xc send` commands work with custom agents that accept terminal text input. Prompt submission and busy-state behavior depend on the CLI; xcontrol does not provide agent-specific readiness detection. Devin's launch command is documented by its vendor; the generic launcher is tested with a simulated executable, not a live Devin account.

## Commands

```sh
xc                               # setup agent in the current directory
xc ./myapp                       # setup agent in another directory
xc check myapp.agents             # validate without launching CLIs
xc availability myapp.agents      # test model access (uses a small prompt)
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

## Agent cannot find a visible group

`xc status` and `xc send` need access to the local tmux Unix socket. A CLI can be visible in a pane while its sandboxed shell commands are denied access to that socket. xcontrol reports this as **Cannot access the tmux socket**, rather than claiming the group has stopped.

Run `xc status myapp.agents` from your normal terminal to distinguish a stopped group from an agent permission restriction. If it works there but fails inside the agent, inspect that CLI's local socket permissions. Codex supports explicit [Unix socket permissions](https://learn.chatgpt.com/docs/permissions#unix-sockets), subject to your version and managed policy. Allowing a tmux socket grants control over that tmux server, so choose that access explicitly. xcontrol does not change sandbox permissions automatically. Do not restart working agents merely because a sandbox cannot query tmux.

## Related tools

There are many ways to run multiple coding agents. These projects include graphical interfaces, terminal workspaces, and agent managers. Their scope varies; the table identifies what each one provides.

| Tool | What it provides |
| --- | --- |
| [T3 Code](https://github.com/pingdotgg/t3code) | A graphical interface for working with coding agents |
| [Herdr](https://github.com/herdrdev/herdr) | An agent-aware terminal runtime and workspace manager |
| [tmux](https://github.com/tmux/tmux) | Persistent terminal sessions and panes; xcontrol uses it underneath |
| [Zellij](https://github.com/zellij-org/zellij) | A terminal workspace and multiplexer |
| [WezTerm](https://github.com/wezterm/wezterm) | A terminal emulator with multiplexing |
| [cmux](https://github.com/manaflow-ai/cmux) | A macOS terminal with workspaces and agent notifications |
| [Vibe Kanban](https://github.com/BloopAI/vibe-kanban) | A board-based interface for organizing coding agent work |
| [Claude Squad](https://github.com/smtg-ai/claude-squad) | A terminal manager for multiple coding agents |
| [Agent of Empires](https://github.com/agent-of-empires/agent-of-empires) | A tmux-based agent manager with terminal and web interfaces |
| [workmux](https://github.com/raine/workmux) | Git worktrees and tmux windows for parallel agent tasks |
| [dmux](https://github.com/standardagents/dmux) | A multiplexer for coding agents and Git worktrees |
| [Agent Deck](https://github.com/asheshgoplani/agent-deck) | A terminal session manager for coding agents |

Additional UI options include [Conductor](https://www.conductor.build/) and [Rex](https://www.superlogical.com/rex/).

xcontrol fits a simple existing setup: tmux is already installed, your agent CLIs are authenticated, and you want to reopen a project's sessions and let agents communicate through a small wrapper.

## Development

```sh
python3 -m unittest discover -s tests -v
```

Tests launch isolated tmux servers with fake agent executables and model responses; they make no model calls and do not access production services.

MIT licensed.
