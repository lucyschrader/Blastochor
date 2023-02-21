from requests import get, post, exceptions
import json
import os
import time

auth_key = "x-api-key"
auth_value = os.environ.get('TE-PAPA-KEY')

headers = {auth_key: auth_value, "Content-Type": "application/json", "Accept": "application/json;profiles=tepapa.collections.api.v1"}

class CoApi():

	# Te Papa Collections Online API

	def __init__(self, quiet=False):
		# Create a new API object with a flag for verbosity.
		self.quiet = quiet

	def search(self, q=None, **kwargs):
		# Build and perform an item search.
		if not q and not kwargs:
			raise ValueError("You must specify search criteria.")
		if q:
			kwargs["query"] = q

		kwargs["quiet"] = self.quiet
		request = Request(**kwargs)
		response = json.loads(post(request.url, data=request.post_body, headers=headers).text)

		if not self.quiet:
			print("Requesting: {}".format(request.url))

		return Results(response, request)

	def view_resource(self, resource_type=None, irn=None):
		# Build a request to return a single document
		if not resource_type and not irn:
			raise ValueError("You must specify a resource type and IRN.")
		if irn:
			resource_url = "https://data.tepapa.govt.nz/collection/{res}/{irn}".format(res=resource_type, irn=irn)

		if self.quiet == False:
			print("Requesting: {}".format(resource_url))

		response = None
		for attempt in range(5):
			if response == None:
				try:
					req = get(resource_url, headers=headers, timeout=5)
					response = json.loads(req.text)
				except exceptions.Timeout:
					print("{} timed out!".format(resource_url))
					time.sleep(1)
				except exceptions.ConnectionError:
					print("Diconnected trying to get {}".format(resource_url))
			else:
				return Resource(response, resource_url)

		return None

class Request():

	# A request to the API.

	def __init__(self, query=None, fields=None, sort=None, size=None, q_from=None, filters=None, facets=None, quiet=True):
		# Build request body for search.
		self.url = "https://data.tepapa.govt.nz/collection/search"
		self.post_body = {}

		if query:
			self.post_body.update(self._singleValueFormatter("query", query))
		if fields:
			self.post_body.update(self._multiValueFormatter("fields", fields))
		if sort:
			self.post_body.update(self._singleValueFormatter("sort", sort))
		if q_from:
			self.post_body.update(self._singleValueFormatter("from", q_from))
		if size:
			self.post_body.update(self._singleValueFormatter("size", size))
		if filters:
			self.post_body.update(self._singleValueFormatter("filters", filters))
		if facets:
			self.post_body.update(self._singleValueFormatter("facets", facets))

		# CO API requires post data to be json-encoded, not form-encoded
		self.post_body = json.dumps(self.post_body)

	def _singleValueFormatter(self, param_name, value):
		return {param_name: value}

	def _multiValueFormatter(self, param_name, values):
		return {param_name: ",".join(values)}

class Results():
	# Results object for a completed search
	def __init__(self, response, request):
		self.request = request
		self.result_count = 0
		self.records = []
#		self.facets = None
		self.errors = None
		if "errorCode" in response:
			self.errors = response
		else:
			self.result_count = response["_metadata"]["resultset"]["count"]
			self.records = [result for result in response["results"]]
			#self.facets = response["facets"]

	def __repr__(self):
		if self.errors is not None:
			return "Error: {}".format(self.errors["userMessage"])
		else:
			return "".join(map(str, self.records))

class Resource():
	# Resource object for a returned resource
	def __init__(self, response, request_url):
		self.request_url = request_url
		self.resource = response
		self.errors = None
		if "errorCode" in response:
			self.errors = response
		else:
			self.resource = response

	def __repr__(self):
		if self.errors is not None:
			return "Error: {}".format(self.errors["userMessage"])
		else:
			return self.resource