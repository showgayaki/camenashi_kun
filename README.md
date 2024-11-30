# camenashi_kun
[TP-LinkのTapoを使用](https://www.tp-link.com/jp/support/faq/2680/)して、我が家のねこちゃんのおトイレを監視します。  
検知したらおトイレの様子の動画を、DiscordにPOSTします。

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
CAMERA_IP=[camera ip address]  # カメラのIPアドレス
CAMERA_USER=[camera username]  # カメラのユーザー名
CAMERA_PASS=[camera password]  # カメラのパスワード

NOTICE_THRESHOLD=5  # 検知対象のラベルが何フレーム現れたら検知とするか
DETECT_LABEL=cat  # 検知対象のラベル
THRESHOLD_NO_DETECTED_SECONDS=25  # 検知対象のラベルが検知されなくなってから、何秒経ったら未検知とするか
PAUSE_SECONDS=60  # エラー時の再起動までの時間
BLACK_SCREEN_SECONDS=300  # 何秒真っ暗画面になったらやばいとするか
MOVIE_SPEED=4  # 動画は何倍速？
DETECT_AREA=0,0,480,384  # 映像の検知対象エリア
IS_NOTIFIED_PING_ERROR='False'  # pingエラーを通知したかどうかのフラグ

SSH_HOSTNAME=  # 動画アップロード先のホスト(~/.ssh/configに記載されているホスト名)
SSH_UPLOAD_DIR=/share/Camenashi  # 動画アップロード先のディレクトリ
THRESHOLD_STORAGE_DAYS=240  # 動画の保存期間(日)
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
User=[user name]
Restart=always
RestartSec=10
ExecStart=[path to]/camenashi_kun/run.sh --no-view

[Install]
WantedBy=multi-user.target
```
RestartSec:再起動時の待機時間(秒)  

`sudo systemctl enable camenashi_kun.service`  
`sudo systemctl start camenashi_kun.service`  

## pingでPermission deniedになるときは
https://github.com/kyan001/ping3/blob/master/TROUBLESHOOTING.md#permission-denied-on-linux  

改行を入れたいので、以下の方がよい  
```echo -e "# allow all users to create icmp sockets\nnet.ipv4.ping_group_range=0 2147483647\n" | sudo tee -a /etc/sysctl.d/ping_group.conf```
