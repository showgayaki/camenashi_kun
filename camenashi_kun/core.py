import time
import datetime
import socket
import signal
import cv2
import numpy as np
from ping3 import ping
from pathlib import Path
from statistics import mean
from .config import Config
from .logger import Logger
from .line_messaging_api import LineMessagingApi
from .aws import S3
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


def save_image(frame, file_name):
    image_dir = Path.joinpath(Path(__file__).resolve().parent, 'images')
    # ディレクトリなかったら作成
    if not image_dir.is_dir():
        Path.mkdir(image_dir)

    # 画像保存パス、stringじゃないといけない
    image_file_path = Path.joinpath(image_dir, f'{file_name}.png')
    # 画像保存
    cv2.imwrite(str(image_file_path), frame)
    return image_dir, image_file_path


def post_line(line_info, message_dict):
    bot = LineMessagingApi(line_info['access_token'])
    message_result = bot.send_message(line_info['to'], message_dict)
    return message_result


def video_message(label, urls):
    message_dict = {
        'messages': [
            {
                'type': 'text',
                'text': f'{label}を動体検知しました'
            },
            {
                'type': 'video',
                'originalContentUrl': urls['video'],
                'previewImageUrl': urls['image'],
            }
        ]
    }
    return message_dict


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
        last_label = ''  # メール送信用の検知した物体のラベル
        image_dir = ''  # キャプチャ画像保存用ディレクトリ
        image_file_path = ''  # キャプチャ画像パス
        video_dir = ''  # 録画映像保存用ディレクトリ
        video_file_path = ''  # 録画映像ファイル
        video_writer = None  # opencvのvideo writer
        fps_list = []  # 録画映像のFPS
        no_detected_start = 0  # 非検知秒数のカウント用
        no_detected_elapsed_time = 0  # 非検知経過時間
        view_img = not no_view  # ストリーミング表示するかは、引数から受け取る
        is_first_loop = True  # ループの最初かどうかフラグ
        black_screen_start = 0  # 真っ黒画面になった時間
        black_screen_elapsed_seconds = 0  # 真っ黒画面の経過時間
        is_notified_screen_all_black = False  # 映像が真っ暗になったことを通知したかフラグ

        try:
            for label, frame, fps, log_str in detect.run(weights=WEITHTS, imgsz=IMAGE_SIZE, source=camera_url, nosave=True, view_img=view_img):
                # ループの最初で解像度を取得しておく
                if is_first_loop:
                    frame_height, frame_width, _ = frame.shape
                    is_first_loop = False

                # video_writerオブジェクトがNoneじゃなければ(動体検知したら)、録画する
                if video_writer is not None:
                    video_writer.write(frame)

                # 検知対象リストにあるか判定
                if label in cfg['detect_label']:
                    detected_count += 1
                    # 非検知タイマーリセット
                    no_detected_start = 0
                    # 録画時に指定する用に、FPSをlistに入れておく
                    fps_list.append(fps)

                    # 映像書き出し中以外は、ログ文言に検知回数を追記
                    if video_writer is None:
                        log_str += ' Detected count: {}'.format(detected_count)
                        log.logging('info', log_str)
                elif no_detected_start == 0:
                    # 非検知になったらタイマースタート
                    no_detected_start = time.perf_counter()
                    if detected_count > 0:
                        log.logging('info', 'No detected start.')
                elif detected_count > 0:
                    # 非検知秒数カウント
                    no_detected_elapsed_time = time.perf_counter() - no_detected_start

                    # 非検知秒数閾値を超えたら
                    if no_detected_elapsed_time > cfg['threshold_no_detected_seconds']:
                        log.logging('info', 'No detected for {} seconds.'.format(cfg['threshold_no_detected_seconds']))

                        if video_writer is None:
                            # video_writerオブジェクトがNoneの場合は、検知回数閾値に達さずに非検知になったとき
                            # （一瞬だけトイレに入って、すぐ出た場合を想定）
                            pass
                        else:
                            # 録画終了
                            video_writer.release()
                            log.logging('info', '○○○ Finish Rec ○○○')
                            log.logging('info', '=== Reset detected count. ===')

                            # S3にアップロードして、アップロードしたファイルの署名付きURLを取得
                            aws = S3(cfg['s3_bucket_name'])
                            presigned_urls = {}
                            for key, val in {'image': image_file_path, 'video': video_file_path}.items():
                                upload_result = aws.upload(str(val), val.name)
                                if 'error' in upload_result:
                                    log.logging('error', 'Upload Result: [{}]'.format(upload_result['error']))
                                else:
                                    log.logging('info', 'Upload Result: [{}]'.format(upload_result['info']))
                                    presigned_url = aws.presigned_url(upload_result[log_level], cfg['s3_expires_in'])
                                    log.logging('info', 'Presigned Url: [{}]'.format(presigned_url))
                                    presigned_urls[key] = presigned_url

                            # LINEに通知
                            log.logging('info', 'Start post to LINE.')
                            line_result = post_line(cfg['line_info'], video_message(last_label, presigned_urls))
                            log_level = 'error' if 'error' in line_result else 'info'
                            log.logging(log_level, 'LINE result: {}'.format(line_result[log_level]))

                            # 作成した画像削除
                            remove_images = []
                            for image in image_dir.iterdir():
                                remove_images.append(str(image))
                                Path(image).unlink()
                            log.logging('info', 'Delete images: {}'.format(remove_images))

                            # 作成した映像削除
                            remove_videos = []
                            for video in video_dir.iterdir():
                                remove_videos.append(str(video))
                                Path(video).unlink()
                            log.logging('info', 'Delete videos: {}'.format(remove_videos))

                        log.logging('info', '=== Restart detecting ===')
                        # 初期化
                        last_label = ''
                        video_writer = None
                        detected_count = 0
                        no_detected_start = 0
                        no_detected_elapsed_time = 0

                    continue

                # 検知回数の閾値に達したら画像を保存して、動画書き出し開始
                if detected_count == cfg['notice_threshold']:
                    # 検知ログ
                    log.logging('info', 'Detected: {}'.format(label))
                    # ラベルを取っておく
                    last_label = label
                    # ここのif文を通らないように、+1しておく
                    detected_count += 1
                    # 現在時刻取得
                    dt_now = datetime.datetime.now()
                    file_name = dt_now.strftime('%Y%m%d-%H%M%S')
                    # 画像保存
                    image_dir, image_file_path = save_image(frame, file_name)
                    log.logging('info', 'Image saved: {}'.format(image_file_path))

                    # 動画保存用ディレクトリ
                    video_dir = Path.joinpath(Path(__file__).resolve().parent, 'videos')
                    # ディレクトリなかったら作成
                    if not video_dir.is_dir():
                        Path.mkdir(video_dir)
                        log.logging('info', 'make directory: {}'.format(video_dir))

                    # mp4で動画書き出し
                    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
                    video_file_path = Path(video_dir).joinpath(f'{file_name}.mp4')
                    # FPSは平均値を取る
                    fps_mean = round(mean(fps_list), 0)

                    video_writer = cv2.VideoWriter(str(video_file_path), fourcc, fps_mean, (frame_width, frame_height))
                    log.logging('info', '●●● Start Rec ●●●')

                    continue

                # 4角が真っ黒なら映像取得できていないはず。指定秒数経過したらLINEで通知する。
                if (np.all(frame[0][0] == BLACK_COLOR_CODE) and np.all(frame[0][frame_width - 1] == BLACK_COLOR_CODE)
                        and np.all(frame[frame_height - 1][frame_width - 1] == BLACK_COLOR_CODE) and np.all(frame[frame_height - 1][0] == BLACK_COLOR_CODE)):
                    # 真っ黒画面になってからの経過時間を計測
                    if black_screen_start == 0:
                        log.logging('error', 'Screen has gone BLACK.')
                        is_notified_screen_all_black = False  # 通知フラグ初期化
                        black_screen_start = time.perf_counter()  # 真っ黒スタート時間取得
                        continue
                    else:
                        black_screen_elapsed_seconds = time.perf_counter() - black_screen_start

                    # 通知していなくて、指定時間経過していたら通知
                    if not is_notified_screen_all_black and black_screen_elapsed_seconds > cfg['black_screen_seconds']:
                        # 秒を分に
                        black_screen_elapsed_minutes = int(cfg['black_screen_seconds'] / 60)
                        log.logging('error', '{} minutes have passed since the screen went black.'.format(black_screen_elapsed_minutes))

                        log.logging('info', 'Start post to LINE.')
                        # 現在時刻取得
                        dt_now = datetime.datetime.now()
                        file_name = dt_now.strftime('%Y%m%d-%H%M%S')
                        # 画像保存
                        _, image_file_path = save_image(frame, file_name, False)
                        log.logging('info', 'Image saved: {}'.format(image_file_path))
                        # LINEに通知
                        msg = '\n映像が真っ暗になってから{}分経過しました。\nカメラをリブートした方がいいかもしれません。'.format(black_screen_elapsed_minutes)
                        post_result = post_line(cfg['line_info'], image_file_path, msg)
                        log_level = 'error' if 'Error' in post_result else 'info'
                        log.logging(log_level, 'LINE result: {}'.format(post_result))
                        # 画像削除
                        Path(image_file_path).unlink()
                        # 通知しました
                        is_notified_screen_all_black = True
                    else:
                        continue
                elif black_screen_elapsed_seconds > 0:
                    # 4角真っ黒から回復した場合
                    log.logging('info', 'Recovered from screen black.')
                    # 初期化
                    is_notified_screen_all_black = False
                    black_screen_start = 0
                    black_screen_elapsed_seconds = 0

        except KeyboardInterrupt:
            log.logging('info', 'Ctrl + C pressed...')
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
        msg = {
            'messages': [
                {
                    'type': 'text',
                    'text': '★ping NG\n{}は気絶しているみたいです。'.format(cfg['camera_info']['camera_ip'])
                }
            ]
        }
        # エラーをLINEに送信
        line_result = post_line(cfg['line_info'], msg)
        log_level = 'error' if 'Error' in line_result else 'info'
        log.logging(log_level, 'LINE result: {}'.format(line_result))
        log.logging('info', '===== Stop {} ====='.format(cfg['app_name']))
