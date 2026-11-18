import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

CLI = Path(__file__).resolve().parents[1] / 'bin/xc'
loader = importlib.machinery.SourceFileLoader('xc', str(CLI))
spec = importlib.util.spec_from_loader('xc', loader)
xc = importlib.util.module_from_spec(spec)
loader.exec_module(xc)


@unittest.skipUnless(shutil.which('tmux'), 'tmux required')
class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xc-test-')
        self.root = Path(self.tmp.name)
        self.env = dict(os.environ, HOME=str(self.root), XDG_STATE_HOME=str(self.root/'state'), TMUX_TMPDIR=str(self.root), CODEX_HOME=str(self.root/'codex'), LOG=str(self.root/'events'))
        self.env.pop('TMUX', None)
        (self.root/'bin').mkdir()
        for engine in ('codex', 'claude', 'copilot', 'devin', 'agy'):
            script = self.root/'bin'/engine
            script.write_text('#!/usr/bin/env python3\nimport os,sys,json\nwith open(os.environ["LOG"],"a") as f:f.write(json.dumps({"id":os.environ["XCONTROL_AGENT"],"cwd":os.getcwd(),"args":sys.argv[1:],"config":os.environ["XCONTROL_CONFIG"]})+"\\n")\nfor line in sys.stdin:\n with open(os.environ["LOG"],"a") as f:f.write(json.dumps({"message":line.strip()})+"\\n")\n')
            script.chmod(0o755)
        self.env['PATH'] = str(self.root/'bin') + ':' + os.environ['PATH']
        (self.root/'android space').mkdir()
        (self.root/'ios').mkdir()
        self.config = self.root/'demo.agents'
        self.config.write_text('name="demo"\n[[agents]]\nid="android"\nfolder="android space"\nagent="codex"\n[[agents]]\nid="ios"\nfolder="ios"\nagent="claude"\n')

    def tearDown(self):
        subprocess.run(['tmux', 'kill-server'], env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.tmp.cleanup()

    def cli(self, *args, ok=True, cwd=None):
        result = subprocess.run([str(CLI), *map(str,args)], env=self.env, text=True, capture_output=True, timeout=10, cwd=cwd)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def events(self):
        path = self.root/'events'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def wait(self, predicate):
        deadline = time.monotonic()+5
        while time.monotonic()<deadline:
            if predicate(): return
            time.sleep(.05)
        self.fail('Timed out waiting for fake agent event')

    def start(self):
        self.cli(self.config, '--detach')
        self.wait(lambda:len(self.events())==2)

    def test_check_without_starting(self):
        self.cli('check', self.config)
        self.assertEqual(self.events(), [])

    def test_socket_denial_is_not_reported_as_missing_group(self):
        fake = self.root/'bin'/'tmux'
        fake.write_text('#!/usr/bin/env python3\nimport sys\nprint("error connecting to /tmp/tmux-test/default (Operation not permitted)",file=sys.stderr)\nsys.exit(1)\n')
        fake.chmod(0o755)
        result = self.cli('status', self.config, ok=False)
        self.assertIn('Cannot access the tmux socket', result.stderr)
        self.assertNotIn('Project group is not running', result.stderr)
        self.assertIn('normal terminal', result.stderr)

    def test_mixed_launch_reattach_and_stop(self):
        self.start()
        events = self.events()
        self.assertEqual({e['id'] for e in events}, {'android','ios'})
        android = next(e for e in events if e['id']=='android')
        self.assertEqual(android['cwd'], str(self.root/'android space'))
        self.assertIn('--no-daemon', android['args'])
        self.assertEqual(next(e for e in events if e['id']=='ios')['args'], ['--continue'])
        self.cli(self.config, '--detach')
        self.assertEqual(len(self.events()), 2)
        status = self.cli('status',self.config).stdout
        self.assertIn('android',status)
        self.assertIn('ios',status)
        self.cli(self.config, '-k')
        self.cli('status',self.config,ok=False)

    def test_message_is_literal(self):
        self.start()
        text = 'Review $(touch /tmp/xc-must-not-exist) and `echo hi` safely'
        self.cli('send',self.config,'ios',text)
        self.wait(lambda:any(e.get('message')==text for e in self.events()))
        self.cli('send',self.config,'unknown','hello',ok=False)

    def test_agent_and_shell_panes_follow_tmux_exit_setting(self):
        self.start()
        def tmux(*args):
            return subprocess.check_output(['tmux', *args], env=self.env, text=True).strip()
        rows = self.cli('status', self.config).stdout.splitlines()
        agents = [row.split('\t')[1] for row in rows]
        for target in agents:
            self.assertEqual(tmux('show-options', '-pqv', '-t', target, 'remain-on-exit'), '')
        shell = tmux('split-window', '-t', agents[0], '-P', '-F', '#{pane_id}', 'sleep 0.2')
        self.wait(lambda: shell not in tmux('list-panes', '-a', '-F', '#{pane_id}').splitlines())
        tmux('send-keys', '-t', agents[0], 'C-d')
        self.wait(lambda: agents[0] not in tmux('list-panes', '-a', '-F', '#{pane_id}').splitlines())

    def test_duplicate_workspace_other_group_rejected(self):
        self.start()
        other = self.root/'other.agents'
        other.write_text(self.config.read_text().replace('name="demo"','name="other"'))
        self.cli(other,'--detach',ok=False)
        self.assertEqual(len(self.events()),2)

    def test_independent_group(self):
        self.start()
        (self.root/'other').mkdir()
        other = self.root/'other.agents'
        other.write_text('name="other"\n[[agents]]\nid="other"\nfolder="other"\n')
        self.cli(other,'--detach')
        self.wait(lambda:len(self.events())==3)
        self.cli('stop',other)
        self.assertIn('android',self.cli('status',self.config).stdout)

    def test_reject_executable_fields_and_missing_folder(self):
        self.config.write_text('name="demo"\ncommand="touch evil"\n')
        self.cli('check',self.config,ok=False)
        self.config.write_text('[[agents]]\nid="a"\nfolder="absent"\n')
        self.cli('check',self.config,ok=False)

    def test_dead_pane_rejects_message(self):
        self.start()
        pane = self.cli('status',self.config).stdout.splitlines()[0].split('\t')[1]
        subprocess.run(['tmux','set-option','-p','-t',pane,'remain-on-exit','on'],env=self.env,check=True)
        subprocess.run(['tmux','send-keys','-t',pane,'C-c'],env=self.env,check=True)
        self.wait(lambda:'exited' in self.cli('status',self.config).stdout)
        self.cli('send',self.config,'android','do not run in shell',ok=False)

    def test_copilot_workspace_session(self):
        self.config.write_text(self.config.read_text().replace('agent="claude"', 'agent="copilot"'))
        self.start()
        args = next(e for e in self.events() if e['id']=='ios')['args']
        self.assertEqual(args[0], '--session-id')
        import uuid
        self.assertEqual(str(uuid.UUID(args[1])), args[1])
        self.cli('stop', self.config)
        (self.root/'events').unlink()
        self.start()
        self.assertEqual(next(e for e in self.events() if e['id']=='ios')['args'], args)

    def test_custom_cli_literal_args_and_messages(self):
        args = ['--example', '$(touch /tmp/xc-no-shell)', 'value with spaces']
        import json
        toml_args = json.dumps(args)
        self.config.write_text(self.config.read_text().replace('agent="claude"', 'agent="devin"\nargs=' + toml_args))
        self.start()
        self.assertEqual(next(e for e in self.events() if e['id']=='ios')['args'], args)
        self.cli('send', self.config, 'ios', 'Review the API contract')
        self.wait(lambda:any(e.get('message')=='Review the API contract' for e in self.events()))

    def test_custom_cli_rejects_unknown_resume_and_bad_args(self):
        original = self.config.read_text()
        for value in ['agent="devin"\nresume="auto"', 'agent="devin"\nargs="--flag"', 'agent="devin; echo bad"']:
            self.config.write_text(original.replace('agent="claude"', value))
            self.cli('check', self.config, ok=False)

    def test_explicit_and_new_sessions(self):
        config = self.config.read_text().replace('agent="codex"','agent="codex"\nresume="new"').replace('agent="claude"','agent="claude"\nresume="12345678-1234-1234-1234-123456789abc"')
        self.config.write_text(config)
        self.start()
        self.assertIn('--resume',next(e for e in self.events() if e['id']=='ios')['args'])
        self.assertNotIn('resume',next(e for e in self.events() if e['id']=='android')['args'])

    def test_codex_bypass_default_and_opt_out(self):
        self.start()
        self.assertIn('--dangerously-bypass-approvals-and-sandbox', next(e for e in self.events() if e['id']=='android')['args'])
        self.cli('stop', self.config)
        (self.root/'events').unlink()
        self.config.write_text(self.config.read_text().replace('agent="codex"', 'agent="codex"\nbypass=false'))
        self.start()
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', next(e for e in self.events() if e['id']=='android')['args'])

    def test_invalid_bypass_options(self):
        original = self.config.read_text()
        for value in ['"true"', '1']:
            self.config.write_text(original.replace('agent="codex"', 'agent="codex"\nbypass='+value))
            self.cli('check', self.config, ok=False)
        self.config.write_text(original.replace('agent="claude"', 'agent="claude"\nbypass=true'))
        self.cli('check', self.config, ok=False)

    def test_switch_preserves_pane_peers_and_literal_context(self):
        self.start()
        before = self.cli('status', self.config).stdout
        target = next(line.split('\t')[1] for line in before.splitlines() if line.startswith('android\t'))
        self.cli('send', self.config, 'android', 'User task: review pending code without deploying')
        self.wait(lambda:any(e.get('message') == 'User task: review pending code without deploying' for e in self.events()))
        note = 'Keep changes. Do not deploy. $(touch /tmp/xc-switch-injection)'
        self.cli('switch', self.config, 'android', 'copilot', '--note', note)
        self.wait(lambda: len([e for e in self.events() if e.get('id') == 'android']) == 2)
        after = self.cli('status', self.config).stdout
        self.assertIn('android\t' + target, after)
        self.assertIn('\tcopilot', after)
        self.assertIn(next(line for line in before.splitlines() if line.startswith('ios\t')), after)
        event = [e for e in self.events() if e.get('id') == 'android'][-1]
        self.assertEqual(event['args'][0], '-i')
        self.assertNotIn('--session-id', event['args'])
        self.assertIn('untrusted terminal history', event['args'][1])
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', event['args'])
        files = list((self.root/'state/xcontrol/handoffs').glob('*.md'))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].stat().st_mode & 0o777, 0o600)
        self.assertIn(note, files[0].read_text())
        self.assertIn('User task: review pending code', files[0].read_text())
        self.cli('send', self.config, 'android', 'Continue the review')
        self.wait(lambda:any(e.get('message') == 'Continue the review' for e in self.events()))
        self.cli('switch', self.config, 'android', 'agy')
        self.wait(lambda: len([e for e in self.events() if e.get('id') == 'android']) == 3)
        event = [e for e in self.events() if e.get('id') == 'android'][-1]
        self.assertEqual(event['args'][0], '--prompt-interactive')
        self.assertIn('\tagy', self.cli('status', self.config).stdout)
        self.assertEqual(len([e for e in self.events() if e.get('id') == 'ios']), 1)
        self.cli('switch', self.config, 'android', 'devin')
        self.wait(lambda: len([e for e in self.events() if e.get('id') == 'android']) == 4)
        event = [e for e in self.events() if e.get('id') == 'android'][-1]
        self.assertEqual(event['args'][:3], ['--process-model', 'in-process', '--'])
        self.assertNotIn('dangerous', event['args'])
        snapshots = list((self.root/'state/xcontrol/handoffs').glob('*.md'))
        self.assertEqual(len(snapshots), 3)
        self.assertEqual(sum('Previous handoff' in p.read_text() for p in snapshots), 2)
        self.assertIn('\tdevin', self.cli('status', self.config).stdout)

    def test_switch_back_to_codex_preserves_opt_out_and_starts_fresh(self):
        self.config.write_text(self.config.read_text().replace('agent="codex"', 'agent="codex"\nbypass=false'))
        self.start()
        self.cli('switch', self.config, 'android', 'copilot')
        self.wait(lambda: len([e for e in self.events() if e.get('id') == 'android']) == 2)
        self.cli('switch', self.config, 'android', 'codex')
        self.wait(lambda: len([e for e in self.events() if e.get('id') == 'android']) == 3)
        event = [e for e in self.events() if e.get('id') == 'android'][-1]
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', event['args'])
        self.assertNotIn('resume', event['args'])
        self.assertIn('untrusted terminal history', event['args'][-1])

    def test_switch_validation_does_not_interrupt_existing_agent(self):
        self.start()
        original = self.cli('status', self.config).stdout
        for ident, engine in [('missing', 'copilot'), ('android', 'codex'), ('android', 'unsupported-agent')]:
            self.cli('switch', self.config, ident, engine, ok=False)
            self.assertEqual(self.cli('status', self.config).stdout, original)
        target = next(line.split('\t')[1] for line in original.splitlines() if line.startswith('android\t'))
        self.env['TMUX_PANE'] = target
        self.cli('switch', self.config, 'android', 'copilot', ok=False)
        self.assertEqual(len([e for e in self.events() if 'id' in e]), 2)

    def test_switch_auto_excludes_current_and_failure_leaves_it_running(self):
        self.start()
        self.config.write_text('availability={copilot=["python3","-c","raise SystemExit(0)"]}\n' + self.config.read_text())
        self.cli('switch', self.config, 'android')
        self.wait(lambda: len([e for e in self.events() if e.get('id') == 'android']) == 2)
        self.assertIn('\tcopilot', self.cli('status', self.config).stdout)
        self.config.write_text(self.config.read_text().replace('availability={copilot=["python3","-c","raise SystemExit(0)"]}',
            'availability={codex=["python3","-c","raise SystemExit(1)"],claude=["python3","-c","raise SystemExit(1)"]}'))
        self.cli('switch', self.config, 'android', ok=False)
        self.assertIn('\tcopilot', self.cli('status', self.config).stdout)
        self.assertEqual(len([e for e in self.events() if 'id' in e]), 3)

    def test_switch_rejects_workspace_lock_conflict(self):
        self.start()
        other = self.root/'other.agents'
        other.write_text('name="other"\n[[agents]]\nid="other"\nfolder="android space"\nagent="copilot"\n')
        self.cli(other, '--detach')
        self.wait(lambda:len([e for e in self.events() if 'id' in e]) == 3)
        self.cli('switch', self.config, 'android', 'copilot', ok=False)
        self.assertIn('\tcodex', self.cli('status', self.config).stdout)
        self.assertEqual(len([e for e in self.events() if 'id' in e]), 3)

    def test_no_arguments_shows_help_without_starting(self):
        result = self.cli(cwd=self.root)
        self.assertIn('usage:', result.stdout)
        self.assertEqual(self.events(), [])
        self.assertFalse((self.root/'state').exists())
        for option in ('--detach', '-k'):
            self.cli(option, cwd=self.root, ok=False)
        self.assertFalse((self.root/'state').exists())

    def test_directory_bootstrap_launch_reattach_and_stop(self):
        script = self.root/'bin'/'codex'
        original = script.read_text()
        script.write_text(original.replace('import os,sys,json\n',
            'import os,sys,json\nif "exec" in sys.argv:\n print(json.dumps({"type":"item.completed","item":{"type":"agent_message","text":"XCONTROL_OK"}}))\n print(json.dumps({"type":"turn.completed"}))\n sys.exit(0)\n'))
        self.cli('.', '--detach', cwd=self.root)
        self.wait(lambda: len(self.events()) == 1)
        event = self.events()[0]
        self.assertEqual(event['cwd'], str(self.root))
        self.assertEqual(event['id'], 'setup')
        self.assertIn('Ask me to confirm', event['args'][-1])
        self.assertNotIn('resume', event['args'])
        generated = Path(event['config'])
        self.assertTrue(generated.is_relative_to(self.root/'state'))
        self.assertEqual(list(self.root.glob('*.agents')), [self.config])
        self.assertIn('setup', self.cli('status', self.root).stdout)
        self.cli(self.root, '--detach')
        self.assertEqual(len(self.events()), 1)
        self.cli('stop', self.root)

    def test_initial_prompt_requires_new_builtin_session(self):
        original = self.config.read_text()
        for fields in ['prompt="hello"', 'resume="new"\nprompt=""',
                       'resume="new"\nprompt=123']:
            self.config.write_text(original.replace('agent="claude"', 'agent="claude"\n'+fields))
            self.cli('check', self.config, ok=False)
        self.config.write_text(original.replace('agent="claude"', 'agent="claude"\nresume="new"\nprompt="Help configure my project"'))
        self.start()
        self.assertEqual(next(e for e in self.events() if e['id']=='ios')['args'], ['Help configure my project'])

    def auto_config(self, checks):
        table = ', '.join(json.dumps(key) + ' = ' + json.dumps(value) for key, value in checks.items())
        self.config.write_text('name="demo"\navailability={' + table + '}\n[[agents]]\nid="android"\nfolder="android space"\nagent="auto"\ncandidates=["codex","copilot"]\n')

    def test_auto_skips_exhausted_and_keeps_selected_engine(self):
        self.auto_config({'codex': ['python3', '-c', 'raise SystemExit(1)'],
                          'copilot': ['python3', '-c', 'raise SystemExit(0)']})
        self.cli('check', self.config)
        self.assertEqual(self.events(), [])
        self.cli(self.config, '--detach')
        self.wait(lambda: len(self.events()) == 1)
        self.assertEqual(self.events()[0]['args'][0], '--session-id')
        self.assertIn('\tcopilot', self.cli('status', self.config).stdout)
        # Reattaching must not re-run checks or replace a running CLI.
        self.auto_config({'codex': ['python3', '-c', 'raise SystemExit(0)'],
                          'copilot': ['python3', '-c', 'raise SystemExit(1)']})
        self.cli(self.config, '--detach')
        self.assertEqual(len(self.events()), 1)
        self.assertIn('\tcopilot', self.cli('status', self.config).stdout)
        self.cli('send', self.config, 'android', 'Check the API')
        self.wait(lambda: any(e.get('message') == 'Check the API' for e in self.events()))

    def test_auto_does_not_treat_unknown_as_available_or_leak_output(self):
        self.auto_config({'codex': ['python3', '-c', 'print("private-details"); raise SystemExit(2)'],
                          'copilot': ['python3', '-c', 'raise SystemExit(1)']})
        result = self.cli(self.config, '--detach', ok=False)
        self.assertNotIn('private-details', result.stdout + result.stderr)
        self.assertIn('no candidate has confirmed', result.stderr)
        self.assertEqual(self.events(), [])

    def test_availability_checks_are_cached_and_literal(self):
        marker = self.root/'checks'
        self.auto_config({'codex': ['python3', '-c',
            'from pathlib import Path; p=Path("checks"); p.write_text(p.read_text()+"x" if p.exists() else "x")'],
            'copilot': ['python3', '-c', 'raise SystemExit(1)']})
        self.config.write_text(self.config.read_text() + '\n[[agents]]\nid="ios"\nfolder="ios"\nagent="auto"\n')
        self.start()
        self.assertEqual(marker.read_text(), 'x')
        self.assertEqual({e['args'][0] for e in self.events()}, {'--no-daemon'})
        result = self.cli('availability', self.config)
        self.assertIn('codex\tavailable', result.stdout)
        self.assertIn('copilot\tunavailable', result.stdout)

    def test_invalid_auto_configuration(self):
        for suffix in ['candidates=[]', 'candidates=["codex","codex"]',
                       'candidates=["auto"]', 'candidates=["codex; echo bad"]',
                       'args=["--model","other"]', 'resume="12345678-1234-1234-1234-123456789abc"']:
            self.config.write_text('[[agents]]\nid="a"\nfolder="ios"\nagent="auto"\n' + suffix)
            self.cli('check', self.config, ok=False)

    def test_auto_detects_resolved_workspace_conflict(self):
        self.auto_config({'codex': ['python3', '-c', 'raise SystemExit(0)']})
        self.config.write_text(self.config.read_text() + '\n[[agents]]\nid="other"\nfolder="android space"\nagent="codex"\n')
        self.cli(self.config, '--detach', ok=False)
        self.assertEqual(self.events(), [])

    def test_auto_custom_candidate_and_literal_checker_arguments(self):
        literal = '$(touch should-not-exist); `echo bad`'
        self.auto_config({'devin': ['python3', '-c',
            'import sys; assert sys.argv[1] == ' + repr(literal), literal]})
        self.config.write_text(self.config.read_text().replace('candidates=["codex","copilot"]', 'candidates=["missing-xc-agent-123","devin"]'))
        self.cli(self.config, '--detach')
        self.wait(lambda: len(self.events()) == 1)
        self.assertEqual(self.events()[0]['args'], [])
        self.assertIn('\tdevin', self.cli('status', self.config).stdout)
        self.assertFalse((self.root/'should-not-exist').exists())


class ResumeTest(unittest.TestCase):
    def test_read_only_interactive_metadata(self):
        import sqlite3
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'state_5.sqlite'
            with sqlite3.connect(db) as con:
                con.execute('CREATE TABLE threads (id TEXT,cwd TEXT,source TEXT,archived INTEGER,updated_at INTEGER)')
                con.executemany('INSERT INTO threads VALUES (?,?,?,?,?)', [('interactive','/project','cli',0,1),('review','/project','exec',0,9),('archived','/project','cli',1,10)])
            before=db.read_bytes()
            with patch.dict(os.environ,{'CODEX_HOME':directory}):
                self.assertEqual(xc.latest_codex('/project'),'interactive')
            self.assertEqual(before,db.read_bytes())


class AvailabilityTest(unittest.TestCase):
    def test_structured_success_requires_model_answer(self):
        self.assertTrue(xc.probe_success('copilot', 'XCONTROL_OK\n'))
        self.assertFalse(xc.probe_success('copilot', 'Logged in successfully'))
        self.assertTrue(xc.probe_success('claude', json.dumps({'type':'result', 'result':'XCONTROL_OK', 'is_error':False})))
        self.assertFalse(xc.probe_success('claude', json.dumps({'type':'result', 'result':'XCONTROL_OK', 'is_error':True})))
        answer = {'type':'item.completed', 'item':{'type':'agent_message','text':'XCONTROL_OK'}}
        complete = {'type':'turn.completed'}
        self.assertTrue(xc.probe_success('codex', '\n'.join(map(json.dumps, [answer, complete]))))
        self.assertFalse(xc.probe_success('codex', json.dumps(answer)))
        self.assertFalse(xc.probe_success('codex', '\n'.join(map(json.dumps, [answer, complete, {'type':'turn.failed'}]))))
        for engine in ('codex', 'claude'):
            self.assertFalse(xc.probe_success(engine, 'invalid JSON'))

    def test_model_probe_retry_and_isolated_directory(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cli = root/'copilot'
            log = root/'calls'
            cli.write_text("#!/usr/bin/env python3\nimport os,sys,json\nfrom pathlib import Path\np=Path(os.environ['PROBE_LOG'])\nn=len(p.read_text().splitlines()) if p.exists() else 0\nwith p.open('a') as f:f.write(json.dumps({'cwd':os.getcwd(),'args':sys.argv[1:]})+'\\n')\nif n == 0: print('unauthorized');sys.exit(1)\nprint('XCONTROL_OK')\n")
            cli.chmod(0o755)
            with patch.dict(os.environ, {'PATH':directory+':'+os.environ['PATH'], 'PROBE_LOG':str(log)}):
                self.assertEqual(xc.model_availability('copilot', timeout=2), 'available')
                calls = [json.loads(line) for line in log.read_text().splitlines()]
                self.assertEqual(len(calls), 2)
                self.assertTrue(all('xc-probe-' in c['cwd'] for c in calls))
                self.assertIn('--available-tools=', calls[0]['args'])
                self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', xc.probe_command('codex'))
                self.assertIn('read-only', xc.probe_command('codex'))
                cli.write_text('#!/usr/bin/env python3\nimport time\ntime.sleep(30)\n')
                start = time.monotonic()
                self.assertEqual(xc.model_availability('copilot', timeout=.1), 'unavailable')
                self.assertLess(time.monotonic()-start, 3)

    def test_failure_is_not_success_even_with_marker(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            cli = Path(directory)/'copilot'
            cli.write_text('#!/usr/bin/env python3\nprint("XCONTROL_OK")\nraise SystemExit(1)\n')
            cli.chmod(0o755)
            with patch.dict(os.environ, {'PATH':directory+':'+os.environ['PATH']}):
                self.assertEqual(xc.model_availability('copilot'), 'unavailable')
        self.assertEqual(xc.model_availability('unknown-custom-agent'), 'unknown')

if __name__=='__main__': unittest.main()
