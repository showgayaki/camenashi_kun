from email.mime import image
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from jinja2 import Environment, FileSystemLoader
from pathlib import Path


class Mail:
    def __init__(self, smtp_dict):
        self.smtp_dict = smtp_dict.copy()

    def build_body(self, label, image_list):
        # テンプレート読み込み
        env = Environment(loader=FileSystemLoader(Path(__file__).resolve().parent.joinpath('templates')))
        template = env.get_template('base.html')

        # テンプレートに渡してbody作成
        body = template.render(label=label, image_list=image_list)
        return body

    def create_message(self, body_dict, image_list=None):
        msg = MIMEMultipart()
        msg['Subject'] = body_dict['subject']
        msg['To'] = self.smtp_dict['mail_to']
        msg['Cc'] = self.smtp_dict['mail_cc']
        msg['Date'] = formatdate()

        body = MIMEText(body_dict['body'], 'html')
        msg.attach(body)

        # 画像があればMIMEオブジェクト追加
        if image_list:
            for i, image_file_path in enumerate(image_list):
                with open(image_file_path, 'rb') as f:
                    image = MIMEImage(f.read())
                    image.add_header('Content-ID', '<detected_image_{}>'.format(i + 1))
                msg.attach(image)
        return msg

    def send_mail(self, msg):
        smtp_obj = smtplib.SMTP(self.smtp_dict['smtp_server'], self.smtp_dict['smtp_port'])
        send_list = self.smtp_dict['mail_to'].split(',')
        # Ccがあれば追加
        if self.smtp_dict['mail_cc']:
            send_list += self.smtp_dict['mail_cc'].split(',')
        try:
            smtp_obj.ehlo()
            smtp_obj.starttls()
            smtp_obj.login(self.smtp_dict['smtp_user'], self.smtp_dict['smtp_pass'])
            smtp_obj.sendmail(self.smtp_dict['smtp_user'], send_list, str(msg))
            # Ccの有無でログ出力変更
            if self.smtp_dict['mail_cc']:
                send_target = 'To [{}] Cc [{}]'.format(self.smtp_dict['mail_to'], self.smtp_dict['mail_cc'])
            else:
                send_target = 'To [{}]'.format(self.smtp_dict['mail_to'])
            return 'Succeeded to send mail. {}'.format(send_target)
        except smtplib.SMTPException as e:
            return 'Error: {}'.format(e)
        finally:
            smtp_obj.close()
