import time
import datetime
import socket
import signal
import cv2
from ping3 import ping
from pathlib import Path
from .config import Config
from .logger import Logger
from .line_notify import LineNotify
from .mail import Mail
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
    result = f'Ping Try Count {try_count + 1}: Connect to {target_ip} is '
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


def save_image(frame, file_name, concatenated=False):
    dir_name = Path(__file__).resolve().parent.name
    image_dir = Path.joinpath(Path(__file__).resolve().parents[1], f'{dir_name}/images')
    # ディレクトリなかったら作成
    if not image_dir.is_dir():
        Path.mkdir(image_dir)

    if concatenated:
        # 画像保存パス、stringじゃないといけない
        image_file_path = str(Path.joinpath(image_dir, f'{file_name}_concatenated.png'))
    else:
        # 画像保存パス、stringじゃないといけない
        image_file_path = str(Path.joinpath(image_dir, f'{file_name}.png'))
        # 上下左右に白の余白を追加
        frame = cv2.copyMakeBorder(frame, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=[255, 255, 255])

    # 画像保存
    cv2.imwrite(image_file_path, frame)
    return image_dir, image_file_path


def post_line(line_info, image_file_path, label):
    bot = LineNotify(line_info['api_url'], line_info['access_token'])
    payload = {
        'message': f'\n{label}を動体検知しました。',
        'stickerPackageId': None,
        'stickerId': None
    }
    image = image_file_path
    return bot.send_message(payload, image)


def send_mail(cfg, label=None, image_list=None):
    mail_info = cfg['mail_info']
    mail = Mail(mail_info)

    # メール本文作成
    if image_list:
        body = mail.build_body(label, image_list)
    else:
        body = ('[{}]と疎通確認が取れませんでした。<br>'
        '[{}]の状態を確認してください。<br><br>'
        '{}を終了します。<br>'
        '問題解消後、{}を再開してください。').format(
            cfg['camera_info']['camera_ip'],
            cfg['camera_info']['camera_ip'],
            cfg['app_name'],
            cfg['app_name']
        )

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
    root_dir = Path(__file__).resolve().parents[1]
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
        else:
            # ping返って来なかったら待機して再度ping
            time.sleep(5)

    # 疎通確認が取れたら実行
    if ping_result:
        detected_count = 0 # 検知回数
        image_list = [] # 保存した画像Pathリスト
        last_label = '' # メール送信用の検知した物体のラベル
        label = '' # メール送信用の検知した物体のラベル
        no_detected_start = 0 # 非検知秒数のカウント用
        past_time = 0 # 非検知経過時間
        # ストリーミング表示するかは、引数から受け取る
        view_img = not no_view
        try:
            for label, frame, log_str in detect.run(weights=WEITHTS, imgsz=IMAGE_SIZE, source=camera_url, nosave=True, view_img=view_img):
                # 画像PathリストにPathが入っていたら、メール通知
                if len(image_list) > 0:
                    # 現在時刻取得
                    dt_now = datetime.datetime.now()
                    file_name = dt_now.strftime('%Y%m%d-%H%M%S')
                    # 画像保存
                    image_dir, image_file_path = save_image(frame, file_name, False)
                    log_level = 'info'
                    log.logging(log_level, 'Image saved: {}'.format(image_file_path))
                    image_list.append(image_file_path)

                    # 画像一覧取得(画像連結が逆になったことがあったのでソートしておく)
                    image_list = [str(image) for image in image_dir.glob('*.png')]
                    image_list.sort()
                    log.logging(log_level, 'Concatenate Images: {}'.format(image_list))
                    # 画像を連結
                    concatenate_list = [cv2.imread(image) for image in image_list]
                    concatenated_iamge = cv2.vconcat(concatenate_list)
                    # ファイル名の時間箇所が被らないように1秒加算
                    dt_now = dt_now + datetime.timedelta(seconds=1)
                    file_name = dt_now.strftime('%Y%m%d-%H%M%S')
                    # 連結した画像保存
                    _, image_file_path = save_image(concatenated_iamge, file_name, True)
                    log.logging(log_level, 'Concatenated Image saved: {}'.format(image_file_path))

                    # LINEに通知
                    log.logging(log_level, 'Start post to LINE.')
                    post_result = post_line(cfg['line_info'], image_file_path, last_label)
                    log_level = 'error' if 'Error' in post_result else 'info'
                    log.logging(log_level, 'LINE result: {}'.format(post_result))

                    # 作成した画像削除
                    remove_images = []
                    for image in image_dir.iterdir():
                        remove_images.append(str(image))
                        Path(image).unlink()
                    log_level = 'info'
                    log.logging(log_level, 'Delete images: {}'.format(remove_images))
                    # 初期化
                    last_label = ''
                    image_list = []
                    # 検知後は一時停止して、連続通知回避
                    log.logging(log_level, 'Pause detecting for {} seconds'.format(cfg['pause_seconds']))
                    time.sleep(cfg['pause_seconds'])
                    # カウンタ・タイマーリセット
                    detected_count = 0
                    no_detected_start = 0
                    past_time = 0
                    log.logging(log_level, '=== Restart detecting ===')
                    continue

                # 検知対象リストにあるか判定
                if label in cfg['detect_label']:
                    detected_count += 1
                    # 非検知タイマーリセット
                    no_detected_start = 0
                    # ログ文言に検知回数を追記
                    log_str += ' Detected count: {}'.format(detected_count)
                    log.logging(log_level, log_str)
                elif no_detected_start == 0:
                    # 非検知になったらタイマースタート
                    no_detected_start = time.perf_counter()
                elif detected_count > 0:
                    # 非検知秒数カウント
                    past_time = time.perf_counter() - no_detected_start
                    # 非検知秒数閾値に達したらリセット
                    if past_time > cfg['pause_seconds']:
                        log_level = 'info'
                        log.logging(log_level, 'No detected for {} seconds.'.format(cfg['pause_seconds']))
                        log.logging(log_level, '=== Reset detected count. ===')
                        detected_count = 0
                        no_detected_start = 0
                        past_time = 0

                # 検知回数の閾値に達したら画像を保存する
                # 送信する画像の2枚目はcapture_interval後のキャプチャを取得したいため、ここではメール送信まで行わない
                if detected_count == cfg['notice_threshold']:
                    # 検知ログ
                    log_level = 'info'
                    log.logging(log_level, 'Detected: {}'.format(label))
                    # ラベルを取っておく
                    last_label = label
                    # カウンタリセット
                    detected_count = 0
                    # 現在時刻取得
                    dt_now = datetime.datetime.now()
                    file_name = dt_now.strftime('%Y%m%d-%H%M%S')
                    # 画像保存
                    _, image_file_path = save_image(frame, file_name, False)
                    image_list.append(image_file_path)
                    log.logging(log_level, 'Image saved: {}'.format(image_file_path))
                    log.logging(log_level, 'Capture interval: {} seconds'.format(cfg['capture_interval']))
                    # 待機
                    time.sleep(cfg['capture_interval'])
                    continue

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
