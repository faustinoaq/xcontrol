<p><img src="assets/logo.svg" alt="xcontrol mascot" width="128"></p>

# xcontrol

Run your coding agents in tmux. Resume their sessions and let them message each other.

I used to manage agents across projects with a few tmux scripts. They worked well, so I cleaned them up and shared them here.

![Android, iOS, and server agents running in tmux](assets/myapp-tmux.png)

## Install

You'll need Linux or WSL2, Python 3.11+, tmux, and your agent CLIs installed and signed in.

```sh
git clone https://github.com/faustinoaq/xcontrol.git
cd xcontrol
./install.sh
```

Keep `~/.local/bin` on your PATH. The installer links to this checkout, so keep it around.

## Get started

Already have a config? Open it:

```sh
xc myapp.agents
```

Need help creating one? Run this in your project:

```sh
xc .
```

A setup agent looks at your folders and suggests a team. It asks before writing your config. This checks model access with small calls that count toward your usage.

Plain `xc` just shows help.

## A small example

Save `myapp.agents` beside your project folders:

```toml
name = "myapp"

[[agents]]
id = "android"
folder = "./myapp-android"
agent = "codex"
role = "Android app"

[[agents]]
id = "ios"
folder = "./myapp-ios"
agent = "copilot"
role = "iOS app"

[[agents]]
id = "server"
folder = "./myapp-server"
agent = "claude"
role = "Server APIs"
```

Folders are relative to this file. Roles are labels, not prompts. Use separate folders or worktrees when running the same CLI more than once.

Codex, Copilot, and Claude resume conversations by default. Add `resume = "new"` to start fresh. Other CLIs, such as Devin, work too: set `agent` to their executable name and add any flags in `args`.

**Codex runs with approvals and sandboxing disabled by default.** Set `bypass = false` to keep its normal permissions. Other CLIs keep their own defaults.

## Everyday commands

```sh
xc myapp.agents                  # start or reattach
xc status myapp.agents           # see who's running
xc send myapp.agents server "Please review the API changes"
xc stop myapp.agents             # close the group
xc check myapp.agents            # validate the config, no model calls
```

Detach with `Ctrl+b d`. Agents keep running. Mouse support is on, so you can click panes, resize them, and scroll.

Exiting an agent follows your tmux `remain-on-exit` setting. You can reopen its saved conversation later. To apply config changes, stop and reopen the group.

## Let agents talk

Inside a managed pane, agents can find peers and send messages:

```sh
xc status "$XCONTROL_CONFIG"
xc send "$XCONTROL_CONFIG" ios "Does this API change work for you?"
```

Messages go straight into the other agent's terminal. There is no queue, so a busy agent or an open dialog may need your attention.

## Pick an available agent

Replace an agent's CLI choice with:

```toml
agent = "auto"
candidates = ["codex", "copilot", "claude"]
```

xcontrol tries them in order with a small model call and picks the first that answers. These calls count toward usage and may cost money. Reattaching doesn't check again. To change a running pane, use `xc switch`.

## Hit a usage limit?

Switch just that pane from another terminal:

```sh
xc switch myapp.agents server copilot
xc switch myapp.agents server agy
xc switch myapp.agents server devin
xc switch myapp.agents server             # check for an available alternative
```

The new CLI gets the role, recent terminal history, and Git state. Other panes keep running. Add `--note "what to continue"` if useful.

Switch when the old agent is idle or blocked: it is replaced. This starts a fresh conversation, not a full history import. Selection without a CLI makes small access-check calls. Limits are not watched automatically.

## Ask your agent to set it up

The installer includes a [Codex skill](skills/xcontrol/SKILL.md). Try:

> Use xcontrol to create myapp.agents with myapp-android using Codex, myapp-ios using Copilot, and myapp-server using Claude.

See the [reference](docs/reference.md) for resume options, custom CLIs, access checks, and troubleshooting.

## Related tools

There are plenty of options, including T3 Code and Herdr. If you already use tmux, xcontrol is a small wrapper around the setup you have.

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

## Development

```sh
python3 -m unittest discover -s tests -v
```

Tests use isolated tmux servers and fake agents. No model calls.

MIT licensed.
