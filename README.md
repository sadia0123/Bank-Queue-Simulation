# Bank Queue Simulation and Waiting Time Analysis

An interactive Streamlit project for exploring how customer arrivals, service duration, and the number of bank counters affect waiting time. It creates **synthetic** customers, animates their journey through a shared queue, exports customer-level data, and compares the mean wait with a chosen benchmark using a two-sided one-sample t-test.

> This is a teaching simulation. It does not use real bank records or represent a particular bank.

## Features

- Navigate between four focused views: **Simulation**, **Results**, **T-Test**, and **Dataset**.
- Set the number of counters, arrival period, mean arrival interval, mean service time, random seed, benchmark, and significance level.
- On the Simulation page, watch customers arrive one by one, see the live waiting count, and pause/resume or scrub the timeline. Choose slow, normal, or fast playback.
- On Results, view per-customer waiting times, a wait-time histogram, and counter throughput.
- Review the one-sample t-test on its own page and inspect/download customer data on the Dataset page.
- Save the latest run in `results/`.

## Project structure

```text
Bank-Queue-Simulation/
├── app.py
├── simulation.py
├── requirements.txt
├── run_app.bat              # Windows launcher
├── README.md
├── .gitignore
├── .streamlit/config.toml   # Forces the light theme the page styling is designed for
└── results/                 # Created automatically; latest run is saved here
```

## Run locally

Python 3.10 or newer is required (Streamlit 1.50 or newer is installed by `requirements.txt`).

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Streamlit prints a local address (usually `http://localhost:8501`) to open in a browser. Change the controls in the left panel and select **Run simulation** to regenerate the data and charts.

## Model and statistical analysis

- Time unit: seconds throughout the app, data, graphs, and test.
- Inter-arrival and service durations are independently generated from exponential distributions. The user-provided values are their means.
- Customers join a single first-come-first-served queue and take the earliest available counter.
- New arrivals stop at the selected arrival-period duration. The simulation then drains the queue so each generated customer has a completed service record.
- A two-sided one-sample t-test evaluates H₀: μ = benchmark against H₁: μ ≠ benchmark at the selected α.
- Limitations of the test: waiting times are right-skewed and often contain many zeros, and consecutive customers' waits are correlated, so the t-test's normality and independence assumptions are only approximate. Treat the p-value as a teaching illustration, not exact inference.
- Runs with more than about 2,000 customers are not animated (the other pages still work).

For example, a five-minute benchmark must be entered as **300 seconds**.

## Output files

After each run, the app writes:

- `results/customer_data.csv` — one row per synthetic customer.
- `results/summary.json` — configuration, descriptive measures, confidence interval, test statistic, p-value, and decision.
- `results/counter_summary.csv` — number served and mean wait for every counter (idle counters show 0).

The app also provides download buttons. Each subsequent run replaces the three local “latest run” files.

## Dataset fields

| Field | Meaning |
|---|---|
| `customer_id` | Unique synthetic customer number |
| `arrival_time` | Arrival time from the start of the simulated day (seconds) |
| `service_time` | Generated service duration (seconds) |
| `waiting_time` | Time between arrival and service start (seconds) |
| `service_start` | Time service begins (seconds) |
| `departure_time` | Time service ends and customer leaves (seconds) |
| `counter_id` | Counter assigned to the customer |

## Publishing to GitHub

Initialize a repository in this folder, commit the files, and push to an account you have permission to use. Generated files in `results/` are recreated on every run.

## Technologies

Python, Streamlit, NumPy, pandas, SciPy, and Plotly.
