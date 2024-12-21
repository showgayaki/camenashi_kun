import datetime as dt
from datetime import datetime
from pathlib import Path
from logging import getLogger

import paramiko


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

        logger.info(f'SSH config: {self.config}')

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

    def remove_old_files(self, target_dir: str, threshold_storage_days: int) -> None:
        logger.info('Starting remove old files on SSH server.')
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        client.load_system_host_keys()

        # 経過日数計算用
        today = datetime.today()
        threshold_timedelta = dt.timedelta(days=threshold_storage_days)
        logger.info(f'Removing files older than {(today - dt.timedelta(days=threshold_storage_days)).date()}')

        try:
            client.connect(
                self.config['hostname'],
                username=self.config['user'],
                key_filename=self.config['identityfile'],
                port=self.config['port']
            )
            sftp_connection = client.open_sftp()

            # dir内のファイルで、拡張子が.mp4のファイルのみリストにして返す
            file_list = [file for file in sftp_connection.listdir(target_dir) if Path(file).suffix == '.mp4']
            file_list.sort()

            sftp_connection.chdir(target_dir)
            removed_files = []
            for file_name in file_list:
                # ファイル更新日時を取得して、保存期間を過ぎているか検証
                file_date = datetime.fromtimestamp(sftp_connection.stat(file_name).st_mtime)
                difference = today - file_date

                # 保存期間を過ぎたら削除
                if difference > threshold_timedelta:
                    file_path = Path(target_dir).joinpath(file_name)
                    removed_files.append(str(file_path))
                    client.exec_command(f'rm {file_path}')
                    logger.info(f'Remove file: {file_path}')

            if len(removed_files) == 0:
                logger.info('No files found to remove on the SSH server.')
            else:
                logger.info(f'Removed files: {removed_files}')
        except Exception as e:
            logger.error(e)
        finally:
            client.close()


def test():
    ssh = Ssh('okomesan')
    ssh.remove_old_files('/share/Camenashi', 150)
