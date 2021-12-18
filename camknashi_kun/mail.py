import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate


class Mail:
    def __init__(self, smtp_dict):
        self.smtp_dict = smtp_dict.copy()

    def create_message(self, body_dict):
        msg = MIMEText(body_dict['body'], 'html')
        msg['Subject'] = body_dict['subject']
        msg['To'] = self.smtp_dict['mail_to']
        msg['Cc'] = self.smtp_dict['mail_cc']
        msg['Date'] = formatdate()
        return msg

    def send_mail(self, msg):
        smtp_obj = smtplib.SMTP(self.smtp_dict['smtp_server'], self.smtp_dict['smtp_port'])
        try:
            smtp_obj.ehlo()
            smtp_obj.starttls()
            smtp_obj.login(self.smtp_dict['smtp_user'], self.smtp_dict['smtp_pass'])
            smtp_obj.sendmail(self.smtp_dict['smtp_user'], self.smtp_dict['mail_to'], str(msg))
            return 'Succeeded to send mail. To [{}]'.format(self.smtp_dict['mail_to'])
        except smtplib.SMTPException as e:
            return 'Error: {}'.format(e)
        finally:
            smtp_obj.close()
