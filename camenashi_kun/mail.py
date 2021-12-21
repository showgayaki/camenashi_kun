from email.mime import image
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from pathlib import Path


class Mail:
    def __init__(self, smtp_dict):
        self.smtp_dict = smtp_dict.copy()

    def create_message(self, body_dict, image_list=None):
        msg = MIMEMultipart()
        msg['Subject'] = body_dict['subject']
        msg['To'] = self.smtp_dict['mail_to']
        msg['Cc'] = self.smtp_dict['mail_cc']
        msg['Date'] = formatdate()

        body = MIMEText(body_dict['body'], 'html')
        msg.attach(body)

        # 画像があったら添付
        if image_list:
            for image_file_path in image_list:
                with open(image_file_path, 'rb') as f:
                    img = f.read()
                    image = MIMEImage(img, name=Path(image_file_path).name)
                msg.attach(image)
        return msg

    def send_mail(self, msg):
        smtp_obj = smtplib.SMTP(self.smtp_dict['smtp_server'], self.smtp_dict['smtp_port'])
        send_list = self.smtp_dict['mail_to'].split(',') + self.smtp_dict['mail_cc'].split(',')
        try:
            smtp_obj.ehlo()
            smtp_obj.starttls()
            smtp_obj.login(self.smtp_dict['smtp_user'], self.smtp_dict['smtp_pass'])
            smtp_obj.sendmail(self.smtp_dict['smtp_user'], send_list, str(msg))
            return 'Succeeded to send mail. To [{}]'.format(self.smtp_dict['mail_to'])
        except smtplib.SMTPException as e:
            return 'Error: {}'.format(e)
        finally:
            smtp_obj.close()
