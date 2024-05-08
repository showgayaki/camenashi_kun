import paramiko
from pathlib import Path


class Ssh:
    def __init__(self, hostname):
        ssh_config = paramiko.SSHConfig()
        config_file_path=str(Path.home().joinpath('.ssh', 'config'))

        with open(config_file_path, 'r') as f:
            ssh_config.parse(f)

        self.config = ssh_config.lookup(hostname)
        if 'port' not in self.config:
            self.config['port'] = 22

    def sftp_upload(self, local, server):
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
            return {'level': 'info', 'result': 'Succeeded', 'detail': local}
        except Exception as e:
            return {'level': 'error', 'result': 'Failed', 'detail': str(e)}
        finally:
            client.close()
