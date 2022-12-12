import time
import datetime
import socket
import signal
import cv2
import numpy as np
from ping3 import ping
from pathlib import Path
from .config import Config
from .logger import Logger
from .line_notify import LineNotify
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


def post_line(line_info, image_file_path, msg):
    bot = LineNotify(line_info['api_url'], line_info['access_token'])
    payload = {
        'message': msg,
        'stickerPackageId': None,
        'stickerId': None
    }
    return bot.send_message(payload, image_file_path)


def main(no_view=False):
    WEITHTS = 'yolov5/yolov5s.pt'
    IMAGE_SIZE = [640, 640]
    computer_name = socket.gethostname()
    root_dir = Path(__file__).resolve().parents[1]
    # systemdの終了を受け取る
    signal.signal(signal.SIGTERM, raise_exception)
    # ログ
    log = Logger(root_dir)
    # 設定読み込み
    cfg = load_config(root_dir)
    # アプリケーション開始ログ
    log.logging('info', '===== {} Started on {} ====='.format(cfg['app_name'], computer_name))
    camera_url = 'rtsp://{}:{}@{}:554/stream2'.format(
        cfg['camera_info']['camera_user'],
        cfg['camera_info']['camera_pass'],
        cfg['camera_info']['camera_ip'],
    )
    log.logging('info', 'Camera IP address: {}.'.format(cfg['camera_info']['camera_ip']))

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
        BLACK_COLOR_CODE = 0
        detected_count = 0  # 検知回数
        image_list = []  # 保存した画像Pathリスト
        last_label = ''  # メール送信用の検知した物体のラベル
        label = ''  # メール送信用の検知した物体のラベル
        no_detected_start = 0  # 非検知秒数のカウント用
        elapsed_time = 0  # 非検知経過時間
        view_img = not no_view  # ストリーミング表示するかは、引数から受け取る
        is_first_loop = True  # ループの最初かどうかフラグ
        black_screen_start = 0  # 真っ黒画面になった時間
        is_notified_screen_all_black = False  # 映像が真っ暗になったことを通知したかフラグ
        try:
            for label, frame, log_str in detect.run(weights=WEITHTS, imgsz=IMAGE_SIZE, source=camera_url, nosave=True, view_img=view_img):
                # ループの最初で解像度を取得しておく
                if is_first_loop:
                    frame_height, frame_width, _ = frame.shape
                    is_first_loop = False

                # 画像PathリストにPathが入っていたら、LINE通知
                if len(image_list) > 0:
                    # 現在時刻取得
                    dt_now = datetime.datetime.now()
                    file_name = dt_now.strftime('%Y%m%d-%H%M%S')
                    # 画像保存
                    image_dir, image_file_path = save_image(frame, file_name, False)
                    log.logging('info', 'Image saved: {}'.format(image_file_path))
                    image_list.append(image_file_path)

                    # 画像一覧取得(画像連結が逆になったことがあったのでソートしておく)
                    image_list = [str(image) for image in image_dir.glob('*.png')]
                    image_list.sort()
                    log.logging('info', 'Concatenate Images: {}'.format(image_list))
                    # 画像を連結
                    concatenate_list = [cv2.imread(image) for image in image_list]
                    concatenated_image = cv2.vconcat(concatenate_list)
                    # ファイル名の時間箇所が被らないように1秒加算
                    dt_now = dt_now + datetime.timedelta(seconds=1)
                    file_name = dt_now.strftime('%Y%m%d-%H%M%S')
                    # 連結した画像保存
                    _, image_file_path = save_image(concatenated_image, file_name, True)
                    log.logging('info', 'Concatenated Image saved: {}'.format(image_file_path))

                    # LINEに通知
                    log.logging('info', 'Start post to LINE.')
                    post_result = post_line(cfg['line_info'], image_file_path, f'\n{last_label}を動体検知しました。')
                    log_level = 'error' if 'Error' in post_result else 'info'
                    log.logging(log_level, 'LINE result: {}'.format(post_result))

                    # 作成した画像削除
                    remove_images = []
                    for image in image_dir.iterdir():
                        remove_images.append(str(image))
                        Path(image).unlink()
                    log.logging('info', 'Delete images: {}'.format(remove_images))
                    # 初期化
                    last_label = ''
                    image_list = []
                    # 検知後は一時停止して、連続通知回避
                    log.logging('info', 'Pause detecting for {} seconds'.format(cfg['pause_seconds']))
                    time.sleep(cfg['pause_seconds'])
                    # カウンタ・タイマーリセット
                    detected_count = 0
                    no_detected_start = 0
                    elapsed_time = 0
                    log.logging('info', '=== Restart detecting ===')
                    continue

                # 検知対象リストにあるか判定
                if label in cfg['detect_label']:
                    detected_count += 1
                    # 非検知タイマーリセット
                    no_detected_start = 0
                    # ログ文言に検知回数を追記
                    log_str += ' Detected count: {}'.format(detected_count)
                    log.logging('info', log_str)
                elif no_detected_start == 0:
                    # 非検知になったらタイマースタート
                    no_detected_start = time.perf_counter()
                elif detected_count > 0:
                    # 非検知秒数カウント
                    elapsed_time = time.perf_counter() - no_detected_start
                    # 非検知秒数閾値に達したらリセット
                    if elapsed_time > cfg['pause_seconds']:
                        log.logging('info', 'No detected for {} seconds.'.format(cfg['pause_seconds']))
                        log.logging('info', '=== Reset detected count. ===')
                        detected_count = 0
                        no_detected_start = 0
                        elapsed_time = 0

                # 検知回数の閾値に達したら画像を保存する
                # 送信する画像の2枚目はcapture_interval後のキャプチャを取得したいため、ここではメール送信まで行わない
                if detected_count == cfg['notice_threshold']:
                    # 検知ログ
                    log.logging('info', 'Detected: {}'.format(label))
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
                    log.logging('info', 'Image saved: {}'.format(image_file_path))
                    log.logging('info', 'Capture interval: {} seconds'.format(cfg['capture_interval']))
                    # 待機
                    time.sleep(cfg['capture_interval'])
                    continue

                # 4角が真っ黒なら映像取得できていないはず。指定秒数経過したらLINEで通知する。
                if (np.all(frame[0][0] == BLACK_COLOR_CODE) and np.all(frame[0][frame_width - 1] == BLACK_COLOR_CODE)
                        and np.all(frame[frame_height - 1][frame_width - 1] == BLACK_COLOR_CODE) and np.all(frame[frame_height - 1][0] == BLACK_COLOR_CODE)):
                    # 真っ黒画面になってからの経過時間を計測
                    if black_screen_start == 0:
                        log.logging('error', 'Screen has gone BLACK.')
                        black_screen_start = time.perf_counter()
                        continue
                    else:
                        black_screen_elapsed_seconds = time.perf_counter() - black_screen_start

                    if is_notified_screen_all_black:
                        continue
                    elif black_screen_elapsed_seconds > cfg['black_screen_seconds']:
                        # 秒を分に
                        black_screen_elapsed_minutes = cfg['black_screen_seconds'] / 60
                        log.logging('error', '{} minutes have passed since the screen went black.'.format(black_screen_elapsed_minutes))

                        log.logging('info', 'Start post to LINE.')
                        # 現在時刻取得
                        dt_now = datetime.datetime.now()
                        file_name = dt_now.strftime('%Y%m%d-%H%M%S')
                        # 画像保存
                        _, image_file_path = save_image(frame, file_name, False)
                        log.logging('info', 'Image saved: {}'.format(image_file_path))
                        # LINEに通知
                        msg = '\n映像が真っ暗になってから{:.0f}分経過しました。\nカメラをリブートした方がいいかもしれません。'.format(black_screen_elapsed_minutes)
                        post_result = post_line(cfg['line_info'], image_file_path, msg)
                        log_level = 'error' if 'Error' in post_result else 'info'
                        log.logging(log_level, 'LINE result: {}'.format(post_result))
                        # 画像削除
                        Path(image_file_path).unlink()
                        # 通知しました
                        is_notified_screen_all_black = True
                        # 初期化
                        black_screen_start = 0
                        black_screen_elapsed_seconds = 0
                elif is_notified_screen_all_black:
                    log.logging('info', 'Recovered from screen black.')
                    # 4角真っ黒kから回復したら初期化
                    is_notified_screen_all_black = False
                    black_screen_start = 0
                    black_screen_elapsed_seconds = 0

        except KeyboardInterrupt:
            log.logging('info', 'Ctrl + C pressed...'.format(cfg['app_name']))
            log.logging('info', '===== Stop {} ====='.format(cfg['app_name']))
        except TerminatedExecption:
            log.logging('info', 'TerminatedExecption: stopped by systemd')
            log.logging('info', '===== Stop {} ====='.format(cfg['app_name']))
        except OSError as e:
            import traceback
            traceback.print_exc()
            log.logging('error', 'ERROR: {}'.format(e))
            # エラー発生したら一時停止してから再起動
            log.logging('info', 'Pause detecting for {} seconds'.format(cfg['pause_seconds']))
            time.sleep(cfg['pause_seconds'])
            log.logging('info', '*** Restart {} ***'.format(cfg['app_name']))
            # systemdで再起動
            raise e
        except Exception as e:
            log.logging('error', 'Unkown Error: {}'.format(e))
            # エラー発生したら一時停止してから再起動
            log.logging('info', 'Pause detecting for {} seconds'.format(cfg['pause_seconds']))
            time.sleep(cfg['pause_seconds'])
            log.logging('info', '*** Restart {} ***'.format(cfg['app_name']))
            # systemdで再起動
            raise e
    else:
        log.logging('error', '[{}] is NOT responding. Please check device.'
                    .format(cfg['camera_info']['camera_ip']))
        # エラーをLINEに送信
        post_result = post_line(
            cfg['line_info'],
            None,
            '\n★ping NG\n{}は気絶しているみたいです。'.format(cfg['camera_info']['camera_ip'])
        )
        log_level = 'error' if 'Error' in post_result else 'info'
        log.logging(log_level, 'LINE result: {}'.format(post_result))
        log.logging('info', '===== Stop {} ====='.format(cfg['app_name']))
