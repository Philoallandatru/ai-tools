# Manual Tests Directory

This directory contains manual test scripts for development and validation.

## Test Scripts

### Comment Analysis
- **test_comment_sampling.py** - Test intelligent comment sampling strategy
  - Validates sampling logic for different comment counts
  - Tests keyword matching functionality
  - Verifies coverage rates

### Full Analysis
- **test_full_analysis.py** - Full Jira analysis test
  - Tests all 7 analyzers end-to-end
  - Generates complete analysis reports
  - Validates report quality

### Filter Testing
- **test_filter_integration.py** - Test LLM response filters integration
- **test_mock_filter.py** - Test filter with mock data
- **test_reasoning_filter.py** - Test reasoning process filter

### Prompt Optimization
- **test_prompt_optimization.py** - Test prompt optimization strategies
  - Validates high-frequency analyzer prompts
  - Tests prompt template system

## Usage

Run tests from the project root directory:

```bash
# Test comment sampling strategy
python tests/manual/test_comment_sampling.py

# Run full analysis test (requires local LLM service)
python tests/manual/test_full_analysis.py

# Test filters
python tests/manual/test_filter_integration.py
python tests/manual/test_reasoning_filter.py

# Test prompt optimization
python tests/manual/test_prompt_optimization.py
```

## Requirements

- Active virtual environment
- Local LLM service running (for full analysis tests)
- Valid `config.yaml` configuration
- Source Jira data in `sources/` directory

## Notes

- These are manual tests, not automated unit tests
- Some tests require external services (LLM, Jira)
- Test results are saved to `tests/outputs/` directory:
  - `jira/` - Jira analysis results
  - `reports/` - Test reports
  - `archive/` - Historical test files
- Check individual test files for specific requirements
