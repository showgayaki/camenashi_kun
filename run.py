import argparse
import time
import datetime
import socket
import signal
from typing import Optional
import cv2
import base64
from ping3 import ping
from pathlib import Path
from camenashi_kun.config import Config
from camenashi_kun.logger import Logger
from camenashi_kun.mail import Mail
import yolov5.detect as detect


class TerminatedExecption(Exception):
    pass

def raise_exception(*_):
    raise TerminatedExecption()


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
    return image_dir, image_file_path


def send_mail(cfg, label=None, image_list=None):
    mail_info = cfg['mail_info']
    mail = Mail(mail_info)

    # メール本文作成
    if image_list:
        body = mail.build_body(label, image_list)
    else:
        body = '[{}]と疎通確認が取れませんでした。<br>[{}]の状態を確認してください。'.format(
            cfg['camera_info']['camera_ip'], cfg['camera_info']['camera_ip'])

    body_dict = {
        'subject': '動体検知@{} from {}'.format(cfg['camera_info']['camera_ip'], cfg['app_name']),
        'body': body
    }
    msg = mail.create_message(body_dict, image_list)
    mail_result = mail.send_mail(msg)
    return mail_result


def main(no_view=False):
    WEITHTS = 'yolov5/yolov5s.pt'
    IMAGE_SIZE = [640, 640]
    computer_name = socket.gethostname()
    root_dir = Path(__file__).resolve().parent
    # systemdの終了を受け取る
    signal.signal(signal.SIGTERM, raise_exception)
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
        detected_count = 0 # 検知回数
        no_detected_count = 0 # 非検知回数
        mail_flag = False # メール送信フラグ
        image_list = [] # 保存した画像パスリスト
        last_label = '' # メール送信用の検知した物体のラベル
        # ストリーミング表示するかは、引数から受け取る
        view_img = not no_view
        try:
            for label, frame, log_str in detect.run(weights=WEITHTS, imgsz=IMAGE_SIZE, source=camera_url, nosave=True, view_img=view_img):
                # 検知対象リストにあるか判定
                if label in cfg['detect_label']:
                    detected_count += 1
                    log.logging(log_level, log_str)
                else:
                    no_detected_count += 1

                # メール通知フラグが立っていたらメール送信
                if mail_flag:
                    # Falseに戻す
                    mail_flag = False
                    # 現在時刻取得
                    dt_now = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
                    # 画像保存
                    image_dir, image_file_path = save_image(frame, dt_now)
                    log_level = 'info'
                    log.logging(log_level, 'Image saved: {}'.format(image_file_path))
                    image_list.append(image_file_path)
                    # 画像添付メール送信
                    mail_result = send_mail(cfg, last_label, image_list)
                    # メール送信ログ
                    log_level = 'error' if 'Error' in mail_result else 'info'
                    log.logging(log_level, 'Mail result: {}'.format(mail_result))
                    # 作成した画像削除
                    remove_images = []
                    for image in image_dir.iterdir():
                        remove_images.append(str(image))
                        Path(image).unlink()
                    log.logging(log_level, 'Delete images: {}'.format(remove_images))
                    # 初期化
                    last_label = ''
                    image_list = []
                    # 検知後は一時停止して、連続通知回避
                    log.logging(log_level, 'Pause detecting for {} seconds'.format(cfg['pause_seconds']))
                    time.sleep(cfg['pause_seconds'])
                    log.logging(log_level, '=== Restart detecting ===')

                # 検知回数の閾値に達したら画像を保存して通知
                if detected_count == cfg['notice_threshold']:
                    mail_flag = True
                    # 検知ログ
                    log_level = 'info'
                    log.logging(log_level, 'Detected: {}'.format(label))
                    # ラベルを取っておく
                    last_label = label
                    # カウンタリセット
                    detected_count = 0
                    # 現在時刻取得
                    dt_now = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
                    # 画像保存
                    _, image_file_path = save_image(frame, dt_now)
                    image_list.append(image_file_path)
                    log.logging(log_level, 'Image saved: {}'.format(image_file_path))
                    log.logging(log_level, 'Capture interval: {} seconds'.format(cfg['capture_interval']))
                    # 待機
                    time.sleep(cfg['capture_interval'])
                    continue
                elif no_detected_count == cfg['notice_threshold']:
                    # 検知対象の非検知が続いたらリセット
                    last_label = ''
                    image_list = []
                    no_detected_count = 0

        except KeyboardInterrupt:
            log_level = 'info'
            log.logging(log_level, 'Ctrl + C pressed...'.format(cfg['app_name']))
            log.logging(log_level, '===== Stop {} ====='.format(cfg['app_name']))
        except TerminatedExecption:
            log.logging(log_level, 'TerminatedExecption: stopped by systemd')
            log.logging(log_level, '===== Stop {} ====='.format(cfg['app_name']))
        except OSError as e:
            import traceback
            traceback.print_exc()
            log_level = 'error'
            log.logging(log_level, 'ERROR: {}'.format(e))
            # エラー発生したら一時停止してから再起動
            log_level = 'info'
            log.logging(log_level, 'Pause detecting for {} seconds'.format(cfg['pause_seconds']))
            time.sleep(cfg['pause_seconds'])
            log.logging(log_level, '*** Restart {} ***'.format(cfg['app_name']))
            # systemdで再起動
            raise e
        except Exception as e:
            log_level = 'error'
            log.logging(log_level, 'Unkown Error: {}'.format(e))
            # エラー発生したら一時停止してから再起動
            log_level = 'info'
            log.logging(log_level, 'Pause detecting for {} seconds'.format(cfg['pause_seconds']))
            time.sleep(cfg['pause_seconds'])
            log.logging(log_level, '*** Restart {} ***'.format(cfg['app_name']))
            # systemdで再起動
            raise e
    else:
        log_level = 'error'
        log.logging(log_level, '[{}] is NOT responding. Please check device.'
        .format(cfg['camera_info']['camera_ip']))
        # エラーメール送信
        mail_result = send_mail(cfg)
        log_level = 'error' if 'Error' in mail_result else 'info'
        log.logging(log_level, 'Mail result: {}'.format(mail_result))
        log.logging(log_level, '===== Stop {} ====='.format(cfg['app_name']))


def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-view', default=False, action='store_true', help='hide stream')
    opt = parser.parse_args()
    return opt


if __name__ == '__main__':
    opt = parse_opt()
    main(**vars(opt))
