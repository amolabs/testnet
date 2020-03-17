# AMO 테스트넷
테스트넷의 genesis.json 파일과 실행 스크립트들.

## setup.sh 사용
이 스크립트는 데이터 디렉토리와 설정파일들을 준비하는 과정을 도와준다.

### 사용법
```bash
./setup.sh <data_root> <moniker> [peers]
```

### 정보 
- `<data_root>`는 노드의 데이터 파일들과 설정 파일들이 있는 장소이다. 사용자가
  쓰기 권한을 가지고 있는 어떤 디렉토리 이름을 지정하면 스크립트가 디렉토리를
  만들거나 이미 있는 디렉토리라면 재사용한다. 디렉토리의 이름은
  `<path_to_data_dir>/<node_name>`의 형태로 할 것을 권장한다. 
- `<moniker>`는 이 노드의 이름으로 사람이 읽을 용도이다. 이 노드를 충분히
  설명하는 아무 이름이라도 괜찮다.
- `[peers]`는 peer들의 주소를 comma로 구분하여 적은 것이다. peer 주소는
  `node_id@ip_address_or_hostname:p2p_port`의 형태여야 한다. `node_id`는
  `curl`과 같은 명령으로 `http://ip_address_or_hostname:26657/status`에
  질의해서 알 수 있다. `p2p_port`의 디폴트 값은 26656이다.

해당 스크립트가 amod 서비스를 `systemctl`에 등록하게 됨에 따라, 서비스는
`start`, `stop` 등과 같은 명령어들로 제어될 수 있다. 예를 들어, 노드를 시작하기
위해서는, `systemctl start amod` 명령어를 실행하면 된다. 최근에 실행되는 AMO
테스트넷은 172.104.88.12에서 실행되는 seed 노드를 운영하고 있다. 다른 적덩한
peer를 알지 못한다면 이 노드를 peer로 지정할 것을 권장한다.

## upgrade.sh 사용
이 스크립트는 프로토콜이 업그레이드 되는 시점에 최신의 바이너리를 기존의 것과
교체하는 방식으로 노드의 프로토콜 업그레이드를 도와준다. 

## orchestration/do.py 사용
이 파이썬 스트립트는 AMO 노드들을 병렬로 오케스트레이션 하기 위한 다음 기능들을
제공한다.

### 기능
- `init`: 노드 실행, 코인 분배 그리고 코인 stake
- `up`: 단순 노드 실행
- `down`: 노드 종료
- `restart`: `down` -> `up` 순차적으로 실행
- `setup`: `orchestration/data/<target>` 아래에 위치한 config 파일들 해당
  target 노드에 복사
- `reset`: `down` -> `setup` -> `init` 순차적으로 실행 
- `upgrade`: 노드 프로토콜 업그레이드
- `exec`: 사용자 입력 명령어 노드들에서 동시 실행
- `scp`: 로컬 경로의 파일들을 원격 경로에 ssh 로 복사

### 사용법
```bash
./orchestration/do.py { init | up | down | restart | setup | reset | upgrade | exec | scp }
```

### 필수사항
이 스크립트를 사용하기 위해서는 다음의 프리셋 데이터가 필요하다:
- `$HOME/.ssh/id_rsa`: ssh 프라이빗 키
- `orchestration/config.json`: 노드 정보
- `orchestration/data/<target>/node_key.json`: tendermint 노드 키
- `orchestration/data/<target>/priv_validator_key.json`: tendermint validator
  키

`data` 폴더 아래에 위치한 tendermint 관련 키 정보는
`orchestration/config.json`에 적힌 정보와 일치하여야 한다.
