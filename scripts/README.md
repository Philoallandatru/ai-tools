# Scripts Directory

This directory contains utility scripts for development, testing, and maintenance.

## Scripts

### Analysis & Diagnostics
- **analyze_prompts.py** - Analyze and optimize LLM prompts
- **diagnose_confluence.py** - Diagnose Confluence connection issues
- **health-check.py** - System health check script

### Testing
- **run_e2e_tests.py** - Run end-to-end tests
- **test_all_commands.bat** - Test all commands (Windows)
- **test_all_commands.sh** - Test all commands (Unix/Linux)

### Utilities
- **download_modelscope_model.py** - Download models from ModelScope
- **scheduler.py** - Task scheduler utility

## Usage

Run scripts from the project root directory:

```bash
# Example: Run health check
python scripts/health-check.py

# Example: Analyze prompts
python scripts/analyze_prompts.py

# Example: Run E2E tests
python scripts/run_e2e_tests.py
```

## Notes

- All scripts should be run from the project root directory
- Make sure to activate the virtual environment before running scripts
- Check individual script files for specific usage instructions
