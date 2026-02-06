================================================================================
SPyTest Failure Analysis Report Generator - README
================================================================================

Author: Athira / Claude Code
Date: 2026-02-06
Version: 1.0

================================================================================
OVERVIEW
================================================================================

The Failure Analysis Report Generator is a Python utility that automatically
analyzes SPyTest test execution logs and generates comprehensive CSV reports
containing testcase-level failure details with extracted error snippets from
log files.

This tool is designed to streamline the debugging process by aggregating all
failure information from multiple test batches into a single, easily navigable
CSV file.

================================================================================
FEATURES
================================================================================

- Automatically scans SPyTest log directories for test results
- Extracts all failed test cases from testcases.csv files
- Locates corresponding module log files for each failure
- Extracts relevant error snippets (up to 500 characters)
- Generates detailed CSV reports with:
  * Test batch name
  * Feature and test case information
  * Test function and module paths
  * Result type and execution timestamp
  * Error descriptions and log snippets
  * Full log file paths for deep analysis
- Provides summary statistics by batch, result type, and feature
- Reusable for any SPyTest log directory structure

================================================================================
INSTALLATION
================================================================================

No installation required. The script uses standard Python 3 libraries:
- os
- sys
- csv
- re
- pathlib
- datetime
- typing

Prerequisites:
- Python 3.8 or higher
- SPyTest log directory with results files

================================================================================
USAGE
================================================================================

Basic Syntax:
-------------
python3 generate_failure_analysis.py <log_root_directory> [output_csv]

Parameters:
-----------
  log_root_directory  : Path to the root directory containing SPyTest logs
                        (e.g., ./logs/SM_ISCLI_20260205)

  output_csv          : (Optional) Custom output CSV filename
                        If not specified, auto-generates filename like:
                        <log_dir_name>_failure_analysis_<timestamp>.csv

Examples:
---------

1. Auto-generate output filename:

   python3 ./utils/generate_failure_analysis.py ./logs/SM_ISCLI_20260205

   Output: SM_ISCLI_20260205_failure_analysis_20260206_143052.csv

2. Specify custom output filename:

   python3 ./utils/generate_failure_analysis.py \
       ./logs/SM_ISCLI_20260205 \
       sm_iscli_failures.csv

3. Analyze different log directory:

   python3 ./utils/generate_failure_analysis.py ./logs/NTP_REGRESSION_20260206

4. Run from different location:

   cd /home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest
   python3 ./utils/generate_failure_analysis.py ./logs/SM_ISCLI_20260205

================================================================================
LOG DIRECTORY STRUCTURE
================================================================================

Expected log directory structure:

./logs/SM_ISCLI_20260205/
├── BATCH_1_NAME/
│   └── 220323/
│       ├── results_*_testcases.csv       <- Parsed for failures
│       ├── module_*.log                  <- Error snippet extraction
│       └── other result files
├── BATCH_2_NAME/
│   └── 220323/
│       └── ...
└── dashboard/

The script will:
1. Find all results_*_testcases.csv files recursively
2. Parse each CSV to identify failures (Fail, ConfigFail, EnvFail, etc.)
3. Locate corresponding module log files
4. Extract error context from logs

================================================================================
OUTPUT FORMAT
================================================================================

Generated CSV Columns:
----------------------

1.  Batch                - Test batch name (e.g., SM_ISCLI_13_IBGP_MULTIPATH)
2.  Feature              - Feature being tested
3.  Test Case ID         - Unique test case identifier
4.  Test Function        - Python test function name
5.  Module               - Test module file path
6.  Result               - Failure type (Fail, ConfigFail, EnvFail, etc.)
7.  Result Type          - Mapped or NotMapped
8.  Executed On          - Timestamp of test execution
9.  Description          - Short failure description from test
10. Devices              - Test devices used (e.g., "spine02, leaf01")
11. Error Snippet        - Extracted error logs (up to 500 characters)
12. Log File Path        - Full path to detailed module log file

Sample Output:
--------------

Batch,Feature,Test Case ID,Test Function,Module,Result,Result Type,...
SM_ISCLI_74_HOSTNAME_VALIDATION,==UNKNOWN==,TestHostnameValidation.test_hostname_change_verify,TestHostnameValidation.test_hostname_change_verify,Bug-fix/test_hostname_validation.py,Fail,NotMapped,2026-02-05 17:13:44,Hostname DVT1 not found in 'show version',"spine02, leaf01","2026-02-05 17:17:49  111 T0000: INFO  [D1-spine02] FCMD: date...",logs/SM_ISCLI_20260205/SM_ISCLI_74_HOSTNAME_VALIDATION/220323/results_2026_02_05_22_40_58_mlog_Bug-fix_test_hostname_validation.log

================================================================================
SUMMARY STATISTICS
================================================================================

After generating the CSV, the script displays summary statistics:

Example Output:
---------------

============================================================
FAILURE ANALYSIS SUMMARY
============================================================

Failures by Batch:
  SM_ISCLI_74_HOSTNAME_VALIDATION                      3
  SM_ISCLI_12_SHOW_IP_INTERFACE                        3
  SM_ISCLI_46_PORT_BREAKOUT                            2
  SM_ISCLI_73_VRF_INTERFACE_VALIDATION                 1
  SM_ISCLI_82_BGP_VRF_VALIDATION                       1

Failures by Result Type:
  Fail                  12
  ConfigFail             2
  EnvFail                1

Failures by Feature:
  ==UNKNOWN==                      9
  IP Interface                     3
  BGP                              2

============================================================

================================================================================
ERROR SNIPPET EXTRACTION
================================================================================

The script automatically extracts relevant error context from log files by:

1. Locating the module log file for each failed test
2. Searching for common failure patterns:
   - Report(Fail, ...)
   - FAILED test_*
   - AssertionError
   - Error:
   - Exception:
   - Traceback
   - "failed to give prompt"
   - "not found in"
   - "Configuration failed"

3. Capturing 5 lines before and after the error for context
4. Limiting snippets to 500 characters for CSV compatibility

If specific error patterns are not found, the script includes the last 10
lines of the log file.

================================================================================
USE CASES
================================================================================

1. Quick Failure Overview:
   - Run script after batch test execution
   - Get instant summary of all failures
   - Identify problematic batches or features

2. Debugging Support:
   - CSV contains error snippets for quick diagnosis
   - Log file paths provided for deep analysis
   - Can be shared with team for collaborative debugging

3. Regression Analysis:
   - Compare failure reports across different runs
   - Track failure trends over time
   - Identify recurring issues

4. Test Report Generation:
   - Import CSV into Excel/Google Sheets
   - Create pivot tables and charts
   - Generate executive summaries

5. CI/CD Integration:
   - Run script automatically after test execution
   - Archive failure reports
   - Trigger notifications for high failure counts

================================================================================
VIEWING THE REPORT
================================================================================

Recommended Tools:
------------------

1. Microsoft Excel / LibreOffice Calc:
   - Open CSV file directly
   - Use filters on columns
   - Create pivot tables
   - Sort by batch, feature, or result type

2. Command Line:
   - View with column:
     column -t -s',' SM_ISCLI_20260205_failure_analysis.csv | less -S

   - Count failures by batch:
     cut -d',' -f1 SM_ISCLI_20260205_failure_analysis.csv | sort | uniq -c

3. Python/Pandas:
   import pandas as pd
   df = pd.read_csv('SM_ISCLI_20260205_failure_analysis.csv')
   print(df.groupby('Batch')['Result'].value_counts())

4. Online CSV Viewers:
   - https://www.convertcsv.com/csv-viewer-editor.htm
   - https://csvfiddle.io/

================================================================================
TROUBLESHOOTING
================================================================================

Issue: Script says "No failures found!"
Solution:
  - Verify log directory path is correct
  - Check that results_*_testcases.csv files exist
  - Confirm tests actually failed (not all passed)

Issue: Error snippets show "Log file not found"
Solution:
  - Module log files may have different naming pattern
  - Check log directory structure matches expected format
  - Verify module_*.log files exist in batch directories

Issue: CSV shows truncated error snippets
Solution:
  - This is intentional (500 char limit for CSV)
  - Use "Log File Path" column to view full logs

Issue: Permission denied error
Solution:
  - Ensure read permissions on log directory
  - Check Python script has execute permissions:
    chmod +x generate_failure_analysis.py

================================================================================
CUSTOMIZATION
================================================================================

You can modify the script to:

1. Adjust error snippet length:
   - Edit line containing: if len(error_snippet) > 500
   - Change 500 to desired character limit

2. Add custom error patterns:
   - Edit failure_patterns list in extract_error_from_module_log()
   - Add new regex patterns for your error types

3. Change log file search patterns:
   - Edit log_files = list(log_dir.glob(...))
   - Modify glob pattern to match your log naming

4. Add additional CSV columns:
   - Extend fieldnames list
   - Add corresponding data to row dict

================================================================================
INTEGRATION WITH DASHBOARD
================================================================================

The failure analysis CSV complements the SPyTest HTML dashboard:

Dashboard HTML: Graphical overview, pass/fail charts, test duration
Failure CSV:    Detailed failure analysis, error snippets, log paths

Workflow:
1. Review dashboard HTML for high-level overview
2. Run failure analysis script for detailed debugging
3. Use CSV to identify specific failures
4. Navigate to log files using provided paths

================================================================================
SCRIPT LOCATION
================================================================================

Script Path:
/home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest/utils/generate_failure_analysis.py

Quick Access:
cd /home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest
python3 ./utils/generate_failure_analysis.py --help

================================================================================
SUPPORT AND FEEDBACK
================================================================================

For issues, enhancements, or questions:
- Check this README first
- Review script docstring: python3 generate_failure_analysis.py (no args)
- Examine script source code for implementation details

Common enhancements:
- JSON output format
- Excel file generation with formatting
- Email report distribution
- Integration with Jira/bug tracking systems
- Historical trend analysis

================================================================================
VERSION HISTORY
================================================================================

v1.0 (2026-02-06):
  - Initial release
  - CSV report generation
  - Error snippet extraction
  - Summary statistics
  - Batch/feature/result type analysis

================================================================================
EXAMPLE WORKFLOW
================================================================================

Complete Example:
-----------------

# Step 1: Run batch tests
cd /home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest
./batch_sm_iscli.sh

# Step 2: Wait for completion, note log directory
# Output: Logs Root : ./logs/SM_ISCLI_20260206

# Step 3: Generate failure analysis
python3 ./utils/generate_failure_analysis.py ./logs/SM_ISCLI_20260206

# Step 4: Review output
✓ Failure analysis report generated: SM_ISCLI_20260206_failure_analysis_20260206_150432.csv
  Total failures analyzed: 8

# Step 5: Open CSV in Excel or view in terminal
libreoffice SM_ISCLI_20260206_failure_analysis_20260206_150432.csv

# Step 6: For specific failure, check full log
# (Use Log File Path from CSV)
less /home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest/logs/SM_ISCLI_20260206/SM_ISCLI_74_HOSTNAME_VALIDATION/220323/results_2026_02_06_22_40_58_mlog_Bug-fix_test_hostname_validation.log

================================================================================
NOTES
================================================================================

- Script is read-only and does not modify any log files
- Multiple runs on same log directory will create new timestamped CSVs
- CSV files can be large for batches with many failures
- Error snippets prioritize recent errors (last 500 lines of log)
- Script handles Unicode/special characters in log files

================================================================================
END OF README
================================================================================
