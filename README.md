# SEFA Dashboard – Smart Edge AI Farming Architecture

A local, internet-independent farming dashboard prototype based on the
SEFA architecture document. Runs entirely on a laptop, Raspberry Pi, or
any machine with Python 3.9+.

## What it does

- Simulates 16 distributed sensor nodes across a 4×4 field grid (A1–D4)
- Collects moisture, temperature, pH, EC, and battery readings
- Generates simulated Edge AI crop analysis (disease / pest / stress)
- Applies a rule-based decision engine to classify each zone
- Stores everything in a local SQLite database
- Displays everything in a 6-page Streamlit dashboard

## Pages

| Page | Purpose |
|---|---|
| 🏠 Live Field Status | Current zone status + zones needing action |
| 🗺 Zone Map | Color-coded field grid + moisture heatmap |
| 🚨 Alerts | All alerts, filtered by severity |
| 🤖 AI Monitoring | Per-zone AI predictions + confidence |
| 📈 Historical Trends | Moisture/temp over time for a chosen zone |
| 🌱 Analytics | Water/labour savings estimates + distributions |

## Run

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 0

