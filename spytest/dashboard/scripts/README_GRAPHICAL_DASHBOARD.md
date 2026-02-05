# Graphical Dashboard Generator for SPyTest Results

## Overview

The `generate_graphical_dashboard.py` script creates a modern, visually appealing HTML dashboard with graphical representations of SPyTest test results. It scans a log directory root and generates a comprehensive dashboard with:

- **Tabbed interface** for different test modules
- **Progress bars** showing pass/fail/skip percentages
- **Summary statistics** with color-coded cards
- **Detailed test case listings** with interactive tables
- **Modern, responsive design** with gradient headers and smooth animations

## Features

- Modern UI with gradient backgrounds and card-based layout
- Interactive tabs for navigating between test modules
- Visual progress bars with color-coded segments (Pass=Green, Fail=Red, Skip=Yellow)
- Summary cards showing overall statistics
- Detailed test case tables with hover effects
- Fully self-contained HTML file (no external dependencies)
- Mobile-responsive design

## Usage

### Basic Usage

```bash
python3 dashboard/scripts/generate_graphical_dashboard.py \
    --log-root logs/SM_ISCLI_20260204 \
    --out dashboard/sm_iscli_dashboard.html
```

### With Custom Batch Name

```bash
python3 dashboard/scripts/generate_graphical_dashboard.py \
    --log-root logs/SM_ISCLI_20260204 \
    --out dashboard.html \
    --name "SM_ISCLI Test Suite - February 2026"
```

### Help

```bash
python3 dashboard/scripts/generate_graphical_dashboard.py --help
```

## Command-Line Options

- `--log-root <path>`: **Required**. Root directory containing test logs (e.g., `logs/SM_ISCLI_20260204`)
- `--out <path>`: **Required**. Output HTML file path (e.g., `dashboard.html`)
- `--name <text>`: Optional. Custom batch name for dashboard title (default: derived from log-root directory name)

## Expected Directory Structure

The script expects the following directory structure in the log root:

```
logs/SM_ISCLI_20260204/
├── <date>/
│   ├── <feature1>/
│   │   └── <timestamp>/
│   │       └── results_*_stats.csv
│   ├── <feature2>/
│   │   └── <timestamp>/
│   │       └── results_*_stats.csv
│   └── ...
```

OR:

```
logs/SM_ISCLI_20260204/
├── <feature1>/
│   ├── <date1>/
│   │   └── <timestamp>/
│   │       └── results_*_stats.csv
│   └── <date2>/
│       └── <timestamp>/
│           └── results_*_stats.csv
```

The script recursively searches for `results_*_stats.csv` files within the log root directory.

## CSV File Format

The script parses SPyTest CSV stats files with the following expected columns:

- `Module`: Test module name
- `Function`: Test function name
- `Result`: Test result (Pass/PASSED, Fail/Failed/FAILED/SCRIPTERROR, Skip/Skipped/SKIPPED)
- `Test Time`: Test execution time
- `Description`: Test description

## Output Dashboard Features

### 1. Header Section
- Batch name and generation timestamp
- Gradient purple/blue background

### 2. Summary Section
- Four summary cards showing:
  - Total tests
  - Passed tests (with percentage)
  - Failed tests (with percentage)
  - Skipped tests (with percentage)
- Overall progress bar with color-coded segments

### 3. Tabbed Navigation
- One tab per test module/feature
- Click to switch between modules
- Active tab highlighted

### 4. Module Details (Per Tab)
- Module summary with statistics
- Progress bar for the module
- Detailed test case table with:
  - Serial number
  - Test case ID (monospace font)
  - Description
  - Result (color-coded badge)
  - Execution time

## Example Output

```
Dashboard generated successfully: dashboard/sm_iscli_graphical_dashboard.html
Total modules: 10
Total tests: 46
Pass: 33 (71.7%)
Fail: 4 (8.7%)
Skip: 0 (0.0%)
```

## Design Highlights

- **Color Scheme**:
  - Primary: Purple/Blue gradient (#667eea to #764ba2)
  - Pass: Green (#28a745)
  - Fail: Red (#dc3545)
  - Skip: Yellow/Orange (#ffc107)

- **Interactive Elements**:
  - Tab switching with fade-in animation
  - Table row hover effects
  - Responsive card layouts

- **Typography**:
  - Main font: Segoe UI, Tahoma, Geneva, Verdana, sans-serif
  - Code/Test IDs: Courier New (monospace)

## Troubleshooting

### No test results found

**Error**: "No test results found in the specified log directory."

**Solution**:
- Verify the log-root path is correct
- Ensure `results_*_stats.csv` files exist in subdirectories
- Check directory structure matches expected format

### Empty dashboard / No test case details

**Issue**: Dashboard shows modules but no test cases

**Cause**: CSV files may be empty or have incorrect format

**Solution**:
- Verify CSV files have the expected columns (Module, Function, Result, etc.)
- Check that Result column contains valid values (Pass, Fail, Skip)

### Script fails to parse CSV

**Error**: "Warning: Failed to parse {csv_file}"

**Solution**:
- Check CSV file encoding (should be UTF-8)
- Verify CSV file is not corrupted
- Ensure CSV has proper header row

## Comparison with Other Dashboard Scripts

| Feature | `generate_graphical_dashboard.py` | `generate_dashboard.py` |
|---------|----------------------------------|-------------------------|
| Input | Log directory root | Database JSON file |
| Graphical Design | Yes (modern UI) | Basic (simple tables) |
| Progress Bars | Yes | No |
| Tabbed Interface | Yes | No |
| Summary Cards | Yes | No |
| Use Case | Single batch visualization | Historical tracking |

## Integration with Batch Scripts

You can integrate this script into your batch test execution workflow:

```bash
#!/bin/bash

# Run batch tests
./bin/batch_full_run.sh --batch SM_ISCLI --output logs/SM_ISCLI_$(date +%Y%m%d)

# Generate dashboard
python3 dashboard/scripts/generate_graphical_dashboard.py \
    --log-root logs/SM_ISCLI_$(date +%Y%m%d) \
    --out dashboard/sm_iscli_latest.html \
    --name "SM_ISCLI - $(date +%Y-%m-%d)"

echo "Dashboard available at: dashboard/sm_iscli_latest.html"
```

## Browser Compatibility

The dashboard is compatible with modern browsers:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## File Size

The generated HTML file is self-contained and typically:
- Small batches (10-50 tests): ~20-50 KB
- Medium batches (50-200 tests): ~50-200 KB
- Large batches (200+ tests): ~200 KB - 1 MB

## Credits

Developed for the SPyTest framework to provide modern, visual test result dashboards.
