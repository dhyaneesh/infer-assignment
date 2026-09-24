# Retail evaluation monitor

Local technical-review dashboard for the retail evaluator extensions and prompt
experiments. It reads completed benchmark artifacts; refreshing it does not run
simulations or make model calls.

From `bench/tau2-bench`:

```bash
uv run python monitor/scripts/refresh_monitor.py
uv run python -m unittest discover -s monitor/tests -v
npm --prefix monitor ci
npm --prefix monitor run build
python -m http.server 4173 --directory monitor/dist
```

Open `http://localhost:4173`. To verify that the checked-in snapshot is current:

```bash
uv run python monitor/scripts/refresh_monitor.py --check
```

Add future experiments in `experiments.json`. Every experiment must point to a
70-task backfilled results file and a 69-task diagnostic summary excluding task
105. The refresh command fails on missing files, duplicate IDs, mismatched task
populations, or unreconciled legality counts.
