import paramiko
import datetime
from pathlib import Path
from logging import getLogger


logger = getLogger(__name__)


class Ssh:
    def __init__(self, hostname: str) -> None:
        ssh_config = paramiko.SSHConfig()
        config_file_path = str(Path.home().joinpath('.ssh', 'config'))

        with open(config_file_path, 'r') as f:
            ssh_config.parse(f)

        self.config = ssh_config.lookup(hostname)
        if 'port' not in self.config:
            self.config['port'] = 22

        logger.info(f'ssh config => {self.config}')

    def sftp_upload(self, local: str, server: str) -> bool:
        logger.info('Starting SFTP upload.')
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        client.load_system_host_keys()
        try:
            client.connect(
                self.config['hostname'],
                username=self.config['user'],
                key_filename=self.config['identityfile'],
                port=self.config['port']
            )
            sftp_connection = client.open_sftp()
            sftp_connection.put(local, server)
            logger.info(f'SFTP uploaded: {server}')
            return True
        except Exception as e:
            logger.error(e)
            return False
        finally:
            client.close()

    def remove_old_files(self, dir: str, threshold_storage_days: int) -> None:
        logger.info('Starting remove old files on SSH server.')
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        client.load_system_host_keys()

        # 経過日数計算用
        today = datetime.datetime.today()
        threshold_timedelta = datetime.timedelta(days=threshold_storage_days)

        try:
            client.connect(
                self.config['hostname'],
                username=self.config['user'],
                key_filename=self.config['identityfile'],
                port=self.config['port']
            )
            sftp_connection = client.open_sftp()

            # dir変数から絶対パスを取得
            stdin, stdout, stderr = client.exec_command(f'cd {dir}; pwd')
            dir = [line.strip() for line in stdout][0]
            # dir内のファイルで、拡張子が.mp4のファイルのみリストにして返す
            file_list = [file for file in sftp_connection.listdir(dir) if Path(file).suffix == '.mp4']
            file_list.sort()

            removed_files = []
            for file_name in file_list:
                # ファイル名から日時を取得して、経過日数を計算
                file_date = datetime.datetime.strptime(Path(file_name).stem, '%Y%m%d-%H%M%S')
                difference = today - file_date

                # 保存期間を過ぎたら削除
                if difference > threshold_timedelta:
                    file_path = Path(dir).joinpath(file_name)
                    removed_files.append(str(file_path))
                    client.exec_command('rm {}'.format(file_path))
                    logger.info(f'Remove file: {file_path}')

            if len(removed_files) == 0:
                logger.info('No files found to delete on the SSH server.')
            else:
                logger.info(f'Removed files: {removed_files}')
        except Exception as e:
            logger.error(e)
        finally:
            client.close()
            del client, stdin, stdout, stderr
