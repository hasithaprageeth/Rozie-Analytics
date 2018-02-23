from django.shortcuts import render
import os, sqlite3
from datetime import datetime as dt
from datetime import timedelta
import random
from gensim.summarization.summarizer import summarize

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

##########################################################################################################
# Recent Analytics
def recentAnalytics(request):
	clusters , records = getRecentClusters()
	context = {'clusters' : clusters, 'records' : records, 'recent' : 'active'}
	template_name = 'analytics/analytics.html'

	return render(request, template_name, context)

def recentAnalyticsDetail(request, cluster):
	cloud, summary, records = getRecentClusterDetail(cluster)
	context = {'cloud': cloud, 'summary' : summary, 'records' : records, 'recent' : 'active', 'clust' : cluster}
	template_name = 'analytics/analytics-detail.html'
	return render(request, template_name, context)


##########################################################################################################
# Full Analytics
def fullAnalytics(request):
	clusters , records = getFullClusters()
	context = {'clusters' : clusters, 'records' : records, 'full' : 'active'}
	template_name = 'analytics/analytics.html'
	return render(request, template_name, context)

def fullAnalyticsDetail(request, cluster):
	cloud, summary, records = getFullClusterDetail(cluster)
	context = {'cloud': cloud, 'summary' : summary,'records' : records, 'full' : 'active', 'clust' : cluster}
	template_name = 'analytics/analytics-detail.html'
	return render(request, template_name, context)


##########################################################################################################
# Periodic Updates
def recentAnalyticsUpdate(request):
	clusters , records = getRecentClusters()
	context = {'clusters' : clusters, 'records' : records, 'recent' : 'active'}
	template_name = 'analytics/analytics-update.html'
	return render(request, template_name, context)

def fullAnalyticsUpdate(request):
	clusters , records = getFullClusters()
	context = {'clusters' : clusters, 'records' : records, 'recent' : 'active'}
	template_name = 'analytics/analytics-update.html'
	return render(request, template_name, context)

def recentAnalyticsDetailUpdate(request, cluster):
	cloud, summary, records = getRecentClusterDetail(cluster)
	context = {'cloud': cloud, 'summary' : summary, 'records' : records, 'recent' : 'active', 'clust' : cluster}
	template_name = 'analytics/analytics-detail-update.html'
	return render(request, template_name, context)

def fullAnalyticsDetailUpdate(request, cluster):
	cloud, summary, records = getFullClusterDetail(cluster)
	context = {'cloud': cloud, 'summary' : summary,'records' : records, 'full' : 'active', 'clust' : cluster}
	template_name = 'analytics/analytics-detail-update.html'
	return render(request, template_name, context)


##########################################################################################################
# DB Connection
def getDBConnection():
	connection = sqlite3.connect(os.path.join(BASE_DIR,'tweets.db'))
	return connection.cursor()


##########################################################################################################
# Recent Analytics Methods
def getRecentClusters():
	c = getDBConnection()

	c.execute(""" SELECT cluster_id, COUNT(tweet_id) as points FROM recent_tweets
		 WHERE assignment_time > '%s' GROUP BY cluster_id ORDER BY points DESC LIMIT 10 """ % (dt.utcnow() - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S'))
	rows1 = c.fetchall()
	r1 = []

	for r in rows1:
		if (r[0] != ''):
			r1.append({'cluster_id': r[0], 'points': r[1]})

	c.execute(" SELECT * FROM clusters WHERE cluster_id != '' ORDER BY tweet_rate DESC ")
	rows2 = c.fetchall()
	r2 = []

	for r in rows2:
		r2.append({'cluster_id': r[0], 'summary': r[1], 'tweet_rate': r[2]})

	return r1, r2

def getRecentClusterDetail(cluster):
	c = getDBConnection()

	c.execute(" SELECT summary FROM clusters WHERE cluster_id = '%s' " % cluster)
	r2 = c.fetchall()
	r2 = r2[0][0]

	c.execute(" SELECT * FROM recent_tweets WHERE cluster_id = '%s' AND  assignment_time > '%s' " % (cluster, (dt.utcnow() - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')))
	rows3 = c.fetchall()
	r1 = []
	r3 = []

	for r in rows3:
		r1 = r1 + [t1 for t1 in r[1].split()]
		r3.append({'tweet_id': r[0], 'preprocessed_text': r[1], 'full_text': r[2], 'created_at': r[3], 'cluster_id' : r[4], 'assignment_time': r[5]})

	random.shuffle(r1)
	r1 = r1[:1000]

	return r1, r2, r3


##########################################################################################################
# Full Analytics Methods
def getFullClusters():
	c = getDBConnection()

	c.execute(" SELECT cluster_id, COUNT(tweet_id) as points FROM recent_tweets GROUP BY cluster_id ORDER BY points DESC LIMIT 10 ")
	rows1 = c.fetchall()
	r1 = []

	for r in rows1:
		if (r[0] != ''):
			r1.append({'cluster_id': r[0], 'points': r[1]})

	c.execute(" SELECT * FROM clusters WHERE cluster_id != '' ORDER BY tweet_rate DESC ")
	rows2 = c.fetchall()
	r2 = []

	for r in rows2:
		r2.append({'cluster_id': r[0], 'summary': r[1], 'tweet_rate': r[2]})

	return r1, r2

def getFullClusterDetail(cluster):
	c = getDBConnection()

	c.execute(" SELECT * FROM recent_tweets WHERE cluster_id = '%s' " % cluster)
	rows1 = c.fetchall()
	r1 = []
	r2 = ""
	r3 = []

	for r in rows1:
		r1 += r[1].split()

		if (r[-1] == "."):
			r2 += r[1]
		else:
			r2 += r[1] + "."

		r3.append({'tweet_id': r[0], 'preprocessed_text': r[1], 'full_text': r[2], 'created_at': r[3], 'cluster_id' : r[4], 'assignment_time': r[5]})

	random.shuffle(r1)
	r1 = r1[:1000]

	if (len(rows1) > 20):
		r2 = summarize(r2, word_count = 25)

	return r1, r2, r3