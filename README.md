# camknashi_kun

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
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=[user name@gmail.com]
SMTP_PASS=[your password]
MAIL_TO=[email address]
MAIL_CC=[email address]

CAMERA_IP=[local ip address]
CAMERA_USER=[camera user name]
CAMERA_PASS=[camera password]

NOTICE_THRESHOLD=20
DETECT_LABEL=cat
PAUSE_SECONDS=60
```

## 実行
環境によってどちらかのコマンドを叩く。  
仮想環境に入っていなくてもOK。  
`bash run.sh`  
`zsh run.sh`  

## サービス登録
`chmod 755 run.sh`  
`sudo vi /lib/systemd/system/camenashi_kun.service`  
```
[Unit]
Description=camenashi_kun

[Service]
Type=simple
Restart=always
ExecStart=[path to]/camenashi_kun/run.sh --no-view

[Install]
WantedBy=multi-user.target
```
`sudo systemctl enable camenashi_kun.service`  
`sudo systemctl start camenashi_kun.service`  
