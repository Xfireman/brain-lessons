"""Offline native Codex smoke test: synthetic responses, real host hook decisions.

Requires Codex CLI 0.162.1 on PATH. No credentials or remote model calls.
The exact reviewed fixture hook is trusted only in a disposable Codex home.
"""
import argparse
import http.server
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

SOURCE = Path(__file__).resolve().parents[1] / 'src'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cli', type=Path, help='Use an installed brain-lessons executable instead of source')
options = parser.parse_args()
cli_command = [str(options.cli.resolve())] if options.cli else [sys.executable, '-m', 'brain_lessons']
base = Path(tempfile.mkdtemp(prefix='brain-codex-native-')).resolve()


def tool_outputs(value):
    """Only capture synthetic tool results, never dump prompts or tool schemas."""
    found = []
    if isinstance(value, dict):
        if value.get('type') in ('function_call_output', 'custom_tool_call_output', 'tool_result') or value.get('role') == 'tool':
            found.append({key: value[key] for key in ('type', 'role', 'output', 'content') if key in value})
        else:
            for child in value.values():
                found.extend(tool_outputs(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(tool_outputs(child))
    return found


class Client:
    def __init__(self, env, work):
        self.events = []
        self.buffer = b''
        self.seq = 0
        self.err = (work.parent / 'server-error.log').open('ab')
        self.process = subprocess.Popen(['codex', 'app-server', '--stdio'], cwd=work, env=env,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err,
                                        start_new_session=True)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.call('initialize', {'clientInfo': {'name': 'brain-lessons-smoke', 'version': '1'}, 'capabilities': {'experimentalApi': True}})
        self.send({'method': 'initialized', 'params': {}})

    def send(self, value):
        self.process.stdin.write((json.dumps(value) + '\n').encode())
        self.process.stdin.flush()

    def until(self, predicate, seconds=30):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                value = json.loads(line)
                self.events.append(value)
                if predicate(value):
                    return value
            if self.selector.select(min(1, max(0, deadline - time.monotonic()))):
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError('Codex app-server exited')
                self.buffer += chunk
        raise TimeoutError('Codex fixture deadline')

    def call(self, method, params):
        self.seq += 1
        ident = self.seq
        self.send({'id': ident, 'method': method, 'params': params})
        response = self.until(lambda x: x.get('id') == ident)
        if 'error' in response:
            raise RuntimeError({'method': method, 'error': response['error']})
        return response['result']

    def close(self):
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
        self.selector.close()
        self.process.stdin.close()
        self.process.stdout.close()
        self.err.close()


def run_case(enabled):
    case = base / ('enabled' if enabled else 'control')
    work = case / 'project'
    home = case / 'home'
    config_home = home / '.codex'
    work.mkdir(parents=True)
    config_home.mkdir(parents=True)
    (work / '.git').mkdir()
    cli_env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
    cli_env['PYTHONDONTWRITEBYTECODE'] = '1'
    if not options.cli:
        cli_env['PYTHONPATH'] = str(SOURCE)
    def cli(*args):
        p = subprocess.run([*cli_command, '--root', str(work), *args],
                           env=cli_env, text=True, capture_output=True, timeout=15)
        assert p.returncode == 0, p.stderr
    cli('init')
    cli('learn', 'blocked-shell', '--title', 'Synthetic shell rule', '--instruction', 'This fixture command is blocked.',
        '--command', 'printf BRAIN_SHOULD_NOT_RUN', '--sample-command', 'printf BRAIN_SHOULD_NOT_RUN', '--action', 'block')
    cli('learn', 'generated-file', '--title', 'Synthetic generated file', '--instruction', 'Edit the source fixture instead.',
        '--tool', 'Write', '--path', 'generated.py', '--sample-path', 'generated.py', '--action', 'block')
    cli('learn', 'allowed-reminder', '--title', 'Synthetic reminder', '--instruction', 'BRAIN_NATIVE_REMINDER: this is project context.',
        '--command', 'printf BRAIN_ALLOWED', '--sample-command', 'printf BRAIN_ALLOWED')
    if not enabled:
        for path in (work / '.brain/lessons').glob('*.json'):
            value = json.loads(path.read_text())
            value['enabled'] = False
            path.write_text(json.dumps(value))
    cli('install', 'codex', '--with-skill')
    requests = []
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            tools = request.get('tools', [])
            index = len(requests)
            requests.append({'path': self.path, 'reminder_visible': 'BRAIN_NATIVE_REMINDER' in json.dumps(request),
                             'tool_outputs': tool_outputs(request)})
            if index in (0, 2):
                command = 'printf BRAIN_SHOULD_NOT_RUN > blocked.txt' if index == 0 else 'printf BRAIN_ALLOWED > allowed.txt'
                item = {'type': 'function_call', 'id': f'fc_{index}', 'call_id': f'call_{index}', 'name': 'exec_command',
                        'arguments': json.dumps({'cmd': command, 'workdir': str(work)}), 'status': 'completed'}
            elif index == 1:
                item = {'type': 'custom_tool_call', 'id': 'ctc_1', 'call_id': 'call_1', 'name': 'apply_patch',
                        'input': '*** Begin Patch\n*** Add File: generated.py\n+value = 1\n*** End Patch', 'status': 'completed'}
            else:
                item = {'type': 'message', 'id': 'msg_done', 'role': 'assistant', 'status': 'completed',
                        'content': [{'type': 'output_text', 'text': 'Fixture complete.', 'annotations': []}]}
            response = {'id': f'resp_{index}', 'object': 'response', 'created_at': 1, 'model': 'gpt-6-astra', 'status': 'completed',
                        'output': [item], 'usage': {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2,
                        'input_tokens_details': {'cached_tokens': 0}, 'output_tokens_details': {'reasoning_tokens': 0}}}
            events = [({'type': 'response.created', 'response': {**response, 'status': 'in_progress', 'output': []}}),
                      {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
                      {'type': 'response.completed', 'response': response}]
            body = ''.join('event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n' for event in events).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = ('model = "gpt-6-astra"\nmodel_provider = "fixture"\n'
              '[features]\nhooks = true\n'
              '[model_providers.fixture]\nname = "Local fixture"\nwire_api = "responses"\n'
              f'base_url = "http://127.0.0.1:{server.server_port}/v1"\nrequires_openai_auth = false\n'
              f'[projects.{json.dumps(str(work))}]\ntrust_level = "trusted"\n')
    (config_home / 'config.toml').write_text(config)
    env = {'PATH': os.environ['PATH'], 'HOME': str(home), 'CODEX_HOME': str(config_home),
           'LANG': 'en_US.UTF-8', 'TMPDIR': str(case), 'PYTHONDONTWRITEBYTECODE': '1'}
    client = None
    try:
        client = Client(env, work)
        skills = client.call('skills/list', {'cwds': [str(work)], 'forceReload': True})['data'][0]
        assert not skills['errors'], skills['errors']
        discovered = [s for s in skills['skills'] if s['name'] == 'brain-remember']
        assert len(discovered) == 1, discovered
        assert Path(discovered[0]['path']) == work / '.agents/skills/brain-remember/SKILL.md', discovered
        hooks = client.call('hooks/list', {'cwds': [str(work)]})['data'][0]
        assert not hooks['errors'], hooks['errors']
        matching = [h for h in hooks['hooks'] if str(work / '.codex/hooks.json') == h['sourcePath']]
        assert len(matching) == 1, hooks
        entry = matching[0]
        assert entry['trustStatus'] == 'untrusted', entry
        client.close()
        client = None
        # Explicitly trust only this reviewed fixture hash in this disposable home.
        config += f'\n[hooks.state.{json.dumps(entry["key"])}]\ntrusted_hash = {json.dumps(entry["currentHash"])}\n'
        (config_home / 'config.toml').write_text(config)
        client = Client(env, work)
        current = client.call('hooks/list', {'cwds': [str(work)]})['data'][0]['hooks']
        assert any(h['key'] == entry['key'] and h['trustStatus'] == 'trusted' for h in current), current
        started = client.call('thread/start', {'cwd': str(work), 'ephemeral': True, 'approvalPolicy': 'never',
                                              'sandbox': 'workspace-write', 'baseInstructions': 'Run only the synthetic fixture calls. No other tools.'})
        assert started['sandbox']['type'] == 'workspaceWrite', 'Filesystem sandbox must remain enabled'
        assert started['sandbox']['networkAccess'] is False, 'Default tool network isolation must remain enabled'
        tid = started['thread']['id']
        client.call('turn/start', {'threadId': tid, 'input': [{'type': 'text', 'text': 'Run the local synthetic smoke fixture.', 'text_elements': []}]})
        client.until(lambda x: x.get('method') == 'turn/completed', 60)
        runs = [e['params']['run'] for e in client.events if e.get('method') == 'hook/completed']
        result = {'enabled': enabled, 'skill_discovered': True, 'hook_statuses': [r['status'] for r in runs],
                  'blocked_shell_exists': (work / 'blocked.txt').exists(), 'generated_exists': (work / 'generated.py').exists(),
                  'allowed_exists': (work / 'allowed.txt').exists(),
                  'reminder_reached_model_input': any(x['reminder_visible'] for x in requests)}
        (case / 'events.json').write_text(json.dumps(client.events, indent=2))
        print(json.dumps(result), flush=True)
        if not result['allowed_exists'] or result['blocked_shell_exists'] != (not enabled) or result['generated_exists'] != (not enabled):
            diagnostics = []
            for event in client.events:
                item = event.get('params', {}).get('item', {})
                if event.get('method') == 'item/completed' and item.get('type') in ('commandExecution', 'fileChange'):
                    diagnostics.append({k: item.get(k) for k in ('type', 'status', 'exitCode', 'aggregatedOutput')})
                elif event.get('method') == 'error':
                    diagnostics.append(event.get('params', {}))
            details = json.dumps({'events': diagnostics, 'tool_outputs': [x['tool_outputs'] for x in requests]})
            print('Native fixture diagnostics: ' + details[:12000] + (' [truncated]' if len(details) > 12000 else ''), flush=True)
        assert result['allowed_exists'], 'Allowed command did not execute'
        assert result['blocked_shell_exists'] == (not enabled), 'Shell decision not enforced'
        assert result['generated_exists'] == (not enabled), 'Patch decision not enforced'
        assert result['reminder_reached_model_input'] == enabled, 'Reminder not delivered to model input'
        if enabled:
            assert result['hook_statuses'].count('blocked') >= 2, result
        return result
    finally:
        if client is not None:
            (case / 'events.json').write_text(json.dumps(client.events, indent=2))
            client.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


try:
    results = [run_case(False), run_case(True)]
    print(json.dumps({'result': 'PASS', 'cases': len(results)}))
    shutil.rmtree(base)
except Exception:
    print('Evidence: ' + str(base), file=sys.stderr)
    raise
