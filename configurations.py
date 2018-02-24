# Twitter Authentication
consumer_key = 'N68ojyg0TQrSTxTZvURKyZ1o3'
consumer_secret = 'fSv1PO72uBJbPSkIiiBNAcLNASMuxoRLg5hsRh6OAD6LDNNif1'
access_token = '213560061-XKaREtskNRnH1SFt5lcQS6KaEBXJNxV1rpOnBm38'
access_token_secret = 'K77yciRInc5maybhPAlTVkWE7PZmKPh2UbKKEWGx7aI3m'

# Stream Listner
mention_list = ['@united'] 	# Twitter stream  listner @ list

# Databases
tweet_database_name = 'tweets.db'	# Database to store incoming tweets

# Tweet Filters
language = 'en'			# Language filter for tweets
min_tweet_length = 3	# Minimum Length of a tweet, to consider for clustering 

# Clusters
drop_limit = 50			# Minimum tweet count of a cluster to avoid dropping
max_cos_distance = 0.6	# Maximum cosine distance limit allowed to assign a tweet to a cluster

# CSR Model
no_features = 1048576	# Number of features to consider for Hash Vectorized Model

# Time Durations
reset_duration = 4                	# Time interval to reset the database (in hours)
recent_duration = 30				# Time interval for recent tweet clustering (in minutes)
tweet_rate_limit = 1				# Time interval for calculating incoming tweet rate for each clusters (in minutes)
date_format = '%Y-%m-%d %H:%M:%S'	# Date formatting

# Jaccard Similarity
jaccard_threshold = 0.55	# Threshold value to consider Jaccard Similarity of incoming tweets

# Summerization
no_words = 25		# Maximum number of words to be in the cluster summary
no_sentences = 20 	# Miniumum number of sentences required to perform summarization (libary minimum is 10 sentences)

