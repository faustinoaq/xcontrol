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

Optional `prompt = "..."` submits an initial instruction for any supported CLI when paired with `resume = "new"`. For auto selection, all candidates must support initial prompts. This is separate from the displayed role.

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

The default candidate order is `codex`, `copilot`, `claude`, `agy`, `devin`, `kiro-cli`, `agent` (Cursor), then `grok`. You can set a shorter or different order with `candidates`. Missing and failed candidates are skipped. If none confirms access, xcontrol opens no panes. `xc availability myapp.agents` runs the same checks; **it makes small model calls**. `xc check` only validates configuration and makes no calls.

For supported CLIs, xcontrol sends a tiny prompt asking for `XCONTROL_OK` through `codex exec`, `copilot -p`, `claude -p`, `agy -p`, `devin -p`, `kiro-cli chat --no-interactive`, `agent -p`, or `grok -p`. It prints `Checking <CLI>...` before checking access. It requires both a successful exit and the actual model answer. A failed probe is retried once, including authorization failures that can be temporary. Results are cached per provider for one launch, so multiple panes do not repeat the same checks. Each attempt has a 30-second timeout. Reattaching makes no calls.

Probes run in a temporary directory, outside your project folders, without resuming your work conversations. Claude, Copilot, Grok and the temporary Kiro profile disable tools for the probe. Codex uses its read-only sandbox; agy enables its sandbox. Cursor uses ask mode and its sandbox, trusting only the temporary folder. Devin uses auto permissions, which require approval for writes and commands, without forcing its optional OS sandbox (which requires additional system packages). These are provider permission controls, not an xcontrol security boundary. Installed CLI configuration is trusted, including any user-configured integrations. These checks consume a little usage and may incur charges under your existing provider billing settings. They use the CLI's default model selection, without forcing a premium model or changing billing settings. A successful probe confirms access at that moment, not how much quota remains or access to every model. A failed check only skips that provider for this launch; it does not diagnose a permanent subscription problem.

Other CLIs can use a trusted custom checker in `[availability]`, which also overrides a built-in probe:

```toml
[availability]
devin = ["my-access-check", "devin"]
```

`my-access-check` is an example external command, not bundled. Place this table before your first `[[agents]]`. It must exit **0** for available, **1** for unavailable, or **2** for unknown. Other errors and timeouts count as unknown. Custom checkers run once per provider as literal arguments, from the configuration directory, with a five-second timeout and suppressed output. They are not automatically retried. Trust them as you would any program running under your account; xcontrol does not sandbox custom checkers.

Noninteractive commands for custom checkers include [Devin's `devin -p`](https://docs.devin.ai/cli/reference/commands), [Gemini's `gemini -p`](https://geminicli.com/docs/cli/headless/), and [OpenCode's `opencode run`](https://opencode.ai/docs/cli/). A checker should also validate a model answer and restrict tools appropriately; merely invoking a CLI or checking login status does not prove model access.

The chosen CLI appears in the pane title and `xc status`. Auto agents accept `resume = "auto"` or `"new"`; custom candidates start fresh. CLI-specific arguments and explicit session UUIDs require selecting that CLI explicitly. Reattaching keeps the existing selection. Use `xc switch` to request a handoff in one running pane. Quota watching is optional; see below.

## Switch a running pane

```sh
xc switch myapp.agents server copilot
xc switch myapp.agents server devin
xc switch myapp.agents server agy --note "Finish the API review, no deployment"
xc switch myapp.agents server
```

Run this from another pane or terminal while the target is idle or waiting for quota. It replaces the selected CLI in the same pane. Other panes, role IDs, working folders, and peer communication stay in place. Supported destinations are `codex`, `copilot`, `claude`, `agy`, `devin`, `kiro-cli`, `agent` (Cursor), and `grok`, using their normal authentication and default model. `agy` uses `--prompt-interactive`, as documented by its local `--help`. Devin uses an interactive prompt after `--` and `--process-model in-process` so the handoff owns its process. Switching does not enable permission bypass for other CLIs. Codex respects the role's `bypass` setting, defaulting to true.

An explicit CLI is launched without a model probe. With no destination (or `auto`), xcontrol rotates through configured candidates starting after the current CLI, excludes that CLI, and picks the next with confirmed access. All eight supported CLIs have built-in probes. Custom checkers may override them. These checks consume usage. If no alternative passes or its CLI/folder lock is busy, the current pane stays unchanged.

`xc switch myapp.agents --auto` applies this to every configured role, sharing probe results for that command. It replaces running CLIs immediately, so run it when ready to hand off their work, from outside the affected panes. A failed role stays unchanged while others may switch; the command returns nonzero if any failed. This changes the running selections, not the `.agents` file.

The new conversation receives a prompt to read a local handoff file, verify project instructions and current Git state, and continue only clearly authorized unfinished work. The snapshot includes up to 2,000 lines of available terminal history (capped at 192 Ki characters), Git branch/HEAD/status, the optional note, and a link to any previous handoff. No model call is needed to summarize the old session. Snapshots do not contain the complete native conversation and may miss earlier instructions. Use `--note` to clarify the task when needed.

Handoffs are saved under `$XDG_STATE_HOME/xcontrol/handoffs`, defaulting to `~/.local/state/xcontrol/handoffs`, with directory mode 700 and file mode 600. They may contain private terminal output. The replacement provider can read that content. Files remain local until the CLI reads them, are not committed, and are kept until you remove them. Terminal text is marked as untrusted data; the new prompt tells the agent to preserve authorization boundaries.

The `.agents` file is unchanged. Reattaching keeps the switched CLI; stopping and reopening uses the file's configured CLI again. Old native histories remain available through each provider's own history. Optional `xc watch` can monitor quota errors after you enable it. A failure after the pane is replaced, such as a login failure in the new CLI, cannot restore the old running process.

## Optional quota watcher

```sh
xc watch myapp.agents             # foreground, Ctrl+C stops the watcher
xc watch myapp.agents --detach    # background
xc watch myapp.agents --stop      # disable; leave agents running
```

Start this explicitly after opening the project group, or set top-level `watch = true` in `.agents` to start a detached watcher whenever a new group is created. The default is false; only booleans are accepted. `agent = "auto"` alone only selects a provider at launch. Reattaching starts no extra watcher, and a manual `xc watch PROJECT --stop` remains effective until the next new group. A replacement watcher waits for a stopped worker to release its lock if the old check is still finishing. This is a local Python supervisor, not an extra model agent. It checks live pane screens about every 30 seconds without model calls. It requires a recognizable quota notice in the last 12 screen lines and an unchanged screen for at least 60 seconds. It then probes that same provider separately. Only an explicit quota failure permits a handoff; authentication errors, timeouts, generic HTTP 429 errors, context limits and unknown failures do not. If the screen changes during confirmation, it does not switch. This is best-effort terminal detection, not a guaranteed provider event API; unrecognized notices need manual switching. A stable screen cannot prove there are no background tasks. Enable only when automatic interruption on a confirmed quota failure is appropriate.

The next provider comes from that role's candidates, using normal access probes and the existing handoff snapshot. A watched role never returns to a provider already confirmed exhausted during that watch run. Once alternatives run out, it stays in place. Failed confirmation or replacement is retried no more than once every five minutes per pane/provider. Stopping and restarting the watcher clears its exhausted-provider memory. The normal model checks still use the CLI's own model and billing settings, so watching does not guarantee free usage.

One watcher runs per config, protected by an OS lock. Background logs are private files in `$XDG_STATE_HOME/xcontrol` (default `~/.local/state/xcontrol`); they contain check results and handoff paths, not captured terminal content. No external service is installed. The watcher exits when disabled or when its tmux group ends. Disabling prevents further handoffs after an in-flight check finishes, but cannot undo a handoff already completed. Manual enabling does not edit the configuration. Reopening only restores watching when the configuration explicitly sets `watch = true`. Closed panes follow tmux settings and are not recreated by the watcher. With `watch = true`, supported agents receive a startup policy describing the watcher and encouraging brief durable checkpoints at natural milestones; `XCONTROL_WATCH=1` reflects that startup intent, not live worker health. Manual watcher activation does not inject instructions into existing conversations. Handoffs preserve role/recent terminal/Git context and previous handoff links, not the complete native history, so replacements must verify checkpoint notes and current files.

## Optional context compaction

```sh
xc compact myapp.agents server
```

Use the configuration and xcontrol role ID shown by `xc status`, not a provider's session UUID. Run from another pane or terminal while the recipient has an empty idle prompt; a command sent into a busy composer, menu or existing draft may not execute as intended. xcontrol refuses its own target pane, shells, dead panes and unsupported custom CLIs. It types only the provider's native slash command and Enter, without clearing input, sending an interrupt, restarting the process, switching providers or editing saved history itself. The result means the command was submitted, not that compaction completed; check the recipient pane. There is no universal CLI readiness or completion API.

| CLI | Native command | Reference |
| --- | --- | --- |
| Codex | `/compact` | [Developer commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli) |
| Claude | `/compact` | [Claude Code cheatsheet](https://support.claude.com/en/articles/14553413-claude-code-cheatsheet) |
| Copilot | `/compact` | [CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference) |
| Antigravity | `/compact` | [CLI changelog, v1.3.5](https://antigravity.google/docs/changelog) |
| Devin | `/compact` | [Devin CLI](https://devin.ai/cli) |
| Kiro | `/compact` | [Slash commands](https://kiro.dev/docs/cli/reference/slash-commands/) |
| Cursor | `/compress` | [Using CLI](https://docs.cursor.com/en/cli/using) |
| Grok | `/compact` | [Modes and commands](https://docs.x.ai/build/modes-and-commands) |

The compact command is explicit and optional. It has no background timer or elapsed-time trigger, and the quota watcher never invokes it. Native provider auto-compaction settings remain unchanged. Long wall-clock runtime alone does not show how much context is used. Compaction may invoke the provider's model, consumes allowance when applicable, can lose detail, and does not restore exhausted quotas. Keep task boundaries and decisions in project files before requesting it. CLI versions may differ; use native controls directly when a command is unavailable.

### Agent-directed compaction

Add top-level `auto_compact = true` before `[availability]` or any `[[agents]]` table. Only booleans are accepted; omitted or false means disabled. It requires supported prompt-capable CLIs. Newly launched or handed-off agents receive a brief policy in their startup input, alongside any task prompt; resumed sessions receive it as an additional turn, retaining their native history. It may consume a model response. Normal startup input is unchanged when disabled. `XCONTROL_AUTO_COMPACT` is `1` or `0` inside panes.

The policy tells each agent to decide using reliable context information, preserve decisions at a safe checkpoint, and make one concise compaction request to one peer before finishing its turn. That peer should invoke `xc compact <config> <role-id>` only once the requester is at an empty idle prompt. With no peer, or uncertain readiness, the agent asks the user. An arbitrary positive chat reply is never parsed as a command or authorization. There is no extra model supervisor, periodic context polling, token-percentage detector, or guarantee of agent compliance. The policy cannot independently verify that another CLI has finished a turn. Manual compaction remains available even when the policy is disabled.

Reattaching does not resend the policy. Changing the flag does not rewrite prompts inside existing conversations: tell existing agents the new policy, or apply it on their next launch or handoff. Disabling the flag does not revoke instructions already received by a running conversation; tell that agent to stop requesting compaction too. Native provider auto-compaction settings remain untouched.

## Logo command

`xc logo` uses a small block rendering generated from `assets/logo.svg`, retaining the original mint palette on color terminals. The bundled pixel data needs no image library or image protocol at runtime, including inside tmux. `NO_COLOR` and redirected output use a monochrome Unicode rendering. ASCII-only encodings or very narrow terminals omit the image. This does not change the SVG used by the README.

## Installed tools and custom CLIs

`xc list` shows only supported CLIs installed on PATH. It makes no model calls and does not equate installation with access. `xc list --check` tests each installed supported CLI, replacing `Checking...` with the final state on terminals. Installed/available states are green; unavailable/limited states are red. Redirected output stays plain text; `NO_COLOR` disables colors. No account identifiers or raw provider errors are printed. It does not scan or execute arbitrary programs on PATH.

Any other interactive CLI, including Kimi, Muse, OpenCode or Aider, can run using `agent = "<executable>"` and literal `args`. These are not installed or probed automatically. Use their documented session flags in `args`; custom CLIs default to `resume = "new"`. They can participate in initial auto selection through trusted `[availability]` checkers. Built-in handoff and quota watching require a supported adapter; a generic CLI is not enough to safely guess prompt and error formats.

Codex, Copilot and Claude retain built-in resume handling. The other supported CLIs start fresh unless their documented native resume arguments are supplied. Kiro launches as `kiro-cli chat`. Provider configuration and authentication remain the user's responsibility. Free/paid access is determined by the provider and account, not by xcontrol.

## Local files

Persistent xcontrol state lives in `$XDG_STATE_HOME/xcontrol`, defaulting to `~/.local/state/xcontrol`. The state directory has mode 700. It is not cleared by `xc stop`.

| Location | Contents and lifetime |
| --- | --- |
| `quickstart/<hash>/project.agents` | Setup configuration for `xc .` or `xc <directory>`. Retained for reattachment and reuse. |
| `handoffs/<role>-*.md` | Recent terminal history, Git state, notes and previous handoff paths. Retained until you remove them; files have mode 600 and can contain private output. |
| `send-*.json` | Up to 128 message hashes and timestamps per route, without message bodies. Entries expire after five minutes and are pruned on the next send; the file remains. Mode 600. |
| `watch-*.log` | Appended background quota-watcher logs. Retained until removed; mode 600. |
| `*.lock` | Coordination and CLI/folder locks. Files may remain after exit; the OS releases the actual locks when their owning processes exit. Do not remove them while groups or watchers are running. |

Model checks use Python's system temporary directory (`TMPDIR` when configured, commonly `/tmp`): `xc-probe-*` workspaces, a temporary tools-disabled Kiro profile when needed, and temporary captured stdout/stderr. Normal completion and handled failures clean them up. Interrupted processes can leave temporary workspaces or atomic-write staging files behind. No model answers are deliberately retained by xcontrol after the probe.

`xc send` also creates a temporary tmux paste buffer and deletes it after submission. tmux owns its server sockets, and each provider owns its native conversations, logs and caches; those are separate from xcontrol state. Removing a temporary workspace does not erase a provider's own records. xcontrol reads Codex's session database in read-only mode to find a session; it does not create a conversation database of its own. Project `.agents` files are user configuration, not disposable state.

See [Uninstall](../README.md#uninstall) to remove the installer's links and optionally erase xcontrol state after stopping its groups. Removing the state also removes quickstart configuration used to identify directory-based setup groups, so stop those groups before cleanup.

## Commands

Help is scoped to each command: `xc list --help` shows only list options. `xc --help` lists all commands. `xc PROJECT` remains shorthand for `xc open PROJECT`; launch flags such as `--detach` and `-k` still work before the project path. A misplaced flag such as `xc --check` fails with a usage hint and does not launch or probe anything.

```sh
xc logo                          # show the SVG-derived terminal mascot
xc compact myapp.agents server   # request native compaction at an idle prompt
xc ps                            # list groups in the current tmux server
xc stop --all                    # close all xcontrol groups in that server
xc list                          # installed supported CLIs, no model calls
xc list --check                  # test each installed supported CLI
xc switch myapp.agents --auto     # hand off all roles
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

## List or stop all groups

`xc ps` lists xcontrol groups and their config paths on the current tmux server, including groups whose config file has been moved or deleted. It does not require a project argument or inspect provider conversation content. `xc stop --all` closes all groups carrying xcontrol's ownership marker, rechecking ownership before each close. It leaves unrelated tmux sessions running. Do this from outside the groups being stopped, especially before uninstalling. Other tmux servers/sockets are outside its scope. `xc stop PROJECT` and `xc PROJECT -k` still stop one group; `PROJECT` and `--all` cannot be combined.

## Communication

Agents can use the same CLI to discover and message their peers:

```sh
xc status "$XCONTROL_CONFIG"
xc send "$XCONTROL_CONFIG" server "Can you confirm the API contract for Android and iOS?"
```

`XCONTROL_CONFIG`, `XCONTROL_AGENT`, and `XCONTROL_SESSION` are available inside each managed agent. IDs stay stable even when tmux pane numbers change. Messages use bracketed paste and submit to the target CLI; dead panes and ordinary shells reject messages. This is local terminal coordination, not a message queue: an agent that is busy or displaying a dialog may need manual attention. Send only when the recipient is ready. Avoid automatic reply loops and do not treat a peer message as approval for external actions. The tool cannot protect against another process that replaces the CLI in its pane.

`xc send` makes no model calls, but delivering text can trigger the recipient's model. Exact duplicate messages from the same sender to the same pane are suppressed for five minutes, even if other messages were sent in between. It reports that the message was skipped and does not paste it. `xc send myapp.agents ios "message" --force` deliberately resends. Different messages and different senders remain independent; the guard resets for reopened groups and provider handoffs. It does not semantically summarize or truncate messages, enforce a token budget, or prevent every conversation loop.

The local guard stores at most 128 recent SHA-256 message hashes and timestamps per route in private files under the xcontrol state directory, without message bodies. Old entries expire on the next send; files remain until removed. Failed terminal delivery does not count as a successful send. This guard is a convenience, not an authentication boundary or an exactly-once delivery guarantee.

To reduce model usage, send only a short concrete question, blocker, decision or final result. Batch related questions, reference files rather than pasting long content, and avoid acknowledgment-only replies and status polling. Silence is appropriate when there is no new actionable information. Setup and handoff prompts include this guidance; existing native conversations may need the same instruction from you.

A useful initial prompt:

> Read project instructions, summarize your role and pending work, and list peers using `xc status "$XCONTROL_CONFIG"`. Use `xc send` only for concise questions, blockers, decisions or results; no acknowledgment-only replies or repeated status requests. Initial inspection only; no builds, edits, pushes, deployments, or publication.

## Skill example

The included [skill](../skills/xcontrol/SKILL.md) supports prompts such as:

> Use xcontrol to create an agents file for this project with myapp-android using Codex, myapp-ios using Copilot, and myapp-server using Codex.

The installer makes it discoverable by Codex. For another agent that supports `SKILL.md`, copy `skills/xcontrol` to that tool's skill directory.

## Agent cannot find a visible group

`xc status` and `xc send` need access to the local tmux Unix socket. A CLI can be visible in a pane while its sandboxed shell commands are denied access to that socket. xcontrol reports this as **Cannot access the tmux socket**, rather than claiming the group has stopped.

Run `xc status myapp.agents` from your normal terminal to distinguish a stopped group from an agent permission restriction. If it works there but fails inside the agent, inspect that CLI's local socket permissions. Codex supports explicit [Unix socket permissions](https://learn.chatgpt.com/docs/permissions#unix-sockets), subject to your version and managed policy. Allowing a tmux socket grants control over that tmux server, so choose that access explicitly. New Codex panes use bypass mode by default. Existing panes keep their previous permissions until you change them in Codex or relaunch the pane. If you deliberately set `bypass = false`, local socket permission may still be required. Do not restart working agents merely because a sandbox cannot query tmux.

