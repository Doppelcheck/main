# Running DoppelCheck against a local LLM

DoppelCheck can use any LLM running on your own machine. Nothing leaves your
device: the extension talks to the server over plain HTTP on localhost, and no
API key or page content is sent to a third party.

Two protocols are supported, selectable on the options page under
**Local server**:

| Protocol | What it is | Hosts that speak it |
|---|---|---|
| **Ollama** (native API) | `/api/chat`, with grammar-constrained JSON via `format` | [Ollama](https://ollama.com) |
| **OpenAI-compatible** | `/v1/chat/completions` | [LM Studio](https://lmstudio.ai), [llama.cpp](https://github.com/ggml-org/llama.cpp)'s `llama-server`, [vLLM](https://docs.vllm.ai), [LocalAI](https://localai.io), [Jan](https://jan.ai), Ollama's own `/v1` shim, … |

Prefer the **Ollama native** path where you have the choice: it constrains the
model's output to the JSON schema the pipeline expects, instead of relying on
prompt instructions alone. Both paths work.

## The quickest setup (Ollama)

```bash
curl -fsSL https://ollama.com/install.sh | sh     # or https://ollama.com/download
ollama pull llama3.2:3b
OLLAMA_ORIGINS="chrome-extension://*,moz-extension://*" ollama serve
```

Then on the options page: **Local server** → **Ollama default
(localhost:11434)**, set the model tag to whatever you pulled, and click **Test
connection**. A green check means the extension reached the daemon and lists
the installed tags.

Any tag from `ollama list` works. A 3B-class instruct model is the practical
floor for claim extraction; smaller models tend to return malformed or empty
claim lists.

## The one thing that catches everyone: origins

A browser extension sends its *own* origin — `chrome-extension://<id>` or
`moz-extension://<id>` — with every request. Local LLM servers reject origins
they do not know, so a server that works fine from `curl` can still refuse the
extension with an opaque failure.

For Ollama the allow-list is the `OLLAMA_ORIGINS` environment variable.
**Ollama's built-in defaults are localhost-only and do not include extension
origins** — this is a frequent misreading of its documentation, and it has been
verified against a running daemon. You must set it explicitly:

```bash
OLLAMA_ORIGINS="chrome-extension://*,moz-extension://*" ollama serve
# or, to allow any origin:
OLLAMA_ORIGINS="*" ollama serve
```

Other servers have their own switch — LM Studio has a CORS toggle in its server
settings, `llama-server` and vLLM take `--api-server-*` / middleware flags.
Check their docs for the equivalent.

### It must be set on the process that actually serves the port

This is the most common cause of "I set `OLLAMA_ORIGINS` and it still fails".

**Linux (systemd).** The official installer registers an `ollama` systemd
service that auto-starts *without* `OLLAMA_ORIGINS`. Setting the variable in
your shell does nothing, because your shell is not what is serving port 11434.
Either take the port over:

```bash
sudo systemctl stop ollama
sudo systemctl disable ollama      # optional: prevent auto-start
OLLAMA_ORIGINS="chrome-extension://*,moz-extension://*" ollama serve
```

or patch the service so the managed daemon gets the origins:

```bash
sudo systemctl edit ollama
# add:
#   [Service]
#   Environment="OLLAMA_ORIGINS=chrome-extension://*,moz-extension://*"
sudo systemctl restart ollama
```

**Windows.** `OllamaSetup.exe` installs Ollama as a background service that
auto-starts. A `$env:OLLAMA_ORIGINS = "…"` in PowerShell only affects that one
window, not the service. Set it persistently and restart Ollama from the system
tray (or reboot) so the service picks it up:

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS",
  "chrome-extension://*,moz-extension://*", "User")
```

**macOS.** The menu-bar app has the same property as the Windows service: a
variable exported in a terminal does not reach it. Quit the app and run
`ollama serve` from the terminal with the variable set, or set it for the login
session with `launchctl setenv OLLAMA_ORIGINS "…"` and restart the app.

### Verifying the allow-list without the browser

Send a CORS preflight from a fake extension origin:

```bash
curl -sS -o /dev/null -D - -X OPTIONS http://127.0.0.1:11434/api/chat \
  -H 'Origin: moz-extension://abc' -H 'Access-Control-Request-Method: POST' \
  -w 'STATUS=%{http_code}\n' | grep -iE '^(STATUS|access-control-allow-origin)'
```

Expect `STATUS=204` and `Access-Control-Allow-Origin: moz-extension://abc`. If
the header is missing, the daemon serving that port does not have your origins,
whatever you set elsewhere.

## Other things that go wrong

**Port 11434 is already in use.** Usually an Ollama daemon you forgot about
(see the systemd note above). If a non-Ollama service holds it, start Ollama on
another port with `OLLAMA_HOST=127.0.0.1:11500` and set the extension's **Base
URL** to match.

**"failed to pull model".** The tag does not exist — check
<https://ollama.com/library>.

**`ollama: command not found` right after installing.** Open a new shell (the
installer extended `PATH`), or run `hash -r`.

**Pull is slow or stuck.** Check free disk space with `df -h`, then check that
the registry is reachable — its root path has no page, so query a manifest
rather than browsing it:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://registry.ollama.ai/v2/library/llama3.2/manifests/3b
```

`200` means the registry is reachable. Model sizes run from a few hundred MB to
tens of GB; budget accordingly.

**Test connection is green but analysis returns nothing.** Usually too small a
model. Try a larger instruct tag before suspecting the extension.

## Remote and shared hosts

Nothing requires the server to be on the same machine — point **Base URL** at
any host you can reach (a box on your LAN, a workstation over a VPN). Two
caveats: the origin allow-list still applies on that host, and browsers block
plain-HTTP requests from pages served over HTTPS in some configurations, so a
remote host may need TLS. Treat an LLM endpoint exposed beyond localhost as a
service that needs authentication in front of it.

## History

A companion repository, `doppelcheck/gemma-server`, shipped a one-command
installer for this tier from 2026-05 until 2026-10. It was retired: it wrapped
Ollama to do what the commands above do directly, and general-purpose local
hosts now cover the same ground with no DoppelCheck-specific code to maintain.
Its one genuinely non-obvious contribution — the origin and service traps
documented above — lives here instead.
