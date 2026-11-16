"""Project-scoped SSH/SFTP helper. Authentication uses the local private key."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import warnings
warnings.filterwarnings('ignore')
import logging
logging.getLogger('paramiko').setLevel(logging.CRITICAL)
import paramiko

ROOT = Path(__file__).resolve().parents[1]
REMOTE = '/root/gpufree-data/nlp_final'

def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['sync','exec','get','put','serve'])
    p.add_argument('argument', nargs='?', default='')
    args = p.parse_args()
    client = paramiko.SSHClient()
    client.load_host_keys(str(Path.home()/'.ssh'/'known_hosts'))
    for attempt in range(6):
        try:
            client.connect('120.209.70.195',port=31341,username='root',
                           key_filename=str(Path.home()/'.ssh'/'nlp_final_ed25519'),
                           look_for_keys=False,allow_agent=False,timeout=20,banner_timeout=20)
            break
        except (paramiko.SSHException, OSError):
            if attempt == 5:
                raise
            time.sleep(5)
    client.get_transport().set_keepalive(20)
    try:
        if args.action == 'serve':
            print('SSH_SESSION_READY',flush=True)
            for line in sys.stdin:
                request=json.loads(line)
                if request.get('action')=='sync':
                    _,out,err=client.exec_command('mkdir -p '+REMOTE+'/scripts '+REMOTE+'/data '+REMOTE+'/logs')
                    out.channel.recv_exit_status()
                    files=list((ROOT/'scripts').glob('*.py'))+list((ROOT/'scripts').glob('*.sh'))
                    files+=list((ROOT/'data').glob('*.jsonl'))+list((ROOT/'data').glob('*.json'))+list((ROOT/'data').glob('*.gz'))
                    files+=[ROOT/'requirements.txt',ROOT/'DATA_CONTRACT.md']
                    with client.open_sftp() as sftp:
                        for f in files:
                            sftp.put(str(f),REMOTE+'/'+f.relative_to(ROOT).as_posix())
                    print('SYNC_OK',len(files),flush=True)
                elif request.get('action')=='get':
                    rel=Path(request['path'])
                    if rel.is_absolute() or '..' in rel.parts:
                        raise ValueError('project-relative path required')
                    dest=ROOT/rel
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    with client.open_sftp() as sftp:
                        sftp.get(REMOTE+'/'+rel.as_posix(),str(dest))
                    print('GET_OK',rel,flush=True)
                else:
                    _,out,err=client.exec_command(request['cmd'])
                    for output in out:
                        print(output,end='',flush=True)
                    print(err.read().decode('utf-8',errors='replace'),end='',flush=True)
                    print('COMMAND_EXIT',out.channel.recv_exit_status(),flush=True)
                print('SSH_REQUEST_DONE',flush=True)
            return
        if args.action == 'sync':
            _,out,err = client.exec_command('mkdir -p '+REMOTE+'/scripts '+REMOTE+'/data '+REMOTE+'/logs')
            if out.channel.recv_exit_status():
                raise RuntimeError(err.read().decode())
            sftp = client.open_sftp()
            files = list((ROOT/'scripts').glob('*.py'))+list((ROOT/'scripts').glob('*.sh'))
            files += list((ROOT/'data').glob('*.jsonl'))+list((ROOT/'data').glob('*.json'))+list((ROOT/'data').glob('*.gz'))
            files += [ROOT/'requirements.txt', ROOT/'DATA_CONTRACT.md']
            for f in files:
                sftp.put(str(f),REMOTE+'/'+f.relative_to(ROOT).as_posix())
            print('uploaded',len(files),'files')
            sftp.close()
        elif args.action == 'put':
            with client.open_sftp() as sftp:
                for value in args.argument.split(','):
                    relative=Path(value)
                    if relative.is_absolute() or '..' in relative.parts:
                        raise ValueError('project-relative path required')
                    sftp.put(str(ROOT/relative),REMOTE+'/'+relative.as_posix())
                    print('uploaded',relative)
        elif args.action == 'get':
            relative = Path(args.argument)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('project-relative path required')
            target = ROOT/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            with client.open_sftp() as sftp:
                sftp.get(REMOTE+'/'+relative.as_posix(),str(target))
            print('downloaded',relative)
        else:
            _,out,err = client.exec_command(args.argument,get_pty=False)
            for line in out:
                print(line,end='',flush=True)
            error = err.read().decode('utf-8',errors='replace')
            if error:
                print(error,file=sys.stderr)
            code = out.channel.recv_exit_status()
            if code:
                raise SystemExit(code)
    finally:
        client.close()

if __name__ == '__main__':
    main()
