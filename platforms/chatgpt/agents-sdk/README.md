# OpenAI Agents SDK example

Runnable-looking example that wires HireMesh workers as Agents with handoffs.

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=...
export HIREMESH_HOME=/path/to/data
python hiremesh_agents.py
```

## Scheduling

- cron / launchd invoking `python hiremesh_agents.py --worker scout` (etc.)
- Optionally, if you use ChatGPT **scheduled tasks** / automation features in your account, point them at the same prompts — treat that as optional and product-dependent.

## Notes

Tool functions wrap the repo's `scripts/*.py`. Browser/Gmail actions remain stubs for you to bind to your own automation.
