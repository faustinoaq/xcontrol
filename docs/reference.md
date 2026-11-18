# xcontrol reference

[Back to the README](../README.md)

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

**Codex panes bypass approvals and sandboxing by default**, using `--dangerously-bypass-approvals-and-sandbox`, so they can control tmux and communicate with peers. This gives Codex unrestricted access under your user account. Set `bypass = false` on a Codex or auto agent to inherit normal Codex permissions instead; for auto agents this setting applies only when Codex is selected. Availability probes remain restricted. Copilot, Claude, and custom CLIs keep their normal permissions. All CLIs inherit your model and authentication settings. Roles are printed in each pane; they are **not automatically sent as prompts**. The `agent` field names an executable on your PATH, and optional `args` are passed as literal arguments. xcontrol does not evaluate shell syntax. Use configuration files you trust: launching an agent runs that executable with your normal account access.

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

The chosen CLI appears in the pane title and `xc status`. Auto agents accept `resume = "auto"` or `"new"`; custom candidates start fresh. CLI-specific arguments and explicit session UUIDs require selecting that CLI explicitly. Reattaching keeps the existing selection. Use `xc switch` to request a handoff in one running pane. Quota detection is not automatic.

## Switch a running pane

```sh
xc switch myapp.agents server copilot
xc switch myapp.agents server devin
xc switch myapp.agents server agy --note "Finish the API review, no deployment"
xc switch myapp.agents server
```

Run this from another pane or terminal while the target is idle or waiting for quota. It replaces the selected CLI in the same pane. Other panes, role IDs, working folders, and peer communication stay in place. Supported destinations are Codex, Copilot, Claude, `agy`, and Devin, using their normal authentication and default model. `agy` uses `--prompt-interactive`, as documented by its local `--help`. Devin uses an interactive prompt after `--` and `--process-model in-process` so the handoff owns its process. Switching does not enable permission bypass for Copilot, Claude, agy, or Devin. Codex respects the role's `bypass` setting, defaulting to true.

An explicit CLI is launched without a model probe. With no destination (or `auto`), xcontrol checks the configured candidates in order, excluding the current CLI, and picks the first with confirmed access. Defaults are Codex, Copilot, and Claude. These checks consume usage. `agy` and `devin` can be selected explicitly; automatic selection requires adding them to an auto role's candidates and providing a trusted `[availability]` checker. If no alternative passes or its CLI/folder lock is busy, the current pane stays unchanged.

The new conversation receives a prompt to read a local handoff file, verify project instructions and current Git state, and continue only clearly authorized unfinished work. The snapshot includes up to 2,000 lines of available terminal history (capped at 192 Ki characters), Git branch/HEAD/status, the optional note, and a link to any previous handoff. No model call is needed to summarize the old session. Snapshots do not contain the complete native conversation and may miss earlier instructions. Use `--note` to clarify the task when needed.

Handoffs are saved under `$XDG_STATE_HOME/xcontrol/handoffs`, defaulting to `~/.local/state/xcontrol/handoffs`, with directory mode 700 and file mode 600. They may contain private terminal output. The replacement provider can read that content. Files remain local until the CLI reads them, are not committed, and are kept until you remove them. Terminal text is marked as untrusted data; the new prompt tells the agent to preserve authorization boundaries.

The `.agents` file is unchanged. Reattaching keeps the switched CLI; stopping and reopening uses the file's configured CLI again. Old native histories remain available through each provider's own history. xcontrol does not monitor quota errors or switch providers without an explicit command. A failure after the pane is replaced, such as a login failure in the new CLI, cannot restore the old running process.

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
xc                               # show usage without launching anything
xc .                             # setup agent in the current directory
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

Mouse support is enabled for new xcontrol sessions, so you can click panes, resize borders, and scroll. Other tmux sessions keep their existing settings. To disable it in the current session, run `tmux set-option mouse off`.

All panes follow your tmux `remain-on-exit` setting. With `set -g remain-on-exit off`, panes close when their agent exits. Saved conversations remain available through the CLI's native session history.

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

The included [skill](../skills/xcontrol/SKILL.md) supports prompts such as:

> Use xcontrol to create an agents file for this project with myapp-android using Codex, myapp-ios using Copilot, and myapp-server using Codex.

The installer makes it discoverable by Codex. For another agent that supports `SKILL.md`, copy `skills/xcontrol` to that tool's skill directory.

## Agent cannot find a visible group

`xc status` and `xc send` need access to the local tmux Unix socket. A CLI can be visible in a pane while its sandboxed shell commands are denied access to that socket. xcontrol reports this as **Cannot access the tmux socket**, rather than claiming the group has stopped.

Run `xc status myapp.agents` from your normal terminal to distinguish a stopped group from an agent permission restriction. If it works there but fails inside the agent, inspect that CLI's local socket permissions. Codex supports explicit [Unix socket permissions](https://learn.chatgpt.com/docs/permissions#unix-sockets), subject to your version and managed policy. Allowing a tmux socket grants control over that tmux server, so choose that access explicitly. New Codex panes use bypass mode by default. Existing panes keep their previous permissions until you change them in Codex or relaunch the pane. If you deliberately set `bypass = false`, local socket permission may still be required. Do not restart working agents merely because a sandbox cannot query tmux.

