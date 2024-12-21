import time
import datetime
import signal
from logging import getLogger
from pathlib import Path
from statistics import mean

import cv2
import numpy as np
from ping3 import ping

from camenashi_kun import env
from camenashi_kun.ffmpeg import Ffmpeg
from camenashi_kun.ssh import Ssh
from camenashi_kun.discord import Discord
import yolov5.detect as detect


logger = getLogger(__name__)
disco = Discord(env.DISCORD_WEBHOOK_URL)


class TerminatedExecption(Exception):
    pass


def raise_exception(*_):
    raise TerminatedExecption()


def ping_to_target(target_ip: str) -> bool:
    RETRY_COUNT = 3
    for i in range(RETRY_COUNT):
        result = f'Ping Try Count {i + 1}: Connect to {target_ip} is '
        # ping実行
        try:
            res = ping(target_ip)
            if type(res) is float:
                logger.info(f'{result}...OK')
                # 前回pingエラーを送信していたら、回復したよを送信する
                if env.IS_NOTIFIED_PING_ERROR:
                    # Discordに通知
                    disco.post(f'\n★ping OK\n{env.CAMERA_IP}と疎通が取れました。\n検知を再開します。')
                    # 環境変数を更新
                    env.update_value('IS_NOTIFIED_PING_ERROR', False)
                return True
            else:
                raise
        except Exception as e:
            logger.error(f'{result}...NG')
            logger.error(e)

        # ping返って来なかったらちょっと待ってから再度ping
        time.sleep(5)

    return False


def main(no_view=False) -> None:
    # systemdの終了を受け取る
    signal.signal(signal.SIGTERM, raise_exception)
    logger.info(f'Camera IP address: {env.CAMERA_IP}.')

    # pingで疎通確認が取れたら実行
    if ping_to_target(env.CAMERA_IP):
        logger.info('Start streaming and detecting.')

        BLACK_COLOR_CODE = 0
        detected_count = 0  # 検知回数
        video_dir = Path.joinpath(Path(__file__).resolve().parent, 'videos')  # 録画映像保存用ディレクトリ
        video_file_path = Path()  # 録画映像ファイル
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
                weights='yolov5/yolov5s.pt',
                imgsz=[360, 640],
                source=f'rtsp://{env.CAMERA_USER}:{env.CAMERA_PASS}@{env.CAMERA_IP}:554/stream2',
                nosave=True,
                view_img=view_img,
                detect_area=env.DETECT_AREA
            ):
                # ループの最初で解像度を取得しておく
                if is_first_loop:
                    frame_height, frame_width, _ = frame.shape
                    logger.info(f'frame_width: {frame_width}, frame_height: {frame_height}')
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
                        logger.info(log_str)
                elif no_detected_start == 0:
                    # 非検知になったらタイマースタート
                    no_detected_start = time.perf_counter()
                    if detected_count > 0:
                        logger.info('No detected start.')
                elif detected_count > 0:
                    # 非検知秒数カウント
                    no_detected_elapsed_time = time.perf_counter() - no_detected_start

                    # 非検知秒数閾値を超えたら
                    if no_detected_elapsed_time > env.THRESHOLD_NO_DETECTED_SECONDS:
                        logger.info(f'No detected for {env.THRESHOLD_NO_DETECTED_SECONDS} seconds.')

                        if video_writer is None:
                            # video_writerオブジェクトがNoneの場合は、検知回数閾値に達さずに非検知になったとき
                            # （一瞬だけトイレに入って、すぐ出た場合を想定）
                            pass
                        else:
                            # 録画終了
                            video_writer.release()
                            logger.info('○○○ Finish Rec ○○○')
                            logger.info('=== Reset detected count. ===')

                            # 圧縮
                            ffmpeg = Ffmpeg()
                            video_file_path = ffmpeg.compress(video_file_path, env.FFMPEG_OPTIONS)

                            # SFTPでアップロード
                            ssh = Ssh(env.SSH_HOSTNAME)
                            logger.info(f'SSH to {env.SSH_HOSTNAME}({ssh.config["hostname"]})')
                            # NASに動画をSFTPでアップロード
                            sftp_upload_result = ssh.sftp_upload(
                                str(video_file_path),
                                str(Path(env.SSH_UPLOAD_DIR).joinpath(video_file_path.name)),
                            )

                            # アップロードが成功したら古いファイルは削除
                            if sftp_upload_result:
                                ssh.remove_old_files(env.SSH_UPLOAD_DIR, env.THRESHOLD_STORAGE_DAYS)

                            # Discordに通知できた映像は削除する
                            # 以前POSTに失敗したファイルもvideosディレクトリに残っているはずなので
                            # ここで順番にPOSTする
                            removed_videos = []
                            sorted_videos = sorted(video_dir.iterdir(), key=lambda x: x.name)
                            for video in sorted_videos:
                                uploaded_file_path = f'//{ssh.config["hostname"]}{Path(env.SSH_UPLOAD_DIR).joinpath(video.name)}'
                                if disco.post(
                                    f'{env.DETECT_LABEL}を動体検知しました\n{uploaded_file_path}',
                                    [video],
                                    mention_id=env.MENTION_ID,
                                ):
                                    removed_videos.append(str(video))
                                    # 削除
                                    Path(video).unlink()
                                    # 動画が複数あれば、次のPOSTまでちょっと待機
                                    if len(sorted_videos) > 1:
                                        time.sleep(3)
                                else:
                                    # POSTに失敗したら、以降のファイルは次回に持ち越し
                                    break
                            logger.info(f'Delete videos: {removed_videos}')

                        logger.info('=== Restart detecting ===')
                        # 初期化
                        video_writer = None
                        detected_count = 0
                        no_detected_start = 0
                        no_detected_elapsed_time = 0

                    continue

                # 検知回数の閾値に達したら動画書き出し開始
                if detected_count == env.NOTICE_THRESHOLD:
                    # 検知ログ
                    logger.info(f'Detected: {env.DETECT_LABEL}')
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
                        logger.info(f'make directory: {video_dir}')

                    # 書き出し設定
                    fourcc = cv2.VideoWriter_fourcc('a', 'v', 'c', '1')
                    video_suffix = 'mp4'

                    # 動画書き出し
                    video_file_path = Path(video_dir).joinpath(f'{file_name}.{video_suffix}')
                    # FPSは平均を取って、何倍速か計算
                    rec_fps = round(mean(fps_list), 0) * env.MOVIE_SPEED

                    video_writer = cv2.VideoWriter(str(video_file_path), fourcc, rec_fps, (frame_width, frame_height))
                    logger.info('●●● Start Rec ●●●')

                    continue

                # 4角が真っ黒なら映像取得できていないはず。指定秒数経過したら通知する。
                if (np.all(frame[0][0] == BLACK_COLOR_CODE) and np.all(frame[0][frame_width - 1] == BLACK_COLOR_CODE)
                        and np.all(frame[frame_height - 1][frame_width - 1] == BLACK_COLOR_CODE) and np.all(frame[frame_height - 1][0] == BLACK_COLOR_CODE)):
                    # 真っ黒画面になってからの経過時間を計測
                    if black_screen_start == 0:
                        logger.error('Screen has gone BLACK.')
                        is_notified_screen_all_black = False  # 通知フラグ初期化
                        black_screen_start = time.perf_counter()  # 真っ黒スタート時間取得
                        continue
                    else:
                        black_screen_elapsed_seconds = time.perf_counter() - black_screen_start

                    # 通知していなくて、指定時間経過していたら通知
                    if not is_notified_screen_all_black and black_screen_elapsed_seconds > env.BLACK_SCREEN_SECONDS:
                        # 秒を分に
                        black_screen_elapsed_minutes = int(env.BLACK_SCREEN_SECONDS / 60)
                        logger.error(f'{black_screen_elapsed_minutes} minutes have passed since the screen went black.')

                        logger.info('Start post to Discord.')
                        # 現在時刻取得
                        dt_now = datetime.datetime.now()
                        file_name = dt_now.strftime('%Y%m%d-%H%M%S')
                        # Discordに通知
                        is_notified_screen_all_black = disco.post(
                            f'\n映像が真っ暗になってから{black_screen_elapsed_minutes}分経過しました。\nカメラをリブートした方がいいかもしれません。'
                        )
                    else:
                        continue
                elif black_screen_elapsed_seconds > 0:
                    # 4角真っ黒から回復した場合
                    logger.info('Recovered from screen black.')
                    # 初期化
                    is_notified_screen_all_black = False
                    black_screen_start = 0
                    black_screen_elapsed_seconds = 0

        except KeyboardInterrupt:
            logger.info('Ctrl + C pressed...')
        except TerminatedExecption:
            logger.info('TerminatedExecption: stopped by systemd')
        except OSError as e:
            import traceback
            traceback.print_exc()
            logger.error(f'ERROR: {e}')
            # Discordに通知
            disco.post(f'\nやばいです。\n\n{e}\n\nが起きました。{env.PAUSE_SECONDS}秒後に再起動します。')
            # エラー発生したら一時停止してから再起動
            logger.info(f'Pause detecting for {env.PAUSE_SECONDS} seconds')
            time.sleep(env.PAUSE_SECONDS)
            logger.info(f'*** Restart {env.APP_NAME} ***')
            # systemdで再起動
            raise e
        except Exception as e:
            logger.error(f'Unkown Error: {e}')
            # Discordに通知
            disco.post(f'\nやばいです。\n\n{e}\n\nが起きました。\n{env.PAUSE_SECONDS}秒後に再起動します。')
            # エラー発生したら一時停止してから再起動
            logger.info(f'Pause detecting for {env.APP_NAME} seconds')
            time.sleep(env.PAUSE_SECONDS)
            logger.info(f'*** Restart {env.APP_NAME} ***')
            # systemdで再起動
            raise e
    else:
        logger.error(f'[{env.CAMERA_IP}] is NOT responding. Please check device.')

        # すでにpingエラーを通知していたら何もしない
        if env.IS_NOTIFIED_PING_ERROR:
            pass
        else:
            # Discordに通知できたら.env書き換え
            env.update_value(
                'IS_NOTIFIED_PING_ERROR',
                disco.post(f'\n★ping NG\n{env.CAMERA_IP}は気絶しているみたいです。')
            )
