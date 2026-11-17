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
        for engine in ('codex', 'claude', 'copilot'):
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

    def cli(self, *args, ok=True):
        result = subprocess.run([str(CLI), *map(str,args)], env=self.env, text=True, capture_output=True, timeout=10)
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

    def test_explicit_and_new_sessions(self):
        config = self.config.read_text().replace('agent="codex"','agent="codex"\nresume="new"').replace('agent="claude"','agent="claude"\nresume="12345678-1234-1234-1234-123456789abc"')
        self.config.write_text(config)
        self.start()
        self.assertIn('--resume',next(e for e in self.events() if e['id']=='ios')['args'])
        self.assertNotIn('resume',next(e for e in self.events() if e['id']=='android')['args'])


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

if __name__=='__main__': unittest.main()
