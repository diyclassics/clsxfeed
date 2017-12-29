from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import os
import sys
import feedparser
#import json
import urllib.request, urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re

from sqlalchemy import exc

from pprint import pprint

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from models import Entries

# Constants
ENTRIES_LIMIT = 50

# Variables
errors = []

RSS_FEEDS = {
    "Brill": {
        'Mnemosyne': 'http://booksandjournals.brillonline.com/rss/content/journals/1568525x/latestarticles?fmt=rss',
    },
    #"DeGruyter": {
    #        "Trends in Classics": "view-source:https://www.degruyter.com/dg/rssalerts/$002fj$002ftcs/Trends$0020in$0020Classics/toc/NaN",   
    #},
    "DLOP": {
      'Greek, Roman, and Byzantine Studies': 'http://grbs.library.duke.edu/gateway/plugin/WebFeedGatewayPlugin/rss',  
    },
    "HAMLA": {
        'Dictynna': "http://journals.openedition.org/dictynna/backend?format=rssdocuments"
    },
    "JHU": 
        {
            'American Journal of Philology': 'https://muse.jhu.edu/feeds/latest_articles?jid=6',
            'Classical World': 'https://muse.jhu.edu/feeds/latest_articles?jid=317',
            'Illinois Classical Studies': 'https://muse.jhu.edu/feeds/latest_articles?jid=653',
            'Mouseion: Journal of the Classical Association of Canada': 'https://muse.jhu.edu/feeds/latest_articles?jid=366',
            'Syllecta Classica': 'https://muse.jhu.edu/feeds/latest_articles?jid=534',
            'Transactions of the American Philological Association': 'https://muse.jhu.edu/feeds/latest_articles?jid=12',
            },
    "Chicago":
        {
            'Classical Philology': 'http://www.journals.uchicago.edu/action/showFeed?type=etoc&feed=rss&jc=cp',
            },
}

def _build_authors(authors_list):
    return ", ".join([item['name'] for item in authors_list])


def get_date_published(entry):
    if entry.updated_parsed:
        entry.published_parsed = entry.updated_parsed
    return entry.published_parsed

publishers = []        
journals = []
full_entries = []
current_entries = []
articles = []

# Add error trapping in case feed URLs are unavailable

for publisher in RSS_FEEDS.keys():
    publishers.append(publisher)
    for journal, url in RSS_FEEDS[publisher].items():
        entries = []
        journals.append(journal)
        entries = [entry for entry in feedparser.parse(url).entries]
        for entry in entries:
            date_published = get_date_published(entry)
            link = entry.link
            link_ = Entries.query.filter_by(link=link).first()
            if not link_:
                current_entries.append((publisher, journal, date_published, entry))
            full_entries.append((publisher, journal, date_published, entry))

            
class Article(object):
    def __init__(self, entry):
        self.entry = entry
        self.url = entry.link


class BrillArticle(Article):
    def __init__(self, entry):
        Article.__init__(self, entry)
        
        with urllib.request.urlopen(self.url) as response:
            self.soup = BeautifulSoup(response.read(), 'lxml')
        
        if 'authors' in self.entry.keys():
            self.entry.authors = ", ".join([item['name'] for item in self.entry.authors])
        journal = self.soup.find("a", {"class" : "detailtitle2"})
        if journal:
            self.entry.journal = journal.get('title')
        self.entry.published = time.strftime('%Y-%m-%d', self.entry.updated_parsed)
        self.entry.summary = re.sub(r'<div><strong> Source: </strong>Page Count \d+</div>','',self.entry.summary)
        if len(self.entry.summary) == 0:
            self.entry.content = {'value': self.entry.summary}
        else:
            self.entry.content = {'value': '[No summary available.]'}
        #pprint(self.entry)
        volume = self.soup.find("meta", {"name" : "citation_year"})
        if volume:
            self.entry.volume = volume.get('content')
        else:
            self.entry.volume = None
        
class ChicagoArticle(Article):
    def __init__(self, entry):
        Article.__init__(self, entry)
        if 'authors' in self.entry.keys():
            self.entry.authors = ", ".join([item['name'] for item in self.entry.authors])
        else:
            self.entry.authors = None
        self.entry.journal = self.entry.dc_source
        self.entry.volume = self.entry.prism_volume
        self.entry.published_parsed = self.entry.updated_parsed
        self.entry.published = time.strftime('%Y-%m-%d', self.entry.updated_parsed)
        self.entry.content = {'value': "[<i>Classical Philology</i> does not provide summaries/abstracts/etc. in the RSS feed for articles.]"}
      

    
class DeGruyterArticles(Article):
    def __init__(self, entry):
        Article.__init__(self, entry)
        #print(self.entry)
        
#        if 'authors' in self.entry.keys():
#            self.entry.authors = ", ".join([item['name'] for item in self.entry.authors])
#        self.entry.journal = self.entry.rights[re.search(r'\d\d\d\d',self.entry.rights).end()+1:]
#        
#        self.entry.volume = self.entry.prism_volume
#        self.entry.published_parsed = self.entry.updated_parsed
#        self.entry.published = time.strftime('%Y-%m-%d', self.entry.updated_parsed)
#        self.entry.content = {'value': self.entry.summary}
    
    
class DLOPArticle(Article):
    def __init__(self, entry):
        Article.__init__(self, entry)
        
        if 'authors' in self.entry.keys():
            self.entry.authors = ", ".join([item['name'] for item in self.entry.authors])
        self.entry.journal = self.entry.rights[re.search(r'\d\d\d\d',self.entry.rights).end()+1:]
        
        self.entry.volume = self.entry.prism_volume
        self.entry.published_parsed = self.entry.updated_parsed
        self.entry.published = time.strftime('%Y-%m-%d', self.entry.updated_parsed)
        self.entry.content = {'value': self.entry.summary}


class HAMLAArticle(Article):
    def __init__(self, entry):
        Article.__init__(self, entry)
        #pprint(self.entry)
        
        with urllib.request.urlopen(self.url) as response:
            self.soup = BeautifulSoup(response.read(), 'lxml')
        
        if 'authors' in self.entry.keys():
            self.entry.authors = _build_authors(self.entry.authors)
        self.entry.journal = self.entry.link[self.entry.link.find('.org')+5:self.entry.link.rfind('/')].title()
        
        #self.entry.volume = self.entry.prism_volume
        volume = self.soup.find("meta", {"name" : "citation_issue"})
        if volume:
            self.entry.volume = volume.get('content')
        
        self.entry.published_parsed = self.entry.updated_parsed
        self.entry.published = time.strftime('%Y-%m-%d', self.entry.updated_parsed)
        self.entry.content = {'value': self.entry.summary}
        
        
class JHUArticle(Article):
    def __init__(self, entry):
        Article.__init__(self, entry)
        
        with urllib.request.urlopen(self.url) as response:
            self.soup = BeautifulSoup(response.read(), 'lxml')
        
        authors = self.soup.findAll("meta", {"name" : "citation_author"})
        if authors:
            authors = [author.get('content') for author in authors]
            self.entry.authors = ", ".join(authors)
        else:
            self.entry.authors = None
            
        journal = self.soup.find("meta", {"name" : "citation_journal_title"})
        if journal:
            self.entry.journal = journal.get('content')
        
        volume = self.soup.find("meta", {"name" : "citation_volume"})
        if volume:
            self.entry.volume = volume.get('content')
            #print(self.entry.journal)
            if self.entry.journal == "Mouseion: Journal of the Classical Association of Canada":
                self.entry.volume = self.entry.volume[-2:]
            
            self.entry.content = {'value': self.entry.summary_detail.value}


# Add error trapping in case URLs for scraping can't be opened

for publisher, _, _, entry in current_entries:
        if publisher == 'Brill':
            #print('*************YES***************')
            article = BrillArticle(entry)
        elif publisher == "Chicago":
            article = ChicagoArticle(entry)
        #elif publisher == "DeGruyter":
        #    article = DeGruyterArticle(entry)
        elif publisher == "DLOP":
            article = DLOPArticle(entry)
        elif publisher == "HAMLA":
            article = HAMLAArticle(entry)
        elif publisher == "JHU":
            article = JHUArticle(entry)
        else:
            pass
        articles.append(article.entry)

        
for article in articles:
    print(article.link, article.title, article.authors, article.journal, article.volume, article.published)
    entry = Entries(
        link = article.link,
        title = article.title,
        authors = article.authors,
        journal = article.journal,
        volume = article.volume,
        published = article.published,
        content = article.content['value'] 
        )
    link_ = Entries.query.filter_by(link=article.link).first()
    if link_:
        print('Already in database')
    else:
        try:
            db.session.add(entry)
            db.session.commit()
            print('Added entry: %s' % article.link)
        except exc.IntegrityError as e:
            db.session().rollback()
            print("Unexpected error:", sys.exc_info()[0])
            print("Unable to add item to database: %s." % article.link)
        #print(errors)
        
        
@app.route('/')
def index():
    
    articles_sorted = Entries.query.all()
    articles_sorted = sorted(
        articles_sorted,
        key=lambda x: x.published,
        reverse=True
    )[:ENTRIES_LIMIT]
    
    return render_template(
        'index.html',
        entries=articles_sorted, 
        info={
            'currtime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'journals': sorted(journals),
            'limit': ENTRIES_LIMIT,
        }
    )


if __name__ == '__main__':
    app.run()
