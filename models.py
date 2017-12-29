from app import db
from sqlalchemy.dialects.postgresql import JSON


class Entries(db.Model):
    __tablename__ = 'entries'
    
    id = db.Column(db.Integer, primary_key=True)
    link = db.Column(db.String(), unique=True)
    title = db.Column(db.String())
    authors = db.Column(db.String())
    journal = db.Column(db.String())
    volume = db.Column(db.String())
    published = db.Column(db.String()) # Date?
    content = db.Column(db.String())

    
    def __init__(self, link, title, authors, journal, volume, published, content):
        self.link = link
        self.title = title
        self.authors = authors
        self.journal = journal
        self.volume = volume
        self.published = published
        self.content = content
    
    def __repr__(self):
        return '<id {}>'.format(self.id)
