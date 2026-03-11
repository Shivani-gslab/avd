# CLI Generators: Migrating from Jinja2 to Python

## Context

AVD generates EOS device configurations from structured YAML data.
Previously this was done via **209 Jinja2 templates** (`.j2` files).
The migration replaces them with **Python generator classes** — one per config section.

**Current state:** 2 generators done (`boot.py`, `config_comment.py`), 207 remaining.

---

## Directory Structure

```
cli_generators/          ← NEW (Python approach)
├── base.py              ← Framework: CliConfig, CliGenerator, @cli_config_contributor
├── boot.py              ← Migrated from boot.j2
├── config_comment.py    ← Migrated from config_comment.j2
└── __init__.py

j2templates/eos/         ← LEGACY (being replaced)
├── boot.j2
├── aaa.j2
└── ... (209 files total)
```

---

## Core Framework (`base.py`)

### 1. `CliConfig` — Output Accumulator

Builds the final config string incrementally.

```python
class CliConfig:
    def __init__(self) -> None:
        self._lines: list[str] = []

    def append(self, line: str | None) -> None:
        """Adds a line. Multi-line strings are auto-split on \\n."""
        if line:
            if "\n" in line:
                self._lines.extend(line.split("\n"))
            else:
                self._lines.append(line)

    def get_config(self) -> str:
        return "\n".join(self._lines)
```

### 2. `@cli_config_contributor` — Decorator

Marks methods as config contributors so `render()` can discover and call them automatically.

```python
@cli_config_contributor
def boot(self) -> None:
    ...

# With optional conditional execution:
@cli_config_contributor(toggle_and_value=("event_monitor.enabled", True))
def event_monitor(self) -> None:
    ...
```

The decorator sets `_is_cli_config_contributor = True` on the method.
The `toggle_and_value` variant wraps the method to skip it unless the condition is met.

### 3. `CliGenerator` — Base Class

```python
class CliGenerator:
    def __init__(self, structured_config: EosCliConfigGen | dict) -> None:
        if isinstance(structured_config, dict):
            self.data = EosCliConfigGen(**structured_config)
        else:
            self.data = structured_config
        self.cli_config = CliConfig()

    def render(self) -> str:
        for method in self.cli_config_methods():
            method(self)
        return self.cli_config.get_config()

    @classmethod
    def cli_config_methods(cls) -> list:
        """Discover all methods marked with @cli_config_contributor via reflection."""
        return [
            getattr(cls, key)
            for key in dir(cls)
            if getattr(getattr(cls, key), "_is_cli_config_contributor", False)
        ]
```

---

## Execution Flow

```
BootGenerator(config_dict)
    │
    ├── __init__: converts dict → EosCliConfigGen (Pydantic model)
    │             creates empty CliConfig()
    │
    └── render()
        ├── discover @cli_config_contributor methods via reflection
        ├── call each method → method appends to self.cli_config
        └── return cli_config.get_config()  →  "!\nboot secret sha512 mykey"
```

Each generator is **single-use by design** — one instantiation, one `render()` call.

---

## Side-by-Side: `boot.j2` vs `boot.py`

### Jinja2 (`boot.j2`) — 15 lines

```jinja2
{% if boot is arista.avd.defined %}
!
{%     if boot.secret.key is arista.avd.defined %}
{%         if boot.secret.hash_algorithm is arista.avd.defined('md5') %}
{%             set hash_algorithm = 5 %}
{%         endif %}
boot secret {{ hash_algorithm | arista.avd.default('sha512') }} {{ boot.secret.key | arista.avd.hide_passwords(hide_passwords) }}
{%     endif %}
{% endif %}
```

### Python (`boot.py`) — same logic

```python
class BootGenerator(CliGenerator):

    @cli_config_contributor
    def boot(self) -> None:
        if not get_v2(self.data, "boot.secret.key"):
            return

        hide_passwords_enabled = get_v2(self.data, "eos_cli_config_gen_configuration.hide_passwords", default=False)

        hash_algorithm = "sha512"
        if get_v2(self.data, "boot.secret.hash_algorithm") == "md5":
            hash_algorithm = "5"

        key = hide_passwords(get_v2(self.data, "boot.secret.key"), hide_passwords_enabled)

        self.cli_config.append("!")
        self.cli_config.append(f"boot secret {hash_algorithm} {key}")
```

**Same output. Standard Python. No custom template syntax.**

---

## Migration Benefits

| Pain Point in Jinja2 | Python Solution |
|----------------------|-----------------|
| Custom filters (`arista.avd.defined`, `arista.avd.default`) | Standard Python (`if not x`, `or default`) |
| No IDE autocomplete | Full type hints + Pydantic models (`self.data.boot.secret.key`) |
| Runtime template errors | Type errors caught at import/lint time |
| Cannot unit test templates directly | Unit test each generator class independently |
| Nested `{% if %}{% for %}` becomes unreadable | Clean Python control flow |
| No Python debugger support | Standard `pdb` / IDE breakpoints work |

---

## Migration Pattern (for each new generator)

```python
from pyavd._utils.get import get_v2
from .base import CliGenerator, cli_config_contributor


class [Feature]Generator(CliGenerator):
    """Generator for [feature] CLI configuration. Migrated from [feature].j2"""

    @cli_config_contributor
    def [feature](self) -> None:
        # 1. Guard: return early if config not present
        if not get_v2(self.data, "path.to.key"):
            return

        # 2. Extract values with defaults
        value = get_v2(self.data, "path.to.key", default="default_val")

        # 3. Build CLI output
        self.cli_config.append("!")
        self.cli_config.append(f"feature {value}")
```

---

## Enhancement Points

### 1. `cli_config.clear()` is unnecessary
`render()` contains `self.cli_config.clear()` but each generator is instantiated and called once — `_lines` is always `[]` when `render()` runs. It's dead code that adds confusion.

### 2. Generator discovery is manual
Currently generators must be manually imported in `__init__.py`. This could be automated via a plugin/registry pattern.

### 3. `get_v2()` vs direct model access
`get_v2(self.data, "boot.secret.key")` works but bypasses Pydantic's type system.
Direct access (`self.data.boot.secret.key`) gives IDE autocomplete and type checking — preferred where possible.

### 4. Method execution order depends on `dir()`
`dir()` returns names alphabetically. Execution order of contributor methods is implicit. A `_keys()` override or explicit ordering mechanism would make this explicit.

---

## Key Files

| File | Purpose |
|------|---------|
| `cli_generators/base.py` | Framework: `CliConfig`, `CliGenerator`, `@cli_config_contributor` |
| `cli_generators/boot.py` | Example: boot secret generator |
| `cli_generators/config_comment.py` | Example: config comment generator |
| `j2templates/eos/boot.j2` | Legacy template (reference for migration) |
| `pyavd/_utils/get.py` | `get_v2()` — safe nested attribute access |
| `pyavd/j2filters/hide_passwords.py` | Password hiding utility (reused in Python generators) |
| `schema/__init__.py` | Pydantic models (`EosCliConfigGen`) — structured config data |
