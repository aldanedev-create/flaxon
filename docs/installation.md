# Installation

## Requirements

Before installing Flaxon, ensure your system has:

- **Python 3.11** or newer
- **pip** (Python package installer)

You can verify your Python version with:

```bash
python --version
```

or

```bash
python3 --version
```

---

# Installing Flaxon

## Basic Installation

Install the core framework:

```bash
pip install flaxon
```

This installs Flaxon with its core functionality and no optional extras.

---

# Optional Feature Sets

Flaxon uses optional dependency groups so you only install what you need.

## Standard Installation

Includes the recommended packages for most projects.

```bash
pip install "flaxon[standard]"
```

---

## ASGI Server Support

Installs an ASGI server for running production applications.

```bash
pip install "flaxon[server]"
```

---

## Template Support (Jinax)

Adds support for server-side HTML rendering with Jinax.

```bash
pip install "flaxon[templates]"
```

---

## Development Tools

Installs tools useful for contributing to Flaxon.

```bash
pip install "flaxon[dev]"
```

Includes development utilities such as:

- Pytest
- Ruff
- MyPy
- Development dependencies

---

## Install Everything

Install all commonly used features.

```bash
pip install "flaxon[standard,dev,server]"
```

---

# Optional Dependency Groups

| Group | Description |
|--------|-------------|
| `server` | ASGI server support (Uvicorn) |
| `templates` | Jinax template rendering (Jinja2) |
| `standard` | Recommended packages for most applications |
| `dev` | Development tools (Pytest, Ruff, MyPy, etc.) |
| `docs` | Documentation tools (MkDocs) |

---

# Verify the Installation

Check that Flaxon is installed correctly.

```bash
python -c "import flaxon; print(flaxon.__version__)"
```

You should see the installed version printed to the terminal.

---

# Create Your First Project

After installation, create your application.

```python
from flaxon import Flaxon

app = Flaxon("hello-world")

@app.get("/")
async def home():
    return {
        "message": "Hello, Flaxon!"
    }
```

Run the application:

```bash
flaxon run app:app --reload
```

Visit:

```
http://localhost:8000
```

---

# Virtual Environments

Using a virtual environment is strongly recommended.

Create one:

```bash
python -m venv .venv
```

Activate it.

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows (Command Prompt)

```cmd
.venv\Scripts\activate.bat
```

### Windows (PowerShell)

```powershell
.venv\Scripts\Activate.ps1
```

Then install Flaxon:

```bash
pip install flaxon
```

---

# Development Installation

If you want to contribute to Flaxon or work from source:

Clone the repository:

```bash
git clone https://github.com/aldanedev-create/Flaxon-Backend-Framework.git
```

Move into the project directory:

```bash
cd Flaxon-Backend-Framework
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

Linux/macOS

```bash
source .venv/bin/activate
```

Windows

```powershell
.venv\Scripts\Activate.ps1
```

Install Flaxon in editable mode:

```bash
pip install -e ".[standard,dev]"
```

Run the test suite:

```bash
pytest
```

---

# Upgrading Flaxon

To upgrade to the latest version:

```bash
pip install --upgrade flaxon
```

Or upgrade with optional features:

```bash
pip install --upgrade "flaxon[standard]"
```

---

# Uninstalling

Remove Flaxon from your environment:

```bash
pip uninstall flaxon
```

---

# Troubleshooting

### `pip` is not recognized

Ensure Python is installed and added to your system's `PATH`.

---

### Python version is too old

Flaxon requires **Python 3.11 or newer**.

Check your version:

```bash
python --version
```

---

### Virtual environment not activated

Activate your virtual environment before installing packages.

---

### Permission denied

Try upgrading `pip` first:

```bash
python -m pip install --upgrade pip
```

Then reinstall Flaxon.

---

# Next Steps

Now that Flaxon is installed, continue with:

- **Quick Start** — Build your first application.
- **Configuration** — Configure your project.
- **Routing** — Learn how to define routes.
- **Architecture** — Understand how Flaxon works.
- **Deployment** — Prepare your application for production.

You're ready to start building modern Python applications with Flaxon.
## Build the complete application

After installation, follow the [full-stack quick start](quickstart.md).
Teloce compiles the interface and Flaxon serves it alongside your APIs.
See [10 lessons](fullstack/index.md) for the full application workflow.
