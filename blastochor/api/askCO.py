from requests import get, post, exceptions
import json
import os
import time
from blastochor.settings.Settings import config, stats

class Query():
	# Run a single query to the API to return either a page of results or a single resource
	# Provide a method (either GET or POST), a complete URL, and whether redirects are allowed
	# Redirects cannot be allowed on a scroll POST request
	def __init__(self, method=None, url=None, allow_redirects=True):
		auth_key = "x-api-key"
		auth_value = config.get("api_key")
		headers = {auth_key: auth_value, "Content-Type": "application/json", "Accept": "application/json;profiles=tepapa.collections.api.v1"}
		timeout = config.get("timeout")
		attempts = config.get("attempts")

		self.response = None

		for attempt in range(attempts):
			if self.response == None:
				try:
					if not config.get("quiet"):
						print("Requesting {}".format(url))
					if method == "GET":
						self.response = get(url, headers=headers, timeout=timeout, allow_redirects=allow_redirects)
					elif method == "POST":
						self.response = post(url, headers=headers, timeout=timeout, allow_redirects=allow_redirects)
				except exceptions.Timeout:
					if not config.get("quiet"):
						print("{} timed out!".format(url))
					time.sleep(1)
				except exceptions.ConnectionError:
					if not config.get("quiet"):
						print("Disconnected trying to get {}".format(url))
			else:
				stats.api_call_count +=1

class Search():
	def __init__(self, **kwargs):
		# Build a search for a specified page of records
		self.method = None
		self.request_url = config.get("base_url")
		self.request_body = {}

		self.query = kwargs.get("query")
		self.fields = kwargs.get("fields")
		self.sort = kwargs.get("sort")
		self.start = kwargs.get("start")
		self.size = kwargs.get("size")
		self.filters = kwargs.get("filters")
		self.headers = kwargs.get("headers")

		self.status_code = None
		self.results = None

		self.build_query()

		response = Query(method=self.method, url=self.request_url).response
		if response.status_code == 200:
			self.records = Results(response=response, request=self.request_url)

	def build_query(self):
		if config.get("endpoint") == "object":
			self.request_url += "/search"
			self.method = "POST"

			if self.query:
				self.post_body.update(self._singleValueFormatter("query", self.query))
			if self.fields:
				self.post_body.update(self._multiValueFormatter("fields", self.fields))
			if self.sort:
				self.post_body.update(self._singleValueFormatter("sort", self.sort))
			if self.start:
				self.post_body.update(self._singleValueFormatter("from", self.start))
			if self.size:
				self.post_body.update(self._singleValueFormatter("size", self.size))
			if self.filters:
				self.post_body.update(self._singleValueFormatter("filters", self.filters))

			# CO API requires post data to be json-encoded, not form-encoded
			self.post_body = json.dumps(self.post_body)
		else:
			self.request_url += "/{}?q=".format(config.get("endpoint"))
			self.method = "GET"

			url_parts = []
			query_parts = []

			if self.query:
				query_parts.append(query)
			if self.filters:
				for f in filters:
					query_parts.append("{k}:{v}".format(k=f["field"], v=f["keyword"]))

			query_string = " AND ".joint(query_parts)
			url_parts.append(query_string)
			
			if self.fields:
				url_parts.append("fields={}".format(self.fields))
			if self.start:
				url_parts.append("from={}".format(self.start))
			if self.size:
				url_parts.append("size={}".format(self.size))
			if self.sort:
				url_parts.append("sort={}".format(self.sort))

			self.request_url += "&".join(url_parts)

			if not config.get("quiet"):
				print("Search url: {}".format(self.request_url))
		
	def _singleValueFormatter(self, param_name, value):
		return {param_name: value}

	def _multiValueFormatter(self, param_name, values):
		return {param_name: ",".join(values)}

class Scroll():
	# Continually call all matching records until done
	def __init__(self, **kwargs):
		self.scroll_post_url = None
		self.scroll_get_url = None

		self.query = kwargs.get("query")
		self.fields = kwargs.get("fields")
		self.sort = kwargs.get("sort")
		self.size = kwargs.get("size")
		self.filters = kwargs.get("filters")
		self.duration = kwargs.get("duration")

		self.record_limit = None
		self.status_code = None
		self.results = None

		if config.get("max_records") != -1:
			self.record_limit = config.get("max_records")

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

		self.scroll_post_url = "{b}{q}&size={s}&duration={d}".format(b=scroll_base_url, q=" AND ".join(url_parts), s=self.size, d=self.duration)

		if not config.get("quiet"):
			print("Scroll post url: {}".format(self.scroll_post_url))

	def post_scroll(self):
		response = Query(method="POST", url=self.scroll_post_url, allow_redirects=False).response
		if response.status_code == 303:
			self.results = Results(response=response, request=self.scroll_post_url)
			self.scroll_get_url = "{b}{l}".format(b=config.get("base_url"), l=response.headers["Location"])
			self.status_code = 303

			if not config.get("quiet"):
				print("Scroll get url: {}".format(self.scroll_get_url))

	def get_scroll(self):
		while self.status_code == 303:
			if self.record_limit:
				if len(self.results.records) >= self.record_limit:
					if not config.get("quiet"):
						print("Scroll hit record limit")
						break
			response = Query(method="GET", url=self.scroll_get_url).response
			if response.status_code == 303:
				self.results.add_records(response=response)
			self.status_code = response.status_code

class Results():
	# Results object for a completed search or scroll
	def __init__(self, response, request):
		self.request = request
		self.result_count = None
		self.error_code = None
		self.error_message = None
		self.status = response.status_code

		self.records = []

		# TODO: Ensure we're handling the range of possible errors
		response_json = json.loads(response.text)
		if response_json.get("errorCode"):
			self.error_code = self.response_json.get("errorCode")
			self.error_message = self.response_json.get("userMessage")
		else:
			self.count_records(response)
			self.add_records(response)

	def count_records(self, response):
		if self.status == "200" or "303":
			response = json.loads(response.text)
			self.result_count = response["_metadata"]["resultset"]["count"]

	def add_records(self, response):
		if self.status == "200" or "303":
			response = json.loads(response.text)
			records = [result for result in response["results"]]
			self.records.extend(records)
		else:
			return response.status

class Resource():
	# Resource object to build a query and hold a returned resource
	def __init__(self, endpoint, irn):
		self.endpoint = endpoint
		self.irn = irn
		self.request_url = config.get("base_url")
		self.data = None
		self.error_code = None
		self.error_message = None
		self.status = None

		self.get_resource()

	def get_resource(self):
		self.request_url += "/{endpoint}/{irn}".format(endpoint=self.endpoint, irn=self.irn)
		response = Query(method="GET", url=self.request_url).response
		
		self.status = response.status_code
		response_json = json.loads(response.text)
		if response_json.get("errorCode"):
			self.error_code = self.response_json.get("errorCode")
			self.error_message = self.response_json.get("userMessage")
		else:
			self.data = json.loads(response.text)