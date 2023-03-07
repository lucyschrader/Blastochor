from requests import get, post, exceptions
import json
import os
import time
from blastochor.settings.Settings import config

class CoApi():

	# Te Papa Collections Online API

	def __init__(self):
		# Create a new API object
		auth_key = "x-api-key"
		auth_value = config.get("api_key")
		self.headers = {auth_key: auth_value, "Content-Type": "application/json", "Accept": "application/json;profiles=tepapa.collections.api.v1"}

	def search(self, q=None, **kwargs):
		# Build and perform an item search.
		if not q and not kwargs:
			raise ValueError("You must specify search criteria.")
		if q:
			kwargs["query"] = q

		if not config.get("endpoint"):
			print("No endpoint provided.")
			config["endpoint"] = "object"

		request = Request(**kwargs)

		if request.method == "GET":
			response = json.loads(get(request.url, headers=self.headers).text)
		elif request.method == "POST":
			response = json.loads(post(request.url, data=request.post_body, headers=self.headers).text)

		if not config.get("quiet"):
			print("Requesting: {}".format(request.url))
			
		return Results(response, request)


	def view_resource(self, endpoint=None, irn=None):
		# Build a request to return a single document
		if not endpoint or not irn:
			raise ValueError("You must specify a resource type and IRN.")
		if irn:
			resource_url = config.get("base_url") + "/{endpoint}/{irn}".format(endpoint=endpoint, irn=irn)

		if not config.get("quiet"):
			print("Requesting: {}".format(resource_url))

		response = None
		for attempt in range(5):
			if response == None:
				try:
					req = get(resource_url, headers=self.headers, timeout=5)
					response = json.loads(req.text)
				except exceptions.Timeout:
					print("{} timed out!".format(resource_url))
					time.sleep(1)
				except exceptions.ConnectionError:
					print("Disconnected trying to get {}".format(resource_url))
			else:
				return Resource(response, resource_url)

		return None

class Scroll():
	# TODO: Make all this work
	def __init__(self, query=None, fields=None, sort=None, filters=None, headers=None, duration=1):
		self.scroll_post_url = None
		self.scroll_get_url = None

		self.query = query
		self.fields = fields
		self.sort = sort
		self.filters = filters
		self.headers = headers
		self.duration = duration

		self.status_code = None
		self.results = None

		self.build_query()

	def build_query(self):
		if config.get("endpoint") == "object":
			slug = "search"
		else:
			slug = config.get("endpoint")

		scroll_base_url = "{b}/{s}/_scroll/?q=".format(b=config.get("base_url"), s=slug)

		url_parts = []

		if self.query:
			url_parts.append(self.query)
		if self.filters:
			for f in self.filters:
				url_parts.append("{k}:{v}".format(k=f["field"], v=f["keyword"]))

		self.scroll_post_url = "{b}{q}&duration={d}".format(b=scroll_base_url, q=" AND ".join(url_parts), d=self.duration)

		if not config.get("quiet"):
			print("Scroll post url: {}".format(self.scroll_post_url))

	def post_scroll(self, headers):
		r = post(self.scroll_post_url, headers=headers)
		print(r.status_code)
		print(r.text)
		print(json.loads(r).text)
		if r.status_code == 303:
			self.scroll_get_url = "{b}{l}".format(b=config.get("base_url"), l=r.headers["Location"])
			self.results = Results(request=self.scroll_post_url)
			self.status_code = 303

			if not config.get("quiet"):
				print("Scroll get url: {}".format(self.scroll_get_url))

	def get_scroll(self, headers):
		while self.status_code == 303:
			r = get(self.scroll_get_url, headers=headers)
			if r.status_code == 303:
				response = json.loads(r).text
				self.results.add_records(response)
			self.status_code = r.status_code

class Request():

	# A request to the API.

	def __init__(self, query=None, fields=None, sort=None, size=None, start=None, filters=None, facets=None, duration=None):
		self.method = None

		# Build request body for search.
		if config.get("endpoint") == "object":
			self.url = "https://data.tepapa.govt.nz/collection/search"
			self.method = "POST"

			self.post_body = {}

			if query:
				self.post_body.update(self._singleValueFormatter("query", query))
			if fields:
				self.post_body.update(self._multiValueFormatter("fields", fields))
			if sort:
				self.post_body.update(self._singleValueFormatter("sort", sort))
			if start:
				self.post_body.update(self._singleValueFormatter("from", start))
			if size:
				self.post_body.update(self._singleValueFormatter("size", size))
			if filters:
				self.post_body.update(self._singleValueFormatter("filters", filters))
			if facets:
				self.post_body.update(self._singleValueFormatter("facets", facets))

			# CO API requires post data to be json-encoded, not form-encoded
			self.post_body = json.dumps(self.post_body)

		else:
			self.url = "https://data.tepapa.govt.nz/collection/{}?".format(config.get("endpoint"))
			self.method = "GET"

			# TODO: Add 'sort' url part
			url_parts = []

			if start:
				url_parts.append("from={}".format(start))
			if size:
				url_parts.append("size={}".format(size))

			q_parts = []
			if query:
				q_parts.append(query)
			if filters:
				for f in filters:
					q_parts.append("{k}:{v}".format(k=f["field"], v=f["keyword"]))

			q_string = "q=" + " AND ".join(q_parts)
			url_parts.append(q_string)

			self.url += "&".join(url_parts)

	def _singleValueFormatter(self, param_name, value):
		return {param_name: value}

	def _multiValueFormatter(self, param_name, values):
		return {param_name: ",".join(values)}

class Results():
	# Results object for a completed search
	def __init__(self, response, request):
		self.request = request
		self.records = []
		self.result_count = 0
		self.errors = None

		if "errorCode" in response:
			self.errors = response
		else:
			self.result_count = response["_metadata"]["resultset"]["count"]
			self.records = [result for result in response["results"]]

class Resource():
	# Resource object for a returned resource
	def __init__(self, response, request_url):
		self.request_url = request_url
		self.data = response
		self.errors = None
		if "errorCode" in response:
			self.errors = response
		else:
			self.resource = response

	def __repr__(self):
		if self.errors is not None:
			return "Error: {}".format(self.errors["userMessage"])
		else:
			return self.data