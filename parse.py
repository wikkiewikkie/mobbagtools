import sqlite3
import datetime

from collections import OrderedDict
from email import generator
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import format_datetime


class MobilyzeCase(object):

    def __init__(self, path):
        self.path = path

        self.conversations = OrderedDict()
        self.participants = dict()
        self.messages = dict()

        self.conn = sqlite3.connect(self.path)
        self.cursor = self.conn.cursor()

        self._populate_conversations()
        print(len(self.conversations), "conversations")
        self._populate_participants()
        print(len(self.participants), "participants")
        self._populate_messages()
        print(len(self.messages), "messages")

    def _populate_conversations(self):
        for row in self.cursor.execute('SELECT id, service FROM message_conversations ORDER BY id'):
            self.conversations[str(row[0])] = Conversation(self, str(row[0]), row[1])
           
    def _populate_participants(self):
        for row in self.cursor.execute('SELECT id, display_name, display_address FROM message_participants ORDER BY id'):
            self.participants[str(row[0])] = Participant(self, str(row[0]), row[1], row[2])

    def _populate_messages(self):
        for row in self.cursor.execute('SELECT id, sender_id, conversation_id FROM messages ORDER BY conversation_id, time'):
            self.messages[str(row[0])] = Message(self,
                                                 str(row[0]),
                                                 self.participants[str(row[1])],
                                                 self.conversations[str(row[2])])


class Conversation(object):

    def __init__(self, case, _id, service):
        self.case = case

        self._id = _id
        self.service = service
        self._participants = None

    @property
    def participants(self):
        if self._participants is None:
            self._participants = []
            for row in self.case.cursor.execute('SELECT participant_id FROM message_conversation_participants WHERE conversation_id = ?', (self._id, )):
                self._participants.append(self.case.participants[str(row[0])])
        return self._participants

    def __repr__(self):

        return "{} - {}".format(self._id, self.service)
        
        
class Message(object):

    def __init__(self, case, _id, sender, conversation):
        self.case = case
        
        self._id = _id
        self.conversation = conversation
        self.sender = sender

        self._attachments = None
        self._datetime = None
        self._text = None
        
    def __repr__(self):
        return "{} from {}".format(self._id, self.sender)

    @property
    def attachments(self):
        if self._attachments == None:
            self._attachments = []
            for row in self.case.cursor.execute('SELECT file_id, attachment_name, mime_type FROM message_attachments WHERE message_id = ?', (self._id, )):
                self._attachments.append(MessageAttachment(self, str(row[0]), row[1], row[2]))
        return self._attachments

    @property
    def datetime(self):
        if self._datetime == None:
            self.case.cursor.execute('SELECT time FROM messages WHERE id = ?', (self._id, ))
            self._datetime = self.case.cursor.fetchone()[0]
            self._datetime = datetime.datetime.strptime(self._datetime, "%Y-%m-%d %H:%M:%S")
        return self._datetime
    
    @property
    def text(self):
        if self._text == None:
            self.case.cursor.execute('SELECT text FROM messages WHERE id = ?', (self._id, ))
            self._text = self.case.cursor.fetchone()[0]
        return self._text
    
    @property
    def recipients(self):
        r = []
        for part in self.conversation.participants:
            if part != self.sender:
                r.append(part)
        return r

    def to_eml(self, path):
        html = "<html>\n<head>\n<meta charset='UTF-8'>\n</head>\n<body>\n"
        html += self.text
        html += "\n</body>\n</html>"
        
        msg = MIMEMultipart('mixed')
        msg['Subject'] = ""
        msg['From'] = str(self.sender)
        msg['To'] = ", ".join([str(x) for x in self.recipients])
        msg['Date'] = format_datetime(self.datetime)

        part = MIMEText(html, 'html', "utf-8")

        msg.attach(part)

        for attach in self.attachments:
            try:
                try:
                    p = MIMEBase(attach.mime_type.split("/")[0], attach.mime_type.split("/")[1])
                except IndexError:
                    # handle edge cases where mime type is unspecified
                    p = MIMEBase("application", "octet-stream")
                    print("Mime Type Unspecified", self._id)
                p.set_payload(attach.get_data()) 
  
                # encode into base64 
                encoders.encode_base64(p) 
   
                p.add_header('Content-Disposition', "attachment; filename=%s" % attach.name) 
  
                # attach the instance 'p' to instance 'msg' 
                msg.attach(p)
            except TypeError:
                # handle edge cases where attachment file is not found in file store
                print("Attachment not found", self._id
        
        with open(path, "w", encoding="utf8") as eml_file:
            gen = generator.Generator(eml_file)
            gen.flatten(msg)


            
            
    def to_html(self, path):
        html = "<html>\n<head>\n<meta charset='UTF-8'>\n</head>\n<body>\n"
        html += self.text
        html += "\n</body>\n</html>"

        with open(path, "w", encoding="utf8") as html_file:
            html_file.write(html)


class Participant(object):

    def __init__(self, case, _id, name, address):
        self.case = case
        
        self._id = _id
        self.name = name
        self.address = address

    def __repr__(self):
        return "{} <{}>".format(self.name, self.address)


class MessageAttachment(object):

    def __init__(self, case, _id, name, mime_type):
        self.case = case

        self._id = _id
        self.name = name
        self.mime_type = mime_type

    def get_data(self):
        conn = sqlite3.connect("index.db")
        cursor = conn.cursor()
        cursor.execute('SELECT storage_name FROM files WHERE id = ?', (self._id, ))
        storage_name = cursor.fetchone()[0]
        path = "FileData\\store\\{}\\{}".format(storage_name[0:2], storage_name)
        with open(path, "rb") as att_file:
            return att_file.read()
        

        
class CaseFile(object):

    def __init__(self, case, _id, name, mime_type):
        self.case = case

        self._id = _id
        

case = MobilyzeCase('UserDataIndex.sdb')


i = 1    
for id, message in case.messages.items():

    message.to_eml("eml2\\{} - {} - {}.eml".format(str(i).zfill(5), message._id.zfill(5), message.conversation._id.zfill(5)))

    i += 1

    
