#CSV to PDF tool

Only works ith the tested files in `test_data/`.

1. Install wkhtmltopdf from https://wkhtmltopdf.org/downloads.html for whatever system you have.
2. Install Python from https://www.python.org/ for you exact system.
3. Install requirements from `requirements.txt` via pip (`pip install -r requirements.txt`).
4. run the script via `python main.py generate`; you can pass extra arguments as;
    - `python main.py generate --output_directory=final_reports --file_name=comprehensive_report.pdf`
5. The tool will look into the relative path for {`week_data`, `period_data`, `quarter_data`, `year_data`} directories.
6. Ensure you have `origin.csv` and `dz_origin.csv` updated and present in all these folders too.

hit me up; onesmus.mukewa@gmail.com