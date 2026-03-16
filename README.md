```                                                                                                
       ███          █████   █████  ███                       █████   ████  ███   █████   
      ░░░███       ░░███   ░░███  ░░░                       ░░███   ███░  ░░░   ░░███    
        ░░░███      ░███    ░███  ████  █████ █████  ██████  ░███  ███    ████  ███████  
          ░░░███    ░███████████ ░░███ ░░███ ░░███  ███░░███ ░███████    ░░███ ░░░███░   
           ███░     ░███░░░░░███  ░███  ░███  ░███ ░███████  ░███░░███    ░███   ░███    
         ███░       ░███    ░███  ░███  ░░███ ███  ░███░░░   ░███ ░░███   ░███   ░███ ███
       ███░         █████   █████ █████  ░░█████   ░░██████  █████ ░░████ █████  ░░█████ 
      ░░░          ░░░░░   ░░░░░ ░░░░░    ░░░░░     ░░░░░░  ░░░░░   ░░░░ ░░░░░    ░░░░░                                                                                                                                                                           
```

<div align="center">

**> HiveKit**

Command-line interface for managing Hive AI agent experiments

[![PyPI version](https://badge.fury.io/py/hivekit.svg)](https://badge.fury.io/py/hivekit)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[Installation](#installation) • [Quick Start](#quick-start) • [Documentation](./docs/)

</div>

## Installation

```bash
pip install hivekit
```

**Requirements:** Python 3.12+

**From source:**
```bash
git clone https://github.com/hiverge/hivekit.git
cd hivekit
source start.sh
```

## Quick Start

```bash
hive init
hive login
hive edit config
hive create exp my-experiment
hive list exp
```

## Commands

```bash
hive init                  # Initialize configuration
hive login                 # Authenticate
hive edit config           # Edit config file
hive create exp <name>     # Create experiment
hive list exp              # List experiments
hive get exp <name>        # Get experiment details
hive delete exp <name>     # Delete experiment
```

For detailed help: `hive --help` or `hive <command> --help`

## Configuration

HiveKit uses `~/.hive/config.yaml` for experiment configuration. See [hive.yaml](./hive.yaml) for examples.

**Key sections:**
- `repo` - Source repository
- `runtime` - Execution settings
- `sandbox` - Environment configuration
- `provider` - Cloud provider settings

**Custom config:**
```bash
hive create exp prod-exp -f ~/.hive/config-prod.yaml
```

**Environment variables:**
- `EDITOR` - Config editor (default: vim)

## Development

**Setup:**
```bash
git clone https://github.com/hiverge/hivekit.git
cd hivekit
source start.sh
```

**Testing:**
```bash
uv pip install -e ".[test]"
make test
```

**Linting:**
```bash
uv pip install -e ".[lint]"
make lint
```

## Support

- 📖 [Documentation](https://docs.hiverge.io)
- 🐛 [Issues](https://github.com/hiverge/hivekit/issues)

## License

MIT License - see [LICENSE](LICENSE)
