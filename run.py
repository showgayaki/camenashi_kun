import time
import datetime
import socket
import cv2
import base64
from ping3 import ping
from pathlib import Path
from camenashi_kun.config import Config
from camenashi_kun.logger import Logger
from camenashi_kun.mail import Mail
import yolov5.detect as detect


def load_config(root_dir):
    config = Config(root_dir)
    cfg = config.fetch_config()
    return cfg


def ping_to_target(try_count, target_ip):
    res = None
    log_level = 'info'
    result = f'TryCount {try_count + 1}: Connect to {target_ip} is '
    # ping実行
    try:
        res = ping(target_ip)
    except Exception as e:
        log_level = 'error'
        result = str(e)

    # 値が返って来なかったらエラーログ
    if res is None:
        log_level = 'error'
        result += 'NG.'
    else:
        result += 'OK.'
    return log_level, result


def save_image(frame, file_name):
    dir_name = Path(__file__).resolve().parent.name
    image_dir = Path.joinpath(Path(__file__).resolve().parent, f'{dir_name}/images')
    # ディレクトリなかったら作成
    if not image_dir.is_dir():
        Path.mkdir(image_dir)

    # 画像保存パス、stringじゃないといけない
    image_file_path = str(Path.joinpath(image_dir, f'{file_name}.png'))
    # 画像保存
    cv2.imwrite(image_file_path, frame)
    return image_file_path


def send_mail(cfg, label=None, image_file_path=None):
    mail_info = cfg['mail_info']
    mail = Mail(mail_info)

    # 画像をbase64に変換
    if image_file_path:
        with open(image_file_path, 'rb') as f:
            data = base64.b64encode(f.read())
        image = 'data:image/png;base64,{}'.format(data.decode('utf-8'))
        body = '{} を動体検知しました。<img src="{}" style="width: 100%; margin-top: 20px;">'.format(label, image)
    else:
        body = '[{}]と疎通確認が取れませんでした。<br>[{}]の状態を確認してください。'.format(
            cfg['camera_info']['camera_ip'], cfg['camera_info']['camera_ip'])

    body_dict = {
        'subject': '動体検知@{} from {}'.format(cfg['camera_info']['camera_ip'], cfg['app_name']),
        'body': body
    }
    msg = mail.create_message(body_dict)
    mail_result = mail.send_mail(msg)
    return mail_result


def main():
    WEITHTS = 'yolov5/yolov5s.pt'
    IMAGE_SIZE = [640, 640]
    computer_name = socket.gethostname()
    root_dir = Path(__file__).resolve().parent
    # ログ
    log = Logger(root_dir)
    log_level = 'info'
    # 設定読み込み
    cfg = load_config(root_dir)
    # アプリケーション開始ログ
    log.logging(log_level, '===== {} Started on {} ====='.format(cfg['app_name'], computer_name))
    camera_url = 'rtsp://{}:{}@{}:554/stream2'.format(
        cfg['camera_info']['camera_user'],
        cfg['camera_info']['camera_pass'],
        cfg['camera_info']['camera_ip'],
    )
    log.logging(log_level, 'Camera IP address: {}.'.format(cfg['camera_info']['camera_ip']))

    # pingで疎通確認
    RETRY_COUNT = 3
    for i in range(RETRY_COUNT):
        log_level, msg = ping_to_target(i, cfg['camera_info']['camera_ip'])
        log.logging(log_level, msg)
        ping_result = False
        if log_level == 'info':
            log.logging(log_level, 'Start streaming and detecting.')
            ping_result = True
            break

    # 疎通確認が取れたら実行
    if ping_result:
        detected_count = 0
        last_label = ''
        try:
            for label, frame, log_str in detect.run(weights=WEITHTS, imgsz=IMAGE_SIZE, source=camera_url, nosave=True):
                # 検知対象リストにあるか判定
                if label in cfg['detect_label']:
                    detected_count += 1
                    log.logging(log_level, log_str)

                # 検知回数の閾値に達したら画像を保存して通知
                if detected_count == cfg['notice_threshold']:
                    # カウンタリセット
                    detected_count = 0
                    # 現在時刻取得
                    dt_now = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
                    # 画像保存
                    image_file_path = save_image(frame, dt_now)
                    # 画像添付メール送信
                    mail_result = send_mail(cfg, label, image_file_path)
                    log_level = 'error' if 'Error' in mail_result else 'info'
                    log.logging(log_level, 'Mail result: {}'.format(mail_result))
                    # 検知後は一時停止して、連続通知回避
                    log.logging(log_level, 'Pause detecting for {} seconds'.format(cfg['pause_seconds']))
                    time.sleep(cfg['pause_seconds'])
                    log.logging(log_level, 'Restart detecting.')

                    break
        except KeyboardInterrupt:
            log_level = 'info'
            log.logging(log_level, 'Ctrl + C pressed...'.format(cfg['app_name']))
            log.logging(log_level, '===== Finish {} ====='.format(cfg['app_name']))
    else:
        log_level = 'error'
        log.logging(log_level, '[{}] is NOT responding. Please check device.'
        .format(cfg['camera_info']['camera_ip']))
        # エラーメール送信
        mail_result = send_mail(cfg)
        log_level = 'error' if 'Error' in mail_result else 'info'
        log.logging(log_level, 'Mail result: {}'.format(mail_result))
        log.logging(log_level, '===== Finish {} ====='.format(cfg['app_name']))


if __name__ == '__main__':
    main()
