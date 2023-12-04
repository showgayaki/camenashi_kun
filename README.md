# camenashi_kun

## インストール
### 準備
open-pythonのインストールに失敗するときは、cmakeのインストールが必要かもしれないので以下実行（ubuntuの場合）。  
`sudo apt install update -y`  
`sudo apt install upgrade -y`  
`sudo apt install cmake`  
参考：https://docs.opencv.org/4.x/d2/de6/tutorial_py_setup_in_ubuntu.html  

#### SciPyインストール
SciPyのインストールに失敗するときは、以下が必要かも。  
`sudo apt install libatlas-base-dev gfortran`  
参考：https://qiita.com/jooex/items/61a9169f2f88580d15ff

### 仮想環境作成
`python3 -m venv .venv`  
`source .venv/bin/activate`  
`pip install -r requirements.txt`  

## .env設定例
```
CAMERA_IP=[camera ip address]
CAMERA_USER=[camera username]
CAMERA_PASS=[camera password]

NOTICE_THRESHOLD=6
DETECT_LABEL=cat
THRESHOLD_NO_DETECTED_SECONDS=30
PAUSE_SECONDS=60
BLACK_SCREEN_SECONDS=300

LINE_NOTIFY_ACCESS_TOKEN=
LINE_MESSAGING_API_ACCESS_TOKEN=
TO=
LINE_MESSAGING_API_LIMIT=200
IS_NOTIFY_REACHED_LIMIT=False

AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=ap-northeast-1
S3_BUCKET_NAME=camenashi-kun
S3_EXPIRES_IN=43200
```

## 実行
環境によってどちらかのコマンドを叩く。  
仮想環境に入っていなくてもOK。  
`bash run.sh`  
`zsh run.sh`  

### Options
`--no-view`：ストリーミングを表示しない。サービスで起動する際などに利用。  

## サービス登録
`chmod 755 run.sh`  
`sudo vi /lib/systemd/system/camenashi_kun.service`  
```
[Unit]
Description=camenashi_kun

[Service]
Type=simple
Restart=on-failure
RestartSec=1200
ExecStart=[path to]/camenashi_kun/run.sh --no-view

[Install]
WantedBy=multi-user.target
```
RestartSec:再起動時の待機時間(秒)  
RestartSecを設定していないと、pingでの疎通確認が取れない時に毎秒のようにメール送信される。  

`sudo systemctl enable camenashi_kun.service`  
`sudo systemctl start camenashi_kun.service`  
