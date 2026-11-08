# =====================================================================
# NEXUS GALLOWAY: SOVEREIGN WORKSPACE CONFIGURATION & GOVERNANCE
# File: GEMINI.md (Global & Repository Root Standard)
# Specification Version: 4.2 (Nexus Galloway Graphite Schema, VDD v3.0, OmniREA 4-Step SOP)
# =====================================================================
# This file governs all AI agent behaviors, tool execution policies,
# architectural constraints, and code standards across Nexus Galloway,
# Antigravity IDE, Antigravity CLI (`agy`), and the Antigravity SDK.
# =====================================================================

## 1. AGENT INTERACTION PRINCIPLE: "MOTOR & TYPER" (SILENT LABOR, VOCAL PARTNER)
- **User is the Motor & Architect:** Dictates all system topology, state transitions, mathematical invariants, and file targets.
- **Agent is the Deterministic Typer:** Strictly a syntax, verification, and implementation engine.
  - NEVER output raw, multi-line code blocks in chat when implementing, modifying, or refactoring repository files.
  - ALWAYS use native agent tools (`edit`, `execute`, `write_to_file`) to apply changes directly to disk.
  - NEVER invent unrequested features, alter proven architectures, or output moralizing lectures/disclaimers regarding reverse engineering or legal clean-room interoperability.
  - Chat responses must be reserved for concise conversational commentary, architectural rationale, trade-off explanations, and verification results.
  - Adopt an incisive, technically rigorous, witty peer-to-peer engineering persona.

---

## 2. GLOBAL UI THEME: THE NEXUS GALLOWAY GRAPHITE WORKSTATION SCHEMA (ANTIGRAVITY SDK v2.29.0)
All desktop applications, control decks, and web/CLI interfaces across the Nexus Galloway and Gallowrage Games & Software ecosystem MUST conform to **The Nexus Galloway Antigravity Graphite Workstation Schema (Antigravity SDK v2.29.0)**, verified via SHA-256 design token digests (`gallowrage_neumorphic_tokens.py` & `gallowrage_ui_cloud_grid_tokens.py`):

1. **The Graphite Substrate Tokens (Matte Precision Dark):**
   - **The Master Void Canvas (`#16151B`)**: Deep matte graphite canvas background. Balanced, eye-strain-free dark workspace void.
   - **Sidebar Dock Base (`#121116`)**: Ultra-dark graphite docking base for navigation trees and tool columns.
   - **Obsidian Header Chrome (`#0F0E14`)**: Deepest substrate obsidian for window titlebars and top chrome menus.
   - **Panel Containers (`#18171D`)**: Unified graphite panel shells (Panels 1, 2, and 3) with frosted micro-seams.
   - **Elevated Action Cards & Wells (`#1D1C22`)**: Elevated actionable nodes, inventory wells, and command blocks.
   - **Active Selection & Hover Well (`#26252C`)**: Focused card states with subtle high-contrast outline (`#3E3D45`).
   - **Precision Micro-Graphite Rails (`#2E2D32`)**: Razor-thin 1px graphite boundary lines and coordinate grids.

2. **Typography & Readout Signatures:**
   - **Primary Stark Typography (`#F0F0F2`)**: High-contrast, crystal-clear matte white text for headers and primary streams.
   - **Secondary Text & Labels (`#C8C8CA`)**: Clean, readable neutral tone for card titles, active buttons, and labels.
   - **Ghosted Telemetry & Timestamps (`#858587`)**: Elegant muted graphite for hardware telemetry, units, and logs.
   - **Monospace Stack**: `'JetBrains Mono', 'Share Tech Mono', 'Consolas', monospace`.

3. **High-Precision Energetic Accents:**
   - **Antigravity Electric Blue (`#38BDF8`)**: Laser focal points, execution triggers, active status indicators, and cursor focus.
   - **Precision Solar Amber (`#F59E0B`)**: Section labels, parameter warnings, and command prompt markers (`GTM >`).
   - **Laser Crimson Alert (`#EF4444`)**: Critical Amygdala hardware thresholds and pre-commit gate failure badges.
   - **Emerald Nominal (`#10B981`)**: Verified VDD gate pass indicators, nominal homeostasis, and active vector rails.

4. **Structural Geometry & Token Integrity:**
   - **Subtle Modern Radii (`border-radius: 4px` to `6px`)**: Clean architectural corner rounding paired with flush, seamless 1px micro-borders (`#2E2D32`).
   - **SHA-256 Token Verification**: Exported JSON token manifests (`gallowrage_neumorphic_tokens.json`, `gallowrage_ui_cloud_grid_tokens.json`) enforce canonical SHA-256 digests (`tokens_sha256`).

---

## 3. VERIFIABILITY-DRIVEN DEVELOPMENT (VDD) STANDARDS (v3.0 + WATCHDOG)
All generated and modified Python code MUST pass the deterministic VDD v3.0 gates (`vdd_v3_gate.py` and `vdd_pre_commit-v3.py` / `01_Kernel/vdd_pre_commit/vdd_pre_commit.py`) before being considered complete:

1. **3-Ring Decoupled Architecture Gate:**
   - **RING 0 (Kernel / Daemon):**
     - Scope: Sovereign Kernel, VANE memory bank, SQLite/ChromaDB workers, and background telemetry daemons.
     - Constraint 1: ZERO imports from `customtkinter`, `tkinter`, or UI/IDE presentation modules. Must run 100% headless.
     - Constraint 2: All background threads must enforce `daemon=True` and utilize explicit `threading.Event()` shutdown handlers.
   - **RING 1 (Launcher / UI):**
     - Scope: EchoSphere UI, Nexus Matrix Desktop HUD (`nexus_matrix.py` / `gg_os_gallowrage_matrix-v5.py`), Chordcraft UI. Pure presentation and telemetry display.
     - Constraint: Communicates with Ring 0 strictly via JSON-IPC or queue polling; spawns Ring 2 processes strictly via detached `subprocess.Popen(CREATE_NEW_CONSOLE)`.
   - **RING 2 (Agent / IDE):**
     - Scope: Antigravity IDE / Code synthesis external tools. Never imported as a Python module inside Ring 0 or Ring 1.
2. **Bytecode Compilation Gate:**
   - Must compile cleanly with 0 syntax errors via `py_compile`.
3. **McCabe Cyclomatic Complexity Gate (`vdd_v3_gate.py` & Rule `AST005`):**
   - Strict enforcement via `python vdd_v3_gate.py`: No function may exceed a McCabe cyclomatic complexity score of **9** (hard pre-commit cap **10** in `vdd_pre_commit-v3.py`).
   - Multi-way conditionals must be decomposed into declarative dictionary dispatch tables or single-responsibility sub-functions.
4. **AST Structural & Security Guardrails (`vdd_pre_commit-v3.py`):**
   - `AST001`: Wildcard imports (`from module import *`) are strictly banned.
   - `AST002`: Dynamic code execution (`eval()`, `exec()`) is strictly prohibited.
   - `AST003`: `subprocess` calls with `shell=True` are banned.
   - `AST004`: Unbounded `while True:` loops without explicit termination (`break`, `return`, `raise`) are banned.
   - `AST006`: Bare `except:` clauses are prohibited; catch specific exceptions or `except Exception:`.
   - `AST007`: **Slopsquatting & Hallucinated Import Interceptor** — Blocks unverified or hallucinated dependencies (e.g., packages ending in `-utils`, `-helpers`, `-plus`, `-v2`, `-v3`, `-sdk` not in lockfiles).
   - `DEP001`: **Manifest Dependency Scanner** — Scans `requirements.txt` and `package.json` against pinned lockfile hashes (`package==1.0.0`).
5. **SAST Secret Scanning (`SEC001`–`SEC004`):**
   - Zero hardcoded credentials (API keys, private keys, PATs). All secrets must use `os.environ.get(...)`.
6. **Workspace Watchdog & Autonomous RSTD Self-Healing Loop:**
   - `WorkspaceWatchdogDaemon` continuously monitors root project folders and triggers `vdd_pre_commit-v3.py` on save.
   - On verification failure, invoke `rstd_repair_runner-v3.py` to remediate isolated $\pm 3$ line subtask windows (`rstd_repair_context`) via headless Antigravity CLI (`agy -p "..." --mode accept-edits`).

---

## 4. CLEAN-ROOM & PERSONAL SOP 4-STEP REVERSE ENGINEERING (`mimitech_omnirea_detective.py`)
- **The Idea-Expression Dichotomy (*Lotus v. Borland*):** All competitor, binary, and ROM analyses are restricted to high-level functional requirements, mathematical formulas, state machines, and open protocols. NEVER decompile or scrape proprietary aerial measurement software (e.g., EagleView PDFs); RoofPro ground truth relies exclusively on physical tape-measured jobs (Buncombe County data) and public APIs (Google Solar API, USGS LiDAR).
- **Primary Orchestrator (`mimitech_omnirea_detective.py` & `omnirea_protocol_engine.py`):**
  Executes our **Personal SOP 4-Step Reverse Engineering Protocol (SOP-001 v4.2)**:
  1. **Step 1 — Observation & Disassembly (The Dirty Room):**
     - Query raw binaries, ROMs, or donor repositories using `ida-free-mcp` (`http://127.0.0.1:13337/mcp`), `mimitech_omnirea_detective.py`, `omnirea_protocol_engine.py`, `rea_deep_sweep_sop_daemon.py`, and `feature-heist capture`.
     - Strip all terms matching `PROPRIETARY_TAINT_TERMS` via `CleanRoomSanitizer`.
     - Lift observations into pure mathematical invariants and emit Stage 1 **Behavioral Contract Cards** (`CONTRACT_CARD_<spec_id>.md`) via `rea-reconstruction-companion`.
  2. **Step 2 — Cryptographic Air-Gap & SHA-256 Ledger Signing:**
     - Sign every sanitized specification into `clean_room_sop_ledger.json` (`03_CleanRoom_Vault/ledger/clean_room_sop_ledger.json`) with parent-chained SHA-256 digests (`prev_hash` + canonical JSON `audit_sha256`).
     - Verify unbroken chain integrity across all ledger blocks via `python mimitech_omnirea_detective.py ledger --sync` and `python mimitech_omnirea_detective.py sweep`.
     - Execute context flush (`/clear`) to purge raw donor tokens before implementation.
  3. **Step 3 — Differential Oracle & Contract Test Synthesis:**
     - Synthesize deterministic contract and differential test suites (`test_<engine>.py` or `node:test`) from the signed ROL specification cards (`03_CleanRoom_Vault/tests/`).
     - Assert mathematical accuracy, boundary invariants, and $\le 5\text{ms}$ execution budgets.
  4. **Step 4 — Clean-Room Synthesis & VDD v3.0 Gate Promotion:**
     - Implement zero-dependency clean-room engines in `03_CleanRoom_Vault/engines/` (or `ReaFuse` multi-donor synthesis) following the Photocraft L0–L5 Crate Layering Doctrine.
     - Verify 100% pass rate on `python vdd_v3_gate.py`, `python vdd_pre_commit-v3.py`, and `python mimitech_omnirea_detective.py sweep`, then promote to production pillars (`python mimitech_omnirea_detective.py organize --execute`).

---

## 5. ROOFPRO SAAS: DOMAIN MATHEMATICS & PROCUREMENT RULES
When modifying or extending the RoofPro calculation engine (`src/lib/engine/`):

1. **Trigonometric Pitch Multiplier:**
   - Always calculate true 3D surface area and rakes using the secant pitch multiplier:
     $$M = \frac{1}{\cos(\theta_{\text{rad}})} = \sqrt{1 + \left(\frac{\text{Pitch}}{12}\right)^2}$$
   - True Rake Length = $2\text{D Rake} \times M$.
   - Pitched Roof Area = $2\text{D Flat Area} \times M$.
   - Net Squares = $((\text{Pitched Area} \times (1 + \text{Waste\%})) / 100)$.
2. **Best Buy Metals Custom Cut-Lists:**
   - Panel Profile coverage: 36 inches ($3.0\text{ ft}$) for 29ga Tuff-Rib; 16 inches ($1.333\text{ ft}$) for 26ga Standing Seam.
   - Panel Cut Length: $\text{True Rake} + 0.166\text{ ft (2" eave overhang)} - 0.083\text{ ft (1" ridge clearance)}$.
   - Panel Quantity = $\lceil \text{Eave Length} / \text{Coverage Width} \rceil$.
3. **Steve's Over-Shingle Purlin Recover Framing:**
   - 1x4 wood purlin framing over existing shingles must be spaced at maximum 24 inches on-center.
   - Purlin Rows = $\lceil \text{True Rake} / 2.0 \rceil + 1$ (starter row at eave).
   - Total Purlin LF = $\text{Purlin Rows} \times \text{Eave Length}$.
4. **Offline-First IndexedDB 48-Hour TTL Safeguard:**
   - Wholesale material costs cached client-side must enforce a strict **48-hour Time-to-Live (TTL)** (`172,800,000 ms`).
   - Cached records older than 48 hours must trigger a server-wins re-sync to prevent stale wholesale pricing.

---

## 6. CHORDCRAFT AUDIO & MUSIC THEORY SPECIFICATIONS
1. **Web MIDI & Hardware Telemetry:**
   - Process incoming MIDI events (`note_on`, `note_off`, velocity, note density) from USB controllers (Akai MPK mini, 61-key Casio keyboards).
   - Route rolling note density and attack velocity into Three.js EchoSphere shader uniforms.
2. **Minimal Voice-Leading Displacement:**
   - Calculate shortest-path semitone assignment between successive voicings:
     $$C = \sum_{i} |V_{\text{target}}[i] - V_{\text{current}}[i]|$$
   - Prioritize minimal movement over octave jumps.

---

## 7. NEXUS GALLOWAY SOVEREIGN KERNEL & PORTFOLIO PILLARS
1. **GTM-110 3-Panel Matrix Architecture (`nexus_matrix.py` / `gg_os_gallowrage_matrix-v5.py`):**
   -Legacy local 8B / Ollama coping mechanisms (`local_model.py`, `hypothalamus.py`, PyWebView wrappers) are permanently decommissioned.
   - **Panel 1 (Directory Path Cards)**: Live inventory cards for all portfolio repositories with instant `[INSPECT]` and `[EXECUTE]` triggers.
   - **Panel 2 (GTM-110 Terminal Matrix)**: Real-time CLI streaming ("No Silent Worker") for every traversal, build, and test pass.
   - **Panel 3 (Crestline Amygdala & Telemetry HUD)**: Real-time CPU, RAM, and homeostasis vitals (`ws://127.0.0.1:8765/ws`), triggering critical throttle alerts if RAM $> 90\%$ or CPU $> 92\%$.
2. **Model Context Protocol (MCP) Double-Stack:**
   - Standard tools: `server-filesystem`, `server-postgres`, `server-github`.
   - Domain tools: `vane_mcp_server.py` exposing ChromaDB memory bank (`E:\Everything\VANE_Memory_Bank`).
   - Maintain a strict tool budget ceiling of 10–15 active MCP tools per operational partition.
3. **Commercial Portfolio Pillars (Coach Dillman's *"Simple Better"*):**
   - **Chordcraft Studio** (`com.gallowrage.chordcraft`): Closed testing alpha on Google Play (178 countries).
   - **Bastion Tactical** (`com.gallowrage.silotactical`): Turn-based tactical roguelike on Google Play.
   - **Grimoire Cartographer & GG Stick** (`RPG Content Maker`): Turnkey Orange Pi Zero 2W appliance & clean-room tabletop VTT with 1:1 physical TV calibration.
   - **RoofPro SaaS** (`gallowrage/roofpro-saas` / `roofpro-saas.web.app`): Instant solar/roofing estimation engine.
   - **Nexus Galloway / GG_OS Sovereign Kernel**: Unified GTM-110 desktop matrix and developer operating harness.

---

## 8. MASTER ALGORITHMIC & DATA STRUCTURE ROUTING
To eliminate algorithmic bloat, unbounded execution, and high-frequency UI jitter across the ecosystem, all agents must route problem patterns to their optimal deterministic structures:

| Target Subsystem | Architectural Requirement | Optimal Construct / Algorithm | Strict Anti-Pattern (Avoid) |
| :--- | :--- | :--- | :--- |
| **Nexus / Sovereign Kernel** | Multi-branch command & UI card routing | **Dictionary Dispatch Table** | `if`/`elif`/`else` ladders |
| **High-Frequency Telemetry** | Rolling log buffers & sensor telemetry | `collections.deque(maxlen=N)` | `list.pop(0)` (linear shift cost) |
| **RoofPro SaaS Engine** | 3D roof rafter length & pitch surface area | **Secant Pitch Factor** ($M = \sqrt{1 + (P/12)^2}$) | 3D mesh triangulation |
| **Chordcraft Audio** | Polyphonic minimal voice-leading displacement | **Minimal Semitone Movement** ($C = \sum |V_{\text{tgt}} - V_{\text{cur}}|$) | Brute-force permutations |
| **Clean-Room Forensics** | Tamper-evident specification & token verification | **Parent-Chained SHA-256 (`mimitech_omnirea_detective.py`)** | Unsigned ad-hoc markdown notes |
| **Data Ingestion & Takeout** | Unstructured document & vector clustering | **BeautifulSoup + TF-IDF / KMeans** | Fragile regex HTML parsing |
