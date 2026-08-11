#!/usr/bin/env python3
"""obsprobe.py -- OBSAgent 자리에 앉아 XIS 를 통해 ics_sim 을 찔러 보는 최소 도구.

OBSAgent(obstool)를 아직 안 띄운 단계에서 XIS 의 라우팅을 판정하려면
'OBS 이름으로 보내고 OBS 앞으로 오는 것을 받는' 제3 노드가 하나 필요하다.
isisPerl/isisCmd 는 서버 IP 와 ISIS.pm 경로가 하드코딩돼 있어 손봐야 하므로
표준 라이브러리만 쓰는 이 스크립트로 대신한다.

  python3 obsprobe.py                      # XIS 127.0.0.1:6660, 내 ID=OBS, 내 포트=6650
  python3 obsprobe.py --xis-host 1.2.3.4 --my-id KCMD --my-port 6655

기동하면 <ID>>XIS PING 을 한 번 보내 등록하고, 이후
  - 받은 데이터그램을 전부 그대로 찍고
  - stdin 한 줄을 그대로 와이어에 실어 보낸다 (CR 는 자동으로 붙는다)

    > OBS>K.IC STATUS
    > OBS>ICS EXPNUM

Ctrl+C 또는 quit 로 종료.  포트 6650 은 실제 OBSAgent 의 포트이므로,
obstool 을 띄우기 전에 반드시 이 프로브를 먼저 끌 것.
"""
import argparse
import socket
import sys
import threading
from datetime import datetime, timezone


def stamp() -> str:
    return datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]


def reader(sock: socket.socket) -> None:
    while True:
        try:
            data, addr = sock.recvfrom(4096)
        except OSError:
            return
        text = data.decode('latin-1').rstrip('\r\n')
        print(f'\r{stamp()} <<< [{addr[0]}:{addr[1]}] {text}\n> ', end='', flush=True)


def main() -> int:
    p = argparse.ArgumentParser(description='XIS 경유 IMPv2 프로브')
    p.add_argument('--xis-host', default='127.0.0.1')
    p.add_argument('--xis-port', type=int, default=6660)
    p.add_argument('--my-id', default='OBS')
    p.add_argument('--my-port', type=int, default=6650)
    p.add_argument('--bind-host', default='0.0.0.0')
    args = p.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.bind_host, args.my_port))
    dest = (args.xis_host, args.xis_port)

    threading.Thread(target=reader, args=(sock,), daemon=True).start()

    def send(line: str) -> None:
        sock.sendto((line + '\r').encode('latin-1'), dest)
        print(f'{stamp()} >>> {line}')

    print(f'-- {args.my_id} @ {args.bind_host}:{args.my_port} -> XIS {dest[0]}:{dest[1]}')
    send(f'{args.my_id}>XIS PING')

    try:
        for raw in sys.stdin:
            line = raw.strip()
            if not line:
                print('> ', end='', flush=True)
                continue
            if line in ('quit', 'exit'):
                break
            send(line)
            print('> ', end='', flush=True)
    except KeyboardInterrupt:
        pass
    sock.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
