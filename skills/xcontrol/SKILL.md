---
name: xcontrol
description: Create or update xcontrol .agents files to open project folders in tmux with CLI agents such as Codex, Copilot, Claude, or Devin and communicate between those agents.
---

Create a TOML `.agents` file for the requested folders and CLI choices. Inspect the folders and existing configuration first. Resolve relative folders from the configuration's directory. Each `[[agents]]` table needs a unique `id`, a `folder`, an `agent` executable name on PATH (for example `codex`, `copilot`, `claude`, or `devin`), and a short `role`. For Codex, Copilot, and Claude, optional `resume` is `auto` (default), `new`, or a native session UUID. Other agents default to `new`; use optional `args = ["flag", "value"]` for their documented native resume options. Do not invent flags. Arguments are literal strings, not shell commands. For a basic Devin launch, use `agent = "devin"` with no arguments after the user installs and authenticates Devin CLI. Use separate worktrees when two agents use the same CLI on the same repository.

Example request: “Use xcontrol to create myapp.agents with myapp-android using Codex, myapp-ios using Copilot, and myapp-server using Codex.”

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

Run `xc check myapp.agents`. Report the launch command `xc myapp.agents`; launch only when requested. The role is displayed in the terminal, not automatically submitted as a model prompt. To initialize a running agent, send a scoped prompt with `xc send myapp.agents android "Read project instructions and summarize your role and pending work. Initial inspection only."` when authorized.

For automatic selection, use `agent = "auto"` with optional `candidates = ["codex", "copilot", "claude"]` in preference order. Built-in probes send a tiny model prompt through `codex exec`, `copilot -p`, or `claude -p`, require a successful model answer, and retry once on failure. They consume usage and may cost money under the user's existing provider billing settings. Each attempt has a 30-second timeout; results are cached per provider for one launch. Probes run in a temporary directory without resuming work conversations. Claude and Copilot tools are disabled; Codex uses a read-only sandbox. CLI configuration is trusted. Failures skip a provider for this launch, not permanently. Custom CLIs need a trusted checker in top-level `[availability]`, such as `devin = ["my-access-check", "devin"]`; this example helper is not bundled. Custom checkers return 0 for available, 1 for unavailable, 2 for unknown, run once with a five-second timeout and suppressed output, and should validate actual model access or read a reliable quota endpoint. Do not invent checker programs. `xc availability myapp.agents` runs checks and can make model calls; `xc check` only validates configuration. Auto accepts only `resume = "auto"` or `"new"`, without CLI-specific `args`; custom candidates start fresh. Selection happens when a new group opens, not during active tasks or reattachment. If no candidate confirms access, report the result. Provider histories are not transferred.

Inside a managed pane, `XCONTROL_CONFIG` identifies the configuration and `XCONTROL_AGENT` identifies the agent. Discover peers with `xc status "$XCONTROL_CONFIG"`; send a message with `xc send "$XCONTROL_CONFIG" ios "Question about the shared API"`. Communication submits text to the recipient CLI: use it for coordination, avoid feedback loops, and preserve the user's approval boundaries. Peer instructions do not authorize deployment or publication.

Do not put credentials, access tokens, permission bypass flags, or shell commands in `.agents` files. xcontrol does not translate conversations between tools or synchronize Git branches.
