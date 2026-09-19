# RouteIQ

A smart switch for payment gateways, built on top of [Hyperswitch](https://github.com/juspay/hyperswitch).

Businesses that accept payments through several gateways need to decide which one handles each transaction. RouteIQ makes that decision automatically: it learns which gateway performs best and reroutes when one degrades.

<!-- Add an architecture diagram or a screenshot of the dashboard/logs here. -->

## The problem

Static routing rules ("always use gateway A, fall back to B") ignore real performance. And a learning-based router has its own weakness, the **cold-start problem**: with no history, it has no idea which gateway is better, so it has to try them all and can lose transactions while learning.

## How RouteIQ solves it

- **Multi-armed bandit (MAB) server**: treats each gateway as an "arm" and balances exploring less-tried gateways with using the ones that succeed most often
- **Health system**: tracks gateway success rates and latency, and takes unhealthy gateways out of rotation
- **Cold-start handling**: [Describe your approach in one or two sentences, e.g. priors, warm-up period, or health-based seeding]
- **Hyperswitch integration**: [Describe how routing decisions are passed to Hyperswitch]

## Tech stack

| Component | Technology |
|---|---|
| Core routing logic | Rust |
| Services and API | Python, FastAPI |
| Payment orchestration | Hyperswitch |

## Architecture

```
Payment request
      │
      ▼
 Hyperswitch ──► RouteIQ (MAB server + health system)
                      │
                      ▼
              Chosen gateway
```

[Replace with an accurate diagram of your setup.]

## Results

[Add any simulation or test results, e.g. "In a simulated run with 3 gateways, RouteIQ reached X% success versus Y% for static routing." Only include numbers you actually measured.]

## Running locally

```bash
git clone [repo url]
cd routeiq
cp .env.example .env   # fill in your own values

# Rust component
cargo build --release

# Python services
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload   # [adjust to your entry point]
```

## Status

[e.g. "Prototype / built for a hackathon / work in progress"]

## Author

Onaopemipo Samuel Ehalaiye · [GitHub](https://github.com/samuelehalaiye-tech) · [LinkedIn](https://www.linkedin.com/in/onaopemipo-ehalaiye-7b140b424/)
