<div align="center">
  <a href="https://flaxon-website.vercel.app/">
    <img src="https://raw.githubusercontent.com/aldanedev-create/flaxon/main/assets/flaxon.png" alt="Flaxon logo" width="200">
  </a>
  <h1>Flaxon</h1>
  <p><strong>The Python full-stack framework.</strong></p>
  <p>Simple Python. Serious Applications.</p>

  <a href="https://pypi.org/project/flaxon/"><img src="https://img.shields.io/pypi/v/flaxon.svg?style=for-the-badge" alt="PyPI version"></a>
  <a href="https://github.com/aldanedev-create/flaxon/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="MIT License"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/code%20style-ruff-000000.svg?style=for-the-badge" alt="Code style: Ruff"></a>
</div>

## Getting Started

Flaxon is an async-first Python full-stack framework with built-in Admin, CMS, authentication, database tools, WebSockets, and a modular application system. Build interactive applications with **Teloce**, complete server-rendered applications with **Jinax**, or combine both.

Requires **Python 3.11+**. In an activated virtual environment:

```bash
python -m pip install "flaxon[standard]"
flaxon new my-project --no-venv
cd my-project
python -m pip install -e .
python management.py makemigrations
python management.py migrate
python management.py setup-admin
flaxon run app:app --reload
```

Open [localhost:8000](http://127.0.0.1:8000/) to see your application. The starter includes a welcome interface, feature modules, custom CLI commands, migrations, and a protected Admin dashboard.

See the [getting started guide](https://github.com/aldanedev-create/flaxon/blob/main/docs/getting-started.md) for the complete setup.

## Documentation

Visit the [Flaxon documentation](https://flaxon-website.vercel.app/docs.html) or browse the [repository guides](https://github.com/aldanedev-create/flaxon/blob/main/docs/index.md).

- [Teloce full-stack applications](https://github.com/aldanedev-create/flaxon/blob/main/docs/api/teloce.md)
- [Jinax server-rendered applications](https://github.com/aldanedev-create/flaxon/blob/main/docs/guides/jinax.md)
- [Admin and CMS](https://github.com/aldanedev-create/flaxon/blob/main/docs/guides/admin-cms.md)
- [Modules](https://github.com/aldanedev-create/flaxon/blob/main/docs/guides/Modules.md)
- [Deployment](https://github.com/aldanedev-create/flaxon/blob/main/docs/deployment.md)

## Examples

Explore the [example applications](https://github.com/aldanedev-create/flaxon/tree/main/examples), including a [modular Teloce shop](https://github.com/aldanedev-create/flaxon/tree/main/examples/teloce_modules_shop), [taskboard](examples/teloce_taskboard/), and [school portal](https://github.com/aldanedev-create/flaxon/tree/main/examples/school_portal).

## Community and Contributing

Created and maintained by **Aldane Hutchinson**. Contributions, documentation improvements, and examples are welcome.

Report bugs and suggest features through [GitHub Issues](https://github.com/aldanedev-create/flaxon/issues). Read the [contribution guidelines](https://github.com/aldanedev-create/flaxon/blob/main/CONTRIBUTING.md) and [Code of Conduct](https://github.com/aldanedev-create/flaxon/blob/main/CODE_OF_CONDUCT.md) to get involved.

## Security

Report vulnerabilities privately following [SECURITY.md](https://github.com/aldanedev-create/flaxon/blob/main/SECURITY.md).

## License

[MIT](LICENSE).

Models and Python migrations are integrated through Tortoise ORM. See the [settings and management guide](docs/guides/orm.md).
