import time
import datetime
import socket
import signal
import cv2
import numpy as np
from ping3 import ping
from pathlib import Path
from statistics import mean
from .env import Env
from .logger import Logger
from .discord import Discord
from .ssh import Ssh
import yolov5.detect as detect


class TerminatedExecption(Exception):
    pass


def raise_exception(*_):
    raise TerminatedExecption()


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
        result += '...NG.'
    else:
        result += '...OK.'
    return log_level, result


def main(no_view=False):
    WEITHTS = 'yolov5/yolov5s.pt'
    IMAGE_SIZE = [384, 640]
    computer_name = socket.gethostname()
    root_dir = Path(__file__).resolve().parents[1]
    # systemdの終了を受け取る
    signal.signal(signal.SIGTERM, raise_exception)
    # ログ
    log = Logger(root_dir)
    # 設定読み込み
    env = Env()
    # 通知用
    disco = Discord(env.DISCORD_WEBHOOK_URL)
    # アプリケーション開始ログ
    log.logging('info', f'===== {env.APP_NAME} Started on {computer_name} =====')
    camera_url = f'rtsp://{env.CAMERA_USER}:{env.CAMERA_PASS}@{env.CAMERA_IP}:554/stream2'
    log.logging('info', f'Camera IP address: {env.CAMERA_IP}.')

    # pingで疎通確認
    RETRY_COUNT = 3
    for i in range(RETRY_COUNT):
        log_level, msg = ping_to_target(i, env.CAMERA_IP)
        log.logging(log_level, msg)
        ping_result = False
        if log_level == 'info':
            # 前回pingエラーを送信していたら、回復したよを送信する
            if env.IS_NOTIFIED_PING_ERROR:
                # Discordに通知
                msg = f'\n★ping OK\n{env.CAMERA_IP}と疎通が取れました。\n検知を再開します。'
                discord_result = disco.post(msg)
                log.logging(discord_result['level'], f'Discord result: {discord_result["detail"]}')

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
            for label_list, frame, fps, log_str in detect.run(
                weights=WEITHTS,
                imgsz=IMAGE_SIZE,
                source=camera_url,
                nosave=True,
                view_img=view_img,
                    detect_area=env.DETECT_AREA):
                # ループの最初で解像度を取得しておく
                if is_first_loop:
                    frame_height, frame_width, _ = frame.shape
                    is_first_loop = False

                # video_writerオブジェクトがNoneじゃなければ(動体検知したら)、録画する
                if video_writer is not None:
                    video_writer.write(frame)

                # 検知対象リストにあるか判定
                if env.DETECT_LABEL in label_list:
                    detected_count += 1
                    # 非検知タイマーリセット
                    no_detected_start = 0
                    # 録画時に指定する用に、FPSをlistに入れておく
                    fps_list.append(fps)

                    # 映像書き出し中以外は、ログ文言に検知回数を追記
                    if video_writer is None:
                        log_str += f'Detected count: {detected_count}'
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
                    if no_detected_elapsed_time > env.THRESHOLD_NO_DETECTED_SECONDS:
                        log.logging('info', f'No detected for {env.THRESHOLD_NO_DETECTED_SECONDS} seconds.')

                        if video_writer is None:
                            # video_writerオブジェクトがNoneの場合は、検知回数閾値に達さずに非検知になったとき
                            # （一瞬だけトイレに入って、すぐ出た場合を想定）
                            pass
                        else:
                            # 録画終了
                            video_writer.release()
                            log.logging('info', '○○○ Finish Rec ○○○')
                            log.logging('info', '=== Reset detected count. ===')

                            # SFTPでアップロード
                            ssh = Ssh(env.SSH_HOSTNAME)
                            log.logging('info', f'SSH to {env.SSH_HOSTNAME}({ssh.config["hostname"]})')
                            # NASに動画をSFTPでアップロード
                            sftp_upload_result = ssh.sftp_upload(
                                str(video_file_path),
                                str(Path(env.SSH_UPLOAD_DIR).joinpath(video_file_path.name)),
                            )
                            log.logging(sftp_upload_result['level'], f'SFTP Upload Result: {sftp_upload_result["result"]}({sftp_upload_result["detail"]})')

                            if sftp_upload_result['level'] != 'error':
                                # 古いファイルは削除
                                remove_result = ssh.remove_old_files(env.SSH_UPLOAD_DIR, env.THRESHOLD_STORAGE_DAYS)
                                if remove_result is None:
                                    log.logging('info', f'SSH server: No files are older than {env.THRESHOLD_STORAGE_DAYS} days')
                                else:
                                    log.logging(remove_result['level'], f'Remove Result: {remove_result["result"]}')
                                    log.logging(remove_result['level'], f'Removed Files: {remove_result["detail"]}')

                            # Discordに通知
                            discord_result = disco.post(
                                f'\n{env.DETECT_LABEL}を動体検知しました',
                                [video_file_path]
                            )
                            log.logging(discord_result['level'], f'Discord result: {discord_result["detail"]}')

                            # # 作成した映像削除
                            # remove_videos = []
                            # for video in video_dir.iterdir():
                            #     remove_videos.append(str(video))
                            #     Path(video).unlink()
                            # log.logging('info', f'Delete videos: {remove_videos}')

                        log.logging('info', '=== Restart detecting ===')
                        # 初期化
                        video_writer = None
                        detected_count = 0
                        no_detected_start = 0
                        no_detected_elapsed_time = 0

                    continue

                # 検知回数の閾値に達したら動画書き出し開始
                if detected_count == env.NOTICE_THRESHOLD:
                    # 検知ログ
                    log.logging('info', f'Detected: {env.DETECT_LABEL}')
                    # ここのif文を通らないように、+1しておく
                    detected_count += 1
                    # 現在時刻取得
                    dt_now = datetime.datetime.now()
                    file_name = dt_now.strftime('%Y%m%d-%H%M%S')

                    # 動画保存用ディレクトリ
                    video_dir = Path.joinpath(Path(__file__).resolve().parent, 'videos')
                    # ディレクトリなかったら作成
                    if not video_dir.is_dir():
                        Path.mkdir(video_dir)
                        log.logging('info', f'make directory: {video_dir}')

                    # 書き出し設定
                    fourcc = cv2.VideoWriter_fourcc('a', 'v', 'c', '1')
                    video_suffix = 'mp4'

                    # 動画書き出し
                    video_file_path = Path(video_dir).joinpath(f'{file_name}.{video_suffix}')
                    # FPSは平均を取って、何倍速か計算
                    rec_fps = round(mean(fps_list), 0) * env.MOVIE_SPEED

                    video_writer = cv2.VideoWriter(str(video_file_path), fourcc, rec_fps, (frame_width, frame_height))
                    log.logging('info', '●●● Start Rec ●●●')

                    continue

                # 4角が真っ黒なら映像取得できていないはず。指定秒数経過したら通知する。
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
                    if not is_notified_screen_all_black and black_screen_elapsed_seconds > env.BLACK_SCREEN_SECONDS:
                        # 秒を分に
                        black_screen_elapsed_minutes = int(env.BLACK_SCREEN_SECONDS / 60)
                        log.logging('error', f'{black_screen_elapsed_minutes} minutes have passed since the screen went black.')

                        log.logging('info', 'Start post to Discord.')
                        # 現在時刻取得
                        dt_now = datetime.datetime.now()
                        file_name = dt_now.strftime('%Y%m%d-%H%M%S')
                        # Discordに通知
                        msg = ('\n映像が真っ暗になってから{black_screen_elapsed_minutes}分経過しました。\nカメラをリブートした方がいいかもしれません。')
                        discord_result = disco.post(msg)
                        log.logging(discord_result['level'], f'Discord result: {discord_result["detail"]}')
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
            log.logging('info', f'===== Stop {env.APP_NAME} =====')
        except TerminatedExecption:
            log.logging('info', 'TerminatedExecption: stopped by systemd')
            log.logging('info', f'===== Stop {env.APP_NAME} =====')
        except OSError as e:
            import traceback
            traceback.print_exc()
            log.logging('error', f'ERROR: {e}')
            # Discordに通知
            msg = f'\nやばいです。\n\n{e}\n\nが起きました。{env.PAUSE_SECONDS}秒後に再起動します。'
            discord_result = disco.post(msg)
            log.logging(discord_result['level'], f'Discord result: {discord_result["detail"]}')
            # エラー発生したら一時停止してから再起動
            log.logging('info', f'Pause detecting for {env.PAUSE_SECONDS} seconds')
            time.sleep(env.PAUSE_SECONDS)
            log.logging('info', f'*** Restart {env.APP_NAME} ***')
            # systemdで再起動
            raise e
        except Exception as e:
            log.logging('error', f'Unkown Error: {e}')
            # Discordに通知
            msg = f'\nやばいです。\n\n{e}\n\nが起きました。\n{env.PAUSE_SECONDS}秒後に再起動します。'
            discord_result = disco.post(msg)
            log.logging(discord_result['level'], f'Discord result: {discord_result["detail"]}')
            # エラー発生したら一時停止してから再起動
            log.logging('info', f'Pause detecting for {env.APP_NAME} seconds')
            time.sleep(env.PAUSE_SECONDS)
            log.logging('info', f'*** Restart {env.APP_NAME} ***')
            # systemdで再起動
            raise e
    else:
        log.logging('error', f'[{env.CAMERA_IP}] is NOT responding. Please check device.')

        # すでにpingエラーを通知していたら何もしな
        if env.IS_NOTIFIED_PING_ERROR:
            pass
        else:
            # Discordに通知
            msg = f'\n★ping NG\n{env.CAMERA_IP}は気絶しているみたいです。'
            discord_result = disco.post(msg)
            log.logging(discord_result['level'], f'Discord result: {discord_result["detail"]}')

        log.logging('info', f'===== Stop {env.APP_NAME} =====')
