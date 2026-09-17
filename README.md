# atloscli

Command line tool for Atlos.

## Install

```sh
pip install -e ".[dev]"
```

## Usage

Store your Atlos project API token in `~/.config/atlos`:

```sh
mkdir -p ~/.config && install -m 600 /dev/null ~/.config/atlos
$EDITOR ~/.config/atlos
```

Then:

```sh
atloscli incidents          # slug, status, description (tab-separated)
atloscli incidents --json   # one JSON object per line
atloscli incident 7X7YFH    # all fields of one incident
atloscli incident 7X7YFH --json
atloscli materials          # source material: id, URL, title (tab-separated)
atloscli materials --json   # one JSON object per line
```

## Development

```sh
make install   # create .venv and install with dev dependencies (needs uv)
make lint      # ruff check + format check
make format    # apply ruff fixes and formatting
make test      # run pytest (file tests need exiftool)
make check     # lint + test
```
