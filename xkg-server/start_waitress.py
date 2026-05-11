#!/usr/bin/env python3
"""Start XKG server with auto-load and wait for data before binding port."""
import sys, os, time, threading
sys.path.insert(0, '/tmp/repos/x-knowledge-graph')

from main import app, graph_data, CLI_ARGS, auto_load_data, AUTO_LOAD_DONE

# Trigger auto-load synchronously (don't use thread) so data is ready before serve()
print("[XKG] Pre-loading data before server start...", flush=True)
auto_load_data()
print(f"[XKG] Pre-load done: {len(graph_data.get('actions', []))} actions", flush=True)

# Now serve
from waitress import serve
print("[XKG] Starting server on port 18050...", flush=True)
serve(app, host='0.0.0.0', port=18050, threads=8)
