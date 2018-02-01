# encoding=utf8
import tweepy as tp
import sqlite3
import langid
from nltk import word_tokenize
from datasketch import MinHashLSHForest, MinHash
from datetime import datetime as dt
from datetime import timedelta
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import HashingVectorizer
import numpy as np
import sys
reload(sys)
sys.setdefaultencoding('utf8')

# Twitter authentication
consumer_key = 'N68ojyg0TQrSTxTZvURKyZ1o3'
consumer_secret = 'fSv1PO72uBJbPSkIiiBNAcLNASMuxoRLg5hsRh6OAD6LDNNif1'
access_token = '213560061-XKaREtskNRnH1SFt5lcQS6KaEBXJNxV1rpOnBm38'
access_token_secret = 'K77yciRInc5maybhPAlTVkWE7PZmKPh2UbKKEWGx7aI3m'

auth = tp.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tp.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

# DB Connection 
connection = sqlite3.connect('tweets.db')
c = connection.cursor()

# MinHash and MinHash LSH Forest
m1 = MinHash(num_perm=128)
m2 = MinHash(num_perm=128)
forest = MinHashLSHForest(num_perm=128)

# Clustering
start_time = dt.utcnow()
vectorizer = HashingVectorizer(stop_words='english')
km_model = None
cluster = ''
cluster_points = None

# Create tweet table
def create_table():
	c.execute("""CREATE TABLE IF NOT EXISTS tweets
		(tweet_id TEXT PRIMARY KEY,
		 preprocessed_text TEXT,
		 full_text TEXT,
		 created_at TEXT,
		 cluster TEXT,
		 tweet TEXT)""")
	connection.commit()

def clean_table():	
	c.execute(""" DELETE FROM tweets
		WHERE created_at < '%s' """ % (dt.utcnow() - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S'))
	connection.commit()

def load_forest():
	c.execute(" SELECT tweet_id, preprocessed_text FROM tweets ")
	rows = c.fetchall()

	for row in rows:
		for t1 in word_tokenize(row[1]):
			m1.update(t1.encode('utf8'))

		forest.add(row[0], m1)
	forest.index()

def check_duration():
	global start_time
	if ((dt.utcnow() - start_time).total_seconds()/60) > 1:
		start_time = dt.utcnow()
		calculate_clusters()

def calculate_clusters():
	global cluster_points
	global km_model

	if cluster_points != None:

		sorted_clust_points = []
		counter = -1
		for key, value in sorted(cluster_points.iteritems(), key=lambda (k,v):(v,k), reverse= True):			
			sorted_clust_points.append(key)
			counter = counter + 1

			if counter >= 40 and value < 10:
				c.execute(" DELETE FROM tweets WHERE cluster = '%s' " % key)
		connection.commit()
		load_forest()

	c.execute(""" SELECT tweet_id, preprocessed_text FROM tweets 		
		WHERE created_at > '%s' """ % (dt.utcnow() - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S'))
	rows = c.fetchall()

	if len(rows) > 50:
		if km_model == None:
			km_model = KMeans(n_clusters=50)

		tweets = []
		for row in rows:
			tweets.append(row[1])

		hash_model = vectorizer.fit_transform(tweets)
		km_model.fit(hash_model)

		for idx, row  in enumerate(rows):
			c.execute(" UPDATE tweets SET cluster = '%s' WHERE tweet_id = '%s' " % (km_model.labels_[idx], row[0]))
		connection.commit()

		cluster_points = {i: len(np.where(km_model.labels_ == i)[0]) for i in range(km_model.n_clusters)}


def get_extended_tweets(status):
	extended_tweet_list = []

	if status.id_str not in forest:
		if 'RT @' in status.text:
			pass
			#extended_tweet_list.append(api.get_status(id=(status.retweeted_status).id, tweet_mode = 'extended')) if hasattr(status, 'retweeted_status') and ((status.retweeted_status).id_str not in forest) else None
		elif status.is_quote_status == True:
			#extended_tweet_list.append(api.get_status(id=(status.quoted_status).get('id'), tweet_mode = 'extended')) if hasattr(status, 'quoted_status') and ((status.quoted_status).get('id_str') not in forest) else None
			extended_tweet_list.append(api.get_status(id=status.id, tweet_mode = 'extended'))
		else:
			extended_tweet_list.append(api.get_status(id=status.id, tweet_mode = 'extended'))

	return extended_tweet_list


def preprocess_tweet(ex_tweet):

	if ex_tweet != None:
		ful_txt = ex_tweet.full_text

		symbols = ex_tweet.entities.get('symbols')
		user_mentions = ex_tweet.entities.get('user_mentions')
		hashtags = ex_tweet.entities.get('hashtags')
		urls = ex_tweet.entities.get('urls')
		media = ex_tweet.entities.get('media')

		if (symbols != None) and (symbols != []):
			for s in symbols:
				ful_txt = ful_txt.replace("$" + s.get('text'), "")
		if (user_mentions != None) and (user_mentions != []):
			for u in user_mentions:
				mention = u.get('screen_name')
				ful_txt = ful_txt.replace("@" + mention, "") if mention != 'united' else ful_txt.replace("@united", "united")
		if (hashtags != None) and (hashtags != []):
			ful_txt = ful_txt.replace("#", "")
		if (urls != None) and (urls != []):
			for u in urls:
				ful_txt = ful_txt.replace(u.get('url'), "")
		if (media != None) and (media != []):
			for m in media:
				ful_txt = ful_txt.replace(m.get('url'), "")

		ful_txt = ful_txt.replace("&amp;", "&").replace(":", "").decode('unicode_escape').encode('ascii','ignore')

		if (len(ful_txt.split()) > 3):
			return ex_tweet, ful_txt
		else:
			return None, None
	else:
		return None, None


def store_tweet(tweet, text):
	global cluster
	global cluster_points

	if (tweet != None) and (text != None):	
		cluster = (km_model.predict(vectorizer.fit_transform([text])))[0] if km_model != None else ''
		tokenized_text = word_tokenize(text)

		for t1 in tokenized_text:
			m1.update(t1.encode('utf8'))

		result = forest.query(m1, 1)

		if result != []:			
			c.execute(" SELECT preprocessed_text FROM tweets WHERE tweet_id = '%s' " % result[0])			
			row = c.fetchone()

			if row != None:
				for t2 in word_tokenize(row[0]):
					m2.update(t2.encode('utf8'))

				if m1.jaccard(m2) < 0.55:
					forest.add(tweet.id_str, m1)
					Tweet(tweet.id_str,
				  		text,
						tweet.full_text,
						tweet.created_at,
						str(cluster),
						str(tweet._json)).insert()
					if cluster != '':
						cluster_points[cluster] = (cluster_points[cluster] + 1) 
				else:
					pass	
		else:
			forest.add(tweet.id_str, m1)
			Tweet(tweet.id_str,
			  	text,
				tweet.full_text,
				tweet.created_at,
				str(cluster),
				str(tweet._json)).insert()			
			if cluster != '':
				cluster_points[cluster] = (cluster_points[cluster] + 1)
		forest.index()


# Define a Preprocessed Tweet
class Tweet():
    # Data on the tweet
    def __init__(self, tweet_id, preprocessed_text, full_text, created_at, cluster, tweet):
        self.tweet_id = tweet_id
        self.preprocessed_text = preprocessed_text
        self.full_text = full_text
        self.created_at = created_at
        self.cluster = cluster
        self.tweet = tweet

    # Insert tweet to DB
    def insert(self):
        c.execute(""" INSERT INTO tweets (tweet_id, preprocessed_text, full_text, created_at, cluster, tweet) 
        	VALUES (?, ?, ?, ?, ?, ?) """, (self.tweet_id, self.preprocessed_text, self.full_text, self.created_at, self.cluster, self.tweet))
        connection.commit()


# Stream Listener class
class RozieStreamListener(tp.StreamListener):

	def on_status(self, status):
		try:
			check_duration()
			lang = langid.classify(status.text)[0]

			if lang == 'en':
				tweet_list = get_extended_tweets(status)				

				for tweet in tweet_list:
					ex_tweet, ful_txt = preprocess_tweet(tweet)
					store_tweet(ex_tweet, ful_txt)
				print('Sucess')
			return True
        
		except Exception as e:
			print(e)
			pass		        
 
	def on_error(self, status_code):
		print('Got an error with status code: ' + str(status_code))
		if (status_code == 420):
			return False
		else:
			return True # To continue listening
 
 	def on_timeout(self):
		print('Timeout...')
		return True # To continue listening

def main():
	create_table()
	clean_table()
	load_forest()
	print('Loaded MinHash Forest')

	listener = RozieStreamListener()
	stream = tp.Stream(auth = auth, listener = listener)
	stream.filter(track=['@united', '#united', '#trump'])

	print("DB Connection Close...")
	connection.close()

if __name__ == '__main__':
	main()