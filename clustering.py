import configurations as conf
import tweepy as tp
import sqlite3
import langid
import html
import preprocessor as p
from nltk import word_tokenize
from datasketch import MinHashLSHForest, MinHash
from datetime import datetime as dt
from datetime import timedelta
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_distances
from scipy.sparse import random
from gensim.summarization.summarizer import summarize
from gensim.summarization import keywords
import numpy as np

auth = tp.OAuthHandler(conf.consumer_key, conf.consumer_secret)
auth.set_access_token(conf.access_token, conf.access_token_secret)
api = tp.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

# Database Connection 
connection = sqlite3.connect(conf.tweet_database_name)
c = connection.cursor()

# MinHash and MinHash LSH Forest
m1 = MinHash(num_perm=128)
m2 = MinHash(num_perm=128)
forest = None

# Timers
reset_start_time = dt.utcnow()
drop_start_time = dt.utcnow()
tweet_rate_start = dt.utcnow()

# Clustering
vectorizer = HashingVectorizer(stop_words='english')
centroids = {}
hash_vec_sum = {}
cluster_point_count = {}
cluster_point_count_old = cluster_point_count.copy()


# Create Tables : clusters, recent_tweets and history_tweets
def create_tables():
	c.execute("""CREATE TABLE IF NOT EXISTS clusters
		(cluster_id TEXT PRIMARY KEY,
		 summary TEXT,
		 tweet_count INTEGER,
		 tweet_rate INTEGER)""")

	c.execute("""CREATE TABLE IF NOT EXISTS recent_tweets
		(tweet_id TEXT PRIMARY KEY,
		 preprocessed_text TEXT,
		 full_text TEXT,
		 created_at TEXT,
		 cluster_id TEXT,
		 assignment_time TEXT,
		 tweet TEXT,
		 FOREIGN KEY(cluster_id) REFERENCES clusters(cluster_id))""")

	c.execute("""CREATE TABLE IF NOT EXISTS history_tweets
		(tweet_id TEXT PRIMARY KEY,
		 preprocessed_text TEXT,
		 full_text TEXT,
		 created_at TEXT,
		 cluster_id TEXT,
		 assignment_time TEXT,
		 tweet TEXT,
		 FOREIGN KEY(cluster_id) REFERENCES clusters(cluster_id))""")
	connection.commit()


# Clean Tables : clusters, recent_tweets and history_tweets
def clean_tables():
	before = (dt.utcnow() - timedelta(minutes=conf.recent_duration)).strftime(conf.date_format)
	
	c.execute(""" INSERT OR REPLACE INTO history_tweets (tweet_id, preprocessed_text, full_text, created_at, cluster_id, assignment_time, tweet)
		SELECT tweet_id, preprocessed_text, full_text, created_at, cluster_id, assignment_time, tweet FROM recent_tweets WHERE assignment_time < '%s' """ % before)
	c.execute(" DELETE FROM recent_tweets WHERE assignment_time < '%s' " % before)
	c.execute(" DELETE FROM clusters ")
	connection.commit()


# Load MinHashLSHForest
def load_forest():
	global forest
	forest = MinHashLSHForest(num_perm=128)

	c.execute(" SELECT tweet_id, preprocessed_text FROM recent_tweets ")
	rows = c.fetchall()

	for row in rows:
		for t1 in word_tokenize(row[1]):
			m1.update(t1.encode('utf8'))

		forest.add(row[0], m1)
	forest.index()
	return rows


# Recalculate Clusters
def recalculate_clusters(rows):
	update_recs = []

	for row in rows:
		cluster, assignment_time = calculate_cluster(row[1])

		update_recs.append((cluster, assignment_time, row[0]))
	
	if len(update_recs) > 0:
		c.executemany(" UPDATE recent_tweets SET cluster_id = ?, assignment_time = ?  WHERE tweet_id = ? " , update_recs)
		connection.commit()


# Check Reset Time
def check_reset_time():
	global reset_start_time
	global centroids
	global hash_vec_sum
	global cluster_point_count
	global cluster_point_count_old

	if ((dt.utcnow() - reset_start_time).total_seconds()/3600) > conf.reset_duration:

		prev_time = reset_start_time.strftime(conf.date_format)
		reset_start_time = dt.utcnow()

		print("Resetting database")
		c.execute(""" INSERT OR REPLACE INTO history_tweets (tweet_id, preprocessed_text, full_text, created_at, cluster_id, assignment_time, tweet)
					SELECT tweet_id, preprocessed_text, full_text, created_at, cluster_id, assignment_time, tweet FROM recent_tweets """)
		c.execute(" DELETE FROM recent_tweets ")
		c.execute(" DELETE FROM clusters ")		
		connection.commit()

		centroids = {}
		hash_vec_sum = {}
		cluster_point_count = {}
		cluster_point_count_old = cluster_point_count.copy()

		tmp = load_forest()


# Check Drop Time and Drop Inactive Clusters
def check_drop_time():
	global drop_start_time
	global hash_vec_sum
	global cluster_point_count
	global cluster_point_count_old

	if ((dt.utcnow() - drop_start_time).total_seconds()/60) > conf.recent_duration:

		prev_time = drop_start_time.strftime(conf.date_format)
		drop_start_time = dt.utcnow()

		drop_list = []
		limit = len(centroids) + 1

		for i in range(1,limit):
			c.execute(" SELECT * FROM recent_tweets WHERE cluster_id = '%s' and assignment_time > '%s' " % (i, prev_time))
			rows = c.fetchall()

			if(len(rows) < conf.drop_limit):
				drop_list.append(str(i))
				hash_vec_sum[i] = None
				cluster_point_count[i] = 0
				cluster_point_count_old[i] = 0

		if len(drop_list) > 0:
			print("Dropping Custers : %s " % drop_list)

			c.executemany(""" INSERT OR REPLACE INTO history_tweets (tweet_id, preprocessed_text, full_text, created_at, cluster_id, assignment_time, tweet)
				SELECT tweet_id, preprocessed_text, full_text, created_at, cluster_id, assignment_time, tweet FROM recent_tweets WHERE cluster_id = ? """, drop_list)
			c.executemany(" DELETE FROM recent_tweets WHERE cluster_id = ? ",  drop_list)
			c.executemany(" UPDATE clusters SET summary = '', tweet_count = 0, tweet_rate = 0 WHERE cluster_id = ? ",  drop_list)
			connection.commit()
		
			tmp = load_forest()


# Cluster Tweet Rate
def calculate_tweet_rate():
	global tweet_rate_start
	global cluster_point_count
	global cluster_point_count_old
	
	cluster_recs = []

	if ((dt.utcnow() - tweet_rate_start).total_seconds()/60) > conf.tweet_rate_limit:
		tweet_rate_start = dt.utcnow()

		print("Calculating Cluster Tweet Rate")
		limit = len(centroids) + 1

		for i in range(1,limit):
			rate = cluster_point_count[i] - cluster_point_count_old[i]

			cluster_recs.append((cluster_point_count[i], rate, str(i)))

		cluster_point_count_old = cluster_point_count.copy()

		c.executemany(" UPDATE clusters SET tweet_count = ?, tweet_rate = ? WHERE cluster_id = ? ", cluster_recs)
		connection.commit()


# Cluster Summary
def calculate_summary(cluster):
	c.execute(" SELECT preprocessed_text FROM recent_tweets WHERE cluster_id = '%s' " % cluster)
	rows = c.fetchall()
	text = ""
	summary = ""

	for row in rows:
		r = str(row[0])

		if (r[-1] == "."):		
			text += r
		else:
			text += r + "."

	if (len(rows) > conf.no_sentences):
		summary = summarize(text, word_count = conf.no_words)

	c.execute(" UPDATE clusters SET summary = ? WHERE cluster_id = ? ", (summary, cluster))
	connection.commit()


# Calculate Cluster
def calculate_cluster(tweet_text):
	global centroids
	global hash_vec_sum
	global cluster_point_count
	global cluster_point_count_old

	tweet_model = vectorizer.fit_transform([tweet_text])
	cos_distance = {}
	cluster = None

	if(len(centroids) > 0):

		for k, v in centroids.items():		
			cos_distance[k] = cosine_distances(tweet_model, v).item(0,0)

		cluster, distance = min(cos_distance.items(), key=lambda x: x[1])

		if(distance < conf.max_cos_distance):
			hash_vec_sum[cluster] = (hash_vec_sum[cluster] + tweet_model)
			cluster_point_count[cluster] = cluster_point_count[cluster] + 1
			c.execute(" UPDATE clusters SET tweet_count = ? WHERE cluster_id = ? ", (cluster_point_count[cluster], cluster))
		else:
			cluster = len(centroids) + 1
			hash_vec_sum[cluster] =  tweet_model
			cluster_point_count[cluster] = 1
			cluster_point_count_old[cluster] = 0
			c.execute(" INSERT OR REPLACE INTO clusters (cluster_id, summary, tweet_count, tweet_rate) VALUES (?, ?, ?, ?) ", (cluster, '', cluster_point_count[cluster], 1))
	else:
		cluster = 1
		hash_vec_sum[cluster] =  tweet_model
		cluster_point_count[cluster] = 1
		cluster_point_count_old[cluster] = 0
		c.execute(" INSERT OR REPLACE INTO clusters (cluster_id, summary, tweet_count, tweet_rate) VALUES (?, ?, ?, ?) ", (cluster, '', cluster_point_count[cluster], 1))
	
	connection.commit()

	centroids[cluster]= hash_vec_sum[cluster]/cluster_point_count[cluster]
	return cluster, dt.utcnow().strftime(conf.date_format)


# Get Extended Tweets
def get_extended_tweets(status):
	extended_tweet_list = []

	if 'RT @' in status.text:
		extended_tweet_list.append(api.get_status(id=(status.retweeted_status).id, tweet_mode = 'extended')) if hasattr(status, 'retweeted_status') and ((status.retweeted_status).id_str not in forest) and (langid.classify((status.retweeted_status).text)[0] == 'en') else None
	elif status.is_quote_status == True:
		extended_tweet_list.append(api.get_status(id=(status.quoted_status).get('id'), tweet_mode = 'extended')) if hasattr(status, 'quoted_status') and ((status.quoted_status).get('id_str') not in forest) and (langid.classify((status.quoted_status).get('text'))[0] == 'en') else None
		extended_tweet_list.append(api.get_status(id=status.id, tweet_mode = 'extended'))
	else:
		extended_tweet_list.append(api.get_status(id=status.id, tweet_mode = 'extended'))

	return extended_tweet_list


# Preprocess Extended Tweet
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

		ful_txt = p.clean(html.unescape(ful_txt))

		if (len(ful_txt.split()) > conf.min_tweet_length):
			return ex_tweet, ful_txt
		else:
			return None, None
	else:
		return None, None


# Storing Preprocessed Tweet
def store_tweet(tweet, text):

	if (tweet != None) and (text != None):		
		tokenized_text = word_tokenize(text)
		cluster = ''

		for t1 in tokenized_text:
			m1.update(t1.encode('utf8'))

		result = forest.query(m1, 1)

		if result != []:			
			c.execute(" SELECT preprocessed_text FROM recent_tweets WHERE tweet_id = '%s' " % result[0])			
			row = c.fetchone()

			if row != None:
				for t2 in word_tokenize(row[0]):
					m2.update(t2.encode('utf8'))

				if m1.jaccard(m2) < conf.jaccard_threshold:

					forest.add(tweet.id_str, m1)
					cluster, assignment_time = calculate_cluster(text)					

					Tweet(tweet.id_str,
				  		text,
						tweet.full_text,
						tweet.created_at,
						str(cluster),
						assignment_time,
						str(tweet._json)).insert()
				else:
					pass	
		else:
			forest.add(tweet.id_str, m1)
			cluster, assignment_time = calculate_cluster(text)

			Tweet(tweet.id_str,
			  	text,
				tweet.full_text,
				tweet.created_at,
				str(cluster),
				assignment_time,
				str(tweet._json)).insert()
		forest.index()
		
		if cluster != '':
			calculate_summary(str(cluster))


# Define a Preprocessed Tweet
class Tweet():

    # Data on the tweet
    def __init__(self, tweet_id, preprocessed_text, full_text, created_at, cluster_id, assignment_time, tweet):
        self.tweet_id = tweet_id
        self.preprocessed_text = preprocessed_text
        self.full_text = full_text
        self.created_at = created_at
        self.cluster_id = cluster_id
        self.assignment_time = assignment_time
        self.tweet = tweet

    # Insert Preprocessed Tweet to recent_tweets table
    def insert(self):
        c.execute(""" INSERT INTO recent_tweets (tweet_id, preprocessed_text, full_text, created_at, cluster_id, assignment_time, tweet) 
        	VALUES (?, ?, ?, ?, ?, ?, ?) """, (self.tweet_id, self.preprocessed_text, self.full_text, self.created_at, self.cluster_id, self.assignment_time, self.tweet))
        connection.commit()


# Stream Listener class
class RozieStreamListener(tp.StreamListener):

	def on_status(self, status):
		try:
			check_reset_time()
			check_drop_time()
			calculate_tweet_rate()

			if status.id_str not in forest:
				lang = langid.classify(status.text)[0]

				if lang == conf.language:
					tweet_list = get_extended_tweets(status)

					for tweet in tweet_list:
						ex_tweet, ful_txt = preprocess_tweet(tweet)
						store_tweet(ex_tweet, ful_txt)
					print('Tweets Processed : %s' % len(tweet_list))
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
	create_tables()
	clean_tables()
	recalculate_clusters(load_forest())	
	print('Initialization Complete')

	listener = RozieStreamListener()
	stream = tp.Stream(auth = auth, listener = listener)
	stream.filter(track=conf.mention_list)

	print('Closing Database Connection...')
	connection.close()

if __name__ == '__main__':
	main()