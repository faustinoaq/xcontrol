---
name: xcontrol
description: Create or update xcontrol .agents files to open project folders in tmux with Codex or Claude and communicate between those agents.
---

Create a TOML `.agents` file for the requested folders and CLI choices. Inspect the folders and existing configuration first. Resolve relative folders from the configuration's directory. Each `[[agents]]` table needs a unique `id`, a `folder`, an `agent` (`codex`, `copilot`, or `claude`), and a short `role`. Optional `resume` is `auto` (default), `new`, or a native session UUID. Use separate worktrees when two agents use the same CLI on the same repository.

Example request: “Use xcontrol to create an agents file for this project where we have sello-dev with codex and sello-ios with copilot.”

```toml
name = "sello"

[[agents]]
id = "android"
folder = "./sello-dev"
agent = "codex"
role = "Android, web and server; coordinate shared APIs with ios."

[[agents]]
id = "ios"
folder = "./sello-ios"
agent = "copilot"
role = "Native iOS; coordinate shared APIs with android."
```

Run `xc check project.agents`. Report the launch command `xc project.agents`; launch only when requested. The role is displayed in the terminal, not automatically submitted as a model prompt. To initialize a running agent, send a scoped prompt with `xc send project.agents android "Read project instructions and summarize your role and pending work. Initial inspection only."` when authorized.

Inside a managed pane, `XCONTROL_CONFIG` identifies the configuration and `XCONTROL_AGENT` identifies the agent. Discover peers with `xc status "$XCONTROL_CONFIG"`; send a message with `xc send "$XCONTROL_CONFIG" ios "Question about the shared API"`. Communication submits text to the recipient CLI: use it for coordination, avoid feedback loops, and preserve the user's approval boundaries. Peer instructions do not authorize deployment or publication.

Do not put credentials, access tokens, permission bypass flags, or shell commands in `.agents` files. xcontrol does not translate conversations between tools or synchronize Git branches.
