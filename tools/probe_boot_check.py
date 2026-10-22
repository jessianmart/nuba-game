"""Sonda mínima de boot: a pagina carrega? startMatch existe? o que falhou?
Run: python tools/probe_boot_check.py   (cwd = repo root)
"""
import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.getcwd())
import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location('suite', 'tools/test_e2e_suite.py')
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def http_json(port, path):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=5) as r:
        return json.load(r)


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_boot_')
    proc = subprocess.Popen([
        suite.find_edge_path(), '--headless=new', f'--remote-debugging-port={port}', '--disable-gpu',
        '--window-size=844,390', '--inprivate', f'--user-data-dir={profile}',
        'http://localhost:8080/index.html'
    ])
    time.sleep(4)
    try:
        tabs = None
        for _ in range(20):
            try:
                tabs = http_json(port, '/json')
                break
            except Exception:
                time.sleep(0.5)
        pages = [t for t in tabs if t['type'] == 'page']
        print('tabs:', [(t['title'][:26], t['url'][:56]) for t in pages])
        tab = next((t for t in pages if 'localhost:8080' in t['url']), pages[0])
        c = suite.CDPClient(tab['webSocketDebuggerUrl'])
        await c.connect()

        async def ev(expr):
            raw = await c.eval_js(expr)
            if not isinstance(raw, dict):
                return raw
            if 'value' in raw:
                return raw['value']
            return {'RAW_NO_VALUE': str(raw)[:300]}

        for i in range(24):
            state = await ev("({ rs: document.readyState, t: typeof window.startMatch, "
                             "heroes: typeof window.HERO_KITS, title: document.title, "
                             "err: (window.__BOOT_ERR || null) })")
            print(f"  t={i*2}s -> {state}")
            if isinstance(state, dict) and state.get('t') == 'function':
                print('BOOT OK')
                break
            time.sleep(2)
        errs = c.console_errors[:6]
        print(f'console errors: {len(c.console_errors)}')
        for e in errs:
            print('   ', str(e)[:220])
        c.running = False
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        import shutil  # noqa: E402
        shutil.rmtree(profile, ignore_errors=True)


asyncio.run(main())
